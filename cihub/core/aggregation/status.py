"""Status helpers for aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.core.reporting import detect_language


def load_dispatch_metadata(dispatch_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in dispatch_dir.rglob("*.json"):
        try:
            data = json.loads(path.read_text())
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


def _status_from_report(report_data: dict[str, Any]) -> tuple[str, str]:
    results = report_data.get("results", {}) or {}
    status = results.get("build") or results.get("test") or "unknown"
    if status in {"success", "failure", "skipped"}:
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
