"""Generate triage bundle outputs from existing report artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.triage_service import (
    CATEGORY_BY_TOOL,
    SEVERITY_BY_CATEGORY,
    TRIAGE_SCHEMA_VERSION,
    TriageBundle,
    _build_markdown,
    _sort_failures,
    _timestamp,
    aggregate_triage_bundles,
    detect_flaky_patterns,
    detect_gate_changes,
    generate_triage_bundle,
    write_triage_bundle,
)
from cihub.types import CommandResult
from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    TIMEOUT_NETWORK,
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)

# Maximum errors to include in triage bundle (prevents huge payloads)
MAX_ERRORS_IN_TRIAGE = 20


def _build_meta(args: argparse.Namespace) -> dict[str, object]:
    return {
        "command": "cihub triage",
        "args": [str(arg) for arg in vars(args).values() if arg is not None],
    }


def _get_current_repo() -> str | None:
    """Get current repo from git remote."""
    try:
        result = safe_run(
            ["git", "remote", "get-url", "origin"],
            timeout=TIMEOUT_QUICK,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # Parse owner/repo from various git URL formats
        match = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
        if match:
            return match.group(1).removesuffix(".git")
    except (CommandNotFoundError, CommandTimeoutError):
        pass
    return None


def _fetch_run_info(run_id: str, repo: str | None) -> dict[str, Any]:
    """Fetch workflow run info via gh CLI."""
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "run", "view", run_id, "--json", "name,status,conclusion,headBranch,headSha,url,jobs"]
    if repo:
        cmd.extend(["--repo", repo])
    result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch run info: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected response format from gh run view")
    return data


def _list_runs(
    repo: str | None,
    workflow: str | None = None,
    branch: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """List recent workflow runs with optional filtering."""
    gh_bin = resolve_executable("gh")
    json_fields = "databaseId,name,status,conclusion,headBranch,createdAt"
    cmd = [gh_bin, "run", "list", "--json", json_fields, "--limit", str(limit)]
    if repo:
        cmd.extend(["--repo", repo])
    if workflow:
        cmd.extend(["--workflow", workflow])
    if branch:
        cmd.extend(["--branch", branch])

    result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list runs: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if not isinstance(data, list):
        return []
    return data


def _download_artifacts(run_id: str, repo: str | None, dest_dir: Path) -> bool:
    """Download workflow artifacts via gh CLI. Returns True if artifacts found."""
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "run", "download", run_id, "--dir", str(dest_dir)]
    if repo:
        cmd.extend(["--repo", repo])
    result = safe_run(cmd, timeout=TIMEOUT_BUILD)  # 600s for large artifacts
    # gh run download returns 0 even if no artifacts, check if anything was downloaded
    if result.returncode != 0:
        return False
    # Check if any files were actually downloaded
    return any(dest_dir.iterdir()) if dest_dir.exists() else False


def _find_report_in_artifacts(artifacts_dir: Path) -> Path | None:
    """Find first report.json in downloaded artifacts (may be nested in subdirs)."""
    for report_path in artifacts_dir.rglob("report.json"):
        return report_path
    return None


def _find_all_reports_in_artifacts(artifacts_dir: Path) -> list[Path]:
    """Find all report.json files in downloaded artifacts."""
    return sorted(artifacts_dir.rglob("report.json"), key=lambda p: str(p))


def _find_tool_outputs_in_artifacts(artifacts_dir: Path) -> Path | None:
    """Find tool-outputs directory in downloaded artifacts."""
    for tool_outputs in artifacts_dir.rglob("tool-outputs"):
        if tool_outputs.is_dir():
            return tool_outputs
    return None


def _fetch_failed_logs(run_id: str, repo: str | None) -> str:
    """Fetch failed job logs via gh CLI."""
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "run", "view", run_id, "--log-failed"]
    if repo:
        cmd.extend(["--repo", repo])
    result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
    if result.returncode != 0:
        # May fail if no failures or other issue
        return ""
    return result.stdout


def _parse_log_failures(logs: str, run_id: str = "", repo: str | None = None) -> list[dict[str, Any]]:
    """Parse failure information from gh run view --log-failed output."""
    failures: list[dict[str, Any]] = []
    current_job = ""
    current_step = ""
    error_lines: list[str] = []

    for line in logs.split("\n"):
        # Detect job/step headers (format: "JobName\tStepName\tTimestamp Message")
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                job = parts[0].strip()
                step = parts[1].strip()
                if job and job != current_job:
                    current_job = job
                if step and step != current_step:
                    # Save previous errors
                    if error_lines and current_step:
                        failures.append(_create_log_failure(current_job, current_step, error_lines, run_id, repo))
                    current_step = step
                    error_lines = []

        # Detect error annotations
        if "##[error]" in line:
            error_msg = line.split("##[error]", 1)[1].strip() if "##[error]" in line else line
            error_lines.append(error_msg)
        elif "error:" in line.lower() and current_step:
            error_lines.append(line.strip())

    # Save last batch
    if error_lines and current_step:
        failures.append(_create_log_failure(current_job, current_step, error_lines, run_id, repo))

    return failures


def _infer_tool_from_step(step: str) -> str:
    """Infer tool name from step name."""
    step_lower = step.lower()
    if "mypy" in step_lower or "typecheck" in step_lower:
        return "mypy"
    if "ruff" in step_lower:
        return "ruff"
    if "pytest" in step_lower or "test" in step_lower:
        return "pytest"
    if "bandit" in step_lower:
        return "bandit"
    if "pip-audit" in step_lower or "pip_audit" in step_lower:
        return "pip_audit"
    if "checkstyle" in step_lower:
        return "checkstyle"
    if "spotbugs" in step_lower:
        return "spotbugs"
    if "actionlint" in step_lower:
        return "actionlint"
    return "workflow"


def _create_log_failure(
    job: str, step: str, errors: list[str], run_id: str = "", repo: str | None = None
) -> dict[str, Any]:
    """Create a failure entry from log parsing."""
    tool = _infer_tool_from_step(step)
    category = CATEGORY_BY_TOOL.get(tool, "workflow")
    severity = SEVERITY_BY_CATEGORY.get(category, "medium")

    # Build reproduce command with run_id if available
    reproduce_cmd = f"gh run view {run_id} --log-failed" if run_id else "gh run view --log-failed"
    if repo:
        reproduce_cmd += f" --repo {repo}"

    return {
        "id": f"{tool}:{job}:{step}",
        "category": category,
        "severity": severity,
        "tool": tool,
        "status": "failed",
        "reason": "workflow_failed",
        "message": f"{job} / {step}: {len(errors)} error(s)",
        "job": job,
        "step": step,
        "errors": errors[:MAX_ERRORS_IN_TRIAGE],
        "artifacts": [],
        "reproduce": {"command": reproduce_cmd, "cwd": ".", "env": {}},
        "hints": [
            f"Review the {step} step output for details",
            "Check the error messages above for specific fixes",
        ],
    }


def _generate_remote_triage_bundle(
    run_id: str,
    repo: str | None,
    output_dir: Path,
    *,
    force_aggregate: bool = False,
    force_per_repo: bool = False,
) -> TriageBundle | tuple[dict[str, Path], dict[str, Any]]:
    """Generate triage bundle from a remote GitHub workflow run.

    Strategy:
    1. Download artifacts to persistent path: {output_dir}/runs/{run_id}/artifacts/
    2. Auto-detect report.json files:
       - 1 report  → single triage bundle (returns TriageBundle)
       - N reports → multi-triage aggregation (returns artifacts dict + result dict)
    3. If no artifacts, fall back to parsing log output (returns TriageBundle)

    Args:
        run_id: GitHub workflow run ID
        repo: Repository in owner/repo format
        output_dir: Output directory for triage artifacts
        force_aggregate: Force aggregated output for multi-report mode
        force_per_repo: Force per-repo output for multi-report mode (separate bundles)

    Returns:
        TriageBundle for single-report or log-fallback mode.
        tuple[dict, dict] for multi-report mode (artifacts, result_data).
    """
    run_info = _fetch_run_info(run_id, repo)
    notes: list[str] = [f"Analyzed from remote run: {run_id}"]

    # Persistent artifact storage
    run_dir = output_dir / "runs" / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    has_artifacts = _download_artifacts(run_id, repo, artifacts_dir)

    if has_artifacts:
        # Find ALL report.json files (may be multiple for orchestrator runs)
        report_paths = _find_all_reports_in_artifacts(artifacts_dir)

        if len(report_paths) > 1:
            # Multi-report mode: aggregate all reports (unless per-repo mode)
            notes.append(f"Found {len(report_paths)} reports")
            bundles: list[TriageBundle] = []
            per_repo_paths: dict[str, Path] = {}

            for report_path in report_paths:
                meta = {
                    "command": f"cihub triage --run {run_id}",
                    "args": [],
                    "correlation_id": run_id,
                    "repo": repo or _get_current_repo() or "",
                    "branch": run_info.get("headBranch", ""),
                    "commit_sha": run_info.get("headSha", ""),
                    "workflow_ref": run_info.get("url", ""),
                }
                bundle = generate_triage_bundle(
                    output_dir=report_path.parent,
                    report_path=report_path,
                    meta=meta,
                )
                bundles.append(bundle)

                # Write individual bundle if per-repo mode
                if force_per_repo:
                    # Use artifact folder name as identifier
                    repo_name = report_path.parent.name
                    triage_path = run_dir / f"triage-{repo_name}.json"
                    md_path = run_dir / f"triage-{repo_name}.md"
                    triage_path.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
                    md_path.write_text(bundle.summary_markdown, encoding="utf-8")
                    per_repo_paths[repo_name] = triage_path

            # Per-repo mode: return index of individual bundles
            if force_per_repo:
                index_path = run_dir / "triage-index.json"
                index_data = {
                    "run_id": run_id,
                    "repo_count": len(bundles),
                    "bundles": {name: str(path) for name, path in per_repo_paths.items()},
                }
                index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

                artifacts_out = {
                    "index": index_path,
                    "artifacts_dir": artifacts_dir,
                    **{f"triage_{name}": path for name, path in per_repo_paths.items()},
                }
                result_data = {
                    "mode": "per-repo",
                    "repo_count": len(bundles),
                    "passed_count": sum(1 for b in bundles if b.overall_status == "passed"),
                    "failed_count": sum(1 for b in bundles if b.overall_status == "failed"),
                    "bundles": list(per_repo_paths.keys()),
                }
                return artifacts_out, result_data

            # Aggregate and write multi-triage output (default)
            result = aggregate_triage_bundles(bundles)
            multi_triage_path = run_dir / "multi-triage.json"
            multi_md_path = run_dir / "multi-triage.md"

            multi_triage_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
            multi_md_path.write_text(result.summary_markdown, encoding="utf-8")

            artifacts_out = {
                "multi_triage": multi_triage_path,
                "multi_markdown": multi_md_path,
                "artifacts_dir": artifacts_dir,
            }
            return artifacts_out, result.to_dict()

        elif len(report_paths) == 1:
            # Single report mode
            report_path = report_paths[0]
            notes.append(f"Using structured artifacts from: {report_path.parent}")

            meta = {
                "command": f"cihub triage --run {run_id}",
                "args": [],
                "correlation_id": run_id,
                "repo": repo or _get_current_repo() or "",
                "branch": run_info.get("headBranch", ""),
                "commit_sha": run_info.get("headSha", ""),
                "workflow_ref": run_info.get("url", ""),
            }
            bundle = generate_triage_bundle(
                output_dir=report_path.parent,
                report_path=report_path,
                meta=meta,
            )
            # Add notes about artifact source
            triage_data = dict(bundle.triage)
            triage_data["notes"] = notes + (triage_data.get("notes") or [])
            triage_data["paths"]["artifacts_dir"] = str(artifacts_dir)
            return TriageBundle(
                triage=triage_data,
                priority=bundle.priority,
                markdown=_build_markdown(triage_data, max_failures=20),
                history_entry=bundle.history_entry,
            )

    # Fall back to log parsing if no artifacts
    notes.append("No artifacts found, using log parsing")
    logs = _fetch_failed_logs(run_id, repo)
    failures = _parse_log_failures(logs, run_id, repo)
    priority = _sort_failures(failures)

    run_data = {
        "correlation_id": run_id,
        "repo": repo or _get_current_repo() or "",
        "commit_sha": run_info.get("headSha", ""),
        "branch": run_info.get("headBranch", ""),
        "run_id": run_id,
        "workflow_name": run_info.get("name", ""),
        "workflow_url": run_info.get("url", ""),
        "command": f"cihub triage --run {run_id}",
        "args": [],
    }

    failure_count = len([f for f in failures if f.get("status") == "failed"])

    summary = {
        "overall_status": run_info.get("conclusion", "failure"),
        "failure_count": failure_count,
        "warning_count": 0,
        "info_count": 0,
        "evidence_error_count": 0,
        "skipped_count": 0,
        "required_not_run_count": 0,
        "tool_counts": {"configured": 0, "ran": 0},
    }

    triage = {
        "schema_version": TRIAGE_SCHEMA_VERSION,
        "generated_at": _timestamp(),
        "run": run_data,
        "paths": {
            "output_dir": str(run_dir),
            "artifacts_dir": str(artifacts_dir),
            "report_path": "",
            "summary_path": "",
        },
        "summary": summary,
        "tool_evidence": [],
        "evidence_issues": [],
        "failures": priority,
        "warnings": [],
        "notes": notes,
    }

    priority_payload = {
        "schema_version": "cihub-priority-v1",
        "failures": priority,
    }

    history_entry = {
        "timestamp": triage["generated_at"],
        "correlation_id": run_id,
        "output_dir": str(run_dir),
        "overall_status": summary["overall_status"],
        "failure_count": summary["failure_count"],
    }

    markdown = _build_markdown(triage, max_failures=20)

    return TriageBundle(
        triage=triage,
        priority=priority_payload,
        markdown=markdown,
        history_entry=history_entry,
    )


def _generate_multi_report_triage(
    reports_dir: Path,
    output_dir: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Generate triage for multiple report.json files in a directory.

    Returns (artifacts dict, multi-triage result dict).
    """
    bundles: list[TriageBundle] = []

    # Find all report.json files
    for report_path in reports_dir.rglob("report.json"):
        # Use the report's parent directory as output_dir context
        report_output_dir = report_path.parent
        bundle = generate_triage_bundle(
            output_dir=report_output_dir,
            report_path=report_path,
            meta={"command": "cihub triage --multi"},
        )
        bundles.append(bundle)

    if not bundles:
        raise RuntimeError(f"No report.json files found in {reports_dir}")

    # Aggregate bundles
    result = aggregate_triage_bundles(bundles)

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    multi_triage_path = output_dir / "multi-triage.json"
    multi_md_path = output_dir / "multi-triage.md"

    multi_triage_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    multi_md_path.write_text(result.summary_markdown, encoding="utf-8")

    artifacts = {
        "multi_triage": multi_triage_path,
        "multi_markdown": multi_md_path,
    }

    return artifacts, result.to_dict()


