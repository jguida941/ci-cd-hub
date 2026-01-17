"""Tests for cihub.utils.project module.

This module tests the consolidated project detection utilities:
- get_repo_name: Repository name resolution from config/env/git
- detect_java_project_type: Java build system detection (Maven/Gradle)

Includes both parameterized tests and Hypothesis property-based tests.
"""

# TEST-METRICS:

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.utils.project import (
    _detect_java_project_type,
    _get_repo_name,
    detect_java_project_type,
    get_repo_name,
)

# ============================================================================
# get_repo_name Tests
# ============================================================================


class TestGetRepoName:
    """Tests for get_repo_name function."""

    def test_from_github_repository_env(self, tmp_path: Path) -> None:
        """Environment variable GITHUB_REPOSITORY takes precedence."""
        config: dict = {}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            result = get_repo_name(config, tmp_path)
        assert result == "owner/repo"

    def test_from_config_repo_section(self, tmp_path: Path) -> None:
        """Config repo.owner and repo.name are used if no env var."""
        config = {"repo": {"owner": "myowner", "name": "myrepo"}}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == "myowner/myrepo"

    def test_from_git_remote_ssh(self, tmp_path: Path) -> None:
        """Git SSH remote URL is parsed correctly."""
        config: dict = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "cihub.utils.project.get_git_remote",
                return_value="git@github.com:gitowner/gitrepo.git",
            ):
                with patch(
                    "cihub.utils.project.parse_repo_from_remote",
                    return_value=("gitowner", "gitrepo"),
                ):
                    result = get_repo_name(config, tmp_path)
        assert result == "gitowner/gitrepo"

    def test_from_git_remote_https(self, tmp_path: Path) -> None:
        """Git HTTPS remote URL is parsed correctly."""
        config: dict = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "cihub.utils.project.get_git_remote",
                return_value="https://github.com/org/project.git",
            ):
                with patch(
                    "cihub.utils.project.parse_repo_from_remote",
                    return_value=("org", "project"),
                ):
                    result = get_repo_name(config, tmp_path)
        assert result == "org/project"

    def test_returns_empty_when_no_source(self, tmp_path: Path) -> None:
        """Returns empty string when no information available."""
        config: dict = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == ""

    def test_env_takes_precedence_over_config(self, tmp_path: Path) -> None:
        """Environment variable overrides config values."""
        config = {"repo": {"owner": "config-owner", "name": "config-repo"}}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "env/repo"}):
            result = get_repo_name(config, tmp_path)
        assert result == "env/repo"

    def test_config_takes_precedence_over_git(self, tmp_path: Path) -> None:
        """Config values override git remote."""
        config = {"repo": {"owner": "config-owner", "name": "config-repo"}}
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "cihub.utils.project.get_git_remote",
                return_value="git@github.com:git/repo.git",
            ):
                result = get_repo_name(config, tmp_path)
        assert result == "config-owner/config-repo"

    def test_handles_missing_owner_in_config(self, tmp_path: Path) -> None:
        """Incomplete config falls through to git remote."""
        config = {"repo": {"name": "only-name"}}  # Missing owner
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == ""

    def test_handles_empty_repo_section(self, tmp_path: Path) -> None:
        """Empty repo section falls through to git remote."""
        config = {"repo": {}}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == ""

    @pytest.mark.parametrize(
        "repo_value",
        [None, "string", 123, [], True],
        ids=["none", "string", "int", "list", "bool"],
    )
    def test_handles_invalid_repo_config_types(self, tmp_path: Path, repo_value: object) -> None:
        """Non-dict repo config values are handled gracefully."""
        config = {"repo": repo_value}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == ""


class TestGetRepoNameAliases:
    """Tests for backward compatibility aliases."""

    def test_underscore_alias_is_same_function(self) -> None:
        """_get_repo_name is an alias for get_repo_name."""
        assert _get_repo_name is get_repo_name


# ============================================================================
# detect_java_project_type Tests
# ============================================================================


