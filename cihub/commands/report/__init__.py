"""Report build and summary commands package.

This package splits the report module into logical submodules while
maintaining backward compatibility by re-exporting all public symbols.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.ci_config import load_ci_config
from cihub.ci_report import (
    build_java_report,
    build_python_report,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.reporting import render_summary_from_path
from cihub.types import CommandResult
from cihub.utils import (
    _detect_java_project_type,
    _get_repo_name,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.utils.env import _parse_env_bool
from cihub.utils.progress import _bar

# Import submodule functions
from .aggregate import _aggregate_report
from .build import _build_report
from .dashboard import (
    _detect_language,
    _generate_dashboard_summary,
    _generate_html_dashboard,
    _get_report_status,
    _load_dashboard_reports,
)
from .helpers import (
    _append_summary,
    _build_context,
    _coerce_bool,
    _load_tool_outputs,
    _resolve_include_details,
    _resolve_summary_path,
    _resolve_write_summary,
    _tool_enabled,
)
from .outputs import _report_outputs
from .summary import (
    _kyverno_summary,
    _orchestrator_load_summary,
    _orchestrator_trigger_summary,
    _security_overall_summary,
    _security_repo_summary,
    _security_zap_summary,
    _smoke_overall_summary,
    _smoke_repo_summary,
)
from .validate import _validate_report


def cmd_report(args: argparse.Namespace) -> CommandResult:
    """Main router for report subcommands."""
    if args.subcommand == "aggregate":
        return _aggregate_report(args)

    if args.subcommand == "outputs":
        return _report_outputs(args)

    if args.subcommand == "summary":
        report_path = Path(args.report)
        summary_text = render_summary_from_path(report_path)
        write_summary = _resolve_write_summary(args.write_github_summary)
        output_path = Path(args.output) if args.output else None
        if output_path:
            output_path.write_text(summary_text, encoding="utf-8")
        github_summary = _resolve_summary_path(None, write_summary)
        if github_summary:
            github_summary.write_text(summary_text, encoding="utf-8")
        # Return CommandResult with summary text for display
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Summary rendered",
            artifacts={"summary": str(output_path) if output_path else ""},
            data={"raw_output": summary_text} if write_summary and not output_path else None,
        )

    if args.subcommand == "security-summary":
        mode = args.mode
        if mode == "repo":
            summary_text = _security_repo_summary(args)
        elif mode == "zap":
            summary_text = _security_zap_summary(args)
        else:
            summary_text = _security_overall_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Security summary generated ({mode} mode)",
            data={"raw_output": summary_text} if not write_summary else None,
        )

    if args.subcommand == "smoke-summary":
        mode = args.mode
        if mode == "repo":
            summary_text = _smoke_repo_summary(args)
        else:
            summary_text = _smoke_overall_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Smoke summary generated ({mode} mode)",
            data={"raw_output": summary_text} if not write_summary else None,
        )

    if args.subcommand == "kyverno-summary":
        summary_text = _kyverno_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Kyverno summary generated",
            data={"raw_output": summary_text} if not write_summary else None,
        )

    if args.subcommand == "orchestrator-summary":
        if args.mode == "load-config":
            summary_text = _orchestrator_load_summary(args)
        else:
            summary_text = _orchestrator_trigger_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Orchestrator summary generated ({args.mode} mode)",
            data={"raw_output": summary_text} if not write_summary else None,
        )

    if args.subcommand == "validate":
        return _validate_report(args)

    if args.subcommand == "dashboard":
        reports_dir = Path(args.reports_dir)
        output_path = Path(args.output)
        output_format = getattr(args, "format", "html")
        schema_mode = getattr(args, "schema_mode", "warn")

        # Load reports
        reports, skipped, warnings = _load_dashboard_reports(reports_dir, schema_mode)

        # Generate summary
        dashboard_summary = _generate_dashboard_summary(reports)

        # Output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_format == "json":
            output_path.write_text(json.dumps(dashboard_summary, indent=2), encoding="utf-8")
        else:
            html_content = _generate_html_dashboard(dashboard_summary)
            output_path.write_text(html_content, encoding="utf-8")

        # Exit with error if strict mode and reports were skipped
        exit_code = EXIT_FAILURE if (schema_mode == "strict" and skipped > 0) else EXIT_SUCCESS

        # Build summary message
        summary_parts = [f"Generated {output_format} dashboard: {output_path}"]
        summary_parts.append(f"Loaded {len(reports)} reports")
        if skipped > 0:
            summary_parts.append(f"Skipped {skipped} reports with non-2.0 schema")

        return CommandResult(
            exit_code=exit_code,
            summary="\n".join(summary_parts),
            artifacts={"dashboard": str(output_path)},
            problems=[{"severity": "warning", "message": w} for w in warnings],
            data={"reports_loaded": len(reports), "reports_skipped": skipped},
        )

    if args.subcommand == "build":
        return _build_report(args)

    return CommandResult(
        exit_code=EXIT_USAGE,
        summary=f"Unknown report subcommand: {args.subcommand}",
    )


# ============================================================================
# Public API - Re-exports for backward compatibility
# ============================================================================

__all__ = [
    # Main command
    "cmd_report",
    # Helpers from helpers.py (used by tests)
    "_append_summary",
    "_build_context",
    "_coerce_bool",
    "_detect_java_project_type",
    "_get_repo_name",
    "_load_tool_outputs",
    "_resolve_include_details",
    "_resolve_summary_path",
    "_resolve_write_summary",
    "_tool_enabled",
    # Helpers from dashboard.py (used by tests)
    "_detect_language",
    "_generate_dashboard_summary",
    "_generate_html_dashboard",
    "_get_report_status",
    "_load_dashboard_reports",
    # Helpers from summary.py (used by tests)
    "_kyverno_summary",
    "_orchestrator_load_summary",
    "_orchestrator_trigger_summary",
    "_security_overall_summary",
    "_security_repo_summary",
    "_security_zap_summary",
    "_smoke_overall_summary",
    "_smoke_repo_summary",
    # Helpers from validate.py
    "_validate_report",
    # Re-exports from utils (used by tests)
    "_parse_env_bool",
    "_bar",
    # Re-exports for backward compatibility (used by mutant tests)
    "get_git_remote",
    "get_git_branch",
    "parse_repo_from_remote",
    "load_ci_config",
    "build_python_report",
    "build_java_report",
]
