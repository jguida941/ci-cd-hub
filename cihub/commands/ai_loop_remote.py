"""Remote AI loop execution using GitHub Actions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

from cihub.commands.ai_loop_analysis import (
    extract_failures,
    is_test_only_failures,
    problems_from_failures,
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
)
from cihub.commands.ai_loop_guardrails import (
    check_guardrails,
    detect_remote_repo,
    get_git_sha,
    get_worktree_changes,
    is_protected_branch,
    push_iteration,
)
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
    RemoteRun,
    SessionPaths,
)
from cihub.exit_codes import EXIT_FAILURE
from cihub.types import CommandResult
from cihub.utils.exec_utils import TIMEOUT_NETWORK, resolve_executable, safe_run
from cihub.utils.github import check_gh_auth, check_gh_installed


def run_remote_loop(
    *,
    settings: LoopSettings,
    session_paths: SessionPaths,
    state: LoopState,
    collect_suggestions,
    detect_flaky_patterns,
    cmd_fix,
) -> CommandResult:
    from cihub.commands.triage.remote import generate_remote_triage_bundle

    if settings.remote_provider != "gh":
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Remote provider not supported: {settings.remote_provider}",
        )

    gh_ok, gh_err = check_gh_installed()
    if not gh_ok:
        return CommandResult(exit_code=EXIT_FAILURE, summary=gh_err)
    gh_auth_ok, gh_auth_err = check_gh_auth()
    if not gh_auth_ok:
        return CommandResult(exit_code=EXIT_FAILURE, summary=gh_auth_err)

    remote_repo = settings.remote_repo or detect_remote_repo(settings.repo_path)
    if not remote_repo:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Unable to detect remote repo. Use --remote-repo owner/repo.",
        )

    if not settings.allow_protected_branch and is_protected_branch(settings.push_branch):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Refusing to push to protected branch: {settings.push_branch}",
        )

    if not settings.allow_dirty:
        dirty_files = get_worktree_changes(settings.repo_path)
        if dirty_files:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Working tree is dirty. Use --allow-dirty or commit changes.",
            )

    suggestions: list[dict[str, Any]] = []
    last_iteration_artifacts: IterationArtifacts | None = None

    for iteration in iteration_range(state.max_iterations):
        state.iteration = iteration
        iteration_dir = init_iteration_dir(session_paths.session_dir, iteration)
        artifacts = init_iteration_artifacts(iteration_dir, settings.bundle_dir)
        last_iteration_artifacts = artifacts

        if not settings.remote_dry_run:
            push_error = push_iteration(settings, iteration)
            if push_error:
                if "No changes to commit" in push_error:
                    state.stop_reason = "no_changes"
                    suggestions.append(
                        {
                            "message": push_error,
                            "code": "CIHUB-AI-NO-CHANGES",
                        }
                    )
                else:
                    state.stop_reason = "push_failed"
                    suggestions.append({"message": push_error, "code": "CIHUB-AI-PUSH-FAILED"})
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

        run_id = resolve_run_id(
            settings=settings,
            repo=remote_repo,
            commit_sha=get_git_sha(settings.repo_path),
        )
        if not run_id:
            state.stop_reason = "run_not_found"
            suggestions.append(
                {
                    "message": "Could not locate a matching GitHub Actions run",
                    "code": "CIHUB-AI-RUN-NOT-FOUND",
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

        run_info = wait_for_run(remote_repo, run_id, settings.max_duration_seconds)
        if not run_info:
            state.stop_reason = "remote_run_timeout"
            suggestions.append(
                {
                    "message": "Timed out waiting for remote run to complete",
                    "code": "CIHUB-AI-RUN-TIMEOUT",
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

        triage_data = None
        if settings.triage_mode != "none":
            triage_output = settings.triage_output_dir or iteration_dir
            try:
                triage_data = run_remote_triage(
                    generate_remote_triage_bundle,
                    run_id,
                    remote_repo,
                    triage_output,
                )
            except Exception as exc:  # noqa: BLE001
                if settings.fallback == "local":
                    triage_data = run_local_fallback_triage(
                        settings,
                        session_paths,
                        iteration_dir,
                        iteration,
                    )
                else:
                    state.stop_reason = "triage_failed"
                    suggestions.append(
                        {
                            "message": f"Remote triage failed: {exc}",
                            "code": "CIHUB-AI-TRIAGE-FAILED",
                        }
                    )

        if run_info.conclusion == "success":
            state.stop_reason = "success"
            save_iteration_state(artifacts.state_path, state, None)
            write_iteration_metrics(artifacts.metrics_path, state, None, run_info)
            write_session_summary(
                session_paths.session_dir,
                state,
                settings.contract,
                iteration_dir,
                run_info,
            )
            if settings.artifact_pack:
                write_artifact_pack(settings, iteration_dir, artifacts)
            return success_result(settings, state, iteration_dir, artifacts, run_info)

        failures = extract_failures(triage_data)
        if failures:
            state.last_failure_signature = frozenset(
                f"{item.get('tool', 'unknown')}:{str(item.get('message', ''))[:50]}" for item in failures
            )
        state.suggestions = collect_suggestions(
            problems_from_failures(failures),
            failures,
        )
        suggestions.extend(state.suggestions)

        flaky_result = detect_flaky_patterns(session_paths.history_path)
        if flaky_result.get("suspected_flaky") and is_test_only_failures(failures):
            state.stop_reason = "flaky"
            suggestions.append(
                {
                    "message": "Flaky tests suspected in remote loop",
                    "code": "CIHUB-AI-FLAKY-DETECTED",
                }
            )

        if not state.stop_reason:
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

        if state.stop_reason:
            save_iteration_state(artifacts.state_path, state, None)
            write_iteration_metrics(artifacts.metrics_path, state, None, run_info)
            write_session_summary(
                session_paths.session_dir,
                state,
                settings.contract,
                iteration_dir,
                run_info,
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

        save_iteration_state(artifacts.state_path, state, None)
        write_iteration_metrics(artifacts.metrics_path, state, None, run_info)
        write_session_summary(
            session_paths.session_dir,
            state,
            settings.contract,
            iteration_dir,
            run_info,
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
        None,
    )


def resolve_run_id(settings: LoopSettings, repo: str, commit_sha: str | None) -> str | None:
    if settings.triage_mode == "run" and settings.triage_run_id:
        return settings.triage_run_id
    if settings.triage_mode == "latest":
        return latest_run_id(repo, settings.workflow, settings.push_branch)
    if settings.triage_mode == "auto":
        if commit_sha:
            run_id = run_id_for_commit(repo, settings.workflow, settings.push_branch, commit_sha)
            if run_id:
                return run_id
        return latest_run_id(repo, settings.workflow, settings.push_branch)
    return settings.triage_run_id


def run_id_for_commit(repo: str, workflow: str | None, branch: str, commit_sha: str) -> str | None:
    started = time.time()
    while time.time() - started < TIMEOUT_NETWORK:
        runs = list_runs(repo, workflow=workflow, branch=branch, limit=20)
        for run in runs:
            if str(run.get("headSha", "")) == commit_sha:
                return str(run.get("databaseId"))
        time.sleep(5)
    return None


def latest_run_id(repo: str, workflow: str | None, branch: str) -> str | None:
    runs = list_runs(repo, workflow=workflow, branch=branch, limit=1)
    if runs:
        return str(runs[0].get("databaseId"))
    return None


def list_runs(repo: str, workflow: str | None, branch: str | None, limit: int) -> list[dict[str, Any]]:
    gh_bin = resolve_executable("gh")
    fields = "databaseId,headSha,status,conclusion,headBranch,createdAt"
    cmd = [gh_bin, "run", "list", "--json", fields, "--limit", str(limit)]
    cmd.extend(["--repo", repo])
    if workflow:
        cmd.extend(["--workflow", workflow])
    if branch:
        cmd.extend(["--branch", branch])
    result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return data


def wait_for_run(repo: str, run_id: str, max_duration_seconds: int) -> RemoteRun | None:
    gh_bin = resolve_executable("gh")
    started = time.time()
    while time.time() - started < max_duration_seconds:
        cmd = [
            gh_bin,
            "run",
            "view",
            run_id,
            "--json",
            "status,conclusion,url",
            "--repo",
            repo,
        ]
        result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
        if result.returncode != 0:
            time.sleep(5)
            continue
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            time.sleep(5)
            continue
        status = payload.get("status", "")
        conclusion = payload.get("conclusion", "")
        url = payload.get("url", "")
        if status == "completed":
            return RemoteRun(run_id=run_id, conclusion=conclusion, status=status, url=url)
        time.sleep(5)
    return None


def run_remote_triage(generate_remote_triage_bundle, run_id: str, repo: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = generate_remote_triage_bundle(run_id, repo, output_dir)
    if isinstance(result, tuple):
        _artifacts, data = result
        data_path = output_dir / "multi-triage.json"
        data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return cast(dict[str, Any], data)

    triage = result.triage
    priority = result.priority
    markdown = result.markdown
    (output_dir / "triage.json").write_text(json.dumps(triage, indent=2), encoding="utf-8")
    (output_dir / "priority.json").write_text(json.dumps(priority, indent=2), encoding="utf-8")
    (output_dir / "triage.md").write_text(markdown, encoding="utf-8")
    return cast(dict[str, Any], triage)


def run_local_fallback_triage(
    settings: LoopSettings,
    session_paths: SessionPaths,
    iteration_dir: Path,
    iteration: int,
) -> dict[str, Any]:
    from cihub.commands.ci import cmd_ci

    ci_args = build_ci_args(
        settings=settings,
        output_dir=session_paths.ci_output_dir,
        iteration=iteration,
        max_iterations=settings.max_iterations,
    )
    run_ci_with_triage(cmd_ci, ci_args)
    snapshot_ci_outputs(session_paths.ci_output_dir, iteration_dir)
    triage_path = session_paths.ci_output_dir / "triage.json"
    if triage_path.exists():
        return cast(dict[str, Any], json.loads(triage_path.read_text(encoding="utf-8")))
    return {}
