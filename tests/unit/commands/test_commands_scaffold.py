"""Unit tests for scaffold commands."""

import argparse
from pathlib import Path

import pytest

from cihub.commands.scaffold import cmd_scaffold
from cihub.types import CommandResult


class TestScaffoldPython:
    """Tests for Python scaffold types."""

    # TEST-METRICS:

    def test_scaffold_python_pyproject(self, tmp_path: Path) -> None:
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="python-pyproject",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / "pyproject.toml").exists()
        assert (dest / "tests" / "test_app.py").exists()

    def test_scaffold_python_setup(self, tmp_path: Path) -> None:
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="python-setup",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / "setup.py").exists()
        assert (dest / "tests" / "test_core.py").exists()

    def test_scaffold_python_src_layout(self, tmp_path: Path) -> None:
        """Test python-src-layout scaffold with src/ directory structure."""
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="python-src-layout",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / "pyproject.toml").exists()
        assert (dest / "src").exists()
        assert (dest / "src" / "cihub_src_sample" / "__init__.py").exists()
        assert (dest / "src" / "cihub_src_sample" / "core.py").exists()
        assert (dest / "tests" / "test_core.py").exists()


class TestScaffoldJava:
    """Tests for Java scaffold types."""

    def test_scaffold_java_maven(self, tmp_path: Path) -> None:
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="java-maven",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / "pom.xml").exists()
        assert (dest / "src" / "main" / "java" / "com" / "cihub" / "App.java").exists()
        assert (dest / "src" / "test" / "java" / "com" / "cihub" / "AppTest.java").exists()

    def test_scaffold_java_gradle(self, tmp_path: Path) -> None:
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="java-gradle",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / "build.gradle").exists()
        assert (dest / "settings.gradle").exists()
        assert (dest / "src" / "main" / "java" / "com" / "cihub" / "App.java").exists()
        assert (dest / "src" / "test" / "java" / "com" / "cihub" / "AppTest.java").exists()

    def test_scaffold_java_multi_module(self, tmp_path: Path) -> None:
        """Test java-multi-module scaffold with parent POM and child modules."""
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="java-multi-module",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        # Parent POM
        assert (dest / "pom.xml").exists()
        # Child modules
        assert (dest / "module-core" / "pom.xml").exists()
        assert (dest / "module-app" / "pom.xml").exists()
        # Source files
        assert (dest / "module-core" / "src" / "main" / "java" / "com" / "cihub" / "core" / "Calculator.java").exists()
        assert (dest / "module-app" / "src" / "main" / "java" / "com" / "cihub" / "app" / "App.java").exists()


class TestScaffoldMonorepo:
    """Tests for monorepo scaffold type."""

    def test_scaffold_monorepo(self, tmp_path: Path) -> None:
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type="monorepo",
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        # Monorepo should have both java/ and python/ subdirs
        assert (dest / "java").exists() or (dest / "python").exists(), "Monorepo should have language subdirs"


class TestScaffoldList:
    """Tests for scaffold --list."""

    def test_scaffold_list_json(self) -> None:
        args = argparse.Namespace(list=True, type=None, path=None, force=False, json=True)
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "fixtures" in result.data

    def test_scaffold_list_contains_all_types(self) -> None:
        """Ensure all scaffold types are discoverable."""
        args = argparse.Namespace(list=True, type=None, path=None, force=False, json=True)
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        fixtures = result.data.get("fixtures", [])
        types = [f["type"] for f in fixtures]
        # All expected types should be present (all 7 scaffold types)
        expected = [
            "python-pyproject",
            "python-setup",
            "python-src-layout",
            "java-maven",
            "java-gradle",
            "java-multi-module",
            "monorepo",
        ]
        for exp in expected:
            assert exp in types, f"Missing scaffold type: {exp}"


class TestScaffoldValidation:
    """Validate that scaffold templates produce valid project structures."""

    @pytest.mark.parametrize(
        "scaffold_type,build_file",
        [
            ("python-pyproject", "pyproject.toml"),
            ("python-setup", "setup.py"),
            ("python-src-layout", "pyproject.toml"),
            ("java-maven", "pom.xml"),
            ("java-gradle", "build.gradle"),
            ("java-multi-module", "pom.xml"),
        ],
    )
    def test_scaffold_produces_buildable_project(self, tmp_path: Path, scaffold_type: str, build_file: str) -> None:
        """Each scaffold type should produce a project with valid build config."""
        dest = tmp_path / "fixture"
        args = argparse.Namespace(
            list=False,
            type=scaffold_type,
            path=str(dest),
            force=False,
            json=True,
        )
        result = cmd_scaffold(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert (dest / build_file).exists(), f"Missing {build_file} for {scaffold_type}"

        # Verify build file is not empty and contains expected content
        content = (dest / build_file).read_text()
        assert len(content) > 50, f"Build file {build_file} seems too small"
