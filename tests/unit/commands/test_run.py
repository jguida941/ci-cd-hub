"""Tests for cihub.commands.run module."""

# TEST-METRICS:
#   Coverage: 100.0%

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from cihub.ci_runner import ToolResult
from cihub.commands.run import _resolve_candidate_languages, _tool_enabled, cmd_run
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


class TestToolEnabled:
    """Tests for _tool_enabled helper."""

    def test_returns_true_for_bool_true(self) -> None:
        config = {"python": {"tools": {"ruff": True}}}
        assert _tool_enabled(config, "ruff", "python") is True

    def test_returns_false_for_bool_false(self) -> None:
        config = {"python": {"tools": {"ruff": False}}}
        assert _tool_enabled(config, "ruff", "python") is False

    def test_returns_enabled_from_dict(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_enabled(config, "pytest", "python") is True

    def test_returns_false_when_enabled_is_false(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": False}}}}
        assert _tool_enabled(config, "pytest", "python") is False

    def test_returns_false_for_missing_tool(self) -> None:
        config = {"python": {"tools": {}}}
        assert _tool_enabled(config, "missing", "python") is False

    def test_returns_false_for_non_dict_python_block(self) -> None:
        config: dict[str, Any] = {"python": "not_a_dict"}
        assert _tool_enabled(config, "ruff", "python") is False

    def test_returns_false_for_non_dict_tools(self) -> None:
        config = {"python": {"tools": "not_a_dict"}}
        assert _tool_enabled(config, "ruff", "python") is False


class TestCandidateLanguages:
    """Tests for language resolution helper."""

    def test_python_only_tool(self) -> None:
        assert _resolve_candidate_languages("ruff") == ["python"]

    def test_java_only_tool(self) -> None:
        assert _resolve_candidate_languages("owasp") == ["java"]

    def test_multi_language_tool(self) -> None:
        candidates = _resolve_candidate_languages("trivy")
        assert "python" in candidates
        assert "java" in candidates


class TestCmdRun:
    """Tests for cmd_run command."""

    def test_returns_usage_error_for_unsupported_tool(self, tmp_path: Path) -> None:
        """Test unsupported tool returns EXIT_USAGE."""
        (tmp_path / ".ci-hub.yml").write_text("language: python\nrepo:\n  owner: test\n  name: repo\n")
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="unsupported",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            result = cmd_run(args)

        assert result.exit_code == EXIT_USAGE
        assert "Unsupported tool" in result.summary

    def test_skips_disabled_tool(self, tmp_path: Path) -> None:
        """Test skips disabled tool without --force."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"ruff": False}},
            }
            result = cmd_run(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "skipped" in result.summary

    def test_runs_tool_when_enabled(self, tmp_path: Path) -> None:
        """Test runs tool when enabled."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = True
        mock_result.to_payload.return_value = {"tool": "ruff", "ran": True}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "ruff" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"ruff": True}},
            }
            result = cmd_run(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "passed" in result.summary

    def test_runs_tool_with_force_flag(self, tmp_path: Path) -> None:
        """Test --force runs tool even when disabled."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="bandit",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=True,  # Force run
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = True
        mock_result.to_payload.return_value = {"tool": "bandit"}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "bandit" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"bandit": False}},  # Disabled
            }
            result = cmd_run(args)

        assert result.exit_code == EXIT_SUCCESS

    def test_returns_failure_when_tool_fails(self, tmp_path: Path) -> None:
        """Test returns failure when tool fails."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="pytest",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=True,
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = False
        mock_result.to_payload.return_value = {"tool": "pytest", "ran": True}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "pytest" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {"language": "python"}
            result = cmd_run(args)

        assert result.exit_code == EXIT_FAILURE
        assert "failed" in result.summary

    def test_returns_failure_on_config_load_error(self, tmp_path: Path) -> None:
        """Test returns failure when config fails to load."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.side_effect = Exception("Config error")
            result = cmd_run(args)

        assert result.exit_code == EXIT_FAILURE
        assert "Failed to load config" in result.summary

    def test_returns_failure_for_missing_workdir(self, tmp_path: Path) -> None:
        """Test returns failure when workdir doesn't exist."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir="nonexistent",
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            result = cmd_run(args)

        assert result.exit_code == EXIT_FAILURE
        assert "Workdir not found" in result.summary

    def test_returns_failure_when_tool_not_found(self, tmp_path: Path) -> None:
        """Test returns failure when tool executable not found."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=True,
        )

        def raise_not_found(*args: Any, **kwargs: Any) -> None:
            raise FileNotFoundError("ruff not found")

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", return_value=raise_not_found),
        ):
            mock_load.return_value = {"language": "python"}
            result = cmd_run(args)

        assert result.exit_code == EXIT_FAILURE
        assert "not found" in result.summary

    def test_mutmut_uses_config_timeout(self, tmp_path: Path) -> None:
        """Test mutmut runner receives timeout from config."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="mutmut",
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=True,
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = True
        mock_result.to_payload.return_value = {"tool": "mutmut"}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "mutmut" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"mutmut": {"timeout_minutes": 30}}},
            }
            cmd_run(args)

        # Verify timeout was passed (30 min * 60 = 1800 seconds)
        mock_runner.assert_called_once()
        call_args = mock_runner.call_args[0]
        assert call_args[2] == 1800  # timeout in seconds

    def test_uses_workdir_from_config(self, tmp_path: Path) -> None:
        """Test uses workdir from repo.subdir in config."""
        subdir = tmp_path / "src"
        subdir.mkdir()

        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir=None,  # Not specified
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=True,
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = True
        mock_result.to_payload.return_value = {"tool": "ruff"}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "ruff" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {
                "language": "python",
                "repo": {"subdir": "src"},
            }
            cmd_run(args)

        # Verify the runner was called with the subdir path
        mock_runner.assert_called_once()
        call_args = mock_runner.call_args
        workdir_arg = call_args[0][0]
        assert str(workdir_arg).endswith("src")

    def test_writes_output_to_custom_path(self, tmp_path: Path) -> None:
        """Test writes output to custom path when specified."""
        output_file = tmp_path / "custom_output.json"
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=True,
            workdir=None,
            output=str(output_file),
            output_dir=str(tmp_path / ".cihub"),
            force=True,
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = True
        mock_result.to_payload.return_value = {"tool": "ruff"}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "ruff" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {"language": "python"}
            cmd_run(args)

        # Verify write_json was called with custom path
        mock_result.write_json.assert_called_once()
        path_arg = mock_result.write_json.call_args[0][0]
        assert str(path_arg) == str(output_file)

    def test_success_returns_command_result_with_output_info(self, tmp_path: Path) -> None:
        """Test successful run returns CommandResult with output path in data."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=False,  # Doesn't matter now - always returns CommandResult
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=True,
        )

        mock_result = MagicMock(spec=ToolResult)
        mock_result.success = True
        mock_result.to_payload.return_value = {"tool": "ruff", "ran": True, "success": True}
        mock_runner = MagicMock(return_value=mock_result)

        def _fake_get_runner(tool: str, language: str):
            if tool == "ruff" and language == "python":
                return mock_runner
            return None

        with (
            patch("cihub.commands.run.load_ci_config") as mock_load,
            patch("cihub.commands.run.get_runner", side_effect=_fake_get_runner),
        ):
            mock_load.return_value = {"language": "python"}
            result = cmd_run(args)

        # Now returns CommandResult instead of int
        assert result.exit_code == EXIT_SUCCESS
        assert "items" in result.data
        assert any("Wrote output" in item for item in result.data["items"])

    def test_config_error_returns_command_result(self, tmp_path: Path) -> None:
        """Test config error returns CommandResult with problem details."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="ruff",
            json=False,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.side_effect = Exception("Config missing")
            result = cmd_run(args)

        # Returns CommandResult with error info
        assert result.exit_code == EXIT_FAILURE
        assert "Failed to load config" in result.summary
        assert any(p["code"] == "CIHUB-RUN-001" for p in result.problems)

    def test_unsupported_tool_returns_command_result(self, tmp_path: Path) -> None:
        """Test unsupported tool returns CommandResult with problem details."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="unknown_tool",
            json=False,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            result = cmd_run(args)

        # Returns CommandResult with error info
        assert result.exit_code == EXIT_USAGE
        assert "Unsupported tool" in result.summary
        assert any(p["code"] == "CIHUB-RUN-003" for p in result.problems)

    def test_disabled_tool_returns_command_result(self, tmp_path: Path) -> None:
        """Test disabled tool returns CommandResult with skipped status."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="bandit",
            json=False,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"bandit": False}},
            }
            result = cmd_run(args)

        # Returns CommandResult indicating tool was skipped
        assert result.exit_code == EXIT_SUCCESS
        assert "skipped" in result.summary
        assert "items" in result.data

    def test_pip_audit_normalizes_to_pip_audit(self, tmp_path: Path) -> None:
        """Test pip-audit tool name is normalized to pip_audit internally."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            tool="pip-audit",  # Hyphenated form
            json=True,
            workdir=None,
            output=None,
            output_dir=str(tmp_path / ".cihub"),
            force=False,
        )

        with patch("cihub.commands.run.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"pip_audit": False}},  # Config uses underscore
            }
            result = cmd_run(args)

        # Should recognize pip-audit as pip_audit and skip it
        assert result.exit_code == EXIT_SUCCESS
        assert "skipped" in result.summary
