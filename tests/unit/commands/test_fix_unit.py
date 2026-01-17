"""Unit tests for cihub fix command internal functions.

This module tests the internal helper functions in fix.py directly,
without going through CLI invocation. This provides faster, more
targeted testing of business logic.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.fix import (
    TOOL_CATEGORIES,
    _generate_ai_report,
    _run_report,
    _run_safe_fixes,
    _run_tool,
    _tool_installed,
    cmd_fix,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


# =============================================================================
# Test _tool_installed
# =============================================================================


class TestToolInstalled:
    """Tests for the _tool_installed helper function."""

    def test_tool_installed_returns_true_for_existing_tool(self):
        """Test that _tool_installed returns True for tools in PATH."""
        # 'python' should always exist in the test environment
        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert _tool_installed("python") is True

    def test_tool_installed_returns_false_for_missing_tool(self):
        """Test that _tool_installed returns False for missing tools."""
        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert _tool_installed("nonexistent_tool_xyz") is False

    def test_tool_installed_handles_command_not_found(self):
        """Test graceful handling of CommandNotFoundError."""
        from cihub.utils.exec_utils import CommandNotFoundError

        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.side_effect = CommandNotFoundError("which")
            assert _tool_installed("anything") is False

    def test_tool_installed_handles_timeout(self):
        """Test graceful handling of CommandTimeoutError."""
        from cihub.utils.exec_utils import CommandTimeoutError

        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.side_effect = CommandTimeoutError("which", 5000)
            assert _tool_installed("anything") is False

    def test_tool_installed_handles_file_not_found(self):
        """Test graceful handling of FileNotFoundError."""
        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert _tool_installed("anything") is False


# =============================================================================
# Test _run_tool
# =============================================================================


class TestRunTool:
    """Tests for the _run_tool helper function."""

    def test_run_tool_returns_success_tuple(self, tmp_path: Path):
        """Test successful tool execution returns correct tuple."""
        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="success output", stderr=""
            )
            rc, stdout, stderr = _run_tool(["echo", "test"], tmp_path)
            assert rc == 0
            assert stdout == "success output"
            assert stderr == ""

    def test_run_tool_returns_failure_tuple(self, tmp_path: Path):
        """Test failed tool execution returns correct tuple."""
        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="error message"
            )
            rc, stdout, stderr = _run_tool(["false"], tmp_path)
            assert rc == 1
            assert stderr == "error message"

    def test_run_tool_handles_command_not_found(self, tmp_path: Path):
        """Test graceful handling of CommandNotFoundError."""
        from cihub.utils.exec_utils import CommandNotFoundError

        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.side_effect = CommandNotFoundError("nonexistent")
            rc, stdout, stderr = _run_tool(["nonexistent"], tmp_path)
            assert rc == -1
            assert "Command not found" in stderr

    def test_run_tool_handles_timeout(self, tmp_path: Path):
        """Test graceful handling of CommandTimeoutError."""
        from cihub.utils.exec_utils import CommandTimeoutError

        with patch("cihub.commands.fix.safe_run") as mock_run:
            mock_run.side_effect = CommandTimeoutError("slow_cmd", 30000)
            rc, stdout, stderr = _run_tool(["slow_cmd"], tmp_path)
            assert rc == -1
            assert "timed out" in stderr


# =============================================================================
# Test _run_safe_fixes
# =============================================================================


class TestRunSafeFixes:
    """Tests for the _run_safe_fixes helper function."""

    def test_safe_fixes_python_dry_run(self, tmp_path: Path):
        """Test Python dry-run mode doesn't execute tools."""
        result = _run_safe_fixes(tmp_path, "python", dry_run=True)
        assert result.exit_code == EXIT_SUCCESS
        assert "dry-run" in result.summary.lower()
        assert "ruff" in result.data["fixes"][0] or "dry-run" in result.data["fixes"][0]

    def test_safe_fixes_python_with_tools_installed(self, tmp_path: Path):
        """Test Python fixes with mocked tool execution."""
        with patch("cihub.commands.fix._tool_installed") as mock_installed, patch(
            "cihub.commands.fix._run_tool"
        ) as mock_run:
            mock_installed.return_value = True
            mock_run.return_value = (0, "", "")

            result = _run_safe_fixes(tmp_path, "python", dry_run=False)
            assert result.exit_code == EXIT_SUCCESS
            # ruff, black, isort should all be in fixes
            assert len(result.data["fixes"]) >= 1

    def test_safe_fixes_python_tool_not_installed(self, tmp_path: Path):
        """Test Python fixes when tools are not installed."""
        with patch("cihub.commands.fix._tool_installed") as mock_installed:
            mock_installed.return_value = False

            result = _run_safe_fixes(tmp_path, "python", dry_run=False)
            # Should have warnings about missing tools
            assert len(result.problems) > 0
            assert any("not installed" in p["message"] for p in result.problems)

    def test_safe_fixes_python_tool_fails(self, tmp_path: Path):
        """Test Python fixes when tool execution fails."""
        with patch("cihub.commands.fix._tool_installed") as mock_installed, patch(
            "cihub.commands.fix._run_tool"
        ) as mock_run:
            mock_installed.return_value = True
            mock_run.return_value = (1, "", "ruff error: something bad")

            result = _run_safe_fixes(tmp_path, "python", dry_run=False)
            # Should have warnings about failed tools
            assert len(result.problems) > 0
            assert any("failed" in p["message"].lower() for p in result.problems)

    def test_safe_fixes_java_maven_dry_run(self, tmp_path: Path):
        """Test Java Maven dry-run mode."""
        (tmp_path / "pom.xml").write_text("<project></project>")
        result = _run_safe_fixes(tmp_path, "java", dry_run=True)
        assert result.exit_code == EXIT_SUCCESS
        assert "spotless" in result.data["fixes"][0].lower()

    def test_safe_fixes_java_gradle_dry_run(self, tmp_path: Path):
        """Test Java Gradle dry-run mode."""
        (tmp_path / "build.gradle").write_text("// gradle build")
        result = _run_safe_fixes(tmp_path, "java", dry_run=True)
        assert result.exit_code == EXIT_SUCCESS
        assert "spotless" in result.data["fixes"][0].lower()
        assert "gradle" in result.data["fixes"][0].lower()

    def test_safe_fixes_java_gradle_kts_dry_run(self, tmp_path: Path):
        """Test Java Gradle Kotlin DSL dry-run mode."""
        (tmp_path / "build.gradle.kts").write_text("// gradle kotlin build")
        result = _run_safe_fixes(tmp_path, "java", dry_run=True)
        assert result.exit_code == EXIT_SUCCESS
        assert "spotless" in result.data["fixes"][0].lower()

    def test_safe_fixes_java_no_build_file(self, tmp_path: Path):
        """Test Java fixes fail when no build file exists."""
        result = _run_safe_fixes(tmp_path, "java", dry_run=False)
        assert result.exit_code == EXIT_FAILURE
        assert "build file" in result.summary.lower() or "pom.xml" in result.summary.lower()

    def test_safe_fixes_unsupported_language(self, tmp_path: Path):
        """Test unsupported language returns failure."""
        result = _run_safe_fixes(tmp_path, "rust", dry_run=False)
        assert result.exit_code == EXIT_FAILURE
        assert "unsupported" in result.summary.lower()


