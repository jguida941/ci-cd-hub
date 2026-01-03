"""Rendering helpers for aggregation summaries."""

from __future__ import annotations

from typing import Any

from cihub.core.reporting import render_summary


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    def collect_values(key: str) -> list[float]:
        return [r[key] for r in results if isinstance(r.get(key), (int, float))]

    coverages = collect_values("coverage")
    mutations = collect_values("mutation_score")

    owasp_critical = collect_values("owasp_critical")
    owasp_high = collect_values("owasp_high")
    owasp_medium = collect_values("owasp_medium")
    bandit_high = collect_values("bandit_high")
    bandit_medium = collect_values("bandit_medium")
    pip_audit_vulns = collect_values("pip_audit_vulns")
    trivy_critical = collect_values("trivy_critical")
    trivy_high = collect_values("trivy_high")
    semgrep_findings = collect_values("semgrep_findings")

    checkstyle_issues = collect_values("checkstyle_issues")
    spotbugs_issues = collect_values("spotbugs_issues")
    pmd_violations = collect_values("pmd_violations")
    ruff_errors = collect_values("ruff_errors")
    black_issues = collect_values("black_issues")
    isort_issues = collect_values("isort_issues")
    mypy_errors = collect_values("mypy_errors")

    aggregated: dict[str, Any] = {}

    if coverages:
        aggregated["coverage_average"] = round(sum(coverages) / len(coverages), 1)
    if mutations:
        aggregated["mutation_average"] = round(sum(mutations) / len(mutations), 1)

    aggregated["total_critical_vulns"] = sum(owasp_critical) + sum(trivy_critical)
    aggregated["total_high_vulns"] = sum(owasp_high) + sum(bandit_high) + sum(trivy_high)
    aggregated["total_medium_vulns"] = sum(owasp_medium) + sum(bandit_medium)
    aggregated["total_pip_audit_vulns"] = sum(pip_audit_vulns)
    aggregated["total_semgrep_findings"] = sum(semgrep_findings)
    aggregated["total_code_quality_issues"] = (
        sum(checkstyle_issues)
        + sum(spotbugs_issues)
        + sum(pmd_violations)
        + sum(ruff_errors)
        + sum(black_issues)
        + sum(isort_issues)
        + sum(mypy_errors)
    )

    return aggregated


def generate_details_markdown(results: list[dict[str, Any]]) -> str:
    lines = ["# Per-Repo Details", ""]
    for entry in results:
        config = entry.get("config", "unknown")
        report_data = entry.get("_report_data")
        status = entry.get("status", "unknown")
        conclusion = entry.get("conclusion", "unknown")
        lines.append(f"<details><summary><strong>{config}</strong></summary>")
        lines.append("")
        if report_data:
            try:
                detailed_summary = render_summary(report_data, include_metrics=True)
                lines.append(detailed_summary)
            except Exception as exc:
                lines.append(f"*Error rendering summary: {exc}*")
        else:
            lines.append(f"*No report.json available (status: {status}, conclusion: {conclusion}).*")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines)


