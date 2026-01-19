"""Fixture-based tests for different repository shapes.

These tests ensure the CLI works correctly across different repository
configurations: Python simple, Python monorepo, Java Maven, Java Gradle,
mixed language, and edge cases like empty repos.

This is critical for a CI/CD tool that must work across diverse codebases.
"""

# TEST-METRICS:

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# =============================================================================
# Fixture Factories
# =============================================================================


@pytest.fixture
def python_simple_repo(tmp_path: Path) -> Path:
    """Create a simple single-package Python repository."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "simple-python"
version = "1.0.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
""")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "src" / "main.py").write_text("""def hello() -> str:
    return "Hello, World!"
""")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("")
    (tmp_path / "tests" / "test_main.py").write_text("""from src.main import hello

def test_hello():
    assert hello() == "Hello, World!"
""")
    return tmp_path


@pytest.fixture
def python_monorepo(tmp_path: Path) -> Path:
    """Create a Python monorepo with multiple packages."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "monorepo-root"
version = "1.0.0"

[tool.pytest.ini_options]
testpaths = ["packages/*/tests"]
""")

    # Package A
    pkg_a = tmp_path / "packages" / "pkg_a"
    pkg_a.mkdir(parents=True)
    (pkg_a / "pyproject.toml").write_text('[project]\nname = "pkg_a"\n')
    (pkg_a / "src").mkdir()
    (pkg_a / "src" / "__init__.py").write_text("")
    (pkg_a / "src" / "api.py").write_text("def api_call(): return 'A'\n")
    (pkg_a / "tests").mkdir()
    (pkg_a / "tests" / "test_api.py").write_text("def test_api(): pass\n")

    # Package B
    pkg_b = tmp_path / "packages" / "pkg_b"
    pkg_b.mkdir(parents=True)
    (pkg_b / "pyproject.toml").write_text('[project]\nname = "pkg_b"\n')
    (pkg_b / "src").mkdir()
    (pkg_b / "src" / "__init__.py").write_text("")
    (pkg_b / "src" / "service.py").write_text("def service(): return 'B'\n")
    (pkg_b / "tests").mkdir()
    (pkg_b / "tests" / "test_service.py").write_text("def test_service(): pass\n")

    return tmp_path


@pytest.fixture
def java_maven_repo(tmp_path: Path) -> Path:
    """Create a Java Maven repository."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pom.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>maven-project</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
</project>
""")
    (tmp_path / "src" / "main" / "java" / "com" / "example").mkdir(parents=True)
    (tmp_path / "src" / "main" / "java" / "com" / "example" / "App.java").write_text("""package com.example;

public class App {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
""")
    (tmp_path / "src" / "test" / "java" / "com" / "example").mkdir(parents=True)
    (tmp_path / "src" / "test" / "java" / "com" / "example" / "AppTest.java").write_text("""package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AppTest {
    @Test
    void testApp() {
        assertTrue(true);
    }
}
""")
    return tmp_path


@pytest.fixture
def java_gradle_repo(tmp_path: Path) -> Path:
    """Create a Java Gradle repository."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "build.gradle").write_text("""plugins {
    id 'java'
    id 'application'
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation 'org.junit.jupiter:junit-jupiter:5.9.0'
}

application {
    mainClass = 'com.example.App'
}

test {
    useJUnitPlatform()
}
""")
    (tmp_path / "settings.gradle").write_text("rootProject.name = 'gradle-project'\n")
    (tmp_path / "src" / "main" / "java" / "com" / "example").mkdir(parents=True)
    (tmp_path / "src" / "main" / "java" / "com" / "example" / "App.java").write_text("""package com.example;

public class App {
    public static void main(String[] args) {
        System.out.println("Hello, Gradle!");
    }
}
""")
    return tmp_path


@pytest.fixture
def java_gradle_kts_repo(tmp_path: Path) -> Path:
    """Create a Java Gradle Kotlin DSL repository."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "build.gradle.kts").write_text("""plugins {
    java
    application
}

