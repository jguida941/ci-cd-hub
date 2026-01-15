"""Report building helpers for cihub ci."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cihub import __version__


@dataclass(frozen=True, slots=True, kw_only=True)
class RunContext:
    repository: str | None
    branch: str | None
    run_id: str | None
    run_number: str | None
    commit: str | None
    correlation_id: str | None
    workflow_ref: str | None
    workdir: str | None
    build_tool: str | None
    retention_days: int | None
    project_type: str | None
    docker_compose_file: str | None
    docker_health_endpoint: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportMetrics:
    """Extracted metrics for report building.

    This dataclass captures the language-agnostic shape of metrics
    that both Python and Java reports share, allowing the report
    builder to be unified.
    """

    # Test results
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    tests_runtime: float
    test_status: str  # "success", "failure", or "skipped"
    status_field_name: str  # "test" for Python, "build" for Java

    # Coverage
    coverage: int
    coverage_lines_covered: int
    coverage_lines_total: int

    # Mutation testing
    mutation_score: int
    mutation_killed: int
    mutation_survived: int

    # Security vulns (aggregated from ALL security tools including static analysis)
    critical_vulns: int
    high_vulns: int
    medium_vulns: int
    low_vulns: int

    # Dependency scanner vulns only (trivy only for Python, owasp/trivy for Java)
    # Used for dependency_severity which should NOT include static analysis (bandit)
    dep_critical: int
    dep_high: int
    dep_medium: int
    dep_low: int

    # Language-specific tool metrics dict
    tool_metrics: dict[str, Any]

    # Language version (e.g., "3.12" or "17")
    language_version: str
    language_version_field: str  # "python_version" or "java_version"

    # Environment extras (Java has more fields)
    environment_extras: dict[str, Any]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _set_threshold(thresholds: dict[str, Any], key: str, value: Any) -> None:
    """Set a threshold if value is not None and key not already set."""
    if value is None:
        return
    thresholds.setdefault(key, value)


def _derive_trivy_fallbacks(thresholds: dict[str, Any]) -> None:
    """Derive trivy thresholds from general vuln limits (shared by Python/Java).

    Internal thresholds - NOT user-configurable via .ci-hub.yml.
    Trivy critical/high mirror the general max_critical_vulns/max_high_vulns.
    """
    if "max_trivy_critical" not in thresholds:
        max_crit = thresholds.get("max_critical_vulns")
        if max_crit is not None:
            thresholds["max_trivy_critical"] = max_crit
    if "max_trivy_high" not in thresholds:
        max_high = thresholds.get("max_high_vulns")
        if max_high is not None:
            thresholds["max_trivy_high"] = max_high


def _resolve_python_thresholds(config: dict[str, Any], thresholds: dict[str, Any]) -> None:
    """Extract Python tool thresholds from config."""
    tools = config.get("python", {}).get("tools", {}) or {}

    # Direct tool config mappings
    _set_threshold(thresholds, "coverage_min", tools.get("pytest", {}).get("min_coverage"))
    _set_threshold(thresholds, "mutation_score_min", tools.get("mutmut", {}).get("min_mutation_score"))
    _set_threshold(thresholds, "max_ruff_errors", tools.get("ruff", {}).get("max_errors"))
    _set_threshold(thresholds, "max_black_issues", tools.get("black", {}).get("max_issues"))
    _set_threshold(thresholds, "max_isort_issues", tools.get("isort", {}).get("max_issues"))
    _set_threshold(thresholds, "max_semgrep_findings", tools.get("semgrep", {}).get("max_findings"))
    _set_threshold(thresholds, "trivy_cvss_fail", tools.get("trivy", {}).get("fail_on_cvss"))

    # Fallback: trivy_cvss_fail from owasp_cvss_fail (legacy compatibility)
    if "trivy_cvss_fail" not in thresholds and "owasp_cvss_fail" in thresholds:
        thresholds["trivy_cvss_fail"] = thresholds["owasp_cvss_fail"]

    # Fallback: pip_audit from max_high_vulns
    if "max_pip_audit_vulns" not in thresholds:
        max_high = thresholds.get("max_high_vulns")
        if max_high is not None:
            thresholds["max_pip_audit_vulns"] = max_high

    # Internal/derived thresholds - NOT user-configurable via .ci-hub.yml
    # mypy always fails on any error (no config to allow N errors)
    thresholds.setdefault("max_mypy_errors", 0)

    # Bandit severity thresholds - 0 when toggle enabled
    bandit_cfg = tools.get("bandit", {}) or {}
    if bandit_cfg.get("fail_on_medium", False):
        thresholds.setdefault("max_bandit_medium", 0)
    if bandit_cfg.get("fail_on_low", False):
        thresholds.setdefault("max_bandit_low", 0)

    # Trivy fallbacks from general vuln limits
    _derive_trivy_fallbacks(thresholds)


def _resolve_java_thresholds(config: dict[str, Any], thresholds: dict[str, Any]) -> None:
    """Extract Java tool thresholds from config."""
    tools = config.get("java", {}).get("tools", {}) or {}

    # Direct tool config mappings
    _set_threshold(thresholds, "coverage_min", tools.get("jacoco", {}).get("min_coverage"))
    _set_threshold(thresholds, "mutation_score_min", tools.get("pitest", {}).get("min_mutation_score"))
    _set_threshold(thresholds, "max_checkstyle_errors", tools.get("checkstyle", {}).get("max_errors"))
    _set_threshold(thresholds, "max_spotbugs_bugs", tools.get("spotbugs", {}).get("max_bugs"))
    _set_threshold(thresholds, "max_pmd_violations", tools.get("pmd", {}).get("max_violations"))
    _set_threshold(thresholds, "owasp_cvss_fail", tools.get("owasp", {}).get("fail_on_cvss"))
    _set_threshold(thresholds, "trivy_cvss_fail", tools.get("trivy", {}).get("fail_on_cvss"))
    _set_threshold(thresholds, "max_semgrep_findings", tools.get("semgrep", {}).get("max_findings"))

    # Trivy fallbacks from general vuln limits
    _derive_trivy_fallbacks(thresholds)


def resolve_thresholds(config: dict[str, Any], language: str) -> dict[str, Any]:
    """Resolve thresholds from config for the given language.

    Combines base thresholds from config with language-specific tool thresholds.
    Also derives internal/fallback thresholds that aren't directly user-configurable.
    """
    thresholds = dict(config.get("thresholds", {}) or {})

    if language == "python":
        _resolve_python_thresholds(config, thresholds)
    else:
        _resolve_java_thresholds(config, thresholds)

    return thresholds


def _get_metric(
    tool_results: dict[str, dict[str, Any]],
    tool: str,
    key: str,
    default: int | float = 0,
) -> int | float:
    metrics = tool_results.get(tool, {}).get("metrics", {})
    value = metrics.get(key, default)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return default
    return default


def _get_docker_metrics(tool_results: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """Extract docker metrics shared by both languages."""
    docker_data = tool_results.get("docker", {}).get("metrics", {})
    return {
        "docker_missing_compose": bool(docker_data.get("docker_missing_compose", False)),
        "docker_health_ok": bool(docker_data.get("docker_health_ok", False)),
    }


def _extract_python_metrics(
    config: dict[str, Any],
    tool_results: dict[str, dict[str, Any]],
    tools_configured: dict[str, bool],
) -> ReportMetrics:
    """Extract metrics from Python tool results."""
    # Test metrics from pytest
    pytest_enabled = tools_configured.get("pytest", False)
    tests_failed = int(_get_metric(tool_results, "pytest", "tests_failed", 0))
    tests_passed = int(_get_metric(tool_results, "pytest", "tests_passed", 0))
    tests_skipped = int(_get_metric(tool_results, "pytest", "tests_skipped", 0))
    tests_runtime = float(_get_metric(tool_results, "pytest", "tests_runtime_seconds", 0.0))

    test_status = "skipped"
    if pytest_enabled:
        test_status = "success" if tests_failed == 0 else "failure"

    # Coverage from pytest
    coverage = int(_get_metric(tool_results, "pytest", "coverage", 0))
    coverage_lines_covered = int(_get_metric(tool_results, "pytest", "coverage_lines_covered", 0))
    coverage_lines_total = int(_get_metric(tool_results, "pytest", "coverage_lines_total", 0))

    # Mutation from mutmut
    mutation_score = int(_get_metric(tool_results, "mutmut", "mutation_score", 0))
    mutation_killed = int(_get_metric(tool_results, "mutmut", "mutation_killed", 0))
    mutation_survived = int(_get_metric(tool_results, "mutmut", "mutation_survived", 0))

    # Security: bandit + pip_audit + trivy
    bandit_high = int(_get_metric(tool_results, "bandit", "bandit_high", 0))
    bandit_med = int(_get_metric(tool_results, "bandit", "bandit_medium", 0))
    bandit_low = int(_get_metric(tool_results, "bandit", "bandit_low", 0))
    pip_audit_vulns = int(_get_metric(tool_results, "pip_audit", "pip_audit_vulns", 0))
    trivy_critical = int(_get_metric(tool_results, "trivy", "trivy_critical", 0))
    trivy_high = int(_get_metric(tool_results, "trivy", "trivy_high", 0))
    trivy_medium = int(_get_metric(tool_results, "trivy", "trivy_medium", 0))
    trivy_low = int(_get_metric(tool_results, "trivy", "trivy_low", 0))
    trivy_max_cvss = float(_get_metric(tool_results, "trivy", "trivy_max_cvss", 0.0))

    # Build tool_metrics dict
    docker_metrics = _get_docker_metrics(tool_results)
    tool_metrics = {
        "ruff_errors": _get_metric(tool_results, "ruff", "ruff_errors", 0),
        "mypy_errors": _get_metric(tool_results, "mypy", "mypy_errors", 0),
        "bandit_high": bandit_high,
        "bandit_medium": bandit_med,
        "bandit_low": bandit_low,
        "black_issues": _get_metric(tool_results, "black", "black_issues", 0),
        "isort_issues": _get_metric(tool_results, "isort", "isort_issues", 0),
        "pip_audit_vulns": pip_audit_vulns,
        "semgrep_findings": _get_metric(tool_results, "semgrep", "semgrep_findings", 0),
        "trivy_critical": trivy_critical,
        "trivy_high": trivy_high,
        "trivy_medium": trivy_medium,
        "trivy_low": trivy_low,
        "trivy_max_cvss": trivy_max_cvss,
        **docker_metrics,
    }

    return ReportMetrics(
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        tests_skipped=tests_skipped,
        tests_runtime=tests_runtime,
        test_status=test_status,
        status_field_name="test",
        coverage=coverage,
        coverage_lines_covered=coverage_lines_covered,
        coverage_lines_total=coverage_lines_total,
        mutation_score=mutation_score,
        mutation_killed=mutation_killed,
        mutation_survived=mutation_survived,
        # Aggregated vulns include bandit (static analysis) + trivy (dependencies)
        critical_vulns=trivy_critical,
        high_vulns=bandit_high + trivy_high,
        medium_vulns=bandit_med + trivy_medium,
        low_vulns=bandit_low + trivy_low,
        # Dependency-only vulns (trivy only for Python) - excludes bandit
        dep_critical=trivy_critical,
        dep_high=trivy_high,
        dep_medium=trivy_medium,
        dep_low=trivy_low,
        tool_metrics=tool_metrics,
        language_version=config.get("python", {}).get("version", ""),
        language_version_field="python_version",
        environment_extras={},
    )


def _extract_java_metrics(
    config: dict[str, Any],
    tool_results: dict[str, dict[str, Any]],
    context: RunContext,
) -> ReportMetrics:
    """Extract metrics from Java tool results."""
    # Test metrics from build tool
    build_payload = tool_results.get("build", {})
    build_success = bool(build_payload.get("success", False))
    tests_passed = int(_get_metric(tool_results, "build", "tests_passed", 0))
    tests_failed = int(_get_metric(tool_results, "build", "tests_failed", 0))
    tests_skipped = int(_get_metric(tool_results, "build", "tests_skipped", 0))
    tests_runtime = float(_get_metric(tool_results, "build", "tests_runtime_seconds", 0.0))

    build_status = "success"
    if not build_success or tests_failed > 0:
        build_status = "failure"

    # Coverage from jacoco
    coverage = int(_get_metric(tool_results, "jacoco", "coverage", 0))
    coverage_lines_covered = int(_get_metric(tool_results, "jacoco", "coverage_lines_covered", 0))
    coverage_lines_total = int(_get_metric(tool_results, "jacoco", "coverage_lines_total", 0))

    # Mutation from pitest
    mutation_score = int(_get_metric(tool_results, "pitest", "mutation_score", 0))
    mutation_killed = int(_get_metric(tool_results, "pitest", "mutation_killed", 0))
    mutation_survived = int(_get_metric(tool_results, "pitest", "mutation_survived", 0))

    # Security: owasp + trivy
    owasp_critical = int(_get_metric(tool_results, "owasp", "owasp_critical", 0))
    owasp_high = int(_get_metric(tool_results, "owasp", "owasp_high", 0))
    owasp_medium = int(_get_metric(tool_results, "owasp", "owasp_medium", 0))
    owasp_low = int(_get_metric(tool_results, "owasp", "owasp_low", 0))
    owasp_max_cvss = float(_get_metric(tool_results, "owasp", "owasp_max_cvss", 0.0))
    trivy_critical = int(_get_metric(tool_results, "trivy", "trivy_critical", 0))
    trivy_high = int(_get_metric(tool_results, "trivy", "trivy_high", 0))
    trivy_medium = int(_get_metric(tool_results, "trivy", "trivy_medium", 0))
    trivy_low = int(_get_metric(tool_results, "trivy", "trivy_low", 0))
    trivy_max_cvss = float(_get_metric(tool_results, "trivy", "trivy_max_cvss", 0.0))

    # Build tool_metrics dict
    docker_metrics = _get_docker_metrics(tool_results)
    tool_metrics = {
        "checkstyle_issues": _get_metric(tool_results, "checkstyle", "checkstyle_issues", 0),
        "spotbugs_issues": _get_metric(tool_results, "spotbugs", "spotbugs_issues", 0),
        "pmd_violations": _get_metric(tool_results, "pmd", "pmd_violations", 0),
        "owasp_critical": owasp_critical,
        "owasp_high": owasp_high,
        "owasp_medium": owasp_medium,
        "owasp_low": owasp_low,
        "owasp_max_cvss": owasp_max_cvss,
        "semgrep_findings": _get_metric(tool_results, "semgrep", "semgrep_findings", 0),
        "trivy_critical": trivy_critical,
        "trivy_high": trivy_high,
        "trivy_medium": trivy_medium,
        "trivy_low": trivy_low,
        "trivy_max_cvss": trivy_max_cvss,
        **docker_metrics,
    }

    # For Java, all vulns come from dependency scanners (owasp + trivy)
    # No static analysis tool like bandit, so aggregated == dependency
    dep_critical = owasp_critical + trivy_critical
    dep_high = owasp_high + trivy_high
    dep_medium = owasp_medium + trivy_medium
    dep_low = owasp_low + trivy_low

    return ReportMetrics(
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        tests_skipped=tests_skipped,
        tests_runtime=tests_runtime,
        test_status=build_status,
        status_field_name="build",
        coverage=coverage,
        coverage_lines_covered=coverage_lines_covered,
        coverage_lines_total=coverage_lines_total,
        mutation_score=mutation_score,
        mutation_killed=mutation_killed,
        mutation_survived=mutation_survived,
        critical_vulns=dep_critical,
        high_vulns=dep_high,
        medium_vulns=dep_medium,
        low_vulns=dep_low,
        # Dependency-only (owasp + trivy for Java)
        dep_critical=dep_critical,
        dep_high=dep_high,
        dep_medium=dep_medium,
        dep_low=dep_low,
        tool_metrics=tool_metrics,
        language_version=config.get("java", {}).get("version", ""),
        language_version_field="java_version",
        environment_extras={
            "build_tool": context.build_tool,
            "project_type": context.project_type,
            "docker_compose_file": context.docker_compose_file,
            "docker_health_endpoint": context.docker_health_endpoint,
        },
    )


def _build_report(
    metrics: ReportMetrics,
    tools_configured: dict[str, bool],
    tools_ran: dict[str, bool],
    tools_success: dict[str, bool],
    thresholds: dict[str, Any],
    context: RunContext,
    *,
    tools_require_run: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a CI report from extracted metrics.

    This is the shared report builder used by both Python and Java.
    Language-specific differences are captured in ReportMetrics.
    """
    results = {
        metrics.status_field_name: metrics.test_status,
        "coverage": metrics.coverage,
        "coverage_lines_covered": metrics.coverage_lines_covered,
        "coverage_lines_total": metrics.coverage_lines_total,
        "mutation_score": metrics.mutation_score,
        "mutation_killed": metrics.mutation_killed,
        "mutation_survived": metrics.mutation_survived,
        "tests_passed": metrics.tests_passed,
        "tests_failed": metrics.tests_failed,
        "tests_skipped": metrics.tests_skipped,
        "tests_runtime_seconds": metrics.tests_runtime,
        "critical_vulns": metrics.critical_vulns,
        "high_vulns": metrics.high_vulns,
        "medium_vulns": metrics.medium_vulns,
        "low_vulns": metrics.low_vulns,
    }

    # dependency_severity uses dep_* fields (dependency scanners only)
    # This excludes static analysis tools like bandit for Python
    dependency_severity = {
        "critical": metrics.dep_critical,
        "high": metrics.dep_high,
        "medium": metrics.dep_medium,
        "low": metrics.dep_low,
    }

    environment = {
        "workdir": context.workdir,
        "retention_days": context.retention_days,
        **metrics.environment_extras,
    }

    report = {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": __version__,
            "workflow_ref": context.workflow_ref or "",
            "generated_at": _timestamp(),
        },
        "repository": context.repository or "",
        "run_id": context.run_id or "",
        "run_number": context.run_number or "",
        "commit": context.commit or "",
        "branch": context.branch or "",
        "hub_correlation_id": context.correlation_id or "",
        "timestamp": _timestamp(),
        metrics.language_version_field: metrics.language_version,
        "results": results,
        "tool_metrics": metrics.tool_metrics,
        "tools_configured": tools_configured,
        "tools_ran": tools_ran,
        "tools_success": tools_success,
        "tools_require_run": tools_require_run or {},
        "thresholds": thresholds,
        "environment": environment,
        "dependency_severity": dependency_severity,
    }
    return report


