"""CommandResult helpers for the AI loop."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from cihub.commands.ai_loop_artifacts import collect_files_generated
from cihub.commands.ai_loop_types import IterationArtifacts, LoopSettings, LoopState, RemoteRun
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult


def success_result(
    settings: LoopSettings,
    state: LoopState,
    iteration_dir: Path,
    artifacts: IterationArtifacts,
    run_info: RemoteRun | None = None,
) -> CommandResult:
    data: dict[str, Any] = {
        "iterations": state.iteration,
        "fixes_applied": state.fixes_applied,
        "duration_seconds": time.time() - state.start_time,
        "session_dir": str(iteration_dir.parent),
        "iteration_dir": str(iteration_dir),
    }
    if run_info:
        data["run_id"] = run_info.run_id
        data["run_url"] = run_info.url
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"All CI checks passed after {state.iteration} iteration(s)",
        data=data,
        files_generated=collect_files_generated(iteration_dir, artifacts),
    )


def failure_result(
    settings: LoopSettings,
    state: LoopState,
    iteration_dir: Path,
    artifacts: IterationArtifacts | None,
    suggestions: list[dict[str, Any]],
    result: CommandResult | None,
) -> CommandResult:
    suggestions = [
        *suggestions,
        {"message": "Review triage outputs for remaining issues"},
        {"message": "Run 'cihub fix --report --ai' for detailed recommendations"},
    ]
    data: dict[str, Any] = {
        "iterations": state.iteration,
        "fixes_applied": state.fixes_applied,
        "remaining_failures": len(state.last_failure_signature),
        "duration_seconds": time.time() - state.start_time,
        "session_dir": str(iteration_dir.parent),
        "iteration_dir": str(iteration_dir),
    }
    if state.stop_reason:
        data["stop_reason"] = state.stop_reason
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Could not fix all issues after {state.iteration} iterations",
        problems=result.problems if result else [],
        suggestions=suggestions,
        data=data,
        files_generated=collect_files_generated(iteration_dir, artifacts),
    )
