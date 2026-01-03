"""Metric extraction helpers for aggregation."""

from __future__ import annotations

from typing import Any


def extract_metrics_from_report(report_data: dict[str, Any], run_status: dict[str, Any]) -> None:
    results_data = report_data.get("results", {}) or {}
    tool_metrics = report_data.get("tool_metrics", {}) or {}

    run_status["coverage"] = results_data.get("coverage")
    run_status["mutation_score"] = results_data.get("mutation_score")

    run_status["checkstyle_issues"] = tool_metrics.get("checkstyle_issues")
    run_status["spotbugs_issues"] = tool_metrics.get("spotbugs_issues")
    run_status["pmd_violations"] = tool_metrics.get("pmd_violations")
    run_status["owasp_critical"] = tool_metrics.get("owasp_critical")
    run_status["owasp_high"] = tool_metrics.get("owasp_high")
    run_status["owasp_medium"] = tool_metrics.get("owasp_medium")

    run_status["tests_passed"] = results_data.get("tests_passed")
    run_status["tests_failed"] = results_data.get("tests_failed")
    run_status["ruff_errors"] = tool_metrics.get("ruff_errors")
    run_status["black_issues"] = tool_metrics.get("black_issues")
    run_status["isort_issues"] = tool_metrics.get("isort_issues")
    run_status["mypy_errors"] = tool_metrics.get("mypy_errors")
    run_status["bandit_high"] = tool_metrics.get("bandit_high")
    run_status["bandit_medium"] = tool_metrics.get("bandit_medium")
    run_status["pip_audit_vulns"] = tool_metrics.get("pip_audit_vulns")

    run_status["semgrep_findings"] = tool_metrics.get("semgrep_findings")
    run_status["trivy_critical"] = tool_metrics.get("trivy_critical")
    run_status["trivy_high"] = tool_metrics.get("trivy_high")

    run_status["tools_ran"] = report_data.get("tools_ran", {})
    run_status["tools_configured"] = report_data.get("tools_configured", {})
    run_status["tools_success"] = report_data.get("tools_success", {})