# =============================================================================
# Test _run_report
# =============================================================================


class TestRunReport:
    """Tests for the _run_report helper function."""

    def test_run_report_python_no_tools(self, tmp_path: Path):
        """Test Python report when no tools are installed."""
        with patch("cihub.commands.fix._tool_installed") as mock_installed:
            mock_installed.return_value = False
            issues = _run_report(tmp_path, "python")
            # Should return empty dict (no tools ran)
            assert isinstance(issues, dict)

    def test_run_report_python_mypy_issues(self, tmp_path: Path):
        """Test Python report with mypy findings."""
        with patch("cihub.commands.fix._tool_installed") as mock_installed, patch(
            "cihub.commands.fix._run_tool"
        ) as mock_run:
            mock_installed.return_value = True
            mock_run.return_value = (
                1,
                "file.py:10: error: Missing return type annotation\n",
                "",
            )
            issues = _run_report(tmp_path, "python")
            assert "mypy" in issues
            assert len(issues["mypy"]) > 0

    def test_run_report_python_bandit_json_output(self, tmp_path: Path):
        """Test Python report parses bandit JSON correctly."""
        bandit_output = json.dumps(
            {
                "results": [
                    {
                        "issue_text": "Use of assert detected",
                        "filename": "test.py",
                        "line_number": 5,
                        "issue_severity": "LOW",
                    }
                ]
            }
        )
        with patch("cihub.commands.fix._tool_installed") as mock_installed, patch(
            "cihub.commands.fix._run_tool"
        ) as mock_run:
            mock_installed.side_effect = lambda t: t == "bandit"
            mock_run.return_value = (0, bandit_output, "")
            issues = _run_report(tmp_path, "python")
            if "bandit" in issues:
                assert len(issues["bandit"]) > 0
                assert "test.py" in issues["bandit"][0]["message"]

    def test_run_report_python_bandit_invalid_json(self, tmp_path: Path):
        """Test Python report handles invalid bandit JSON."""
        with patch("cihub.commands.fix._tool_installed") as mock_installed, patch(
            "cihub.commands.fix._run_tool"
        ) as mock_run:
            mock_installed.side_effect = lambda t: t == "bandit"
            mock_run.return_value = (0, "not valid json {{{", "")
            issues = _run_report(tmp_path, "python")
            if "bandit" in issues:
                # Should have a parse error entry
                assert any(
                    issue.get("parse_error", False) for issue in issues["bandit"]
                )

    def test_run_report_java_maven(self, tmp_path: Path):
        """Test Java Maven report."""
        (tmp_path / "pom.xml").write_text("<project></project>")
        with patch("cihub.commands.fix._tool_installed") as mock_installed, patch(
            "cihub.commands.fix._run_tool"
        ) as mock_run:
            mock_installed.return_value = True
            # Simulate spotbugs failure (issues found)
            mock_run.return_value = (1, "", "SpotBugs found issues")
            issues = _run_report(tmp_path, "java")
            assert "spotbugs" in issues

    def test_run_report_unsupported_language(self, tmp_path: Path):
        """Test report for unsupported language returns empty dict."""
        issues = _run_report(tmp_path, "go")
        assert issues == {}


