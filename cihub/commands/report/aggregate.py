"""Report aggregation command logic."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import aggregate_from_dispatch, aggregate_from_reports_dir
from cihub.types import CommandResult
from cihub.utils.debug import emit_debug_context
from cihub.utils.env import get_github_token
from cihub.utils.github_context import GitHubContext

from .helpers import _resolve_include_details, _resolve_write_summary


def _emit_aggregate_debug_context(
    *,
    args: argparse.Namespace,
    result,
    write_summary: bool,
    include_details: bool,
    summary_file: Path | None,
    details_file: Path | None,
    hub_run_id: str,
    hub_event: str,
    total_repos: int,
    reports_dir: Path | None,
    token_env: str | None = None,
    token_source: str | None = None,
) -> None:
    report_path = str(result.report_path) if result and getattr(result, "report_path", None) else None
    summary_path = str(result.summary_path) if result and getattr(result, "summary_path", None) else None
    details_path = str(result.details_path) if result and getattr(result, "details_path", None) else None
    entries = [
        ("mode", "reports_dir" if reports_dir else "dispatch"),
        ("reports_dir", str(reports_dir) if reports_dir else None),
        ("dispatch_dir", str(args.dispatch_dir) if not reports_dir else None),
        ("output_file", str(args.output)),
        ("defaults_file", str(args.defaults_file)),
        ("summary_file", str(summary_file) if summary_file else None),
        ("details_file", str(details_file) if details_file else None),
        ("write_github_summary", str(write_summary)),
        ("include_details", str(include_details)),
        ("total_repos", str(total_repos)),
        ("hub_run_id", hub_run_id),
        ("hub_event", hub_event),
        ("strict", str(bool(args.strict))),
        ("timeout_sec", str(int(args.timeout)) if not reports_dir else None),
        ("token_env", token_env if not reports_dir else None),
        ("token_source", token_source if not reports_dir else None),
        ("report_path", report_path),
        ("summary_path", summary_path),
        ("details_path", details_path),
        (
            "dispatched_repos",
            str(getattr(result, "dispatched_repos", "")) if result and hasattr(result, "dispatched_repos") else None,
        ),
        (
            "passed_count",
            str(getattr(result, "passed_count", "")) if result and hasattr(result, "passed_count") else None,
        ),
        (
            "failed_count",
            str(getattr(result, "failed_count", "")) if result and hasattr(result, "failed_count") else None,
        ),
        (
            "threshold_exceeded",
            (
                str(getattr(result, "threshold_exceeded", ""))
                if result and hasattr(result, "threshold_exceeded")
                else None
            ),
        ),
        (
            "success",
            str(bool(getattr(result, "success", False))) if result and hasattr(result, "success") else None,
        ),
    ]
    emit_debug_context("report aggregate", entries)


def _aggregate_report(args: argparse.Namespace) -> CommandResult:
    """Aggregate reports from dispatch metadata or reports directory."""
    write_summary = _resolve_write_summary(getattr(args, "write_github_summary", None))
    include_details = _resolve_include_details(getattr(args, "include_details", None))
    summary_file = Path(args.summary_file) if args.summary_file else None
    details_file = Path(args.details_output) if args.details_output else None
    if summary_file is None and write_summary:
        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env:
            summary_file = Path(summary_env)

    ctx = GitHubContext.from_env()
    total_repos = args.total_repos or int(os.environ.get("TOTAL_REPOS", 0) or 0)
    hub_run_id = args.hub_run_id or os.environ.get("HUB_RUN_ID", ctx.run_id or "")
    hub_event = args.hub_event or os.environ.get("HUB_EVENT", ctx.event_name or "")

    reports_dir = getattr(args, "reports_dir", None)
    if reports_dir:
        result = aggregate_from_reports_dir(
            reports_dir=Path(reports_dir),
            output_file=Path(args.output),
            defaults_file=Path(args.defaults_file),
            hub_run_id=hub_run_id,
            hub_event=hub_event,
            total_repos=total_repos,
            summary_file=summary_file,
            details_file=details_file,
            include_details=include_details,
            strict=bool(args.strict),
        )
        _emit_aggregate_debug_context(
            args=args,
            result=result,
            write_summary=write_summary,
            include_details=include_details,
            summary_file=summary_file,
            details_file=details_file,
            hub_run_id=hub_run_id,
            hub_event=hub_event,
            total_repos=total_repos,
            reports_dir=Path(reports_dir),
        )
        exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE
        summary = "Aggregation complete" if result.success else "Aggregation failed"
        files_generated = []
        if result.report_path:
            files_generated.append(str(result.report_path))
        if result.summary_path:
            files_generated.append(str(result.summary_path))
        if result.details_path:
            files_generated.append(str(result.details_path))
        return CommandResult(
            exit_code=exit_code,
            summary=summary,
            artifacts={
                "report": str(result.report_path) if result.report_path else "",
                "summary": str(result.summary_path) if result.summary_path else "",
                "details": str(result.details_path) if result.details_path else "",
            },
            files_generated=files_generated or [],
        )

    # Get token using standardized priority: GH_TOKEN -> GITHUB_TOKEN -> HUB_DISPATCH_TOKEN
    token, token_source = get_github_token(
        explicit_token=args.token,
        token_env=args.token_env,
    )
    if not token:
        message = "Missing token (set GH_TOKEN, GITHUB_TOKEN, or HUB_DISPATCH_TOKEN)"
        _emit_aggregate_debug_context(
            args=args,
            result=None,
            write_summary=write_summary,
            include_details=include_details,
            summary_file=summary_file,
            details_file=details_file,
            hub_run_id=hub_run_id,
            hub_event=hub_event,
            total_repos=total_repos,
            reports_dir=None,
            token_env=args.token_env,
            token_source=token_source,
        )
        return CommandResult(exit_code=EXIT_FAILURE, summary=message)

    result = aggregate_from_dispatch(
        dispatch_dir=Path(args.dispatch_dir),
        output_file=Path(args.output),
        defaults_file=Path(args.defaults_file),
        token=token,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
        summary_file=summary_file,
        details_file=details_file,
        include_details=include_details,
        strict=bool(args.strict),
        timeout_sec=int(args.timeout),
    )
    _emit_aggregate_debug_context(
        args=args,
        result=result,
        write_summary=write_summary,
        include_details=include_details,
        summary_file=summary_file,
        details_file=details_file,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
        reports_dir=None,
        token_env=args.token_env,
        token_source=token_source,
    )
    exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE
    summary = "Aggregation complete" if result.success else "Aggregation failed"

    files_generated = []
    if result.report_path:
        files_generated.append(str(result.report_path))
    if result.summary_path:
        files_generated.append(str(result.summary_path))
    if result.details_path:
        files_generated.append(str(result.details_path))

    return CommandResult(
        exit_code=exit_code,
        summary=summary,
        artifacts={
            "report": str(result.report_path) if result.report_path else "",
            "summary": str(result.summary_path) if result.summary_path else "",
            "details": str(result.details_path) if result.details_path else "",
        },
        files_generated=files_generated or [],
    )
