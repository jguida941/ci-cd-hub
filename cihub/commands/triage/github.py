"""GitHub API client for triage operations.

Encapsulates all GitHub CLI (gh) interactions for fetching run info,
listing runs, downloading artifacts, and fetching logs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    TIMEOUT_NETWORK,
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)


@dataclass
class RunInfo:
    """Information about a GitHub Actions workflow run."""

    run_id: str
    name: str
    status: str
    conclusion: str
    head_branch: str
    head_sha: str
    url: str
    jobs: list[dict[str, Any]]

    @classmethod
    def from_gh_response(cls, data: dict[str, Any], run_id: str) -> RunInfo:
        """Create RunInfo from gh CLI JSON response."""
        return cls(
            run_id=run_id,
            name=data.get("name", ""),
            status=data.get("status", ""),
            conclusion=data.get("conclusion", ""),
            head_branch=data.get("headBranch", ""),
            head_sha=data.get("headSha", ""),
            url=data.get("url", ""),
            jobs=data.get("jobs", []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "run_id": self.run_id,
            "name": self.name,
            "status": self.status,
            "conclusion": self.conclusion,
            "headBranch": self.head_branch,
            "headSha": self.head_sha,
            "url": self.url,
        }


class GitHubRunClient:
    """Encapsulates GitHub CLI interactions for workflow runs.

    This class provides a clean interface for:
    - Fetching run metadata
    - Listing runs with filters
    - Downloading artifacts
    - Fetching failed logs

    Example:
        client = GitHubRunClient(repo="owner/repo")
        run_info = client.fetch_run_info("12345")
        client.download_artifacts("12345", Path("./artifacts"))
    """

    def __init__(self, repo: str | None = None):
        """Initialize GitHub client.

        Args:
            repo: Repository in owner/repo format. If None, uses current repo.
        """
        self.repo = repo or self._detect_repo()

    @staticmethod
    def _detect_repo() -> str | None:
        """Detect current repo from git remote."""
        try:
            result = safe_run(
                ["git", "remote", "get-url", "origin"],
                timeout=TIMEOUT_QUICK,
            )
            if result.returncode != 0:
                return None
            url = result.stdout.strip()
            # Parse owner/repo from various git URL formats
            match = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
            if match:
                return match.group(1).removesuffix(".git")
        except (CommandNotFoundError, CommandTimeoutError):
            pass
        return None

    def fetch_run_info(self, run_id: str) -> RunInfo:
        """Fetch workflow run info via gh CLI.

        Args:
            run_id: GitHub workflow run ID

        Returns:
            RunInfo with run metadata

        Raises:
            RuntimeError: If fetch fails or returns unexpected format
        """
        gh_bin = resolve_executable("gh")
        cmd = [gh_bin, "run", "view", run_id, "--json", "name,status,conclusion,headBranch,headSha,url,jobs"]
        if self.repo:
            cmd.extend(["--repo", self.repo])

        result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch run info: {result.stderr.strip()}")

        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format from gh run view")

        return RunInfo.from_gh_response(data, run_id)

    def fetch_run_info_raw(self, run_id: str) -> dict[str, Any]:
        """Fetch workflow run info as raw dict (for backward compatibility).

        Args:
            run_id: GitHub workflow run ID

        Returns:
            Dict with run metadata from gh CLI
        """
        info = self.fetch_run_info(run_id)
        payload = info.to_dict()
        payload["jobs"] = info.jobs
        return payload

    def list_runs(
        self,
        workflow: str | None = None,
        branch: str | None = None,
        status: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent workflow runs with optional filtering.

        Args:
            workflow: Filter by workflow name
            branch: Filter by branch name
            status: Filter by status (e.g., "failure", "success")
            limit: Maximum number of runs to return

        Returns:
            List of run dicts with databaseId, name, status, etc.
        """
        gh_bin = resolve_executable("gh")
        json_fields = "databaseId,name,status,conclusion,headBranch,createdAt"
        cmd = [gh_bin, "run", "list", "--json", json_fields, "--limit", str(limit)]

        if self.repo:
            cmd.extend(["--repo", self.repo])
        if workflow:
            cmd.extend(["--workflow", workflow])
        if branch:
            cmd.extend(["--branch", branch])
        if status:
            cmd.extend(["--status", status])

        result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to list runs: {result.stderr.strip()}")

        data = json.loads(result.stdout)
        if not isinstance(data, list):
            return []
        return data

    def get_latest_failed_run(
        self,
        workflow: str | None = None,
        branch: str | None = None,
    ) -> str | None:
        """Get the most recent failed workflow run ID.

        Args:
            workflow: Optional workflow name filter
            branch: Optional branch name filter

        Returns:
            Run ID as string, or None if no failed runs found
        """
        try:
            runs = self.list_runs(
                workflow=workflow,
                branch=branch,
                status="failure",
                limit=1,
            )
            if runs and len(runs) > 0:
                return str(runs[0]["databaseId"])
        except (RuntimeError, json.JSONDecodeError, KeyError):
            pass
        return None

    def download_artifacts(self, run_id: str, dest_dir: Path) -> bool:
        """Download workflow artifacts via gh CLI.

        Args:
            run_id: GitHub workflow run ID
            dest_dir: Directory to download artifacts to

        Returns:
            True if artifacts were found and downloaded
        """
        gh_bin = resolve_executable("gh")
        cmd = [gh_bin, "run", "download", run_id, "--dir", str(dest_dir)]
        if self.repo:
            cmd.extend(["--repo", self.repo])

        result = safe_run(cmd, timeout=TIMEOUT_BUILD)  # 600s for large artifacts

        # gh run download returns 0 even if no artifacts, check if anything was downloaded
        if result.returncode != 0:
            return False

        # Check if any files were actually downloaded
        return any(dest_dir.iterdir()) if dest_dir.exists() else False

    def fetch_failed_logs(self, run_id: str) -> str:
        """Fetch failed job logs via gh CLI.

        Args:
            run_id: GitHub workflow run ID

        Returns:
            Log output as string, or empty string if no failures
        """
        gh_bin = resolve_executable("gh")
        cmd = [gh_bin, "run", "view", run_id, "--log-failed"]
        if self.repo:
            cmd.extend(["--repo", self.repo])

        result = safe_run(cmd, timeout=TIMEOUT_NETWORK)
        if result.returncode != 0:
            # May fail if no failures or other issue
            return ""
        return result.stdout


