"""Report build and summary commands."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.ci_report import (
    RunContext,
    build_java_report,
    build_python_report,
    resolve_thresholds,
)
from cihub.cli import (
    CommandResult,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.reporting import render_summary_from_path
from cihub.services import (
    ValidationRules,
    aggregate_from_dispatch,
    aggregate_from_reports_dir,
    validate_report,
)


def _tool_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    tools = config.get(language, {}).get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        return bool(entry.get("enabled", False))
    return False


def _get_repo_name(config: dict[str, Any], repo_path: Path) -> str:
    repo_env = os.environ.get("GITHUB_REPOSITORY")
    if repo_env:
        return repo_env
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    owner = repo_info.get("owner")
    name = repo_info.get("name")
    if owner and name:
        return f"{owner}/{name}"
    remote = get_git_remote(repo_path)
    if remote:
        parsed = parse_repo_from_remote(remote)
        if parsed[0] and parsed[1]:
            return f"{parsed[0]}/{parsed[1]}"
    return ""


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
        commit=os.environ.get("GITHUB_SHA") or "",
        correlation_id=correlation_id,
        workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF"),
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _detect_java_project_type(workdir: Path) -> str:
    pom = workdir / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "<modules>" in content:
            modules = len(re.findall(r"<module>.*?</module>", content))
            return f"Multi-module ({modules} modules)" if modules else "Multi-module"
        return "Single module"

    settings_gradle = workdir / "settings.gradle"
    settings_kts = workdir / "settings.gradle.kts"
    if settings_gradle.exists() or settings_kts.exists():
        return "Multi-module"
    if (workdir / "build.gradle").exists() or (workdir / "build.gradle.kts").exists():
        return "Single module"
    return "Unknown"


def _load_tool_outputs(tool_dir: Path) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for path in tool_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tool = str(data.get("tool") or path.stem)
            outputs[tool] = data
        except json.JSONDecodeError:
            continue
    return outputs


# ============================================================================
# Report Validation (service-backed)
# ============================================================================

def _validate_report(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Validate report.json structure and content."""
    report_path = Path(args.report)
    if not report_path.exists():
        message = f"Report file not found: {report_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"Error: {message}")
        return EXIT_FAILURE

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        message = f"Invalid JSON in report: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"Error: {message}")
        return EXIT_FAILURE

    errors: list[str] = []
    expect_mode = getattr(args, "expect", "clean")
    coverage_min = getattr(args, "coverage_min", 70)

    summary_text = None
    if getattr(args, "summary", None):
        summary_path = Path(args.summary)
        if not summary_path.exists():
            errors.append(f"summary file not found: {summary_path}")
        else:
            summary_text = summary_path.read_text(encoding="utf-8")

    reports_dir = None
    if getattr(args, "reports_dir", None):
        reports_dir = Path(args.reports_dir)
        if not reports_dir.exists():
            errors.append(f"reports dir not found: {reports_dir}")
            reports_dir = None

    rules = ValidationRules(
        expect_clean=expect_mode == "clean",
        coverage_min=coverage_min,
        strict=bool(getattr(args, "strict", False)),
    )
    result = validate_report(
        report,
        rules,
        summary_text=summary_text,
        reports_dir=reports_dir,
    )

    errors.extend(result.errors)
    warnings = list(result.warnings)

    if getattr(args, "debug", False) and result.debug_messages:
        print("Validation debug output:")
        for msg in result.debug_messages:
            print(f"  {msg}")

    if getattr(args, "verbose", False):
        print(f"\nErrors: {len(errors)}, Warnings: {len(warnings)}")

    if errors:
        if not json_mode:
            print(f"Validation FAILED with {len(errors)} errors:")
            for err in errors:
                print(f"  ::error::{err}")
        if warnings:
            for warn in warnings:
                print(f"  ::warning::{warn}")
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Validation failed: {len(errors)} errors",
                problems=[{"severity": "error", "message": e} for e in errors]
                + [{"severity": "warning", "message": w} for w in warnings],
            )
        return EXIT_FAILURE

    if warnings:
        if not json_mode:
            print(f"Validation passed with {len(warnings)} warnings:")
            for warn in warnings:
                print(f"  ::warning::{warn}")
        if rules.strict:
            if json_mode:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary=f"Validation failed (strict): {len(warnings)} warnings",
                    problems=[{"severity": "warning", "message": w} for w in warnings],
                )
            return EXIT_FAILURE

    if not json_mode:
        print("Validation PASSED")
    if json_mode:
        return CommandResult(exit_code=EXIT_SUCCESS, summary="Validation passed")
    return EXIT_SUCCESS


