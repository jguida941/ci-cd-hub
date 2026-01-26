"""Tool verification module for triage command.

This module provides utilities for verifying that configured CI tools
actually ran and produced expected artifacts/metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.services.report_validator import ValidationRules, validate_report


def _verify_tools_dict(
    report: dict[str, Any],
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "verified": True,
        "drift": [],  # Tools configured but didn't run
        "no_proof": [],  # Tools ran but no metrics/artifacts
        "failures": [],  # Tools that failed
        "unknown": [],  # Tools ran but did not report tools_success
        "optional": [],  # Tools configured but not required to run
        "skipped": [],  # Tools not configured
        "passed": [],  # Tools ran, have proof, and succeeded
        "summary": "",
        "tool_matrix": [],  # Full matrix for display
    }

    tools_configured = report.get("tools_configured", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}
    tools_require_run = report.get("tools_require_run", {}) or {}

    def _requires_run(tool_name: str) -> bool:
        if tool_name in tools_require_run:
            return bool(tools_require_run.get(tool_name, False))
        return True

    rules = ValidationRules(consistency_only=True)
    validation = validate_report(report, rules, reports_dir=reports_dir)

    all_tools = set(tools_configured.keys()) | set(tools_ran.keys())
    for tool in sorted(all_tools):
        configured = tools_configured.get(tool, False)
        ran = tools_ran.get(tool, False)
        success = tools_success.get(tool) if tool in tools_success else None

        tool_entry = {
            "tool": tool,
            "configured": configured,
            "ran": ran,
            "success": success,
            "status": "unknown",
            "issue": None,
        }

        if not configured:
            tool_entry["status"] = "skipped"
            result["skipped"].append(tool)
        elif configured and not ran:
            if _requires_run(tool):
                tool_entry["status"] = "drift"
                tool_entry["issue"] = "Configured but did not run"
                result["drift"].append({"tool": tool, "message": "Configured but did not run"})
                result["verified"] = False
            else:
                tool_entry["status"] = "optional"
                tool_entry["issue"] = "Configured but optional; did not run"
                result["optional"].append({"tool": tool, "message": "Configured but optional; did not run"})
        elif ran and success is None:
            tool_entry["status"] = "unknown"
            tool_entry["issue"] = "Ran but tools_success missing"
            result["unknown"].append({"tool": tool, "message": "Ran but tools_success missing"})
            result["verified"] = False
        elif ran and success:
            tool_entry["status"] = "passed"
            result["passed"].append(tool)
        elif ran and success is False:
            tool_entry["status"] = "failed"
            tool_entry["issue"] = "Ran but failed"
            result["failures"].append({"tool": tool, "message": "Ran but failed"})
            result["verified"] = False

        result["tool_matrix"].append(tool_entry)

    for warning in validation.warnings:
        warning_lower = warning.lower()
        if "no proof found" in warning_lower or "no report evidence" in warning_lower:
            for tool in all_tools:
                if f"'{tool}'" in warning:
                    result["no_proof"].append({"tool": tool, "message": warning})
                    result["verified"] = False
                    for entry in result["tool_matrix"]:
                        if entry["tool"] == tool and entry["status"] == "passed":
                            entry["status"] = "no_proof"
                            entry["issue"] = "Ran but no metrics/artifacts found"
                    break

    for warning in validation.warnings:
        if "empty output files" in warning.lower():
            for tool in all_tools:
                if f"'{tool}'" in warning:
                    if not any(p["tool"] == tool for p in result["no_proof"]):
                        result["no_proof"].append({"tool": tool, "message": warning})
                        result["verified"] = False
                    break

    total = len(result["tool_matrix"])
    drift_count = len(result["drift"])
    no_proof_count = len(result["no_proof"])
    failures_count = len(result["failures"])
    unknown_count = len(result["unknown"])
    passed = len(result["passed"])
    optional_count = len(result["optional"])
    skipped_count = len(result["skipped"])

    if total == 0:
        result["summary"] = "No tools found in report"
    elif drift_count == 0 and no_proof_count == 0 and failures_count == 0 and unknown_count == 0:
        result["summary"] = f"All {passed} configured tools verified (ran with proof)"
    else:
        issues = []
        if drift_count:
            issues.append(f"{drift_count} configured but did not run")
        if no_proof_count:
            issues.append(f"{no_proof_count} ran but no proof")
        if unknown_count:
            issues.append(f"{unknown_count} ran but tools_success missing")
        if failures_count:
            issues.append(f"{failures_count} failed")
        result["summary"] = f"Issues found: {', '.join(issues)}"

    result["verified"] = (
        result["verified"]
        and failures_count == 0
        and drift_count == 0
        and no_proof_count == 0
        and unknown_count == 0
    )
    result["counts"] = {
        "total": total,
        "passed": passed,
        "drift": drift_count,
        "no_proof": no_proof_count,
        "failures": failures_count,
        "unknown": unknown_count,
        "optional": optional_count,
        "skipped": skipped_count,
    }
    return result


def _merge_target_result(
    base: dict[str, Any],
    target_result: dict[str, Any],
    slug: str,
    language: str | None = None,
    subdir: str | None = None,
) -> None:
    target_result["slug"] = slug
    target_result["language"] = language
    target_result["subdir"] = subdir
    base["targets"].append(target_result)
    base["verified"] = base["verified"] and target_result.get("verified", False)

    for key in ("drift", "no_proof", "failures", "unknown", "optional", "skipped"):
        for item in target_result.get(key, []):
            if isinstance(item, dict):
                merged = dict(item)
            else:
                merged = {"tool": str(item), "message": ""}
            merged["target"] = slug
            msg = merged.get("message", "")
            merged["message"] = f"[{slug}] {msg}".strip()
            base[key].append(merged)

    base["passed"].extend([f"{slug}:{tool}" for tool in target_result.get("passed", [])])

    counts = target_result.get("counts", {})
    for key in base["counts"]:
        base["counts"][key] += int(counts.get(key, 0))


def _finalize_summary(base: dict[str, Any]) -> None:
    total = base["counts"]["total"]
    if total == 0:
        base["summary"] = "No tools found in report"
        return
    if base["verified"]:
        base["summary"] = f"All {base['counts']['passed']} configured tools verified across {len(base['targets'])} targets"
        return
    issues = []
    if base["counts"]["drift"]:
        issues.append(f"{base['counts']['drift']} configured but didn't run")
    if base["counts"]["no_proof"]:
        issues.append(f"{base['counts']['no_proof']} ran but no proof")
    if base["counts"]["unknown"]:
        issues.append(f"{base['counts']['unknown']} ran but tools_success missing")
    if base["counts"]["failures"]:
        issues.append(f"{base['counts']['failures']} failed")
    base["summary"] = f"Tool verification: {', '.join(issues)}"


def verify_tools_from_report(
    report_path: Path,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify that configured tools actually ran and have proof.

    Uses report_validator to check:
    - Tools configured but didn't run (DRIFT)
    - Tools that ran but have no proof (metrics/artifacts)
    - Tool failures vs success claims

    Args:
        report_path: Path to report.json
        reports_dir: Optional directory containing tool artifacts

    Returns:
        Dict with verification results: drift, no_proof, failures, summary
    """
    base: dict[str, Any] = {
        "verified": True,
        "drift": [],
        "no_proof": [],
        "failures": [],
        "unknown": [],
        "optional": [],
        "skipped": [],
        "passed": [],
        "summary": "",
        "tool_matrix": [],
        "targets": [],
        "counts": {
            "total": 0,
            "passed": 0,
            "drift": 0,
            "no_proof": 0,
            "failures": 0,
            "unknown": 0,
            "optional": 0,
            "skipped": 0,
        },
    }

    if not report_path.exists():
        base["verified"] = False
        base["summary"] = f"Report not found: {report_path}"
        return base

    try:
        with report_path.open(encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        base["verified"] = False
        base["summary"] = f"Invalid JSON in report: {e}"
        return base

    targets = report.get("targets")
    if isinstance(targets, list) and targets:
        for entry in targets:
            if not isinstance(entry, dict):
                base["verified"] = False
                base["failures"].append({"tool": "report", "message": "Invalid targets entry"})
                continue
            slug = entry.get("slug") or entry.get("subdir") or "target"
            target_report = entry.get("report")
            if not isinstance(target_report, dict):
                base["verified"] = False
                base["failures"].append({"tool": "report", "message": f"[{slug}] missing target report"})
                continue
            target_reports_dir = reports_dir
            if reports_dir and entry.get("slug"):
                target_reports_dir = reports_dir / "targets" / str(entry.get("slug"))
            target_result = _verify_tools_dict(target_report, target_reports_dir)
            _merge_target_result(
                base,
                target_result,
                slug=slug,
                language=entry.get("language"),
                subdir=entry.get("subdir"),
            )

        _finalize_summary(base)
        return base

    return _verify_tools_dict(report, reports_dir)


def verify_tools_from_reports(report_paths: list[Path], reports_dir: Path | None = None) -> dict[str, Any]:
    """Verify tools across multiple report.json files."""
    base: dict[str, Any] = {
        "verified": True,
        "drift": [],
        "no_proof": [],
        "failures": [],
        "unknown": [],
        "optional": [],
        "skipped": [],
        "passed": [],
        "summary": "",
        "tool_matrix": [],
        "targets": [],
        "counts": {
            "total": 0,
            "passed": 0,
            "drift": 0,
            "no_proof": 0,
            "failures": 0,
            "unknown": 0,
            "optional": 0,
            "skipped": 0,
        },
    }

    for report_path in report_paths:
        if not report_path.exists():
            continue
        try:
            with report_path.open(encoding="utf-8") as f:
                report = json.load(f)
        except json.JSONDecodeError:
            base["verified"] = False
            base["failures"].append({"tool": "report", "message": f"Invalid JSON in {report_path}"})
            continue

        environment = report.get("environment", {}) if isinstance(report.get("environment"), dict) else {}
        slug = report_path.parent.name
        target_reports_dir = report_path.parent
        target_result = _verify_tools_dict(report, target_reports_dir)
        _merge_target_result(
            base,
            target_result,
            slug=slug,
            language=environment.get("language"),
            subdir=environment.get("workdir"),
        )

    _finalize_summary(base)
    return base


def format_verify_tools_output(verify_result: dict[str, Any]) -> list[str]:
    """Format tool verification for human-readable output.

    Args:
        verify_result: Result from verify_tools_from_report()

    Returns:
        List of formatted output lines
    """
    lines = [
        "Tool Verification Report",
        "=" * 50,
    ]

    def _append_matrix(matrix: list[dict[str, Any]]) -> None:
        lines.append("")
        lines.append("| Tool | Configured | Ran | Success | Status |")
        lines.append("|------|------------|-----|---------|--------|")
        for entry in matrix:
            configured = "yes" if entry["configured"] else "no"
            ran = "yes" if entry["ran"] else "no"
            if entry["success"] is None:
                success = "?"
            else:
                success = "yes" if entry["success"] else "no"
            status = entry["status"].upper()
            lines.append(f"| {entry['tool']} | {configured} | {ran} | {success} | {status} |")

    targets = verify_result.get("targets", [])
    if targets:
        for target in targets:
            slug = target.get("slug", "target")
            subdir = target.get("subdir") or "."
            label = f"{slug} ({subdir})"
            lines.append("")
            lines.append(f"Target: {label}")
            _append_matrix(target.get("tool_matrix", []))
            counts = target.get("counts", {})
            lines.append("")
            lines.append(f"Total: {counts.get('total', 0)} tools")
            lines.append(f"  Passed: {counts.get('passed', 0)}")
            lines.append(f"  Drift (configured but didn't run): {counts.get('drift', 0)}")
            lines.append(f"  No proof (ran but no metrics/artifacts): {counts.get('no_proof', 0)}")
            lines.append(f"  Unknown (ran but tools_success missing): {counts.get('unknown', 0)}")
            lines.append(f"  Failed: {counts.get('failures', 0)}")
            lines.append(f"  Optional (configured but not required): {counts.get('optional', 0)}")
            lines.append(f"  Skipped (not configured): {counts.get('skipped', 0)}")

        lines.append("")
        lines.append(f"Summary: {verify_result.get('summary', 'Unknown')}")
        return lines

    _append_matrix(verify_result.get("tool_matrix", []))

    lines.append("")
    counts = verify_result.get("counts", {})
    lines.append(f"Total: {counts.get('total', 0)} tools")
    lines.append(f"  Passed: {counts.get('passed', 0)}")
    lines.append(f"  Drift (configured but didn't run): {counts.get('drift', 0)}")
    lines.append(f"  No proof (ran but no metrics/artifacts): {counts.get('no_proof', 0)}")
    lines.append(f"  Unknown (ran but tools_success missing): {counts.get('unknown', 0)}")
    lines.append(f"  Failed: {counts.get('failures', 0)}")
    lines.append(f"  Optional (configured but not required): {counts.get('optional', 0)}")
    lines.append(f"  Skipped (not configured): {counts.get('skipped', 0)}")

    if verify_result.get("drift"):
        lines.append("")
        lines.append("DRIFT - Tools configured but didn't run:")
        for item in verify_result["drift"]:
            lines.append(f"  - {item['tool']}: {item['message']}")

    if verify_result.get("no_proof"):
        lines.append("")
        lines.append("NO PROOF - Tools ran but no metrics/artifacts:")
        for item in verify_result["no_proof"]:
            lines.append(f"  - {item['tool']}: {item['message']}")

    if verify_result.get("unknown"):
        lines.append("")
        lines.append("UNKNOWN - Tools ran but tools_success missing:")
        for item in verify_result["unknown"]:
            lines.append(f"  - {item['tool']}: {item['message']}")

    if verify_result.get("optional"):
        lines.append("")
        lines.append("OPTIONAL - Configured but not required to run:")
        for item in verify_result["optional"]:
            lines.append(f"  - {item['tool']}: {item['message']}")

    if verify_result.get("failures"):
        lines.append("")
        lines.append("FAILED - Tools that failed:")
        for item in verify_result["failures"]:
            lines.append(f"  - {item['tool']}: {item['message']}")

    lines.append("")
    lines.append(f"Summary: {verify_result.get('summary', 'Unknown')}")

    return lines


# Backward compatibility aliases
_verify_tools_from_report = verify_tools_from_report
_format_verify_tools_output = format_verify_tools_output


__all__ = [
    "format_verify_tools_output",
    "verify_tools_from_report",
    "verify_tools_from_reports",
    # Backward compatibility
    "_format_verify_tools_output",
    "_verify_tools_from_report",
]
