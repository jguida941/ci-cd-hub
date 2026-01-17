"""Detect stale documentation references.

This package implements `cihub docs stale` which detects documentation
references to code symbols that have been removed, renamed, or deleted.

Architecture (from DOC_AUTOMATION_AUDIT.md Part 9):
1. EXTRACT SYMBOLS - Parse Python AST for functions/classes/constants
2. EXTRACT DOC REFS - Parse markdown for backticks, CLI commands, file paths
3. GIT DIFF - Compare base vs head to find removed/renamed symbols
4. CORRELATE - Match doc refs to changed symbols
5. OUTPUT - Human, JSON, or AI prompt pack format

Module structure:
- types: Data models (CodeSymbol, DocReference, StaleReference, StaleReport)
- extraction: Symbol extraction (AST) and reference extraction (Markdown)
- git: Git operations (compare symbols, file status, etc.)
- comparison: Stale reference detection (correlation logic)
- output: Output formatters (human, JSON, AI prompt pack)

Re-exports all public API from submodules for backward compatibility.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.github_context import OutputContext
from cihub.utils.paths import project_root

# Import from submodules
from .comparison import (
    filter_by_reason,
    find_stale_references,
    group_stale_by_file,
)
from .extraction import (
    extract_doc_references,
    extract_python_symbols,
    extract_refs_from_file,
    extract_symbols_from_file,
)
from .git import (
    compare_symbols,
    get_changed_files,
    get_file_at_ref,
    get_file_status,
    get_merge_base,
    get_renamed_files,
    get_symbols_at_ref,
    is_git_repo,
    resolve_git_ref,
)
from .output import (
    format_ai_output,
    format_github_summary,
    format_human_output,
    format_json_output,
)
from .types import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_SINCE,
    FALSE_POSITIVE_TOKENS,
    KIND_BACKTICK,
    KIND_CLI_COMMAND,
    KIND_CLI_FLAG,
    KIND_CONFIG_KEY,
    KIND_ENV_VAR,
    KIND_FILE_PATH,
    PARSED_FENCE_TYPES,
    REASON_DELETED_FILE,
    REASON_REMOVED,
    REASON_RENAMED,
    SKIPPED_FENCE_TYPES,
    CodeSymbol,
    DocReference,
    StaleReference,
    StaleReport,
)

__all__ = [
    # Main command
    "cmd_docs_stale",
    # Types
    "CodeSymbol",
    "DocReference",
    "StaleReference",
    "StaleReport",
    # Constants
    "DEFAULT_SINCE",
    "DEFAULT_EXCLUDE_PATTERNS",
    "PARSED_FENCE_TYPES",
    "SKIPPED_FENCE_TYPES",
    "FALSE_POSITIVE_TOKENS",
    "KIND_BACKTICK",
    "KIND_CLI_COMMAND",
    "KIND_CLI_FLAG",
    "KIND_FILE_PATH",
    "KIND_CONFIG_KEY",
    "KIND_ENV_VAR",
    "REASON_REMOVED",
    "REASON_RENAMED",
    "REASON_DELETED_FILE",
    # Extraction
    "extract_python_symbols",
    "extract_symbols_from_file",
    "extract_doc_references",
    "extract_refs_from_file",
    # Git
    "is_git_repo",
    "resolve_git_ref",
    "get_merge_base",
    "get_changed_files",
    "get_file_status",
    "get_file_at_ref",
    "get_symbols_at_ref",
    "compare_symbols",
    "get_renamed_files",
    # Comparison
    "find_stale_references",
    "group_stale_by_file",
    "filter_by_reason",
    # Output
    "format_human_output",
    "format_json_output",
    "format_ai_output",
    "format_github_summary",
]


def _matches_pattern(path: str, pattern: str) -> bool:
    """Simple glob-like pattern matching."""
    return fnmatch.fnmatch(path, pattern)


def cmd_docs_stale(args: argparse.Namespace) -> CommandResult:
    """Detect stale documentation references.

    Compares code symbols between a base git ref and HEAD, then finds
    documentation references to removed or renamed symbols.

    This is the main entry point for `cihub docs stale`.
    """
    # Extract arguments with defaults
    since = getattr(args, "since", DEFAULT_SINCE) or DEFAULT_SINCE
    include_all = getattr(args, "all", False)
    include_generated = getattr(args, "include_generated", False)
    fail_on_stale = getattr(args, "fail_on_stale", False)
    skip_fences = getattr(args, "skip_fences", False)
    # Note: --ai and --json modes are handled by the CLI framework's renderer selection
    code_path = Path(getattr(args, "code", "cihub"))
    docs_path = Path(getattr(args, "docs", "docs"))
    output_dir = getattr(args, "output_dir", None)
    tool_output = getattr(args, "tool_output", None)
    ai_output = getattr(args, "ai_output", None)

    root = project_root()

    # Verify git repo
    if not is_git_repo(root):
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Not a git repository",
            problems=[
                {
                    "severity": "error",
                    "message": f"{root} is not a git repository",
                    "code": "CIHUB-DOCS-NOT-GIT",
                }
            ],
        )

    # Resolve git ref
    resolved = resolve_git_ref(since, root)
    if not resolved:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Invalid git reference: {since}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Could not resolve git reference: {since}",
                    "code": "CIHUB-DOCS-BAD-REF",
                }
            ],
        )

    # Build exclusion patterns
    exclude_patterns: list[str] = []
    if not include_generated:
        exclude_patterns.append("docs/reference/**")
    if not include_all:
        exclude_patterns.append("docs/development/archive/**")

    # Compare symbols between base and head
    removed, added, renamed = compare_symbols(since, root / code_path, root)

    # Get file status (deleted, renamed)
    file_status = get_file_status(since, root)
    deleted_files = [f for f, s in file_status.items() if s == "D"]
    renamed_file_pairs = get_renamed_files(since, root)

    # Collect doc references
    docs_dir = root / docs_path
    all_refs: list[DocReference] = []

    for md_file in docs_dir.rglob("*.md"):
        # Check exclusion patterns
        rel_path = str(md_file.relative_to(root))
        if any(_matches_pattern(rel_path, pat) for pat in exclude_patterns):
            continue

        refs = extract_refs_from_file(md_file, skip_fences)
        all_refs.extend(refs)

    # Also check root README.md
    root_readme = root / "README.md"
    if root_readme.exists():
        all_refs.extend(extract_refs_from_file(root_readme, skip_fences))

    # Find stale references
    stale = find_stale_references(
        all_refs,
        removed,
        renamed,
        deleted_files,
        renamed_file_pairs,
    )

    # Build report
    report = StaleReport(
        git_range=since,
        changed_symbols=list(removed | added | {old for old, _ in renamed}),
        removed_symbols=list(removed),
        added_symbols=list(added),
        renamed_symbols=renamed,
        deleted_files=deleted_files,
        renamed_files=renamed_file_pairs,
        stale_references=stale,
    )

    # Generate outputs
    json_data = format_json_output(report)

    # Write tool output if requested
    if tool_output:
        try:
            tool_path = Path(tool_output)
            tool_path.parent.mkdir(parents=True, exist_ok=True)
            tool_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        except OSError as e:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Failed to write tool output: {e}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Could not write to {tool_output}: {e}",
                        "code": "CIHUB-DOCS-WRITE-ERROR",
                    }
                ],
            )

    # Write AI output if requested
    if ai_output:
        try:
            ai_path = Path(ai_output)
            ai_path.parent.mkdir(parents=True, exist_ok=True)
            ai_text = format_ai_output(report)
            ai_path.write_text(ai_text, encoding="utf-8")
        except OSError as e:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Failed to write AI output: {e}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Could not write to {ai_output}: {e}",
                        "code": "CIHUB-DOCS-WRITE-ERROR",
                    }
                ],
            )

    # Write to output directory if requested
    if output_dir:
        try:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            (out_path / "docs_stale.json").write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            (out_path / "docs_stale.prompt.md").write_text(format_ai_output(report), encoding="utf-8")
        except OSError as e:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Failed to write to output directory: {e}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Could not write to {output_dir}: {e}",
                        "code": "CIHUB-DOCS-WRITE-ERROR",
                    }
                ],
            )

    # Write GitHub summary if requested (checks both --summary and --github-summary)
    ctx = OutputContext.from_args(args)
    if ctx.has_summary():
        ctx.write_summary(format_github_summary(report, since))

    # Determine exit code
    has_stale = len(stale) > 0
    exit_code = EXIT_SUCCESS
    if has_stale and fail_on_stale:
        exit_code = EXIT_FAILURE

    # Build summary message
    summary = f"Stale references: {len(stale)}"
    if not has_stale:
        summary = "No stale references found"

    # Return CommandResult with report in data
    # AIRenderer will find "stale_report" and call format_ai_output(report)
    # HumanRenderer/JsonRenderer use summary + problems
    return CommandResult(
        exit_code=exit_code,
        summary=summary,
        problems=[
            {
                "severity": "warning" if not fail_on_stale else "error",
                "message": f"{ref.doc_file}:{ref.doc_line}: `{ref.reference}` ({ref.reason})",
                "code": "CIHUB-DOCS-STALE",
            }
            for ref in stale
        ],
        data={
            **json_data,
            "stale_report": report,  # For AIRenderer
        },
    )