class TestDetectJavaProjectType:
    """Tests for detect_java_project_type function."""

    def test_maven_single_module(self, tmp_path: Path) -> None:
        """Detects Maven single module project."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><artifactId>test</artifactId></project>")
        result = detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_maven_multi_module_with_count(self, tmp_path: Path) -> None:
        """Detects Maven multi-module project with module count."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<project>
            <modules>
                <module>core</module>
                <module>api</module>
                <module>web</module>
            </modules>
            </project>"""
        )
        result = detect_java_project_type(tmp_path)
        assert result == "Multi-module (3 modules)"

    def test_maven_multi_module_empty_modules(self, tmp_path: Path) -> None:
        """Detects Maven multi-module with empty modules section."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><modules></modules></project>")
        result = detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_gradle_single_module(self, tmp_path: Path) -> None:
        """Detects Gradle single module project."""
        build = tmp_path / "build.gradle"
        build.write_text("plugins { id 'java' }")
        result = detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_gradle_kotlin_single_module(self, tmp_path: Path) -> None:
        """Detects Gradle Kotlin DSL single module project."""
        build = tmp_path / "build.gradle.kts"
        build.write_text('plugins { id("java") }')
        result = detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_gradle_multi_module_settings(self, tmp_path: Path) -> None:
        """Detects Gradle multi-module from settings.gradle."""
        settings = tmp_path / "settings.gradle"
        settings.write_text("include ':core', ':api'")
        result = detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_gradle_kotlin_multi_module_settings(self, tmp_path: Path) -> None:
        """Detects Gradle Kotlin DSL multi-module from settings.gradle.kts."""
        settings = tmp_path / "settings.gradle.kts"
        settings.write_text('include(":core", ":api")')
        result = detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_unknown_when_no_build_files(self, tmp_path: Path) -> None:
        """Returns Unknown when no build system files exist."""
        result = detect_java_project_type(tmp_path)
        assert result == "Unknown"

    def test_maven_pom_read_error(self, tmp_path: Path) -> None:
        """Handles OSError when reading pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.mkdir()  # Create directory instead of file to cause read error
        result = detect_java_project_type(tmp_path)
        # Should return "Single module" since pom.xml exists but can't be read
        assert result == "Single module"

    def test_maven_takes_precedence_over_gradle(self, tmp_path: Path) -> None:
        """Maven (pom.xml) is checked before Gradle."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><artifactId>test</artifactId></project>")
        build = tmp_path / "build.gradle"
        build.write_text("plugins { id 'java' }")
        result = detect_java_project_type(tmp_path)
        assert result == "Single module"

    @pytest.mark.parametrize(
        "module_count,expected",
        [
            (1, "Multi-module (1 modules)"),
            (5, "Multi-module (5 modules)"),
            (10, "Multi-module (10 modules)"),
        ],
        ids=["one", "five", "ten"],
    )
    def test_module_count_variants(self, tmp_path: Path, module_count: int, expected: str) -> None:
        """Module count is correctly extracted."""
        modules = "\n".join(f"<module>module{i}</module>" for i in range(module_count))
        pom = tmp_path / "pom.xml"
        pom.write_text(f"<project><modules>{modules}</modules></project>")
        result = detect_java_project_type(tmp_path)
        assert result == expected


class TestDetectJavaProjectTypeAliases:
    """Tests for backward compatibility aliases."""

    def test_underscore_alias_is_same_function(self) -> None:
        """_detect_java_project_type is an alias for detect_java_project_type."""
        assert _detect_java_project_type is detect_java_project_type


# ============================================================================
# Integration Tests
# ============================================================================


class TestProjectUtilsIntegration:
    """Integration tests for project utilities."""

    def test_get_repo_name_with_real_git_remote(self, tmp_path: Path) -> None:
        """Test get_repo_name resolution chain with mocked git."""
        # Test the full resolution chain: env -> config -> git -> empty
        config = {"repo": {"owner": "fallback", "name": "repo"}}

        # 1. With env var set
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "env/repo"}):
            assert get_repo_name(config, tmp_path) == "env/repo"

        # 2. Without env var, uses config
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                assert get_repo_name(config, tmp_path) == "fallback/repo"

    def test_detect_java_project_type_returns_string(self, tmp_path: Path) -> None:
        """detect_java_project_type always returns a string."""
        # Unknown project
        result = detect_java_project_type(tmp_path)
        assert isinstance(result, str)
        assert result in ["Single module", "Multi-module", "Unknown"]


