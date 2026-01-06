"""Detect stale documentation references.

This module implements `cihub docs stale` which detects documentation
references to code symbols that have been removed, renamed, or deleted.

Architecture (from DOC_AUTOMATION_AUDIT.md Part 9):
1. EXTRACT SYMBOLS - Parse Python AST for functions/classes/constants
2. EXTRACT DOC REFS - Parse markdown for backticks, CLI commands, file paths
3. GIT DIFF - Compare base vs head to find removed/renamed symbols
4. CORRELATE - Match doc refs to changed symbols
5. OUTPUT - Human, JSON, or AI prompt pack format
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.github_context import OutputContext
from cihub.utils.paths import hub_root

# Constants from Part 11
DEFAULT_SINCE = "HEAD~10"

# Fence types to parse for CLI examples (Part 11 Decision 1)
PARSED_FENCE_TYPES = {"bash", "shell", "console", "sh", "zsh", ""}

# Fence types to skip (illustrative code examples)
SKIPPED_FENCE_TYPES = {"python", "json", "yaml", "xml", "java", "javascript", "typescript", "go", "rust"}

# Default exclusion patterns (Part 11 Decision 2)
DEFAULT_EXCLUDE_PATTERNS = [
    "docs/reference/**",  # Generated docs - use `cihub docs check` instead
    "docs/development/archive/**",  # Archived docs - historical
]

# False positive filters (Part 11)
FALSE_POSITIVE_TOKENS = frozenset({
    "true", "false", "none", "null", "yes", "no",
    "ok", "error", "warning", "info", "debug",
    "http", "https", "localhost", "github",
    "md", "py", "json", "yaml", "yml", "txt",
    "a", "b", "c", "i", "j", "k", "n", "x", "y", "z",
})


@dataclass
class CodeSymbol:
    """A symbol extracted from Python code."""

    name: str
    kind: str  # "function", "class", "constant"
    file: str
    line: int


@dataclass
class DocReference:
    """A reference extracted from documentation."""

    reference: str
    kind: str  # "backtick", "cli_command", "cli_flag", "file_path", "config_key", "env_var"
    file: str
    line: int
    context: str  # Surrounding text for AI output


@dataclass
class StaleReference:
    """A documentation reference that may be stale."""

    doc_file: str
    doc_line: int
    reference: str
    reason: str  # "removed", "renamed", "deleted_file"
    suggestion: str
    context: str


@dataclass
class StaleReport:
    """Complete report of stale references."""

    git_range: str
    changed_symbols: list[str] = field(default_factory=list)
    removed_symbols: list[str] = field(default_factory=list)
    added_symbols: list[str] = field(default_factory=list)
    renamed_symbols: list[tuple[str, str]] = field(default_factory=list)  # (old, new)
    deleted_files: list[str] = field(default_factory=list)
    renamed_files: list[tuple[str, str]] = field(default_factory=list)  # (old, new)
    stale_references: list[StaleReference] = field(default_factory=list)


# =============================================================================
# Symbol Extraction (Python AST)
# =============================================================================


def extract_python_symbols(content: str, file_path: str = "<unknown>") -> list[CodeSymbol]:
    """Extract functions, classes, and constants from Python source.

    Args:
        content: Python source code
        file_path: Path for error reporting

    Returns:
        List of CodeSymbol objects
    """
    symbols: list[CodeSymbol] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Gracefully handle unparseable Python
        return symbols

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            symbols.append(CodeSymbol(
                name=node.name,
                kind="function",
                file=file_path,
                line=node.lineno,
            ))
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols.append(CodeSymbol(
                name=node.name,
                kind="async_function",
                file=file_path,
                line=node.lineno,
            ))
        elif isinstance(node, ast.ClassDef):
            symbols.append(CodeSymbol(
                name=node.name,
                kind="class",
                file=file_path,
                line=node.lineno,
            ))
        elif isinstance(node, ast.Assign):
            # Check for module-level constants (UPPER_CASE)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(CodeSymbol(
                        name=target.id,
                        kind="constant",
                        file=file_path,
                        line=node.lineno,
                    ))

    return symbols


def extract_symbols_from_file(file_path: Path) -> list[CodeSymbol]:
    """Extract symbols from a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return extract_python_symbols(content, str(file_path))
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# Reference Extraction (Markdown)
# =============================================================================