def _format_gate_history_output(gate_result: dict[str, Any]) -> list[str]:
    """Format gate history analysis for human-readable output."""
    lines = [
        "Gate History Analysis",
        "=" * 50,
        f"Runs analyzed: {gate_result['runs_analyzed']}",
    ]

    if gate_result.get("new_failures"):
        lines.append(f"New failures: {', '.join(gate_result['new_failures'])}")

    if gate_result.get("fixed_gates"):
        lines.append(f"Fixed gates: {', '.join(gate_result['fixed_gates'])}")

    if gate_result.get("recurring_failures"):
        lines.append("Recurring issues:")
        for item in gate_result["recurring_failures"]:
            lines.append(f"  - {item['gate']} (fails {item['fail_rate']}%): {''.join(item['history'])}")

    if gate_result.get("gate_history"):
        lines.append("Gate timeline (last 10 runs):")
        for gate, timeline in gate_result["gate_history"].items():
            lines.append(f"  - {gate}: {''.join(timeline)}")

    lines.append(f"Summary: {gate_result['summary']}")
    return lines


def _format_flaky_output(flaky_result: dict[str, Any]) -> list[str]:
    """Format flaky analysis for human-readable output."""
    suspected = "YES" if flaky_result["suspected_flaky"] else "No"
    lines = [
        "Flaky Test Analysis",
        "=" * 50,
        f"Runs analyzed: {flaky_result['runs_analyzed']}",
        f"State changes: {flaky_result['state_changes']}",
        f"Flakiness score: {flaky_result['flakiness_score']}%",
        f"Suspected flaky: {suspected}",
    ]

    if flaky_result.get("recent_history"):
        lines.append(f"Recent runs (newest last): {flaky_result['recent_history']}")

    if flaky_result.get("details"):
        lines.append("Details:")
        for detail in flaky_result["details"]:
            lines.append(f"  - {detail}")

    lines.append(f"Recommendation: {flaky_result['recommendation']}")
    return lines


