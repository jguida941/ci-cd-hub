"""Generate triage bundle outputs from existing report artifacts.

This is the main command handler for `cihub triage`. The implementation
has been modularized into submodules:
- types.py: Constants, severity maps, filter helpers
- github.py: GitHub API client
- artifacts.py: Artifact finding utilities
- log_parser.py: Log parsing for failures
- remote.py: Remote bundle generation
- verification.py: Tool verification
- output.py: Output formatting
- watch.py: Watch mode
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

# Import from submodules
from cihub.commands.triage.artifacts import find_report_in_artifacts as _find_report_in_artifacts
from cihub.commands.triage.github import download_artifacts as _download_artifacts
from cihub.commands.triage.github import get_latest_failed_run as _get_latest_failed_run
from cihub.commands.triage.github import list_runs as _list_runs
from cihub.commands.triage.output import format_flaky_output as _format_flaky_output
from cihub.commands.triage.output import format_gate_history_output as _format_gate_history_output
from cihub.commands.triage.remote import generate_multi_report_triage as _generate_multi_report_triage
from cihub.commands.triage.remote import generate_remote_triage_bundle as _generate_remote_triage_bundle
from cihub.commands.triage.types import build_meta as _build_meta
from cihub.commands.triage.types import filter_bundle as _filter_bundle
from cihub.commands.triage.verification import format_verify_tools_output as _format_verify_tools_output
from cihub.commands.triage.verification import verify_tools_from_report as _verify_tools_from_report
from cihub.commands.triage.watch import watch_for_failures as _watch_for_failures
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.triage_service import (
    detect_flaky_patterns,
    detect_gate_changes,
    generate_triage_bundle,
    write_triage_bundle,
)
from cihub.types import CommandResult


def _maybe_enhance(
    args: argparse.Namespace,
    result: CommandResult,
    *,
    mode: str = "analyze",
) -> CommandResult:
    if getattr(args, "ai", False):
        from cihub.ai import enhance_result

        return enhance_result(result, mode=mode)
    return result


def cmd_triage(args: argparse.Namespace) -> CommandResult:
    """Main entry point for the triage command."""
    output_dir = Path(args.output_dir or ".cihub")
    run_id = getattr(args, "run", None)
    artifacts_dir = getattr(args, "artifacts_dir", None)
    repo = getattr(args, "repo", None)

    # Validate repo format (owner/repo) to prevent injection
    if repo is not None:
        repo_pattern = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9]*/[a-zA-Z0-9][-a-zA-Z0-9_.]*$")
        if not repo_pattern.match(repo):
            return _maybe_enhance(
                args,
                CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary=f"Invalid repo format: {repo}",
                    problems=[
                        {
                            "severity": "error",
                            "message": f"Repo must be in 'owner/repo' format (got: {repo})",
                            "code": "CIHUB-TRIAGE-INVALID-REPO",
                        }
                    ],
                    data={"repo": repo},
                ),
            )

    multi_mode = getattr(args, "multi", False)
    reports_dir = getattr(args, "reports_dir", None)
    detect_flaky = getattr(args, "detect_flaky", False)
    gate_history = getattr(args, "gate_history", False)
    workflow_filter = getattr(args, "workflow", None)
    branch_filter = getattr(args, "branch", None)
    aggregate_mode = getattr(args, "aggregate", False)
    per_repo_mode = getattr(args, "per_repo", False)
    latest_mode = getattr(args, "latest", False)
    watch_mode = getattr(args, "watch", False)
    watch_interval = getattr(args, "interval", 30)
    min_severity = getattr(args, "min_severity", None)
    category_filter = getattr(args, "category", None)

    # Handle --watch mode (background daemon)
    if watch_mode:
        return _maybe_enhance(
            args,
            _watch_for_failures(
                args=args,
                interval=watch_interval,
                repo=repo,
                workflow=workflow_filter,
                branch=branch_filter,
            ),
        )

    run_note = None

    # Handle --latest mode (auto-find most recent failed run)
    if latest_mode and not run_id:
        run_id = _get_latest_failed_run(
            repo=repo,
            workflow=workflow_filter,
            branch=branch_filter,
        )
        if not run_id:
            filter_parts = []
            if workflow_filter:
                filter_parts.append(f"workflow={workflow_filter}")
            if branch_filter:
                filter_parts.append(f"branch={branch_filter}")
            filter_desc = f" ({', '.join(filter_parts)})" if filter_parts else ""
            return _maybe_enhance(
                args,
                CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary=f"No failed runs found{filter_desc}",
                    problems=[
                        {
                            "severity": "info",
                            "message": "No recent failed workflow runs to triage",
                            "code": "CIHUB-TRIAGE-NO-FAILURES",
                        }
                    ],
                ),
            )
        run_note = f"Auto-selected latest failed run: {run_id}"

    # Handle --gate-history mode (standalone analysis)
    if gate_history:
        history_path = output_dir / "history.jsonl"
        gate_result = detect_gate_changes(history_path)

        return _maybe_enhance(
            args,
            CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=gate_result["summary"],
                data={
                    **gate_result,
                    "raw_output": "\n".join(_format_gate_history_output(gate_result)),
                },
            ),
        )

    # Handle --detect-flaky mode (standalone analysis)
    if detect_flaky:
        history_path = output_dir / "history.jsonl"
        flaky_result = detect_flaky_patterns(history_path)

        return _maybe_enhance(
            args,
            CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=(
                    "Flaky analysis: "
                    f"score={flaky_result['flakiness_score']}%, "
                    f"suspected={flaky_result['suspected_flaky']}"
                ),
                data={
                    **flaky_result,
                    "raw_output": "\n".join(_format_flaky_output(flaky_result)),
                },
            ),
        )

    # Handle --verify-tools mode (standalone analysis)
    verify_tools = getattr(args, "verify_tools", False)
    if verify_tools:
        return _maybe_enhance(
            args,
            _handle_verify_tools(
                args=args,
                output_dir=output_dir,
                run_id=run_id,
                latest_mode=latest_mode,
                repo=repo,
                workflow_filter=workflow_filter,
                branch_filter=branch_filter,
            ),
        )

    try:
        # Multi-report mode
        if multi_mode:
            return _maybe_enhance(args, _handle_multi_mode(reports_dir, output_dir))

        # Handle --workflow/--branch filters without explicit --run
        if (workflow_filter or branch_filter) and not run_id:
            runs = _list_runs(repo, workflow=workflow_filter, branch=branch_filter, limit=10)
            if not runs:
                run_filter_parts: list[str] = []
                if workflow_filter:
                    run_filter_parts.append(f"workflow={workflow_filter}")
                if branch_filter:
                    run_filter_parts.append(f"branch={branch_filter}")
                raise ValueError(f"No runs found matching: {', '.join(run_filter_parts)}")

            # Use the most recent run
            run_id = str(runs[0]["databaseId"])
            run_note = f"Using most recent run: {run_id} ({runs[0].get('name', 'unknown')})"
            if len(runs) > 1:
                run_note += f" (Found {len(runs)} matching runs, use --run to specify)"

        if run_id:
            # Remote run analysis mode (with persistent artifacts)
            result = _generate_remote_triage_bundle(
                run_id,
                repo,
                output_dir,
                force_aggregate=aggregate_mode,
                force_per_repo=per_repo_mode,
            )

            # Check if multi-report mode was triggered (returns tuple)
            if isinstance(result, tuple):
                artifacts_out, result_data = result
                passed = result_data["passed_count"]
                failed = result_data["failed_count"]

                return _maybe_enhance(
                    args,
                    CommandResult(
                        exit_code=EXIT_SUCCESS,
                        summary=f"Run {run_id}: {result_data['repo_count']} repos, {passed} passed, {failed} failed",
                        artifacts={k: str(v) for k, v in artifacts_out.items()},
                        files_generated=[
                            str(artifacts_out.get("multi_triage", "")),
                            str(artifacts_out.get("multi_markdown", "")),
                        ],
                        data=(
                            {
                                **result_data,
                                "run_note": run_note,
                            }
                            if run_note
                            else result_data
                        ),
                    ),
                )

            # Single report or log-fallback mode (returns TriageBundle)
            bundle = result
            # Apply filters if specified
            bundle = _filter_bundle(bundle, min_severity, category_filter)
            run_dir = output_dir / "runs" / run_id
            artifacts = write_triage_bundle(bundle, run_dir)
        elif artifacts_dir:
            # Offline artifacts mode
            artifacts_path = Path(artifacts_dir)
            bundle = generate_triage_bundle(
                output_dir=artifacts_path,
                meta=_build_meta(args),
            )
            # Apply filters if specified
            bundle = _filter_bundle(bundle, min_severity, category_filter)
            artifacts = write_triage_bundle(bundle, output_dir)
        else:
            # Local mode (existing behavior)
            report_path = Path(args.report) if args.report else None
            summary_path = Path(args.summary) if args.summary else None
            bundle = generate_triage_bundle(
                output_dir=output_dir,
                report_path=report_path,
                summary_path=summary_path,
                meta=_build_meta(args),
            )
            # Apply filters if specified
            bundle = _filter_bundle(bundle, min_severity, category_filter)
            artifacts = write_triage_bundle(bundle, output_dir)
    except Exception as exc:  # noqa: BLE001 - surface error in CLI
        return _maybe_enhance(
            args,
            CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Failed to generate triage bundle: {exc}",
                problems=[
                    {
                        "severity": "error",
                        "message": str(exc),
                        "code": "CIHUB-TRIAGE-ERROR",
                    }
                ],
            ),
        )

    # Build summary with filter info
    failure_count = bundle.triage.get("summary", {}).get("failure_count", 0)
    filters_applied = bundle.triage.get("filters_applied")
    if filters_applied:
        original_count = filters_applied.get("original_failure_count", 0)
        applied_filter_parts: list[str] = []
        if filters_applied.get("min_severity"):
            applied_filter_parts.append(f"severity>={filters_applied['min_severity']}")
        if filters_applied.get("category"):
            applied_filter_parts.append(f"category={filters_applied['category']}")
        filter_str = ", ".join(applied_filter_parts)
        summary = f"Triage bundle generated ({failure_count}/{original_count} failures, filtered by {filter_str})"
    else:
        summary = f"Triage bundle generated ({failure_count} failures)"

    # Extract failures as problems for visibility
    problems: list[dict[str, Any]] = []
    for failure in bundle.priority.get("failures", []):
        problems.append(
            {
                "severity": failure.get("severity", "error"),
                "message": failure.get("message", "Unknown failure"),
                "code": failure.get("id", "CIHUB-TRIAGE-FAILURE"),
                "category": failure.get("category", "unknown"),
                "tool": failure.get("tool", "unknown"),
            }
        )

    # Run tool verification and add to output
    tool_verification: dict[str, Any] | None = None
    triage_report_path = bundle.triage.get("paths", {}).get("report_path")
    if triage_report_path:
        triage_report_file = Path(triage_report_path)
        if triage_report_file.exists():
            tool_verification = _verify_tools_from_report(
                triage_report_file,
                triage_report_file.parent,
            )
            # Add tool verification issues to problems
            for item in tool_verification.get("drift", []):
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Tool '{item['tool']}': {item['message']}",
                        "code": "CIHUB-VERIFY-DRIFT",
                        "category": "tool",
                        "tool": item["tool"],
                    }
                )
            for item in tool_verification.get("no_proof", []):
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Tool '{item['tool']}': {item['message']}",
                        "code": "CIHUB-VERIFY-NO-PROOF",
                        "category": "tool",
                        "tool": item["tool"],
                    }
                )

    # Generate suggestions based on failures
    suggestions: list[dict[str, Any]] = []
    if problems:
        suggestions.append(
            {
                "message": f"Run 'cat {artifacts['priority']}' for detailed failure info",
                "code": "CIHUB-TRIAGE-VIEW-PRIORITY",
            }
        )
        suggestions.append(
            {
                "message": f"Run 'cat {artifacts['markdown']}' for human-readable summary",
                "code": "CIHUB-TRIAGE-VIEW-MARKDOWN",
            }
        )
    if tool_verification and (tool_verification.get("drift") or tool_verification.get("no_proof")):
        suggestions.append(
            {
                "message": "Run 'cihub triage --verify-tools' for detailed tool verification",
                "code": "CIHUB-TRIAGE-VERIFY-TOOLS",
            }
        )

    return _maybe_enhance(
        args,
        CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=summary,
            problems=problems,
            suggestions=suggestions,
            artifacts={key: str(path) for key, path in artifacts.items()},
            files_generated=[
                str(artifacts["triage"]),
                str(artifacts["priority"]),
                str(artifacts["markdown"]),
            ],
            data={
                "schema_version": bundle.triage.get("schema_version", ""),
                "failure_count": failure_count,
                "filters_applied": filters_applied,
                "tool_verification": tool_verification,
                "key_values": {
                    "triage": str(artifacts["triage"]),
                    "priority": str(artifacts["priority"]),
                    "prompt_pack": str(artifacts["markdown"]),
                    "history": str(artifacts["history"]),
                },
                **({"run_note": run_note} if run_note else {}),
            },
        ),
    )


def _handle_verify_tools(
    args: argparse.Namespace,
    output_dir: Path,
    run_id: str | None,
    latest_mode: bool,
    repo: str | None,
    workflow_filter: str | None,
    branch_filter: str | None,
) -> CommandResult:
    """Handle --verify-tools mode (standalone analysis)."""
    # Find report.json (from args, latest run, or default location)
    report_path: Path | None = None
    reports_dir_path: Path | None = None

    if args.report:
        report_path = Path(args.report)
        reports_dir_path = report_path.parent
    elif run_id or latest_mode:
        # Use remote run artifacts
        effective_run_id = run_id
        if latest_mode and not run_id:
            effective_run_id = _get_latest_failed_run(
                repo=repo,
                workflow=workflow_filter,
                branch=branch_filter,
            )
        if effective_run_id:
            run_dir = output_dir / "runs" / effective_run_id
            artifacts_dir = run_dir / "artifacts"
            # Download artifacts if not already present
            if not artifacts_dir.exists() or not list(artifacts_dir.iterdir()):
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                _download_artifacts(effective_run_id, repo, artifacts_dir)
            report_path = _find_report_in_artifacts(artifacts_dir)
            reports_dir_path = report_path.parent if report_path else None
    else:
        # Default: look in output_dir
        report_path = output_dir / "report.json"
        reports_dir_path = output_dir

    if not report_path or not report_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No report.json found for tool verification",
            problems=[
                {
                    "severity": "error",
                    "message": "Provide --report path or use --run/--latest to fetch artifacts",
                    "code": "CIHUB-VERIFY-NO-REPORT",
                }
            ],
        )

    verify_result = _verify_tools_from_report(report_path, reports_dir_path)

    # Build problems from verification issues
    verify_problems: list[dict[str, Any]] = []
    for item in verify_result.get("drift", []):
        verify_problems.append(
            {
                "severity": "warning",
                "message": f"{item['tool']}: {item['message']}",
                "code": "CIHUB-VERIFY-DRIFT",
                "category": "tool",
                "tool": item["tool"],
            }
        )
    for item in verify_result.get("no_proof", []):
        verify_problems.append(
            {
                "severity": "warning",
                "message": f"{item['tool']}: {item['message']}",
                "code": "CIHUB-VERIFY-NO-PROOF",
                "category": "tool",
                "tool": item["tool"],
            }
        )
    for item in verify_result.get("failures", []):
        verify_problems.append(
            {
                "severity": "error",
                "message": f"{item['tool']}: {item['message']}",
                "code": "CIHUB-VERIFY-FAILED",
                "category": "tool",
                "tool": item["tool"],
            }
        )

    # Build suggestions
    verify_suggestions: list[dict[str, Any]] = []
    if verify_result.get("drift"):
        verify_suggestions.append(
            {
                "message": "Check workflow config - ensure tools are enabled in workflow steps",
                "code": "CIHUB-VERIFY-CHECK-WORKFLOW",
            }
        )
    if verify_result.get("no_proof"):
        verify_suggestions.append(
            {
                "message": "Tools may have run but not produced expected output files",
                "code": "CIHUB-VERIFY-CHECK-OUTPUTS",
            }
        )

    exit_code = EXIT_SUCCESS if verify_result["verified"] else EXIT_FAILURE

    return CommandResult(
        exit_code=exit_code,
        summary=verify_result["summary"],
        problems=verify_problems,
        suggestions=verify_suggestions,
        data={
            **verify_result,
            "raw_output": "\n".join(_format_verify_tools_output(verify_result)),
            "report_path": str(report_path),
        },
    )


def _handle_multi_mode(
    reports_dir: str | None,
    output_dir: Path,
) -> CommandResult:
    """Handle --multi mode for aggregating multiple reports."""
    if not reports_dir:
        raise ValueError("--reports-dir is required with --multi")
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        raise ValueError(f"Reports directory not found: {reports_path}")

    artifacts, result_data = _generate_multi_report_triage(reports_path, output_dir)
    passed = result_data["passed_count"]
    failed = result_data["failed_count"]

    # Extract problems from failures_by_tool
    multi_problems: list[dict[str, Any]] = []
    for tool, repos in result_data.get("failures_by_tool", {}).items():
        multi_problems.append(
            {
                "severity": "error",
                "message": f"{tool}: {len(repos)} repo(s) failed",
                "code": f"CIHUB-MULTI-{tool.upper()}",
                "category": "tool",
                "tool": tool,
                "repos": repos,
            }
        )

    multi_suggestions: list[dict[str, Any]] = []
    if multi_problems:
        multi_suggestions.append(
            {
                "message": f"Run 'cat {artifacts['multi_markdown']}' for detailed breakdown",
                "code": "CIHUB-MULTI-VIEW-MARKDOWN",
            }
        )
        multi_suggestions.append(
            {
                "message": f"Run 'cat {artifacts['multi_triage']}' for JSON data",
                "code": "CIHUB-MULTI-VIEW-JSON",
            }
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Aggregated {result_data['repo_count']} repos: {passed} passed, {failed} failed",
        problems=multi_problems,
        suggestions=multi_suggestions,
        artifacts={key: str(path) for key, path in artifacts.items()},
        files_generated=[str(artifacts["multi_triage"]), str(artifacts["multi_markdown"])],
        data=result_data,
    )