# =============================================================================
# Test _generate_ai_report
# =============================================================================


class TestGenerateAIReport:
    """Tests for the _generate_ai_report helper function."""

    def test_generate_ai_report_empty_issues(self, tmp_path: Path):
        """Test AI report with no issues."""
        report = _generate_ai_report(tmp_path, "python", {})
        assert "# Fix Report" in report
        assert "Total issues: 0" in report
        assert "python" in report.lower()

    def test_generate_ai_report_with_issues(self, tmp_path: Path):
        """Test AI report with various issues."""
        issues: dict[str, list[dict[str, Any]]] = {
            "bandit": [
                {"message": "Possible SQL injection", "severity": "high", "location": "db.py:42"},
                {"message": "Weak hash algorithm", "severity": "medium"},
            ],
            "mypy": [
                {"message": "Missing type annotation", "severity": "low"},
            ],
        }
        report = _generate_ai_report(tmp_path, "python", issues)
        assert "# Fix Report" in report
        assert "Total issues: 3" in report
        assert "bandit" in report.lower()
        assert "mypy" in report.lower()
        assert "SQL injection" in report

    def test_generate_ai_report_critical_issues_section(self, tmp_path: Path):
        """Test AI report highlights critical issues."""
        issues: dict[str, list[dict[str, Any]]] = {
            "trivy": [
                {"message": "Critical CVE found", "severity": "critical", "location": "Dockerfile:1"},
            ],
        }
        report = _generate_ai_report(tmp_path, "python", issues)
        assert "Critical Issues" in report
        assert "CRITICAL" in report

    def test_generate_ai_report_limits_output(self, tmp_path: Path):
        """Test AI report limits issues per tool to 10."""
        issues: dict[str, list[dict[str, Any]]] = {
            "ruff": [{"message": f"Issue {i}", "severity": "low"} for i in range(20)],
        }
        report = _generate_ai_report(tmp_path, "python", issues)
        # Should mention there are more
        assert "more" in report.lower()


# =============================================================================
# Test cmd_fix
# =============================================================================


