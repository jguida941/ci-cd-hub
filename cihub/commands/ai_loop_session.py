"""Session and iteration helpers for the AI loop."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cihub.commands.ai_loop_guardrails import detect_remote_repo, get_branch
from cihub.commands.ai_loop_types import IterationArtifacts, LoopSettings, SessionPaths


def init_session_paths(settings: LoopSettings) -> SessionPaths:
    settings.output_root.mkdir(parents=True, exist_ok=True)

    if settings.resume:
        session_dir = settings.output_root
        if not session_dir.exists():
            raise OSError(f"Resume directory does not exist: {session_dir}")
    else:
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        session_dir = settings.output_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

    ci_output_dir = session_dir / "ci"
    ci_output_dir.mkdir(parents=True, exist_ok=True)
    history_path = ci_output_dir / "history.jsonl"

    lock_path = lock_path_for_settings(settings)

    return SessionPaths(
        output_root=settings.output_root,
        session_dir=session_dir,
        ci_output_dir=ci_output_dir,
        history_path=history_path,
        lock_path=lock_path,
    )


def lock_path_for_settings(settings: LoopSettings) -> Path:
    lock_dir = settings.output_root / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    branch = settings.push_branch if settings.remote else get_branch(settings.repo_path)
    branch_slug = branch.replace("/", "-")
    repo_slug = detect_remote_repo(settings.repo_path) or settings.repo_path.name
    repo_slug = repo_slug.replace("/", "-")
    return lock_dir / f"{repo_slug}-{branch_slug}.lock"


def acquire_lock(path: Path | None, resume: bool) -> str | None:
    if path is None:
        return None
    if path.exists() and not resume:
        return f"AI loop lock exists: {path}"
    payload = {
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return None


def release_lock(path: Path | None) -> None:
    if not path:
        return
    try:
        path.unlink()
    except OSError:
        return


def iteration_range(max_iterations: int | None) -> range:
    if max_iterations is None:
        return range(1, 10_000_000)
    return range(1, max_iterations + 1)


def init_iteration_dir(session_dir: Path, iteration: int) -> Path:
    iteration_dir = session_dir / f"iteration-{iteration}"
    iteration_dir.mkdir(parents=True, exist_ok=True)
    return iteration_dir


def init_iteration_artifacts(iteration_dir: Path, bundle_dir: Path | None) -> IterationArtifacts:
    return IterationArtifacts(
        iteration_dir=iteration_dir,
        ci_result_path=iteration_dir / "ci-result.json",
        state_path=iteration_dir / "state.json",
        metrics_path=iteration_dir / "metrics.json",
        review_path=iteration_dir / "review.md",
        bundle_json=(bundle_dir / f"bundle-{iteration_dir.name}.json") if bundle_dir else None,
        bundle_md=(bundle_dir / f"bundle-{iteration_dir.name}.md") if bundle_dir else None,
    )
