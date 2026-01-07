"""Contract tests for gate evaluation consistency.

Issue 13/19: Verify that gates.py decisions match reporting.py rendering.

These tests ensure that when gates.py says a gate passes/fails, the summary
rendering in reporting.py shows the corresponding status.
"""

from __future__ import annotations

from cihub.core.reporting import build_quality_gates
from cihub.services.ci_engine.gates import (
    _evaluate_java_gates,
    _evaluate_python_gates,
)


class TestGateReportingContractPython:
    """Contract tests ensuring gates.py and reporting.py agree for Python."""

    def test_no_tests_ran_both_fail(self) -> None:
        """Issue 12: When tests_total == 0, both should indicate failure."""
        report = {
            "results": {"tests_passed": 0, "tests_failed": 0, "tests_skipped": 0},
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
            "tool_metrics": {},
            "thresholds": {},
        }
        thresholds: dict = {}
        tools_configured = {"pytest": True}
        config: dict = {}

        # gates.py should fail
        gate_failures = _evaluate_python_gates(report, thresholds, tools_configured, config)
        assert "no tests ran - cannot verify quality" in gate_failures

        # reporting.py should show NOT RUN or failure
        summary_lines = list(build_quality_gates(report, "python"))
        summary_text = "\n".join(summary_lines)
        assert "NOT RUN" in summary_text or "0 passed" in summary_text

    def test_tests_passed_both_pass(self) -> None:
        """When tests pass, both gates.py and reporting.py should pass."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0, "tests_skipped": 0, "coverage": 80},
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
            "tool_metrics": {},
            "thresholds": {"coverage_min": 70},
        }
        thresholds = {"coverage_min": 70}
        tools_configured = {"pytest": True}
        config: dict = {}

        # gates.py should pass
        gate_failures = _evaluate_python_gates(report, thresholds, tools_configured, config)
        assert len(gate_failures) == 0

        # reporting.py should show PASSED status
        summary_lines = list(build_quality_gates(report, "python"))
        summary_text = "\n".join(summary_lines)
        assert "PASSED" in summary_text

    def test_test_failures_both_fail(self) -> None:
        """When tests fail, both gates.py and reporting.py should fail."""
        report = {
            "results": {"tests_passed": 5, "tests_failed": 3, "tests_skipped": 0},
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": False},
            "tool_metrics": {},
            "thresholds": {},
        }
        thresholds: dict = {}
        tools_configured = {"pytest": True}
        config: dict = {}

        # gates.py should fail
        gate_failures = _evaluate_python_gates(report, thresholds, tools_configured, config)
        assert "pytest failures detected" in gate_failures

        # reporting.py should show FAILED status
        summary_lines = list(build_quality_gates(report, "python"))
        summary_text = "\n".join(summary_lines)
        # Should show FAILED status (uppercase)
        assert "FAILED" in summary_text

    def test_tool_not_run_shows_not_run(self) -> None:
        """When tool configured but not run, reporting.py shows NOT RUN."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0},
            "tools_configured": {"pytest": True, "ruff": True},
            "tools_ran": {"pytest": True, "ruff": False},
            "tools_success": {"pytest": True},
            "tool_metrics": {},
            "thresholds": {},
        }

        summary_lines = list(build_quality_gates(report, "python"))
        summary_text = "\n".join(summary_lines)
        # Ruff should show NOT RUN since it was configured but didn't run
        assert "NOT RUN" in summary_text


class TestGateReportingContractJava:
    """Contract tests ensuring gates.py and reporting.py agree for Java."""

    def test_no_tests_ran_both_fail(self) -> None:
        """Issue 12: When tests_total == 0, both should indicate failure."""
        report = {
            "results": {"tests_passed": 0, "tests_failed": 0, "tests_skipped": 0},
            "tools_configured": {"jacoco": True},
            "tools_ran": {"jacoco": True},
            "tools_success": {"jacoco": True},
            "tool_metrics": {},
            "thresholds": {},
        }
        thresholds: dict = {}
        tools_configured: dict = {}
        config: dict = {}

        # gates.py should fail
        gate_failures = _evaluate_java_gates(report, thresholds, tools_configured, config)
        assert "no tests ran - cannot verify quality" in gate_failures

        # reporting.py should show NOT RUN or failure
        summary_lines = list(build_quality_gates(report, "java"))
        summary_text = "\n".join(summary_lines)
        assert "NOT RUN" in summary_text or "0 passed" in summary_text

    def test_tests_passed_both_pass(self) -> None:
        """When tests pass, both gates.py and reporting.py should pass."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0, "tests_skipped": 0, "coverage": 80},
            "tools_configured": {"jacoco": True},
            "tools_ran": {"jacoco": True},
            "tools_success": {"jacoco": True},
            "tool_metrics": {},
            "thresholds": {"coverage_min": 70},
        }
        thresholds = {"coverage_min": 70}
        tools_configured = {"jacoco": True}
        config: dict = {}

        # gates.py should pass
        gate_failures = _evaluate_java_gates(report, thresholds, tools_configured, config)
        assert len(gate_failures) == 0

        # reporting.py should show PASSED status
        summary_lines = list(build_quality_gates(report, "java"))
        summary_text = "\n".join(summary_lines)
        assert "PASSED" in summary_text

    def test_owasp_vulns_both_fail(self) -> None:
        """When OWASP finds vulns above threshold, both should fail."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0},
            "tools_configured": {"owasp": True},
            "tools_ran": {"owasp": True},
            "tools_success": {"owasp": True},
            "tool_metrics": {"owasp_critical": 3, "owasp_high": 5},
            "thresholds": {"max_critical_vulns": 0, "max_high_vulns": 0},
        }
        thresholds = {"max_critical_vulns": 0, "max_high_vulns": 0}
        tools_configured = {"owasp": True}
        config: dict = {}

        # gates.py should fail
        gate_failures = _evaluate_java_gates(report, thresholds, tools_configured, config)
        assert any("owasp" in f for f in gate_failures)

        # reporting.py should show VULNERABILITIES status (uppercase)
        summary_lines = list(build_quality_gates(report, "java"))
        summary_text = "\n".join(summary_lines)
        # Should show "VULNERABILITIES" label (not "PASSED")
        assert "VULNERABILITIES" in summary_text
        assert "PASSED" not in summary_text.split("OWASP")[1].split("|")[0] if "OWASP" in summary_text else True

    def test_tool_not_run_shows_not_run(self) -> None:
        """When tool configured but not run, reporting.py shows NOT RUN."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0},
            "tools_configured": {"jacoco": True, "pitest": True},
            "tools_ran": {"jacoco": True, "pitest": False},
            "tools_success": {"jacoco": True},
            "tool_metrics": {},
            "thresholds": {},
        }

        summary_lines = list(build_quality_gates(report, "java"))
        summary_text = "\n".join(summary_lines)
        # PITest should show NOT RUN since it was configured but didn't run
        assert "NOT RUN" in summary_text
