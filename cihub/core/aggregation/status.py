"""Status helpers for aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.core.gate_specs import evaluate_threshold, get_metric_value, get_thresholds
from cihub.core.reporting import detect_language


def load_dispatch_metadata(dispatch_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in dispatch_dir.rglob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print(f"Warning: skipping non-object JSON in {path}")
                continue
            data["_source"] = str(path)
            entries.append(data)
        except Exception as exc:
            print(f"Warning: could not read {path}: {exc}")
    return entries


def create_run_status(entry: dict[str, Any]) -> dict[str, Any]:
    repo = entry.get("repo", "unknown/unknown")
    run_id = entry.get("run_id")

    return {
        "config": entry.get("config", repo.split("/")[-1] if "/" in repo else repo),
        "repo": repo,
        "subdir": entry.get("subdir", ""),
        "language": entry.get("language"),
        "branch": entry.get("branch"),
        "workflow": entry.get("workflow"),
        "run_id": run_id or "",
        "correlation_id": entry.get("correlation_id", ""),
        "status": "missing_run_id" if not run_id else "unknown",
        "conclusion": "unknown",
        # Common quality metrics
        "coverage": None,
        "mutation_score": None,
        # Java-specific tools
        "checkstyle_issues": None,
        "spotbugs_issues": None,
        "pmd_violations": None,
        "owasp_critical": None,
        "owasp_high": None,
        "owasp_medium": None,
        # Python-specific tools
        "tests_passed": None,
        "tests_failed": None,
        "ruff_errors": None,
        "black_issues": None,
        "isort_issues": None,
        "mypy_errors": None,
        "bandit_high": None,
        "bandit_medium": None,
        "pip_audit_vulns": None,
        # Cross-language security tools
        "semgrep_findings": None,
        "trivy_critical": None,
        "trivy_high": None,
        # Track which tools ran
        "tools_ran": {},
        "tools_configured": {},
        "tools_success": {},
    }


def _artifact_name_from_report(report_path: Path, reports_dir: Path) -> str:
    try:
        relative = report_path.relative_to(reports_dir)
    except ValueError:
        relative = report_path

    if relative.parts:
        return relative.parts[0]
    return report_path.parent.name or report_path.stem


def _config_from_artifact_name(artifact_name: str) -> str:
    suffix = "-ci-report"
    if artifact_name.endswith(suffix):
        return artifact_name[: -len(suffix)]
    return artifact_name


def _evaluate_threshold_failures(report_data: dict[str, Any], language: str) -> list[str]:
    if language not in {"python", "java"}:
        return []
    thresholds = report_data.get("thresholds", {}) or {}
    if not thresholds:
        return []
    results = report_data.get("results", {}) or {}
    tool_metrics = report_data.get("tool_metrics", {}) or {}

    failures: list[str] = []
    for spec in get_thresholds(language):
        if spec.key not in thresholds:
            continue
        threshold_value = thresholds.get(spec.key)
        if threshold_value is None:
            continue
        metric_value = get_metric_value(spec, results, tool_metrics)
        passed, msg = evaluate_threshold(spec, metric_value, threshold_value)
        if not passed and msg:
            failures.append(msg)
    return failures


def _evaluate_tool_failures(report_data: dict[str, Any], language: str) -> list[str]:
    results = report_data.get("results", {}) or {}
    tools_configured = report_data.get("tools_configured", {}) or {}
    tools_ran = report_data.get("tools_ran", {}) or {}
    tools_success = report_data.get("tools_success", {}) or {}
    tools_require_run = report_data.get("tools_require_run", {}) or {}

    tests_passed = int(results.get("tests_passed", 0) or 0)
    tests_failed = int(results.get("tests_failed", 0) or 0)
    tests_skipped = int(results.get("tests_skipped", 0) or 0)
    tests_total = tests_passed + tests_failed + tests_skipped

    failures: list[str] = []
    if language == "python":
        if tools_configured.get("pytest"):
            if tests_total == 0:
                failures.append("no tests ran - cannot verify quality")
            elif tests_failed > 0:
                failures.append("pytest failures detected")
    elif language == "java":
        if tests_total == 0:
            failures.append("no tests ran - cannot verify quality")
        elif tests_failed > 0:
            failures.append("test failures detected")
    else:
        if tests_failed > 0:
            failures.append("test failures detected")

    for tool, configured in tools_configured.items():
        if not configured:
            continue
        if tools_require_run.get(tool) and not tools_ran.get(tool):
            failures.append(f"{tool} configured but did not run (require_run_or_fail=true)")
        if tools_ran.get(tool) and tools_success.get(tool) is False:
            failures.append(f"{tool} failed")

    return failures


def _status_from_report(report_data: dict[str, Any]) -> tuple[str, str]:
    results = report_data.get("results", {}) or {}
    status = results.get("build") or results.get("test")
    status = status if status in {"success", "failure", "skipped"} else None

    language = detect_language(report_data)
    failures: list[str] = []
    if status == "failure":
        failures.append("build/test failure")
    failures.extend(_evaluate_tool_failures(report_data, language))
    failures.extend(_evaluate_threshold_failures(report_data, language))
    if failures:
        return "completed", "failure"

    if status:
        return "completed", status

    tests_failed = results.get("tests_failed")
    if isinstance(tests_failed, int):
        return "completed", "failure" if tests_failed > 0 else "success"
    return "completed", "unknown"


def _run_status_from_report(
    report_data: dict[str, Any],
    report_path: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    artifact_name = _artifact_name_from_report(report_path, reports_dir)
    config_name = _config_from_artifact_name(artifact_name)
    repo = report_data.get("repository") or config_name
    branch = report_data.get("branch") or ""
    workflow_ref = report_data.get("metadata", {}).get("workflow_ref", "")
    correlation = report_data.get("hub_correlation_id", "") or ""
    run_id = report_data.get("run_id", "") or ""
    workdir = report_data.get("environment", {}).get("workdir") or ""
    language = detect_language(report_data)

    entry = {
        "config": config_name,
        "repo": repo,
        "subdir": workdir if workdir not in ("", ".") else "",
        "language": language,
        "branch": branch,
        "workflow": workflow_ref,
        "run_id": run_id,
        "correlation_id": correlation,
    }
    run_status = create_run_status(entry)
    status, conclusion = _status_from_report(report_data)
    run_status["status"] = status
    run_status["conclusion"] = conclusion
    return run_status


def _run_status_for_invalid_report(report_path: Path, reports_dir: Path, reason: str) -> dict[str, Any]:
    artifact_name = _artifact_name_from_report(report_path, reports_dir)
    config_name = _config_from_artifact_name(artifact_name)
    entry = {
        "config": config_name,
        "repo": config_name,
        "subdir": "",
        "language": "unknown",
        "branch": "",
        "workflow": "",
        "run_id": "",
        "correlation_id": "",
    }
    run_status = create_run_status(entry)
    run_status["status"] = reason
    run_status["conclusion"] = "failure"
    return run_status
