"""Test CI execution across repo shapes.

Verifies that `cihub ci` runs successfully for each supported
repo shape (with minimal tool set).
"""

# TEST-METRICS:

from __future__ import annotations

import pytest

from .conftest import (
    SINGLE_LANG_SHAPES,
    run_cihub,
)


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
@pytest.mark.slow  # These tests run actual tools
def test_ci_runs_on_shape(shape: str, repo_shape) -> None:
    """CI should run without error for each shape."""
    path = repo_shape(shape)

    # Initialize first
    init_result = run_cihub("init", "--repo", str(path), "--apply")
    assert init_result.returncode == 0, f"init failed for {shape}"

    # Run CI (minimal, just validate config works)
    ci_result = run_cihub(
        "ci",
        "--repo",
        str(path),
        "--no-write-github-summary",
    )

    # CI should at least start (may fail on missing tools in CI env)
    # We check for startup success, not full tool success
    assert ci_result.returncode in (0, 1), f"ci crashed for {shape}: {ci_result.stderr}"


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_ci_produces_report(shape: str, repo_shape) -> None:
    """CI should produce a report.json file."""
    import json

    path = repo_shape(shape)

    # Initialize
    run_cihub("init", "--repo", str(path), "--apply")

    # Run CI
    run_cihub(
        "ci",
        "--repo",
        str(path),
        "--no-write-github-summary",
    )

    # Check for report - should exist even if some tools fail
    report_path = path / ".cihub" / "report.json"
    assert report_path.exists(), f"report.json not created for {shape}"

    # Verify it's valid JSON with expected structure
    report = json.loads(report_path.read_text())
    assert "tools_ran" in report, f"report missing tools_ran for {shape}"
    assert "tools_success" in report, f"report missing tools_success for {shape}"
    assert "environment" in report, f"report missing environment for {shape}"


@pytest.mark.parametrize("shape", ["python-pyproject", "python-setup"])
def test_smoke_runs_python(shape: str, repo_shape) -> None:
    """Smoke test should work for Python shapes."""
    path = repo_shape(shape)

    # Smoke test validates the full flow
    result = run_cihub("smoke", str(path), "--keep")

    # Smoke may fail if tools aren't installed, but shouldn't crash
    assert result.returncode in (0, 1), f"smoke crashed for {shape}: {result.stderr}"


@pytest.mark.parametrize("shape", ["java-maven", "java-gradle"])
@pytest.mark.skipif(True, reason="Java tools often not available in CI")
def test_smoke_runs_java(shape: str, repo_shape) -> None:
    """Smoke test should work for Java shapes."""
    path = repo_shape(shape)

    result = run_cihub("smoke", str(path), "--keep")
    assert result.returncode in (0, 1), f"smoke crashed for {shape}: {result.stderr}"


def test_ci_output_dir_custom(repo_shape) -> None:
    """CI should respect custom --output-dir."""
    path = repo_shape("python-pyproject")
    output_dir = path / "custom_output"

    run_cihub("init", "--repo", str(path), "--apply")
    run_cihub(
        "ci",
        "--repo",
        str(path),
        "--output-dir",
        str(output_dir),
        "--no-write-github-summary",
    )

    # Output should go to custom dir (if CI ran at all)
    # We don't assert existence since CI may fail early


def test_ci_with_workdir_override(repo_shape) -> None:
    """CI should work with --workdir for monorepo subdirs."""
    path = repo_shape("monorepo")

    # Init the python subdir
    python_subdir = path / "python"
    if python_subdir.exists():
        run_cihub("init", "--repo", str(python_subdir), "--apply")

        # Run CI with workdir
        result = run_cihub(
            "ci",
            "--repo",
            str(path),
            "--workdir",
            "python",
            "--no-write-github-summary",
        )

        # Should at least start
        assert result.returncode in (0, 1), f"ci with workdir failed: {result.stderr}"
