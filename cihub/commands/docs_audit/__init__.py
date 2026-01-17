"""Documentation lifecycle and metadata audit.

This package implements `cihub docs audit` which validates documentation
structure, lifecycle, and metadata according to project conventions.

Architecture (from DOC_AUTOMATION_AUDIT.md Part 12.J):
1. LIFECYCLE - Validate active/ ↔ STATUS.md sync, archive headers
2. ADR METADATA - Lint Status/Date/Superseded-by fields
3. HEADERS - Universal header enforcement for manual docs (Part 12.Q)
4. REFERENCES - Scan for broken docs/... path references
5. OUTPUT - Human, JSON, or GitHub summary format

Module structure:
- types: Data models (AuditFinding, AuditReport, ADRMetadata)
- lifecycle: Lifecycle validation (active/, archive/, STATUS.md)
- adr: ADR metadata linting
- headers: Universal header enforcement (Part 12.Q)
- references: Plain-text docs/ reference scanning
- output: Output formatters (human, JSON, GitHub summary)

Re-exports all public API from submodules for backward compatibility.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult
from cihub.utils.github_context import OutputContext
from cihub.utils.paths import project_root

# Import from submodules
from .adr import get_adr_files, parse_adr_metadata, validate_adr_metadata
from .consistency import (
    check_timestamp_freshness,
    find_duplicate_tasks,
    find_placeholders,
    parse_checklist_items,
    validate_consistency,
    validate_timestamps,
)
from .headers import (
    EXEMPT_DIRS,
    EXEMPT_FILES,
    GENERATED_DOCS,
    has_generated_banner,
    has_superseded_header,
    is_exempt_doc,
    parse_doc_header,
    validate_doc_headers,
    validate_header_value,
)
from .inventory import build_doc_inventory
from .lifecycle import (
    check_active_status_sync,
    check_archive_superseded_headers,
    check_master_plan_active_sync,
    get_active_docs,
    get_archive_docs,
    parse_master_plan_active_docs,
    parse_status_md_entries,
    validate_lifecycle,
)
from .output import (
    format_github_summary,
    format_human_output,
    format_json_output,
    group_findings_by_category,
    group_findings_by_file,
)
from .references import extract_doc_references, validate_doc_references
from .types import (
    ACTIVE_DOCS_DIR,
    ADR_DIR,
    ADR_REQUIRED_FIELDS,
    ADR_VALID_STATUSES,
    ARCHIVE_DOCS_DIR,
    STATUS_MD_PATH,
    ADRMetadata,
    AuditFinding,
    AuditReport,
    DocInventoryCategory,
    DocInventorySummary,
    FindingCategory,
    FindingSeverity,
)

__all__ = [
    # Main command
    "cmd_docs_audit",
    # Types
    "AuditFinding",
    "AuditReport",
    "ADRMetadata",
    "FindingSeverity",
    "FindingCategory",
    "DocInventoryCategory",
    "DocInventorySummary",
    # Constants
    "ACTIVE_DOCS_DIR",
    "ARCHIVE_DOCS_DIR",
    "STATUS_MD_PATH",
    "ADR_DIR",
    "ADR_REQUIRED_FIELDS",
    "ADR_VALID_STATUSES",
    # Lifecycle functions
    "get_active_docs",
    "get_archive_docs",
    "parse_master_plan_active_docs",
    "parse_status_md_entries",
    "check_active_status_sync",
    "check_archive_superseded_headers",
    "check_master_plan_active_sync",
    "validate_lifecycle",
    # ADR functions
    "get_adr_files",
    "parse_adr_metadata",
    "validate_adr_metadata",
    # Reference functions
    "extract_doc_references",
    "validate_doc_references",
    # Header functions (Part 12.Q)
    "GENERATED_DOCS",
    "EXEMPT_DIRS",
    "EXEMPT_FILES",
    "is_exempt_doc",
    "has_superseded_header",
    "has_generated_banner",
    "parse_doc_header",
    "validate_header_value",
    "validate_doc_headers",
    # Consistency functions (Part 13)
    "find_duplicate_tasks",
    "validate_timestamps",
    "check_timestamp_freshness",
    "find_placeholders",
    "parse_checklist_items",
    "validate_consistency",
    # Output functions
    "format_human_output",
    "format_json_output",
    "format_github_summary",
    "group_findings_by_category",
    "group_findings_by_file",
    # Inventory
    "build_doc_inventory",
]


def cmd_docs_audit(args: argparse.Namespace) -> CommandResult:
    """Run documentation audit.

    Validates documentation lifecycle, ADR metadata, headers, references, and consistency.

    Args:
        args: Parsed command line arguments
            --output-dir: Output directory for artifacts (default: .cihub/tool-outputs)
            --json: JSON output mode
            --github-summary: Write to GITHUB_STEP_SUMMARY
            --skip-headers: Skip Part 12.Q universal header validation
            --skip-references: Skip reference scanning (faster)
            --skip-consistency: Skip Part 13 consistency checks (faster)
            --inventory: Include doc inventory counts in JSON output

    Returns:
        CommandResult with audit findings
    """
    repo_root = project_root()
    skip_references = getattr(args, "skip_references", False)
    skip_consistency = getattr(args, "skip_consistency", False)
    include_inventory = getattr(args, "inventory", False)
    output_dir = getattr(args, "output_dir", None)
    github_summary = getattr(args, "github_summary", False)

    # Run all validations
    report = AuditReport()

    # 1. Lifecycle validation (active/ ↔ STATUS.md sync)
    lifecycle_findings, active_docs, status_entries, archive_docs = validate_lifecycle(repo_root)
    report.findings.extend(lifecycle_findings)
    report.active_docs = active_docs
    report.status_entries = status_entries
    report.archive_docs = archive_docs

    # 2. ADR metadata validation
    adr_files = get_adr_files(repo_root)
    report.adr_files = adr_files
    adr_findings = validate_adr_metadata(adr_files, repo_root)
    report.findings.extend(adr_findings)

    # 3. Universal header validation (Part 12.Q)
    skip_headers = getattr(args, "skip_headers", False)
    if not skip_headers:
        header_findings = validate_doc_headers(repo_root)
        report.findings.extend(header_findings)

    # 4. Reference validation (optional, can be slow)
    if not skip_references:
        ref_findings = validate_doc_references(repo_root)
        report.findings.extend(ref_findings)

    # 5. Consistency validation (Part 13: duplicates, timestamps, placeholders)
    if not skip_consistency:
        consistency_findings = validate_consistency(repo_root)
        report.findings.extend(consistency_findings)

    # 6. Inventory summary (optional)
    if include_inventory:
        report.inventory_summary = build_doc_inventory(repo_root)

    # Prepare output context for artifacts
    ctx = OutputContext.from_args(args)

    # Write tool outputs if output_dir specified
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Write JSON artifact
        json_path = out_path / "docs_audit.json"
        json_path.write_text(
            json.dumps(format_json_output(report), indent=2),
            encoding="utf-8",
        )

    # Write GitHub summary if requested
    if github_summary:
        summary_text = format_github_summary(report)
        ctx.write_summary(summary_text)

    # Determine exit code
    exit_code = EXIT_FAILURE if report.has_errors else EXIT_SUCCESS

    # Format summary
    if report.has_errors:
        summary = f"Documentation audit failed: {report.error_count} errors, {report.warning_count} warnings"
    elif report.warning_count > 0:
        summary = f"Documentation audit passed with {report.warning_count} warnings"
    else:
        summary = "Documentation audit passed: no issues found"

    # Convert findings to problems format
    problems = [f.to_dict() for f in report.findings]

    # Suggestions for errors
    suggestions = []
    if report.has_errors:
        suggestions.append(
            {
                "message": "Fix errors before merging",
                "code": "CIHUB-AUDIT-FIX",
            }
        )

    return CommandResult(
        exit_code=exit_code,
        summary=summary,
        problems=problems,
        suggestions=suggestions,
        data=report.to_dict(),
    )