# ============================================================================
# Hypothesis Property-Based Tests
# ============================================================================


class TestGetRepoNamePropertyBased:
    """Property-based tests for get_repo_name."""

    @given(
        owner=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
            min_size=1,
            max_size=20,
        ),
        name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_config_format_invariant(self, owner: str, name: str) -> None:
        """Property: Config with owner/name always produces 'owner/name' format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = {"repo": {"owner": owner, "name": name}}
            with patch.dict(os.environ, {}, clear=True):
                with patch("cihub.utils.project.get_git_remote", return_value=None):
                    result = get_repo_name(config, tmp_path)
            assert result == f"{owner}/{name}"
            assert "/" in result

    @given(repo_str=st.from_regex(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", fullmatch=True))
    @settings(max_examples=50)
    def test_env_var_passthrough(self, repo_str: str) -> None:
        """Property: GITHUB_REPOSITORY env var is passed through unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": repo_str}):
                result = get_repo_name({}, tmp_path)
            assert result == repo_str

    @given(config=st.dictionaries(st.text(max_size=10), st.integers()))
    @settings(max_examples=30)
    def test_invalid_config_returns_string(self, config: dict) -> None:
        """Property: Any config that isn't valid still returns a string (empty or from git)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.dict(os.environ, {}, clear=True):
                with patch("cihub.utils.project.get_git_remote", return_value=None):
                    result = get_repo_name(config, tmp_path)
            assert isinstance(result, str)


class TestDetectJavaProjectTypePropertyBased:
    """Property-based tests for detect_java_project_type."""

    @given(module_count=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_module_count_always_positive_in_output(self, module_count: int) -> None:
        """Property: Module count in output matches number of <module> tags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            modules = "\n".join(f"<module>m{i}</module>" for i in range(module_count))
            pom = tmp_path / "pom.xml"
            pom.write_text(f"<project><modules>{modules}</modules></project>")

            result = detect_java_project_type(Path(tmpdir))

            assert "Multi-module" in result
            # Extract count from result string
            if "modules)" in result:
                count_str = result.split("(")[1].split(" ")[0]
                assert int(count_str) == module_count

    @given(
        pom_exists=st.booleans(),
        build_gradle_exists=st.booleans(),
        build_kts_exists=st.booleans(),
        settings_gradle_exists=st.booleans(),
        settings_kts_exists=st.booleans(),
    )
    @settings(max_examples=50)
    def test_always_returns_valid_type(
        self,
        pom_exists: bool,
        build_gradle_exists: bool,
        build_kts_exists: bool,
        settings_gradle_exists: bool,
        settings_kts_exists: bool,
    ) -> None:
        """Property: Result is always one of the valid project types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create files based on strategy inputs
            if pom_exists:
                (tmp_path / "pom.xml").write_text("<project></project>")
            if build_gradle_exists:
                (tmp_path / "build.gradle").write_text("")
            if build_kts_exists:
                (tmp_path / "build.gradle.kts").write_text("")
            if settings_gradle_exists:
                (tmp_path / "settings.gradle").write_text("")
            if settings_kts_exists:
                (tmp_path / "settings.gradle.kts").write_text("")

            result = detect_java_project_type(tmp_path)

            # Result must be a valid type
            valid_types = {"Single module", "Multi-module", "Unknown"}
            assert any(result.startswith(t.split()[0]) for t in valid_types), f"Invalid result: {result}"
            assert isinstance(result, str)

    @given(content=st.text(max_size=1000))
    @settings(max_examples=30)
    def test_arbitrary_pom_content_no_crash(self, content: str) -> None:
        """Property: Arbitrary pom.xml content doesn't crash the function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            pom = tmp_path / "pom.xml"
            pom.write_text(content)

            # Should not raise
            result = detect_java_project_type(tmp_path)
            assert isinstance(result, str)
