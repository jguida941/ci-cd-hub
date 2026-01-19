"""Extended tests for tool_cmd.py to improve coverage.

This module adds comprehensive tests for the tool command subcommands
that were previously undertested, including validate, info, configure,
and the wizard functions.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from cihub.commands.tool_cmd import (
    TOOL_METADATA,
    _cmd_configure,
    _cmd_disable,
    _cmd_enable,
    _cmd_info,
    _cmd_list,
    _cmd_status,
    _cmd_validate,
    _configure_in_profile,
    _disable_for_all_repos,
    _disable_in_profile,
    _enable_for_all_repos,
    _enable_for_repo,
    _enable_in_profile,
    _get_install_hint,
    _get_tool_info,
    _get_tool_settings,
    _get_tools_for_language,
    _validate_tool_language_for_repo,
    cmd_tool,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE

# =============================================================================
# Helper functions for tests
# =============================================================================


def _write_registry(tmp_path: Path, registry: dict[str, object]) -> None:
    """Write a registry.json file to the test path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")


def _base_registry(repo_config: dict[str, object]) -> dict[str, object]:
    """Create a base registry with a single repo."""
    return {
        "schema_version": "cihub-registry-v1",
        "tiers": {"standard": {}},
        "repos": {"alpha": repo_config},
    }


def _write_profile(tmp_path: Path, name: str, content: dict[str, Any]) -> Path:
    """Write a profile YAML file."""
    import yaml

    profiles_dir = tmp_path / "templates" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profiles_dir / f"{name}.yaml"
    profile_path.write_text(yaml.dump(content), encoding="utf-8")
    return profile_path


# =============================================================================
# Test cmd_tool dispatcher
# =============================================================================


