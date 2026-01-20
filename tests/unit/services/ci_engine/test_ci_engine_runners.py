"""Tests for CI engine tool runner functions.

Split from test_ci_engine.py for better organization.
Tests: _run_dep_command, _install_python_dependencies, _run_python_tools, _run_java_tools
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.services.ci_engine import (
    JAVA_RUNNERS,
    PYTHON_RUNNERS,
    _install_python_dependencies,
    _run_dep_command,
    _run_java_tools,
    _run_python_tools,
)


class TestRunDepCommand:
    """Tests for _run_dep_command function."""

    def test_success_returns_true(self, tmp_path: Path) -> None:
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc):
            result = _run_dep_command(["echo", "hello"], tmp_path, "test", problems)
        assert result is True
        assert len(problems) == 0

    def test_failure_returns_false_and_adds_problem(self, tmp_path: Path) -> None:
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "error occurred"
        mock_proc.stdout = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = _run_dep_command(["false"], tmp_path, "test cmd", problems)
        assert result is False
        assert len(problems) == 1
        assert "test cmd failed" in problems[0]["message"]


class TestInstallPythonDependencies:
    """Tests for _install_python_dependencies function."""

    def test_skips_when_install_disabled(self, tmp_path: Path) -> None:
        config = {"python": {"dependencies": {"install": False}}}
        problems: list = []
        _install_python_dependencies(config, tmp_path, problems)
        assert len(problems) == 0

    def test_runs_custom_commands(self, tmp_path: Path) -> None:
        config = {"python": {"dependencies": {"commands": ["pip install pytest"]}}}
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc):
            _install_python_dependencies(config, tmp_path, problems)
        assert len(problems) == 0

    def test_installs_qt_system_deps_when_qt_dependency_present(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = 'test'\ndependencies = ['PySide6']\n"
        )
        config: dict = {}
        problems: list = []
        calls: list[list[str]] = []

        def fake_run(cmd, workdir, label, problems):
            calls.append(cmd)
            return True

        def fake_which(name: str):
            if name == "apt-get":
                return "/usr/bin/apt-get"
            if name == "sudo":
                return "/usr/bin/sudo"
            return None

        with patch("cihub.services.ci_engine.python_tools._run_dep_command", side_effect=fake_run), patch(
            "cihub.services.ci_engine.python_tools.shutil.which",
            side_effect=fake_which,
        ), patch("cihub.services.ci_engine.python_tools.sys.platform", "linux"):
            _install_python_dependencies(config, tmp_path, problems)

        assert any("libegl1" in part for cmd in calls for part in cmd)

    def test_installs_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("pytest\n")
        config: dict = {}
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            _install_python_dependencies(config, tmp_path, problems)
        # Should have called pip install -r requirements.txt
        assert mock_run.called

    def test_installs_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        config: dict = {}
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            _install_python_dependencies(config, tmp_path, problems)
        assert mock_run.called


class TestRunPythonTools:
    """Tests for _run_python_tools function."""

    def test_runs_enabled_tools(self, tmp_path: Path) -> None:
        from cihub.ci_runner import ToolResult

        workdir = tmp_path / "repo"
        workdir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {"python": {"tools": {"ruff": {"enabled": True}}}}
        problems: list = []

        mock_result = ToolResult(tool="ruff", ran=True, success=True, metrics={"ruff_errors": 0})
        # Create a custom runners dict with mock ruff
        mock_runners = dict(PYTHON_RUNNERS)
        mock_runners["ruff"] = lambda *args, **kwargs: mock_result
        outputs, ran, success = _run_python_tools(config, tmp_path, "repo", output_dir, problems, mock_runners)

        assert ran.get("ruff") is True
        assert success.get("ruff") is True

    def test_warns_for_unsupported_tool(self, tmp_path: Path) -> None:
        workdir = tmp_path / "repo"
        workdir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {"python": {"tools": {"codeql": {"enabled": True}}}}  # codeql has no runner
        problems: list = []

        _run_python_tools(config, tmp_path, "repo", output_dir, problems, PYTHON_RUNNERS)

        # Should have warned about unsupported tool
        unsupported_warnings = [p for p in problems if "not supported" in p["message"]]
        assert len(unsupported_warnings) == 1

    def test_bandit_success_respects_fail_on_flags(self, tmp_path: Path) -> None:
        from cihub.ci_runner import ToolResult

        workdir = tmp_path / "repo"
        workdir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {
            "python": {
                "tools": {
                    "bandit": {
                        "enabled": True,
                        "fail_on_high": True,
                        "fail_on_medium": False,
                        "fail_on_low": False,
                    }
                }
            }
        }
        problems: list = []

        mock_result = ToolResult(
            tool="bandit",
            ran=True,
            success=False,
            metrics={"bandit_high": 0, "bandit_medium": 0, "bandit_low": 5, "parse_error": False},
        )
        mock_runners = dict(PYTHON_RUNNERS)
        mock_runners["bandit"] = lambda *args, **kwargs: mock_result
        _, ran, success = _run_python_tools(config, tmp_path, "repo", output_dir, problems, mock_runners)

        assert ran.get("bandit") is True
        assert success.get("bandit") is True

    def test_raises_for_missing_workdir(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config: dict = {}
        problems: list = []

        with pytest.raises(FileNotFoundError):
            _run_python_tools(config, tmp_path, "nonexistent", output_dir, problems, PYTHON_RUNNERS)


class TestRunJavaTools:
    """Tests for _run_java_tools function."""

    def test_runs_java_build(self, tmp_path: Path) -> None:
        from cihub.ci_runner import ToolResult

        workdir = tmp_path / "repo"
        workdir.mkdir()
        (workdir / "pom.xml").write_text("<project/>")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {"java": {"tools": {"jacoco": {"enabled": False}}}}
        problems: list = []

        mock_build = ToolResult(tool="build", ran=True, success=True, metrics={})
        with patch("cihub.services.ci_engine.java_tools.run_java_build", return_value=mock_build):
            outputs, ran, success = _run_java_tools(
                config,
                tmp_path,
                "repo",
                output_dir,
                "maven",
                problems,
                JAVA_RUNNERS,
            )

        assert "build" in outputs

    def test_raises_for_missing_workdir(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config: dict = {}
        problems: list = []

        with pytest.raises(FileNotFoundError):
            _run_java_tools(config, tmp_path, "nonexistent", output_dir, "maven", problems, JAVA_RUNNERS)
