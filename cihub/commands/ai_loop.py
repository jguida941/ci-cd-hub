"""Autonomous AI CI fix loop command."""

from __future__ import annotations

import argparse

from cihub.commands.ai_loop_analysis import break_reason as _break_reason
from cihub.commands.ai_loop_analysis import should_break as _should_break
from cihub.commands.ai_loop_artifacts import save_iteration_state as _save_iteration_state
from cihub.commands.ai_loop_ci import build_ci_args as _build_ci_args
from cihub.commands.ai_loop_ci import run_ci_with_triage as _run_ci_with_triage
from cihub.commands.ai_loop_local import run_local_loop
from cihub.commands.ai_loop_remote import run_remote_loop
from cihub.commands.ai_loop_session import acquire_lock, init_session_paths, release_lock
from cihub.commands.ai_loop_settings import resolve_settings as _resolve_settings
from cihub.commands.ai_loop_types import AI_LOOP_CONFIG, LoopState
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult


def cmd_ai_loop(args: argparse.Namespace) -> CommandResult:
    """
    Autonomous AI CI fix loop.

    Continuously runs `cihub ci`, generates triage bundles,
    applies safe fixes, and re-validates until all CI checks pass
    or max iterations reached.
    """
    # Lazy imports to avoid circular dependencies
    from cihub.commands.ci import cmd_ci
    from cihub.commands.fix import cmd_fix
    from cihub.services.ai.patterns import collect_suggestions
    from cihub.services.triage_service import detect_flaky_patterns

    try:
        settings = _resolve_settings(args)
    except ValueError as exc:
        return CommandResult(exit_code=EXIT_USAGE, summary=str(exc))

    try:
        session_paths = init_session_paths(settings)
    except OSError as exc:
        return CommandResult(exit_code=EXIT_FAILURE, summary=f"Failed to initialize session: {exc}")

    lock_error = acquire_lock(session_paths.lock_path, settings.resume)
    if lock_error:
        return CommandResult(exit_code=EXIT_FAILURE, summary=lock_error)

    state = LoopState(
        max_iterations=settings.max_iterations,
        max_duration_seconds=settings.max_duration_seconds,
    )

    contract = settings.contract
    ci_result: CommandResult | None = None

    try:
        if settings.remote:
            result = run_remote_loop(
                settings=settings,
                session_paths=session_paths,
                state=state,
                collect_suggestions=collect_suggestions,
                detect_flaky_patterns=detect_flaky_patterns,
                cmd_fix=cmd_fix,
            )
        else:
            result = run_local_loop(
                settings=settings,
                session_paths=session_paths,
                state=state,
                collect_suggestions=collect_suggestions,
                detect_flaky_patterns=detect_flaky_patterns,
                cmd_ci=cmd_ci,
                cmd_fix=cmd_fix,
            )
        ci_result = result
    finally:
        release_lock(session_paths.lock_path)

    if not ci_result:
        return CommandResult(exit_code=EXIT_FAILURE, summary="AI loop failed without result")

    if contract and contract.output_promise and ci_result.exit_code == EXIT_SUCCESS:
        data = ci_result.data or {}
        data["output_promise"] = contract.output_promise
        ci_result.data = data

    return ci_result


__all__ = [
    "AI_LOOP_CONFIG",
    "LoopState",
    "_break_reason",
    "_build_ci_args",
    "_resolve_settings",
    "_run_ci_with_triage",
    "_save_iteration_state",
    "_should_break",
    "cmd_ai_loop",
]
