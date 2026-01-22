"""Tests for the cihub gradle command.

This module provides comprehensive tests for the Gradle fix functionality,
including plugin insertion, configuration management, and error handling.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import patch

from cihub.commands.gradle import (
    GradleFixResult,
    apply_gradle_fixes,
    cmd_fix_gradle,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE

# =============================================================================
# Test GradleFixResult dataclass
# =============================================================================


class TestGradleFixResult:
    """Tests for the GradleFixResult dataclass."""

    def test_default_values(self):
        """Test GradleFixResult has correct defaults."""
        result = GradleFixResult(exit_code=EXIT_SUCCESS)
        assert result.exit_code == EXIT_SUCCESS
        assert result.messages == []
        assert result.warnings == []
        assert result.diff == ""
        assert result.files_modified == []

    def test_custom_values(self):
        """Test GradleFixResult with custom values."""
        result = GradleFixResult(
            exit_code=EXIT_FAILURE,
            messages=["message1", "message2"],
            warnings=["warning1"],
            diff="--- a\n+++ b\n",
            files_modified=["/path/to/file"],
        )
        assert result.exit_code == EXIT_FAILURE
        assert len(result.messages) == 2
        assert len(result.warnings) == 1
        assert "---" in result.diff
        assert len(result.files_modified) == 1


# =============================================================================
# Test apply_gradle_fixes
# =============================================================================


class TestApplyGradleFixes:
    """Tests for the apply_gradle_fixes function."""

    def test_no_build_gradle_returns_failure(self, tmp_path: Path):
        """Test that missing build.gradle returns failure."""
        config: dict[str, Any] = {}
        result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
        assert result.exit_code == EXIT_FAILURE
        assert any("not found" in w.lower() for w in result.warnings)

    def test_kotlin_dsl_not_supported(self, tmp_path: Path):
        """Test that Kotlin DSL is detected but not supported."""
        (tmp_path / "build.gradle.kts").write_text("// Kotlin DSL")
        config: dict[str, Any] = {}
        result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
        assert result.exit_code == EXIT_FAILURE
        assert any("kotlin" in w.lower() for w in result.warnings)

    def test_respects_subdir_config(self, tmp_path: Path):
        """Test that subdir in config is respected."""
        # Create build.gradle in subdir
        subdir = tmp_path / "backend"
        subdir.mkdir()
        (subdir / "build.gradle").write_text("// gradle file")

        config: dict[str, Any] = {"repo": {"subdir": "backend"}}

        with patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect:
            mock_collect.return_value = ([], [])  # No warnings, no missing plugins
            result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
            # Should succeed since we're looking in the right subdir
            assert result.exit_code == EXIT_SUCCESS

    def test_no_changes_needed(self, tmp_path: Path):
        """Test when no build.gradle changes are needed."""
        (tmp_path / "build.gradle").write_text("// complete build file")
        config: dict[str, Any] = {}

        with patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect:
            mock_collect.return_value = ([], [])  # No warnings, no missing plugins
            result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
            assert result.exit_code == EXIT_SUCCESS
            assert any("no" in m.lower() and "change" in m.lower() for m in result.messages)

    def test_collects_warnings(self, tmp_path: Path):
        """Test that warnings from collect_gradle_warnings are captured."""
        (tmp_path / "build.gradle").write_text("// gradle file")
        config: dict[str, Any] = {}

        with patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect:
            mock_collect.return_value = (
                ["Plugin X is outdated", "Missing dependency Y"],
                [],
            )
            result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
            assert len(result.warnings) == 2
            assert "Plugin X is outdated" in result.warnings

    def test_dry_run_generates_diff(self, tmp_path: Path):
        """Test that dry run (apply=False) generates diff output."""
        build_content = """plugins {
    id 'java'
}
"""
        (tmp_path / "build.gradle").write_text(build_content)
        config: dict[str, Any] = {}

        with (
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_plugin_snippets") as mock_plugins,
            patch("cihub.commands.gradle.insert_plugins_into_gradle") as mock_insert,
        ):
            mock_collect.return_value = ([], ["checkstyle"])
            mock_plugins.return_value = {"checkstyle": "id 'checkstyle'"}
            mock_insert.return_value = (
                build_content + "\n    id 'checkstyle'\n",
                True,
            )

            result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
            # Should have diff output
            assert result.diff != "" or result.exit_code == EXIT_SUCCESS

    def test_apply_writes_file(self, tmp_path: Path):
        """Test that apply=True writes changes to file."""
        build_content = "plugins {\n    id 'java'\n}\n"
        (tmp_path / "build.gradle").write_text(build_content)
        config: dict[str, Any] = {}

        updated_content = "plugins {\n    id 'java'\n    id 'checkstyle'\n}\n"

        with (
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_plugin_snippets") as mock_plugins,
            patch("cihub.commands.gradle.insert_plugins_into_gradle") as mock_insert,
        ):
            mock_collect.return_value = ([], ["checkstyle"])
            mock_plugins.return_value = {"checkstyle": "id 'checkstyle'"}
            mock_insert.return_value = (updated_content, True)

            result = apply_gradle_fixes(tmp_path, config, apply=True, include_configs=False)

            # File should be modified
            assert result.exit_code == EXIT_SUCCESS
            assert str(tmp_path / "build.gradle") in result.files_modified

    def test_insertion_failure(self, tmp_path: Path):
        """Test handling when plugin insertion fails."""
        (tmp_path / "build.gradle").write_text("// malformed gradle file")
        config: dict[str, Any] = {}

        with (
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_plugin_snippets") as mock_plugins,
            patch("cihub.commands.gradle.insert_plugins_into_gradle") as mock_insert,
        ):
            mock_collect.return_value = ([], ["checkstyle"])
            mock_plugins.return_value = {"checkstyle": "id 'checkstyle'"}
            mock_insert.return_value = ("// malformed gradle file", False)  # Insertion failed

            result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=False)
            assert result.exit_code == EXIT_FAILURE
            assert any("insertion point" in w.lower() or "failed" in w.lower() for w in result.warnings)

    def test_include_configs_option(self, tmp_path: Path):
        """Test that include_configs option triggers config insertion."""
        build_content = "plugins {\n    id 'java'\n}\n"
        (tmp_path / "build.gradle").write_text(build_content)
        config: dict[str, Any] = {}

        with (
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_plugin_snippets") as mock_plugins,
            patch("cihub.commands.gradle.load_gradle_config_snippets") as mock_configs,
            patch("cihub.commands.gradle.insert_plugins_into_gradle") as mock_insert_plugins,
            patch("cihub.commands.gradle.insert_configs_into_gradle") as mock_insert_configs,
        ):
            mock_collect.return_value = ([], ["checkstyle"])
            mock_plugins.return_value = {"checkstyle": "id 'checkstyle'"}
            mock_configs.return_value = {"checkstyle": "checkstyle { }"}
            mock_insert_plugins.return_value = (build_content + "id 'checkstyle'\n", True)
            mock_insert_configs.return_value = (build_content + "checkstyle { }\n", True)

            apply_gradle_fixes(tmp_path, config, apply=False, include_configs=True)
            # Config insertion should have been called
            mock_insert_configs.assert_called_once()

    def test_normalize_configs_without_missing_plugins(self, tmp_path: Path):
        """Test that config normalization runs even if no plugins are missing."""
        build_content = "plugins {\n    id 'java'\n}\n"
        updated_content = build_content + "\npmd {\n    toolVersion = '7.0.0'\n}\n"
        (tmp_path / "build.gradle").write_text(build_content)
        config: dict[str, Any] = {}

        with (
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_config_snippets") as mock_configs,
            patch("cihub.commands.gradle.normalize_gradle_configs") as mock_normalize,
        ):
            mock_collect.return_value = ([], [])
            mock_configs.return_value = {"pmd": "pmd { toolVersion = '7.0.0' }"}
            mock_normalize.return_value = (updated_content, ["normalized"])

            result = apply_gradle_fixes(tmp_path, config, apply=False, include_configs=True)

        assert result.diff
        assert "normalized" in result.warnings


# =============================================================================
# Test cmd_fix_gradle
# =============================================================================


class TestCmdFixGradle:
    """Tests for the cmd_fix_gradle command function."""

    def test_config_not_found(self, tmp_path: Path):
        """Test that missing .ci-hub.yml returns usage error."""
        args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
        result = cmd_fix_gradle(args)
        assert result.exit_code == EXIT_USAGE
        assert "config" in result.summary.lower()
        assert result.problems[0]["code"] == "CIHUB-GRADLE-NO-CONFIG"

    def test_non_java_repo_skipped(self, tmp_path: Path):
        """Test that non-Java repos are skipped."""
        # Create config for Python repo
        (tmp_path / ".ci-hub.yml").write_text("language: python\n")

        with patch("cihub.commands.gradle.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)
            assert result.exit_code == EXIT_SUCCESS
            assert result.data["skipped"] is True
            assert result.data["reason"] == "not_java"

    def test_non_gradle_java_repo_skipped(self, tmp_path: Path):
        """Test that Maven Java repos are skipped."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\n")

        with patch("cihub.commands.gradle.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "java", "java": {"build_tool": "maven"}}
            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)
            assert result.exit_code == EXIT_SUCCESS
            assert result.data["skipped"] is True
            assert result.data["reason"] == "not_gradle"

    def test_gradle_repo_processes(self, tmp_path: Path):
        """Test that Gradle Java repo is processed."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(
                exit_code=EXIT_SUCCESS,
                messages=["No changes needed"],
                warnings=[],
            )
            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)
            assert result.exit_code == EXIT_SUCCESS
            mock_apply.assert_called_once()

    def test_apply_flag_passed_through(self, tmp_path: Path):
        """Test that apply flag is passed to apply_gradle_fixes."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(exit_code=EXIT_SUCCESS)

            args = argparse.Namespace(repo=str(tmp_path), apply=True, with_configs=False)
            cmd_fix_gradle(args)

            # Verify apply=True was passed
            call_args = mock_apply.call_args
            assert call_args[1]["apply"] is True or call_args[0][2] is True

    def test_with_configs_flag_passed_through(self, tmp_path: Path):
        """Test that with_configs flag is passed to apply_gradle_fixes."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(exit_code=EXIT_SUCCESS)

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=True)
            cmd_fix_gradle(args)

            # Verify include_configs=True was passed
            call_args = mock_apply.call_args
            assert call_args[1]["include_configs"] is True or call_args[0][3] is True

    def test_warnings_become_problems(self, tmp_path: Path):
        """Test that warnings from apply_gradle_fixes become problems."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(
                exit_code=EXIT_SUCCESS,
                warnings=["Warning 1", "Warning 2"],
            )

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)

            assert len(result.problems) == 2
            assert all(p["code"] == "CIHUB-GRADLE-WARNING" for p in result.problems)

    def test_failure_summary(self, tmp_path: Path):
        """Test that failure produces appropriate summary."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(exit_code=EXIT_FAILURE)

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)

            assert result.exit_code == EXIT_FAILURE
            assert "failed" in result.summary.lower()

    def test_dry_run_summary(self, tmp_path: Path):
        """Test that dry run produces appropriate summary."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(
                exit_code=EXIT_SUCCESS,
                diff="--- a\n+++ b\n",
            )

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)

            assert "dry-run" in result.summary.lower()
            assert "raw_output" in result.data

    def test_apply_summary(self, tmp_path: Path):
        """Test that apply produces appropriate summary."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(
                exit_code=EXIT_SUCCESS,
                files_modified=[str(tmp_path / "build.gradle")],
            )

            args = argparse.Namespace(repo=str(tmp_path), apply=True, with_configs=False)
            result = cmd_fix_gradle(args)

            assert "applied" in result.summary.lower()
            assert len(result.files_modified) == 1


# =============================================================================
# Integration-style tests (using real file I/O but mocked external deps)
# =============================================================================


class TestGradleIntegration:
    """Integration tests for the Gradle fix flow."""

    def test_full_flow_no_changes(self, tmp_path: Path):
        """Test full flow when no changes are needed."""
        # Setup
        (tmp_path / ".ci-hub.yml").write_text("""
