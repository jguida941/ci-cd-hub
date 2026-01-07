"""Render unified workflow summaries from report.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from cihub.core.gate_specs import threshold_rows, tool_rows

BAR_WIDTH = 20
BAR_FULL = chr(0x2588)
BAR_EMPTY = chr(0x2591)

ENV_ROWS = [
    ("Java Version", "java_version"),
    ("Python Version", "python_version"),
    ("Build Tool", "build_tool"),
    ("Repository", "repository"),
    ("Branch", "branch"),
    ("Run Number", "run_number"),
    ("Working Directory", "workdir"),
    ("Project Type", "project_type"),
    ("Artifact Retention", "retention_days"),
    ("Docker Compose", "docker_compose_file"),
    ("Health Endpoint", "docker_health_endpoint"),
]


def load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("report.json must be a JSON object")
    return data


def detect_language(report: dict[str, Any]) -> str:
    if "java_version" in report:
        return "java"
    if "python_version" in report:
        return "python"
    return "unknown"


def fmt_bool(value: Any) -> str:
    return "true" if bool(value) else "false"


def fmt_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def fmt_percent(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return f"{value}%"


def fmt_retention(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return f"{value} days"


def fmt_workdir(value: Any) -> str:
    if value in (None, ""):
        return "-"
    if value == ".":
        return "`.` (repo root)"
    return f"`{value}`"


def format_number(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def render_bar(percent: int | None) -> str:
    if percent is None:
        return "-"
    value = max(0, min(100, percent))
    filled = int(value / (100 / BAR_WIDTH))
    bar = f"{BAR_FULL * filled}{BAR_EMPTY * (BAR_WIDTH - filled)}"
    return f"{value}% {bar}"


def build_tools_table(report: dict[str, Any], language: str) -> Iterable[str]:
    tools_configured = report.get("tools_configured", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}
    results = report.get("results", {}) or {}
    env = report.get("environment", {}) or {}

    rows = tool_rows(language)
    lines = [
        "## Tools Enabled",
        "| Category | Tool | Configured | Ran | Success |",
        "|----------|------|------------|-----|---------|",
    ]

    for category, label, key in rows:
        if key == "__build__":
            # Build tool uses "build" as the report key, not "__build__"
            build_tool = env.get("build_tool") or report.get("build_tool") or "build"
            build_status = results.get("build")
            # Check actual build status from report - build is configured if it ran
            build_ran = bool(tools_ran.get("build", False)) or build_status is not None
            build_configured = build_ran  # Build is implicitly configured if it ran
            build_success = fmt_bool(build_status == "success")
            lines.append(
                f"| {category} | {build_tool} | {fmt_bool(build_configured)} "
                f"| {fmt_bool(build_ran)} | {build_success} |"
            )
            continue
        configured = fmt_bool(tools_configured.get(key, False))
        ran = fmt_bool(tools_ran.get(key, False))
        success = fmt_bool(tools_success.get(key, False))
        lines.append(f"| {category} | {label} | {configured} | {ran} | {success} |")

    lines.append("")
    return lines


def build_thresholds_table(report: dict[str, Any], language: str) -> Iterable[str]:
    thresholds = report.get("thresholds", {}) or {}
    rows = threshold_rows(language)
    lines = [
        "## Thresholds (effective)",
        "| Setting | Value |",
        "|---------|-------|",
    ]
    for label, key, suffix in rows:
        value = thresholds.get(key)
        if suffix == "%":
            display = fmt_percent(value)
        else:
            display = fmt_value(value)
        lines.append(f"| {label} | {display} |")
    lines.append("")
    return lines


def build_environment_table(report: dict[str, Any]) -> Iterable[str]:
    env = report.get("environment", {}) or {}
    merged = {
        "java_version": report.get("java_version"),
        "python_version": report.get("python_version"),
        "build_tool": env.get("build_tool") or report.get("build_tool"),
        "repository": report.get("repository"),
        "branch": report.get("branch"),
        "run_number": report.get("run_number"),
        "workdir": env.get("workdir") or report.get("workdir"),
        "project_type": env.get("project_type"),
        "retention_days": env.get("retention_days"),
        "docker_compose_file": env.get("docker_compose_file"),
        "docker_health_endpoint": env.get("docker_health_endpoint"),
    }

    lines = [
        "## Environment",
        "| Setting | Value |",
        "|---------|-------|",
    ]

    for label, key in ENV_ROWS:
        value = merged.get(key)
        if key == "run_number":
            display = f"#{value}" if value else "-"
        elif key == "retention_days":
            display = fmt_retention(value)
        elif key == "workdir":
            display = fmt_workdir(value)
        else:
            display = fmt_value(value)
        lines.append(f"| {label} | {display} |")

    lines.append("")
    return lines


def build_java_metrics(report: dict[str, Any]) -> Iterable[str]:
    results = report.get("results", {}) or {}
    tool_metrics = report.get("tool_metrics", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}

    passed = format_number(results.get("tests_passed"))
    failed = format_number(results.get("tests_failed"))
    skipped = format_number(results.get("tests_skipped"))
    runtime = results.get("tests_runtime_seconds")
    runtime_display = f"{runtime:.3f}s" if isinstance(runtime, (int, float)) else "-"
    total = passed + failed + skipped

    cov = format_number(results.get("coverage"))
    cov_lines_covered = format_number(results.get("coverage_lines_covered"))
    cov_lines_total = format_number(results.get("coverage_lines_total"))
    cov_detail = "-"
    if cov_lines_total > 0:
        cov_detail = f"{cov_lines_covered} / {cov_lines_total} lines covered"

    mut = format_number(results.get("mutation_score"))
    mut_killed = format_number(results.get("mutation_killed"))
    mut_survived = format_number(results.get("mutation_survived"))
    mut_detail = f"{mut_killed} killed, {mut_survived} survived"

    owasp_crit = format_number(tool_metrics.get("owasp_critical"))
    owasp_high = format_number(tool_metrics.get("owasp_high"))
    owasp_med = format_number(tool_metrics.get("owasp_medium"))

    spotbugs = format_number(tool_metrics.get("spotbugs_issues"))
    pmd = format_number(tool_metrics.get("pmd_violations"))
    checkstyle = format_number(tool_metrics.get("checkstyle_issues"))
    semgrep = format_number(tool_metrics.get("semgrep_findings"))
    trivy_crit = format_number(tool_metrics.get("trivy_critical"))
    trivy_high = format_number(tool_metrics.get("trivy_high"))

    jacoco_ran = bool(tools_ran.get("jacoco"))
    pitest_ran = bool(tools_ran.get("pitest"))
    owasp_ran = bool(tools_ran.get("owasp"))
    spotbugs_ran = bool(tools_ran.get("spotbugs"))
    pmd_ran = bool(tools_ran.get("pmd"))
    checkstyle_ran = bool(tools_ran.get("checkstyle"))
    semgrep_ran = bool(tools_ran.get("semgrep"))
    trivy_ran = bool(tools_ran.get("trivy"))

    test_detail = f"Runtime: {runtime_display}, Failures: {failed}, Skipped: {skipped}"
    coverage_value = render_bar(cov) if jacoco_ran else "-"
    coverage_detail = cov_detail if jacoco_ran else "-"
    mutation_value = render_bar(mut) if pitest_ran else "-"
    mutation_detail = mut_detail if pitest_ran else "-"
    owasp_status = "scan complete" if owasp_ran else "-"
    owasp_detail = f"{owasp_crit} crit, {owasp_high} high, {owasp_med} med" if owasp_ran else "-"
    spotbugs_detail = "Static analysis" if spotbugs_ran else "-"
    pmd_detail = "Code analysis" if pmd_ran else "-"
    checkstyle_detail = "Code style" if checkstyle_ran else "-"
    semgrep_detail = "SAST analysis" if semgrep_ran else "-"
    trivy_detail = "Container scan" if trivy_ran else "-"

    lines = [
        "## QA Metrics (Java)",
        "| Metric | Result | Details |",
        "|--------|--------|---------|",
        f"| Tests | {total} executed | {test_detail} |",
        f"| Line Coverage (JaCoCo) | {coverage_value} | {coverage_detail} |",
        f"| Mutation Score (PITest) | {mutation_value} | {mutation_detail} |",
        f"| Dependency-Check | {owasp_status} | {owasp_detail} |",
        f"| SpotBugs | {spotbugs} bugs | {spotbugs_detail} |",
        f"| PMD | {pmd} violations | {pmd_detail} |",
        f"| Checkstyle | {checkstyle} violations | {checkstyle_detail} |",
        f"| Semgrep | {semgrep} findings | {semgrep_detail} |",
        f"| Trivy | {trivy_crit} crit, {trivy_high} high | {trivy_detail} |",
        "",
    ]
    return lines


def build_python_metrics(report: dict[str, Any]) -> Iterable[str]:
    results = report.get("results", {}) or {}
    tool_metrics = report.get("tool_metrics", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}

    passed = format_number(results.get("tests_passed"))
    failed = format_number(results.get("tests_failed"))
    skipped = format_number(results.get("tests_skipped"))
    runtime = results.get("tests_runtime_seconds")
    runtime_display = f"{runtime:.3f}s" if isinstance(runtime, (int, float)) else "-"
    total = passed + failed + skipped

    cov = format_number(results.get("coverage"))
    cov_lines_covered = format_number(results.get("coverage_lines_covered"))
    cov_lines_total = format_number(results.get("coverage_lines_total"))
    cov_detail = "-"
    if cov_lines_total > 0:
        cov_detail = f"{cov_lines_covered} / {cov_lines_total} lines covered"

    mut = format_number(results.get("mutation_score"))
    mut_killed = format_number(results.get("mutation_killed"))
    mut_survived = format_number(results.get("mutation_survived"))
    mut_detail = f"{mut_killed} killed, {mut_survived} survived"

    bandit_high = format_number(tool_metrics.get("bandit_high"))
    bandit_med = format_number(tool_metrics.get("bandit_medium"))
    bandit_low = format_number(tool_metrics.get("bandit_low"))
    ruff = format_number(tool_metrics.get("ruff_errors"))
    black = format_number(tool_metrics.get("black_issues"))
    isort = format_number(tool_metrics.get("isort_issues"))
    mypy = format_number(tool_metrics.get("mypy_errors"))
    pip_audit = format_number(tool_metrics.get("pip_audit_vulns"))
    semgrep = format_number(tool_metrics.get("semgrep_findings"))
    trivy_crit = format_number(tool_metrics.get("trivy_critical"))
    trivy_high = format_number(tool_metrics.get("trivy_high"))

    pytest_ran = bool(tools_ran.get("pytest"))
    mutmut_ran = bool(tools_ran.get("mutmut"))
    ruff_ran = bool(tools_ran.get("ruff"))
    black_ran = bool(tools_ran.get("black"))
    isort_ran = bool(tools_ran.get("isort"))
    mypy_ran = bool(tools_ran.get("mypy"))
    bandit_ran = bool(tools_ran.get("bandit"))
    pip_audit_ran = bool(tools_ran.get("pip_audit"))
    semgrep_ran = bool(tools_ran.get("semgrep"))
    trivy_ran = bool(tools_ran.get("trivy"))

    test_detail = f"Runtime: {runtime_display}, Failures: {failed}, Skipped: {skipped}"
    coverage_value = render_bar(cov) if pytest_ran else "-"
    coverage_detail = cov_detail if pytest_ran else "-"
    mutation_value = render_bar(mut) if mutmut_ran else "-"
    mutation_detail = mut_detail if mutmut_ran else "-"
    ruff_detail = "Linting" if ruff_ran else "-"
    black_detail = "Format check" if black_ran else "-"
    isort_detail = "Import order" if isort_ran else "-"
    mypy_detail = "Type check" if mypy_ran else "-"
    bandit_detail = "Security scan" if bandit_ran else "-"
    bandit_counts = f"high {bandit_high}, med {bandit_med}, low {bandit_low}"
    pip_audit_detail = "Dependency check" if pip_audit_ran else "-"
    semgrep_detail = "SAST analysis" if semgrep_ran else "-"
    trivy_detail = "Container scan" if trivy_ran else "-"

    lines = [
        "## QA Metrics (Python)",
        "| Metric | Result | Details |",
        "|--------|--------|---------|",
        f"| Tests | {total} executed | {test_detail} |",
        f"| Line Coverage (pytest) | {coverage_value} | {coverage_detail} |",
        f"| Mutation Score (mutmut) | {mutation_value} | {mutation_detail} |",
        f"| Ruff | {ruff} issues | {ruff_detail} |",
        f"| Black | {black} issues | {black_detail} |",
        f"| isort | {isort} issues | {isort_detail} |",
        f"| mypy | {mypy} errors | {mypy_detail} |",
        f"| Bandit | {bandit_counts} | {bandit_detail} |",
        f"| pip-audit | {pip_audit} vulns | {pip_audit_detail} |",
        f"| Semgrep | {semgrep} findings | {semgrep_detail} |",
        f"| Trivy | {trivy_crit} crit, {trivy_high} high | {trivy_detail} |",
        "",
    ]
    return lines


def build_dependency_severity(report: dict[str, Any]) -> Iterable[str]:
    results = report.get("results", {}) or {}
    severity = report.get("dependency_severity", {}) or {}
    crit = severity.get("critical", results.get("critical_vulns"))
    high = severity.get("high", results.get("high_vulns"))
    med = severity.get("medium", results.get("medium_vulns"))
    low = severity.get("low", results.get("low_vulns"))

    lines = [
        "## Dependency Severity",
        "| Severity | Count |",
        "|----------|-------|",
        f"| Critical | {format_number(crit)} |",
        f"| High | {format_number(high)} |",
        f"| Medium | {format_number(med)} |",
        f"| Low | {format_number(low)} |",
        "",
    ]
    return lines


def build_quality_gates(report: dict[str, Any], language: str) -> Iterable[str]:
    results = report.get("results", {}) or {}
    tool_metrics = report.get("tool_metrics", {}) or {}
    thresholds = report.get("thresholds", {}) or {}
    tools_configured = report.get("tools_configured", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}
    tools_require_run = report.get("tools_require_run", {}) or {}

    def gate_status(condition: bool, fail_label: str) -> str:
        """Return gate status indicator."""
        if condition:
            return "PASSED"
        return fail_label.upper()

    def ran(tool: str) -> bool:
        return bool(tools_ran.get(tool, False))

    def not_run_status(tool: str) -> str:
        """Return NOT RUN status with annotation for hard-fail vs soft-skip."""
        if tools_require_run.get(tool, False):
            return "NOT RUN (required)"  # Hard-fail: will cause CI to fail
        return "NOT RUN"  # Soft-skip: warning only

    def skip_status() -> str:
        """Return SKIP status."""
        return "SKIP"

    lines = [
        "## Quality Gates",
        "| Check | Status |",
        "|-------|--------|",
    ]

    tests_failed = format_number(results.get("tests_failed"))
    tests_passed = format_number(results.get("tests_passed"))
    tests_skipped = format_number(results.get("tests_skipped"))
    tests_total = tests_failed + tests_passed + tests_skipped
    if tests_total == 0:
        lines.append("| Unit Tests | NOT RUN |")
    else:
        lines.append(f"| Unit Tests | {gate_status(tests_failed == 0, 'Failed')} |")

    if language == "java":
        if tools_configured.get("jacoco", False):
            if not ran("jacoco"):
                lines.append(f"| JaCoCo Coverage | {not_run_status('jacoco')} |")
            else:
                cov = format_number(results.get("coverage"))
                min_cov = format_number(thresholds.get("coverage_min"))
                cov_status = gate_status(cov >= min_cov, "Failed")
                lines.append(f"| JaCoCo Coverage | {cov_status} |")
        else:
            lines.append("| JaCoCo Coverage | SKIP |")

        if tools_configured.get("pitest", False):
            if not ran("pitest"):
                lines.append(f"| PITest Mutation | {not_run_status('pitest')} |")
            else:
                mut = format_number(results.get("mutation_score"))
                min_mut = format_number(thresholds.get("mutation_score_min"))
                mut_status = gate_status(mut >= min_mut, "Failed")
                lines.append(f"| PITest Mutation | {mut_status} |")
        else:
            lines.append("| PITest Mutation | SKIP |")

        if tools_configured.get("checkstyle", False):
            if not ran("checkstyle"):
                lines.append(f"| Checkstyle | {not_run_status('checkstyle')} |")
            else:
                issues = format_number(tool_metrics.get("checkstyle_issues"))
                max_issues = format_number(thresholds.get("max_checkstyle_errors"))
                lines.append(f"| Checkstyle | {gate_status(issues <= max_issues, 'Violations')} |")
        else:
            lines.append("| Checkstyle | SKIP |")

        if tools_configured.get("spotbugs", False):
            if not ran("spotbugs"):
                lines.append(f"| SpotBugs | {not_run_status('spotbugs')} |")
            else:
                issues = format_number(tool_metrics.get("spotbugs_issues"))
                max_issues = format_number(thresholds.get("max_spotbugs_bugs"))
                lines.append(f"| SpotBugs | {gate_status(issues <= max_issues, 'Bugs found')} |")
        else:
            lines.append("| SpotBugs | SKIP |")

        if tools_configured.get("pmd", False):
            if not ran("pmd"):
                lines.append(f"| PMD | {not_run_status('pmd')} |")
            else:
                issues = format_number(tool_metrics.get("pmd_violations"))
                max_issues = format_number(thresholds.get("max_pmd_violations"))
                lines.append(f"| PMD | {gate_status(issues <= max_issues, 'Violations')} |")
        else:
            lines.append("| PMD | SKIP |")

        if tools_configured.get("owasp", False):
            if not ran("owasp"):
                lines.append(f"| OWASP Check | {not_run_status('owasp')} |")
            else:
                crit = format_number(tool_metrics.get("owasp_critical"))
                high = format_number(tool_metrics.get("owasp_high"))
                max_crit = format_number(thresholds.get("max_critical_vulns"))
                max_high = format_number(thresholds.get("max_high_vulns"))
                ok = crit <= max_crit and high <= max_high
                lines.append(f"| OWASP Check | {gate_status(ok, 'Vulnerabilities')} |")
        else:
            lines.append("| OWASP Check | SKIP |")

        if tools_configured.get("semgrep", False):
            if not ran("semgrep"):
                lines.append(f"| Semgrep | {not_run_status('semgrep')} |")
            else:
                findings = format_number(tool_metrics.get("semgrep_findings"))
                max_findings = format_number(thresholds.get("max_semgrep_findings"))
                lines.append(f"| Semgrep | {gate_status(findings <= max_findings, 'Findings')} |")
        else:
            lines.append("| Semgrep | SKIP |")

        if tools_configured.get("trivy", False):
            if not ran("trivy"):
                lines.append(f"| Trivy | {not_run_status('trivy')} |")
            else:
                crit = format_number(tool_metrics.get("trivy_critical"))
                high = format_number(tool_metrics.get("trivy_high"))
                max_crit = format_number(thresholds.get("max_critical_vulns"))
                max_high = format_number(thresholds.get("max_high_vulns"))
                ok = crit <= max_crit and high <= max_high
                lines.append(f"| Trivy | {gate_status(ok, 'Findings')} |")
        else:
            lines.append("| Trivy | SKIP |")

        if tools_configured.get("codeql", False):
            if not ran("codeql"):
                lines.append(f"| CodeQL | {not_run_status('codeql')} |")
            else:
                lines.append(f"| CodeQL | {gate_status(bool(tools_success.get('codeql', False)), 'Failed')} |")
        else:
            lines.append("| CodeQL | SKIP |")

        if tools_configured.get("docker", False):
            docker_missing = bool(tool_metrics.get("docker_missing_compose", False))
            if docker_missing:
                lines.append("| Docker | Missing compose |")
            elif not ran("docker"):
                lines.append(f"| Docker | {not_run_status('docker')} |")
            else:
                lines.append(f"| Docker | {gate_status(bool(tools_success.get('docker', False)), 'Failed')} |")
        else:
            lines.append("| Docker | SKIP |")

        if tools_configured.get("sbom", False):
            if not ran("sbom"):
                lines.append(f"| SBOM | {not_run_status('sbom')} |")
            else:
                lines.append(f"| SBOM | {gate_status(bool(tools_success.get('sbom', False)), 'Failed')} |")
        else:
            lines.append("| SBOM | SKIP |")

    else:
        if tools_configured.get("pytest", False):
            if not ran("pytest"):
                lines.append(f"| pytest | {not_run_status('pytest')} |")
            elif tests_total == 0:
                lines.append(f"| pytest | {not_run_status('pytest')} |")
            else:
                lines.append(f"| pytest | {gate_status(tests_failed == 0, 'Failed')} |")
        else:
            lines.append("| pytest | SKIP |")

        if tools_configured.get("mutmut", False):
            if not ran("mutmut"):
                lines.append(f"| mutmut | {not_run_status('mutmut')} |")
            else:
                mut = format_number(results.get("mutation_score"))
                min_mut = format_number(thresholds.get("mutation_score_min"))
                lines.append(f"| mutmut | {gate_status(mut >= min_mut, 'Failed')} |")
        else:
            lines.append("| mutmut | SKIP |")

        if tools_configured.get("ruff", False):
            if not ran("ruff"):
                lines.append(f"| Ruff | {not_run_status('ruff')} |")
            else:
                issues = format_number(tool_metrics.get("ruff_errors"))
                max_issues = format_number(thresholds.get("max_ruff_errors"))
                lines.append(f"| Ruff | {gate_status(issues <= max_issues, 'Issues')} |")
        else:
            lines.append("| Ruff | SKIP |")

        if tools_configured.get("black", False):
            if not ran("black"):
                lines.append(f"| Black | {not_run_status('black')} |")
            else:
                issues = format_number(tool_metrics.get("black_issues"))
                max_issues = format_number(thresholds.get("max_black_issues"))
                lines.append(f"| Black | {gate_status(issues <= max_issues, 'Issues')} |")
        else:
            lines.append("| Black | SKIP |")

        if tools_configured.get("isort", False):
            if not ran("isort"):
                lines.append(f"| isort | {not_run_status('isort')} |")
            else:
                issues = format_number(tool_metrics.get("isort_issues"))
                max_issues = format_number(thresholds.get("max_isort_issues"))
                lines.append(f"| isort | {gate_status(issues <= max_issues, 'Issues')} |")
        else:
            lines.append("| isort | SKIP |")

        if tools_configured.get("mypy", False):
            if not ran("mypy"):
                lines.append(f"| mypy | {not_run_status('mypy')} |")
            else:
                issues = format_number(tool_metrics.get("mypy_errors"))
                lines.append(f"| mypy | {gate_status(issues == 0, 'Errors')} |")
        else:
            lines.append("| mypy | SKIP |")

        if tools_configured.get("bandit", False):
            if not ran("bandit"):
                lines.append(f"| Bandit | {not_run_status('bandit')} |")
            else:
                high = format_number(tool_metrics.get("bandit_high"))
                max_high = format_number(thresholds.get("max_high_vulns"))
                lines.append(f"| Bandit | {gate_status(high <= max_high, 'Findings')} |")
        else:
            lines.append("| Bandit | SKIP |")

        if tools_configured.get("pip_audit", False):
            if not ran("pip_audit"):
                lines.append(f"| pip-audit | {not_run_status('pip_audit')} |")
            else:
                vulns = format_number(tool_metrics.get("pip_audit_vulns"))
                max_high = format_number(thresholds.get("max_high_vulns"))
                raw_pip = thresholds.get("max_pip_audit_vulns")
                limit = format_number(raw_pip) if raw_pip is not None else max_high
                lines.append(f"| pip-audit | {gate_status(vulns <= limit, 'Findings')} |")
        else:
            lines.append("| pip-audit | SKIP |")

        if tools_configured.get("semgrep", False):
            if not ran("semgrep"):
                lines.append(f"| Semgrep | {not_run_status('semgrep')} |")
            else:
                findings = format_number(tool_metrics.get("semgrep_findings"))
                max_findings = format_number(thresholds.get("max_semgrep_findings"))
                lines.append(f"| Semgrep | {gate_status(findings <= max_findings, 'Findings')} |")
        else:
            lines.append("| Semgrep | SKIP |")

        if tools_configured.get("trivy", False):
            if not ran("trivy"):
                lines.append(f"| Trivy | {not_run_status('trivy')} |")
            else:
                crit = format_number(tool_metrics.get("trivy_critical"))
                high = format_number(tool_metrics.get("trivy_high"))
                max_crit = format_number(thresholds.get("max_critical_vulns"))
                max_high = format_number(thresholds.get("max_high_vulns"))
                ok = crit <= max_crit and high <= max_high
                lines.append(f"| Trivy | {gate_status(ok, 'Findings')} |")
        else:
            lines.append("| Trivy | SKIP |")

        if tools_configured.get("codeql", False):
            if not ran("codeql"):
                lines.append(f"| CodeQL | {not_run_status('codeql')} |")
            else:
                lines.append(f"| CodeQL | {gate_status(bool(tools_success.get('codeql', False)), 'Failed')} |")
        else:
            lines.append("| CodeQL | SKIP |")

        if tools_configured.get("docker", False):
            docker_missing = bool(tool_metrics.get("docker_missing_compose", False))
            if docker_missing:
                lines.append("| Docker | Missing compose |")
            elif not ran("docker"):
                lines.append(f"| Docker | {not_run_status('docker')} |")
            else:
                lines.append(f"| Docker | {gate_status(bool(tools_success.get('docker', False)), 'Failed')} |")
        else:
            lines.append("| Docker | SKIP |")

        if tools_configured.get("sbom", False):
            if not ran("sbom"):
                lines.append(f"| SBOM | {not_run_status('sbom')} |")
            else:
                lines.append(f"| SBOM | {gate_status(bool(tools_success.get('sbom', False)), 'Failed')} |")
        else:
            lines.append("| SBOM | SKIP |")

    lines.append("")
    return lines


def render_summary(report: dict[str, Any], include_metrics: bool = True) -> str:
    language = detect_language(report)
    sections: list[str] = [
        "# Configuration Summary",
        "",
    ]
    sections.extend(build_tools_table(report, language))
    sections.extend(build_thresholds_table(report, language))
    sections.extend(build_environment_table(report))
    if include_metrics:
        if language == "java":
            sections.extend(build_java_metrics(report))
        elif language == "python":
            sections.extend(build_python_metrics(report))
    sections.extend(build_dependency_severity(report))
    sections.extend(build_quality_gates(report, language))
    return "\n".join(sections).strip() + "\n"


def render_summary_from_path(report_path: Path, include_metrics: bool = True) -> str:
    report = load_report(report_path)
    return render_summary(report, include_metrics=include_metrics)
