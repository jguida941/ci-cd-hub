"""Tests for hub_ci release tag and security commands.

Split from test_hub_ci_release.py for better organization.
Tests: cmd_release_parse_tag, cmd_release_update_tag, cmd_zizmor_run, cmd_zizmor_check, cmd_license_check
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.release import (
    cmd_license_check,
    cmd_release_parse_tag,
    cmd_release_update_tag,
    cmd_zizmor_check,
    cmd_zizmor_run,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


@pytest.fixture
def mock_args() -> argparse.Namespace:
    """Create a mock argparse namespace with common attributes."""
    args = argparse.Namespace()
    args.github_step_summary = None
    args.github_output = None
    return args


@pytest.fixture
def sample_sarif(tmp_path: Path) -> Path:
    """Create a sample SARIF file for testing."""
    sarif_path = tmp_path / "zizmor.sarif"
    sarif_data = {
        "version": "2.1.0",
        "runs": [
            {
                "results": [
                    {
                        "ruleId": "test-rule",
                        "level": "error",
                        "message": {"text": "Test finding"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": ".github/workflows/test.yml"},
                                    "region": {"startLine": 10},
                                }
                            }
                        ],
                    }
                ]
            }
        ],
    }
    sarif_path.write_text(json.dumps(sarif_data), encoding="utf-8")
    return sarif_path


# =============================================================================
# cmd_release_parse_tag Tests
# =============================================================================


class TestCmdReleaseParseTag:
    """Tests for cmd_release_parse_tag function."""

    def test_parse_tag_success(self, mock_args: argparse.Namespace):
        """Test successful tag parsing."""
        mock_args.ref = "refs/tags/v1.2.3"

        result = cmd_release_parse_tag(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["version"] == "v1.2.3"
        assert result.data["major"] == "v1"

    def test_parse_tag_not_tag_ref(self, mock_args: argparse.Namespace):
        """Test failure when ref is not a tag."""
        mock_args.ref = "refs/heads/main"

        result = cmd_release_parse_tag(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "not a tag ref" in result.summary.lower()

    def test_parse_tag_from_env(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test tag parsing from GITHUB_REF environment variable."""
        monkeypatch.setenv("GITHUB_REF", "refs/tags/v2.0.0")
        mock_args.ref = None

        result = cmd_release_parse_tag(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["version"] == "v2.0.0"


# =============================================================================
# cmd_release_update_tag Tests
# =============================================================================


class TestCmdReleaseUpdateTag:
    """Tests for cmd_release_update_tag function."""

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_update_tag_success(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test successful tag update."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        mock_args.repo = str(tmp_path)
        mock_args.major = "v1"
        mock_args.version = "v1.2.3"
        mock_args.remote = "origin"

        result = cmd_release_update_tag(mock_args)

        assert result.exit_code == EXIT_SUCCESS

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_update_tag_failure(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test tag update failure."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "error message"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.repo = str(tmp_path)
        mock_args.major = "v1"
        mock_args.version = "v1.2.3"
        mock_args.remote = "origin"

        result = cmd_release_update_tag(mock_args)

        assert result.exit_code == EXIT_FAILURE


# =============================================================================
# cmd_zizmor_run Tests
# =============================================================================


class TestCmdZizmorRun:
    """Tests for cmd_zizmor_run function."""

    @patch("cihub.commands.hub_ci.release.safe_run")
    def test_zizmor_run_success(
        self, mock_safe_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test successful zizmor run."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"version": "2.1.0", "runs": []}'
        mock_safe_run.return_value = mock_proc

        mock_args.workflows = ".github/workflows/"
        mock_args.output = str(tmp_path / "zizmor.sarif")

        result = cmd_zizmor_run(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "SARIF written" in result.summary

    @patch("cihub.commands.hub_ci.release.safe_run")
    def test_zizmor_run_with_findings(
        self, mock_safe_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test zizmor run with findings (non-zero exit but valid SARIF)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = '{"version": "2.1.0", "runs": [{"results": []}]}'
        mock_safe_run.return_value = mock_proc

        mock_args.workflows = ".github/workflows/"
        mock_args.output = str(tmp_path / "zizmor.sarif")

        result = cmd_zizmor_run(mock_args)

        assert result.exit_code == EXIT_SUCCESS  # Still success, SARIF preserved

    @patch("cihub.commands.hub_ci.release.safe_run")
    def test_zizmor_run_not_found(
        self, mock_safe_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test zizmor run when command not found."""
        from cihub.utils.exec_utils import CommandNotFoundError
        mock_safe_run.side_effect = CommandNotFoundError("zizmor")

        mock_args.workflows = ".github/workflows/"
        mock_args.output = str(tmp_path / "zizmor.sarif")

        result = cmd_zizmor_run(mock_args)

        assert result.exit_code == EXIT_SUCCESS  # Empty SARIF written
        assert "not found" in result.summary.lower()


# =============================================================================
# cmd_zizmor_check Tests
# =============================================================================


class TestCmdZizmorCheck:
    """Tests for cmd_zizmor_check function."""

    def test_zizmor_check_no_sarif(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test zizmor check when SARIF file not found."""
        mock_args.sarif = str(tmp_path / "nonexistent.sarif")

        result = cmd_zizmor_check(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "not found" in result.summary.lower()

    def test_zizmor_check_no_findings(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test zizmor check with no findings."""
        sarif_path = tmp_path / "zizmor.sarif"
        sarif_path.write_text('{"version": "2.1.0", "runs": [{"results": []}]}', encoding="utf-8")

        mock_args.sarif = str(sarif_path)

        result = cmd_zizmor_check(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["findings"] == 0

    def test_zizmor_check_with_findings(self, sample_sarif: Path, mock_args: argparse.Namespace):
        """Test zizmor check with findings."""
        mock_args.sarif = str(sample_sarif)

        result = cmd_zizmor_check(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["findings"] > 0

    def test_zizmor_check_note_level_skipped(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test that note-level findings are skipped."""
        sarif_path = tmp_path / "zizmor.sarif"
        sarif_data = {
            "runs": [
                {
                    "results": [
                        {
                            "ruleId": "note-rule",
                            "level": "note",
                            "message": {"text": "Informational"},
                            "locations": [{"physicalLocation": {"artifactLocation": {"uri": "test.yml"}, "region": {"startLine": 1}}}],
                        }
                    ]
                }
            ]
        }
        sarif_path.write_text(json.dumps(sarif_data), encoding="utf-8")

        mock_args.sarif = str(sarif_path)

        result = cmd_zizmor_check(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["findings"] == 0


# =============================================================================
# cmd_license_check Tests
# =============================================================================


class TestCmdLicenseCheck:
    """Tests for cmd_license_check function."""

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_license_check_pass(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test license check with no copyleft licenses."""
        mock_proc = MagicMock()
        mock_proc.stdout = "Name,License\nrequests,Apache 2.0\nflask,BSD-3-Clause"
        mock_run.return_value = mock_proc

        result = cmd_license_check(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["copyleft"] == 0

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_license_check_with_copyleft(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test license check with copyleft licenses."""
        mock_proc = MagicMock()
        mock_proc.stdout = "Name,License\nrequests,Apache 2.0\nsomething,GPL-3.0"
        mock_run.return_value = mock_proc

        result = cmd_license_check(mock_args)

        assert result.exit_code == EXIT_SUCCESS  # Warns but doesn't fail
        assert result.data["copyleft"] == 1

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_license_check_pip_licenses_not_found(
        self, mock_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test license check when pip-licenses not installed."""
        mock_run.side_effect = FileNotFoundError("pip-licenses not found")

        result = cmd_license_check(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "skipped" in result.summary.lower()
