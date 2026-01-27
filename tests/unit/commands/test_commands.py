"""Tests for cihub.commands module."""

# TEST-METRICS:
#   Coverage: 100.0%

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.detect import cmd_detect  # noqa: E402
from cihub.commands.init import cmd_init  # noqa: E402
from cihub.commands.update import cmd_update  # noqa: E402
from cihub.commands.validate import cmd_validate  # noqa: E402
from cihub.exit_codes import EXIT_FAILURE  # noqa: E402

# ==============================================================================
# Tests for cmd_detect
# ==============================================================================


class TestCmdDetect:
    """Tests for the detect command.

    All tests verify CommandResult pattern:
    - Commands return CommandResult (not int)
    - Check result.exit_code for success/failure
    - Check result.data for structured output
    """

    def test_detect_python_project(self, tmp_path: Path) -> None:
        """Detect Python project from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "python"
        assert "Detected language" in result.summary

    def test_detect_java_project(self, tmp_path: Path) -> None:
        """Detect Java project from pom.xml."""
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "java"

    def test_detect_with_explain_flag(self, tmp_path: Path) -> None:
        """Detect with explain flag includes reasons in data."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "python"
        assert "reasons" in result.data
        # Verify human-readable output available
        assert "items" in result.data
        assert len(result.data["items"]) > 0

    def test_detect_with_override(self, tmp_path: Path) -> None:
        """Detect respects language override."""
        # Create Python markers but override to Java
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language="java", explain=False)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "java"
        # Verify raw_output contains JSON for backwards compatibility
        assert "raw_output" in result.data
        output = json.loads(result.data["raw_output"])
        assert output["language"] == "java"


# ==============================================================================
# Tests for cmd_validate
# ==============================================================================


class TestCmdValidate:
    """Tests for the validate command."""

    def test_validate_missing_config(self, tmp_path: Path) -> None:
        """Validate returns error when config missing."""
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result.exit_code == 2
        assert "Config not found" in result.summary

    def test_validate_valid_config(self, tmp_path: Path) -> None:
        """Validate returns success for valid config."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
    ruff:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result.exit_code == 0
        assert "Config OK" in result.summary
        items = result.data.get("items", [])
        assert any("Config OK" in item for item in items)

    def test_validate_invalid_config_schema(self, tmp_path: Path) -> None:
        """Validate returns error for invalid schema."""
        # Missing required fields
        config_content = """
repo:
  owner: test
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result.exit_code == 1
        assert "Validation failed" in result.summary
        items = result.data.get("items", [])
        assert any("Validation failed" in item for item in items)

    def test_validate_java_project_with_pom(self, tmp_path: Path) -> None:
        """Validate Java project checks POM warnings."""
        config_content = """
repo:
  owner: test
  name: example
  language: java
  default_branch: main
language: java
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        # Create a minimal valid pom.xml
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        # Should succeed (may have POM warnings but not in strict mode)
        assert result.exit_code in (0, 1)  # 0 if no warnings, 1 if warnings in strict mode

    def test_validate_java_strict_mode(self, tmp_path: Path) -> None:
        """Validate Java project in strict mode fails on POM warnings."""
        config_content = """
repo:
  owner: test
  name: example
  language: java
  default_branch: main
language: java
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        # Create pom.xml without jacoco plugin (will trigger warning)
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=True)
        result = cmd_validate(args)
        # In strict mode, POM warnings cause failure
        assert result.exit_code == 1
        assert "POM warnings" in result.summary

    def test_validate_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Validate returns error for malformed YAML."""
        # Invalid YAML: unclosed bracket
        invalid_yaml = """
