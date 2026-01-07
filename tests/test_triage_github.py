"""Unit tests for triage GitHub client module.

Tests for GitHubRunClient class and related helper functions.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cihub.commands.triage.github import (
    GitHubRunClient,
    RunInfo,
    download_artifacts,
    fetch_failed_logs,
    fetch_run_info,
    get_current_repo,
    get_latest_failed_run,
    list_runs,
)


class TestRunInfo:
    """Unit tests for RunInfo dataclass."""

    def test_from_gh_response_parses_all_fields(self) -> None:
        """Test RunInfo.from_gh_response parses all expected fields."""
        data = {
            "name": "CI Workflow",
            "status": "completed",
            "conclusion": "failure",
            "headBranch": "main",
            "headSha": "abc123",
            "url": "https://github.com/owner/repo/actions/runs/123",
            "jobs": [{"name": "test", "conclusion": "failure"}],
        }

        info = RunInfo.from_gh_response(data, "123")

        assert info.run_id == "123"
        assert info.name == "CI Workflow"
        assert info.status == "completed"
        assert info.conclusion == "failure"
        assert info.head_branch == "main"
        assert info.head_sha == "abc123"
        assert info.url == "https://github.com/owner/repo/actions/runs/123"
        assert len(info.jobs) == 1

    def test_from_gh_response_handles_missing_fields(self) -> None:
        """Test RunInfo handles missing optional fields gracefully."""
        data = {}  # Empty response

        info = RunInfo.from_gh_response(data, "456")

        assert info.run_id == "456"
        assert info.name == ""
        assert info.status == ""
        assert info.conclusion == ""
        assert info.head_branch == ""
        assert info.head_sha == ""
        assert info.url == ""
        assert info.jobs == []

    def test_to_dict_serializes_correctly(self) -> None:
        """Test RunInfo.to_dict returns serializable dict."""
        info = RunInfo(
            run_id="123",
            name="Test",
            status="completed",
            conclusion="success",
            head_branch="main",
            head_sha="abc",
            url="https://example.com",
            jobs=[],
        )

        result = info.to_dict()

        assert result["run_id"] == "123"
        assert result["name"] == "Test"
        assert result["headBranch"] == "main"  # Uses camelCase for compatibility
        assert "jobs" not in result  # Jobs excluded from serialization


class TestGitHubRunClient:
    """Unit tests for GitHubRunClient class."""

    def test_init_with_explicit_repo(self) -> None:
        """Test client initialization with explicit repo."""
        client = GitHubRunClient(repo="owner/repo")
        assert client.repo == "owner/repo"

    def test_init_detects_repo_from_git(self, monkeypatch) -> None:
        """Test client auto-detects repo from git remote."""
        mock_result = MagicMock(returncode=0, stdout="git@github.com:owner/repo.git\n")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)

        client = GitHubRunClient(repo=None)

        assert client.repo == "owner/repo"

    def test_detect_repo_handles_https_url(self, monkeypatch) -> None:
        """Test repo detection handles HTTPS URLs."""
        mock_result = MagicMock(returncode=0, stdout="https://github.com/owner/repo.git\n")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)

        repo = GitHubRunClient._detect_repo()

        assert repo == "owner/repo"

    def test_detect_repo_returns_none_on_failure(self, monkeypatch) -> None:
        """Test repo detection returns None when git fails."""
        mock_result = MagicMock(returncode=1, stdout="")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)

        repo = GitHubRunClient._detect_repo()

        assert repo is None

    def test_fetch_run_info_success(self, monkeypatch) -> None:
        """Test successful run info fetch."""
        mock_result = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "name": "CI",
                    "status": "completed",
                    "conclusion": "success",
                    "headBranch": "main",
                    "headSha": "abc123",
                    "url": "https://github.com/owner/repo/actions/runs/123",
                    "jobs": [],
                }
            ),
            stderr="",
        )
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        info = client.fetch_run_info("123")

        assert info.run_id == "123"
        assert info.name == "CI"
        assert info.conclusion == "success"

    def test_fetch_run_info_raises_on_failure(self, monkeypatch) -> None:
        """Test fetch_run_info raises RuntimeError on gh failure."""
        mock_result = MagicMock(returncode=1, stdout="", stderr="Not found")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")

        with pytest.raises(RuntimeError, match="Failed to fetch run info"):
            client.fetch_run_info("123")

    def test_list_runs_with_filters(self, monkeypatch) -> None:
        """Test run listing with workflow/branch filters."""
        captured_cmd = []

        def mock_safe_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    [
                        {"databaseId": 123, "name": "CI", "status": "completed"},
                        {"databaseId": 124, "name": "CI", "status": "completed"},
                    ]
                ),
                stderr="",
            )

        monkeypatch.setattr("cihub.commands.triage.github.safe_run", mock_safe_run)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        runs = client.list_runs(workflow="ci.yml", branch="main", limit=5)

        assert len(runs) == 2
        assert runs[0]["databaseId"] == 123
        # Verify filters were passed
        assert "--workflow" in captured_cmd
        assert "--branch" in captured_cmd

    def test_list_runs_returns_empty_on_invalid_response(self, monkeypatch) -> None:
        """Test list_runs returns empty list on non-list response."""
        mock_result = MagicMock(returncode=0, stdout="{}", stderr="")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        runs = client.list_runs()

        assert runs == []

    def test_download_artifacts_success(self, monkeypatch, tmp_path: Path) -> None:
        """Test successful artifact download."""
        mock_result = MagicMock(returncode=0)
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        # Create a file to simulate download
        (tmp_path / "artifact.txt").write_text("test")

        client = GitHubRunClient(repo="owner/repo")
        result = client.download_artifacts("123", tmp_path)

        assert result is True

    def test_download_artifacts_returns_false_on_failure(self, monkeypatch, tmp_path: Path) -> None:
        """Test download_artifacts returns False on gh failure."""
        mock_result = MagicMock(returncode=1)
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        result = client.download_artifacts("123", tmp_path)

        assert result is False

    def test_fetch_failed_logs_success(self, monkeypatch) -> None:
        """Test successful failed logs fetch."""
        mock_result = MagicMock(
            returncode=0,
            stdout="test-job\ttest-step\t2024-01-01 ##[error]Test failed",
        )
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        logs = client.fetch_failed_logs("123")

        assert "##[error]" in logs

    def test_fetch_failed_logs_returns_empty_on_failure(self, monkeypatch) -> None:
        """Test fetch_failed_logs returns empty string on failure."""
        mock_result = MagicMock(returncode=1, stdout="")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        logs = client.fetch_failed_logs("123")

        assert logs == ""

    def test_get_latest_failed_run_success(self, monkeypatch) -> None:
        """Test get_latest_failed_run returns most recent failed run."""
        mock_result = MagicMock(returncode=0, stdout=json.dumps([{"databaseId": 999}]))
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        run_id = client.get_latest_failed_run()

        assert run_id == "999"

    def test_get_latest_failed_run_returns_none_when_no_failures(self, monkeypatch) -> None:
        """Test get_latest_failed_run returns None when no failures found."""
        mock_result = MagicMock(returncode=0, stdout="[]")
        monkeypatch.setattr("cihub.commands.triage.github.safe_run", lambda *args, **kwargs: mock_result)
        monkeypatch.setattr("cihub.commands.triage.github.resolve_executable", lambda x: "gh")

        client = GitHubRunClient(repo="owner/repo")
        run_id = client.get_latest_failed_run()

        assert run_id is None


class TestModuleLevelFunctions:
    """Tests for backward-compatible module-level functions."""

    def test_get_current_repo_delegates_to_client(self, monkeypatch) -> None:
        """Test get_current_repo uses GitHubRunClient._detect_repo."""
        monkeypatch.setattr(GitHubRunClient, "_detect_repo", staticmethod(lambda: "owner/repo"))

        result = get_current_repo()

        assert result == "owner/repo"

    def test_fetch_run_info_delegates_to_client(self, monkeypatch) -> None:
        """Test fetch_run_info creates client and delegates."""
        mock_instance = MagicMock()
        mock_instance.fetch_run_info_raw.return_value = {"run_id": "123"}

        def mock_init(self, repo=None):
            self.repo = repo
            self.fetch_run_info_raw = mock_instance.fetch_run_info_raw

        monkeypatch.setattr(GitHubRunClient, "__init__", mock_init)

        result = fetch_run_info("123", "owner/repo")

        assert result["run_id"] == "123"

    def test_list_runs_delegates_to_client(self, monkeypatch) -> None:
        """Test list_runs creates client and delegates."""
        mock_instance = MagicMock()
        mock_instance.list_runs.return_value = [{"databaseId": 1}]

        def mock_init(self, repo=None):
            self.repo = repo
            self.list_runs = mock_instance.list_runs

        monkeypatch.setattr(GitHubRunClient, "__init__", mock_init)

        result = list_runs("owner/repo", workflow="ci.yml")

        assert len(result) == 1

    def test_download_artifacts_delegates_to_client(self, monkeypatch, tmp_path: Path) -> None:
        """Test download_artifacts creates client and delegates."""
        mock_instance = MagicMock()
        mock_instance.download_artifacts.return_value = True

        def mock_init(self, repo=None):
            self.repo = repo
            self.download_artifacts = mock_instance.download_artifacts

        monkeypatch.setattr(GitHubRunClient, "__init__", mock_init)

        result = download_artifacts("123", "owner/repo", tmp_path)

        assert result is True

    def test_fetch_failed_logs_delegates_to_client(self, monkeypatch) -> None:
        """Test fetch_failed_logs creates client and delegates."""
        mock_instance = MagicMock()
        mock_instance.fetch_failed_logs.return_value = "log output"

        def mock_init(self, repo=None):
            self.repo = repo
            self.fetch_failed_logs = mock_instance.fetch_failed_logs

        monkeypatch.setattr(GitHubRunClient, "__init__", mock_init)

        result = fetch_failed_logs("123", "owner/repo")

        assert result == "log output"

    def test_get_latest_failed_run_delegates_to_client(self, monkeypatch) -> None:
        """Test get_latest_failed_run creates client and delegates."""
        mock_instance = MagicMock()
        mock_instance.get_latest_failed_run.return_value = "999"

        def mock_init(self, repo=None):
            self.repo = repo
            self.get_latest_failed_run = mock_instance.get_latest_failed_run

        monkeypatch.setattr(GitHubRunClient, "__init__", mock_init)

        result = get_latest_failed_run("owner/repo", workflow="ci.yml", branch="main")

        assert result == "999"