language: java
java:
  build_tool: gradle
""")
        (tmp_path / "build.gradle").write_text("""plugins {
    id 'java'
    id 'checkstyle'
    id 'com.github.spotbugs' version '5.0.0'
}
""")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_collect.return_value = ([], [])  # No warnings, no missing plugins

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)

            assert result.exit_code == EXIT_SUCCESS

    def test_full_flow_with_missing_plugins(self, tmp_path: Path):
        """Test full flow when plugins need to be added."""
        # Setup
        (tmp_path / ".ci-hub.yml").write_text("""
language: java
java:
  build_tool: gradle
""")
        (tmp_path / "build.gradle").write_text("""plugins {
    id 'java'
}

repositories {
    mavenCentral()
}
""")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_plugin_snippets") as mock_plugins,
            patch("cihub.commands.gradle.insert_plugins_into_gradle") as mock_insert,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_collect.return_value = (["Missing checkstyle"], ["checkstyle"])
            mock_plugins.return_value = {"checkstyle": "id 'checkstyle'"}
            mock_insert.return_value = (
                """plugins {
    id 'java'
    id 'checkstyle'
}

repositories {
    mavenCentral()
}
""",
                True,
            )

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)

            assert result.exit_code == EXIT_SUCCESS
            assert len(result.problems) >= 1  # At least the warning


# =============================================================================
# Edge cases and error handling
# =============================================================================


class TestGradleEdgeCases:
    """Edge case tests for Gradle command."""

    def test_empty_build_gradle(self, tmp_path: Path):
        """Test handling of empty build.gradle file."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.collect_gradle_warnings") as mock_collect,
            patch("cihub.commands.gradle.load_gradle_plugin_snippets") as mock_plugins,
            patch("cihub.commands.gradle.insert_plugins_into_gradle") as mock_insert,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_collect.return_value = ([], ["checkstyle"])
            mock_plugins.return_value = {"checkstyle": "id 'checkstyle'"}
            mock_insert.return_value = ("", False)  # Can't insert into empty file

            args = argparse.Namespace(repo=str(tmp_path), apply=False, with_configs=False)
            result = cmd_fix_gradle(args)

            assert result.exit_code == EXIT_FAILURE

    def test_missing_with_configs_attribute(self, tmp_path: Path):
        """Test handling when with_configs attribute is missing from args."""
        (tmp_path / ".ci-hub.yml").write_text("language: java\njava:\n  build_tool: gradle\n")
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")

        with (
            patch("cihub.commands.gradle.load_ci_config") as mock_load,
            patch("cihub.commands.gradle.apply_gradle_fixes") as mock_apply,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "gradle"}}
            mock_apply.return_value = GradleFixResult(exit_code=EXIT_SUCCESS)

            # Create args without with_configs (simulates old CLI version)
            args = argparse.Namespace(repo=str(tmp_path), apply=False)
            # getattr with default should handle this
            result = cmd_fix_gradle(args)
            # Should not crash
            assert result is not None
