"""Tests for hub_ci badge commands.

Split from test_hub_ci.py for better organization.
Tests: cmd_badges, cmd_badges_commit
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
from pathlib import Path
from unittest import mock


class TestCmdBadges:
    """Tests for cmd_badges command."""

    @mock.patch("cihub.commands.hub_ci.badges._compare_badges")
    @mock.patch("cihub.commands.hub_ci.badges.badge_tools.main")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_check_mode_success(
        self,
        mock_root: mock.Mock,
        mock_main: mock.Mock,
        mock_compare: mock.Mock,
        tmp_path: Path,
    ) -> None:
        from cihub.commands.hub_ci import cmd_badges
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        (tmp_path / "badges").mkdir()
        mock_main.return_value = 0
        mock_compare.return_value = []

        args = argparse.Namespace(
            check=True,
            config=None,
            output_dir=None,
            artifacts_dir=None,
            ruff_issues=None,
            mutation_score=None,
            mypy_errors=None,
            black_issues=None,
            black_status=None,
            zizmor_sarif=None,
        )
        result = cmd_badges(args)

        assert result.exit_code == EXIT_SUCCESS
        assert mock_main.call_count == 1
        env = mock_main.call_args.kwargs["env"]
        assert env["UPDATE_BADGES"] == "true"
        assert "BADGE_OUTPUT_DIR" in env

    @mock.patch("cihub.commands.hub_ci.badges._compare_badges")
    @mock.patch("cihub.commands.hub_ci.badges.badge_tools.main")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_check_mode_detects_drift(
        self,
        mock_root: mock.Mock,
        mock_main: mock.Mock,
        mock_compare: mock.Mock,
        tmp_path: Path,
    ) -> None:
        from cihub.commands.hub_ci import cmd_badges
        from cihub.exit_codes import EXIT_FAILURE

        mock_root.return_value = tmp_path
        (tmp_path / "badges").mkdir()
        mock_main.return_value = 0
        mock_compare.return_value = ["diff: ruff.json"]

        args = argparse.Namespace(
            check=True,
            config=None,
            output_dir=None,
            artifacts_dir=None,
            ruff_issues=None,
            mutation_score=None,
            mypy_errors=None,
            black_issues=None,
            black_status=None,
            zizmor_sarif=None,
        )
        result = cmd_badges(args)

        assert result.exit_code == EXIT_FAILURE

    @mock.patch("cihub.commands.hub_ci.badges.badge_tools.main")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_updates_badges_with_output_dir(
        self,
        mock_root: mock.Mock,
        mock_main: mock.Mock,
        tmp_path: Path,
    ) -> None:
        from cihub.commands.hub_ci import cmd_badges
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        mock_main.return_value = 0

        output_dir = tmp_path / "badges-out"
        args = argparse.Namespace(
            check=False,
            config=None,
            output_dir=str(output_dir),
            artifacts_dir=None,
            ruff_issues=0,
            mutation_score=88.5,
            mypy_errors=2,
            black_issues=None,
            black_status=None,
            zizmor_sarif=None,
        )
        result = cmd_badges(args)

        assert result.exit_code == EXIT_SUCCESS
        env = mock_main.call_args.kwargs["env"]
        assert env["BADGE_OUTPUT_DIR"] == str(output_dir.resolve())
        assert env["RUFF_ISSUES"] == "0"
        assert env["MUTATION_SCORE"] == "88.5"
        assert env["MYPY_ERRORS"] == "2"


class TestCmdBadgesCommit:
    """Tests for cmd_badges_commit command."""

    @mock.patch("cihub.commands.hub_ci.badges._run_command")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_no_changes(self, mock_root: mock.Mock, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_badges_commit
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        mock_run.side_effect = [
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
        ]

        result = cmd_badges_commit(argparse.Namespace())
        assert result.exit_code == EXIT_SUCCESS
        assert mock_run.call_count == 4

    @mock.patch("cihub.commands.hub_ci.badges._run_command")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_commits_and_pushes(self, mock_root: mock.Mock, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_badges_commit
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        mock_run.side_effect = [
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=1),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
        ]

        result = cmd_badges_commit(argparse.Namespace())
        assert result.exit_code == EXIT_SUCCESS
        assert mock_run.call_count == 6
