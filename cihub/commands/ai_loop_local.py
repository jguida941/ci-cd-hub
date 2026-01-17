"""Local AI loop execution."""

from __future__ import annotations

import time
from typing import Any

from cihub.commands.ai_loop_analysis import (
    break_reason,
    failure_signature,
    is_test_only_failures,
    load_triage_failures,
)
from cihub.commands.ai_loop_artifacts import (
    save_iteration_state,
    write_artifact_pack,
    write_iteration_metrics,
    write_session_summary,
)
from cihub.commands.ai_loop_ci import (
    build_ci_args,
    run_ci_with_triage,
    run_report_fix,
    run_safe_fix,
    snapshot_ci_outputs,
    write_ci_result,
)
from cihub.commands.ai_loop_guardrails import check_guardrails, get_worktree_changes
from cihub.commands.ai_loop_results import failure_result, success_result
from cihub.commands.ai_loop_review import maybe_run_review
from cihub.commands.ai_loop_session import (
    init_iteration_artifacts,
    init_iteration_dir,
    iteration_range,
)
from cihub.commands.ai_loop_types import (
    AI_LOOP_CONFIG,
    IterationArtifacts,
    LoopSettings,
    LoopState,
    SessionPaths,
)
from cihub.exit_codes import EXIT_SUCCESS
from cihub.types import CommandResult


def run_local_loop(
    *,
    settings: LoopSettings,
    session_paths: SessionPaths,
    state: LoopState,
    collect_suggestions,
    detect_flaky_patterns,
    cmd_ci,
    cmd_fix,
) -> CommandResult:
    suggestions: list[dict[str, Any]] = []
    last_iteration_artifacts: IterationArtifacts | None = None
    ci_result: CommandResult | None = None

    for iteration in iteration_range(state.max_iterations):
        state.iteration = iteration
        iteration_dir = init_iteration_dir(session_paths.session_dir, iteration)
        artifacts = init_iteration_artifacts(iteration_dir, settings.bundle_dir)
        last_iteration_artifacts = artifacts

        if time.time() - state.start_time > state.max_duration_seconds:
            state.stop_reason = "duration_timeout"
            suggestions.append(
                {
                    "message": "Loop exceeded max duration",
                    "code": "CIHUB-AI-DURATION-TIMEOUT",
                }
            )
            save_iteration_state(artifacts.state_path, state, None)
            write_iteration_metrics(artifacts.metrics_path, state, None, None)
            write_session_summary(
                session_paths.session_dir,
                state,
                settings.contract,
                iteration_dir,
                None,
            )
            if settings.artifact_pack:
                write_artifact_pack(settings, iteration_dir, artifacts)
            return failure_result(
                settings,
                state,
                iteration_dir,
                artifacts,
                suggestions,
                None,
            )

        ci_args = build_ci_args(
            settings=settings,
            output_dir=session_paths.ci_output_dir,
            iteration=iteration,
            max_iterations=state.max_iterations,
        )
        start_time = time.time()
        ci_result = run_ci_with_triage(cmd_ci, ci_args)
        write_ci_result(artifacts.ci_result_path, ci_result, start_time)

        snapshot_ci_outputs(session_paths.ci_output_dir, iteration_dir)

        if ci_result.exit_code == EXIT_SUCCESS:
            state.stop_reason = "success"
            save_iteration_state(artifacts.state_path, state, ci_result)
            write_iteration_metrics(artifacts.metrics_path, state, ci_result, None)
            write_session_summary(
                session_paths.session_dir,
                state,
                settings.contract,
                iteration_dir,
                None,
            )
            if settings.artifact_pack:
                write_artifact_pack(settings, iteration_dir, artifacts)
            return success_result(settings, state, iteration_dir, artifacts)

        failures = load_triage_failures(session_paths.ci_output_dir)
        state.suggestions = collect_suggestions(ci_result.problems or [], failures)
        suggestions = list(state.suggestions)

        current_failures = failure_signature(ci_result)
        for failure_id in current_failures:
            if failure_id not in state.failures_seen:
                state.failures_seen.append(failure_id)

        flaky_stop = False
        flaky_result = detect_flaky_patterns(session_paths.history_path)
        if flaky_result.get("suspected_flaky"):
            recommendation = str(flaky_result.get("recommendation", "")).replace("\n", " ").strip()
            score = flaky_result.get("flakiness_score", 0)
            suggestions.append(
                {
                    "message": f"Flaky tests suspected (score {score}%). {recommendation}".strip(),
                    "code": "CIHUB-AI-FLAKY-DETECTED",
                }
            )
            if is_test_only_failures(failures):
                state.last_failure_signature = current_failures
                state.stop_reason = "flaky"
                flaky_stop = True

        if not flaky_stop:
            if settings.fix_mode == "safe":
                run_safe_fix(cmd_fix, settings.repo_path, state)
            if settings.fix_mode == "report-only" or settings.emit_report:
                run_report_fix(cmd_fix, settings.repo_path)

        change_files = get_worktree_changes(settings.repo_path)
        guardrail_problem = check_guardrails(change_files)
        if guardrail_problem:
            state.stop_reason = guardrail_problem["code"].lower()
            suggestions.append(
                {
                    "message": guardrail_problem["message"],
                    "code": guardrail_problem["code"],
                }
            )
            save_iteration_state(artifacts.state_path, state, ci_result)
            write_iteration_metrics(artifacts.metrics_path, state, ci_result, None)
            write_session_summary(
                session_paths.session_dir,
                state,
                settings.contract,
                iteration_dir,
                None,
            )
            if settings.artifact_pack:
                write_artifact_pack(settings, iteration_dir, artifacts)
            return failure_result(
                settings,
                state,
                iteration_dir,
                artifacts,
                suggestions,
                ci_result,
            )

        if change_files:
            state.no_change_iterations = 0
        else:
            state.no_change_iterations += 1
            if state.no_change_iterations >= AI_LOOP_CONFIG["no_change_threshold"]:
                state.stop_reason = "no_changes"
                suggestions.append(
                    {
                        "message": "No working tree changes detected across iterations",
                        "code": "CIHUB-AI-NO-CHANGES",
                    }
                )

        maybe_run_review(settings, iteration_dir, state)

        reason = break_reason(state, ci_result)
        if reason:
            state.stop_reason = reason

        if state.stop_reason:
            save_iteration_state(artifacts.state_path, state, ci_result)
            write_iteration_metrics(artifacts.metrics_path, state, ci_result, None)
            write_session_summary(
                session_paths.session_dir,
                state,
                settings.contract,
                iteration_dir,
                None,
            )
            if settings.artifact_pack:
                write_artifact_pack(settings, iteration_dir, artifacts)
            return failure_result(
                settings,
                state,
                iteration_dir,
                artifacts,
                suggestions,
                ci_result,
            )

        save_iteration_state(artifacts.state_path, state, ci_result)
        write_iteration_metrics(artifacts.metrics_path, state, ci_result, None)
        write_session_summary(
            session_paths.session_dir,
            state,
            settings.contract,
            iteration_dir,
            None,
        )
        if settings.artifact_pack:
            write_artifact_pack(settings, iteration_dir, artifacts)

    if not state.stop_reason:
        state.stop_reason = "max_iterations"
    final_iteration_dir = (
        last_iteration_artifacts.iteration_dir if last_iteration_artifacts else session_paths.session_dir
    )
    return failure_result(
        settings,
        state,
        final_iteration_dir,
        last_iteration_artifacts,
        suggestions,
        ci_result,
    )
