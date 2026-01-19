"""Comprehensive unit tests for cihub/commands/hub_ci/security.py.

This module tests security scanning commands: bandit, pip-audit, OWASP, and ruff security rules.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.security import (
    _validate_scan_paths,
    cmd_bandit,
    cmd_pip_audit,
    cmd_security_bandit,
    cmd_security_owasp,
    cmd_security_pip_audit,
    cmd_security_ruff,
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
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repository structure for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n", encoding="utf-8")
    return tmp_path


# =============================================================================
# _validate_scan_paths Tests
# =============================================================================


class TestValidateScanPaths:
    """Tests for the _validate_scan_paths helper function."""

    def test_valid_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that valid relative paths are accepted."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        valid, problems = _validate_scan_paths(["src"])
        assert valid == ["src"]
        assert problems == []

    def test_valid_multiple_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that multiple valid paths work."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()

        valid, problems = _validate_scan_paths(["src", "tests"])
        assert sorted(valid) == ["src", "tests"]
        assert problems == []

    def test_path_traversal_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that path traversal attempts are blocked."""
        monkeypatch.chdir(tmp_path)

        valid, problems = _validate_scan_paths(["../etc/passwd"])
        assert valid == []
        assert len(problems) == 1
        assert "traversal blocked" in problems[0]

    def test_absolute_path_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that absolute paths are blocked."""
        monkeypatch.chdir(tmp_path)

        valid, problems = _validate_scan_paths(["/etc/passwd"])
        assert valid == []
        assert len(problems) == 1
        assert "traversal blocked" in problems[0]

    def test_backslash_path_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that backslash paths are blocked (Windows-style traversal)."""
        monkeypatch.chdir(tmp_path)

        valid, problems = _validate_scan_paths(["..\\etc\\passwd"])
        assert valid == []
        assert len(problems) == 1

    def test_nonexistent_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that non-existent paths are rejected."""
        monkeypatch.chdir(tmp_path)

        valid, problems = _validate_scan_paths(["nonexistent"])
        assert valid == []
        assert len(problems) == 1
        assert "does not exist" in problems[0]

    def test_mixed_valid_invalid_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that valid and invalid paths are handled correctly together."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        valid, problems = _validate_scan_paths(["src", "../etc", "nonexistent"])
        assert valid == ["src"]
        assert len(problems) == 2

    def test_symlink_escape_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that symlinks escaping the directory are handled."""
        monkeypatch.chdir(tmp_path)
        # Create a directory and try to resolve something that would escape
        # This tests the ValueError catch for relative_to failure
        valid, problems = _validate_scan_paths(["../"])
        assert valid == []
        assert len(problems) >= 1


# =============================================================================
# cmd_bandit Tests
# =============================================================================


