"""Triage bundle generation service.

This module is being modularized into cihub/services/triage/.
Imports from this file continue to work for backward compatibility.

See cihub/services/triage/__init__.py for the modular structure.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Re-export types from the new triage package (backward compatibility).
# detect_gate_changes is re-exported for backward compatibility.
from cihub.services.triage.detection import detect_gate_changes  # noqa: F401
from cihub.services.triage.detection import (
    detect_flaky_patterns,
    detect_test_count_regression,
)
from cihub.services.triage.evidence import (
    _check_tool_has_artifacts,
    _format_list,
    _get_nested,
    _get_tool_metrics,
    _load_json,
    _load_tool_outputs,
    _normalize_category,
    _severity_for,
    _tool_artifacts,
    _tool_env_name,
    build_tool_evidence,
    validate_artifact_evidence,
)
from cihub.services.triage.types import (
    CATEGORY_BY_TOOL,
    CATEGORY_ORDER,
    MULTI_TRIAGE_SCHEMA_VERSION,
    PRIORITY_SCHEMA_VERSION,
    SEVERITY_BY_CATEGORY,
    SEVERITY_ORDER,
    TRIAGE_SCHEMA_VERSION,
    MultiTriageResult,
    ToolEvidence,
    ToolStatus,
    TriageBundle,
)

# Explicit re-exports for backward compatibility
__all__ = [
    # Types
    "ToolStatus",
    "ToolEvidence",
    "MultiTriageResult",
    "TriageBundle",
    # Constants
    "TRIAGE_SCHEMA_VERSION",
    "PRIORITY_SCHEMA_VERSION",
    "MULTI_TRIAGE_SCHEMA_VERSION",
    "SEVERITY_ORDER",
    "CATEGORY_ORDER",
    "CATEGORY_BY_TOOL",
    "SEVERITY_BY_CATEGORY",
    # Evidence functions
    "build_tool_evidence",
    "validate_artifact_evidence",
    # Detection functions
    "detect_flaky_patterns",
    "detect_test_count_regression",
    # Bundle generation (defined in this module)
    "aggregate_triage_bundles",
    "generate_triage_bundle",
    "write_triage_bundle",
    # Legacy helper re-exports
    "_load_json",
    "_load_tool_outputs",
    "_format_list",
    "_normalize_category",
    "_severity_for",
    "_tool_env_name",
    "_tool_artifacts",
    "_get_nested",
    "_get_tool_metrics",
    "_check_tool_has_artifacts",
]


# ---------------------------------------------------------------------------
# Local helpers for bundle generation (not yet migrated to triage/ package)
# ---------------------------------------------------------------------------


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repro_command(tool: str, repo_path: Path, workdir: str | None, output_dir: Path) -> dict[str, Any]:
    env_name = _tool_env_name(tool)
    command = f"cihub ci --repo {repo_path} --workdir {workdir or '.'} --output-dir {output_dir}"
    return {"command": command, "cwd": str(repo_path), "env": {env_name: "true"}}


def _failure_entry(
    *,
    tool: str,
    status: str,
    reason: str,
    message: str,
    output_dir: Path,
    tool_payload: dict[str, Any],
    repo_path: Path,
    workdir: str | None,
) -> dict[str, Any]:
    category = _normalize_category(tool)
    severity = _severity_for(category)
    # If a tool is required to run but did not, this is always a hard failure.
    if status == "required_not_run":
        severity = "blocker"
    return {
        "id": f"{tool}:{status}",
        "category": category,
        "severity": severity,
        "tool": tool,
        "status": status,
        "reason": reason,
        "message": message,
        "artifacts": _tool_artifacts(output_dir, tool, tool_payload),
        "reproduce": _repro_command(tool, repo_path, workdir, output_dir),
        "hints": [
            f"Review tool outputs under {output_dir / 'tool-outputs'}",
            "Re-run with CIHUB_VERBOSE=True to stream tool output",
        ],
    }


def _build_markdown(bundle: dict[str, Any], max_failures: int = 10) -> str:
    run = bundle.get("run", {}) if isinstance(bundle.get("run"), dict) else {}
    paths = bundle.get("paths", {}) if isinstance(bundle.get("paths"), dict) else {}
    summary = bundle.get("summary", {}) if isinstance(bundle.get("summary"), dict) else {}
    failures = bundle.get("failures", []) if isinstance(bundle.get("failures"), list) else []
    evidence_issues = bundle.get("evidence_issues", []) if isinstance(bundle.get("evidence_issues"), list) else []

    lines = [
        "# CIHub Triage",
        "",
        f"Repository: {run.get('repo') or '-'}",
        f"Branch: {run.get('branch') or '-'}",
        f"Commit: {run.get('commit_sha') or '-'}",
        f"Correlation ID: {run.get('correlation_id') or '-'}",
        f"Output Dir: {paths.get('output_dir') or '-'}",
        f"Status: {summary.get('overall_status') or '-'}",
        "",
        "## Priority Failures",
    ]

    if not failures:
        if evidence_issues:
            lines.append("No tool failures detected, but evidence issues exist (see below).")
        else:
            lines.append("No failures detected.")

    for failure in failures[:max_failures]:
        artifacts = failure.get("artifacts", []) if isinstance(failure.get("artifacts"), list) else []
        artifact_lines = [f"- {item.get('path')} ({item.get('kind')})" for item in artifacts if item.get("path")]
        reproduce = failure.get("reproduce", {}) if isinstance(failure.get("reproduce"), dict) else {}
        env = reproduce.get("env", {}) if isinstance(reproduce.get("env"), dict) else {}
        env_str = ", ".join([f"{k}={v}" for k, v in env.items()]) if env else "-"

        # Include actual error details if available
        errors = failure.get("errors", []) if isinstance(failure.get("errors"), list) else []
        error_lines = []
        if errors:
            error_lines.append("- Errors:")
            for err in errors[:5]:  # Limit to first 5 errors
                # Truncate long error messages
                err_str = str(err)[:200] + "..." if len(str(err)) > 200 else str(err)
                error_lines.append(f"  - {err_str}")
            if len(errors) > 5:
                error_lines.append(f"  - ... and {len(errors) - 5} more error(s)")

        # Use hints from failure entry if available, otherwise use defaults
        hints = failure.get("hints") or [
            f"Inspect artifacts and logs for {failure.get('tool')}",
            "Re-run locally with the reproduce command",
            "Apply deterministic fixes from tool output",
        ]
        hint_lines = [f"  - {hint}" for hint in hints]

        lines.extend(
            [
                "",
                f"### {failure.get('tool')} ({failure.get('severity')})",
                f"- Status: {failure.get('status')}",
                f"- Category: {failure.get('category')}",
                f"- Reason: {failure.get('reason')}",
                f"- Message: {failure.get('message')}",
                *error_lines,
                f"- Reproduce: {reproduce.get('command') or '-'}",
                f"- Env: {env_str}",
                "- Artifacts:",
                *(artifact_lines if artifact_lines else ["  - -"]),
                "- Hints:",
                *hint_lines,
            ]
        )

    if evidence_issues:
        lines.extend(["", "## Evidence Issues", ""])
        # Show errors first, then warnings, then info.
        order = {"error": 0, "warning": 1, "info": 2}
        sorted_issues = sorted(
            evidence_issues,
            key=lambda i: (order.get(str(i.get("severity")), 99), str(i.get("tool") or ""), str(i.get("issue") or "")),
        )
        for item in sorted_issues[:20]:
            tool = item.get("tool") or "-"
            sev = item.get("severity") or "-"
            issue = item.get("issue") or "-"
            msg = item.get("message") or "-"
            lines.append(f"- [{sev}] {tool}: {issue} — {msg}")

    return "\n".join(lines).strip() + "\n"


def _sort_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    category_index = {name: idx for idx, name in enumerate(CATEGORY_ORDER)}

    def _sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        severity = str(item.get("severity") or "medium")
        category = str(item.get("category") or "cihub")
        severity_rank = SEVERITY_ORDER.get(severity, 99)
        category_rank = category_index.get(category, len(CATEGORY_ORDER))
        return (severity_rank, category_rank, str(item.get("tool") or ""))

    return sorted(failures, key=_sort_key)


# ---------------------------------------------------------------------------
# Public API: Bundle generation and aggregation
# ---------------------------------------------------------------------------


def aggregate_triage_bundles(
    bundles: list[TriageBundle],
) -> MultiTriageResult:
    """Aggregate multiple triage bundles into a multi-repo summary.

    Used for orchestrator runs that produce N report.json files.
    """
    timestamp = _timestamp()
    repos: list[dict[str, Any]] = []
    failures_by_tool: dict[str, list[str]] = {}
    failures_by_repo: dict[str, list[str]] = {}

    passed_count = 0
    failed_count = 0

    for bundle in bundles:
        triage = bundle.triage
        run_info = triage.get("run", {}) or {}
        summary = triage.get("summary", {}) or {}
        failures = triage.get("failures", []) or []

        repo_name = run_info.get("repo", "unknown")
        overall_status = summary.get("overall_status", "unknown")

        if overall_status == "passed":
            passed_count += 1
        else:
            failed_count += 1

        # Track which tools failed for this repo
        repo_failed_tools: list[str] = []
        for failure in failures:
            tool = failure.get("tool", "unknown")
            repo_failed_tools.append(tool)

            # Add to failures_by_tool
            if tool not in failures_by_tool:
                failures_by_tool[tool] = []
            if repo_name not in failures_by_tool[tool]:
                failures_by_tool[tool].append(repo_name)

        if repo_failed_tools:
            failures_by_repo[repo_name] = repo_failed_tools

        repos.append(
            {
                "repo": repo_name,
                "status": overall_status,
                "failure_count": summary.get("failure_count", 0),
                "failed_tools": repo_failed_tools,
                "branch": run_info.get("branch", ""),
                "commit": run_info.get("commit_sha", "")[:8] if run_info.get("commit_sha") else "",
            }
        )

    # Build summary markdown
    md_lines = [
        "# Multi-Repo Triage Summary",
        "",
        f"**Total Repos**: {len(bundles)}",
        f"**Passed**: {passed_count}",
        f"**Failed**: {failed_count}",
        "",
        "## Failures by Tool",
        "",
    ]

    if failures_by_tool:
        for tool, failed_repos in sorted(failures_by_tool.items(), key=lambda x: -len(x[1])):
            repos_preview = ", ".join(failed_repos[:5])
            ellipsis = "..." if len(failed_repos) > 5 else ""
            md_lines.append(f"- **{tool}**: {len(failed_repos)} repos ({repos_preview}{ellipsis})")
    else:
        md_lines.append("No failures detected.")

    md_lines.extend(
        [
            "",
            "## Repo Status",
            "",
            "| Repo | Status | Failed Tools |",
            "|------|--------|--------------|",
        ]
    )

    for repo in repos:
        status_text = "passed" if repo["status"] == "passed" else "failed"
        failed_tools = ", ".join(repo["failed_tools"][:3]) or "-"
        if len(repo["failed_tools"]) > 3:
            failed_tools += "..."
        md_lines.append(f"| {repo['repo']} | {status_text} | {failed_tools} |")

    return MultiTriageResult(
        schema_version=MULTI_TRIAGE_SCHEMA_VERSION,
        generated_at=timestamp,
        repo_count=len(bundles),
        passed_count=passed_count,
        failed_count=failed_count,
        repos=repos,
        failures_by_tool=failures_by_tool,
        failures_by_repo=failures_by_repo,
        summary_markdown="\n".join(md_lines),
    )


def generate_triage_bundle(
    output_dir: Path,
    report_path: Path | None = None,
    summary_path: Path | None = None,
    meta: dict[str, Any] | None = None,
) -> TriageBundle:
    """Generate a triage bundle from CI output.

    Args:
        output_dir: Directory containing CI output (report.json, tool-outputs/, etc.)
        report_path: Optional path to report.json (defaults to output_dir/report.json)
        summary_path: Optional path to summary.md (defaults to output_dir/summary.md)
        meta: Optional metadata dict for missing report fallback

    Returns:
        TriageBundle with triage, priority, markdown, and history_entry
    """
    output_dir = output_dir.resolve()
    report_path = report_path or output_dir / "report.json"
    summary_path = summary_path or output_dir / "summary.md"
    meta = meta or {}

    report = _load_json(report_path)
    tool_outputs = _load_tool_outputs(output_dir / "tool-outputs")
    failures: list[dict[str, Any]] = []
    notes: list[str] = []

    repo_path = output_dir.parent
    workdir = None
    if report:
        environment = report.get("environment", {}) if isinstance(report.get("environment"), dict) else {}
        workdir = environment.get("workdir")

        tools_configured = (
            report.get("tools_configured", {}) if isinstance(report.get("tools_configured"), dict) else {}
        )
        tools_ran = report.get("tools_ran", {}) if isinstance(report.get("tools_ran"), dict) else {}
        tools_success = report.get("tools_success", {}) if isinstance(report.get("tools_success"), dict) else {}
        tools_require_run = (
            report.get("tools_require_run", {}) if isinstance(report.get("tools_require_run"), dict) else {}
        )

        for tool, enabled in tools_configured.items():
            if not enabled:
                continue
            ran = bool(tools_ran.get(tool, False))
            success = bool(tools_success.get(tool, False))
            if success:
                continue
            if ran:
                status = "failed"
                reason = "tool_failed"
                message = f"Tool '{tool}' failed"
            else:
                require_run = bool(tools_require_run.get(tool, False))
                if require_run:
                    status = "required_not_run"
                    reason = "tool_required_not_run"
                    message = f"Tool '{tool}' was required but did not run"
                else:
                    status = "skipped"
                    reason = "tool_skipped"
                    message = f"Tool '{tool}' skipped"
            payload = tool_outputs.get(tool, {})
            failures.append(
                _failure_entry(
                    tool=tool,
                    status=status,
                    reason=reason,
                    message=message,
                    output_dir=output_dir,
                    tool_payload=payload,
                    repo_path=repo_path,
                    workdir=workdir,
                )
            )
    else:
        reason = "missing_report" if not report_path.exists() else "invalid_report"
        message = "report.json not found" if reason == "missing_report" else "report.json invalid"
        failures.append(
            {
                "id": f"cihub:{reason}",
                "category": "cihub",
                "severity": "blocker",
                "tool": "cihub",
                "status": "missing_report",
                "reason": reason,
                "message": message,
                "artifacts": [],
                "reproduce": {
                    "command": f"cihub ci --repo {repo_path} --output-dir {output_dir}",
                    "cwd": str(repo_path),
                },
                "hints": [
                    "Confirm the workflow completed and produced report.json",
                    "Re-run cihub ci to regenerate report outputs",
                ],
            }
        )
        if tool_outputs:
            notes.append(f"Found tool outputs in {output_dir / 'tool-outputs'} without report.json")

    if meta.get("error"):
        notes.append(f"error: {meta['error']}")

    # Build tool evidence for artifact-first explainability
    tool_evidence: list[dict[str, Any]] = []
    evidence_issues: list[dict[str, Any]] = []
    if report:
        evidence_list = build_tool_evidence(report, output_dir)
        tool_evidence = [e.to_dict() for e in evidence_list]
        evidence_issues = validate_artifact_evidence(report, output_dir)

    priority = _sort_failures(failures)
    evidence_error_count = len([i for i in evidence_issues if i.get("severity") == "error"])
    evidence_warning_count = len([i for i in evidence_issues if i.get("severity") == "warning"])
    evidence_info_count = len([i for i in evidence_issues if i.get("severity") == "info"])

    base_failure_count = len(
        [f for f in failures if f.get("status") in {"failed", "missing_report", "required_not_run"}]
    )
    failure_count = base_failure_count + evidence_error_count
    skipped_count = len([f for f in failures if f.get("status") == "skipped"])
    required_not_run_count = len([e for e in tool_evidence if e.get("status") == "required_not_run"])

    run = {
        "correlation_id": report.get("hub_correlation_id") if report else meta.get("correlation_id"),
        "repo": report.get("repository") if report else meta.get("repo"),
        "commit_sha": report.get("commit") if report else meta.get("commit_sha"),
        "branch": report.get("branch") if report else meta.get("branch"),
        "run_id": report.get("run_id") if report else meta.get("run_id"),
        "run_number": report.get("run_number") if report else meta.get("run_number"),
        "workflow_ref": (report.get("metadata", {}) or {}).get("workflow_ref") if report else meta.get("workflow_ref"),
        "command": meta.get("command", "cihub triage"),
        "args": meta.get("args", []),
    }

    tool_counts: dict[str, int] = {
        "configured": len(report.get("tools_configured", {})) if report else 0,
        "ran": len([t for t in (report.get("tools_ran", {}) if report else {}).values() if t]),
        "passed": len([e for e in tool_evidence if e.get("status") == "passed"]),
        "failed": len([e for e in tool_evidence if e.get("status") == "failed"]),
    }

    summary: dict[str, Any] = {
        "overall_status": (
            "failed" if failures or required_not_run_count > 0 or evidence_error_count > 0 else "passed"
        ),
        "failure_count": failure_count,
        "warning_count": evidence_warning_count,
        "info_count": evidence_info_count,
        "evidence_error_count": evidence_error_count,
        "skipped_count": skipped_count,
        "required_not_run_count": required_not_run_count,
        "tool_counts": tool_counts,
    }

    # Extract test counts for trend analysis (Issue 16)
    results = report.get("results", {}) if report else {}
    tests_passed = results.get("tests_passed", 0) or 0
    tests_failed = results.get("tests_failed", 0) or 0
    tests_skipped = results.get("tests_skipped", 0) or 0
    tests_total = tests_passed + tests_failed + tests_skipped

    # Detect test count regressions (Issue 16)
    history_path = output_dir / "history.jsonl"
    regression_warnings = detect_test_count_regression(history_path, tests_total)

    triage = {
        "schema_version": TRIAGE_SCHEMA_VERSION,
        "generated_at": _timestamp(),
        "run": run,
        "paths": {
            "output_dir": str(output_dir),
            "report_path": str(report_path) if report_path.exists() else "",
            "summary_path": str(summary_path) if summary_path.exists() else "",
        },
        "summary": summary,
        "tool_evidence": tool_evidence,
        "evidence_issues": evidence_issues,
        "failures": priority,
        "warnings": regression_warnings,  # Include test count drop warnings
        "notes": notes,
    }

    priority_payload = {
        "schema_version": PRIORITY_SCHEMA_VERSION,
        "failures": priority,
    }

    # Additional metrics for history entry
    coverage = results.get("coverage", 0) or 0
    mutation_score = results.get("mutation_score", 0) or 0

    # Extract gate failures for historical tracking
    gate_failures = [
        f.get("tool", f.get("id", "unknown"))
        for f in failures
        if f.get("category") in {"gate", "test", "security", "lint"}
        and f.get("status") in {"failed", "required_not_run"}
    ]
    gate_passed_count = tool_counts["passed"]
    gate_failed_count = len(gate_failures)

    history_entry = {
        "timestamp": triage["generated_at"],
        "correlation_id": run.get("correlation_id") or "",
        "output_dir": str(output_dir),
        "overall_status": summary["overall_status"],
        "failure_count": summary["failure_count"],
        # Test counts for trend analysis (Issue 16)
        "tests_total": tests_total,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "tests_skipped": tests_skipped,
        "coverage": coverage,
        "mutation_score": mutation_score,
        # Tool counts for drift detection
        "tools_configured": tool_counts["configured"],
        "tools_ran": tool_counts["ran"],
        "tools_passed": tool_counts["passed"],
        "tools_failed": tool_counts["failed"],
        # Gate status for historical tracking
        "gate_failures": gate_failures,
        "gate_passed_count": gate_passed_count,
        "gate_failed_count": gate_failed_count,
        # AI loop iteration tracking (None if not from ai-loop)
        "iteration": meta.get("iteration") if meta else None,
        "max_iterations": meta.get("max_iterations") if meta else None,
    }

    markdown = _build_markdown(triage, max_failures=10)

    return TriageBundle(
        triage=triage,
        priority=priority_payload,
        markdown=markdown,
        history_entry=history_entry,
    )


def write_triage_bundle(bundle: TriageBundle, output_dir: Path) -> dict[str, Path]:
    """Write a triage bundle to disk.

    Args:
        bundle: The TriageBundle to write
        output_dir: Directory to write files to

    Returns:
        Dict mapping file type to path (triage, priority, markdown, history)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    triage_path = output_dir / "triage.json"
    priority_path = output_dir / "priority.json"
    md_path = output_dir / "triage.md"
    history_path = output_dir / "history.jsonl"

    triage_path.write_text(json.dumps(bundle.triage, indent=2), encoding="utf-8")
    priority_path.write_text(json.dumps(bundle.priority, indent=2), encoding="utf-8")
    md_path.write_text(bundle.markdown, encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(bundle.history_entry) + "\n")

    return {
        "triage": triage_path,
        "priority": priority_path,
        "markdown": md_path,
        "history": history_path,
    }
