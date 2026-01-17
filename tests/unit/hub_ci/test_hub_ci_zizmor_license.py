"""Tests for hub_ci zizmor and license commands.

Split from test_hub_ci.py for better organization.
Tests: cmd_zizmor_run, cmd_zizmor_check, cmd_license_check
(Separate from test_hub_ci_security.py which covers bandit/pip-audit/OWASP in depth)
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import pytest


class TestCmdZizmorRun:
    """Tests for cmd_zizmor_run command."""

    @mock.patch("subprocess.run")
    def test_writes_sarif_on_success(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout='{"runs": [{"results": []}]}',
        )
        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()
        assert "runs" in output_path.read_text()

    @mock.patch("subprocess.run")
    def test_writes_sarif_on_findings(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        """Non-zero exit preserves SARIF when stdout is valid."""
        from cihub.commands.hub_ci import cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        # Even if zizmor outputs findings, we keep valid SARIF on non-zero exit
        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout='{"runs": [{"results": [{"level": "error"}]}]}',
        )
        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()
        assert output_path.read_text() == '{"runs": [{"results": [{"level": "error"}]}]}'

    @mock.patch("subprocess.run")
    def test_writes_empty_sarif_on_failure(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import EMPTY_SARIF, cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout="",
        )
        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()
        assert output_path.read_text() == EMPTY_SARIF

    @mock.patch("subprocess.run", side_effect=FileNotFoundError)
    def test_writes_empty_sarif_when_zizmor_missing(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import EMPTY_SARIF, cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()
        assert output_path.read_text() == EMPTY_SARIF


class TestCmdZizmorCheck:
    """Tests for cmd_zizmor_check command."""

    @pytest.mark.parametrize(
        "sarif_exists,sarif_content,expected_exit",
        [
            (False, None, "EXIT_FAILURE"),
            (True, {"runs": [{"results": []}]}, "EXIT_SUCCESS"),
            (True, {"runs": [{"results": [{"level": "error"}]}]}, "EXIT_FAILURE"),
            (True, {"runs": [{"results": [{"level": "warning"}]}]}, "EXIT_FAILURE"),
        ],
        ids=["missing_sarif", "no_findings", "has_error", "has_warning"],
    )
    def test_zizmor_check_scenarios(
        self, tmp_path: Path, sarif_exists: bool, sarif_content: dict | None, expected_exit: str
    ) -> None:
        """Property: cmd_zizmor_check handles SARIF scenarios correctly."""
        from cihub.commands.hub_ci import cmd_zizmor_check
        from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS

        sarif_path = tmp_path / "zizmor.sarif"
        if sarif_exists and sarif_content is not None:
            sarif_path.write_text(json.dumps(sarif_content))

        args = argparse.Namespace(
            sarif=str(sarif_path),
            summary=None,
            github_summary=False,
        )
        result = cmd_zizmor_check(args)

        expected = EXIT_SUCCESS if expected_exit == "EXIT_SUCCESS" else EXIT_FAILURE
        assert result.exit_code == expected


class TestCmdLicenseCheck:
    """Tests for cmd_license_check command."""

    @mock.patch("cihub.commands.hub_ci.release._run_command")
    def test_returns_success_no_copyleft(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_license_check
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            stdout="Name,Version,License\npytest,7.0,MIT\n",
            returncode=0,
        )

        args = argparse.Namespace(summary=None, github_summary=False)
        result = cmd_license_check(args)
        assert result.exit_code == EXIT_SUCCESS

    @mock.patch("cihub.commands.hub_ci.release._run_command")
    def test_warns_on_copyleft(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_license_check
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            stdout="Name,Version,License\nsome-pkg,1.0,GPL-3.0\n",
            returncode=0,
        )

        args = argparse.Namespace(summary=None, github_summary=False)
        result = cmd_license_check(args)
        # Still returns success but warns
        assert result.exit_code == EXIT_SUCCESS
        assert any("copyleft" in p["message"].lower() for p in result.problems)

    @mock.patch("cihub.commands.hub_ci.release._run_command", side_effect=FileNotFoundError)
    def test_skips_when_pip_licenses_missing(self, _mock_run: mock.Mock) -> None:
        """Missing pip-licenses should not crash the command."""
        from cihub.commands.hub_ci import cmd_license_check
        from cihub.exit_codes import EXIT_SUCCESS

        args = argparse.Namespace(summary=None, github_summary=False)
        result = cmd_license_check(args)
        assert result.exit_code == EXIT_SUCCESS
        assert any("pip-licenses" in p["message"].lower() for p in result.problems)
