"""Output formatters for docs audit.

This module provides output formatting for the docs audit command:
1. Human-readable text (default)
2. JSON for scripts and CI (--json)
3. GitHub Actions step summary (--github-summary)

Following the pattern from cihub/commands/docs_stale/output.py.
"""

from __future__ import annotations

from typing import Any

from .types import AuditFinding, AuditReport, FindingCategory, FindingSeverity


def group_findings_by_category(
    findings: list[AuditFinding],
) -> dict[FindingCategory, list[AuditFinding]]:
    """Group findings by category.

    Args:
        findings: List of audit findings

    Returns:
        Dict mapping category to list of findings
    """
    grouped: dict[FindingCategory, list[AuditFinding]] = {}
    for finding in findings:
        if finding.category not in grouped:
            grouped[finding.category] = []
        grouped[finding.category].append(finding)
    return grouped


def group_findings_by_file(
    findings: list[AuditFinding],
) -> dict[str, list[AuditFinding]]:
    """Group findings by file.

    Args:
        findings: List of audit findings

    Returns:
        Dict mapping file path to list of findings
    """
    grouped: dict[str, list[AuditFinding]] = {}
    for finding in findings:
        key = finding.file or "(no file)"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(finding)
    return grouped


def format_human_output(report: AuditReport) -> str:
    """Format report as human-readable text.

    Provides a clear summary of findings suitable for terminal output.
    Groups findings by category for easy navigation.

    Args:
        report: The complete audit report

    Returns:
        Human-readable text output
    """
    lines: list[str] = []

    lines.append("Documentation Audit Report")
    lines.append("=" * 60)
    lines.append("")

    # Stats summary
    lines.append("Summary:")
    lines.append(f"  Active docs: {len(report.active_docs)}")
    lines.append(f"  Archived docs: {len(report.archive_docs)}")
    lines.append(f"  ADR files: {len(report.adr_files)}")
    lines.append(f"  Total findings: {len(report.findings)}")
    lines.append(f"    Errors: {report.error_count}")
    lines.append(f"    Warnings: {report.warning_count}")
    lines.append("")

    if not report.findings:
        lines.append("No issues found.")
        return "\n".join(lines)

    # Group by category for readability
    by_category = group_findings_by_category(report.findings)

    category_labels = {
        FindingCategory.LIFECYCLE: "Lifecycle Issues",
        FindingCategory.SYNC: "Sync Issues (active/ ↔ STATUS.md)",
        FindingCategory.ADR_METADATA: "ADR Metadata Issues",
        FindingCategory.HEADER: "Header Issues",
        FindingCategory.REFERENCE: "Reference Issues",
        FindingCategory.GUIDE_COMMAND: "Guide Command Issues",
    }

    for category, category_findings in sorted(by_category.items(), key=lambda x: x[0].value):
        label = category_labels.get(category, category.value)
        lines.append(f"{label}:")

        for finding in sorted(category_findings, key=lambda f: (f.file or "", f.line or 0)):
            severity_icon = "❌" if finding.severity == FindingSeverity.ERROR else "⚠️"
            location = ""
            if finding.file:
                location = f" [{finding.file}"
                if finding.line:
                    location += f":{finding.line}"
                location += "]"

            lines.append(f"  {severity_icon} {finding.message}{location}")
            if finding.suggestion:
                lines.append(f"      → {finding.suggestion}")

        lines.append("")

    return "\n".join(lines)


def format_json_output(report: AuditReport) -> dict[str, Any]:
    """Format report as JSON-serializable dict.

    Uses the AuditReport.to_dict() method for consistent schema.

    Args:
        report: The complete audit report

    Returns:
        JSON-serializable dict
    """
    return report.to_dict()


def format_github_summary(report: AuditReport) -> str:
    """Format report as GitHub Actions step summary.

    Creates a concise markdown summary suitable for GITHUB_STEP_SUMMARY.

    Args:
        report: The complete audit report

    Returns:
        Markdown summary for GitHub Actions
    """
    lines: list[str] = []

    lines.append("## Documentation Audit")
    lines.append("")

    # Status badge
    if report.has_errors:
        lines.append("**Status:** ❌ Failed")
    elif report.warning_count > 0:
        lines.append("**Status:** ⚠️ Passed with warnings")
    else:
        lines.append("**Status:** ✅ Passed")
    lines.append("")

    # Stats
    lines.append("### Summary")
    lines.append("")
    lines.append(f"- Active docs: **{len(report.active_docs)}**")
    lines.append(f"- Archived docs: **{len(report.archive_docs)}**")
    lines.append(f"- ADR files: **{len(report.adr_files)}**")
    lines.append(f"- Errors: **{report.error_count}**")
    lines.append(f"- Warnings: **{report.warning_count}**")
    lines.append("")

    if report.findings:
        lines.append("### Findings")
        lines.append("")

        # Show up to 15 findings
        for finding in report.findings[:15]:
            severity_icon = "❌" if finding.severity == FindingSeverity.ERROR else "⚠️"
            file_info = f" (`{finding.file}`)" if finding.file else ""
            lines.append(f"- {severity_icon} {finding.message}{file_info}")

        if len(report.findings) > 15:
            lines.append(f"- ... and {len(report.findings) - 15} more")

    return "\n".join(lines)
