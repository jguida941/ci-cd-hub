"""Tests for CI engine project detection functions.

Split from test_ci_engine.py for better organization.
Tests: get_repo_name, _resolve_workdir, detect_java_project_type
"""

# TEST-METRICS:

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cihub.services.ci_engine import (
    _resolve_workdir,
    detect_java_project_type,
    get_repo_name,
)


class TestGetRepoName:
    """Tests for get_repo_name function."""

    def test_from_github_repository_env(self, tmp_path: Path) -> None:
        config: dict = {}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            result = get_repo_name(config, tmp_path)
        assert result == "owner/repo"

    def test_from_config_repo_section(self, tmp_path: Path) -> None:
        config = {"repo": {"owner": "myowner", "name": "myrepo"}}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == "myowner/myrepo"

    def test_from_git_remote(self, tmp_path: Path) -> None:
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

    def test_returns_empty_when_no_source(self, tmp_path: Path) -> None:
        config: dict = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.utils.project.get_git_remote", return_value=None):
                result = get_repo_name(config, tmp_path)
        assert result == ""


class TestResolveWorkdir:
    """Tests for _resolve_workdir function."""

    def test_override_takes_precedence(self, tmp_path: Path) -> None:
        config = {"repo": {"subdir": "src"}}
        with patch("cihub.services.ci_engine.helpers.validate_subdir"):
            result = _resolve_workdir(tmp_path, config, "override")
        assert result == "override"

    def test_uses_config_subdir(self, tmp_path: Path) -> None:
        config = {"repo": {"subdir": "mysubdir"}}
        with patch("cihub.services.ci_engine.helpers.validate_subdir"):
            result = _resolve_workdir(tmp_path, config, None)
        assert result == "mysubdir"

    def test_returns_dot_when_no_subdir(self, tmp_path: Path) -> None:
        config: dict = {}
        result = _resolve_workdir(tmp_path, config, None)
        assert result == "."


class TestDetectJavaProjectType:
    """Tests for detect_java_project_type function."""

    @pytest.mark.parametrize(
        "filename,content,expected_contains",
        [
            # Maven multi-module
            ("pom.xml", "<modules><module>a</module><module>b</module></modules>", ["Multi-module", "2 modules"]),
            # Maven single module
            ("pom.xml", "<project><name>single</name></project>", ["Single module"]),
            # Gradle multi-module
            ("settings.gradle", "include 'a', 'b'", ["Multi-module"]),
            # Gradle Kotlin multi-module
            ("settings.gradle.kts", 'include(":a")', ["Multi-module"]),
            # Gradle single module
            ("build.gradle", "apply plugin: 'java'", ["Single module"]),
        ],
        ids=[
            "maven_multi_module",
            "maven_single_module",
            "gradle_multi_module",
            "gradle_kts_multi_module",
            "gradle_single_module",
        ],
    )
    def test_java_project_types(
        self, tmp_path: Path, filename: str, content: str, expected_contains: list[str]
    ) -> None:
        """Detect various Java project types from build files."""
        (tmp_path / filename).write_text(content)
        result = detect_java_project_type(tmp_path)
        for expected in expected_contains:
            assert expected in result, f"Expected '{expected}' in result '{result}'"

    def test_unknown_project(self, tmp_path: Path) -> None:
        """Empty directory returns Unknown."""
        result = detect_java_project_type(tmp_path)
        assert result == "Unknown"
