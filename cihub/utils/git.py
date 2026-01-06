"""Git-related utilities."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from cihub.utils.exec_utils import (
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)
from cihub.utils.paths import validate_repo_path

GIT_REMOTE_RE = re.compile(r"(?:github\.com[:/])(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")


def parse_repo_from_remote(url: str) -> tuple[str | None, str | None]:
    """Parse owner and repo name from a GitHub remote URL.

    Args:
        url: The remote URL to parse.

    Returns:
        A tuple of (owner, repo) or (None, None) if not a valid GitHub URL.
    """
    match = GIT_REMOTE_RE.search(url)
    if not match:
        return None, None
    return match.group("owner"), match.group("repo")


def get_git_remote(repo_path: Path) -> str | None:
    """Get the origin remote URL for a repository.

    Args:
        repo_path: Path to the repository.

    Returns:
        The remote URL or None if not found.
    """
    try:
        # Validate repo path to prevent path traversal
        validated_path = validate_repo_path(repo_path)
        # Treat repo_path as the repository root. Avoid discovering a parent repo
        # when repo_path is just a directory inside another git worktree.
        if not (validated_path / ".git").exists():
            return None
        git_bin = resolve_executable("git")
        result = safe_run(
            [git_bin, "-C", str(validated_path), "config", "--get", "remote.origin.url"],
            timeout=TIMEOUT_QUICK,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, CommandNotFoundError, CommandTimeoutError, ValueError):
        return None


def get_git_branch(repo_path: Path) -> str | None:
    """Get the current branch name for a repository.

    Args:
        repo_path: Path to the repository.

    Returns:
        The branch name or None if not found.
    """
    try:
        # Validate repo path to prevent path traversal
        validated_path = validate_repo_path(repo_path)
        # Treat repo_path as the repository root. Avoid discovering a parent repo
        # when repo_path is just a directory inside another git worktree.
        if not (validated_path / ".git").exists():
            return None
        git_bin = resolve_executable("git")
        result = safe_run(
            [git_bin, "-C", str(validated_path), "symbolic-ref", "--short", "HEAD"],
            timeout=TIMEOUT_QUICK,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, CommandNotFoundError, CommandTimeoutError, ValueError):
        return None
