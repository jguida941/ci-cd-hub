"""Fixtures for repo shape matrix tests.

This module provides fixtures for testing CI/CD Hub commands across
different repository shapes (Python pyproject, Python setup.py,
Java Maven, Java Gradle, monorepo).

Usage:
    @pytest.mark.parametrize("shape", REPO_SHAPES)
    def test_detect_works(shape, repo_shape):
        path = repo_shape(shape)
        # Test command against path
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Generator

import pytest

# All supported repo shapes from cihub scaffold
REPO_SHAPES = [
    "python-pyproject",
    "python-setup",
    "java-maven",
    "java-gradle",
    "monorepo",
]

# Single-language repo shapes (excludes monorepo which has no root-level language)
SINGLE_LANG_SHAPES = [
    "python-pyproject",
    "python-setup",
    "java-maven",
    "java-gradle",
]

# Language expected for each shape
SHAPE_LANGUAGES = {
    "python-pyproject": "python",
    "python-setup": "python",
    "java-maven": "java",
    "java-gradle": "java",
    # monorepo has no root-level language - use subdirs
}

# Subdirectories for monorepo testing
MONOREPO_SUBDIRS = {
    "java": "java",
    "python": "python",
}


@pytest.fixture
def repo_shape(tmp_path: Path) -> Callable[[str], Path]:
    """Generate a repo shape using cihub scaffold.

    Returns a factory function that creates a repo of the given shape.

    Example:
        def test_example(repo_shape):
            path = repo_shape("python-pyproject")
            assert (path / "pyproject.toml").exists()
    """
    created_paths: list[Path] = []

    def _create_shape(shape: str) -> Path:
        dest = tmp_path / shape.replace("-", "_")
        dest.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "scaffold", shape, str(dest), "--force"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"scaffold {shape} failed: {result.stderr}")

        created_paths.append(dest)
        return dest

    yield _create_shape

    # Cleanup (tmp_path handles this, but be explicit)
    for path in created_paths:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def all_repo_shapes(tmp_path: Path) -> dict[str, Path]:
    """Generate all repo shapes at once.

    Returns a dict mapping shape name to path.
    Useful for tests that need to compare across shapes.
    """
    shapes: dict[str, Path] = {}

    for shape in REPO_SHAPES:
        dest = tmp_path / shape.replace("-", "_")
        dest.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "scaffold", shape, str(dest), "--force"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"scaffold {shape} failed: {result.stderr}")

        shapes[shape] = dest

    return shapes


def run_cihub(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run cihub command and return result.

    Args:
        *args: Command arguments (e.g., "detect", "--repo", ".")
        cwd: Working directory for the command

    Returns:
        CompletedProcess with stdout, stderr, returncode
    """
    return subprocess.run(
        [sys.executable, "-m", "cihub", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def run_cihub_json(*args: str, cwd: Path | None = None) -> dict:
    """Run cihub command with --json and return parsed output.

    Args:
        *args: Command arguments (e.g., "detect", "--repo", ".")
        cwd: Working directory for the command

    Returns:
        Parsed JSON dict from stdout

    Raises:
        AssertionError: If command fails or JSON is invalid
    """
    import json

    result = run_cihub(*args, "--json", cwd=cwd)
    if result.returncode != 0:
        pytest.fail(f"cihub {' '.join(args)} failed: {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON from cihub {' '.join(args)}: {e}\nOutput: {result.stdout}")