repo:
  owner: test
  name: [invalid yaml syntax without closing bracket
"""
        (tmp_path / ".ci-hub.yml").write_text(invalid_yaml, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result.exit_code == 1
        assert "Invalid YAML syntax" in result.summary
        assert len(result.problems) > 0
        assert result.problems[0]["code"] == "CIHUB-VALIDATE-003"

    def test_validate_yaml_root_not_dict(self, tmp_path: Path) -> None:
        """Validate returns error when YAML root is not a dict."""
        # YAML that parses to a list instead of dict
        list_yaml = """
- item1
- item2
- item3
"""
        (tmp_path / ".ci-hub.yml").write_text(list_yaml, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result.exit_code == 1
        assert "Invalid config structure" in result.summary
        assert len(result.problems) > 0
        assert result.problems[0]["code"] == "CIHUB-VALIDATE-004"


# ==============================================================================
# Additional edge case tests
# ==============================================================================


class TestDetectEdgeCases:
    """Edge case tests for detect command.

    All tests verify CommandResult pattern:
    - Commands return CommandResult (not int)
    - Check result.exit_code for success/failure
    - Check result.data for structured output
    """

    def test_detect_empty_directory(self, tmp_path: Path) -> None:
        """Detect returns EXIT_FAILURE for empty directory with no language markers."""
        from cihub.exit_codes import EXIT_FAILURE

        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False)
        result = cmd_detect(args)
        assert result.exit_code == EXIT_FAILURE
        assert "Unable to detect language" in result.summary
        # Error message also available in data["items"]
        assert any("Unable to detect language" in item or "Error" in item for item in result.data.get("items", []))

    def test_detect_empty_directory_with_override(self, tmp_path: Path) -> None:
        """Detect succeeds with language override even for empty directory."""
        args = argparse.Namespace(repo=str(tmp_path), language="python", explain=False)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "python"

    def test_detect_gradle_project(self, tmp_path: Path) -> None:
        """Detect Java project from build.gradle."""
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "java"
        assert "build.gradle" in str(result.data.get("reasons", []))

    def test_detect_requirements_txt_python(self, tmp_path: Path) -> None:
        """Detect Python from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "python"

    def test_detect_setup_py_python(self, tmp_path: Path) -> None:
        """Detect Python from setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result.exit_code == 0
        assert result.data["language"] == "python"


class TestValidateEdgeCases:
    """Edge case tests for validate command."""

    def test_validate_malformed_yaml(self, tmp_path: Path) -> None:
        """Validate returns error for malformed YAML.

        Now returns CommandResult with error details instead of raising.
        """
        (tmp_path / ".ci-hub.yml").write_text("repo:\n  owner: test\n  - invalid list", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)

        # Malformed YAML returns CommandResult with error
        result = cmd_validate(args)
        assert result.exit_code == 1
        assert "Invalid YAML syntax" in result.summary
        assert len(result.problems) > 0
        assert result.problems[0]["code"] == "CIHUB-VALIDATE-003"

    def test_validate_empty_config(self, tmp_path: Path) -> None:
        """Validate handles empty config file."""
        (tmp_path / ".ci-hub.yml").write_text("", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        # Empty config should fail validation
        assert result.exit_code == 1
        assert "Validation failed" in result.summary


# ==============================================================================
# Tests for cmd_init
# ==============================================================================


class TestCmdInit:
    """Tests for the init command.

    NOTE: cmd_init now returns CommandResult (never int).
    Tests check result.exit_code instead of comparing result to int.
    """

    def test_init_python_project(self, tmp_path: Path) -> None:
        """Init creates config for Python project."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        # Check config was created
        config_path = tmp_path / ".ci-hub.yml"
        assert config_path.exists()
        # Check workflow was created
        workflow_path = tmp_path / ".github" / "workflows" / "hub-ci.yml"
        assert workflow_path.exists()

    def test_init_java_project(self, tmp_path: Path) -> None:
        """Init creates config for Java project."""
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        assert (tmp_path / ".ci-hub.yml").exists()
        assert (tmp_path / ".github" / "workflows" / "hub-ci.yml").exists()

    def test_init_hub_workflow_ref_override(self, tmp_path: Path) -> None:
        """Init pins hub workflow ref when provided."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            hub_workflow_ref="audit/test-ref",
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        config = yaml.safe_load((tmp_path / ".ci-hub.yml").read_text(encoding="utf-8"))
        assert config["repo"]["hub_workflow_ref"] == "audit/test-ref"
        workflow = (tmp_path / ".github" / "workflows" / "hub-ci.yml").read_text(encoding="utf-8")
        assert "hub-ci.yml@audit/test-ref" in workflow
        assert "hub_ref: ${{ vars.HUB_REF || 'audit/test-ref' }}" in workflow

    def test_init_fails_when_hub_vars_unverified(self, tmp_path: Path) -> None:
        """Init fails when hub vars cannot be verified and set_hub_vars is true."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language="python",
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            install_from="git",
            config_json=None,
            config_file=None,
            config_override=None,
            set_hub_vars=True,
            hub_repo="owner/repo",
            hub_ref="v1",
            json=False,
        )
        with patch("cihub.commands.init.set_repo_variables", return_value=(False, [], [])):
            result = cmd_init(args)
        assert result.exit_code == EXIT_FAILURE
        assert any(p.get("code") == "CIHUB-HUB-VARS-VERIFY" for p in (result.problems or []))

    def test_init_dry_run(self, tmp_path: Path) -> None:
        """Init dry run returns config in data without writing."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=True,
            apply=False,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        assert result.summary == "Dry run complete"
        assert "raw_output" in result.data  # Config YAML is in data
        # Config should NOT be written in dry run
        assert not (tmp_path / ".ci-hub.yml").exists()

    def test_init_with_subdir(self, tmp_path: Path) -> None:
        """Init handles subdir parameter."""
        subdir = "services/backend"
        (tmp_path / subdir).mkdir(parents=True)
        (tmp_path / subdir / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language="python",
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir=subdir,
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        config_path = tmp_path / ".ci-hub.yml"
        assert config_path.exists()
        config_text = config_path.read_text()
        assert subdir in config_text

    def test_init_sets_install_git_for_targets(self, tmp_path: Path) -> None:
        """Init forces git install when repo targets are configured."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language="python",
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            install_from="pypi",
            config_json=None,
            config_file=None,
            config_override={"repo": {"targets": [{"language": "python", "subdir": "python"}]}},
            set_hub_vars=False,
            hub_repo=None,
            hub_ref=None,
            json=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        config = yaml.safe_load((tmp_path / ".ci-hub.yml").read_text(encoding="utf-8"))
        install_cfg = config.get("install")
        if isinstance(install_cfg, dict):
            source = install_cfg.get("source")
        else:
            source = install_cfg
        assert source == "git"

    def test_init_sets_install_git_for_pytest_args(self, tmp_path: Path) -> None:
        """Init forces git install when pytest args/env are configured."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language="python",
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            install_from="pypi",
            config_json=None,
            config_file=None,
            config_override={"python": {"tools": {"pytest": {"args": ["-k", "not ui"]}}}},
            set_hub_vars=False,
            hub_repo=None,
            hub_ref=None,
            json=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        config = yaml.safe_load((tmp_path / ".ci-hub.yml").read_text(encoding="utf-8"))
        install_cfg = config.get("install")
        if isinstance(install_cfg, dict):
            source = install_cfg.get("source")
        else:
            source = install_cfg
        assert source == "git"

    def test_init_install_from_git_overrides(self, tmp_path: Path) -> None:
        """Init honors --install-from git by setting install.source."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language="python",
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            install_from="git",
            config_json=None,
            config_file=None,
            config_override=None,
            set_hub_vars=False,
            hub_repo=None,
            hub_ref=None,
            json=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        config = yaml.safe_load((tmp_path / ".ci-hub.yml").read_text(encoding="utf-8"))
        install_cfg = config.get("install")
        if isinstance(install_cfg, dict):
            source = install_cfg.get("source")
        else:
            source = install_cfg
        assert source == "git"

    def test_init_detects_language_from_subdir(self, tmp_path: Path) -> None:
        """Init detects language using the subdir when provided."""
        subdir = "services/java"
        (tmp_path / subdir).mkdir(parents=True)
        (tmp_path / subdir / "pom.xml").write_text("<project></project>", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir=subdir,
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        config_text = (tmp_path / ".ci-hub.yml").read_text(encoding="utf-8")
        assert "language: java" in config_text

    def test_init_missing_owner_uses_fallback(self, tmp_path: Path) -> None:
        """Init uses fallback owner when not provided and no git remote."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        # Warning is in problems, not stderr
        assert any("could not detect repo owner" in p.get("message", "") for p in result.problems)
        config_text = (tmp_path / ".ci-hub.yml").read_text()
        assert "unknown" in config_text or tmp_path.name in config_text

    def test_init_preserves_repo_targets(self, tmp_path: Path) -> None:
        """Init should not drop existing repo.targets on re-run."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
  targets:
    - language: python
      subdir: python
    - language: java
      subdir: java
language: java
java:
  version: '21'
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=True,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result.exit_code == 0
        data = yaml.safe_load((tmp_path / ".ci-hub.yml").read_text(encoding="utf-8"))
        targets = data.get("repo", {}).get("targets")
        assert isinstance(targets, list)
        assert {item.get("language") for item in targets} == {"python", "java"}


# ==============================================================================
# Tests for cmd_update
# ==============================================================================


class TestCmdUpdate:
    """Tests for the update command."""

    def test_update_creates_config_if_missing(self, tmp_path: Path) -> None:
        """Update creates config if it doesn't exist."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_update(args)
        assert result.exit_code == 0
        # Config should be created
        assert (tmp_path / ".ci-hub.yml").exists()
        assert (tmp_path / ".github" / "workflows" / "hub-ci.yml").exists()

    def test_update_existing_config(self, tmp_path: Path) -> None:
        """Update regenerates workflow from existing config."""
        # Create initial config
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_update(args)
        assert result.exit_code == 0
        # Workflow should be created/updated
        workflow_path = tmp_path / ".github" / "workflows" / "hub-ci.yml"
        assert workflow_path.exists()

    def test_update_dry_run(self, tmp_path: Path, capsys) -> None:
        """Update dry run shows changes without writing."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            dry_run=True,
            apply=False,
            force=False,
            fix_pom=False,
        )
        result = cmd_update(args)
        assert result.exit_code == 0
        # "Would write" is now in result.data["raw_output"] and result.data["items"]
        assert "Would write" in result.data.get("raw_output", "")
        assert any("Would write" in item for item in result.data.get("items", []))