# ============================================================================
# Dashboard Generation (HTML/JSON)
# ============================================================================


def _load_dashboard_reports(
    reports_dir: Path, schema_mode: str = "warn"
) -> tuple[list[dict[str, Any]], int, list[str]]:
    """Load all report JSON files from the reports directory.

    Args:
        reports_dir: Directory containing report.json files
        schema_mode: "warn" to warn on non-2.0 schema, "strict" to skip them

    Returns:
        Tuple of (reports list, skipped count, warnings)
    """
    reports: list[dict[str, Any]] = []
    skipped = 0
    warnings: list[str] = []

    if not reports_dir.exists():
        return reports, skipped, warnings

    for report_file in reports_dir.glob("**/report.json"):
        try:
            with report_file.open(encoding="utf-8") as f:
                report = json.load(f)
                report["_source_file"] = str(report_file)

                # Validate schema version
                schema_version = report.get("schema_version")
                if schema_version != "2.0":
                    if schema_mode == "strict":
                        warnings.append(
                            f"Skipping {report_file}: schema_version={schema_version}, expected '2.0'"
                        )
                        skipped += 1
                        continue
                    else:
                        warnings.append(
                            f"{report_file} has schema_version={schema_version}, expected '2.0'"
                        )

                reports.append(report)
        except (json.JSONDecodeError, OSError) as e:
            warnings.append(f"Could not load {report_file}: {e}")

    return reports, skipped, warnings


def _detect_language(report: dict[str, Any]) -> str:
    """Detect language from report fields."""
    if report.get("java_version"):
        return "java"
    if report.get("python_version"):
        return "python"
    # Fallback to tools_ran inspection
    tools_ran = report.get("tools_ran", {})
    if tools_ran.get("jacoco") or tools_ran.get("checkstyle") or tools_ran.get("spotbugs"):
        return "java"
    if tools_ran.get("pytest") or tools_ran.get("ruff") or tools_ran.get("bandit"):
        return "python"
    return "unknown"


def _get_report_status(report: dict[str, Any]) -> str:
    """Get build/test status from report (handles both Java and Python)."""
    results = report.get("results", {})
    # Python uses 'test', Java uses 'build'
    status = results.get("test") or results.get("build") or "unknown"
    return status