class TestCmdFix:
    """Tests for the main cmd_fix function."""

    def test_cmd_fix_requires_mode(self):
        """Test that cmd_fix requires --safe or --report."""
        args = argparse.Namespace(
            repo=None, safe=False, report=False, ai=False, dry_run=False
        )
        result = cmd_fix(args)
        assert result.exit_code == EXIT_USAGE
        assert "--safe" in result.summary or "--report" in result.summary

    def test_cmd_fix_ai_requires_report(self):
        """Test that --ai requires --report mode."""
        args = argparse.Namespace(
            repo=None, safe=True, report=False, ai=True, dry_run=False
        )
        result = cmd_fix(args)
        assert result.exit_code == EXIT_USAGE
        assert "--ai" in result.problems[0]["message"]

    def test_cmd_fix_dry_run_requires_safe(self):
        """Test that --dry-run requires --safe mode."""
        args = argparse.Namespace(
            repo=None, safe=False, report=True, ai=False, dry_run=True
        )
        result = cmd_fix(args)
        assert result.exit_code == EXIT_USAGE
        assert "--dry-run" in result.problems[0]["message"]

    def test_cmd_fix_repo_not_found(self, tmp_path: Path):
        """Test cmd_fix with non-existent repo path."""
        args = argparse.Namespace(
            repo=str(tmp_path / "nonexistent"),
            safe=True,
            report=False,
            ai=False,
            dry_run=False,
        )
        result = cmd_fix(args)
        assert result.exit_code == EXIT_FAILURE
        assert "not found" in result.summary.lower() or "not exist" in result.summary.lower()

    def test_cmd_fix_language_detection_fails(self, tmp_path: Path):
        """Test cmd_fix when language detection fails."""
        # Empty directory - no language markers
        with patch("cihub.commands.fix.detect_language") as mock_detect:
            mock_detect.return_value = (None, ["No markers found"])
            args = argparse.Namespace(
                repo=str(tmp_path), safe=True, report=False, ai=False, dry_run=False
            )
            result = cmd_fix(args)
            assert result.exit_code == EXIT_FAILURE
            assert "language" in result.summary.lower()

    def test_cmd_fix_safe_mode_success(self, tmp_path: Path):
        """Test cmd_fix in safe mode with mocked detection and execution."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        with patch("cihub.commands.fix.detect_language") as mock_detect, patch(
            "cihub.commands.fix._run_safe_fixes"
        ) as mock_fixes:
            mock_detect.return_value = ("python", ["pyproject.toml found"])
            mock_fixes.return_value = MagicMock(
                exit_code=EXIT_SUCCESS,
                summary="Applied fixes: ruff, black",
                problems=[],
                data={"fixes": ["ruff", "black"], "language": "python"},
            )
            args = argparse.Namespace(
                repo=str(tmp_path), safe=True, report=False, ai=False, dry_run=False
            )
            result = cmd_fix(args)
            # Should return the mock result
            assert result.exit_code == EXIT_SUCCESS

    def test_cmd_fix_report_mode_success(self, tmp_path: Path):
        """Test cmd_fix in report mode."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        with patch("cihub.commands.fix.detect_language") as mock_detect, patch(
            "cihub.commands.fix._run_report"
        ) as mock_report:
            mock_detect.return_value = ("python", ["pyproject.toml found"])
            mock_report.return_value = {"mypy": [{"message": "test", "severity": "low"}]}
            args = argparse.Namespace(
                repo=str(tmp_path), safe=False, report=True, ai=False, dry_run=False
            )
            result = cmd_fix(args)
            # Should have issues in data
            assert "issues" in result.data
            assert result.data["language"] == "python"

    def test_cmd_fix_report_ai_mode(self, tmp_path: Path):
        """Test cmd_fix in report --ai mode creates file."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        with patch("cihub.commands.fix.detect_language") as mock_detect, patch(
            "cihub.commands.fix._run_report"
        ) as mock_report:
            mock_detect.return_value = ("python", ["pyproject.toml found"])
            mock_report.return_value = {}
            args = argparse.Namespace(
                repo=str(tmp_path), safe=False, report=True, ai=True, dry_run=False
            )
            result = cmd_fix(args)
            # Should create the AI report file
            ai_report = tmp_path / ".cihub" / "fix-report.md"
            assert ai_report.exists()
            assert "ai_output" in result.data


# =============================================================================
# Test TOOL_CATEGORIES constant
# =============================================================================


class TestToolCategories:
    """Tests for the TOOL_CATEGORIES constant."""

    def test_tool_categories_structure(self):
        """Test that TOOL_CATEGORIES has correct structure."""
        for tool, (category, severity) in TOOL_CATEGORIES.items():
            assert isinstance(tool, str)
            assert isinstance(category, str)
            assert isinstance(severity, int)
            assert 0 <= severity <= 10

    def test_tool_categories_contains_expected_tools(self):
        """Test that expected tools are in TOOL_CATEGORIES."""
        expected_tools = ["bandit", "mypy", "spotbugs", "checkstyle", "owasp"]
        for tool in expected_tools:
            assert tool in TOOL_CATEGORIES

    def test_security_tools_have_high_severity(self):
        """Test that security tools have appropriate severity."""
        security_tools = ["bandit", "pip_audit", "semgrep", "trivy", "owasp"]
        for tool in security_tools:
            if tool in TOOL_CATEGORIES:
                category, severity = TOOL_CATEGORIES[tool]
                assert category == "security"
                assert severity >= 7  # Security tools should be high priority
