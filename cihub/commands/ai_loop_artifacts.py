"""Artifact and logging helpers for the AI loop."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cihub.commands.ai_loop_analysis import hash_failure_signature
from cihub.commands.ai_loop_types import Contract, IterationArtifacts, LoopSettings, LoopState, RemoteRun
from cihub.types import CommandResult
from cihub.utils.exec_utils import TIMEOUT_QUICK, CommandNotFoundError, CommandTimeoutError, safe_run


def save_iteration_state(
    state_path: Path,
    state: LoopState,
    result: CommandResult | None,
) -> None:
    state_data: dict[str, Any] = {
        "iteration": state.iteration,
        "exit_code": result.exit_code if result else None,
        "problems_count": len(result.problems) if result and result.problems else 0,
        "fixes_applied_total": len(state.fixes_applied),
        "failures_seen_total": len(state.failures_seen),
        "consecutive_same_failures": state.consecutive_same_failures,
        "stop_reason": state.stop_reason or "",
        "timestamp": time.time(),
    }
    state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")


def write_iteration_metrics(
    path: Path,
    state: LoopState,
    result: CommandResult | None,
    run_info: RemoteRun | None,
) -> None:
    metrics: dict[str, Any] = {
        "iteration": state.iteration,
        "duration_seconds": time.time() - state.start_time,
        "stop_reason": state.stop_reason or "",
        "failure_signature_hash": hash_failure_signature(state.last_failure_signature),
        "exit_code": result.exit_code if result else None,
    }
    if run_info:
        metrics["run_id"] = run_info.run_id
        metrics["run_url"] = run_info.url
        metrics["run_conclusion"] = run_info.conclusion
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def write_session_summary(
    session_dir: Path,
    state: LoopState,
    contract: Contract | None,
    iteration_dir: Path,
    run_info: RemoteRun | None,
) -> None:
    summary_path = session_dir / "ai_loop_summary.md"
    lines = [
        "# AI Loop Summary",
        f"Iteration: {state.iteration}",
        f"Stop reason: {state.stop_reason or ''}",
        f"Session dir: {session_dir}",
        f"Last iteration dir: {iteration_dir}",
        "",
    ]
    if run_info:
        lines.extend(
            [
                "Remote run:",
                f"- Run ID: {run_info.run_id}",
                f"- Status: {run_info.status}",
                f"- Conclusion: {run_info.conclusion}",
                f"- URL: {run_info.url}",
                "",
            ]
        )
    if contract and contract.output_promise and state.stop_reason == "success":
        lines.append(f"<promise>{contract.output_promise}</promise>")
    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def collect_files_generated(iteration_dir: Path, artifacts: IterationArtifacts | None) -> list[str]:
    files = []
    if iteration_dir:
        for name in ("triage.json", "priority.json", "triage.md", "ci-result.json", "state.json"):
            path = iteration_dir / name
            if path.exists():
                files.append(str(path))
    if artifacts and artifacts.bundle_json and artifacts.bundle_json.exists():
        files.append(str(artifacts.bundle_json))
    if artifacts and artifacts.bundle_md and artifacts.bundle_md.exists():
        files.append(str(artifacts.bundle_md))
    return files


def write_artifact_pack(settings: LoopSettings, iteration_dir: Path, artifacts: IterationArtifacts) -> None:
    bundle_dir = settings.bundle_dir or iteration_dir
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_json = artifacts.bundle_json or bundle_dir / "bundle.json"
    bundle_md = artifacts.bundle_md or bundle_dir / "bundle.md"

    files = collect_bundle_files(iteration_dir, settings.repo_path)
    bundle_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "iteration": int(iteration_dir.name.split("-")[-1]) if "-" in iteration_dir.name else 0,
        "files": files,
    }
    bundle_json.write_text(json.dumps(bundle_data, indent=2), encoding="utf-8")

    md_lines = ["# AI Loop Artifact Bundle", ""]
    for item in files:
        md_lines.append(f"- {item['path']} ({item.get('sha256', '')})")
    bundle_md.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")


def collect_bundle_files(iteration_dir: Path, repo_path: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in iteration_dir.glob("*"):
        if path.is_file():
            files.append(_file_entry(path))

    diff_stat = _run_git_capture(["git", "diff", "--stat"], repo_path)
    status = _run_git_capture(["git", "status", "--porcelain"], repo_path)
    diff_patch = _run_git_capture(["git", "diff"], repo_path)

    if diff_stat:
        stat_path = iteration_dir / "diff-stat.txt"
        stat_path.write_text(diff_stat, encoding="utf-8")
        files.append(_file_entry(stat_path))
    if status:
        status_path = iteration_dir / "git-status.txt"
        status_path.write_text(status, encoding="utf-8")
        files.append(_file_entry(status_path))
    if diff_patch:
        patch_path = iteration_dir / "diff.patch"
        patch_path.write_text(diff_patch, encoding="utf-8")
        files.append(_file_entry(patch_path))

    return files


def _file_entry(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _run_git_capture(cmd: list[str], cwd: Path) -> str:
    try:
        result = safe_run(cmd, cwd=cwd, timeout=TIMEOUT_QUICK)
    except (CommandNotFoundError, CommandTimeoutError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout
