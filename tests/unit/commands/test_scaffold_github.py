"""Tests for scaffold --github integration."""

# TEST-METRICS:

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from cihub.commands.scaffold import cmd_scaffold
from cihub.types import CommandResult
from cihub.utils.github import (
    check_gh_auth,
    check_gh_installed,
    git_init_and_commit,
)


class TestGitHubUtilities:
    """Test GitHub utility functions."""

    def test_check_gh_installed_returns_tuple(self) -> None:
        """check_gh_installed returns (bool, str) tuple."""
        result = check_gh_installed()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_check_gh_auth_returns_tuple(self) -> None:
        """check_gh_auth returns (bool, str) tuple."""
        result = check_gh_auth()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_git_init_and_commit_basic(self, tmp_path: Path) -> None:
        """git_init_and_commit initializes a git repo."""
        # Create a file to commit
        (tmp_path / "test.txt").write_text("hello")

        success, error = git_init_and_commit(tmp_path, "Test commit")

        assert success is True
        assert error == ""
        assert (tmp_path / ".git").exists()

    def test_git_init_and_commit_empty_dir_fails(self, tmp_path: Path) -> None:
        """git_init_and_commit fails on empty directory (nothing to commit)."""
        success, error = git_init_and_commit(tmp_path, "Test commit")

        # Git init succeeds but commit fails with nothing to commit
        # The function returns error from git commit
        assert success is False or "nothing to commit" in error.lower()


