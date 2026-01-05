"""Generate triage bundle outputs from existing report artifacts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
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
    generate_triage_bundle,
    write_triage_bundle,
)
from cihub.types import CommandResult
from cihub.utils.exec_utils import resolve_executable


def _build_meta(args: argparse.Namespace) -> dict[str, object]:
    return {
        "command": "cihub triage",
        "args": [str(arg) for arg in vars(args).values() if arg is not None],
    }


def _get_current_repo() -> str | None:
    """Get current repo from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S603, S607
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # Parse owner/repo from various git URL formats
        match = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
        if match:
            return match.group(1).removesuffix(".git")
    except Exception:  # noqa: BLE001, S110 - best effort, silent fail OK
        pass
    return None


def _fetch_run_info(run_id: str, repo: str | None) -> dict[str, Any]:
    """Fetch workflow run info via gh CLI."""
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "run", "view", run_id, "--json", "name,status,conclusion,headBranch,headSha,url,jobs"]
    if repo:
        cmd.extend(["--repo", repo])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch run info: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected response format from gh run view")
    return data


def _download_artifacts(run_id: str, repo: str | None, dest_dir: Path) -> bool:
    """Download workflow artifacts via gh CLI. Returns True if artifacts found."""
    gh_bin = resolve_executable("gh")
    cmd = [gh_bin, "run", "download", run_id, "--dir", str(dest_dir)]
    if repo:
        cmd.extend(["--repo", repo])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    # gh run download returns 0 even if no artifacts, check if anything was downloaded
    if result.returncode != 0:
        return False
    # Check if any files were actually downloaded
    return any(dest_dir.iterdir()) if dest_dir.exists() else False


def _find_report_in_artifacts(artifacts_dir: Path) -> Path | None:
    """Find report.json in downloaded artifacts (may be nested in subdirs)."""
    for report_path in artifacts_dir.rglob("report.json"):
        return report_path
    return None


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
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        # May fail if no failures or other issue
        return ""
    return result.stdout


def _parse_log_failures(logs: str) -> list[dict[str, Any]]:
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
                        failures.append(_create_log_failure(current_job, current_step, error_lines))
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
        failures.append(_create_log_failure(current_job, current_step, error_lines))

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


def _create_log_failure(job: str, step: str, errors: list[str]) -> dict[str, Any]:
    """Create a failure entry from log parsing."""
    tool = _infer_tool_from_step(step)
    category = CATEGORY_BY_TOOL.get(tool, "workflow")
    severity = SEVERITY_BY_CATEGORY.get(category, "medium")

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
        "errors": errors[:20],  # Limit to first 20 errors
        "artifacts": [],
        "reproduce": {"command": f"gh run view {job} --log-failed", "cwd": ".", "env": {}},
        "hints": [
            f"Review the {step} step output for details",
            "Check the error messages above for specific fixes",
        ],
    }


def _generate_remote_triage_bundle(
    run_id: str,
    repo: str | None,
    output_dir: Path,
) -> TriageBundle:
    """Generate triage bundle from a remote GitHub workflow run.

    Strategy:
    1. Try to download artifacts (report.json, tool-outputs/)
    2. If artifacts found, use existing generate_triage_bundle for structured analysis
    3. If no artifacts, fall back to parsing log output
    """
    run_info = _fetch_run_info(run_id, repo)
    notes: list[str] = [f"Analyzed from remote run: {run_id}"]

    # Try to download artifacts first
    with tempfile.TemporaryDirectory() as tmp_dir:
        artifacts_dir = Path(tmp_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        has_artifacts = _download_artifacts(run_id, repo, artifacts_dir)

        if has_artifacts:
            # Look for report.json in downloaded artifacts
            report_path = _find_report_in_artifacts(artifacts_dir)
            tool_outputs_dir = _find_tool_outputs_in_artifacts(artifacts_dir)

            if report_path:
                notes.append(f"Using structured artifacts from: {report_path.parent}")
                # Copy tool-outputs if found
                if tool_outputs_dir:
                    local_tool_outputs = output_dir / "tool-outputs"
                    if local_tool_outputs.exists():
                        shutil.rmtree(local_tool_outputs)
                    shutil.copytree(tool_outputs_dir, local_tool_outputs)

                # Use existing structured analysis
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
                return TriageBundle(
                    triage=triage_data,
                    priority=bundle.priority,
                    markdown=_build_markdown(triage_data, max_failures=20),
                    history_entry=bundle.history_entry,
                )

    # Fall back to log parsing if no artifacts
    notes.append("No artifacts found, using log parsing")
    logs = _fetch_failed_logs(run_id, repo)
    failures = _parse_log_failures(logs)
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
        "skipped_count": 0,
        "tool_counts": {"configured": 0, "ran": 0},
    }

    triage = {
        "schema_version": TRIAGE_SCHEMA_VERSION,
        "generated_at": _timestamp(),
        "run": run_data,
        "paths": {
            "output_dir": str(output_dir),
            "report_path": "",
            "summary_path": "",
        },
        "summary": summary,
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
        "output_dir": str(output_dir),
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


def cmd_triage(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    output_dir = Path(args.output_dir or ".cihub")
    run_id = getattr(args, "run", None)
    artifacts_dir = getattr(args, "artifacts_dir", None)
    repo = getattr(args, "repo", None)

    try:
        if run_id:
            # Remote run analysis mode
            bundle = _generate_remote_triage_bundle(run_id, repo, output_dir)
            artifacts = write_triage_bundle(bundle, output_dir)
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
        message = f"Failed to generate triage bundle: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Triage bundle generated",
            artifacts={key: str(path) for key, path in artifacts.items()},
            data={
                "schema_version": bundle.triage.get("schema_version", ""),
                "failure_count": bundle.triage.get("summary", {}).get("failure_count", 0),
            },
        )

    print(f"Wrote triage: {artifacts['triage']}")
    print(f"Wrote priority: {artifacts['priority']}")
    print(f"Wrote prompt pack: {artifacts['markdown']}")
    print(f"Updated history: {artifacts['history']}")
    return EXIT_SUCCESS
