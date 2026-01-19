"""Tests for hub_ci linting tool commands.

Split from test_hub_ci.py for better organization.
Tests: cmd_ruff, cmd_ruff_format, cmd_mypy, cmd_black, cmd_yamllint
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
from unittest import mock


class TestCmdRuff:
    """Tests for cmd_ruff command."""

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    @mock.patch("subprocess.run")
    def test_returns_success_when_no_issues(self, mock_subprocess: mock.Mock, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_ruff
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        mock_run.return_value = mock.Mock(stdout="[]", returncode=0)
        mock_subprocess.return_value = mock.Mock(returncode=0)

        args = argparse.Namespace(
            path=".",
            force_exclude=False,
            output=None,
            github_output=False,
        )
        result = cmd_ruff(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 0

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    @mock.patch("subprocess.run")
    def test_returns_failure_when_issues_found(self, mock_subprocess: mock.Mock, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_ruff
        from cihub.exit_codes import EXIT_FAILURE
        from cihub.types import CommandResult

        mock_run.return_value = mock.Mock(
            stdout='[{"code": "E501"}]',
            returncode=0,
        )
        mock_subprocess.return_value = mock.Mock(returncode=1)

        args = argparse.Namespace(
            path=".",
            force_exclude=False,
            output=None,
            github_output=False,
        )
        result = cmd_ruff(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_FAILURE
        assert result.data["issues"] == 1


class TestCmdRuffFormat:
    """Tests for cmd_ruff_format command."""

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_returns_success_when_clean(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_ruff_format
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        mock_run.return_value = mock.Mock(stdout="", stderr="", returncode=0)

        args = argparse.Namespace(
            path=".",
            force_exclude=False,
            output=None,
            github_output=False,
            json=True,  # suppress OutputContext stdout fallback
        )
        result = cmd_ruff_format(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["needs_format"] is False

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_returns_failure_when_needs_formatting(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_ruff_format
        from cihub.exit_codes import EXIT_FAILURE

        mock_run.return_value = mock.Mock(stdout="Would reformat x.py\n", stderr="", returncode=1)

        args = argparse.Namespace(
            path=".",
            force_exclude=False,
            output=None,
            github_output=False,
            json=True,
        )
        result = cmd_ruff_format(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.data["needs_format"] is True


class TestCmdMypy:
    """Tests for cmd_mypy command."""

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_returns_success_when_no_errors(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_mypy
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(stdout="Success: no issues found\n", stderr="", returncode=0)

        args = argparse.Namespace(
            path="cihub",
            ignore_missing_imports=True,
            show_error_codes=True,
            output=None,
            github_output=False,
            json=True,
        )
        result = cmd_mypy(args)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["errors"] == 0

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_counts_errors_from_output(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_mypy
        from cihub.exit_codes import EXIT_FAILURE

        mock_run.return_value = mock.Mock(
            stdout="cihub/x.py:1: error: Incompatible types\ncihub/y.py:2: error: Name defined twice\n",
            stderr="",
            returncode=1,
        )

        args = argparse.Namespace(
            path="cihub",
            ignore_missing_imports=True,
            show_error_codes=True,
            output=None,
            github_output=False,
            json=True,
        )
        result = cmd_mypy(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.data["errors"] == 2


class TestCmdBlack:
    """Tests for cmd_black command."""

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_returns_success_no_issues(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_black
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        mock_run.return_value = mock.Mock(stdout="", stderr="", returncode=0)

        args = argparse.Namespace(
            path=".",
            output=None,
            github_output=False,
        )
        result = cmd_black(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 0

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_counts_would_reformat(self, mock_run: mock.Mock, capsys) -> None:
        from cihub.commands.hub_ci import cmd_black

        mock_run.return_value = mock.Mock(
            stdout="would reformat file1.py\nwould reformat file2.py",
            stderr="",
            returncode=1,
        )

        args = argparse.Namespace(
            path=".",
            output=None,
            github_output=False,
        )
        cmd_black(args)
        captured = capsys.readouterr()
        assert "issues=2" in captured.out


class TestCmdYamllint:
    """Tests for cmd_yamllint command."""

    @mock.patch("cihub.commands.hub_ci.validation.safe_run")
    def test_returns_success_when_clean(self, mock_safe_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_yamllint
        from cihub.exit_codes import EXIT_SUCCESS

        mock_safe_run.return_value = mock.Mock(stdout="", stderr="", returncode=0)
        args = argparse.Namespace(
            config=None,
            paths=["config/defaults.yaml"],
            output=None,
            github_output=False,
            json=True,
        )
        result = cmd_yamllint(args)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 0

    @mock.patch("cihub.commands.hub_ci.validation.safe_run")
    def test_returns_failure_when_issues_found(self, mock_safe_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_yamllint
        from cihub.exit_codes import EXIT_FAILURE

        mock_safe_run.return_value = mock.Mock(
            stdout="config/defaults.yaml:1: [error] syntax error\n",
            stderr="",
            returncode=1,
        )
        args = argparse.Namespace(
            config=None,
            paths=["config/defaults.yaml"],
            output=None,
            github_output=False,
            json=True,
        )
        result = cmd_yamllint(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.data["issues"] == 1
