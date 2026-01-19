"""GitHub repository utilities for scaffold and setup commands."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)


def check_gh_installed() -> tuple[bool, str]:
    """Check if gh CLI is installed.

    Returns:
        (success, error_message)
    """
    try:
        resolve_executable("gh")
        return True, ""
    except CommandNotFoundError:
        return False, "gh CLI not found. Install from https://cli.github.com"


def check_gh_auth() -> tuple[bool, str]:
    """Check if gh CLI is authenticated.

    Returns:
        (success, error_message)
    """
    installed, err = check_gh_installed()
    if not installed:
        return False, err

    try:
        result = safe_run(
            ["gh", "auth", "status"],
            timeout=TIMEOUT_QUICK,
        )
        if result.returncode != 0:
            return False, "gh CLI not authenticated. Run: gh auth login"
        return True, ""
    except CommandTimeoutError:
        return False, "gh auth check timed out"
    except Exception as exc:
        return False, f"gh auth check failed: {exc}"


def get_gh_username() -> str | None:
    """Get the authenticated GitHub username.

    Returns:
        Username or None if not authenticated.
    """
    try:
        result = safe_run(
            ["gh", "api", "user", "--jq", ".login"],
            timeout=TIMEOUT_QUICK,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None


def check_repo_exists(owner: str, name: str) -> bool:
    """Check if a GitHub repo already exists.

    Args:
        owner: GitHub username or organization
        name: Repository name

    Returns:
        True if repo exists, False otherwise.
    """
    try:
        result = safe_run(
            ["gh", "repo", "view", f"{owner}/{name}", "--json", "name"],
            timeout=TIMEOUT_QUICK,
        )
        return result.returncode == 0
    except Exception:
        return False


def git_init_and_commit(
    path: Path,
    message: str = "Initial commit",
) -> tuple[bool, str]:
    """Initialize git repo and create initial commit.

    Args:
        path: Directory to initialize
        message: Commit message

    Returns:
        (success, error_message)
    """
    try:
        # git init
        result = safe_run(
            ["git", "init"],
            cwd=path,
            timeout=TIMEOUT_QUICK,
        )
        if result.returncode != 0:
            return False, f"git init failed: {result.stderr}"

        # git add -A
        result = safe_run(
            ["git", "add", "-A"],
            cwd=path,
            timeout=TIMEOUT_QUICK,
        )
        if result.returncode != 0:
            return False, f"git add failed: {result.stderr}"

        # git commit
        result = safe_run(
            ["git", "commit", "-m", message],
            cwd=path,
            timeout=TIMEOUT_QUICK,
        )
        if result.returncode != 0:
            return False, f"git commit failed: {result.stderr}"

        return True, ""

    except CommandTimeoutError as exc:
        return False, f"git operation timed out: {exc}"
    except Exception as exc:
        return False, f"git operation failed: {exc}"


def create_github_repo(
    path: Path,
    name: str,
    *,
    private: bool = False,
    push: bool = True,
    description: str = "",
) -> tuple[bool, str, str]:
    """Create GitHub repo and optionally push.

    Args:
        path: Local repo directory
        name: GitHub repo name
        private: Create private repo
        push: Push after creating
        description: Repo description

    Returns:
        (success, repo_url, error_message)
    """
    try:
        # Build command
        cmd = ["gh", "repo", "create", name]
        if private:
            cmd.append("--private")
        else:
            cmd.append("--public")

        cmd.extend(["--source", str(path)])

        if push:
            cmd.append("--push")

        if description:
            cmd.extend(["--description", description])

        result = safe_run(
            cmd,
            cwd=path,
            timeout=TIMEOUT_NETWORK,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            # Check for common errors
            if "already exists" in stderr.lower():
                return False, "", f"Repository '{name}' already exists on GitHub"
            return False, "", f"gh repo create failed: {stderr}"

        # Extract repo URL from stdout
        repo_url = result.stdout.strip()
        if not repo_url.startswith("http"):
            # Try to construct URL
            owner = get_gh_username() or "unknown"
            repo_url = f"https://github.com/{owner}/{name}"

        return True, repo_url, ""

    except CommandTimeoutError:
        return False, "", "GitHub operation timed out (network issue?)"
    except Exception as exc:
        return False, "", f"GitHub operation failed: {exc}"


def set_repo_variables(
    repo: str,
    variables: Mapping[str, str],
) -> tuple[bool, list[str], list[dict[str, str]]]:
    """Set GitHub Actions repo variables via gh CLI."""
    messages: list[str] = []
    problems: list[dict[str, str]] = []
    if not repo:
        problems.append(
            {
                "severity": "warning",
                "message": "Repo is required to set GitHub variables",
                "code": "CIHUB-HUB-VARS-NO-REPO",
            }
        )
        return False, messages, problems

    ok, err = check_gh_auth()
    if not ok:
        problems.append(
            {
                "severity": "warning",
                "message": err,
                "code": "CIHUB-HUB-VARS-NO-GH",
            }
        )
        return False, messages, problems

    success = True
    for name, value in variables.items():
        if not name or not value:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Skipping empty variable: {name or '<missing>'}",
                    "code": "CIHUB-HUB-VARS-EMPTY",
                }
            )
            success = False
            continue
        try:
            result = safe_run(
                ["gh", "variable", "set", name, "-R", repo, "-b", value],
                timeout=TIMEOUT_NETWORK,
            )
        except CommandNotFoundError:
            problems.append(
                {
                    "severity": "warning",
                    "message": "gh CLI not found. Install from https://cli.github.com",
                    "code": "CIHUB-HUB-VARS-NO-GH",
                }
            )
            return False, messages, problems
        except CommandTimeoutError as exc:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"gh variable set timed out: {exc}",
                    "code": "CIHUB-HUB-VARS-TIMEOUT",
                }
            )
            success = False
            continue
        if result.returncode != 0:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"gh variable set failed for {name}: {result.stderr.strip()}",
                    "code": "CIHUB-HUB-VARS-FAILED",
                }
            )
            success = False
            continue
        messages.append(f"Set {name} on {repo}")
    return success, messages, problems


def push_to_github(path: Path, branch: str = "main") -> tuple[bool, str]:
    """Push local commits to GitHub.

    Args:
        path: Local repo directory
        branch: Branch to push

    Returns:
        (success, error_message)
    """
    try:
        result = safe_run(
            ["git", "push", "-u", "origin", branch],
            cwd=path,
            timeout=TIMEOUT_NETWORK,
        )
        if result.returncode != 0:
            return False, f"git push failed: {result.stderr}"
        return True, ""
    except CommandTimeoutError:
        return False, "git push timed out (network issue?)"
    except Exception as exc:
        return False, f"git push failed: {exc}"