def _parse_fenced_blocks(content: str) -> list[tuple[str, str, int, int]]:
    """Parse fenced code blocks from markdown.

    Returns:
        List of (language, content, start_line, end_line) tuples
    """
    blocks: list[tuple[str, str, int, int]] = []
    lines = content.splitlines()
    in_block = False
    block_lang = ""
    block_content: list[str] = []
    block_start = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not in_block and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_block = True
            block_lang = stripped[3:].strip().split()[0] if len(stripped) > 3 else ""
            block_start = i
            block_content = []
        elif in_block and (stripped == "```" or stripped == "~~~"):
            blocks.append((block_lang.lower(), "\n".join(block_content), block_start, i))
            in_block = False
            block_lang = ""
            block_content = []
        elif in_block:
            block_content.append(line)

    return blocks


def _get_line_region(content: str, line_num: int) -> str:
    """Determine if a line is in prose, inline code, or fenced block."""
    blocks = _parse_fenced_blocks(content)
    for _lang, _block_content, start, end in blocks:
        if start <= line_num <= end:
            return "fenced"
    return "prose"


def extract_doc_references(
    content: str,
    file_path: str = "<unknown>",
    skip_fences: bool = False,
) -> list[DocReference]:
    """Extract code references from markdown content.

    Extracts:
    - Backtick references (`symbol_name`)
    - CLI commands (`cihub ...`)
    - CLI flags (`--flag-name`)
    - File paths (`cihub/commands/...`)
    - Config keys (`repo.owner`, `python.pytest.enabled`)
    - Environment variables (`CIHUB_*`, `CI_HUB_*`)

    Args:
        content: Markdown content
        file_path: Path for reporting
        skip_fences: If True, don't parse fenced blocks

    Returns:
        List of DocReference objects
    """
    refs: list[DocReference] = []
    lines = content.splitlines()
    blocks = _parse_fenced_blocks(content)

    # Build line -> block mapping
    line_to_block: dict[int, tuple[str, str]] = {}
    for lang, block_content, start, end in blocks:
        for ln in range(start, end + 1):
            line_to_block[ln] = (lang, block_content)

    # Pattern definitions
    backtick_re = re.compile(r"`([^`]+)`")
    cli_command_re = re.compile(r"\bcihub\s+[\w-]+(?:\s+[\w-]+)*")
    cli_flag_re = re.compile(r"--[\w-]+")
    file_path_re = re.compile(r"\b(cihub/[\w/.-]+\.py|templates/[\w/.-]+|config/[\w/.-]+)")
    config_key_re = re.compile(r"\b([a-z_]+(?:\.[a-z_]+)+)\b")
    env_var_re = re.compile(r"\b(CIHUB_[A-Z_]+|CI_HUB_[A-Z_]+|GITHUB_[A-Z_]+)\b")

    def get_context(line_num: int, lines: list[str], window: int = 1) -> str:
        """Get context around a line."""
        start = max(0, line_num - 1 - window)
        end = min(len(lines), line_num + window)
        return "\n".join(lines[start:end])

    def is_false_positive(token: str) -> bool:
        """Check if a token is a common false positive."""
        lower = token.lower()
        if lower in FALSE_POSITIVE_TOKENS:
            return True
        # Skip very short tokens
        if len(token) <= 2:
            return True
        # Skip file extensions
        if token.startswith("."):
            return True
        # Skip URLs
        if token.startswith("http://") or token.startswith("https://"):
            return True
        return False

    for line_num, line in enumerate(lines, 1):
        # Check if we're in a fenced block
        block_info = line_to_block.get(line_num)
        if block_info:
            lang, _ = block_info
            if skip_fences:
                continue
            if lang.lower() in SKIPPED_FENCE_TYPES:
                continue
            # Only parse CLI-like fences
            if lang.lower() not in PARSED_FENCE_TYPES:
                continue

        # Skip comment lines in fences
        stripped = line.strip()
        if stripped.startswith("#") and block_info:
            continue

        context = get_context(line_num, lines)

        # Extract backtick references
        for match in backtick_re.finditer(line):
            token = match.group(1)
            if is_false_positive(token):
                continue

            # Determine kind based on content
            if token.startswith("cihub "):
                kind = "cli_command"
            elif token.startswith("--"):
                kind = "cli_flag"
            elif "/" in token and token.endswith(".py"):
                kind = "file_path"
            elif "." in token and token[0].islower():
                kind = "config_key"
            elif token.isupper() and "_" in token:
                kind = "env_var"
            else:
                kind = "backtick"

            refs.append(DocReference(
                reference=token,
                kind=kind,
                file=file_path,
                line=line_num,
                context=context,
            ))

        # Extract CLI commands in prose (not backticked)
        for match in cli_command_re.finditer(line):
            cmd = match.group(0)
            refs.append(DocReference(
                reference=cmd,
                kind="cli_command",
                file=file_path,
                line=line_num,
                context=context,
            ))

        # Extract file paths
        for match in file_path_re.finditer(line):
            path = match.group(1)
            refs.append(DocReference(
                reference=path,
                kind="file_path",
                file=file_path,
                line=line_num,
                context=context,
            ))

        # Extract environment variables
        for match in env_var_re.finditer(line):
            env = match.group(1)
            refs.append(DocReference(
                reference=env,
                kind="env_var",
                file=file_path,
                line=line_num,
                context=context,
            ))

    return refs