def _generate_dashboard_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary from all reports."""
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "2.0",
        "total_repos": len(reports),
        "languages": {},
        "coverage": {"total": 0, "count": 0, "average": 0},
        "mutation": {"total": 0, "count": 0, "average": 0},
        "tests": {"total_passed": 0, "total_failed": 0},
        "repos": [],
    }

    # Aggregate tool statistics across all repos
    tool_stats: dict[str, dict[str, int]] = {}

    for report in reports:
        repo_name = report.get("repository", "unknown")
        results = report.get("results", {})
        tool_metrics = report.get("tool_metrics", {})
        tools_ran = report.get("tools_ran", {})
        tools_configured = report.get("tools_configured", {})
        tools_success = report.get("tools_success", {})

        # Track languages using helper
        lang = _detect_language(report)
        summary["languages"][lang] = summary["languages"].get(lang, 0) + 1

        # Coverage - include zeros in average (only skip if key is missing)
        coverage = results.get("coverage")
        if coverage is not None:
            summary["coverage"]["total"] += coverage
            summary["coverage"]["count"] += 1
        else:
            coverage = 0  # Default for repo_detail below

        # Mutation score - include zeros in average (only skip if key is missing)
        mutation = results.get("mutation_score")
        if mutation is not None:
            summary["mutation"]["total"] += mutation
            summary["mutation"]["count"] += 1
        else:
            mutation = 0  # Default for repo_detail below

        # Test counts
        tests_passed = results.get("tests_passed", 0)
        tests_failed = results.get("tests_failed", 0)
        summary["tests"]["total_passed"] += tests_passed
        summary["tests"]["total_failed"] += tests_failed

        # Repo details with schema 2.0 fields
        repo_detail: dict[str, Any] = {
            "name": repo_name,
            "branch": report.get("branch", "unknown"),
            "language": lang,
            "status": _get_report_status(report),
            "coverage": coverage,
            "mutation_score": mutation,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "timestamp": report.get("timestamp", "unknown"),
            "schema_version": report.get("schema_version", "unknown"),
        }

        # Include tool_metrics if present
        if tool_metrics:
            repo_detail["tool_metrics"] = tool_metrics

        # Include tools_ran if present
        if tools_ran:
            repo_detail["tools_ran"] = tools_ran

        # Include tools_configured and tools_success if present
        if tools_configured:
            repo_detail["tools_configured"] = tools_configured
        if tools_success:
            repo_detail["tools_success"] = tools_success

        summary["repos"].append(repo_detail)

        # Aggregate tool stats across all repos
        for tool, configured in tools_configured.items():
            if tool not in tool_stats:
                tool_stats[tool] = {"configured": 0, "ran": 0, "passed": 0, "failed": 0}
            if configured:
                tool_stats[tool]["configured"] += 1
            if tools_ran.get(tool):
                tool_stats[tool]["ran"] += 1
            if tools_success.get(tool):
                tool_stats[tool]["passed"] += 1
            elif tools_ran.get(tool):
                tool_stats[tool]["failed"] += 1

    # Calculate averages
    if summary["coverage"]["count"] > 0:
        summary["coverage"]["average"] = round(
            summary["coverage"]["total"] / summary["coverage"]["count"], 1
        )

    if summary["mutation"]["count"] > 0:
        summary["mutation"]["average"] = round(
            summary["mutation"]["total"] / summary["mutation"]["count"], 1
        )

    # Add tool stats to summary
    if tool_stats:
        summary["tool_stats"] = tool_stats

    return summary


def _generate_html_dashboard(summary: dict[str, Any]) -> str:
    """Generate an HTML dashboard from the summary."""
    total_tests = summary["tests"]["total_passed"] + summary["tests"]["total_failed"]
    repos_html = ""
    for repo in summary["repos"]:
        status_class = "success" if repo["status"] == "success" else "failure"
        tests_passed = repo.get("tests_passed", 0)
        tests_failed = repo.get("tests_failed", 0)
        tests_class = "success" if tests_failed == 0 else "failure"
        # Escape user-controlled values to prevent XSS
        name = html.escape(str(repo["name"]))
        language = html.escape(str(repo.get("language", "unknown")))
        branch = html.escape(str(repo["branch"]))
        status = html.escape(str(repo["status"]))
        timestamp = html.escape(str(repo["timestamp"]))
        repos_html += f"""
        <tr>
            <td>{name}</td>
            <td>{language}</td>
            <td>{branch}</td>
            <td class="{status_class}">{status}</td>
            <td>{repo["coverage"]}%</td>
            <td class="{tests_class}">{tests_passed}/{tests_passed + tests_failed}</td>
            <td>{repo["mutation_score"]}%</td>
            <td>{timestamp}</td>
        </tr>
        """

    html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI/CD Hub Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 2rem;
        }}
        h1 {{ color: #58a6ff; margin-bottom: 1rem; }}
        h2 {{ color: #8b949e; margin: 1.5rem 0 1rem; font-size: 1.2rem; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 1.5rem;
        }}
        .card-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #58a6ff;
        }}
        .card-label {{
            color: #8b949e;
            font-size: 0.9rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }}
        th {{ background: #21262d; color: #8b949e; font-weight: 600; }}
        .success {{ color: #3fb950; }}
        .failure {{ color: #f85149; }}
        .timestamp {{ color: #8b949e; font-size: 0.8rem; margin-top: 2rem; }}
    </style>
</head>
<body>
    <h1>CI/CD Hub Dashboard</h1>

    <div class="summary">
        <div class="card">
            <div class="card-value">{summary["total_repos"]}</div>
            <div class="card-label">Total Repositories</div>
        </div>
        <div class="card">
            <div class="card-value">{summary["coverage"]["average"]}%</div>
            <div class="card-label">Average Coverage</div>
        </div>
        <div class="card">
            <div class="card-value">{summary["mutation"]["average"]}%</div>
            <div class="card-label">Average Mutation Score</div>
        </div>
        <div class="card">
            <div class="card-value">{len(summary["languages"])}</div>
            <div class="card-label">Languages</div>
        </div>
        <div class="card">
            <div class="card-value">
                {summary["tests"]["total_passed"]}/{total_tests}
            </div>
            <div class="card-label">Tests Passed</div>
        </div>
    </div>

    <h2>Repository Status</h2>
    <table>
        <thead>
            <tr>
                <th>Repository</th>
                <th>Language</th>
                <th>Branch</th>
                <th>Status</th>
                <th>Coverage</th>
                <th>Tests</th>
                <th>Mutation</th>
                <th>Last Run</th>
            </tr>
        </thead>
        <tbody>
            {repos_html}
        </tbody>
    </table>

    <p class="timestamp">Generated: {summary["generated_at"]}</p>
</body>
</html>
"""
    return html_output