def cmd_triage(args: argparse.Namespace) -> CommandResult:
    output_dir = Path(args.output_dir or ".cihub")
    run_id = getattr(args, "run", None)
    artifacts_dir = getattr(args, "artifacts_dir", None)
    repo = getattr(args, "repo", None)
    multi_mode = getattr(args, "multi", False)
    reports_dir = getattr(args, "reports_dir", None)
    detect_flaky = getattr(args, "detect_flaky", False)
    gate_history = getattr(args, "gate_history", False)
    workflow_filter = getattr(args, "workflow", None)
    branch_filter = getattr(args, "branch", None)
    aggregate_mode = getattr(args, "aggregate", False)
    per_repo_mode = getattr(args, "per_repo", False)

    # Handle --gate-history mode (standalone analysis)
    if gate_history:
        history_path = output_dir / "history.jsonl"
        gate_result = detect_gate_changes(history_path)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=gate_result["summary"],
            data={
                **gate_result,
                "raw_output": "\n".join(_format_gate_history_output(gate_result)),
            },
        )

    # Handle --detect-flaky mode (standalone analysis)
    if detect_flaky:
        history_path = output_dir / "history.jsonl"
        flaky_result = detect_flaky_patterns(history_path)

        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=(
                f"Flaky analysis: score={flaky_result['flakiness_score']}%, "
                f"suspected={flaky_result['suspected_flaky']}"
            ),
            data={
                **flaky_result,
                "raw_output": "\n".join(_format_flaky_output(flaky_result)),
            },
        )

    try:
        # Multi-report mode
        if multi_mode:
            if not reports_dir:
                raise ValueError("--reports-dir is required with --multi")
            reports_path = Path(reports_dir)
            if not reports_path.exists():
                raise ValueError(f"Reports directory not found: {reports_path}")

            artifacts, result_data = _generate_multi_report_triage(reports_path, output_dir)
            passed = result_data["passed_count"]
            failed = result_data["failed_count"]

            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"Aggregated {result_data['repo_count']} repos: {passed} passed, {failed} failed",
                artifacts={key: str(path) for key, path in artifacts.items()},
                files_generated=[str(artifacts["multi_triage"]), str(artifacts["multi_markdown"])],
                data=result_data,
            )

        # Handle --workflow/--branch filters without explicit --run
        run_note = None
        if (workflow_filter or branch_filter) and not run_id:
            runs = _list_runs(repo, workflow=workflow_filter, branch=branch_filter, limit=10)
            if not runs:
                filter_desc = []
                if workflow_filter:
                    filter_desc.append(f"workflow={workflow_filter}")
                if branch_filter:
                    filter_desc.append(f"branch={branch_filter}")
                raise ValueError(f"No runs found matching: {', '.join(filter_desc)}")

            # Use the most recent run
            run_id = str(runs[0]["databaseId"])
            run_note = f"Using most recent run: {run_id} ({runs[0].get('name', 'unknown')})"
            if len(runs) > 1:
                run_note += f" (Found {len(runs)} matching runs, use --run to specify)"

        if run_id:
            # Remote run analysis mode (with persistent artifacts)
            result = _generate_remote_triage_bundle(
                run_id, repo, output_dir,
                force_aggregate=aggregate_mode,
                force_per_repo=per_repo_mode,
            )

            # Check if multi-report mode was triggered (returns tuple)
            if isinstance(result, tuple):
                artifacts_out, result_data = result
                passed = result_data["passed_count"]
                failed = result_data["failed_count"]

                return CommandResult(
                    exit_code=EXIT_SUCCESS,
                    summary=f"Run {run_id}: {result_data['repo_count']} repos, {passed} passed, {failed} failed",
                    artifacts={k: str(v) for k, v in artifacts_out.items()},
                    files_generated=[
                        str(artifacts_out.get("multi_triage", "")),
                        str(artifacts_out.get("multi_markdown", "")),
                    ],
                    data={
                        **result_data,
                        "run_note": run_note,
                    } if run_note else result_data,
                )

            # Single report or log-fallback mode (returns TriageBundle)
            bundle = result
            run_dir = output_dir / "runs" / run_id
            artifacts = write_triage_bundle(bundle, run_dir)
        elif artifacts_dir:
            # Offline artifacts mode
            artifacts_path = Path(artifacts_dir)
            bundle = generate_triage_bundle(
                output_dir=artifacts_path,
                meta=_build_meta(args),
            )
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
            artifacts = write_triage_bundle(bundle, output_dir)
    except Exception as exc:  # noqa: BLE001 - surface error in CLI
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Failed to generate triage bundle: {exc}",
            problems=[{
                "severity": "error",
                "message": str(exc),
                "code": "CIHUB-TRIAGE-ERROR",
            }],
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Triage bundle generated",
        artifacts={key: str(path) for key, path in artifacts.items()},
        files_generated=[
            str(artifacts["triage"]),
            str(artifacts["priority"]),
            str(artifacts["markdown"]),
        ],
        data={
            "schema_version": bundle.triage.get("schema_version", ""),
            "failure_count": bundle.triage.get("summary", {}).get("failure_count", 0),
            "key_values": {
                "triage": str(artifacts["triage"]),
                "priority": str(artifacts["priority"]),
                "prompt_pack": str(artifacts["markdown"]),
                "history": str(artifacts["history"]),
            },
        },
    )
