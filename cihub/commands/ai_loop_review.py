"""Review step helpers for the AI loop."""

from __future__ import annotations

import os
from pathlib import Path

from cihub.commands.ai_loop_types import LoopSettings, LoopState
from cihub.utils.exec_utils import TIMEOUT_NETWORK, CommandNotFoundError, CommandTimeoutError, safe_run


def maybe_run_review(settings: LoopSettings, iteration_dir: Path, state: LoopState) -> None:
    if not settings.review_command:
        return
    env = os.environ.copy()
    env["CIHUB_AI_LOOP_ITERATION"] = str(state.iteration)
    env["CIHUB_AI_LOOP_SESSION"] = str(iteration_dir.parent)
    env["CIHUB_AI_LOOP_OUTPUT_DIR"] = str(iteration_dir)
    env["CIHUB_AI_LOOP_REPO"] = str(settings.repo_path)
    cmd = ["/bin/sh", "-c", settings.review_command]
    try:
        result = safe_run(cmd, cwd=settings.repo_path, timeout=TIMEOUT_NETWORK, env=env)
    except (CommandNotFoundError, CommandTimeoutError) as exc:
        iteration_dir.joinpath("review.md").write_text(f"Review command failed: {exc}\n", encoding="utf-8")
        return
    content = (result.stdout or "") + (result.stderr or "")
    if not content.strip():
        content = "(review command produced no output)\n"
    iteration_dir.joinpath("review.md").write_text(content, encoding="utf-8")
