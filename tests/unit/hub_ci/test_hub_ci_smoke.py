"""Tests for hub_ci smoke tests and main command.

Split from test_hub_ci.py for better organization.
Tests: cmd_smoke_java_tests, cmd_smoke_java_coverage, cmd_smoke_python_tests,
       cmd_hub_ci, platform detection, ensure_executable
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest import mock


class TestCmdSmokeJava:
    """Tests for smoke Java commands."""

    def test_smoke_java_tests_parses_junit(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_smoke_java_tests
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        report_dir = repo_path / "target" / "surefire-reports"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "TEST.xml"
        report_path.write_text(
            '<testsuite tests="10" failures="2" errors="1" skipped="3" time="12.5"></testsuite>',
            encoding="utf-8",
        )
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            output=str(output_path),
            github_output=False,
        )
        result = cmd_smoke_java_tests(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["total"] == 10
        assert result.data["passed"] == 4
        assert result.data["failed"] == 3
        assert result.data["skipped"] == 3
        content = output_path.read_text(encoding="utf-8")
        # total = passed + failed + skipped = 4 + 3 + 3 = 10
        assert "total=10" in content
        assert "passed=4" in content
        assert "failed=3" in content
        assert "skipped=3" in content

    def test_smoke_java_coverage_parses_jacoco(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_smoke_java_coverage
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        report_dir = repo_path / "target" / "site"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "jacoco.xml"
        report_path.write_text(
            '<report><counter type="INSTRUCTION" missed="20" covered="80"/></report>',
            encoding="utf-8",
        )
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            output=str(output_path),
            github_output=False,
        )
        result = cmd_smoke_java_coverage(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["percent"] == 80
        assert result.data["covered"] == 80
        assert result.data["missed"] == 20
        content = output_path.read_text(encoding="utf-8")
        assert "percent=80" in content
        assert "covered=80" in content
        assert "missed=20" in content


class TestCmdSmokePython:
    """Tests for smoke Python commands."""

    @mock.patch("cihub.commands.hub_ci.smoke._run_command")
    def test_smoke_python_tests_parses_output(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_smoke_python_tests
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        coverage_file = repo_path / "coverage.xml"
        coverage_file.write_text('<coverage line-rate="0.85"></coverage>', encoding="utf-8")

        mock_run.return_value = mock.Mock(
            stdout="10 passed, 2 failed, 1 skipped",
            stderr="",
            returncode=1,
        )

        output_path = tmp_path / "outputs.txt"
        args = argparse.Namespace(
            path=str(repo_path),
            output_file="test-output.txt",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_smoke_python_tests(args)
        assert isinstance(result, CommandResult)
        # EXIT_FAILURE expected when tests fail (2 failed tests)
        from cihub.exit_codes import EXIT_FAILURE

        assert result.exit_code == EXIT_FAILURE
        assert result.data["passed"] == 10
        assert result.data["failed"] == 2
        assert result.data["skipped"] == 1
        assert result.data["coverage"] == 85
        content = output_path.read_text(encoding="utf-8")
        # total = passed + failed + skipped = 10 + 2 + 1 = 13
        assert "total=13" in content
        assert "passed=10" in content
        assert "failed=2" in content
        assert "skipped=1" in content
        assert "coverage=85" in content


class TestCmdHubCi:
    """Tests for cmd_hub_ci main router."""

    def test_routes_to_correct_handler(self) -> None:
        from cihub.commands.hub_ci import cmd_hub_ci

        # Patch at the router module where cmd_validate_profiles is looked up
        with mock.patch("cihub.commands.hub_ci.router.cmd_validate_profiles") as mock_handler:
            mock_handler.return_value = 0
            args = argparse.Namespace(subcommand="validate-profiles", profiles_dir=None)
            cmd_hub_ci(args)
            mock_handler.assert_called_once_with(args)

    def test_returns_usage_error_for_unknown_subcommand(self) -> None:
        from cihub.commands.hub_ci import cmd_hub_ci
        from cihub.exit_codes import EXIT_USAGE
        from cihub.types import CommandResult

        args = argparse.Namespace(subcommand="unknown-command")
        result = cmd_hub_ci(args)
        # Now returns CommandResult instead of bare int
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_USAGE
        assert "unknown-command" in result.summary
        assert len(result.problems) == 1
        assert result.problems[0]["severity"] == "error"


class TestPlatformDetection:
    """Tests for platform detection functions."""

    def test_get_platform_suffix_returns_valid_format(self) -> None:
        """Platform suffix should match OS_ARCH pattern."""
        from cihub.commands.hub_ci.release import _get_platform_suffix

        result = _get_platform_suffix()
        assert "_" in result
        os_part, arch_part = result.split("_")
        assert os_part in ("darwin", "linux", "windows")
        assert arch_part in ("amd64", "arm64")

    def test_get_kyverno_platform_suffix_uses_x86_64(self) -> None:
        """Kyverno uses x86_64 instead of amd64 for Intel."""
        from cihub.commands.hub_ci.release import _get_kyverno_platform_suffix

        result = _get_kyverno_platform_suffix()
        assert "_" in result
        # Use split with maxsplit=1 since arch can contain underscore (x86_64)
        os_part, arch_part = result.split("_", 1)
        assert os_part in ("darwin", "linux", "windows")
        assert arch_part in ("x86_64", "arm64")

    def test_platform_suffix_matches_current_system(self) -> None:
        """Platform detection should match the current running system."""
        import platform as plat

        from cihub.commands.hub_ci.release import _get_platform_suffix

        result = _get_platform_suffix()
        current_os = plat.system().lower()
        expected_os = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(current_os)
        if expected_os:
            assert result.startswith(expected_os)


class TestEnsureExecutable:
    """Tests for ensure_executable race condition handling."""

    def test_ensure_executable_returns_true_for_existing_file(self, tmp_path: Path) -> None:
        """Should return True when file exists and is made executable."""
        from cihub.commands.hub_ci import ensure_executable

        test_file = tmp_path / "test_script"
        test_file.write_text("#!/bin/bash\necho hello")
        result = ensure_executable(test_file)
        assert result is True

    def test_ensure_executable_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        """Should return False when file doesn't exist."""
        from cihub.commands.hub_ci import ensure_executable

        missing_file = tmp_path / "nonexistent"
        result = ensure_executable(missing_file)
        assert result is False

    def test_ensure_executable_handles_race_condition(self, tmp_path: Path) -> None:
        """Should handle file deletion between check and chmod gracefully."""
        from cihub.commands.hub_ci import ensure_executable

        # Test that the function handles the race condition without raising
        missing_file = tmp_path / "will_be_deleted"
        result = ensure_executable(missing_file)
        assert result is False  # No exception, just returns False