class TestScaffoldGitHubFlags:
    """Test scaffold command with --github flag."""

    def test_scaffold_basic_no_github(self, tmp_path: Path) -> None:
        """Basic scaffold without --github still works."""
        dest = tmp_path / "project"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=False,
            github=False,
            private=False,
            repo_name=None,
            no_init=False,
            no_push=False,
        )

        result = cmd_scaffold(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / "pyproject.toml").exists()
        # Should NOT have CI config without --github
        assert not (dest / ".ci-hub.yml").exists()

    @patch("cihub.commands.scaffold.check_gh_auth")
    def test_scaffold_github_auth_failure(self, mock_auth: MagicMock, tmp_path: Path) -> None:
        """Scaffold --github fails early if not authenticated."""
        mock_auth.return_value = (False, "gh CLI not authenticated")

        dest = tmp_path / "project"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=False,
            github=True,
            private=False,
            repo_name=None,
            no_init=False,
            no_push=False,
        )

        result = cmd_scaffold(args)

        assert result.exit_code != 0
        assert "not authenticated" in result.summary.lower()
        # Should NOT have created any files
        assert not dest.exists()

    @patch("cihub.commands.scaffold.check_gh_auth")
    @patch("cihub.commands.scaffold.get_gh_username")
    @patch("cihub.commands.scaffold.check_repo_exists")
    def test_scaffold_github_repo_exists(
        self,
        mock_exists: MagicMock,
        mock_username: MagicMock,
        mock_auth: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Scaffold --github fails if repo already exists."""
        mock_auth.return_value = (True, "")
        mock_username.return_value = "testuser"
        mock_exists.return_value = True

        dest = tmp_path / "my-project"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=False,
            github=True,
            private=False,
            repo_name=None,
            no_init=False,
            no_push=False,
        )

        result = cmd_scaffold(args)

        assert result.exit_code != 0
        assert "already exists" in result.summary.lower()
        assert result.suggestions is not None
        assert len(result.suggestions) > 0

    @patch("cihub.commands.scaffold.check_gh_auth")
    @patch("cihub.commands.scaffold.get_gh_username")
    @patch("cihub.commands.scaffold.check_repo_exists")
    @patch("cihub.commands.scaffold.git_init_and_commit")
    @patch("cihub.commands.scaffold.create_github_repo")
    @patch("cihub.commands.scaffold._run_init_for_scaffold")
    def test_scaffold_github_full_flow(
        self,
        mock_init: MagicMock,
        mock_create: MagicMock,
        mock_git: MagicMock,
        mock_exists: MagicMock,
        mock_username: MagicMock,
        mock_auth: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Scaffold --github runs the full flow when all checks pass."""
        mock_auth.return_value = (True, "")
        mock_username.return_value = "testuser"
        mock_exists.return_value = False
        mock_init.return_value = CommandResult(exit_code=0, summary="OK", files_generated=[])
        mock_git.return_value = (True, "")
        mock_create.return_value = (True, "https://github.com/testuser/my-project", "")

        dest = tmp_path / "my-project"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=False,
            github=True,
            private=False,
            repo_name=None,
            no_init=False,
            no_push=False,
        )

        result = cmd_scaffold(args)

        assert result.exit_code == 0
        assert "github.com" in result.summary.lower()
        assert result.data.get("github_url") == "https://github.com/testuser/my-project"

        # Verify the flow was executed
        mock_init.assert_called_once()
        mock_git.assert_called_once()
        mock_create.assert_called_once()

    @patch("cihub.commands.scaffold.check_gh_auth")
    @patch("cihub.commands.scaffold.get_gh_username")
    @patch("cihub.commands.scaffold.check_repo_exists")
    @patch("cihub.commands.scaffold.git_init_and_commit")
    @patch("cihub.commands.scaffold.create_github_repo")
    @patch("cihub.commands.scaffold._run_init_for_scaffold")
    def test_scaffold_github_no_init_skips_init(
        self,
        mock_init: MagicMock,
        mock_create: MagicMock,
        mock_git: MagicMock,
        mock_exists: MagicMock,
        mock_username: MagicMock,
        mock_auth: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Scaffold --github --no-init skips the init step."""
        mock_auth.return_value = (True, "")
        mock_username.return_value = "testuser"
        mock_exists.return_value = False
        mock_git.return_value = (True, "")
        mock_create.return_value = (True, "https://github.com/testuser/my-project", "")

        dest = tmp_path / "my-project"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=False,
            github=True,
            private=False,
            repo_name=None,
            no_init=True,  # Skip init
            no_push=False,
        )

        result = cmd_scaffold(args)

        assert result.exit_code == 0
        # init should NOT have been called
        mock_init.assert_not_called()

    @patch("cihub.commands.scaffold.check_gh_auth")
    @patch("cihub.commands.scaffold.get_gh_username")
    @patch("cihub.commands.scaffold.check_repo_exists")
    @patch("cihub.commands.scaffold.git_init_and_commit")
    @patch("cihub.commands.scaffold.create_github_repo")
    @patch("cihub.commands.scaffold._run_init_for_scaffold")
    def test_scaffold_github_custom_repo_name(
        self,
        mock_init: MagicMock,
        mock_create: MagicMock,
        mock_git: MagicMock,
        mock_exists: MagicMock,
        mock_username: MagicMock,
        mock_auth: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Scaffold --github --repo-name uses custom name."""
        mock_auth.return_value = (True, "")
        mock_username.return_value = "testuser"
        mock_exists.return_value = False
        mock_init.return_value = CommandResult(exit_code=0, summary="OK", files_generated=[])
        mock_git.return_value = (True, "")
        mock_create.return_value = (True, "https://github.com/testuser/custom-name", "")

        dest = tmp_path / "local-dir"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=False,
            github=True,
            private=False,
            repo_name="custom-name",  # Custom repo name
            no_init=False,
            no_push=False,
        )

        result = cmd_scaffold(args)

        assert result.exit_code == 0
        # create_github_repo should be called with custom name
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][1] == "custom-name"


class TestScaffoldGitHubLanguageDetection:
    """Test language detection for scaffold types."""

    def test_python_scaffolds_use_python_language(self) -> None:
        """Python scaffold types should use python language for init."""
        from cihub.commands.scaffold import _get_language_for_scaffold

        assert _get_language_for_scaffold("python-pyproject") == "python"
        assert _get_language_for_scaffold("python-setup") == "python"
        assert _get_language_for_scaffold("python-src-layout") == "python"

    def test_java_scaffolds_use_java_language(self) -> None:
        """Java scaffold types should use java language for init."""
        from cihub.commands.scaffold import _get_language_for_scaffold

        assert _get_language_for_scaffold("java-maven") == "java"
        assert _get_language_for_scaffold("java-gradle") == "java"
        assert _get_language_for_scaffold("java-multi-module") == "java"

    def test_monorepo_defaults_to_java(self) -> None:
        """Monorepo scaffold should default to java language."""
        from cihub.commands.scaffold import _get_language_for_scaffold

        assert _get_language_for_scaffold("monorepo") == "java"
