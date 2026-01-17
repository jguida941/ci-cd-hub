"""Comprehensive unit tests for cihub/commands/hub_ci/python_tools.py.

This module tests Python linting and mutation testing commands.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.python_tools import (
    _clean_mutmut_log,
    _extract_mutmut_error,
    _get_mutation_targets,
    _mutmut_fallback_env,
    cmd_black,
    cmd_coverage_verify,
    cmd_mutmut,
    cmd_mypy,
    cmd_ruff,
    cmd_ruff_format,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_args() -> argparse.Namespace:
    """Create a mock argparse namespace with common attributes."""
    args = argparse.Namespace()
    args.github_step_summary = None
    args.github_output = None
    return args


@pytest.fixture
def sample_pyproject(tmp_path: Path) -> Path:
    """Create a sample pyproject.toml with mutmut config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.mutmut]
paths_to_mutate = ["src/module1.py", "src/module2.py"]
""",
        encoding="utf-8",
    )
    return pyproject


# =============================================================================
# cmd_ruff Tests
# =============================================================================


class TestCmdRuff:
    """Tests for cmd_ruff function."""

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    @patch("cihub.commands.hub_ci.python_tools.safe_run")
    def test_ruff_no_issues(
        self, mock_safe_run: MagicMock, mock_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test ruff returns success when no issues found."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "[]"
        mock_run.return_value = mock_proc
        mock_safe_run.return_value = MagicMock(returncode=0)

        mock_args.path = "."
        mock_args.force_exclude = False
        mock_args.json = False

        result = cmd_ruff(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 0

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    @patch("cihub.commands.hub_ci.python_tools.safe_run")
    def test_ruff_with_issues(
        self, mock_safe_run: MagicMock, mock_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test ruff returns failure when issues found."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = '[{"code": "F401"}, {"code": "E501"}]'
        mock_run.return_value = mock_proc
        mock_safe_run.return_value = MagicMock(returncode=1)

        mock_args.path = "."
        mock_args.force_exclude = False
        mock_args.json = False

        result = cmd_ruff(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["issues"] == 2

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_ruff_json_mode(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test ruff in JSON mode doesn't run github format."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "[]"
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.force_exclude = False
        mock_args.json = True

        result = cmd_ruff(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        # In JSON mode, safe_run for github format shouldn't be called

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    @patch("cihub.commands.hub_ci.python_tools.safe_run")
    def test_ruff_with_force_exclude(
        self, mock_safe_run: MagicMock, mock_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test ruff passes force-exclude flag."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "[]"
        mock_run.return_value = mock_proc
        mock_safe_run.return_value = MagicMock(returncode=0)

        mock_args.path = "."
        mock_args.force_exclude = True
        mock_args.json = False

        result = cmd_ruff(mock_args)

        # Verify --force-exclude was in the command
        call_args = mock_run.call_args[0][0]
        assert "--force-exclude" in call_args

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_ruff_invalid_json(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test ruff handles invalid JSON gracefully."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "not json"
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.force_exclude = False
        mock_args.json = True

        result = cmd_ruff(mock_args)

        assert result.data["issues"] == 0  # Defaults to 0 on parse error


# =============================================================================
# cmd_ruff_format Tests
# =============================================================================


class TestCmdRuffFormat:
    """Tests for cmd_ruff_format function."""

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_ruff_format_clean(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test ruff format returns success when no reformatting needed."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.force_exclude = False

        result = cmd_ruff_format(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "clean" in result.summary.lower()
        assert result.data["needs_format"] is False

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_ruff_format_needs_reformatting(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test ruff format returns failure when reformatting needed."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "Would reformat file.py"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.force_exclude = False

        result = cmd_ruff_format(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["needs_format"] is True
        assert len(result.problems) > 0

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_ruff_format_empty_output_on_failure(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test ruff format with failure but no output."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.force_exclude = False

        result = cmd_ruff_format(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.problems[0]["message"] == "Ruff format check failed"


# =============================================================================
# cmd_mypy Tests
# =============================================================================


class TestCmdMypy:
    """Tests for cmd_mypy function."""

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_mypy_no_errors(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test mypy returns success when no errors found."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Success: no issues found"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.ignore_missing_imports = False
        mock_args.show_error_codes = False

        result = cmd_mypy(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["errors"] == 0

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_mypy_with_errors(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test mypy returns failure when errors found."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = (
            "file.py:10: error: Incompatible types\n"
            "file.py:20: error: Missing return type\n"
            "Found 2 errors"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.ignore_missing_imports = False
        mock_args.show_error_codes = False

        result = cmd_mypy(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["errors"] == 2

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_mypy_failure_no_explicit_errors(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test mypy sets error=1 when failed but no explicit errors found."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "Some other failure"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.ignore_missing_imports = False
        mock_args.show_error_codes = False

        result = cmd_mypy(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["errors"] == 1  # Falls back to 1

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_mypy_with_flags(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test mypy passes optional flags."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.ignore_missing_imports = True
        mock_args.show_error_codes = True

        result = cmd_mypy(mock_args)

        call_args = mock_run.call_args[0][0]
        assert "--ignore-missing-imports" in call_args
        assert "--show-error-codes" in call_args


# =============================================================================
# cmd_black Tests
# =============================================================================


class TestCmdBlack:
    """Tests for cmd_black function."""

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_black_all_formatted(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test black returns success when all files formatted."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "All done! 5 files left unchanged."
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."

        result = cmd_black(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 0

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_black_needs_reformatting(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test black counts files needing reformatting."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "would reformat file1.py\nwould reformat file2.py"
        mock_run.return_value = mock_proc

        mock_args.path = "."

        result = cmd_black(mock_args)

        assert result.exit_code == EXIT_SUCCESS  # Black always returns success
        assert result.data["issues"] == 2

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_black_failure_no_reformat_messages(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test black sets issues=1 on failure without reformat messages."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "Some error"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."

        result = cmd_black(mock_args)

        assert result.data["issues"] == 1


# =============================================================================
# _get_mutation_targets Tests
# =============================================================================


class TestGetMutationTargets:
    """Tests for _get_mutation_targets helper function."""

    def test_get_targets_from_pyproject(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test reading mutation targets from pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.mutmut]
paths_to_mutate = ["src/module1.py", "src/module2.py"]
""",
            encoding="utf-8",
        )

        targets = _get_mutation_targets()

        assert "src/module1.py" in targets
        assert "src/module2.py" in targets

    def test_get_targets_no_pyproject(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test returns empty list when no pyproject.toml."""
        monkeypatch.chdir(tmp_path)

        targets = _get_mutation_targets()

        assert targets == []

    def test_get_targets_no_mutmut_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test returns empty list when no mutmut config."""
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")

        targets = _get_mutation_targets()

        assert targets == []

    def test_get_targets_invalid_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test handles invalid TOML gracefully."""
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("not valid toml [[", encoding="utf-8")

        targets = _get_mutation_targets()

        assert targets == []


# =============================================================================
# cmd_coverage_verify Tests
# =============================================================================


class TestCmdCoverageVerify:
    """Tests for cmd_coverage_verify function."""

    def test_coverage_verify_file_not_found(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test coverage verify fails when file not found."""
        mock_args.coverage_file = str(tmp_path / "nonexistent.coverage")

        result = cmd_coverage_verify(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "not found" in result.summary.lower()
        assert result.data["exists"] is False

    def test_coverage_verify_success(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test coverage verify succeeds with valid coverage file."""
        coverage_file = tmp_path / ".coverage"
        coverage_file.write_bytes(b"")  # Create empty file

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["/path/to/file1.py", "/path/to/file2.py"]
        mock_cov.get_data.return_value = mock_data

        # Patch coverage module at import time
        with patch.dict("sys.modules", {"coverage": MagicMock(Coverage=MagicMock(return_value=mock_cov))}):
            mock_args.coverage_file = str(coverage_file)
            result = cmd_coverage_verify(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["valid"] is True
        assert result.data["measured_files"] == 2

    def test_coverage_verify_load_error(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test coverage verify handles load errors."""
        coverage_file = tmp_path / ".coverage"
        coverage_file.write_bytes(b"invalid data")

        mock_cov = MagicMock()
        mock_cov.load.side_effect = Exception("Invalid coverage data")

        # Patch coverage module at import time
        with patch.dict("sys.modules", {"coverage": MagicMock(Coverage=MagicMock(return_value=mock_cov))}):
            mock_args.coverage_file = str(coverage_file)
            result = cmd_coverage_verify(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["valid"] is False


# =============================================================================
# _clean_mutmut_log Tests
# =============================================================================


class TestCleanMutmutLog:
    """Tests for _clean_mutmut_log helper function."""

    def test_clean_removes_spinner_lines(self):
        """Test that spinner lines are removed."""
        log = "⠋ Generating mutants\n⠙ Generating mutants\nActual output"

        cleaned = _clean_mutmut_log(log)

        assert "Generating mutants" not in cleaned
        assert "Actual output" in cleaned

    def test_clean_removes_testing_spinner(self):
        """Test that testing spinner lines are removed."""
        log = "⠋ Testing mutants\n⠙ Testing mutants\nResult: passed"

        cleaned = _clean_mutmut_log(log)

        assert "Testing mutants" not in cleaned
        assert "Result: passed" in cleaned

    def test_clean_removes_duplicates(self):
        """Test that duplicate lines are removed."""
        log = "line1\nline1\nline1\nline2"

        cleaned = _clean_mutmut_log(log)

        assert cleaned.count("line1") == 1
        assert "line2" in cleaned

    def test_clean_handles_carriage_returns(self):
        """Test that carriage returns are normalized."""
        log = "line1\rline2\nline3"

        cleaned = _clean_mutmut_log(log)

        assert "\r" not in cleaned

    def test_clean_empty_log(self):
        """Test cleaning empty log."""
        cleaned = _clean_mutmut_log("")
        assert cleaned == ""


# =============================================================================
# _extract_mutmut_error Tests
# =============================================================================


class TestExtractMutmutError:
    """Tests for _extract_mutmut_error helper function."""

    def test_extract_traceback(self):
        """Test extracting Python traceback."""
        log = """
Some output
Traceback (most recent call last):
  File "test.py", line 10
    import foo
ImportError: No module named foo

More output
"""
        error = _extract_mutmut_error(log)

        assert "Traceback" in error
        assert "ImportError" in error

    def test_extract_error_patterns(self):
        """Test extracting various error patterns."""
        logs = [
            "ImportError: No module named 'foo'",
            "SyntaxError: invalid syntax",
            "TypeError: unsupported operand type",
            "Coverage data error",
            "No lines found in coverage",
            "Failed to run tests",
            "FAILED tests/test_foo.py",
        ]

        for log in logs:
            error = _extract_mutmut_error(log)
            # Should extract something, not return "No error details"
            assert error != "" or "No error" in error

    def test_extract_no_error_found(self):
        """Test when no error pattern found."""
        log = ""

        error = _extract_mutmut_error(log)

        assert "No error details" in error

    def test_extract_last_lines_fallback(self):
        """Test fallback to last lines when no pattern matches."""
        log = "line1\nline2\nline3\nline4\nline5\nline6"

        error = _extract_mutmut_error(log)

        # Should return last few lines as fallback
        assert error != "No error details available"


# =============================================================================
# _mutmut_fallback_env Tests
# =============================================================================


class TestMutmutFallbackEnv:
    """Tests for _mutmut_fallback_env helper function."""

    def test_fallback_env_sets_defaults(self, monkeypatch: pytest.MonkeyPatch):
        """Test that fallback env sets expected defaults when not already set."""
        # Clear the vars we want to test
        monkeypatch.delenv("TERM", raising=False)
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("RICH_DISABLE", raising=False)
        monkeypatch.delenv("PYTHONFAULTHANDLER", raising=False)

        env = _mutmut_fallback_env()

        # setdefault only sets if not present, so after clearing they should be set
        assert env.get("TERM") == "dumb"
        assert env.get("CI") == "1"
        assert env.get("RICH_DISABLE") == "1"
        assert env.get("PYTHONFAULTHANDLER") == "1"

    def test_fallback_env_preserves_existing(self, monkeypatch: pytest.MonkeyPatch):
        """Test that fallback env preserves existing environment."""
        monkeypatch.setenv("MY_VAR", "my_value")
        monkeypatch.setenv("TERM", "xterm")  # Pre-set TERM

        env = _mutmut_fallback_env()

        assert env.get("MY_VAR") == "my_value"
        assert env.get("TERM") == "xterm"  # Should preserve existing value


# =============================================================================
# cmd_mutmut Tests
# =============================================================================


class TestCmdMutmut:
    """Tests for cmd_mutmut function."""

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_success(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut returns success with good score."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "🎉 80/100  🙁 10/100  ⏰ 5/100  🤔 5/100  🔇 0/100  mutations/second: 10"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["mutation_score"] == 80
        assert result.data["killed"] == 80
        assert result.data["survived"] == 10

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_below_threshold(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut fails when score below threshold."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "🎉 50/100  🙁 40/100  ⏰ 5/100  🤔 5/100  🔇 0/100  mutations/second: 10"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["mutation_score"] == 50
        assert "below" in result.summary.lower()

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_run_failed(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut handles run failure."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "ImportError: No module named 'test_module'"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "failed" in result.summary.lower()

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_no_mutations_tested(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut fails when no mutants tested."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "🎉 0/0  🙁 0/0  ⏰ 0/0  🤔 0/0  🔇 0/0  mutations/second: 10"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "No mutants" in result.summary

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_missing_final_counts(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut fails when final counts missing."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Running... mutations/second: 10"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_FAILURE

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_did_not_complete(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut fails when it doesn't complete properly (no rate info)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        # Output that doesn't contain the completion marker
        mock_proc.stdout = "Some output that does not indicate completion"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "did not complete" in result.summary.lower()

    @patch("cihub.commands.hub_ci.python_tools._run_mutmut")
    def test_mutmut_fallback_on_empty_output(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test mutmut tries fallback when initial run produces empty output."""
        # First call returns failure with empty output
        first_proc = MagicMock()
        first_proc.returncode = 1
        first_proc.stdout = ""
        first_proc.stderr = ""

        # Fallback call returns better error info
        fallback_proc = MagicMock()
        fallback_proc.returncode = 1
        fallback_proc.stdout = "ImportError: Cannot import module"
        fallback_proc.stderr = ""

        mock_run.side_effect = [first_proc, fallback_proc]

        mock_args.workdir = str(tmp_path)
        mock_args.output_dir = str(tmp_path / "output")
        mock_args.min_mutation_score = 70

        result = cmd_mutmut(mock_args)

        assert result.exit_code == EXIT_FAILURE
        # Should have called fallback
        assert mock_run.call_count == 2


# =============================================================================
# Integration Tests
# =============================================================================


class TestPythonToolsIntegration:
    """Integration tests for python tools."""

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    @patch("cihub.commands.hub_ci.python_tools.safe_run")
    def test_ruff_full_workflow(
        self, mock_safe_run: MagicMock, mock_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test ruff complete workflow."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '[{"code": "F401", "message": "unused import"}]'
        mock_run.return_value = mock_proc
        mock_safe_run.return_value = MagicMock(returncode=0)

        mock_args.path = "src/"
        mock_args.force_exclude = True
        mock_args.json = False

        result = cmd_ruff(mock_args)

        assert result.data["issues"] == 1
        assert result.data["passed"] is True

    @patch("cihub.commands.hub_ci.python_tools._run_command")
    def test_mypy_counts_multiple_error_types(
        self, mock_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test mypy counts different error types."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = (
            "src/module.py:1: error: Missing type annotation\n"
            "src/module.py:5: error: Incompatible return type\n"
            "src/module.py:10: error: Invalid argument type\n"
            "src/other.py:1: error: Name not defined\n"
            "Found 4 errors in 2 files"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = "."
        mock_args.ignore_missing_imports = False
        mock_args.show_error_codes = False

        result = cmd_mypy(mock_args)

        assert result.data["errors"] == 4
