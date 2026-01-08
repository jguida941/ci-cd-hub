"""Shared pytest fixtures for all tests.

This module provides centralized fixtures to reduce duplication across test files.
Fixtures here are automatically available to all tests without explicit imports.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

# =============================================================================
# Hypothesis Configuration for Deterministic Testing
# =============================================================================
# Configure hypothesis to use derandomize=True in CI/mutation testing.
# This makes hypothesis use a deterministic seed based on the test function name,
# ensuring the same examples are generated on every run. This prevents flaky tests
# while still getting full property-based testing coverage.
#
# See: https://hypothesis.readthedocs.io/en/latest/settings.html#hypothesis.settings.derandomize

try:
    from hypothesis import Phase, settings

    # Register a deterministic profile for CI and mutation testing
    # derandomize=True seeds RNG from test function hash = same examples every run
    settings.register_profile(
        "ci",
        derandomize=True,
        max_examples=50,  # Reasonable coverage without being slow
        phases=[Phase.explicit, Phase.reuse, Phase.generate],  # Skip shrinking for speed
        deadline=None,  # No timeout in CI (mutation testing can be slow)
    )

    # Mutation testing profile - even more constrained for speed
    # database=None is CRITICAL for mutmut compatibility - the hypothesis database
    # causes failures in subprocess environments because mutmut runs pytest in a
    # subprocess with a different working directory, and the database path becomes invalid
    settings.register_profile(
        "mutation",
        derandomize=True,
        max_examples=20,  # Fewer examples for faster mutation runs
        phases=[Phase.explicit, Phase.generate],  # Skip reuse and shrinking
        deadline=None,
        database=None,  # Disable database for subprocess compatibility
    )

    # Load appropriate profile based on environment
    # Check multiple indicators for mutation testing/CI environment:
    # - MUTATION_SCORE_MIN: set by our CI workflow
    # - MUTANT_UNDER_TEST: set by mutmut during actual mutation testing
    # - CI: standard CI environment variable
    # - Non-interactive (no TTY): likely subprocess (mutmut, CI pipeline, etc.)
    import sys

    if os.environ.get("MUTATION_SCORE_MIN") is not None or os.environ.get("MUTANT_UNDER_TEST") is not None:
        # Running under mutation testing - use constrained deterministic profile
        settings.load_profile("mutation")
    elif os.environ.get("CI") is not None:
        # Running in CI - use deterministic profile
        settings.load_profile("ci")
    elif not sys.stdin.isatty():
        # Running in a subprocess (likely mutmut or similar) - use mutation profile
        # This catches cases where env vars aren't propagated to subprocess
        settings.load_profile("mutation")
    # Otherwise use default profile (randomized, for local development exploration)

except ImportError:
    # hypothesis not installed - skip configuration
    pass

# =============================================================================
# Repository Fixtures
# =============================================================================


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal temporary repository structure.

    Returns a tmp_path with basic repo files (.git, pyproject.toml).
    Use this for tests that need a valid repo context.
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-repo"\n')
    return tmp_path


@pytest.fixture
def tmp_python_repo(tmp_repo: Path) -> Path:
    """Create a temporary Python repository structure.

    Extends tmp_repo with Python-specific files.
    """
    (tmp_repo / "src").mkdir()
    (tmp_repo / "src" / "__init__.py").write_text("")
    (tmp_repo / "tests").mkdir()
    (tmp_repo / "tests" / "__init__.py").write_text("")
    (tmp_repo / "tests" / "test_example.py").write_text("def test_example(): pass\n")
    return tmp_repo


@pytest.fixture
def tmp_java_repo(tmp_repo: Path) -> Path:
    """Create a temporary Java repository structure.

    Extends tmp_repo with Java-specific files (Maven).
    """
    (tmp_repo / "src" / "main" / "java").mkdir(parents=True)
    (tmp_repo / "src" / "test" / "java").mkdir(parents=True)
    (tmp_repo / "pom.xml").write_text("<project></project>\n")
    return tmp_repo


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Return a minimal valid CI Hub configuration.

    Use this as a base and modify for specific test cases.
    """
    return {
        "python": {
            "tools": {
                "pytest": {"enabled": True, "min_coverage": 70},
                "ruff": {"enabled": True},
                "black": {"enabled": True},
                "isort": {"enabled": True},
                "mypy": {"enabled": True},
                "bandit": {"enabled": True},
            }
        },
        "thresholds": {
            "coverage_min": 70,
            "mutation_score_min": 60,
            "max_critical_vulns": 0,
            "max_high_vulns": 5,
        },
    }


