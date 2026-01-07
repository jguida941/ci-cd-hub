"""Output formatters for docs stale detection.

This module provides three output modes:
1. Human-readable text (default)
2. JSON for scripts and CI (--json)
3. AI-consumable markdown prompt pack (--ai)

The AI output follows Part 12.D guidelines from DOC_AUTOMATION_AUDIT.md:
- Per-file packets with context
- Explicit constraints (no generated docs, no ADR edits)
- CLI terminology
"""

from __future__ import annotations

from typing import Any

from .comparison import group_stale_by_file
from .types import StaleReport


def format_human_output(report: StaleReport) -> str:
    """Format report as human-readable text.

    Provides a clear summary of findings suitable for terminal output.
    Groups stale references by file for easy navigation.

    Args:
        report: The complete stale report

    Returns:
        Human-readable text output
    """
    lines: list[str] = []

    lines.append("Stale Documentation Report")
    lines.append("=" * 60)
    lines.append(f"Git range: {report.git_range}")
    lines.append("")

    # Stats summary
    lines.append("Summary:")
    lines.append(f"  Removed symbols: {len(report.removed_symbols)}")
    lines.append(f"  Renamed symbols: {len(report.renamed_symbols)}")
    lines.append(f"  Deleted files: {len(report.deleted_files)}")
    lines.append(f"  Stale references: {len(report.stale_references)}")
    lines.append("")

    if not report.stale_references:
        lines.append("No stale references found.")
        return "\n".join(lines)

    # Group by file for readability
    by_file = group_stale_by_file(report.stale_references)

    for doc_file, refs in sorted(by_file.items()):
        lines.append(f"{doc_file}:")
        for ref in sorted(refs, key=lambda r: r.doc_line):
            lines.append(f"  Line {ref.doc_line}: `{ref.reference}` ({ref.reason})")
            lines.append(f"    → {ref.suggestion}")
        lines.append("")

    return "\n".join(lines)


def format_json_output(report: StaleReport) -> dict[str, Any]:
    """Format report as JSON-serializable dict.

    Uses the StaleReport.to_dict() method for consistent schema.

    Args:
        report: The complete stale report

    Returns:
        JSON-serializable dict matching the schema from Part 11
    """
    return report.to_dict()


def format_ai_output(report: StaleReport) -> str:
    """Format report as AI-consumable markdown prompt pack.

    Follows Part 12.D guidelines:
    - Per-file packets with context
    - Explicit constraints (no generated docs, no ADR edits)
    - CLI terminology (never internal nicknames)
    - Bounded output for stable prompts

    This output is designed to be piped to a file and fed to Claude/GPT
    externally. NO network calls are made by this command.

    Args:
        report: The complete stale report

    Returns:
        Markdown prompt pack string
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

    if report.deleted_files:
        lines.append("### Deleted Files")
        lines.append("")
        for f in sorted(report.deleted_files):
            lines.append(f"- `{f}`")
        lines.append("")

    if not report.stale_references:
        lines.append("No stale references found.")
        return "\n".join(lines)

    lines.append("## Files Requiring Updates")
    lines.append("")

    # Group by file for per-file packets
    by_file = group_stale_by_file(report.stale_references)

    for doc_file, refs in sorted(by_file.items()):
        # Skip generated docs and ADRs per Part 12.D constraints
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


def format_github_summary(report: StaleReport, since: str) -> str:
    """Format report as GitHub Actions step summary.

    Creates a concise markdown summary suitable for GITHUB_STEP_SUMMARY.

    Args:
        report: The complete stale report
        since: The git reference used

    Returns:
        Markdown summary for GitHub Actions
    """
    lines: list[str] = []

    lines.append("## Documentation Staleness Check")
    lines.append("")
    lines.append(f"Git range: `{since}`")
    lines.append("")
    lines.append(f"- Removed symbols: **{len(report.removed_symbols)}**")
    lines.append(f"- Renamed symbols: **{len(report.renamed_symbols)}**")
    lines.append(f"- Stale references: **{len(report.stale_references)}**")
    lines.append("")

    if report.stale_references:
        lines.append("### Stale References Found")
        lines.append("")
        # Limit to first 10 for concise summary
        for ref in report.stale_references[:10]:
            lines.append(f"- `{ref.doc_file}:{ref.doc_line}`: `{ref.reference}` ({ref.reason})")
        if len(report.stale_references) > 10:
            lines.append(f"- ... and {len(report.stale_references) - 10} more")
    else:
        lines.append("No stale references found")

    return "\n".join(lines)
