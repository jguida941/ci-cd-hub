"""Tests for cmd_init config_override functionality (R-002)."""

# TEST-METRICS:

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.commands.init import cmd_init
from cihub.exit_codes import EXIT_SUCCESS


class TestInitConfigOverride:
    """Tests for config_override parameter in cmd_init."""

    def test_config_override_sets_language(self, tmp_path: Path) -> None:
        """config_override language is used instead of detected language."""
        # Create a Python project (would normally detect as python)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        args = argparse.Namespace(
            repo=str(tmp_path),
            apply=True,
            force=True,
            dry_run=False,
            wizard=False,
            json=False,
            language=None,
            owner="test-owner",
            name="test-repo",
            branch="main",
            subdir="",
            fix_pom=False,
            install_from="pypi",
            # R-002: Pass config_override with different language
            config_override={"language": "java", "repo": {"owner": "override-owner"}},
        )

        result = cmd_init(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data is not None
        # Language should be from override, not detected
        assert result.data["language"] == "java"
        assert result.data["owner"] == "override-owner"

        # Verify .ci-hub.yml was written with override language
        config_path = tmp_path / ".ci-hub.yml"
        assert config_path.exists()
        content = config_path.read_text()
        assert "language: java" in content

    def test_config_override_merges_with_detected(self, tmp_path: Path) -> None:
        """config_override is merged with detected config."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        args = argparse.Namespace(
            repo=str(tmp_path),
            apply=True,
            force=True,
            dry_run=False,
            wizard=False,
            json=False,
            language=None,
            owner="test-owner",
            name="test-repo",
            branch="main",
            subdir="",
            fix_pom=False,
            install_from="pypi",
            # Override only thresholds, keep detected language
            config_override={"thresholds": {"coverage_min": 90}},
        )

        result = cmd_init(args)

        assert result.exit_code == EXIT_SUCCESS
        # Language should still be detected (python)
        assert result.data["language"] == "python"
        assert result.data["owner"] == "test-owner"

        # Verify thresholds were merged
        config_path = tmp_path / ".ci-hub.yml"
        content = config_path.read_text()
        assert "coverage_min: 90" in content

    def test_config_override_ignored_when_empty(self, tmp_path: Path) -> None:
        """Empty config_override is ignored."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        args = argparse.Namespace(
            repo=str(tmp_path),
            apply=True,
            force=True,
            dry_run=False,
            wizard=False,
            json=False,
            language=None,
            owner="test-owner",
            name="test-repo",
            branch="main",
            subdir="",
            fix_pom=False,
            install_from="pypi",
            config_override={},  # Empty dict
        )

        result = cmd_init(args)

        assert result.exit_code == EXIT_SUCCESS
        # Should use detected language
        assert result.data["language"] == "python"

    def test_config_override_ignored_when_not_dict(self, tmp_path: Path) -> None:
        """Non-dict config_override is ignored."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        args = argparse.Namespace(
            repo=str(tmp_path),
            apply=True,
            force=True,
            dry_run=False,
            wizard=False,
            json=False,
            language=None,
            owner="test-owner",
            name="test-repo",
            branch="main",
            subdir="",
            fix_pom=False,
            install_from="pypi",
            config_override="not a dict",  # Invalid type
        )

        result = cmd_init(args)

        assert result.exit_code == EXIT_SUCCESS
        # Should use detected language
        assert result.data["language"] == "python"

    def test_config_override_not_applied_when_wizard_true(self, tmp_path: Path, monkeypatch) -> None:
        """config_override is ignored when wizard=True."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        mock_config = {
            "language": "python",
            "repo": {"owner": "wizard-owner", "name": "wizard-repo"},
        }

        class MockWizardResult:
            config = mock_config

        class MockWizardRunner:
            def __init__(self, *args, **kwargs):
                pass

            def run_init_wizard(self, detected):
                return MockWizardResult()

        monkeypatch.setattr("cihub.commands.init.HAS_WIZARD", True)
        monkeypatch.setattr("cihub.wizard.core.WizardRunner", MockWizardRunner)

        args = argparse.Namespace(
            repo=str(tmp_path),
            apply=False,
            force=False,
            dry_run=True,
            wizard=True,
            json=False,
            language=None,
            owner="test-owner",
            name="test-repo",
            branch="main",
            subdir="",
            fix_pom=False,
            install_from="pypi",
            config_override={"language": "java"},
        )

        result = cmd_init(args)

        assert result.exit_code == EXIT_SUCCESS
        # Wizard config should win over config_override
        assert result.data["language"] == "python"


class TestInitWizardDataIncludesConfig:
    """Tests that wizard mode includes config in CommandResult.data."""

    def test_wizard_mode_includes_config_in_data(self, tmp_path: Path, monkeypatch) -> None:
        """When wizard=True, CommandResult.data includes config."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        # Mock the wizard to return a known config
        mock_config = {
            "language": "python",
            "repo": {"owner": "wizard-owner", "name": "wizard-repo"},
            "python": {"version": "3.12"},
        }

        class MockWizardResult:
            config = mock_config

        class MockWizardRunner:
            def __init__(self, *args, **kwargs):
                pass

            def run_init_wizard(self, detected):
                return MockWizardResult()

        monkeypatch.setattr("cihub.commands.init.HAS_WIZARD", True)
        monkeypatch.setattr("cihub.wizard.core.WizardRunner", MockWizardRunner)

        args = argparse.Namespace(
            repo=str(tmp_path),
            apply=False,
            force=False,
            dry_run=True,
            wizard=True,
            json=False,
            language=None,
            owner=None,
            name=None,
            branch="main",
            subdir="",
            fix_pom=False,
            install_from="pypi",
        )

        result = cmd_init(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data is not None
        # Wizard mode should include config in data
        assert "config" in result.data
        assert result.data["config"]["language"] == "python"
        assert result.data["config"]["repo"]["owner"] == "wizard-owner"
        assert result.data["owner"] == "wizard-owner"
