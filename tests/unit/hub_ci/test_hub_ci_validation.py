"""Tests for hub_ci validation commands.

Split from test_hub_ci.py for better organization.
Tests: cmd_validate_profiles, cmd_enforce, cmd_verify_matrix_keys,
       cmd_quarantine_check, cmd_repo_check, cmd_source_check
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import os
from pathlib import Path
from unittest import mock


class TestCmdValidateProfiles:
    """Tests for cmd_validate_profiles command."""

    def test_validates_yaml_files(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_validate_profiles
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "test.yaml").write_text("key: value\n")

        args = argparse.Namespace(profiles_dir=str(profiles_dir))
        result = cmd_validate_profiles(args)
        # CommandResult migration: check exit_code instead of direct comparison
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS

    def test_fails_on_non_dict_yaml(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_validate_profiles
        from cihub.exit_codes import EXIT_FAILURE
        from cihub.types import CommandResult

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "bad.yaml").write_text("- list\n- item\n")

        args = argparse.Namespace(profiles_dir=str(profiles_dir))
        result = cmd_validate_profiles(args)
        # CommandResult migration: check exit_code instead of direct comparison
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_FAILURE


class TestCmdEnforce:
    """Tests for cmd_enforce command."""

    def test_returns_success_when_all_pass(self) -> None:
        from cihub.commands.hub_ci import cmd_enforce
        from cihub.exit_codes import EXIT_SUCCESS

        env = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            args = argparse.Namespace()
            result = cmd_enforce(args)
            assert result.exit_code == EXIT_SUCCESS

    def test_returns_failure_when_check_fails(self) -> None:
        from cihub.commands.hub_ci import cmd_enforce
        from cihub.exit_codes import EXIT_FAILURE

        env = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "failure",  # This one fails
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            args = argparse.Namespace()
            result = cmd_enforce(args)
            assert result.exit_code == EXIT_FAILURE

    def test_ignores_skipped_results(self) -> None:
        from cihub.commands.hub_ci import cmd_enforce
        from cihub.exit_codes import EXIT_SUCCESS

        env = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "skipped",  # Skipped, not failure
            "RESULT_MUTATION": "skipped",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "skipped",
            "RESULT_SCORECARD": "skipped",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            args = argparse.Namespace()
            result = cmd_enforce(args)
            assert result.exit_code == EXIT_SUCCESS


class TestVerifyMatrixKeys:
    """Tests for verify-matrix-keys helper."""

    def test_verify_matrix_keys_passes(self, tmp_path: Path, monkeypatch) -> None:
        from cihub.commands import hub_ci
        from cihub.commands.hub_ci import validation
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        hub = tmp_path
        (hub / ".github" / "workflows").mkdir(parents=True)
        (hub / ".github" / "workflows" / "hub-run-all.yml").write_text(
            "matrix.owner\n",
            encoding="utf-8",
        )

        # Patch project_root in the validation module where it's used
        monkeypatch.setattr(validation, "project_root", lambda: hub)
        result = hub_ci.cmd_verify_matrix_keys(argparse.Namespace())
        # CommandResult migration: check exit_code
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS

    def test_verify_matrix_keys_fails_on_missing(self, tmp_path: Path, monkeypatch) -> None:
        from cihub.commands import hub_ci
        from cihub.commands.hub_ci import validation
        from cihub.exit_codes import EXIT_FAILURE
        from cihub.types import CommandResult

        hub = tmp_path
        (hub / ".github" / "workflows").mkdir(parents=True)
        (hub / ".github" / "workflows" / "hub-run-all.yml").write_text(
            "matrix.missing_key\n",
            encoding="utf-8",
        )

        # Patch project_root in the validation module where it's used
        monkeypatch.setattr(validation, "project_root", lambda: hub)
        result = hub_ci.cmd_verify_matrix_keys(argparse.Namespace())
        # CommandResult migration: check exit_code
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_FAILURE


class TestQuarantineCheck:
    """Tests for quarantine-check helper."""

    def test_quarantine_check_passes(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_quarantine_check
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        args = argparse.Namespace(path=str(tmp_path))
        result = cmd_quarantine_check(args)
        # CommandResult migration: check exit_code
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS

    def test_quarantine_check_fails(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_quarantine_check
        from cihub.exit_codes import EXIT_FAILURE
        from cihub.types import CommandResult

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from _quarantine import thing\n", encoding="utf-8")

        args = argparse.Namespace(path=str(tmp_path))
        result = cmd_quarantine_check(args)
        # CommandResult migration: check exit_code
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_FAILURE


class TestCmdRepoCheck:
    """Tests for cmd_repo_check command."""

    def test_repo_present_outputs_true(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_repo_check
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        repo_path.mkdir(parents=True)
        output_path = tmp_path / "outputs.txt"
        git_marker = repo_path / ".git"

        args = argparse.Namespace(
            path=str(repo_path),
            owner="owner",
            name="repo",
            output=str(output_path),
            github_output=False,
        )
        original_exists = Path.exists

        def fake_exists(self: Path) -> bool:
            if self == git_marker:
                return True
            return original_exists(self)

        with mock.patch.object(Path, "exists", fake_exists):
            result = cmd_repo_check(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["present"] is True
        assert "present=true" in output_path.read_text(encoding="utf-8")

    def test_repo_missing_outputs_false(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_repo_check
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            owner="owner",
            name="repo",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_repo_check(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["present"] is False
        assert "present=false" in output_path.read_text(encoding="utf-8")


class TestCmdSourceCheck:
    """Tests for cmd_source_check command."""

    def test_detects_python_source(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_source_check
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            language="python",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_source_check(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["has_source"] is True
        assert "has_source=true" in output_path.read_text(encoding="utf-8")

    def test_detects_java_source(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_source_check
        from cihub.exit_codes import EXIT_SUCCESS
        from cihub.types import CommandResult

        repo_path = tmp_path / "repo"
        (repo_path / "src").mkdir(parents=True)
        (repo_path / "src" / "App.java").write_text("class App {}", encoding="utf-8")
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            language="java",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_source_check(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["has_source"] is True
        assert "has_source=true" in output_path.read_text(encoding="utf-8")
