"""Tests for hub_ci release platform detection utilities.

Split from test_hub_ci_release.py for better organization.
Tests: platform detection helpers, _trivy_asset_name, _resolve_actionlint_version, _iter_yaml_files
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.release import (
    _get_kyverno_platform_suffix,
    _get_platform_suffix,
    _iter_yaml_files,
    _resolve_actionlint_version,
    _trivy_asset_name,
)

# =============================================================================
# Fixtures (shared with other test_hub_ci_release_* files)
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

    def test_get_platform_suffix_os_part(self):
        """Test that OS part is valid."""
        suffix = _get_platform_suffix()
        os_part = suffix.split("_")[0]
        assert os_part in ("linux", "darwin", "windows")

    def test_get_platform_suffix_arch_part(self):
        """Test that architecture part is valid."""
        suffix = _get_platform_suffix()
        arch_part = suffix.split("_")[1]
        assert arch_part in ("amd64", "arm64")

    def test_get_kyverno_platform_suffix_format(self):
        """Test that kyverno platform suffix has expected format."""
        suffix = _get_kyverno_platform_suffix()
        assert "_" in suffix

    def test_get_kyverno_platform_suffix_uses_x86_64(self):
        """Test that kyverno uses x86_64 for AMD64 architecture."""
        suffix = _get_kyverno_platform_suffix()
        # Kyverno uses x86_64 instead of amd64 for Intel
        parts = suffix.split("_", 1)
        assert parts[0] in ("linux", "darwin", "windows")
        assert parts[1] in ("x86_64", "arm64")


# =============================================================================
# _trivy_asset_name Tests
# =============================================================================


class TestTrivyAssetName:
    """Tests for _trivy_asset_name function."""

    @patch("platform.system")
    @patch("platform.machine")
    def test_linux_amd64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for Linux AMD64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        result = _trivy_asset_name("0.50.0")

        assert "Linux" in result
        assert "64bit" in result
        assert "0.50.0" in result

    @patch("platform.system")
    @patch("platform.machine")
    def test_darwin_arm64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for macOS ARM64."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        result = _trivy_asset_name("0.50.0")

        assert "macOS" in result
        assert "ARM64" in result

    @patch("platform.system")
    @patch("platform.machine")
    def test_windows_amd64(self, mock_machine: MagicMock, mock_system: MagicMock):
        """Test trivy asset name for Windows AMD64."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "AMD64"

        result = _trivy_asset_name("0.50.0")

        assert "Windows" in result
        assert result.endswith(".zip")

    @patch("platform.system")
    def test_unsupported_os(self, mock_system: MagicMock):
        """Test trivy asset name raises for unsupported OS."""
        mock_system.return_value = "FreeBSD"

        with pytest.raises(ValueError, match="Unsupported"):
            _trivy_asset_name("0.50.0")


# =============================================================================
# _resolve_actionlint_version Tests
# =============================================================================


class TestResolveActionlintVersion:
    """Tests for _resolve_actionlint_version function."""

    def test_explicit_version(self):
        """Test that explicit version is returned as-is."""
        result = _resolve_actionlint_version("1.6.27")
        assert result == "1.6.27"

    @patch("urllib.request.urlopen")
    def test_latest_version_resolved(self, mock_urlopen: MagicMock):
        """Test that 'latest' resolves to actual version."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.7.0"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = _resolve_actionlint_version("latest")

        assert result == "1.7.0"

    @patch("urllib.request.urlopen")
    def test_latest_version_failure(self, mock_urlopen: MagicMock):
        """Test that failure to resolve latest raises error."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to resolve"):
            _resolve_actionlint_version("latest")


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
