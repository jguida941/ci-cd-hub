"""Comprehensive unit tests for cihub/commands/hub_ci/release.py.

This module tests release, tooling install, and summary commands.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import tarfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.release import (
    _get_kyverno_platform_suffix,
    _get_platform_suffix,
    _iter_yaml_files,
    _resolve_actionlint_version,
    _trivy_asset_name,
    cmd_actionlint,
    cmd_actionlint_install,
    cmd_enforce,
    cmd_gitleaks_summary,
    cmd_kyverno_install,
    cmd_kyverno_test,
    cmd_kyverno_validate,
    cmd_license_check,
    cmd_pytest_summary,
    cmd_release_parse_tag,
    cmd_release_update_tag,
    cmd_summary,
    cmd_trivy_install,
    cmd_trivy_summary,
    cmd_zizmor_check,
    cmd_zizmor_run,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


# =============================================================================
# Fixtures
# =============================================================================


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
# Platform Detection Tests
# =============================================================================


class TestPlatformDetection:
    """Tests for platform detection helper functions."""

    def test_get_platform_suffix_format(self):
        """Test that platform suffix has expected format."""
        suffix = _get_platform_suffix()
        assert "_" in suffix
        parts = suffix.split("_")
        assert len(parts) == 2
        assert parts[0] in ("linux", "darwin", "windows")
        assert parts[1] in ("amd64", "arm64")

    def test_get_kyverno_platform_suffix_format(self):
        """Test that kyverno platform suffix has expected format."""
        suffix = _get_kyverno_platform_suffix()
        assert "_" in suffix
        parts = suffix.split("_")
        assert len(parts) == 2
        assert parts[0] in ("linux", "darwin", "windows")
        assert parts[1] in ("x86_64", "arm64")

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="x86_64")
    def test_get_platform_suffix_linux_amd64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test platform suffix for Linux x86_64."""
        suffix = _get_platform_suffix()
        assert suffix == "linux_amd64"

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_get_platform_suffix_darwin_arm64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test platform suffix for macOS ARM64."""
        suffix = _get_platform_suffix()
        assert suffix == "darwin_arm64"

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="x86_64")
    def test_get_kyverno_platform_suffix_linux_x86_64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test kyverno platform suffix uses x86_64 not amd64."""
        suffix = _get_kyverno_platform_suffix()
        assert suffix == "linux_x86_64"


# =============================================================================
# _trivy_asset_name Tests
# =============================================================================


