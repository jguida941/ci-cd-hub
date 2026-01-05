"""Gate evaluation for Python and Java CI runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cihub.ci_report import RunContext
from cihub.utils import get_git_branch

from .helpers import _get_git_commit, _get_repo_name, _tool_gate_enabled


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
    branch = os.environ.get("GITHUB_REF_NAME") or repo_info.get("default_branch")
    branch = branch or get_git_branch(repo_path) or ""
    return RunContext(
        repository=_get_repo_name(config, repo_path),
        branch=branch,
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_number=os.environ.get("GITHUB_RUN_NUMBER"),
        commit=os.environ.get("GITHUB_SHA") or _get_git_commit(repo_path),
        correlation_id=correlation_id,
        workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF"),
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

    tests_failed = int(results.get("tests_failed", 0))
    if tools_configured.get("pytest") and tests_failed > 0:
        failures.append("pytest failures detected")

    coverage_min = int(thresholds.get("coverage_min", 0) or 0)
    coverage = int(results.get("coverage", 0))
    if tools_configured.get("pytest") and coverage < coverage_min:
        failures.append(f"coverage {coverage}% < {coverage_min}%")

    mut_min = int(thresholds.get("mutation_score_min", 0) or 0)
    mut_score = int(results.get("mutation_score", 0))
    if tools_configured.get("mutmut") and mut_score < mut_min:
        failures.append(f"mutation score {mut_score}% < {mut_min}%")

    max_ruff = int(thresholds.get("max_ruff_errors", 0) or 0)
    ruff_errors = int(metrics.get("ruff_errors", 0))
    if tools_configured.get("ruff") and _tool_gate_enabled(config, "ruff", "python") and ruff_errors > max_ruff:
        failures.append(f"ruff errors {ruff_errors} > {max_ruff}")

    max_black = int(thresholds.get("max_black_issues", 0) or 0)
    black_issues = int(metrics.get("black_issues", 0))
    if tools_configured.get("black") and _tool_gate_enabled(config, "black", "python") and black_issues > max_black:
        failures.append(f"black issues {black_issues} > {max_black}")

    max_isort = int(thresholds.get("max_isort_issues", 0) or 0)
    isort_issues = int(metrics.get("isort_issues", 0))
    if tools_configured.get("isort") and _tool_gate_enabled(config, "isort", "python") and isort_issues > max_isort:
        failures.append(f"isort issues {isort_issues} > {max_isort}")

    mypy_errors = int(metrics.get("mypy_errors", 0))
    if tools_configured.get("mypy") and mypy_errors > 0:
        failures.append(f"mypy errors {mypy_errors} > 0")

    max_high = int(thresholds.get("max_high_vulns", 0) or 0)
    bandit_high = int(metrics.get("bandit_high", 0))
    bandit_medium = int(metrics.get("bandit_medium", 0))
    bandit_low = int(metrics.get("bandit_low", 0))
    bandit_cfg = config.get("python", {}).get("tools", {}).get("bandit", {}) or {}
    fail_on_high = bool(bandit_cfg.get("fail_on_high", True))
    fail_on_medium = bool(bandit_cfg.get("fail_on_medium", False))
    fail_on_low = bool(bandit_cfg.get("fail_on_low", False))
    if tools_configured.get("bandit"):
        if fail_on_high and bandit_high > max_high:
            failures.append(f"bandit high {bandit_high} > {max_high}")
        if fail_on_medium and bandit_medium > 0:
            failures.append(f"bandit medium {bandit_medium} > 0")
        if fail_on_low and bandit_low > 0:
            failures.append(f"bandit low {bandit_low} > 0")

    pip_vulns = int(metrics.get("pip_audit_vulns", 0))
    max_pip = int(thresholds.get("max_pip_audit_vulns", max_high) or 0)
    if tools_configured.get("pip_audit") and _tool_gate_enabled(config, "pip_audit", "python") and pip_vulns > max_pip:
        failures.append(f"pip-audit vulns {pip_vulns} > {max_pip}")

    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
    semgrep_findings = int(metrics.get("semgrep_findings", 0))
    if (
        tools_configured.get("semgrep")
        and _tool_gate_enabled(config, "semgrep", "python")
        and semgrep_findings > max_semgrep
    ):
        failures.append(f"semgrep findings {semgrep_findings} > {max_semgrep}")

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    trivy_critical = int(metrics.get("trivy_critical", 0))
    if (
        tools_configured.get("trivy")
        and bool(config.get("python", {}).get("tools", {}).get("trivy", {}).get("fail_on_critical", True))
        and trivy_critical > max_critical
    ):
        failures.append(f"trivy critical {trivy_critical} > {max_critical}")

    trivy_high = int(metrics.get("trivy_high", 0))
    if (
        tools_configured.get("trivy")
        and bool(config.get("python", {}).get("tools", {}).get("trivy", {}).get("fail_on_high", True))
        and trivy_high > max_high
    ):
        failures.append(f"trivy high {trivy_high} > {max_high}")

    codeql_cfg = config.get("python", {}).get("tools", {}).get("codeql", {}) or {}
    fail_codeql = bool(codeql_cfg.get("fail_on_error", True))
    if tools_configured.get("codeql") and fail_codeql:
        if not tools_ran.get("codeql"):
            failures.append("codeql did not run")
        elif not tools_success.get("codeql"):
            failures.append("codeql failed")

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

    tests_failed = int(results.get("tests_failed", 0))
    if tests_failed > 0:
        failures.append("test failures detected")

    coverage_min = int(thresholds.get("coverage_min", 0) or 0)
    coverage = int(results.get("coverage", 0))
    if tools_configured.get("jacoco") and coverage < coverage_min:
        failures.append(f"coverage {coverage}% < {coverage_min}%")

    mut_min = int(thresholds.get("mutation_score_min", 0) or 0)
    mut_score = int(results.get("mutation_score", 0))
    if tools_configured.get("pitest") and mut_score < mut_min:
        failures.append(f"mutation score {mut_score}% < {mut_min}%")

    max_checkstyle = int(thresholds.get("max_checkstyle_errors", 0) or 0)
    checkstyle_issues = int(metrics.get("checkstyle_issues", 0))
    if (
        tools_configured.get("checkstyle")
        and _tool_gate_enabled(config, "checkstyle", "java")
        and checkstyle_issues > max_checkstyle
    ):
        failures.append(f"checkstyle issues {checkstyle_issues} > {max_checkstyle}")

    max_spotbugs = int(thresholds.get("max_spotbugs_bugs", 0) or 0)
    spotbugs_issues = int(metrics.get("spotbugs_issues", 0))
    if (
        tools_configured.get("spotbugs")
        and _tool_gate_enabled(config, "spotbugs", "java")
        and spotbugs_issues > max_spotbugs
    ):
        failures.append(f"spotbugs issues {spotbugs_issues} > {max_spotbugs}")

    max_pmd = int(thresholds.get("max_pmd_violations", 0) or 0)
    pmd_issues = int(metrics.get("pmd_violations", 0))
    if tools_configured.get("pmd") and _tool_gate_enabled(config, "pmd", "java") and pmd_issues > max_pmd:
        failures.append(f"pmd violations {pmd_issues} > {max_pmd}")

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    max_high = int(thresholds.get("max_high_vulns", 0) or 0)

    owasp_critical = int(metrics.get("owasp_critical", 0))
    owasp_high = int(metrics.get("owasp_high", 0))
    if tools_configured.get("owasp") and (owasp_critical > max_critical or owasp_high > max_high):
        failures.append(f"owasp critical/high {owasp_critical}/{owasp_high} > {max_critical}/{max_high}")

    trivy_critical = int(metrics.get("trivy_critical", 0))
    trivy_high = int(metrics.get("trivy_high", 0))
    trivy_cfg = config.get("java", {}).get("tools", {}).get("trivy", {}) or {}
    trivy_crit_gate = bool(trivy_cfg.get("fail_on_critical", True))
    trivy_high_gate = bool(trivy_cfg.get("fail_on_high", True))
    if tools_configured.get("trivy") and (
        (trivy_crit_gate and trivy_critical > max_critical) or (trivy_high_gate and trivy_high > max_high)
    ):
        failures.append(f"trivy critical/high {trivy_critical}/{trivy_high} > {max_critical}/{max_high}")

    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
    semgrep_findings = int(metrics.get("semgrep_findings", 0))
    if (
        tools_configured.get("semgrep")
        and _tool_gate_enabled(config, "semgrep", "java")
        and semgrep_findings > max_semgrep
    ):
        failures.append(f"semgrep findings {semgrep_findings} > {max_semgrep}")

    codeql_cfg = config.get("java", {}).get("tools", {}).get("codeql", {}) or {}
    fail_codeql = bool(codeql_cfg.get("fail_on_error", True))
    if tools_configured.get("codeql") and fail_codeql:
        if not tools_ran.get("codeql"):
            failures.append("codeql did not run")
        elif not tools_success.get("codeql"):
            failures.append("codeql failed")

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

    return failures
