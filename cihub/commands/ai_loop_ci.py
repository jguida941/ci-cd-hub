"""CI execution helpers for the AI loop."""

from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path
from typing import Callable

from cihub.commands.ai_loop_types import LoopSettings
from cihub.exit_codes import EXIT_SUCCESS
from cihub.types import CommandResult


def build_ci_args(
    *,
    settings: LoopSettings,
    output_dir: Path,
    iteration: int,
    max_iterations: int | None,
) -> argparse.Namespace:
    """Build args for cmd_ci with explicit defaults."""
    ci_args = argparse.Namespace(
        repo=str(settings.repo_path),
        output_dir=str(output_dir),
        report=None,
        summary=None,
        workdir=settings.workdir,
        install_deps=False,
        no_summary=False,
        write_github_summary=None,
        correlation_id=settings.correlation_id,
        config_from_hub=settings.config_from_hub,
    )
    ci_args.ai_loop_iteration = iteration
    ci_args.ai_loop_max_iterations = max_iterations
    return ci_args


def run_ci_with_triage(
    cmd_ci: Callable[[argparse.Namespace], CommandResult],
    ci_args: argparse.Namespace,
) -> CommandResult:
    """Run cmd_ci with triage emission forced on for this call."""
    previous = os.environ.get("CIHUB_EMIT_TRIAGE")
    os.environ["CIHUB_EMIT_TRIAGE"] = "true"
    try:
        return cmd_ci(ci_args)
    finally:
        if previous is None:
            os.environ.pop("CIHUB_EMIT_TRIAGE", None)
        else:
            os.environ["CIHUB_EMIT_TRIAGE"] = previous


def write_ci_result(path: Path, result: CommandResult, started_at: float) -> None:
    payload = result.to_payload(
        command="cihub ci",
        status="success" if result.exit_code == EXIT_SUCCESS else "failure",
        duration_ms=int((time.time() - started_at) * 1000),
    )
    path.write_text(payload_to_json(payload), encoding="utf-8")


def snapshot_ci_outputs(ci_output_dir: Path, iteration_dir: Path) -> None:
    for name in ("report.json", "summary.md", "triage.json", "priority.json", "triage.md"):
        src = ci_output_dir / name
        if src.exists():
            shutil.copy2(src, iteration_dir / name)


def run_safe_fix(cmd_fix, repo_path: Path, state) -> None:
    fix_args = argparse.Namespace(
        repo=str(repo_path),
        safe=True,
        report=False,
        ai=False,
        dry_run=False,
    )
    try:
        fix_result = cmd_fix(fix_args)
        fix_data = fix_result.data or {}
        applied = fix_data.get("fixes", [])
        if applied:
            state.fixes_applied.extend(applied)
    except Exception:  # noqa: BLE001, S110 - continue loop on fix failure
        return


def run_report_fix(cmd_fix, repo_path: Path) -> None:
    report_args = argparse.Namespace(
        repo=str(repo_path),
        safe=False,
        report=True,
        ai=True,
        dry_run=False,
    )
    try:
        cmd_fix(report_args)
    except Exception:  # noqa: BLE001, S110 - best effort
        return


def payload_to_json(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, indent=2)