@pytest.fixture
def sample_java_config() -> dict[str, Any]:
    """Return a minimal valid Java CI Hub configuration."""
    return {
        "java": {
            "tools": {
                "build": {"enabled": True, "tool": "maven"},
                "jacoco": {"enabled": True, "min_coverage": 70},
                "checkstyle": {"enabled": True},
                "spotbugs": {"enabled": True},
                "owasp": {"enabled": True},
            }
        },
        "thresholds": {
            "coverage_min": 70,
            "max_critical_vulns": 0,
            "max_high_vulns": 5,
        },
    }


@pytest.fixture
def empty_config() -> dict[str, Any]:
    """Return an empty configuration dict."""
    return {}


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Factory fixture for mocking environment variables.

    Usage:
        def test_something(mock_env):
            mock_env(GITHUB_REPOSITORY="owner/repo", CI="true")
            # Now os.environ has those values
    """

    def _mock(**env_vars: str) -> None:
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

    return _mock


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Callable[[list[str]], None]:
    """Factory fixture for removing environment variables.

    Usage:
        def test_something(clean_env):
            clean_env(["GITHUB_TOKEN", "CI"])
            # Now those env vars are unset
    """

    def _clean(env_vars: list[str]) -> None:
        for key in env_vars:
            monkeypatch.delenv(key, raising=False)

    return _clean


@pytest.fixture
def github_env(mock_env: Callable[..., None]) -> Callable[..., None]:
    """Set up common GitHub Actions environment variables.

    Usage:
        def test_something(github_env):
            github_env(repo="owner/repo", ref="refs/heads/main")
    """

    def _github_env(
        repo: str = "owner/test-repo",
        ref: str = "refs/heads/main",
        sha: str = "abc123",
        workflow: str = "CI",
        run_id: str = "12345",
    ) -> None:
        mock_env(
            GITHUB_REPOSITORY=repo,
            GITHUB_REF=ref,
            GITHUB_REF_NAME=ref.split("/")[-1],
            GITHUB_SHA=sha,
            GITHUB_WORKFLOW=workflow,
            GITHUB_RUN_ID=run_id,
            GITHUB_ACTIONS="true",
            CI="true",
        )

    return _github_env


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_subprocess(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock subprocess.run for testing command execution.

    Returns a MagicMock that can be configured per test.
    """
    import subprocess

    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


# =============================================================================
# Report Fixtures
# =============================================================================


@pytest.fixture
def sample_report() -> dict[str, Any]:
    """Return a minimal valid CI report structure."""
    return {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": "1.0.0",
            "workflow_ref": "owner/repo/.github/workflows/ci.yml@main",
            "generated_at": "2026-01-05T12:00:00Z",
        },
        "results": {
            "pytest": "passed",
            "ruff": "passed",
            "mypy": "passed",
        },
        "tool_metrics": {
            "coverage": 85.5,
            "test_count": 100,
            "test_failures": 0,
        },
        "tools_configured": {
            "pytest": True,
            "ruff": True,
            "mypy": True,
        },
        "tools_ran": {
            "pytest": True,
            "ruff": True,
            "mypy": True,
        },
        "tools_success": {
            "pytest": True,
            "ruff": True,
            "mypy": True,
        },
        "thresholds": {
            "coverage_min": 70,
        },
    }


# =============================================================================
# Tool Result Fixtures
# =============================================================================


@pytest.fixture
def passing_tool_result() -> dict[str, Any]:
    """Return a passing tool result structure."""
    return {
        "success": True,
        "exit_code": 0,
        "output": "All checks passed",
        "metrics": {},
    }


@pytest.fixture
def failing_tool_result() -> dict[str, Any]:
    """Return a failing tool result structure."""
    return {
        "success": False,
        "exit_code": 1,
        "output": "Checks failed",
        "metrics": {"errors": 5},
    }