class TestTrivyAssetName:
    """Tests for _trivy_asset_name helper function."""

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="x86_64")
    def test_trivy_linux_64bit(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for Linux 64-bit."""
        name = _trivy_asset_name("0.50.0")
        assert name == "trivy_0.50.0_Linux-64bit.tar.gz"

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="aarch64")
    def test_trivy_linux_arm64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for Linux ARM64."""
        name = _trivy_asset_name("0.50.0")
        assert name == "trivy_0.50.0_Linux-ARM64.tar.gz"

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="x86_64")
    def test_trivy_macos_64bit(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for macOS 64-bit."""
        name = _trivy_asset_name("0.50.0")
        assert name == "trivy_0.50.0_macOS-64bit.tar.gz"

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_trivy_macos_arm64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for macOS ARM64."""
        name = _trivy_asset_name("0.50.0")
        assert name == "trivy_0.50.0_macOS-ARM64.tar.gz"

    @patch("platform.system", return_value="Windows")
    @patch("platform.machine", return_value="AMD64")
    def test_trivy_unsupported_platform(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy raises error for unsupported platforms."""
        with pytest.raises(ValueError, match="Unsupported platform"):
            _trivy_asset_name("0.50.0")

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="i386")
    def test_trivy_unsupported_arch(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy raises error for unsupported architectures."""
        with pytest.raises(ValueError, match="Unsupported"):
            _trivy_asset_name("0.50.0")


# =============================================================================
# _resolve_actionlint_version Tests
# =============================================================================


class TestResolveActionlintVersion:
    """Tests for _resolve_actionlint_version helper function."""

    def test_specific_version(self):
        """Test that specific versions are returned unchanged (stripped of v)."""
        assert _resolve_actionlint_version("1.6.27") == "1.6.27"
        assert _resolve_actionlint_version("v1.6.27") == "1.6.27"

    @patch("urllib.request.urlopen")
    def test_latest_version_resolved(self, mock_urlopen: MagicMock):
        """Test that 'latest' resolves to actual version."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.6.27"}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        version = _resolve_actionlint_version("latest")
        assert version == "1.6.27"

    @patch("urllib.request.urlopen")
    def test_latest_version_network_error(self, mock_urlopen: MagicMock):
        """Test that network errors are handled."""
        mock_urlopen.side_effect = OSError("Network error")

        with pytest.raises(RuntimeError, match="Failed to resolve"):
            _resolve_actionlint_version("latest")

    @patch("urllib.request.urlopen")
    def test_latest_version_empty_tag(self, mock_urlopen: MagicMock):
        """Test that empty tag_name raises error."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": ""}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to resolve"):
            _resolve_actionlint_version("latest")


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
# cmd_actionlint Tests
# =============================================================================


class TestCmdActionlint:
    """Tests for cmd_actionlint function."""

    @patch("cihub.commands.hub_ci.release.safe_run")
    @patch("shutil.which")
    def test_actionlint_success(
        self, mock_which: MagicMock, mock_safe_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test successful actionlint run with no issues."""
        mock_which.return_value = "/usr/local/bin/actionlint"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_safe_run.return_value = mock_proc

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = False

        result = cmd_actionlint(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "passed" in result.summary.lower()

    @patch("shutil.which")
    def test_actionlint_not_found(self, mock_which: MagicMock, mock_args: argparse.Namespace):
        """Test actionlint failure when binary not found."""
        mock_which.return_value = None

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = False

        result = cmd_actionlint(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "not found" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release.safe_run")
    @patch("shutil.which")
    def test_actionlint_with_issues(
        self, mock_which: MagicMock, mock_safe_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test actionlint with workflow issues."""
        mock_which.return_value = "/usr/local/bin/actionlint"
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ".github/workflows/ci.yml:10:5: error\n.github/workflows/ci.yml:20:10: warning"
        mock_safe_run.return_value = mock_proc

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = False

        result = cmd_actionlint(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["issues"] == 2

    @patch("cihub.commands.hub_ci.release.safe_run")
    @patch("shutil.which")
    def test_actionlint_with_reviewdog(
        self, mock_which: MagicMock, mock_safe_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test actionlint with reviewdog integration."""
        mock_which.side_effect = lambda x: {
            "actionlint": "/usr/local/bin/actionlint",
            "reviewdog": "/usr/local/bin/reviewdog",
        }.get(x)

        actionlint_proc = MagicMock()
        actionlint_proc.returncode = 0
        actionlint_proc.stdout = ""

        reviewdog_proc = MagicMock()
        reviewdog_proc.returncode = 0

        mock_safe_run.side_effect = [actionlint_proc, reviewdog_proc]

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = True

        result = cmd_actionlint(mock_args)

        assert result.data["reviewdog"] is True


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


# =============================================================================
# cmd_trivy_summary Tests
# =============================================================================


class TestCmdTrivySummary:
    """Tests for cmd_trivy_summary function."""

    def test_trivy_summary_no_files(self, mock_args: argparse.Namespace):
        """Test trivy summary with no input files."""
        mock_args.fs_json = None
        mock_args.config_json = None
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["total_critical"] == 0
        assert result.data["total_high"] == 0

    def test_trivy_summary_with_vulnerabilities(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test trivy summary parses vulnerabilities correctly."""
        fs_json = tmp_path / "trivy-fs.json"
        fs_json.write_text(
            json.dumps({
                "Results": [
                    {
                        "Vulnerabilities": [
                            {"Severity": "CRITICAL"},
                            {"Severity": "HIGH"},
                            {"Severity": "HIGH"},
                            {"Severity": "MEDIUM"},
                        ]
                    }
                ]
            }),
            encoding="utf-8",
        )

        mock_args.fs_json = str(fs_json)
        mock_args.config_json = None
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.data["fs_critical"] == 1
        assert result.data["fs_high"] == 2

    def test_trivy_summary_with_misconfigurations(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test trivy summary parses misconfigurations correctly."""
        config_json = tmp_path / "trivy-config.json"
        config_json.write_text(
            json.dumps({
                "Results": [
                    {
                        "Misconfigurations": [
                            {"Severity": "CRITICAL"},
                            {"Severity": "CRITICAL"},
                            {"Severity": "HIGH"},
                        ]
                    }
                ]
            }),
            encoding="utf-8",
        )

        mock_args.fs_json = None
        mock_args.config_json = str(config_json)
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.data["config_critical"] == 2
        assert result.data["config_high"] == 1

    def test_trivy_summary_invalid_json(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test trivy summary handles invalid JSON gracefully."""
        fs_json = tmp_path / "trivy-fs.json"
        fs_json.write_text("not json", encoding="utf-8")

        mock_args.fs_json = str(fs_json)
        mock_args.config_json = None
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(result.problems) > 0


# =============================================================================
# cmd_kyverno_validate Tests
# =============================================================================


class TestCmdKyvernoValidate:
    """Tests for cmd_kyverno_validate function."""

    def test_validate_no_policies_dir(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test validation when policies directory doesn't exist."""
        mock_args.policies_dir = str(tmp_path / "nonexistent")
        mock_args.templates_dir = None
        mock_args.bin = None

        result = cmd_kyverno_validate(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "no policies found" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release._kyverno_apply")
    def test_validate_success(
        self, mock_apply: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test successful policy validation."""
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy1.yaml").write_text("policy: test", encoding="utf-8")

        mock_apply.return_value = "policy validated successfully"

        mock_args.policies_dir = str(policies_dir)
        mock_args.templates_dir = None
        mock_args.bin = None

        result = cmd_kyverno_validate(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["validated"] >= 1

    @patch("cihub.commands.hub_ci.release._kyverno_apply")
    def test_validate_with_failures(
        self, mock_apply: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test validation with policy failures."""
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy1.yaml").write_text("policy: test", encoding="utf-8")

        mock_apply.return_value = "error: invalid policy"

        mock_args.policies_dir = str(policies_dir)
        mock_args.templates_dir = None
        mock_args.bin = None

        result = cmd_kyverno_validate(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["failed"] >= 1


# =============================================================================
# cmd_kyverno_test Tests
# =============================================================================


class TestCmdKyvernoTest:
    """Tests for cmd_kyverno_test function."""

    def test_test_no_fixtures_dir(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test when fixtures directory doesn't exist."""
        mock_args.policies_dir = str(tmp_path / "policies")
        mock_args.fixtures_dir = str(tmp_path / "nonexistent")
        mock_args.fail_on_warn = False
        mock_args.bin = None

        result = cmd_kyverno_test(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "skipped" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release._kyverno_apply")
    def test_test_pass(
        self, mock_apply: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test policy test with passing results."""
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy1.yaml").write_text("policy: test", encoding="utf-8")

        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "fixture1.yaml").write_text("resource: test", encoding="utf-8")

        mock_apply.return_value = "pass: 1"

        mock_args.policies_dir = str(policies_dir)
        mock_args.fixtures_dir = str(fixtures_dir)
        mock_args.fail_on_warn = False
        mock_args.bin = None

        result = cmd_kyverno_test(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["tested"] >= 1


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


# =============================================================================
# cmd_gitleaks_summary Tests
# =============================================================================


class TestCmdGitleaksSummary:
    """Tests for cmd_gitleaks_summary function."""

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_gitleaks_summary_success(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test gitleaks summary with success outcome."""
        mock_proc = MagicMock()
        mock_proc.stdout = "100"
        mock_run.side_effect = [
            MagicMock(stdout="100"),  # rev-list count
            MagicMock(stdout="file1.py\nfile2.py"),  # ls-files
        ]

        mock_args.outcome = "success"

        result = cmd_gitleaks_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["result"] == "PASS"

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_gitleaks_summary_failure(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test gitleaks summary with failure outcome."""
        mock_run.side_effect = [
            MagicMock(stdout="50"),
            MagicMock(stdout="file1.py"),
        ]

        mock_args.outcome = "failure"

        result = cmd_gitleaks_summary(mock_args)

        assert result.data["result"] == "FAIL"


# =============================================================================
# cmd_pytest_summary Tests
# =============================================================================


class TestCmdPytestSummary:
    """Tests for cmd_pytest_summary function."""

    def test_pytest_summary_no_files(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pytest summary when files don't exist."""
        mock_args.junit_xml = str(tmp_path / "nonexistent.xml")
        mock_args.coverage_xml = str(tmp_path / "nonexistent.xml")
        mock_args.coverage_min = 70

        result = cmd_pytest_summary(mock_args)

        assert result.data["tests_total"] == 0

    def test_pytest_summary_with_results(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pytest summary with test results."""
        junit_xml = tmp_path / "test-results.xml"
        junit_xml.write_text(
            """<?xml version="1.0" encoding="utf-8"?>
            <testsuite tests="10" failures="1" errors="0" skipped="2">
            </testsuite>""",
            encoding="utf-8",
        )

        coverage_xml = tmp_path / "coverage.xml"
        coverage_xml.write_text(
            """<?xml version="1.0" encoding="utf-8"?>
            <coverage line-rate="0.85" lines-covered="850" lines-valid="1000">
            </coverage>""",
            encoding="utf-8",
        )

        mock_args.junit_xml = str(junit_xml)
        mock_args.coverage_xml = str(coverage_xml)
        mock_args.coverage_min = 70

        result = cmd_pytest_summary(mock_args)

        assert result.data["tests_total"] == 10
        assert result.data["tests_failed"] == 1
        assert result.data["tests_skipped"] == 2
        assert result.data["coverage_pct"] == 85


# =============================================================================
# cmd_summary Tests
# =============================================================================


class TestCmdSummary:
    """Tests for cmd_summary function."""

    def test_summary_all_success(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test summary with all successful results."""
        env_vars = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        result = cmd_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["has_issues"] is False

    def test_summary_with_failures(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test summary with some failures."""
        monkeypatch.setenv("RESULT_LINT", "failure")

        result = cmd_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["has_issues"] is True


# =============================================================================
# cmd_enforce Tests
# =============================================================================


class TestCmdEnforce:
    """Tests for cmd_enforce function."""

    def test_enforce_all_pass(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test enforce with all checks passing."""
        env_vars = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_LINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        result = cmd_enforce(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["failed"]) == 0

    def test_enforce_with_failure(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test enforce with some checks failing."""
        monkeypatch.setenv("RESULT_LINT", "failure")
        monkeypatch.setenv("RESULT_TYPECHECK", "failure")

        result = cmd_enforce(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert len(result.data["failed"]) >= 1

    def test_enforce_skipped_allowed(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test enforce allows skipped checks."""
        monkeypatch.setenv("RESULT_MUTATION", "skipped")

        result = cmd_enforce(mock_args)

        assert result.exit_code == EXIT_SUCCESS


# =============================================================================
# _iter_yaml_files Tests
# =============================================================================


class TestIterYamlFiles:
    """Tests for _iter_yaml_files helper function."""

    def test_iter_yaml_files_both_extensions(self, tmp_path: Path):
        """Test that both .yaml and .yml files are found."""
        (tmp_path / "policy1.yaml").write_text("test", encoding="utf-8")
        (tmp_path / "policy2.yml").write_text("test", encoding="utf-8")
        (tmp_path / "other.txt").write_text("test", encoding="utf-8")

        files = _iter_yaml_files(tmp_path)

        assert len(files) == 2
        assert any(f.suffix == ".yaml" for f in files)
        assert any(f.suffix == ".yml" for f in files)

    def test_iter_yaml_files_empty_dir(self, tmp_path: Path):
        """Test iteration on empty directory."""
        files = _iter_yaml_files(tmp_path)
        assert files == []

    def test_iter_yaml_files_sorted(self, tmp_path: Path):
        """Test that files are returned sorted."""
        (tmp_path / "z_policy.yaml").write_text("test", encoding="utf-8")
        (tmp_path / "a_policy.yaml").write_text("test", encoding="utf-8")
        (tmp_path / "m_policy.yaml").write_text("test", encoding="utf-8")

        files = _iter_yaml_files(tmp_path)

        assert files[0].name == "a_policy.yaml"
        assert files[-1].name == "z_policy.yaml"
