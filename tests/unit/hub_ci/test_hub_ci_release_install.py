"""Tests for hub_ci release tool installation commands.

Split from test_hub_ci_release.py for better organization.
Tests: cmd_actionlint_install, cmd_kyverno_install, cmd_trivy_install
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.release import (
    cmd_actionlint_install,
    cmd_kyverno_install,
    cmd_trivy_install,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


@pytest.fixture
def mock_args() -> argparse.Namespace:
    """Create a mock argparse namespace with common attributes."""
    args = argparse.Namespace()
    args.github_step_summary = None
    args.github_output = None
    return args


# =============================================================================
# cmd_actionlint_install Tests
# =============================================================================


class TestCmdActionlintInstall:
    """Tests for cmd_actionlint_install function."""

    @patch("cihub.commands.hub_ci.release._extract_tarball_member")
    @patch("cihub.commands.hub_ci.release._download_file")
    @patch("cihub.commands.hub_ci.release._resolve_actionlint_version")
    def test_install_success(
        self,
        mock_resolve: MagicMock,
        mock_download: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path,
        mock_args: argparse.Namespace,
    ):
        """Test successful actionlint installation."""
        mock_resolve.return_value = "1.6.27"
        mock_extract.return_value = tmp_path / "actionlint"

        mock_args.version = "1.6.27"
        mock_args.dest = str(tmp_path)
        mock_args.checksum = None

        result = cmd_actionlint_install(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "actionlint installed" in result.summary
        assert result.data["version"] == "1.6.27"

    @patch("cihub.commands.hub_ci.release._resolve_actionlint_version")
    def test_install_version_resolve_failure(
        self, mock_resolve: MagicMock, mock_args: argparse.Namespace, tmp_path: Path
    ):
        """Test installation failure when version resolution fails."""
        mock_resolve.side_effect = RuntimeError("Failed to resolve version")

        mock_args.version = "latest"
        mock_args.dest = str(tmp_path)

        result = cmd_actionlint_install(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert len(result.problems) > 0

    @patch("cihub.commands.hub_ci.release._download_file")
    @patch("cihub.commands.hub_ci.release._resolve_actionlint_version")
    def test_install_download_failure(
        self,
        mock_resolve: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
        mock_args: argparse.Namespace,
    ):
        """Test installation failure when download fails."""
        mock_resolve.return_value = "1.6.27"
        mock_download.side_effect = OSError("Download failed")

        mock_args.version = "1.6.27"
        mock_args.dest = str(tmp_path)
        mock_args.checksum = None

        result = cmd_actionlint_install(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "download failed" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release._sha256")
    @patch("cihub.commands.hub_ci.release._download_file")
    @patch("cihub.commands.hub_ci.release._resolve_actionlint_version")
    def test_install_checksum_mismatch(
        self,
        mock_resolve: MagicMock,
        mock_download: MagicMock,
        mock_sha256: MagicMock,
        tmp_path: Path,
        mock_args: argparse.Namespace,
    ):
        """Test installation failure on checksum mismatch."""
        mock_resolve.return_value = "1.6.27"
        mock_sha256.return_value = "wrong_hash"

        mock_args.version = "1.6.27"
        mock_args.dest = str(tmp_path)
        mock_args.checksum = "expected_hash"

        result = cmd_actionlint_install(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "checksum mismatch" in result.summary.lower()


# =============================================================================
# cmd_kyverno_install Tests
# =============================================================================


class TestCmdKyvernoInstall:
    """Tests for cmd_kyverno_install function."""

    @patch("cihub.commands.hub_ci.release._extract_tarball_member")
    @patch("cihub.commands.hub_ci.release._download_file")
    def test_install_success(
        self,
        mock_download: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path,
        mock_args: argparse.Namespace,
    ):
        """Test successful kyverno installation."""
        mock_extract.return_value = tmp_path / "kyverno"

        mock_args.version = "1.11.0"
        mock_args.dest = str(tmp_path)
        mock_args.github_path = False

        result = cmd_kyverno_install(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "kyverno installed" in result.summary

    @patch("cihub.commands.hub_ci.release._download_file")
    def test_install_download_failure(
        self, mock_download: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test installation failure when download fails."""
        mock_download.side_effect = OSError("Download failed")

        mock_args.version = "1.11.0"
        mock_args.dest = str(tmp_path)
        mock_args.github_path = False

        result = cmd_kyverno_install(mock_args)

        assert result.exit_code == EXIT_FAILURE


# =============================================================================
# cmd_trivy_install Tests
# =============================================================================


class TestCmdTrivyInstall:
    """Tests for cmd_trivy_install function."""

    @patch("cihub.commands.hub_ci.release._extract_tarball_member")
    @patch("cihub.commands.hub_ci.release._download_file")
    @patch("cihub.commands.hub_ci.release._trivy_asset_name")
    def test_install_success(
        self,
        mock_asset: MagicMock,
        mock_download: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path,
        mock_args: argparse.Namespace,
    ):
        """Test successful trivy installation."""
        mock_asset.return_value = "trivy_0.50.0_Linux-64bit.tar.gz"
        mock_extract.return_value = tmp_path / "trivy"

        mock_args.version = "0.50.0"
        mock_args.dest = str(tmp_path)
        mock_args.github_path = False

        result = cmd_trivy_install(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "trivy installed" in result.summary

    @patch("cihub.commands.hub_ci.release._trivy_asset_name")
    def test_install_unsupported_platform(
        self, mock_asset: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test installation failure on unsupported platform."""
        mock_asset.side_effect = ValueError("Unsupported platform")

        mock_args.version = "0.50.0"
        mock_args.dest = str(tmp_path)
        mock_args.github_path = False

        result = cmd_trivy_install(mock_args)

        assert result.exit_code == EXIT_FAILURE