def _parse_env_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _resolve_write_summary(flag: bool | None) -> bool:
    if flag is not None:
        return flag
    env_value = _parse_env_bool(os.environ.get("CIHUB_WRITE_GITHUB_SUMMARY"))
    if env_value is not None:
        return env_value
    return True


def _resolve_summary_path(path_value: str | None, write_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if write_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _append_summary(text: str, summary_path: Path | None, print_stdout: bool) -> None:
    if summary_path is None:
        if print_stdout:
            print(text)
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def _bar(value: int) -> str:
    if value < 0:
        value = 0
    filled = min(20, max(0, value // 5))
    return f"{'#' * filled}{'.' * (20 - filled)}"


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    parsed = _parse_env_bool(str(value))
    if parsed is not None:
        return parsed
    return False


def _security_repo_summary(args: argparse.Namespace) -> str:
    has_source = _coerce_bool(args.has_source)
    codeql_status = "Complete" if has_source else "Skipped (no source code)"
    lines = [
        f"# Security & Supply Chain: {args.repo}",
        "",
        f"**Language:** {args.language}",
        "",
        "---",
        "",
        "## Jobs",
        "",
        "| Job | Status | Duration |",
        "|-----|--------|----------|",
    ]
    if args.language == "python":
        lines.extend(
            [
                f"| pip-audit | {args.pip_audit_vulns} vulns | - |",
                f"| bandit | {args.bandit_high} high severity | - |",
                f"| ruff-security | {args.ruff_issues} issues | - |",
                f"| codeql | {codeql_status} | - |",
                "| sbom | Generated | - |",
            ]
        )
    else:
        lines.extend(
            [
                f"| OWASP | {args.owasp_critical} critical, {args.owasp_high} high | - |",
                f"| codeql | {codeql_status} | - |",
                "| sbom | Generated | - |",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Artifacts",
            "",
            "| Name | Size | Digest |",
            "|------|------|--------|",
            f"| sbom-{args.repo}.spdx.json | - | - |",
        ]
    )
    return "\n".join(lines)


def _security_zap_summary(args: argparse.Namespace) -> str:
    repo_present = _coerce_bool(args.repo_present)
    run_zap = _coerce_bool(args.run_zap)
    has_docker = _coerce_bool(args.has_docker)
    if not repo_present:
        status = "Skipped - Repo checkout failed"
    elif not run_zap:
        status = "Skipped - run_zap input is false"
    elif has_docker:
        status = "Scan completed. See artifacts for detailed report."
    else:
        status = "Skipped - No docker-compose.yml found"
    return "\n".join([f"## ZAP DAST Scan: {args.repo}", status])


def _security_overall_summary(args: argparse.Namespace) -> str:
    lines = [
        "# Security & Supply Chain Summary",
        "",
        f"**Repositories Scanned:** {args.repo_count}",
        f"**Run:** #{args.run_number}",
        "",
        "## Tools Executed",
        "",
        "| Tool | Purpose |",
        "|------|---------|",
        "| CodeQL | Static Application Security Testing (SAST) |",
        "| SBOM | Software Bill of Materials generation |",
        "| pip-audit / OWASP | Dependency vulnerability scanning |",
        "| Bandit / Ruff-S | Python security linting |",
        "| ZAP | Dynamic Application Security Testing (DAST) |",
    ]
    return "\n".join(lines)


def _smoke_repo_summary(args: argparse.Namespace) -> str:
    header = [
        f"# Smoke Test Results: {args.owner}/{args.repo}",
        "",
        f"**Branch:** `{args.branch}` | **Language:** `{args.language}` | **Config:** `{args.config}`",
        "",
        "---",
        "",
    ]
    if args.language == "java":
        cov = int(args.coverage)
        lines = [
            "## Java Smoke Test Results",
            "",
            "| Metric | Result | Status |",
            "|--------|--------|--------|",
            f"| **Unit Tests** | {args.tests_total} executed | {'PASS' if args.tests_total > 0 else 'FAIL'} |",
            f"| **Test Failures** | {args.tests_failed} failed | {'WARN' if args.tests_failed > 0 else 'PASS'} |",
            f"| **Coverage (JaCoCo)** | {cov}% {_bar(cov)} | {'PASS' if cov >= 50 else 'WARN'} |",
            f"| **Checkstyle** | {args.checkstyle_violations} violations | {'WARN' if args.checkstyle_violations > 0 else 'PASS'} |",
            f"| **SpotBugs** | {args.spotbugs_issues} potential bugs | {'WARN' if args.spotbugs_issues > 0 else 'PASS'} |",
            "",
            f"**Coverage Details:** {args.coverage_lines} instructions covered",
            "",
            "### Smoke Test Status",
            "**PASS** - Core Java tools executed successfully"
            if args.tests_total > 0 and cov > 0
            else "**FAIL** - Missing test execution or coverage data",
        ]
        return "\n".join(header + lines)

    cov = int(args.coverage)
    lines = [
        "## Python Smoke Test Results",
        "",
        "| Metric | Result | Status |",
        "|--------|--------|--------|",
        f"| **Unit Tests** | {args.tests_total} passed | {'PASS' if args.tests_total > 0 else 'FAIL'} |",
        f"| **Test Failures** | {args.tests_failed} failed | {'WARN' if args.tests_failed > 0 else 'PASS'} |",
        f"| **Coverage (pytest-cov)** | {cov}% {_bar(cov)} | {'PASS' if cov >= 50 else 'WARN'} |",
        f"| **Ruff Lint** | {args.ruff_errors} issues | {'WARN' if args.ruff_errors > 0 else 'PASS'} |",
        f"| **Black Format** | {args.black_issues} files need reformatting | {'WARN' if args.black_issues > 0 else 'PASS'} |",
        "",
        f"**Security:** {args.ruff_security} security-related issues",
        "",
        "### Smoke Test Status",
        "**PASS** - Core Python tools executed successfully"
        if args.tests_total > 0 and cov > 0
        else "**FAIL** - Missing test execution or coverage data",
    ]
    return "\n".join(header + lines)


def _smoke_overall_summary(args: argparse.Namespace) -> str:
    status = "PASSED" if args.test_result == "success" else "FAILED"
    lines = [
        "# Smoke Test Summary",
        "",
        f"**Total Test Repositories:** {args.repo_count}",
        f"**Run Number:** #{args.run_number}",
        f"**Trigger:** {args.event_name}",
        f"**Status:** {status}",
        "",
        "---",
        "",
        "## What Was Tested",
        "",
        "The smoke test validates core hub functionality:",
        "",
        "- Repository discovery and configuration loading",
        "- Language detection (Java and Python)",
        "- Core tool execution (coverage, linting, style checks)",
        "- Artifact generation and upload",
        "- Summary report generation",
    ]
    return "\n".join(lines)


def _kyverno_summary(args: argparse.Namespace) -> str:
    policies_dir = Path(args.policies_dir)
    lines = [
        args.title,
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Policies Validated | {args.validated} |",
        f"| Validation Failures | {args.failed} |",
        f"| Tests Run | {args.run_tests} |",
        "",
        "## Policies Directory",
        f"`{policies_dir}`",
    ]

    if policies_dir.is_dir():
        lines.extend(["", "| Policy | Status |", "|--------|--------|"])
        for policy in sorted(policies_dir.glob("*.y*ml")):
            lines.append(f"| `{policy.name}` | Validated |")

    lines.extend(["", "---"])
    return "\n".join(lines)


def _orchestrator_load_summary(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            "## Hub Orchestrator",
            "",
            f"**Repositories to build:** {args.repo_count}",
        ]
    )


def _orchestrator_trigger_summary(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            f"## {args.repo}",
            "",
            f"- **Owner:** {args.owner}",
            f"- **Language:** {args.language}",
            f"- **Branch:** {args.branch}",
            f"- **Workflow:** {args.workflow_id}",
            f"- **Run ID:** {args.run_id or 'pending'}",
            f"- **Status:** {args.status}",
        ]
    )


def cmd_report(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    if args.subcommand == "aggregate":
        write_summary = _resolve_write_summary(getattr(args, "write_github_summary", None))
        summary_file = Path(args.summary_file) if args.summary_file else None
        if summary_file is None and write_summary:
            summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary_env:
                summary_file = Path(summary_env)

        total_repos = args.total_repos or int(os.environ.get("TOTAL_REPOS", 0) or 0)
        hub_run_id = args.hub_run_id or os.environ.get("HUB_RUN_ID", os.environ.get("GITHUB_RUN_ID", ""))
        hub_event = args.hub_event or os.environ.get("HUB_EVENT", os.environ.get("GITHUB_EVENT_NAME", ""))

        reports_dir = getattr(args, "reports_dir", None)
        if reports_dir:
            result = aggregate_from_reports_dir(
                reports_dir=Path(reports_dir),
                output_file=Path(args.output),
                defaults_file=Path(args.defaults_file),
                hub_run_id=hub_run_id,
                hub_event=hub_event,
                total_repos=total_repos,
                summary_file=summary_file,
                strict=bool(args.strict),
            )
            exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE
            if json_mode:
                summary = "Aggregation complete" if result.success else "Aggregation failed"
                return CommandResult(
                    exit_code=exit_code,
                    summary=summary,
                    artifacts={
                        "report": str(result.report_path) if result.report_path else "",
                        "summary": str(result.summary_path) if result.summary_path else "",
                    },
                )
            return exit_code

        token = args.token
        token_env = args.token_env or "HUB_DISPATCH_TOKEN"  # noqa: S105
        if not token:
            token = os.environ.get(token_env)
        if not token and token_env != "GITHUB_TOKEN":
            token = os.environ.get("GITHUB_TOKEN")
        if not token:
            message = f"Missing token (expected {token_env} or GITHUB_TOKEN)"
            if json_mode:
                return CommandResult(exit_code=EXIT_FAILURE, summary=message)
            print(message)
            return EXIT_FAILURE

        result = aggregate_from_dispatch(
            dispatch_dir=Path(args.dispatch_dir),
            output_file=Path(args.output),
            defaults_file=Path(args.defaults_file),
            token=token,
            hub_run_id=hub_run_id,
            hub_event=hub_event,
            total_repos=total_repos,
            summary_file=summary_file,
            strict=bool(args.strict),
            timeout_sec=int(args.timeout),
        )
        exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE

        if json_mode:
            summary = "Aggregation complete" if result.success else "Aggregation failed"
            return CommandResult(
                exit_code=exit_code,
                summary=summary,
                artifacts={
                    "report": str(result.report_path) if result.report_path else "",
                    "summary": str(result.summary_path) if result.summary_path else "",
                },
            )
        return exit_code
    if args.subcommand == "outputs":
        report_path = Path(args.report)
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            message = f"Failed to read report: {exc}"
            if json_mode:
                return CommandResult(exit_code=EXIT_FAILURE, summary=message)
            print(message)
            return EXIT_FAILURE

        results = report.get("results", {}) or {}
        status = results.get("build") or results.get("test")
        if status not in {"success", "failure", "skipped"}:
            tests_failed = int(results.get("tests_failed", 0))
            status = "failure" if tests_failed > 0 else "success"

        output_path = Path(args.output) if args.output else None
        if output_path is None:
            output_path_env = os.environ.get("GITHUB_OUTPUT")
            if output_path_env:
                output_path = Path(output_path_env)
        if output_path is None:
            message = "No output target specified for report outputs"
            if json_mode:
                return CommandResult(exit_code=EXIT_USAGE, summary=message)
            print(message)
            return EXIT_USAGE

        output_text = (
            f"build_status={status}\n"
            f"coverage={results.get('coverage', 0)}\n"
            f"mutation_score={results.get('mutation_score', 0)}\n"
        )
        output_path.write_text(output_text, encoding="utf-8")

        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Report outputs written",
                artifacts={"outputs": str(output_path)},
            )
        print(f"Wrote outputs: {output_path}")
        return EXIT_SUCCESS

    if args.subcommand == "summary":
        report_path = Path(args.report)
        summary_text = render_summary_from_path(report_path)
        output_path = Path(args.output) if args.output else None
        if output_path:
            output_path.write_text(summary_text, encoding="utf-8")
        else:
            if _resolve_write_summary(args.write_github_summary):
                print(summary_text)
        github_summary = _resolve_summary_path(None, _resolve_write_summary(args.write_github_summary))
        if github_summary:
            github_summary.write_text(summary_text, encoding="utf-8")
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Summary rendered",
                artifacts={"summary": str(output_path) if output_path else ""},
            )
        return EXIT_SUCCESS

    if args.subcommand == "security-summary":
        mode = args.mode
        if mode == "repo":
            summary_text = _security_repo_summary(args)
        elif mode == "zap":
            summary_text = _security_zap_summary(args)
        else:
            summary_text = _security_overall_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return EXIT_SUCCESS

    if args.subcommand == "smoke-summary":
        mode = args.mode
        if mode == "repo":
            summary_text = _smoke_repo_summary(args)
        else:
            summary_text = _smoke_overall_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return EXIT_SUCCESS

    if args.subcommand == "kyverno-summary":
        summary_text = _kyverno_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return EXIT_SUCCESS

    if args.subcommand == "orchestrator-summary":
        if args.mode == "load-config":
            summary_text = _orchestrator_load_summary(args)
        else:
            summary_text = _orchestrator_trigger_summary(args)
        write_summary = _resolve_write_summary(args.write_github_summary)
        summary_path = _resolve_summary_path(args.summary, write_summary)
        _append_summary(summary_text, summary_path, print_stdout=write_summary)
        return EXIT_SUCCESS

    if args.subcommand == "validate":
        return _validate_report(args, json_mode)

    if args.subcommand == "dashboard":
        reports_dir = Path(args.reports_dir)
        output_path = Path(args.output)
        output_format = getattr(args, "format", "html")
        schema_mode = getattr(args, "schema_mode", "warn")

        # Load reports
        reports, skipped, warnings = _load_dashboard_reports(reports_dir, schema_mode)

        if not json_mode:
            print(f"Loaded {len(reports)} reports")
            if skipped > 0:
                print(f"Skipped {skipped} reports with non-2.0 schema")
            for warn in warnings:
                print(f"Warning: {warn}")

        # Generate summary
        summary = _generate_dashboard_summary(reports)

        # Output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_format == "json":
            output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        else:
            html_content = _generate_html_dashboard(summary)
            output_path.write_text(html_content, encoding="utf-8")

        if not json_mode:
            print(f"Generated {output_format} dashboard: {output_path}")

        # Exit with error if strict mode and reports were skipped
        exit_code = EXIT_FAILURE if (schema_mode == "strict" and skipped > 0) else EXIT_SUCCESS

        if json_mode:
            return CommandResult(
                exit_code=exit_code,
                summary=f"Dashboard generated with {len(reports)} reports",
                artifacts={"dashboard": str(output_path)},
                problems=[{"severity": "warning", "message": w} for w in warnings],
            )
        return exit_code

    if args.subcommand != "build":
        message = f"Unknown report subcommand: {args.subcommand}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message)
        return EXIT_USAGE

    repo_path = Path(args.repo or ".").resolve()
    output_dir = Path(args.output_dir or ".cihub")
    tool_dir = Path(args.tool_dir) if args.tool_dir else output_dir / "tool-outputs"
    report_path = Path(args.report) if args.report else output_dir / "report.json"
    summary_path = Path(args.summary) if args.summary else output_dir / "summary.md"

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    language = config.get("language") or ""
    tool_outputs = _load_tool_outputs(tool_dir)

    if language == "python":
        tools_configured = {
            tool: _tool_enabled(config, tool, "python")
            for tool in [
                "pytest",
                "mutmut",
                "hypothesis",
                "ruff",
                "black",
                "isort",
                "mypy",
                "bandit",
                "pip_audit",
                "sbom",
                "semgrep",
                "trivy",
                "codeql",
                "docker",
            ]
        }
        tools_ran = {tool: False for tool in tools_configured}
        tools_success = {tool: False for tool in tools_configured}
        for tool, data in tool_outputs.items():
            tools_ran[tool] = bool(data.get("ran"))
            tools_success[tool] = bool(data.get("success"))
        if tools_configured.get("hypothesis"):
            tools_ran["hypothesis"] = tools_ran.get("pytest", False)
            tools_success["hypothesis"] = tools_success.get("pytest", False)
        thresholds = resolve_thresholds(config, "python")
        context = _build_context(repo_path, config, args.workdir or ".", args.correlation_id)
        report = build_python_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
    elif language == "java":
        tools_configured = {
            tool: _tool_enabled(config, tool, "java")
            for tool in [
                "jacoco",
                "pitest",
                "jqwik",
                "checkstyle",
                "spotbugs",
                "pmd",
                "owasp",
                "semgrep",
                "trivy",
                "codeql",
                "sbom",
                "docker",
            ]
        }
        tools_ran = {tool: False for tool in tools_configured}
        tools_success = {tool: False for tool in tools_configured}
        for tool, data in tool_outputs.items():
            tools_ran[tool] = bool(data.get("ran"))
            tools_success[tool] = bool(data.get("success"))

        if tools_configured.get("jqwik"):
            build_data = tool_outputs.get("build", {}) or {}
            tests_failed = int(build_data.get("metrics", {}).get("tests_failed", 0))
            build_success = bool(build_data.get("success", False))
            tools_ran["jqwik"] = bool(build_data)
            tools_success["jqwik"] = build_success and tests_failed == 0

        thresholds = resolve_thresholds(config, "java")
        build_tool = config.get("java", {}).get("build_tool", "maven").strip().lower() or "maven"
        project_type = _detect_java_project_type(repo_path / (args.workdir or "."))
        docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
        context = _build_context(
            repo_path,
            config,
            args.workdir or ".",
            args.correlation_id,
            build_tool=build_tool,
            project_type=project_type,
            docker_compose_file=docker_cfg.get("compose_file"),
            docker_health_endpoint=docker_cfg.get("health_endpoint"),
        )
        report = build_java_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
    else:
        message = f"report build supports python or java (got '{language}')"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_text = render_summary_from_path(report_path)
    summary_path.write_text(summary_text, encoding="utf-8")

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Report built",
            artifacts={"report": str(report_path), "summary": str(summary_path)},
        )
    print(f"Wrote report: {report_path}")
    print(f"Wrote summary: {summary_path}")
    return EXIT_SUCCESS
