"""Guardrails and git helpers for the AI loop."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from cihub.commands.ai_loop_types import AI_LOOP_CONFIG, LoopSettings
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.git import get_git_branch


def get_worktree_changes(repo_path: Path) -> list[str]:
    try:
        result = safe_run(["git", "status", "--porcelain"], cwd=repo_path, timeout=TIMEOUT_QUICK)
    except (CommandNotFoundError, CommandTimeoutError):
        return []
    if result.returncode != 0:
        return []
    files = []
    for line in result.stdout.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path:
            files.append(path.strip())
    return files


def check_guardrails(changed_files: list[str]) -> dict[str, str] | None:
    if not changed_files:
        return None
    forbidden = AI_LOOP_CONFIG.get("forbidden_paths", [])
    for path in changed_files:
        for pattern in forbidden:
            if fnmatch.fnmatch(path, pattern):
                return {
                    "message": f"Change touches forbidden path: {path}",
                    "code": "CIHUB-AI-FORBIDDEN-PATH",
                }
    max_files = AI_LOOP_CONFIG.get("max_files_per_iteration", 0)
    if max_files and len(changed_files) > max_files:
        return {
            "message": f"Too many files changed ({len(changed_files)} > {max_files})",
            "code": "CIHUB-AI-TOO-MANY-FILES",
        }
    return None


def commit_changes(repo_path: Path, message: str) -> str | None:
    try:
        result = safe_run(["git", "add", "-A"], cwd=repo_path, timeout=TIMEOUT_QUICK)
    except (CommandNotFoundError, CommandTimeoutError) as exc:
        return f"git add failed: {exc}"
    if result.returncode != 0:
        return f"git add failed: {result.stderr.strip()}"

    try:
        result = safe_run(["git", "commit", "-m", message], cwd=repo_path, timeout=TIMEOUT_QUICK)
    except (CommandNotFoundError, CommandTimeoutError) as exc:
        return f"git commit failed: {exc}"
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "nothing to commit" in stderr.lower():
            return "NO_CHANGES"
        return f"git commit failed: {stderr}"
    return None


def push_iteration(settings: LoopSettings, iteration: int) -> str | None:
    if not settings.push:
        return None
    if settings.commit:
        commit_message = f"{settings.commit_message} {iteration}".strip()
        commit_error = commit_changes(settings.repo_path, commit_message)
        if commit_error:
            if commit_error == "NO_CHANGES":
                return "No changes to commit"
            return commit_error
    elif get_worktree_changes(settings.repo_path):
        return "Working tree has changes but --commit is not set"

    cmd = ["git", "push", "-u", settings.push_remote, f"HEAD:{settings.push_branch}"]
    try:
        result = safe_run(cmd, cwd=settings.repo_path, timeout=TIMEOUT_NETWORK)
    except (CommandNotFoundError, CommandTimeoutError) as exc:
        return f"git push failed: {exc}"
    if result.returncode != 0:
        return f"git push failed: {result.stderr.strip()}"
    return None


def get_git_sha(repo_path: Path) -> str | None:
    try:
        result = safe_run(["git", "rev-parse", "HEAD"], cwd=repo_path, timeout=TIMEOUT_QUICK)
    except (CommandNotFoundError, CommandTimeoutError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def get_branch(repo_path: Path) -> str:
    branch = get_git_branch(repo_path)
    return branch or "unknown"


def detect_remote_repo(repo_path: Path) -> str | None:
    try:
        result = safe_run(["git", "remote", "get-url", "origin"], cwd=repo_path, timeout=TIMEOUT_QUICK)
    except (CommandNotFoundError, CommandTimeoutError):
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if "github.com" not in url:
        return None
    parts = url.split("github.com")[-1].strip()
    parts = parts.lstrip(":/")
    if parts.endswith(".git"):
        parts = parts[:-4]
    return parts


def is_protected_branch(branch: str) -> bool:
    return branch in {"main", "master"}
