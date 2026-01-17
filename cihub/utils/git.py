"""Git-related utilities."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from cihub.utils.exec_utils import (
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)
from cihub.utils.filesystem import FileSystem, RealFileSystem
from cihub.utils.paths import validate_repo_path

GIT_REMOTE_RE = re.compile(r"(?:github\.com[:/])(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")


class GitClient(Protocol):
    """Protocol for running git commands."""

    def run(self, args: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        """Run git with the provided arguments."""


class RealGitClient:
    """Real git client backed by safe_run."""

    def __init__(
        self,
        resolver: Callable[[str], str] = resolve_executable,
        runner: Callable[..., subprocess.CompletedProcess[str]] = safe_run,
    ) -> None:
        self._resolver = resolver
        self._runner = runner

    def run(self, args: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        git_bin = self._resolver("git")
        return self._runner([git_bin, *args], cwd=cwd, timeout=timeout, check=True)


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


def get_git_remote(
    repo_path: Path,
    *,
    fs: FileSystem | None = None,
    git: GitClient | None = None,
) -> str | None:
    """Get the origin remote URL for a repository.

    Args:
        repo_path: Path to the repository.
        fs: Optional filesystem abstraction for existence checks.
        git: Optional git client abstraction for running commands.

    Returns:
        The remote URL or None if not found.
    """
    try:
        fs = fs or RealFileSystem()
        git = git or RealGitClient()
        # Validate repo path to prevent path traversal
        validated_path = validate_repo_path(repo_path)
        # Treat repo_path as the repository root. Avoid discovering a parent repo
        # when repo_path is just a directory inside another git worktree.
        if not fs.exists(validated_path / ".git"):
            return None
        result = git.run(["config", "--get", "remote.origin.url"], validated_path, TIMEOUT_QUICK)
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, CommandNotFoundError, CommandTimeoutError, ValueError):
        return None


def get_git_branch(
    repo_path: Path,
    *,
    fs: FileSystem | None = None,
    git: GitClient | None = None,
) -> str | None:
    """Get the current branch name for a repository.

    Args:
        repo_path: Path to the repository.
        fs: Optional filesystem abstraction for existence checks.
        git: Optional git client abstraction for running commands.

    Returns:
        The branch name or None if not found.
    """
    try:
        fs = fs or RealFileSystem()
        git = git or RealGitClient()
        # Validate repo path to prevent path traversal
        validated_path = validate_repo_path(repo_path)
        # Treat repo_path as the repository root. Avoid discovering a parent repo
        # when repo_path is just a directory inside another git worktree.
        if not fs.exists(validated_path / ".git"):
            return None
        result = git.run(["symbolic-ref", "--short", "HEAD"], validated_path, TIMEOUT_QUICK)
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, CommandNotFoundError, CommandTimeoutError, ValueError):
        return None