def extract_refs_from_file(
    file_path: Path,
    skip_fences: bool = False,
) -> list[DocReference]:
    """Extract references from a markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return extract_doc_references(content, str(file_path), skip_fences)
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# Git Operations
# =============================================================================


def _run_git(args: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str, str]:
    """Run a git command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "git not found"


def is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository."""
    code, _, _ = _run_git(["rev-parse", "--git-dir"], path)
    return code == 0


def resolve_git_ref(ref: str, cwd: Path) -> str | None:
    """Resolve a git reference to a commit hash."""
    code, stdout, _ = _run_git(["rev-parse", ref], cwd)
    if code == 0:
        return stdout.strip()
    return None


def get_merge_base(ref1: str, ref2: str, cwd: Path) -> str | None:
    """Get the merge base of two refs."""
    code, stdout, _ = _run_git(["merge-base", ref1, ref2], cwd)
    if code == 0:
        return stdout.strip()
    return None


def get_changed_files(since: str, cwd: Path) -> list[str]:
    """Get list of Python files changed since a ref."""
    code, stdout, _ = _run_git(
        ["diff", "--name-only", since, "--", "*.py"],
        cwd,
    )
    if code != 0:
        return []
    return [f for f in stdout.strip().split("\n") if f]


def get_file_status(since: str, cwd: Path) -> dict[str, str]:
    """Get file status (Added/Deleted/Modified/Renamed) since a ref.

    Returns:
        Dict mapping file path to status (A/D/M/R)
    """
    code, stdout, _ = _run_git(
        ["diff", "--name-status", "--find-renames", since],
        cwd,
    )
    if code != 0:
        return {}

    status: dict[str, str] = {}
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            stat = parts[0][0]  # First char of status
            path = parts[1]
            status[path] = stat
            # Handle renames (R100 old_path new_path)
            if stat == "R" and len(parts) >= 3:
                old_path = parts[1]
                new_path = parts[2]
                status[old_path] = "R"
                status[new_path] = "A"

    return status


def get_file_at_ref(ref: str, file_path: str, cwd: Path) -> str | None:
    """Get file content at a specific git ref."""
    code, stdout, _ = _run_git(["show", f"{ref}:{file_path}"], cwd)
    if code == 0:
        return stdout
    return None


def get_symbols_at_ref(ref: str, file_path: str, cwd: Path) -> set[str]:
    """Get symbol names from a file at a specific git ref."""
    content = get_file_at_ref(ref, file_path, cwd)
    if content is None:
        return set()
    symbols = extract_python_symbols(content, file_path)
    return {s.name for s in symbols}


def compare_symbols(
    since: str,
    code_path: Path,
    cwd: Path,
) -> tuple[set[str], set[str], list[tuple[str, str]]]:
    """Compare symbols between base and head.

    Returns:
        Tuple of (removed, added, renamed) where renamed is list of (old, new) pairs
    """
    changed_files = get_changed_files(since, cwd)

    base_symbols: set[str] = set()
    head_symbols: set[str] = set()

    for file_path in changed_files:
        # Get symbols at base
        base = get_symbols_at_ref(since, file_path, cwd)
        base_symbols.update(base)

        # Get symbols at head (current)
        full_path = cwd / file_path
        if full_path.exists():
            head = {s.name for s in extract_symbols_from_file(full_path)}
            head_symbols.update(head)

    removed = base_symbols - head_symbols
    added = head_symbols - base_symbols

    # Try to detect renames (simple heuristic: similar names)
    renamed: list[tuple[str, str]] = []
    for old in list(removed):
        for new in list(added):
            # Simple rename detection: one is substring of the other
            # or they differ by only a few characters
            if old in new or new in old or _levenshtein_ratio(old, new) > 0.7:
                renamed.append((old, new))
                removed.discard(old)
                added.discard(new)
                break

    return removed, added, renamed


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not s1 or not s2:
        return 0.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0

    # Simple character-based similarity
    matches = sum(1 for c1, c2 in zip(s1, s2) if c1 == c2)
    return matches / max_len


# =============================================================================
# Stale Reference Detection
# =============================================================================


def find_stale_references(
    doc_refs: list[DocReference],
    removed_symbols: set[str],
    renamed_symbols: list[tuple[str, str]],
    deleted_files: list[str],
    renamed_files: list[tuple[str, str]],
) -> list[StaleReference]:
    """Find documentation references that are stale.

    Only flags REMOVED/RENAMED symbols, never ADDED.

    Args:
        doc_refs: All references extracted from docs
        removed_symbols: Symbols that were removed
        renamed_symbols: Symbols that were renamed (old, new)
        deleted_files: Files that were deleted
        renamed_files: Files that were renamed (old, new)

    Returns:
        List of StaleReference objects
    """
    stale: list[StaleReference] = []
    rename_map = dict(renamed_symbols)
    file_rename_map = dict(renamed_files)

    for ref in doc_refs:
        token = ref.reference

        # Check if it matches a removed symbol
        if token in removed_symbols:
            suggestion = "Symbol was removed from codebase"
            # Check if there's a likely rename
            if token in rename_map:
                suggestion = f"Consider updating to `{rename_map[token]}`"
            stale.append(StaleReference(
                doc_file=ref.file,
                doc_line=ref.line,
                reference=token,
                reason="removed",
                suggestion=suggestion,
                context=ref.context,
            ))
            continue

        # Check if it matches a renamed symbol
        if token in rename_map:
            stale.append(StaleReference(
                doc_file=ref.file,
                doc_line=ref.line,
                reference=token,
                reason="renamed",
                suggestion=f"Update to `{rename_map[token]}`",
                context=ref.context,
            ))
            continue

        # Check if it references a deleted file
        if ref.kind == "file_path":
            if token in deleted_files:
                suggestion = "File was deleted"
                if token in file_rename_map:
                    suggestion = f"File renamed to `{file_rename_map[token]}`"
                stale.append(StaleReference(
                    doc_file=ref.file,
                    doc_line=ref.line,
                    reference=token,
                    reason="deleted_file",
                    suggestion=suggestion,
                    context=ref.context,
                ))

    return stale


# =============================================================================
# Output Formatting
# =============================================================================


def format_human_output(report: StaleReport) -> str:
    """Format report as human-readable text."""
    lines: list[str] = []

    lines.append("Stale Documentation Report")
    lines.append("=" * 60)
    lines.append(f"Git range: {report.git_range}")
    lines.append("")

    # Stats
    lines.append("Summary:")
    lines.append(f"  Removed symbols: {len(report.removed_symbols)}")
    lines.append(f"  Renamed symbols: {len(report.renamed_symbols)}")
    lines.append(f"  Deleted files: {len(report.deleted_files)}")
    lines.append(f"  Stale references: {len(report.stale_references)}")
    lines.append("")

    if not report.stale_references:
        lines.append("No stale references found.")
        return "\n".join(lines)

    # Group by file
    by_file: dict[str, list[StaleReference]] = {}
    for ref in report.stale_references:
        by_file.setdefault(ref.doc_file, []).append(ref)

    for doc_file, refs in sorted(by_file.items()):
        lines.append(f"{doc_file}:")
        for ref in sorted(refs, key=lambda r: r.doc_line):
            lines.append(f"  Line {ref.doc_line}: `{ref.reference}` ({ref.reason})")
            lines.append(f"    → {ref.suggestion}")
        lines.append("")

    return "\n".join(lines)


def format_json_output(report: StaleReport) -> dict[str, Any]:
    """Format report as JSON-serializable dict."""
    return {
        "git_range": report.git_range,
        "stats": {
            "removed_symbols": len(report.removed_symbols),
            "added_symbols": len(report.added_symbols),
            "renamed_symbols": len(report.renamed_symbols),
            "deleted_files": len(report.deleted_files),
            "renamed_files": len(report.renamed_files),
            "stale_refs": len(report.stale_references),
        },
        "changed_symbols": {
            "removed": list(report.removed_symbols),
            "added": list(report.added_symbols),
            "renamed": [{"old": old, "new": new} for old, new in report.renamed_symbols],
        },
        "file_changes": {
            "deleted": report.deleted_files,
            "renamed": [{"old": old, "new": new} for old, new in report.renamed_files],
        },
        "stale_references": [
            {
                "doc_file": ref.doc_file,
                "doc_line": ref.doc_line,
                "reference": ref.reference,
                "reason": ref.reason,
                "suggestion": ref.suggestion,
                "context": ref.context,
            }
            for ref in report.stale_references
        ],
    }


def format_ai_output(report: StaleReport) -> str:
    """Format report as AI-consumable markdown prompt pack.

    Following Part 12.D guidelines:
    - Per-file packets with context
    - Explicit constraints
    - No generated docs or ADR edits
    """
    lines: list[str] = []

    lines.append("# Documentation Staleness Report - AI Prompt Pack")
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    lines.append("You are helping update documentation that references code symbols")
    lines.append("that have been removed or renamed. Please follow these rules:")
    lines.append("")
    lines.append("1. **DO NOT** edit files under `docs/reference/**` (these are generated)")
    lines.append("2. **DO NOT** modify ADR content in `docs/adr/**` (requires human authorship)")
    lines.append("3. Make minimal edits - only update the stale references")
    lines.append("4. Preserve code fences and existing formatting")
    lines.append("5. Use 'CLI' terminology (never internal nicknames)")
    lines.append("6. Produce unified diff output for review")
    lines.append("")

    lines.append("## Changes Summary")
    lines.append("")
    lines.append(f"Git range: `{report.git_range}`")
    lines.append("")

    if report.renamed_symbols:
        lines.append("### Renamed Symbols")
        lines.append("")
        for old, new in report.renamed_symbols:
            lines.append(f"- `{old}` → `{new}`")
        lines.append("")

    if report.removed_symbols:
        lines.append("### Removed Symbols")
        lines.append("")
        for sym in sorted(report.removed_symbols):
            lines.append(f"- `{sym}`")
        lines.append("")

    if not report.stale_references:
        lines.append("No stale references found.")
        return "\n".join(lines)

    lines.append("## Files Requiring Updates")
    lines.append("")

    # Group by file
    by_file: dict[str, list[StaleReference]] = {}
    for ref in report.stale_references:
        by_file.setdefault(ref.doc_file, []).append(ref)

    for doc_file, refs in sorted(by_file.items()):
        # Skip generated docs and ADRs
        if "docs/reference/" in doc_file or "docs/adr/" in doc_file:
            continue

        lines.append(f"### `{doc_file}`")
        lines.append("")

        for ref in sorted(refs, key=lambda r: r.doc_line):
            lines.append(f"**Line {ref.doc_line}:** Reference `{ref.reference}`")
            lines.append(f"- Reason: {ref.reason}")
            lines.append(f"- Suggestion: {ref.suggestion}")
            lines.append("")
            lines.append("Context:")
            lines.append("```")
            lines.append(ref.context)
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


# =============================================================================
# Main Command
# =============================================================================


def cmd_docs_stale(args: argparse.Namespace) -> CommandResult:
    """Detect stale documentation references.

    Compares code symbols between a base git ref and HEAD, then finds
    documentation references to removed or renamed symbols.
    """
    since = getattr(args, "since", DEFAULT_SINCE)
    include_all = getattr(args, "all", False)
    include_generated = getattr(args, "include_generated", False)
    fail_on_stale = getattr(args, "fail_on_stale", False)
    skip_fences = getattr(args, "skip_fences", False)
    ai_mode = getattr(args, "ai", False)
    json_mode = getattr(args, "json", False)
    code_path = Path(getattr(args, "code", "cihub"))
    docs_path = Path(getattr(args, "docs", "docs"))
    output_dir = getattr(args, "output_dir", None)
    tool_output = getattr(args, "tool_output", None)
    ai_output = getattr(args, "ai_output", None)

    root = hub_root()

    # Verify git repo
    if not is_git_repo(root):
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Not a git repository",
            problems=[{
                "severity": "error",
                "message": f"{root} is not a git repository",
                "code": "CIHUB-DOCS-NOT-GIT",
            }],
        )

    # Resolve git ref
    resolved = resolve_git_ref(since, root)
    if not resolved:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Invalid git reference: {since}",
            problems=[{
                "severity": "error",
                "message": f"Could not resolve git reference: {since}",
                "code": "CIHUB-DOCS-BAD-REF",
            }],
        )

    # Build exclusion patterns
    exclude_patterns: list[str] = []
    if not include_generated:
        exclude_patterns.append("docs/reference/**")
    if not include_all:
        exclude_patterns.append("docs/development/archive/**")

    # Compare symbols
    removed, added, renamed = compare_symbols(since, root / code_path, root)

    # Get file status
    file_status = get_file_status(since, root)
    deleted_files = [f for f, s in file_status.items() if s == "D"]
    renamed_file_pairs: list[tuple[str, str]] = []  # TODO: parse rename pairs

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
        Path(tool_output).write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    # Write AI output if requested
    if ai_output:
        ai_text = format_ai_output(report)
        Path(ai_output).write_text(ai_text, encoding="utf-8")

    # Write to output directory if requested
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "docs_stale.json").write_text(
            json.dumps(json_data, indent=2), encoding="utf-8"
        )
        (out_path / "docs_stale.prompt.md").write_text(
            format_ai_output(report), encoding="utf-8"
        )

    # Write GitHub summary if requested
    ctx = OutputContext.from_args(args)
    if ctx.summary_path:
        summary_lines = [
            "## Documentation Staleness Check",
            "",
            f"Git range: `{since}`",
            "",
            f"- Removed symbols: **{len(removed)}**",
            f"- Renamed symbols: **{len(renamed)}**",
            f"- Stale references: **{len(stale)}**",
            "",
        ]
        if stale:
            summary_lines.append("### Stale References Found")
            summary_lines.append("")
            for ref in stale[:10]:  # Limit to first 10
                summary_lines.append(f"- `{ref.doc_file}:{ref.doc_line}`: `{ref.reference}` ({ref.reason})")
            if len(stale) > 10:
                summary_lines.append(f"- ... and {len(stale) - 10} more")
        else:
            summary_lines.append("✅ No stale references found")
        ctx.write_summary("\n".join(summary_lines))

    # Determine exit code
    has_stale = len(stale) > 0
    exit_code = EXIT_SUCCESS
    if has_stale and fail_on_stale:
        exit_code = EXIT_FAILURE

    # Format output
    if ai_mode:
        # AI mode prints to stdout (user can redirect)
        ai_text = format_ai_output(report)
        # Return as data for CLI to handle
        return CommandResult(
            exit_code=exit_code,
            summary=f"Stale references: {len(stale)}",
            data={"ai_output": ai_text, **json_data},
        )

    summary = f"Stale references: {len(stale)}"
    if not has_stale:
        summary = "No stale references found"

    return CommandResult(
        exit_code=exit_code,
        summary=summary,
        problems=[{
            "severity": "warning" if not fail_on_stale else "error",
            "message": f"{ref.doc_file}:{ref.doc_line}: `{ref.reference}` ({ref.reason})",
            "code": "CIHUB-DOCS-STALE",
        } for ref in stale],
        data=json_data,
    )


def _matches_pattern(path: str, pattern: str) -> bool:
    """Simple glob-like pattern matching."""
    import fnmatch
    return fnmatch.fnmatch(path, pattern)