# Module-level functions for backward compatibility
def get_current_repo() -> str | None:
    """Get current repo from git remote."""
    return GitHubRunClient._detect_repo()


def fetch_run_info(run_id: str, repo: str | None) -> dict[str, Any]:
    """Fetch workflow run info via gh CLI."""
    client = GitHubRunClient(repo=repo)
    return client.fetch_run_info_raw(run_id)


def list_runs(
    repo: str | None,
    workflow: str | None = None,
    branch: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """List recent workflow runs with optional filtering."""
    client = GitHubRunClient(repo=repo)
    return client.list_runs(workflow=workflow, branch=branch, limit=limit)


def download_artifacts(run_id: str, repo: str | None, dest_dir: Path) -> bool:
    """Download workflow artifacts via gh CLI. Returns True if artifacts found."""
    client = GitHubRunClient(repo=repo)
    return client.download_artifacts(run_id, dest_dir)


def fetch_failed_logs(run_id: str, repo: str | None) -> str:
    """Fetch failed job logs via gh CLI."""
    client = GitHubRunClient(repo=repo)
    return client.fetch_failed_logs(run_id)


def get_latest_failed_run(
    repo: str | None,
    workflow: str | None = None,
    branch: str | None = None,
) -> str | None:
    """Get the most recent failed workflow run ID."""
    client = GitHubRunClient(repo=repo)
    return client.get_latest_failed_run(workflow=workflow, branch=branch)


__all__ = [
    "GitHubRunClient",
    "RunInfo",
    "download_artifacts",
    "fetch_failed_logs",
    "fetch_run_info",
    "get_current_repo",
    "get_latest_failed_run",
    "list_runs",
]