class TestCmdBandit:
    """Tests for the cmd_bandit function."""

    def test_bandit_no_valid_paths(self, mock_args: argparse.Namespace):
        """Test bandit returns failure when no valid paths provided."""
        mock_args.paths = ["../escape"]
        mock_args.output = "bandit.json"
        mock_args.severity = "low"
        mock_args.confidence = "low"

        result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "No valid paths" in result.summary
        assert len(result.problems) > 0
        assert result.problems[0]["code"] == "CIHUB-BANDIT-PATH"

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_success_no_issues(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit returns success when no issues found."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text('{"results": []}', encoding="utf-8")

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = True
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = False

        result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "0 issues" in result.summary or "passed" in result.summary.lower()
        assert result.data["total"] == 0

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_high_severity_failure(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit fails when high severity issues found and threshold enabled."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text(
            '{"results": [{"issue_severity": "HIGH", "issue_confidence": "HIGH"}]}',
            encoding="utf-8",
        )

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = True
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = False

        with patch("cihub.commands.hub_ci.security.safe_run"):
            result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["high"] == 1

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_medium_severity_allowed(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit passes when medium severity issues found but threshold disabled."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text(
            '{"results": [{"issue_severity": "MEDIUM", "issue_confidence": "HIGH"}]}',
            encoding="utf-8",
        )

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = True
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = False

        result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["medium"] == 1

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_env_override_fail_medium(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit respects environment variable overrides."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CIHUB_BANDIT_FAIL_MEDIUM", "true")
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text(
            '{"results": [{"issue_severity": "MEDIUM", "issue_confidence": "HIGH"}]}',
            encoding="utf-8",
        )

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = True
        mock_args.fail_on_medium = False  # Will be overridden by env
        mock_args.fail_on_low = False

        with patch("cihub.commands.hub_ci.security.safe_run"):
            result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "MEDIUM" in result.summary

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_invalid_json_output(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit handles invalid JSON output gracefully."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text("not valid json", encoding="utf-8")

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = True
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = False

        result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["total"] == 0

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_counts_all_severities(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit correctly counts all severity levels."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text(
            json.dumps(
                {
                    "results": [
                        {"issue_severity": "HIGH"},
                        {"issue_severity": "HIGH"},
                        {"issue_severity": "MEDIUM"},
                        {"issue_severity": "LOW"},
                        {"issue_severity": "LOW"},
                        {"issue_severity": "LOW"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = False
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = False

        result = cmd_bandit(mock_args)

        assert result.data["high"] == 2
        assert result.data["medium"] == 1
        assert result.data["low"] == 3
        assert result.data["total"] == 6


# =============================================================================
# cmd_pip_audit Tests
# =============================================================================


class TestCmdPipAudit:
    """Tests for the cmd_pip_audit function."""

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_pip_audit_no_vulns(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pip-audit returns success when no vulnerabilities found."""
        output_file = tmp_path / "pip-audit.json"
        output_file.write_text("[]", encoding="utf-8")

        mock_args.requirements = ["requirements.txt"]
        mock_args.output = str(output_file)

        result = cmd_pip_audit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "No dependency vulnerabilities" in result.summary
        assert result.data["vulnerabilities"] == 0

    @patch("cihub.commands.hub_ci.security._run_command")
    @patch("cihub.commands.hub_ci.security.safe_run")
    def test_pip_audit_with_vulns(
        self, mock_safe_run: MagicMock, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test pip-audit returns failure when vulnerabilities found."""
        output_file = tmp_path / "pip-audit.json"
        # Proper pip-audit JSON format
        output_file.write_text(
            json.dumps(
                [
                    {"name": "package1", "vulns": [{"id": "CVE-1"}]},
                    {"name": "package2", "vulns": [{"id": "CVE-2"}, {"id": "CVE-3"}]},
                ]
            ),
            encoding="utf-8",
        )

        mock_safe_run.return_value = MagicMock(stdout="")
        mock_args.requirements = ["requirements.txt"]
        mock_args.output = str(output_file)

        result = cmd_pip_audit(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "3" in result.summary or "vulnerabilities" in result.summary.lower()
        assert result.data["vulnerabilities"] == 3

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_pip_audit_invalid_json(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pip-audit handles invalid JSON gracefully."""
        output_file = tmp_path / "pip-audit.json"
        output_file.write_text("not json", encoding="utf-8")

        mock_args.requirements = ["requirements.txt"]
        mock_args.output = str(output_file)

        result = cmd_pip_audit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["vulnerabilities"] == 0

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_pip_audit_missing_output_file(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pip-audit handles missing output file."""
        mock_args.requirements = ["requirements.txt"]
        mock_args.output = str(tmp_path / "nonexistent.json")

        result = cmd_pip_audit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["vulnerabilities"] == 0


# =============================================================================
# cmd_security_pip_audit Tests
# =============================================================================


class TestCmdSecurityPipAudit:
    """Tests for the cmd_security_pip_audit function."""

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_pip_audit_success(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security pip-audit returns success."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        report_path = tmp_path / "pip-audit.json"
        report_path.write_text("[]", encoding="utf-8")

        mock_args.path = str(tmp_path)
        mock_args.report = "pip-audit.json"
        mock_args.requirements = []

        result = cmd_security_pip_audit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["vulnerabilities"] == 0
        assert result.data["tool_status"] == "success"

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_pip_audit_with_requirements(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security pip-audit installs requirements before scanning."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
        report_path = tmp_path / "pip-audit.json"
        report_path.write_text("[]", encoding="utf-8")

        mock_args.path = str(tmp_path)
        mock_args.report = "pip-audit.json"
        mock_args.requirements = ["requirements.txt"]

        result = cmd_security_pip_audit(mock_args)

        # Should have called _run_command for pip install and pip-audit
        assert mock_run.call_count >= 1
        assert result.exit_code == EXIT_SUCCESS

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_pip_audit_tool_failed(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security pip-audit handles tool failure."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "tool error"
        mock_run.return_value = mock_proc

        mock_args.path = str(tmp_path)
        mock_args.report = "pip-audit.json"
        mock_args.requirements = []

        result = cmd_security_pip_audit(mock_args)

        assert result.exit_code == EXIT_SUCCESS  # Returns success with status
        assert result.data["tool_status"] == "failed"
        assert len(result.problems) > 0

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_pip_audit_invalid_json_with_failure(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security pip-audit handles invalid JSON when tool failed."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        report_path = tmp_path / "pip-audit.json"
        report_path.write_text("not json", encoding="utf-8")

        mock_args.path = str(tmp_path)
        mock_args.report = "pip-audit.json"
        mock_args.requirements = []

        result = cmd_security_pip_audit(mock_args)

        assert result.data["tool_status"] == "failed"


# =============================================================================
# cmd_security_bandit Tests
# =============================================================================


class TestCmdSecurityBandit:
    """Tests for the cmd_security_bandit function."""

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_bandit_success(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security bandit returns success with no high issues."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        report_path = tmp_path / "bandit.json"
        report_path.write_text('{"results": []}', encoding="utf-8")

        mock_args.path = str(tmp_path)
        mock_args.report = "bandit.json"

        result = cmd_security_bandit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["high"] == 0
        assert result.data["tool_status"] == "success"

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_bandit_with_high_issues(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security bandit counts high severity issues."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        report_path = tmp_path / "bandit.json"
        report_path.write_text(
            '{"results": [{"issue_severity": "HIGH"}, {"issue_severity": "HIGH"}]}',
            encoding="utf-8",
        )

        mock_args.path = str(tmp_path)
        mock_args.report = "bandit.json"

        result = cmd_security_bandit(mock_args)

        assert result.exit_code == EXIT_SUCCESS  # Returns success with count
        assert result.data["high"] == 2

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_bandit_tool_failed_no_report(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security bandit handles tool failure without report."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "bandit error"
        mock_run.return_value = mock_proc

        mock_args.path = str(tmp_path)
        mock_args.report = "bandit.json"

        result = cmd_security_bandit(mock_args)

        assert result.data["tool_status"] == "failed"
        assert len(result.problems) > 0


# =============================================================================
# cmd_security_ruff Tests
# =============================================================================


class TestCmdSecurityRuff:
    """Tests for the cmd_security_ruff function."""

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_ruff_success(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security ruff returns success with no issues."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "[]"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = str(tmp_path)
        mock_args.report = "ruff-security.json"

        result = cmd_security_ruff(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 0
        assert result.data["tool_status"] == "success"

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_ruff_with_issues(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security ruff counts issues correctly."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = '[{"code": "S101"}, {"code": "S102"}, {"code": "S103"}]'
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        mock_args.path = str(tmp_path)
        mock_args.report = "ruff-security.json"

        result = cmd_security_ruff(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["issues"] == 3

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_security_ruff_invalid_json(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test security ruff handles invalid JSON output."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "not json"
        mock_proc.stderr = "error"
        mock_run.return_value = mock_proc

        mock_args.path = str(tmp_path)
        mock_args.report = "ruff-security.json"

        result = cmd_security_ruff(mock_args)

        assert result.data["tool_status"] == "failed"
        assert result.data["issues"] == 0


# =============================================================================
# cmd_security_owasp Tests
# =============================================================================


class TestCmdSecurityOwasp:
    """Tests for the cmd_security_owasp function."""

    @patch("cihub.commands.hub_ci.security.ensure_executable")
    def test_security_owasp_skipped_no_mvnw(
        self, mock_ensure: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security OWASP is skipped when mvnw not found."""
        mock_ensure.return_value = False

        mock_args.path = str(tmp_path)

        result = cmd_security_owasp(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["tool_status"] == "skipped"

    @patch("cihub.commands.hub_ci.security._run_command")
    @patch("cihub.commands.hub_ci.security.ensure_executable")
    def test_security_owasp_success(
        self, mock_ensure: MagicMock, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security OWASP returns success when no critical/high issues."""
        mock_ensure.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        report_path = tmp_path / "target" / "dependency-check-report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text('{"dependencies": []}', encoding="utf-8")

        mock_args.path = str(tmp_path)

        result = cmd_security_owasp(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["critical"] == 0
        assert result.data["high"] == 0

    @patch("cihub.commands.hub_ci.security._run_command")
    @patch("cihub.commands.hub_ci.security.ensure_executable")
    def test_security_owasp_with_vulnerabilities(
        self, mock_ensure: MagicMock, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security OWASP counts vulnerabilities correctly."""
        mock_ensure.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        report_path = tmp_path / "target" / "dependency-check-report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text(
            json.dumps(
                {
                    "dependencies": [
                        {"vulnerabilities": [{"severity": "CRITICAL"}, {"severity": "HIGH"}]},
                        {"vulnerabilities": [{"severity": "HIGH"}]},
                    ]
                }
            ),
            encoding="utf-8",
        )

        mock_args.path = str(tmp_path)

        result = cmd_security_owasp(mock_args)

        assert result.data["critical"] == 1
        assert result.data["high"] == 2

    @patch("cihub.commands.hub_ci.security._run_command")
    @patch("cihub.commands.hub_ci.security.ensure_executable")
    def test_security_owasp_tool_failed_no_report(
        self, mock_ensure: MagicMock, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security OWASP handles tool failure without report."""
        mock_ensure.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        mock_args.path = str(tmp_path)

        result = cmd_security_owasp(mock_args)

        assert result.data["tool_status"] == "failed"
        assert len(result.problems) > 0

    @patch("cihub.commands.hub_ci.security._run_command")
    @patch("cihub.commands.hub_ci.security.ensure_executable")
    def test_security_owasp_invalid_json(
        self, mock_ensure: MagicMock, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test security OWASP handles invalid JSON report."""
        mock_ensure.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        report_path = tmp_path / "target" / "dependency-check-report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text("not json", encoding="utf-8")

        mock_args.path = str(tmp_path)

        result = cmd_security_owasp(mock_args)

        assert result.data["tool_status"] == "failed"


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


class TestSecurityEdgeCases:
    """Edge case tests for security commands."""

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_empty_results_list(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit handles empty results list."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        # Use empty list (valid JSON structure)
        output_file.write_text('{"results": []}', encoding="utf-8")

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = True
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = False

        result = cmd_bandit(mock_args)

        # Should handle gracefully without crash
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["total"] == 0

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_pip_audit_empty_vulns(self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pip-audit handles packages with no vulns."""
        output_file = tmp_path / "pip-audit.json"
        output_file.write_text(
            '[{"name": "package1", "vulns": []}, {"name": "package2", "vulns": []}]',
            encoding="utf-8",
        )

        mock_args.requirements = ["requirements.txt"]
        mock_args.output = str(output_file)

        result = cmd_pip_audit(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["vulnerabilities"] == 0

    def test_validate_paths_empty_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test _validate_scan_paths handles empty path list."""
        monkeypatch.chdir(tmp_path)

        valid, problems = _validate_scan_paths([])
        assert valid == []
        assert problems == []

    @patch("cihub.commands.hub_ci.security._run_command")
    def test_bandit_fail_on_low(
        self, mock_run: MagicMock, tmp_path: Path, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch
    ):
        """Test bandit can fail on low severity issues."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        output_file = tmp_path / "bandit.json"
        output_file.write_text(
            '{"results": [{"issue_severity": "LOW"}]}',
            encoding="utf-8",
        )

        mock_args.paths = ["src"]
        mock_args.output = str(output_file)
        mock_args.severity = "low"
        mock_args.confidence = "low"
        mock_args.fail_on_high = False
        mock_args.fail_on_medium = False
        mock_args.fail_on_low = True

        with patch("cihub.commands.hub_ci.security.safe_run"):
            result = cmd_bandit(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "LOW" in result.summary