def generate_summary_markdown(
    results: list[dict[str, Any]],
    report: dict[str, Any],
    total_repos: int,
    dispatched: int,
    missing: int,
    missing_run_id: int,
    *,
    dispatched_label: str = "Successfully dispatched",
    missing_label: str = "Missing metadata",
    include_details: bool = False,
    details_md: str | None = None,
) -> str:
    def fmt(val, suffix=""):
        return f"{val}{suffix}" if val is not None else "-"

    def status_label_for(entry: dict[str, Any]) -> str:
        status = entry.get("status", "unknown")
        conclusion = entry.get("conclusion", status)
        if status in {"missing_run_id", "fetch_failed", "timed_out", "missing_report"}:
            return "MISSING"
        if conclusion == "success":
            return "PASS"
        if conclusion in {"failure", "failed", "cancelled", "timed_out"}:
            return "FAIL"
        if status == "completed" and isinstance(conclusion, str) and conclusion:
            return conclusion.upper()
        return "PENDING"

    failed_runs = len([r for r in results if status_label_for(r) == "FAIL"])
    missing_runs = len([r for r in results if status_label_for(r) == "MISSING"])
    pending_runs = len([r for r in results if status_label_for(r) == "PENDING"])

    lines = [
        "# CI/CD Hub Report",
        "",
        f"**Run ID:** {report['hub_run_id']}",
        f"**Timestamp:** {report['timestamp']}",
        "",
        "## Dispatch Status",
        f"- Total configs: {total_repos}",
        f"- {dispatched_label}: {dispatched}",
        f"- {missing_label}: {missing}",
        f"- Missing run IDs: {missing_run_id}",
        f"- Failed runs: {failed_runs}",
        f"- Missing reports: {missing_runs}",
        f"- Pending runs: {pending_runs}",
        "",
    ]

    java_results = [r for r in results if r.get("language") == "java"]
    python_results = [r for r in results if r.get("language") == "python"]

    if java_results:
        lines.extend(
            [
                "## Java Repos",
                "",
                "| Config | Status | Coverage | Mutation | Checkstyle | SpotBugs | PMD | OWASP | Semgrep | Trivy |",
                "|--------|--------|----------|----------|------------|----------|-----|-------|---------|-------|",
            ]
        )
        for entry in java_results:
            config = entry.get("config", "unknown")
            status_label = status_label_for(entry)

            cov = fmt(entry.get("coverage"), "%")
            mut = fmt(entry.get("mutation_score"), "%")
            cs = fmt(entry.get("checkstyle_issues"))
            sb = fmt(entry.get("spotbugs_issues"))
            pmd = fmt(entry.get("pmd_violations"))

            oc = entry.get("owasp_critical")
            oh = entry.get("owasp_high")
            om = entry.get("owasp_medium")
            if any(v is not None for v in [oc, oh, om]):
                owasp = f"{oc or 0}/{oh or 0}/{om or 0}"
            else:
                owasp = "-"

            sem = fmt(entry.get("semgrep_findings"))
            tc, th = entry.get("trivy_critical"), entry.get("trivy_high")
            if any(v is not None for v in [tc, th]):
                trivy = f"{tc or 0}/{th or 0}"
            else:
                trivy = "-"

            lines.append(
                f"| {config} | {status_label} | {cov} | {mut} | {cs} | {sb} | {pmd} | {owasp} | {sem} | {trivy} |"
            )
        lines.append("")

    if python_results:
        hdr = "| Config | Status | Coverage | Mutation | Tests | Ruff | Black "
        hdr += "| isort | mypy | Bandit | pip-audit | Semgrep | Trivy |"
        sep = "|--------|--------|----------|----------|-------|------|-------"
        sep += "|-------|------|--------|-----------|---------|-------|"
        lines.extend(["## Python Repos", "", hdr, sep])
        for entry in python_results:
            config = entry.get("config", "unknown")
            status_label = status_label_for(entry)

            cov = fmt(entry.get("coverage"), "%")
            mut = fmt(entry.get("mutation_score"), "%")

            tp, tf = entry.get("tests_passed"), entry.get("tests_failed")
            if any(v is not None for v in [tp, tf]):
                tests = f"{tp or 0}/{tf or 0}"
            else:
                tests = "-"

            ruff = fmt(entry.get("ruff_errors"))
            black = fmt(entry.get("black_issues"))
            isort = fmt(entry.get("isort_issues"))
            mypy = fmt(entry.get("mypy_errors"))

            bh, bm = entry.get("bandit_high"), entry.get("bandit_medium")
            if any(v is not None for v in [bh, bm]):
                bandit = f"{bh or 0}/{bm or 0}"
            else:
                bandit = "-"

            pip = fmt(entry.get("pip_audit_vulns"))
            sem = fmt(entry.get("semgrep_findings"))

            tc, th = entry.get("trivy_critical"), entry.get("trivy_high")
            if any(v is not None for v in [tc, th]):
                trivy = f"{tc or 0}/{th or 0}"
            else:
                trivy = "-"

            lines.append(
                f"| {config} | {status_label} | {cov} | {mut} | {tests} "
                f"| {ruff} | {black} | {isort} | {mypy} | {bandit} "
                f"| {pip} | {sem} | {trivy} |"
            )
        lines.append("")

    lines.extend(["## Aggregated Metrics", "", "### Quality"])
    if "coverage_average" in report:
        lines.append(f"- **Average Coverage:** {report['coverage_average']}%")
    if "mutation_average" in report:
        lines.append(f"- **Average Mutation Score:** {report['mutation_average']}%")
    total_issues = report["total_code_quality_issues"]
    lines.append(f"- **Total Code Quality Issues:** {total_issues}")

    crit = report["total_critical_vulns"]
    high = report["total_high_vulns"]
    med = report["total_medium_vulns"]
    pip_v = report["total_pip_audit_vulns"]
    sem_f = report["total_semgrep_findings"]
    lines.extend(
        [
            "",
            "### Security",
            f"- **Critical Vulnerabilities (OWASP+Trivy):** {crit}",
            f"- **High Vulnerabilities (OWASP+Bandit+Trivy):** {high}",
            f"- **Medium Vulnerabilities (OWASP+Bandit):** {med}",
            f"- **pip-audit Vulnerabilities:** {pip_v}",
            f"- **Semgrep Findings:** {sem_f}",
        ]
    )

    if include_details:
        if details_md is None:
            details_md = generate_details_markdown(results)
        lines.extend(["", "---", ""])
        lines.extend(details_md.splitlines())

    return "\n".join(lines)