def build_python_report(
    config: dict[str, Any],
    tool_results: dict[str, dict[str, Any]],
    tools_configured: dict[str, bool],
    tools_ran: dict[str, bool],
    tools_success: dict[str, bool],
    thresholds: dict[str, Any],
    context: RunContext,
    *,
    tools_require_run: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a CI report for Python projects.

    Extracts metrics from Python-specific tools (pytest, ruff, bandit, etc.)
    and builds a standardized report structure.
    """
    metrics = _extract_python_metrics(config, tool_results, tools_configured)
    return _build_report(
        metrics,
        tools_configured,
        tools_ran,
        tools_success,
        thresholds,
        context,
        tools_require_run=tools_require_run,
    )


def build_java_report(
    config: dict[str, Any],
    tool_results: dict[str, dict[str, Any]],
    tools_configured: dict[str, bool],
    tools_ran: dict[str, bool],
    tools_success: dict[str, bool],
    thresholds: dict[str, Any],
    context: RunContext,
    *,
    tools_require_run: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a CI report for Java projects.

    Extracts metrics from Java-specific tools (Maven/Gradle build, checkstyle,
    spotbugs, owasp, etc.) and builds a standardized report structure.
    """
    metrics = _extract_java_metrics(config, tool_results, context)
    return _build_report(
        metrics,
        tools_configured,
        tools_ran,
        tools_success,
        thresholds,
        context,
        tools_require_run=tools_require_run,
    )
