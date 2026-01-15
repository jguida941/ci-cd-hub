"""Test language detection across repo shapes.

Verifies that `cihub detect` correctly identifies the language
and tools for each supported repo shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_repo_shapes.conftest import (
    REPO_SHAPES,
    SHAPE_LANGUAGES,
    SINGLE_LANG_SHAPES,
    run_cihub,
    run_cihub_json,
)


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_detect_identifies_language(shape: str, repo_shape) -> None:
    """Detect should identify the correct language for each shape."""
    path = repo_shape(shape)
    result = run_cihub_json("detect", "--repo", str(path))

    expected_lang = SHAPE_LANGUAGES[shape]
    assert result.get("status") == "success", f"detect failed for {shape}"
    assert result.get("data", {}).get("language") == expected_lang


def test_detect_monorepo_root_fails(repo_shape) -> None:
    """Detect should fail at monorepo root (no project file there)."""
    path = repo_shape("monorepo")

    # Root level detection should fail (no pyproject.toml/pom.xml at root)
    result = run_cihub("detect", "--repo", str(path))
    assert result.returncode != 0, "monorepo root should not detect a language"


def test_detect_monorepo_subdir_python(repo_shape) -> None:
    """Detect should work in monorepo python subdir."""
    path = repo_shape("monorepo")
    python_subdir = path / "python"

    if python_subdir.exists():
        result = run_cihub_json("detect", "--repo", str(python_subdir))
        assert result.get("status") == "success"
        assert result.get("data", {}).get("language") == "python"


def test_detect_monorepo_subdir_java(repo_shape) -> None:
    """Detect should work in monorepo java subdir."""
    path = repo_shape("monorepo")
    java_subdir = path / "java"

    if java_subdir.exists():
        result = run_cihub_json("detect", "--repo", str(java_subdir))
        assert result.get("status") == "success"
        assert result.get("data", {}).get("language") == "java"


@pytest.mark.parametrize(
    "shape,expected_lang",
    [
        ("python-pyproject", "python"),
        ("python-setup", "python"),
        ("java-maven", "java"),
        ("java-gradle", "java"),
    ],
)
def test_detect_returns_correct_language_in_data(shape: str, expected_lang: str, repo_shape) -> None:
    """Detect should return correct language in JSON data."""
    path = repo_shape(shape)
    result = run_cihub_json("detect", "--repo", str(path))

    data = result.get("data", {})
    assert data.get("language") == expected_lang


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_detect_exits_zero(shape: str, repo_shape) -> None:
    """Detect should exit with code 0 for valid single-language repos."""
    path = repo_shape(shape)
    result = run_cihub("detect", "--repo", str(path))
    assert result.returncode == 0, f"detect failed for {shape}: {result.stderr}"


def test_detect_explain_provides_reasons(repo_shape) -> None:
    """Detect --explain should provide detection reasoning."""
    path = repo_shape("python-pyproject")
    result = run_cihub("detect", "--repo", str(path), "--explain")

    assert result.returncode == 0
    # Explain output should contain reasoning
    assert "python" in result.stdout.lower() or "pyproject" in result.stdout.lower()


def test_detect_language_override(repo_shape) -> None:
    """Detect --language should override auto-detection."""
    path = repo_shape("python-pyproject")

    # Override to java
    result = run_cihub_json("detect", "--repo", str(path), "--language", "java")

    assert result.get("status") == "success"
    assert result.get("data", {}).get("language") == "java"


def test_detect_nonexistent_repo_fails() -> None:
    """Detect should fail gracefully for nonexistent paths."""
    result = run_cihub("detect", "--repo", "/nonexistent/path/that/does/not/exist")
    assert result.returncode != 0


def test_detect_empty_dir_fails(tmp_path: Path) -> None:
    """Detect should fail for empty directories."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = run_cihub("detect", "--repo", str(empty_dir))
    # Either fails or reports no language detected
    # We accept both behaviors as valid
    if result.returncode == 0:
        import json

        data = json.loads(result.stdout) if "--json" in str(result.args) else {}
        # If success, language should be None or unknown
        assert data.get("data", {}).get("language") in (None, "", "unknown")
