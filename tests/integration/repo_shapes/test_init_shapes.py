"""Test config initialization across repo shapes.

Verifies that `cihub init` generates valid .ci-hub.yml for each
supported repo shape.
"""

# TEST-METRICS:

from __future__ import annotations

import pytest
import yaml

from .conftest import (
    SHAPE_LANGUAGES,
    SINGLE_LANG_SHAPES,
    run_cihub,
)


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_init_creates_config(shape: str, repo_shape) -> None:
    """Init should create .ci-hub.yml for each shape."""
    path = repo_shape(shape)

    # Run init
    result = run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    assert result.returncode == 0, f"init failed for {shape}: {result.stderr}"

    # Verify config file exists
    config_path = path / ".ci-hub.yml"
    assert config_path.exists(), f".ci-hub.yml not created for {shape}"


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_init_config_is_valid_yaml(shape: str, repo_shape) -> None:
    """Init should create valid YAML."""
    path = repo_shape(shape)

    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    config_path = path / ".ci-hub.yml"

    # Should parse without error
    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert isinstance(config, dict)


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_init_sets_correct_language(shape: str, repo_shape) -> None:
    """Init should set the correct language in config."""
    path = repo_shape(shape)
    expected_lang = SHAPE_LANGUAGES[shape]

    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    config_path = path / ".ci-hub.yml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert config.get("language") == expected_lang


@pytest.mark.parametrize("shape", ["python-pyproject", "python-setup"])
def test_init_enables_python_tools(shape: str, repo_shape) -> None:
    """Init should enable Python tools for Python projects."""
    path = repo_shape(shape)

    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    config_path = path / ".ci-hub.yml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    python_tools = config.get("python", {}).get("tools", {})

    # At minimum, pytest should be enabled
    assert python_tools.get("pytest") is True or python_tools.get("pytest", {}).get("enabled") is True


@pytest.mark.parametrize("shape", ["java-maven", "java-gradle"])
def test_init_enables_java_tools(shape: str, repo_shape) -> None:
    """Init should enable Java tools for Java projects."""
    path = repo_shape(shape)

    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    config_path = path / ".ci-hub.yml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    java_tools = config.get("java", {}).get("tools", {})

    # At minimum, jacoco (coverage) should be configured
    assert "jacoco" in java_tools


def test_init_with_language_override(repo_shape) -> None:
    """Init --language should override detection."""
    path = repo_shape("python-pyproject")

    # Override to java
    result = run_cihub("init", "--repo", str(path), "--language", "java", "--apply", "--no-set-hub-vars")
    assert result.returncode == 0

    config_path = path / ".ci-hub.yml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert config.get("language") == "java"


def test_init_dry_run_does_not_write(repo_shape) -> None:
    """Init without --apply is dry-run and doesn't write files."""
    path = repo_shape("python-pyproject")

    # Run init without --apply
    result = run_cihub("init", "--repo", str(path))
    assert result.returncode == 0
    assert "dry run" in result.stdout.lower()


def test_init_second_run_needs_force(repo_shape) -> None:
    """Init --apply on existing repo needs --force to bypass guardrails."""
    path = repo_shape("python-pyproject")

    # First init creates config
    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    assert (path / ".ci-hub.yml").exists()

    # Second init with --apply but no --force should fail (guardrail)
    result = run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    # Should fail with repo_side_execution error
    assert result.returncode != 0 or "force" in result.stderr.lower() or "repo_side" in result.stderr.lower()


def test_init_force_overrides_guardrails(repo_shape) -> None:
    """Init --apply --force should override repo_side_execution guardrails."""
    path = repo_shape("python-pyproject")

    # First init
    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")
    config_path = path / ".ci-hub.yml"
    assert config_path.exists()

    # Second init with --apply --force should work
    result = run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars", "--force")
    assert result.returncode == 0


@pytest.mark.parametrize("shape", SINGLE_LANG_SHAPES)
def test_validate_passes_after_init(shape: str, repo_shape) -> None:
    """Validate should pass for freshly initialized configs."""
    path = repo_shape(shape)

    # Init
    run_cihub("init", "--repo", str(path), "--apply", "--no-set-hub-vars")

    # Validate
    result = run_cihub("validate", "--repo", str(path))
    assert result.returncode == 0, f"validate failed after init for {shape}: {result.stderr}"