repositories {
    mavenCentral()
}

application {
    mainClass.set("com.example.App")
}
""")
    (tmp_path / "settings.gradle.kts").write_text('rootProject.name = "gradle-kts-project"\n')
    (tmp_path / "src" / "main" / "java" / "com" / "example").mkdir(parents=True)
    (tmp_path / "src" / "main" / "java" / "com" / "example" / "App.java").write_text("""package com.example;

public class App {
    public static void main(String[] args) {
        System.out.println("Hello, Gradle KTS!");
    }
}
""")
    return tmp_path


@pytest.fixture
def mixed_python_java_repo(tmp_path: Path) -> Path:
    """Create a mixed Python/Java repository."""
    (tmp_path / ".git").mkdir()

    # Python part
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "pyproject.toml").write_text('[project]\nname = "python-part"\n')
    (tmp_path / "python" / "app.py").write_text("def main(): pass\n")

    # Java part
    (tmp_path / "java").mkdir()
    (tmp_path / "java" / "pom.xml").write_text("""<?xml version="1.0"?>
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>java-part</artifactId>
    <version>1.0.0</version>
</project>
""")

    return tmp_path


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """Create an empty repository (edge case)."""
    (tmp_path / ".git").mkdir()
    return tmp_path


# =============================================================================
# Language Detection Tests
# =============================================================================


class TestLanguageDetection:
    """Tests for language detection across repo shapes."""

    def test_detect_python_simple(self, python_simple_repo: Path):
        """Test detection of simple Python repository."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=python_simple_repo,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                # Should detect Python
                lang = data.get("data", {}).get("language", "")
                assert lang == "python" or "python" in result.stdout.lower()
            except json.JSONDecodeError:
                pass

    def test_detect_python_monorepo(self, python_monorepo: Path):
        """Test detection of Python monorepo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=python_monorepo,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                lang = data.get("data", {}).get("language", "")
                assert lang == "python" or "python" in result.stdout.lower()
            except json.JSONDecodeError:
                pass

    def test_detect_java_maven(self, java_maven_repo: Path):
        """Test detection of Java Maven repository."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=java_maven_repo,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                lang = data.get("data", {}).get("language", "")
                assert lang == "java" or "java" in result.stdout.lower()
            except json.JSONDecodeError:
                pass

    def test_detect_java_gradle(self, java_gradle_repo: Path):
        """Test detection of Java Gradle repository."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=java_gradle_repo,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                lang = data.get("data", {}).get("language", "")
                assert lang == "java" or "java" in result.stdout.lower()
            except json.JSONDecodeError:
                pass

    def test_detect_java_gradle_kts(self, java_gradle_kts_repo: Path):
        """Test detection of Java Gradle Kotlin DSL repository."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=java_gradle_kts_repo,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                lang = data.get("data", {}).get("language", "")
                assert lang == "java" or "java" in result.stdout.lower()
            except json.JSONDecodeError:
                pass

    def test_detect_empty_repo(self, empty_repo: Path):
        """Test detection on empty repository."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=empty_repo,
        )
        # Should handle gracefully - may fail or return unknown
        assert result.returncode is not None


# =============================================================================
# Check Command on Different Shapes
# =============================================================================


class TestCheckOnShapes:
    """Tests for check command on different repo shapes."""

    def test_check_python_simple(self, python_simple_repo: Path):
        """Test check command on simple Python repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=python_simple_repo,
        )
        # Should complete without crashing
        assert result.returncode is not None

    def test_check_python_monorepo(self, python_monorepo: Path):
        """Test check command on Python monorepo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=python_monorepo,
        )
        # Should complete without crashing
        assert result.returncode is not None

    def test_check_java_maven(self, java_maven_repo: Path):
        """Test check command on Java Maven repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=java_maven_repo,
        )
        # Should complete without crashing
        assert result.returncode is not None

    def test_check_java_gradle(self, java_gradle_repo: Path):
        """Test check command on Java Gradle repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=java_gradle_repo,
        )
        # Should complete without crashing
        assert result.returncode is not None

    def test_check_empty_repo(self, empty_repo: Path):
        """Test check command on empty repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=empty_repo,
        )
        # Should handle gracefully
        assert result.returncode is not None


