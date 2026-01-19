"""Gate evaluation for Python and Java CI runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cihub.ci_report import RunContext
from cihub.core.gate_specs import (
    evaluate_threshold,
    get_threshold_spec_by_key,
)
from cihub.utils import get_git_branch, get_repo_name
from cihub.utils.github_context import GitHubContext

from .helpers import _get_git_commit, _tool_gate_enabled


def _check_threshold(
    spec_key: str,
    language: str,
    threshold_value: int | float,
    metric_value: int | float,
    failures: list[str],
) -> None:
    """Check a threshold using gate_specs and append failure if any.

    Uses evaluate_threshold from gate_specs to avoid duplicating
    threshold comparison logic. The spec's failure_template is used
    to generate consistent failure messages.
    """
    spec = get_threshold_spec_by_key(language, spec_key)
    if spec:
        passed, msg = evaluate_threshold(spec, metric_value, threshold_value)
        if not passed and msg:
            failures.append(msg)


def _tool_requires_run_or_fail(tool: str, config: dict[str, Any], language: str) -> bool:
    """Determine if a tool requires run or fail based on config hierarchy.

    Resolution order (highest wins):
    1. Per-tool setting: {language}.tools.{tool}.require_run_or_fail
    2. Global tool default: gates.tool_defaults.{tool}
    3. Global default: gates.require_run_or_fail (fallback: false)
    """
    # 1. Check per-tool setting
    lang_tools = config.get(language, {}).get("tools", {}) or {}
    tool_config = lang_tools.get(tool, {}) or {}
    if isinstance(tool_config, dict) and "require_run_or_fail" in tool_config:
        return bool(tool_config["require_run_or_fail"])

    # 2. Check global tool default
    gates_config = config.get("gates", {}) or {}
    tool_defaults = gates_config.get("tool_defaults", {}) or {}
    if tool in tool_defaults:
        return bool(tool_defaults[tool])

    # 3. Fall back to global default
    return bool(gates_config.get("require_run_or_fail", False))


def _check_require_run_or_fail(
    tool: str,
    tools_configured: dict[str, bool],
    tools_ran: dict[str, Any],
    config: dict[str, Any],
    language: str,
) -> str | None:
    """Check if a configured tool that didn't run should cause failure.

    Returns failure message if tool requires run and didn't, None otherwise.
    """
    if not tools_configured.get(tool):
        return None  # Tool not configured - no check needed

    if tools_ran.get(tool):
        return None  # Tool ran - no failure from require_run

    if _tool_requires_run_or_fail(tool, config, language):
        return f"{tool} configured but did not run (require_run_or_fail=true)"

    return None  # Tool didn't run but require_run_or_fail is false


def _build_context(
    repo_path: Path,
    config: dict[str, Any],
    workdir: str,
    correlation_id: str | None,
    build_tool: str | None = None,
    project_type: str | None = None,
    docker_compose_file: str | None = None,
    docker_health_endpoint: str | None = None,
) -> RunContext:
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    ctx = GitHubContext.from_env()
    branch = ctx.ref_name or repo_info.get("default_branch")
    branch = branch or get_git_branch(repo_path) or ""
    return RunContext(
        repository=get_repo_name(config, repo_path),
        branch=branch,
        run_id=ctx.run_id,
        run_number=ctx.run_number,
        commit=ctx.sha or _get_git_commit(repo_path),
        correlation_id=correlation_id,
        workflow_ref=ctx.workflow_ref,
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _evaluate_python_gates(
    report: dict[str, Any],
    thresholds: dict[str, Any],
    tools_configured: dict[str, bool],
    config: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    results = report.get("results", {}) or {}
    metrics = report.get("tool_metrics", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}

    # Issue 12: Check test execution - fail if no tests ran
    tests_passed = int(results.get("tests_passed", 0))
    tests_failed = int(results.get("tests_failed", 0))
    tests_skipped = int(results.get("tests_skipped", 0))
    tests_total = tests_passed + tests_failed + tests_skipped

    if tools_configured.get("pytest"):
        if tests_total == 0:
            failures.append("no tests ran - cannot verify quality")
        elif tests_failed > 0:
            failures.append("pytest failures detected")

    # Coverage gate - uses gate_specs for consistent evaluation
    # Use float() to avoid truncation (79.9% should not become 79%)
    if tools_configured.get("pytest"):
        coverage_min = float(thresholds.get("coverage_min", 0) or 0)
        coverage = float(results.get("coverage", 0))
        _check_threshold("coverage_min", "python", coverage_min, coverage, failures)

    # Mutation score gate - uses gate_specs for consistent evaluation
    # Use float() to avoid truncation
    if tools_configured.get("mutmut"):
        mut_min = float(thresholds.get("mutation_score_min", 0) or 0)
        mut_score = float(results.get("mutation_score", 0))
        _check_threshold("mutation_score_min", "python", mut_min, mut_score, failures)

    # Ruff errors gate - uses gate_specs for consistent evaluation
    if tools_configured.get("ruff") and _tool_gate_enabled(config, "ruff", "python"):
        max_ruff = int(thresholds.get("max_ruff_errors", 0) or 0)
        ruff_errors = int(metrics.get("ruff_errors", 0))
        _check_threshold("max_ruff_errors", "python", max_ruff, ruff_errors, failures)

    # Black issues gate - uses gate_specs for consistent evaluation
    if tools_configured.get("black") and _tool_gate_enabled(config, "black", "python"):
        max_black = int(thresholds.get("max_black_issues", 0) or 0)
        black_issues = int(metrics.get("black_issues", 0))
        _check_threshold("max_black_issues", "python", max_black, black_issues, failures)

    # Isort issues gate - uses gate_specs for consistent evaluation
    if tools_configured.get("isort") and _tool_gate_enabled(config, "isort", "python"):
        max_isort = int(thresholds.get("max_isort_issues", 0) or 0)
        isort_issues = int(metrics.get("isort_issues", 0))
        _check_threshold("max_isort_issues", "python", max_isort, isort_issues, failures)

    # Mypy gate - uses gate_specs for consistent evaluation (threshold always 0)
    if tools_configured.get("mypy"):
        mypy_errors = int(metrics.get("mypy_errors", 0))
        _check_threshold("max_mypy_errors", "python", 0, mypy_errors, failures)

    # Bandit gates - uses gate_specs with severity-level toggles
    max_high = int(thresholds.get("max_high_vulns", 0) or 0)
    bandit_cfg = config.get("python", {}).get("tools", {}).get("bandit", {}) or {}
    fail_on_high = bool(bandit_cfg.get("fail_on_high", True))
    fail_on_medium = bool(bandit_cfg.get("fail_on_medium", False))
    fail_on_low = bool(bandit_cfg.get("fail_on_low", False))
    if tools_configured.get("bandit"):
        if fail_on_high:
            bandit_high = int(metrics.get("bandit_high", 0))
            _check_threshold("max_high_vulns", "python", max_high, bandit_high, failures)
        if fail_on_medium:
            bandit_medium = int(metrics.get("bandit_medium", 0))
            _check_threshold("max_bandit_medium", "python", 0, bandit_medium, failures)
        if fail_on_low:
            bandit_low = int(metrics.get("bandit_low", 0))
            _check_threshold("max_bandit_low", "python", 0, bandit_low, failures)

    # pip-audit gate - uses gate_specs for consistent evaluation
    if tools_configured.get("pip_audit") and _tool_gate_enabled(config, "pip_audit", "python"):
        max_pip = int(thresholds.get("max_pip_audit_vulns", max_high) or 0)
        pip_vulns = int(metrics.get("pip_audit_vulns", 0))
        _check_threshold("max_pip_audit_vulns", "python", max_pip, pip_vulns, failures)

    # Semgrep gate - uses gate_specs for consistent evaluation
    if tools_configured.get("semgrep") and _tool_gate_enabled(config, "semgrep", "python"):
        max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
        semgrep_findings = int(metrics.get("semgrep_findings", 0))
        _check_threshold("max_semgrep_findings", "python", max_semgrep, semgrep_findings, failures)

    # Trivy critical/high gates - uses gate_specs with severity-level toggles
    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    trivy_cfg = config.get("python", {}).get("tools", {}).get("trivy", {}) or {}
    if tools_configured.get("trivy"):
        if bool(trivy_cfg.get("fail_on_critical", True)):
            trivy_critical = int(metrics.get("trivy_critical", 0))
            _check_threshold("max_trivy_critical", "python", max_critical, trivy_critical, failures)
        if bool(trivy_cfg.get("fail_on_high", True)):
            trivy_high = int(metrics.get("trivy_high", 0))
            _check_threshold("max_trivy_high", "python", max_high, trivy_high, failures)

    # CVSS enforcement for Trivy (Python) - uses gate_specs for consistent evaluation
    # Note: threshold=0 disables check (handled in evaluate_threshold)
    if tools_configured.get("trivy") and tools_ran.get("trivy"):
        trivy_cvss_fail = float(thresholds.get("trivy_cvss_fail", 0) or 0)
        trivy_max_cvss = float(metrics.get("trivy_max_cvss", 0) or 0)
        _check_threshold("trivy_cvss_fail", "python", trivy_cvss_fail, trivy_max_cvss, failures)

    codeql_cfg = config.get("python", {}).get("tools", {}).get("codeql", {}) or {}
    fail_codeql = bool(codeql_cfg.get("fail_on_error", True))
    if tools_configured.get("codeql") and fail_codeql:
        if not tools_ran.get("codeql"):
            failures.append("codeql did not run")
        elif not tools_success.get("codeql"):
            failures.append("codeql failed")

    # Hypothesis gate - property-based testing via pytest
    # Hypothesis runs through pytest, so we check ran/success status rather than thresholds
    hypothesis_cfg = config.get("python", {}).get("tools", {}).get("hypothesis", {}) or {}
    fail_hypothesis = bool(hypothesis_cfg.get("fail_on_error", True))
    if tools_configured.get("hypothesis") and fail_hypothesis:
        if not tools_ran.get("hypothesis"):
            failures.append("hypothesis did not run")
        elif not tools_success.get("hypothesis"):
            failures.append("hypothesis failed")

    docker_cfg = config.get("python", {}).get("tools", {}).get("docker", {}) or {}
    fail_docker = bool(docker_cfg.get("fail_on_error", True))
    fail_missing = bool(docker_cfg.get("fail_on_missing_compose", False))
    docker_missing = bool(metrics.get("docker_missing_compose", False))
    if tools_configured.get("docker"):
        if docker_missing:
            if fail_missing:
                failures.append("docker compose file missing")
        elif fail_docker:
            if not tools_ran.get("docker"):
                failures.append("docker did not run")
            elif not tools_success.get("docker"):
                failures.append("docker failed")

    # require_run_or_fail checks: configured tools that didn't run
    # Iterate tools_configured keys to include custom tools (x-* prefix)
    for tool in tools_configured:
        failure = _check_require_run_or_fail(tool, tools_configured, tools_ran, config, "python")
        if failure:
            failures.append(failure)

    return failures


def _evaluate_java_gates(
    report: dict[str, Any],
    thresholds: dict[str, Any],
    tools_configured: dict[str, bool],
    config: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    results = report.get("results", {}) or {}
    metrics = report.get("tool_metrics", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}

    # Issue 12: Check test execution - fail if no tests ran
    tests_passed = int(results.get("tests_passed", 0))
    tests_failed = int(results.get("tests_failed", 0))
    tests_skipped = int(results.get("tests_skipped", 0))
    tests_total = tests_passed + tests_failed + tests_skipped

    if tests_total == 0:
        failures.append("no tests ran - cannot verify quality")
    elif tests_failed > 0:
        failures.append("test failures detected")

    # Coverage gate - uses gate_specs for consistent evaluation
    # Use float() to avoid truncation (79.9% should not become 79%)
    if tools_configured.get("jacoco"):
        coverage_min = float(thresholds.get("coverage_min", 0) or 0)
        coverage = float(results.get("coverage", 0))
        _check_threshold("coverage_min", "java", coverage_min, coverage, failures)

    # Mutation score gate - uses gate_specs for consistent evaluation
    # Use float() to avoid truncation
    if tools_configured.get("pitest"):
        mut_min = float(thresholds.get("mutation_score_min", 0) or 0)
        mut_score = float(results.get("mutation_score", 0))
        _check_threshold("mutation_score_min", "java", mut_min, mut_score, failures)

    # Checkstyle gate - uses gate_specs for consistent evaluation
    if tools_configured.get("checkstyle") and _tool_gate_enabled(config, "checkstyle", "java"):
        max_checkstyle = int(thresholds.get("max_checkstyle_errors", 0) or 0)
        checkstyle_issues = int(metrics.get("checkstyle_issues", 0))
        _check_threshold("max_checkstyle_errors", "java", max_checkstyle, checkstyle_issues, failures)

    # SpotBugs gate - uses gate_specs for consistent evaluation
    if tools_configured.get("spotbugs") and _tool_gate_enabled(config, "spotbugs", "java"):
        max_spotbugs = int(thresholds.get("max_spotbugs_bugs", 0) or 0)
        spotbugs_issues = int(metrics.get("spotbugs_issues", 0))
        _check_threshold("max_spotbugs_bugs", "java", max_spotbugs, spotbugs_issues, failures)

    # PMD gate - uses gate_specs for consistent evaluation
    if tools_configured.get("pmd") and _tool_gate_enabled(config, "pmd", "java"):
        max_pmd = int(thresholds.get("max_pmd_violations", 0) or 0)
        pmd_issues = int(metrics.get("pmd_violations", 0))
        _check_threshold("max_pmd_violations", "java", max_pmd, pmd_issues, failures)

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    max_high = int(thresholds.get("max_high_vulns", 0) or 0)

    # OWASP critical/high gates - uses gate_specs for consistent evaluation
    if tools_configured.get("owasp"):
        owasp_critical = int(metrics.get("owasp_critical", 0))
        owasp_high = int(metrics.get("owasp_high", 0))
        _check_threshold("max_critical_vulns", "java", max_critical, owasp_critical, failures)
        _check_threshold("max_high_vulns", "java", max_high, owasp_high, failures)

    # Trivy critical/high gates - uses gate_specs with severity-level toggles
    trivy_cfg = config.get("java", {}).get("tools", {}).get("trivy", {}) or {}
    if tools_configured.get("trivy"):
        if bool(trivy_cfg.get("fail_on_critical", True)):
            trivy_critical = int(metrics.get("trivy_critical", 0))
            _check_threshold("max_trivy_critical", "java", max_critical, trivy_critical, failures)
        if bool(trivy_cfg.get("fail_on_high", True)):
            trivy_high = int(metrics.get("trivy_high", 0))
            _check_threshold("max_trivy_high", "java", max_high, trivy_high, failures)

    # CVSS enforcement for OWASP (Java) - uses gate_specs for consistent evaluation
    # Note: threshold=0 disables check (handled in evaluate_threshold)
    if tools_configured.get("owasp") and tools_ran.get("owasp"):
        owasp_cvss_fail = float(thresholds.get("owasp_cvss_fail", 0) or 0)
        owasp_max_cvss = float(metrics.get("owasp_max_cvss", 0) or 0)
        _check_threshold("owasp_cvss_fail", "java", owasp_cvss_fail, owasp_max_cvss, failures)

    # CVSS enforcement for Trivy (Java) - uses gate_specs for consistent evaluation
    # Note: threshold=0 disables check (handled in evaluate_threshold)
    if tools_configured.get("trivy") and tools_ran.get("trivy"):
        trivy_cvss_fail = float(thresholds.get("trivy_cvss_fail", 0) or 0)
        trivy_max_cvss = float(metrics.get("trivy_max_cvss", 0) or 0)
        _check_threshold("trivy_cvss_fail", "java", trivy_cvss_fail, trivy_max_cvss, failures)

    # Semgrep gate - uses gate_specs for consistent evaluation
    if tools_configured.get("semgrep") and _tool_gate_enabled(config, "semgrep", "java"):
        max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
        semgrep_findings = int(metrics.get("semgrep_findings", 0))
        _check_threshold("max_semgrep_findings", "java", max_semgrep, semgrep_findings, failures)

    codeql_cfg = config.get("java", {}).get("tools", {}).get("codeql", {}) or {}
    fail_codeql = bool(codeql_cfg.get("fail_on_error", True))
    if tools_configured.get("codeql") and fail_codeql:
        if not tools_ran.get("codeql"):
            failures.append("codeql did not run")
        elif not tools_success.get("codeql"):
            failures.append("codeql failed")

    # jqwik gate - property-based testing for Java (equivalent to Hypothesis)
    # jqwik runs through the build tool's test runner, so we check ran/success status
    jqwik_cfg = config.get("java", {}).get("tools", {}).get("jqwik", {}) or {}
    fail_jqwik = bool(jqwik_cfg.get("fail_on_error", True))
    if tools_configured.get("jqwik") and fail_jqwik:
        if not tools_ran.get("jqwik"):
            failures.append("jqwik did not run")
        elif not tools_success.get("jqwik"):
            failures.append("jqwik failed")

    docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
    fail_docker = bool(docker_cfg.get("fail_on_error", True))
    fail_missing = bool(docker_cfg.get("fail_on_missing_compose", False))
    docker_missing = bool(metrics.get("docker_missing_compose", False))
    if tools_configured.get("docker"):
        if docker_missing:
            if fail_missing:
                failures.append("docker compose file missing")
        elif fail_docker:
            if not tools_ran.get("docker"):
                failures.append("docker did not run")
            elif not tools_success.get("docker"):
                failures.append("docker failed")

    # require_run_or_fail checks: configured tools that didn't run
    # Iterate tools_configured keys to include custom tools (x-* prefix)
    for tool in tools_configured:
        failure = _check_require_run_or_fail(tool, tools_configured, tools_ran, config, "java")
        if failure:
            failures.append(failure)

    return failures