class TestCmdTool:
    """Tests for the cmd_tool dispatcher function."""

    def test_unknown_subcommand(self):
        """Test that unknown subcommand returns usage error."""
        args = argparse.Namespace(subcommand="unknown_cmd")
        result = cmd_tool(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-UNKNOWN-SUBCOMMAND"

    def test_missing_subcommand(self):
        """Test that missing subcommand returns usage error."""
        args = argparse.Namespace(subcommand=None)
        result = cmd_tool(args)
        assert result.exit_code == EXIT_USAGE

    def test_dispatches_to_list(self):
        """Test that 'list' subcommand is dispatched correctly."""
        with patch("cihub.commands.tool_cmd._cmd_list") as mock_list:
            mock_list.return_value = MagicMock(exit_code=EXIT_SUCCESS)
            args = argparse.Namespace(subcommand="list")
            cmd_tool(args)
            mock_list.assert_called_once()

    def test_dispatches_to_enable(self):
        """Test that 'enable' subcommand is dispatched correctly."""
        with patch("cihub.commands.tool_cmd._cmd_enable") as mock_enable:
            mock_enable.return_value = MagicMock(exit_code=EXIT_SUCCESS)
            args = argparse.Namespace(subcommand="enable")
            cmd_tool(args)
            mock_enable.assert_called_once()


# =============================================================================
# Test _cmd_validate
# =============================================================================


class TestCmdValidate:
    """Tests for the _cmd_validate function."""

    def test_validate_plugin_tool(self):
        """Test validation of a plugin/extension tool (no executable)."""
        args = argparse.Namespace(tool="jacoco", install_if_missing=False)
        result = _cmd_validate(args)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["type"] == "plugin"
        assert result.data["installed"] is None

    def test_validate_installed_tool(self):
        """Test validation of an installed tool."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/python"
            args = argparse.Namespace(tool="pytest", install_if_missing=False)
            result = _cmd_validate(args)
            assert result.exit_code == EXIT_SUCCESS
            assert result.data["installed"] is True
            assert "/usr/bin/python" in result.data["path"]

    def test_validate_missing_tool(self):
        """Test validation of a missing tool."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            args = argparse.Namespace(tool="ruff", install_if_missing=False)
            result = _cmd_validate(args)
            assert result.exit_code == EXIT_FAILURE
            assert result.data["installed"] is False
            assert result.problems[0]["code"] == "CIHUB-TOOL-NOT-INSTALLED"

    def test_validate_missing_tool_with_install_hint(self):
        """Test validation suggests installation when tool is missing."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            args = argparse.Namespace(tool="bandit", install_if_missing=True)
            result = _cmd_validate(args)
            assert result.exit_code == EXIT_FAILURE
            assert "install_hint" in result.data
            assert "pip install bandit" in result.data["install_hint"]


# =============================================================================
# Test _cmd_info
# =============================================================================


class TestCmdInfo:
    """Tests for the _cmd_info function."""

    def test_info_known_tool(self):
        """Test info for a known built-in tool."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/ruff"
            args = argparse.Namespace(tool="ruff")
            result = _cmd_info(args)
            assert result.exit_code == EXIT_SUCCESS
            assert result.data["name"] == "ruff"
            assert result.data["category"] == "lint"
            assert result.data["installed"] is True

    def test_info_custom_tool(self):
        """Test info for a custom x-* tool."""
        args = argparse.Namespace(tool="x-my-custom-linter")
        result = _cmd_info(args)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["name"] == "x-my-custom-linter"

    def test_info_unknown_tool(self):
        """Test info for an unknown tool (not built-in, not custom)."""
        args = argparse.Namespace(tool="not_a_real_tool")
        result = _cmd_info(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-UNKNOWN"

    def test_info_includes_settings(self):
        """Test that info includes tool settings."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            args = argparse.Namespace(tool="pytest")
            result = _cmd_info(args)
            assert "settings" in result.data
            assert any(s["name"] == "enabled" for s in result.data["settings"])


# =============================================================================
# Test _cmd_list
# =============================================================================


class TestCmdList:
    """Tests for the _cmd_list function."""

    def test_list_all_tools(self):
        """Test listing all tools (no filters)."""
        args = argparse.Namespace(language=None, category=None, repo=None, enabled_only=False)
        result = _cmd_list(args)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["count"] > 0

    def test_list_python_tools(self):
        """Test listing Python tools only."""
        args = argparse.Namespace(language="python", category=None, repo=None, enabled_only=False)
        result = _cmd_list(args)
        assert result.exit_code == EXIT_SUCCESS
        # All tools should be python or both
        for tool in result.data["tools"]:
            assert tool["language"] in ("python", "both")

    def test_list_java_tools(self):
        """Test listing Java tools only."""
        args = argparse.Namespace(language="java", category=None, repo=None, enabled_only=False)
        result = _cmd_list(args)
        assert result.exit_code == EXIT_SUCCESS
        # All tools should be java or both
        for tool in result.data["tools"]:
            assert tool["language"] in ("java", "both")

    def test_list_by_category(self):
        """Test listing tools by category."""
        args = argparse.Namespace(language=None, category="security", repo=None, enabled_only=False)
        result = _cmd_list(args)
        assert result.exit_code == EXIT_SUCCESS
        # All tools should be security category
        for tool in result.data["tools"]:
            assert tool["category"] == "security"

    def test_list_enabled_only_requires_repo(self):
        """Test that --enabled-only requires --repo."""
        args = argparse.Namespace(language=None, category=None, repo=None, enabled_only=True)
        result = _cmd_list(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-REQUIRES-REPO"

    def test_list_with_nonexistent_repo(self, tmp_path: Path, monkeypatch):
        """Test listing with a repo that doesn't exist."""
        _write_registry(tmp_path, {"schema_version": "cihub-registry-v1", "tiers": {}, "repos": {}})
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(language=None, category=None, repo="nonexistent", enabled_only=False)
        result = _cmd_list(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-REPO-NOT-FOUND"


# =============================================================================
# Test _cmd_enable and _cmd_disable
# =============================================================================


class TestCmdEnableDisable:
    """Tests for _cmd_enable and _cmd_disable functions."""

    def test_enable_no_tool_no_wizard(self):
        """Test enable without tool or wizard."""
        args = argparse.Namespace(tool=None, wizard=False, for_repo=None, all_repos=False, profile=None, json=False)
        result = _cmd_enable(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-NO-NAME"

    def test_enable_unknown_tool(self):
        """Test enable with unknown tool."""
        args = argparse.Namespace(
            tool="not_a_tool", wizard=False, for_repo="repo", all_repos=False, profile=None, json=False
        )
        result = _cmd_enable(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-UNKNOWN"

    def test_enable_no_target(self):
        """Test enable without specifying target."""
        args = argparse.Namespace(tool="ruff", wizard=False, for_repo=None, all_repos=False, profile=None, json=False)
        result = _cmd_enable(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-NO-TARGET"

    def test_disable_no_tool_no_wizard(self):
        """Test disable without tool or wizard."""
        args = argparse.Namespace(tool=None, wizard=False, for_repo=None, all_repos=False, profile=None, json=False)
        result = _cmd_disable(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-NO-NAME"

    def test_wizard_with_json_rejected(self):
        """Test that --wizard with --json is rejected."""
        args = argparse.Namespace(tool=None, wizard=True, for_repo=None, all_repos=False, profile=None, json=True)
        result = _cmd_enable(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-WIZARD-JSON"


# =============================================================================
# Test _cmd_configure
# =============================================================================


class TestCmdConfigure:
    """Tests for _cmd_configure function."""

    def test_configure_missing_args(self):
        """Test configure without required args."""
        args = argparse.Namespace(tool=None, param=None, value=None, repo=None, profile=None, wizard=False, json=False)
        result = _cmd_configure(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-MISSING-ARGS"

    def test_configure_unknown_tool(self):
        """Test configure with unknown tool."""
        args = argparse.Namespace(
            tool="unknown_tool", param="enabled", value="true", repo="repo", profile=None, wizard=False, json=False
        )
        result = _cmd_configure(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-UNKNOWN"

    def test_configure_no_target(self):
        """Test configure without repo or profile target."""
        args = argparse.Namespace(
            tool="ruff", param="enabled", value="true", repo=None, profile=None, wizard=False, json=False
        )
        result = _cmd_configure(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-NO-TARGET"

    def test_configure_parses_boolean_true(self):
        """Test that 'true' is parsed as boolean."""
        with patch("cihub.commands.tool_cmd._configure_for_repo") as mock_config:
            mock_config.return_value = MagicMock(exit_code=EXIT_SUCCESS)
            args = argparse.Namespace(
                tool="ruff", param="enabled", value="true", repo="repo", profile=None, wizard=False, json=False
            )
            _cmd_configure(args)
            # Check that True (bool) was passed, not "true" (str)
            call_args = mock_config.call_args
            assert call_args[0][2] is True

    def test_configure_parses_boolean_false(self):
        """Test that 'false' is parsed as boolean."""
        with patch("cihub.commands.tool_cmd._configure_for_repo") as mock_config:
            mock_config.return_value = MagicMock(exit_code=EXIT_SUCCESS)
            args = argparse.Namespace(
                tool="ruff", param="enabled", value="false", repo="repo", profile=None, wizard=False, json=False
            )
            _cmd_configure(args)
            call_args = mock_config.call_args
            assert call_args[0][2] is False

    def test_configure_parses_integer(self):
        """Test that integer values are parsed correctly."""
        with patch("cihub.commands.tool_cmd._configure_for_repo") as mock_config:
            mock_config.return_value = MagicMock(exit_code=EXIT_SUCCESS)
            args = argparse.Namespace(
                tool="pytest", param="min_coverage", value="70", repo="repo", profile=None, wizard=False, json=False
            )
            _cmd_configure(args)
            call_args = mock_config.call_args
            assert call_args[0][2] == 70

    def test_configure_parses_float(self):
        """Test that float values are parsed correctly."""
        with patch("cihub.commands.tool_cmd._configure_for_repo") as mock_config:
            mock_config.return_value = MagicMock(exit_code=EXIT_SUCCESS)
            args = argparse.Namespace(
                tool="trivy", param="fail_on_cvss", value="7.5", repo="repo", profile=None, wizard=False, json=False
            )
            _cmd_configure(args)
            call_args = mock_config.call_args
            assert call_args[0][2] == 7.5


# =============================================================================
# Test profile operations
# =============================================================================


class TestProfileOperations:
    """Tests for profile enable/disable/configure operations."""

    def test_enable_in_profile_not_found(self, tmp_path: Path, monkeypatch):
        """Test enabling tool in nonexistent profile."""
        # hub_root is imported inside the function, so we patch where it's used
        monkeypatch.setattr("cihub.utils.paths.hub_root", lambda: tmp_path)
        result = _enable_in_profile("ruff", "nonexistent-profile")
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-PROFILE-NOT-FOUND"

    def test_enable_in_profile_success(self, tmp_path: Path, monkeypatch):
        """Test enabling tool in existing profile."""
        monkeypatch.setattr("cihub.utils.paths.hub_root", lambda: tmp_path)
        _write_profile(tmp_path, "python-lib", {"python": {"tools": {}}})

        result = _enable_in_profile("ruff", "python-lib")
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["action"] == "enabled"

    def test_disable_in_profile_success(self, tmp_path: Path, monkeypatch):
        """Test disabling tool in existing profile."""
        monkeypatch.setattr("cihub.utils.paths.hub_root", lambda: tmp_path)
        _write_profile(tmp_path, "python-lib", {"python": {"tools": {"ruff": {"enabled": True}}}})

        result = _disable_in_profile("ruff", "python-lib")
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["action"] == "disabled"

    def test_configure_in_profile_success(self, tmp_path: Path, monkeypatch):
        """Test configuring tool in profile."""
        monkeypatch.setattr("cihub.utils.paths.hub_root", lambda: tmp_path)
        _write_profile(tmp_path, "python-lib", {"python": {"tools": {}}})

        result = _configure_in_profile("pytest", "min_coverage", 80, "python-lib")
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["param"] == "min_coverage"
        assert result.data["value"] == 80

    def test_profile_invalid_yaml(self, tmp_path: Path, monkeypatch):
        """Test handling of invalid YAML in profile."""
        monkeypatch.setattr("cihub.utils.paths.hub_root", lambda: tmp_path)
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        (profiles_dir / "broken.yaml").write_text("{ invalid yaml: [")

        result = _enable_in_profile("ruff", "broken")
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-YAML-ERROR"

    def test_invalid_profile_name(self, tmp_path: Path, monkeypatch):
        """Test validation of profile name."""
        monkeypatch.setattr("cihub.utils.paths.hub_root", lambda: tmp_path)

        # Profile names with invalid characters should be rejected
        result = _enable_in_profile("ruff", "../../../etc/passwd")
        assert result.exit_code == EXIT_FAILURE
        assert "invalid" in result.summary.lower() or result.problems[0]["code"] == "CIHUB-TOOL-INVALID-PROFILE-NAME"


# =============================================================================
# Test repo operations
# =============================================================================


class TestRepoOperations:
    """Tests for repo enable/disable/configure operations."""

    def test_enable_for_repo_not_found(self, tmp_path: Path, monkeypatch):
        """Test enabling tool for nonexistent repo."""
        _write_registry(tmp_path, {"schema_version": "cihub-registry-v1", "tiers": {}, "repos": {}})
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        result = _enable_for_repo("ruff", "nonexistent")
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-REPO-NOT-FOUND"

    def test_enable_for_repo_no_language(self, tmp_path: Path, monkeypatch):
        """Test enabling tool for repo without language set."""
        _write_registry(
            tmp_path,
            _base_registry({"tier": "standard", "config": {}}),
        )
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        result = _enable_for_repo("ruff", "alpha")
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-NO-LANGUAGE"

    def test_disable_for_all_repos(self, tmp_path: Path, monkeypatch):
        """Test disabling tool for all repos."""
        registry = {
            "schema_version": "cihub-registry-v1",
            "tiers": {"standard": {}},
            "repos": {
                "repo1": {"tier": "standard", "language": "python", "config": {}},
                "repo2": {"tier": "standard", "language": "python", "config": {}},
            },
        }
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        result = _disable_for_all_repos("ruff")
        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["updated"]) == 2

    def test_enable_for_all_repos_skips_mismatched_language(self, tmp_path: Path, monkeypatch):
        """Test that enable for all repos skips language-mismatched repos."""
        registry = {
            "schema_version": "cihub-registry-v1",
            "tiers": {"standard": {}},
            "repos": {
                "python_repo": {"tier": "standard", "language": "python", "config": {}},
                "java_repo": {"tier": "standard", "language": "java", "config": {}},
            },
        }
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        # ruff is Python-only
        result = _enable_for_all_repos("ruff")
        assert result.exit_code == EXIT_SUCCESS
        assert "python_repo" in result.data["updated"]
        assert "java_repo" in result.data["skipped"]


# =============================================================================
# Test helper functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions in tool_cmd.py."""

    def test_get_tools_for_language_python(self):
        """Test getting Python tools."""
        tools = _get_tools_for_language("python")
        assert "ruff" in tools
        assert "black" in tools
        assert "pytest" in tools

    def test_get_tools_for_language_java(self):
        """Test getting Java tools."""
        tools = _get_tools_for_language("java")
        assert "jacoco" in tools
        assert "checkstyle" in tools
        assert "spotbugs" in tools

    def test_get_tools_for_language_none(self):
        """Test getting all tools when no language specified."""
        tools = _get_tools_for_language(None)
        # Should have both Python and Java tools
        assert "ruff" in tools
        assert "jacoco" in tools

    def test_get_tool_info_known_tool(self):
        """Test getting info for a known tool."""
        info = _get_tool_info("ruff")
        assert info["name"] == "ruff"
        assert info["language"] == "python"
        assert info["category"] == "lint"
        assert info["executable"] == "ruff"

    def test_get_tool_info_unknown_tool(self):
        """Test getting info for an unknown tool."""
        info = _get_tool_info("mystery_tool")
        assert info["name"] == "mystery_tool"
        assert info["language"] == "unknown"
        assert info["category"] == "unknown"

    def test_get_install_hint(self):
        """Test getting install hints for tools."""
        assert "pip install ruff" in _get_install_hint("ruff")
        assert "pip install bandit" in _get_install_hint("bandit")
        assert "trivy" in _get_install_hint("trivy").lower()

    def test_get_tool_settings(self):
        """Test getting tool settings."""
        settings = _get_tool_settings("pytest")
        setting_names = [s["name"] for s in settings]
        assert "enabled" in setting_names
        assert "min_coverage" in setting_names

    def test_get_tool_settings_unknown(self):
        """Test getting settings for unknown tool."""
        settings = _get_tool_settings("unknown_tool")
        # Should at least have enabled
        assert any(s["name"] == "enabled" for s in settings)

    def test_validate_tool_language_compatible(self):
        """Test language validation for compatible tool/repo."""
        result = _validate_tool_language_for_repo("ruff", "python", "test-repo")
        assert result is None  # None means compatible

    def test_validate_tool_language_incompatible(self):
        """Test language validation for incompatible tool/repo."""
        result = _validate_tool_language_for_repo("spotbugs", "python", "test-repo")
        assert result is not None
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-LANGUAGE-MISMATCH"

    def test_validate_tool_language_custom_tool_always_compatible(self):
        """Test that custom tools are always compatible."""
        result = _validate_tool_language_for_repo("x-custom-linter", "python", "test-repo")
        assert result is None

    def test_validate_tool_language_both_language_compatible(self):
        """Test that 'both' language tools are always compatible."""
        result = _validate_tool_language_for_repo("trivy", "java", "test-repo")
        assert result is None


# =============================================================================
# Test TOOL_METADATA constant
# =============================================================================


class TestToolMetadata:
    """Tests for the TOOL_METADATA constant."""

    def test_metadata_structure(self):
        """Test that TOOL_METADATA has correct structure."""
        for tool, metadata in TOOL_METADATA.items():
            assert isinstance(tool, str)
            assert "language" in metadata
            assert "category" in metadata
            assert "description" in metadata
            assert "executable" in metadata

    def test_python_tools_have_python_language(self):
        """Test that Python tools are marked correctly."""
        python_tools = ["pytest", "ruff", "black", "isort", "mypy", "bandit"]
        for tool in python_tools:
            if tool in TOOL_METADATA:
                assert TOOL_METADATA[tool]["language"] == "python"

    def test_java_tools_have_java_language(self):
        """Test that Java tools are marked correctly."""
        java_tools = ["jacoco", "checkstyle", "spotbugs", "pmd", "owasp"]
        for tool in java_tools:
            if tool in TOOL_METADATA:
                assert TOOL_METADATA[tool]["language"] == "java"

    def test_cross_language_tools_marked_both(self):
        """Test that cross-language tools are marked 'both'."""
        both_tools = ["trivy", "semgrep", "docker"]
        for tool in both_tools:
            if tool in TOOL_METADATA:
                assert TOOL_METADATA[tool]["language"] == "both"


# =============================================================================
# Test _cmd_status
# =============================================================================


class TestCmdStatus:
    """Tests for _cmd_status function."""

    def test_status_requires_repo_or_all(self):
        """Test that status requires --repo or --all."""
        args = argparse.Namespace(repo=None, all=False, language=None)
        result = _cmd_status(args)
        assert result.exit_code == EXIT_USAGE
        assert result.problems[0]["code"] == "CIHUB-TOOL-NO-TARGET"

    def test_status_repo_not_found(self, tmp_path: Path, monkeypatch):
        """Test status for nonexistent repo."""
        _write_registry(tmp_path, {"schema_version": "cihub-registry-v1", "tiers": {}, "repos": {}})
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(repo="nonexistent", all=False, language=None)
        result = _cmd_status(args)
        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["code"] == "CIHUB-TOOL-REPO-NOT-FOUND"

    def test_status_all_repos(self, tmp_path: Path, monkeypatch):
        """Test status for all repos."""
        registry = {
            "schema_version": "cihub-registry-v1",
            "tiers": {"standard": {}},
            "repos": {
                "repo1": {
                    "name": "repo1",
                    "tier": "standard",
                    "language": "python",
                    "config": {"python": {"tools": {"ruff": {"enabled": True}}}},
                },
                "repo2": {
                    "name": "repo2",
                    "tier": "standard",
                    "language": "java",
                    "config": {"java": {"tools": {"checkstyle": {"enabled": True}}}},
                },
            },
        }
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(repo=None, all=True, language=None)
        result = _cmd_status(args)
        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["repos"]) == 2

    def test_status_filter_by_language(self, tmp_path: Path, monkeypatch):
        """Test status filtered by language."""
        registry = {
            "schema_version": "cihub-registry-v1",
            "tiers": {"standard": {}},
            "repos": {
                "python_repo": {"name": "python_repo", "tier": "standard", "language": "python", "config": {}},
                "java_repo": {"name": "java_repo", "tier": "standard", "language": "java", "config": {}},
            },
        }
        _write_registry(tmp_path, registry)
        monkeypatch.setattr("cihub.services.registry_service.hub_root", lambda: tmp_path)

        args = argparse.Namespace(repo=None, all=True, language="python")
        result = _cmd_status(args)
        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["repos"]) == 1
        assert result.data["repos"][0]["language"] == "python"