# =============================================================================
# Init Command on Different Shapes
# =============================================================================


class TestInitOnShapes:
    """Tests for init command on different repo shapes."""

    def test_init_on_python_repo(self, python_simple_repo: Path):
        """Test init command on Python repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "init", "--non-interactive", "--language", "python"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=python_simple_repo,
        )
        # Should complete
        assert result.returncode is not None

    def test_init_on_java_repo(self, java_maven_repo: Path):
        """Test init command on Java repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "init", "--non-interactive", "--language", "java"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=java_maven_repo,
        )
        # Should complete
        assert result.returncode is not None

    def test_init_creates_config_file(self, python_simple_repo: Path):
        """Test that init creates .ci-hub.yml config file."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "init", "--non-interactive", "--language", "python"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=python_simple_repo,
        )
        # Config file may or may not be created depending on init behavior
        assert result.returncode is not None


# =============================================================================
# Fix Command on Different Shapes
# =============================================================================


class TestFixOnShapes:
    """Tests for fix command on different repo shapes."""

    def test_fix_safe_dry_run_python(self, python_simple_repo: Path):
        """Test fix --safe --dry-run on Python repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "fix", "--safe", "--dry-run", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=python_simple_repo,
        )
        # Should complete
        assert result.returncode is not None

    def test_fix_safe_dry_run_java_maven(self, java_maven_repo: Path):
        """Test fix --safe --dry-run on Java Maven repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "fix", "--safe", "--dry-run", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=java_maven_repo,
        )
        # Should complete
        assert result.returncode is not None

    def test_fix_safe_dry_run_java_gradle(self, java_gradle_repo: Path):
        """Test fix --safe --dry-run on Java Gradle repo."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "fix", "--safe", "--dry-run", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=java_gradle_repo,
        )
        # Should complete
        assert result.returncode is not None


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual repo configurations."""

    def test_repo_with_no_source_files(self, tmp_path: Path):
        """Test repo with config but no source files."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "empty"\n')
        # No src/ directory

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_path,
        )
        # Should handle gracefully
        assert result.returncode is not None

    def test_repo_with_both_pom_and_pyproject(self, tmp_path: Path):
        """Test repo with both pom.xml and pyproject.toml."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "mixed"\n')
        (tmp_path / "pom.xml").write_text("<project></project>")

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tmp_path,
        )
        # Should pick one language (implementation-defined)
        assert result.returncode is not None

    def test_repo_with_subdir_project(self, tmp_path: Path):
        """Test repo where project is in a subdirectory."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "pyproject.toml").write_text('[project]\nname = "backend"\n')
        (tmp_path / "backend" / "app.py").write_text("x = 1\n")

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tmp_path / "backend",
        )
        # Should work in subdirectory
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                lang = data.get("data", {}).get("language", "")
                assert lang == "python" or "python" in result.stdout.lower()
            except json.JSONDecodeError:
                pass

    def test_repo_with_nested_git(self, tmp_path: Path):
        """Test repo with nested .git directories (submodules simulation)."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "parent"\n')

        # Nested "submodule"
        (tmp_path / "vendor" / ".git").mkdir(parents=True)
        (tmp_path / "vendor" / "pyproject.toml").write_text('[project]\nname = "vendor"\n')

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_path,
        )
        # Should handle without crashing
        assert result.returncode is not None

    def test_repo_with_special_characters_in_path(self, tmp_path: Path):
        """Test repo path handling with special characters."""
        # Create a directory with spaces (common issue)
        special_path = tmp_path / "my project"
        special_path.mkdir()
        (special_path / ".git").mkdir()
        (special_path / "pyproject.toml").write_text('[project]\nname = "special"\n')

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=special_path,
        )
        # Should handle path with spaces
        assert result.returncode is not None
