"""Tests for ci_runner Python tool runner functions.

Split from test_ci_runner.py for better organization.
Tests: _detect_mutmut_paths, run_mutmut, run_ruff, run_black, run_isort,
       run_mypy, run_pytest, run_bandit, run_pip_audit, run_sbom
"""

# TEST-METRICS:

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from cihub.ci_runner import (
    _detect_mutmut_paths,
    run_black,
    run_isort,
    run_mutmut,
    run_mypy,
    run_ruff,
)


class TestDetectMutmutPaths:
    """Tests for _detect_mutmut_paths function."""

    def test_detects_src_directory(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()

        result = _detect_mutmut_paths(tmp_path)

        assert result == "src/"

    def test_detects_package_with_init(self, tmp_path: Path) -> None:
        (tmp_path / "mypackage").mkdir()
        (tmp_path / "mypackage" / "__init__.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "mypackage/"

    def test_ignores_test_directories(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "__init__.py").write_text("")
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "app/"

    def test_returns_dot_when_no_package_found(self, tmp_path: Path) -> None:
        (tmp_path / "file.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "file.py"

    def test_skips_setup_py_for_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").write_text("")
        (tmp_path / "app.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "app.py"


class TestRunMutmut:
    """Tests for run_mutmut function."""

    def test_temp_config_persists_until_results(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mypackage").mkdir()
        (tmp_path / "mypackage" / "__init__.py").write_text("")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "run ok"
        mock_proc.stderr = ""

        def _fake_results(cmd: list[str], cwd: Path):
            config_path = tmp_path / "setup.cfg"
            assert config_path.exists()
            return MagicMock(stdout="killed\nsurvived\n", stderr="")

        with (
            patch("cihub.core.ci_runner.shared._run_tool_command", return_value=mock_proc),
            patch("cihub.core.ci_runner.shared._run_command", side_effect=_fake_results),
        ):
            result = run_mutmut(tmp_path, output_dir, 60)

        assert result.metrics["mutation_score"] == 50
        assert not (tmp_path / "setup.cfg").exists()

    def test_meta_fallback_when_results_empty(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (tmp_path / "mypackage").mkdir()
        (tmp_path / "mypackage" / "__init__.py").write_text("")
        mutants_dir = tmp_path / "mutants"
        mutants_dir.mkdir()
        (mutants_dir / "app.py.meta").write_text(json.dumps({"exit_code_by_key": {"a": 1, "b": 1, "c": 0}}))

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "run ok"
        mock_proc.stderr = ""

        with (
            patch("cihub.core.ci_runner.shared._run_tool_command", return_value=mock_proc),
            patch("cihub.core.ci_runner.shared._run_command", return_value=MagicMock(stdout="", stderr="")),
        ):
            result = run_mutmut(tmp_path, output_dir, 60)

        assert result.metrics["mutation_killed"] == 2
        assert result.metrics["mutation_survived"] == 1
        assert result.metrics["mutation_score"] == 67


class TestRunRuff:
    """Tests for run_ruff function."""

    def test_runs_ruff_and_parses_output(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '[{"code": "E501", "message": "Line too long"}]'
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_ruff(tmp_path, output_dir)

        assert result.tool == "ruff"
        assert result.ran is True
        assert result.success is True
        assert result.metrics["ruff_errors"] == 1

    def test_counts_security_issues(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = '[{"code": "S101"}, {"code": "S105"}, {"code": "E501"}]'
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_ruff(tmp_path, output_dir)

        assert result.metrics["ruff_security"] == 2
        assert result.metrics["ruff_errors"] == 3


class TestRunBlack:
    """Tests for run_black function."""

    def test_counts_reformat_needed(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "would reformat file1.py\nwould reformat file2.py\n"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_black(tmp_path, output_dir)

        assert result.tool == "black"
        assert result.success is False
        assert result.metrics["black_issues"] == 2


class TestRunIsort:
    """Tests for run_isort function."""

    def test_counts_error_lines(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "ERROR: file1.py\nERROR: file2.py\nSkipping"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_isort(tmp_path, output_dir)

        assert result.tool == "isort"
        assert result.metrics["isort_issues"] == 2

    def test_uses_black_profile(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        captured: dict[str, object] = {}

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured["cmd"] = cmd
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.python_tools.shared._run_tool_command", side_effect=_fake_run):
            run_isort(tmp_path, output_dir, True)

        cmd = captured.get("cmd")
        assert isinstance(cmd, list)
        assert "--profile" in cmd
        assert cmd[cmd.index("--profile") + 1] == "black"

    def test_skips_profile_when_disabled(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        captured: dict[str, object] = {}

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured["cmd"] = cmd
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.python_tools.shared._run_tool_command", side_effect=_fake_run):
            run_isort(tmp_path, output_dir, False)

        cmd = captured.get("cmd")
        assert isinstance(cmd, list)
        assert "--profile" not in cmd


class TestRunMypy:
    """Tests for run_mypy function."""

    def test_counts_errors(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "file.py:1: error: Missing return\nfile.py:5: error: Type mismatch"
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_mypy(tmp_path, output_dir)

        assert result.tool == "mypy"
        assert result.metrics["mypy_errors"] == 2


class TestRunPytest:
    """Tests for run_pytest function."""

    def test_runs_pytest_successfully(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_pytest

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # pytest writes to output_dir (pytest-junit.xml and coverage.xml)
        (output_dir / "pytest-junit.xml").write_text(
            '<?xml version="1.0"?><testsuite tests="5" failures="0" errors="0" skipped="1" time="1.0"/>'
        )
        (output_dir / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="0.85"><packages/></coverage>'
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_pytest(tmp_path, output_dir)

        assert result.tool == "pytest"
        assert result.ran is True
        assert result.success is True
        assert result.metrics["coverage"] == 85
        assert result.metrics["tests_passed"] == 4
        assert result.metrics["tests_skipped"] == 1

    def test_pytest_failure(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_pytest

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # pytest writes to output_dir
        (output_dir / "pytest-junit.xml").write_text(
            '<?xml version="1.0"?><testsuite tests="5" failures="2" errors="0" skipped="0" time="1.0"/>'
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_pytest(tmp_path, output_dir)

        assert result.tool == "pytest"
        assert result.success is False
        assert result.metrics["tests_failed"] == 2

    def test_pytest_args_and_env_passed(self, tmp_path: Path) -> None:
        from cihub.core.ci_runner import python_tools

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        (output_dir / "pytest-junit.xml").write_text(
            '<?xml version="1.0"?><testsuite tests="1" failures="0" errors="0" skipped="0" time="1.0"/>'
        )
        (output_dir / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="1.0"><packages/></coverage>'
        )

        captured: dict[str, object] = {}

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            captured["cmd"] = cmd
            captured["env"] = env
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            return mock_proc

        with patch("cihub.core.ci_runner.python_tools.shared._run_tool_command", side_effect=_fake_run):
            result = python_tools.run_pytest(
                tmp_path,
                output_dir,
                False,
                ["-k", "not ui"],
                {"QT_QPA_PLATFORM": "offscreen"},
            )

        assert result.success is True
        assert "-k" in captured["cmd"]
        assert captured["env"]["QT_QPA_PLATFORM"] == "offscreen"

    def test_pytest_retries_without_xvfb_on_timeout(self, tmp_path: Path) -> None:
        from cihub.core.ci_runner import python_tools

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        calls: list[list[str]] = []

        def _fake_run(tool, cmd, workdir, output_dir, timeout=None, env=None):
            calls.append(cmd)
            if len(calls) == 1:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=124,
                    stdout="",
                    stderr="Command timed out after 600s: xvfb-run pytest",
                )

            (output_dir / "pytest-junit.xml").write_text(
                '<?xml version="1.0"?><testsuite tests="1" failures="0" errors="0" skipped="0" time="1.0"/>'
            )
            (output_dir / "coverage.xml").write_text(
                '<?xml version="1.0"?><coverage line-rate="1.0"><packages/></coverage>'
            )
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with (
            patch("cihub.core.ci_runner.python_tools._should_use_xvfb", return_value=True),
            patch("cihub.core.ci_runner.python_tools.shutil.which", return_value="/usr/bin/xvfb-run"),
            patch("cihub.core.ci_runner.python_tools.shared._run_tool_command", side_effect=_fake_run),
        ):
            result = python_tools.run_pytest(tmp_path, output_dir)

        assert len(calls) == 2
        assert calls[0][0].endswith("xvfb-run")
        assert calls[1][0] == "pytest"
        assert result.success is True


class TestRunBandit:
    """Tests for run_bandit function."""

    def test_parses_bandit_json(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_bandit

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Write the report file that bandit will create
        (output_dir / "bandit-report.json").write_text(
            json.dumps(
                {
                    "results": [
                        {"issue_severity": "HIGH", "test_id": "B101"},
                        {"issue_severity": "MEDIUM", "test_id": "B105"},
                        {"issue_severity": "LOW", "test_id": "B106"},
                    ]
                }
            )
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_bandit(tmp_path, output_dir)

        assert result.tool == "bandit"
        assert result.ran is True
        assert result.metrics["bandit_high"] == 1
        assert result.metrics["bandit_medium"] == 1
        assert result.metrics["bandit_low"] == 1


class TestRunPipAudit:
    """Tests for run_pip_audit function."""

    def test_parses_vulnerabilities(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_pip_audit

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # pip_audit uses dependency dict format
        (output_dir / "pip-audit-report.json").write_text(
            json.dumps(
                {
                    "dependencies": [
                        {"name": "requests", "vulns": [{"id": "CVE-2023-001"}]},
                        {
                            "name": "flask",
                            "vulns": [{"id": "CVE-2023-002"}, {"id": "CVE-2023-003"}],
                        },
                    ]
                }
            )
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_pip_audit(tmp_path, output_dir)

        assert result.tool == "pip_audit"
        assert result.ran is True
        assert result.metrics["pip_audit_vulns"] == 3


class TestRunSbom:
    """Tests for run_sbom function."""

    def test_generates_sbom(self, tmp_path: Path) -> None:
        from cihub.ci_runner import run_sbom

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create pyproject.toml
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        # syft writes stdout which gets saved to sbom.cyclonedx.json
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"bomFormat": "CycloneDX", "components": []}'
        mock_proc.stderr = ""

        with patch("cihub.core.ci_runner.shared._run_command", return_value=mock_proc):
            result = run_sbom(tmp_path, output_dir)

        assert result.tool == "sbom"
        assert result.ran is True
        assert result.success is True
        # Verify the output file was created
        assert (output_dir / "sbom.cyclonedx.json").exists()
