"""Tool verification module for triage command.

This module provides utilities for verifying that configured CI tools
actually ran and produced expected artifacts/metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.services.report_validator import ValidationRules, validate_report


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
    result: dict[str, Any] = {
        "verified": True,
        "drift": [],  # Tools configured but didn't run
        "no_proof": [],  # Tools ran but no metrics/artifacts
        "failures": [],  # Tools that failed
        "skipped": [],  # Tools not configured
        "passed": [],  # Tools ran, have proof, and succeeded
        "summary": "",
        "tool_matrix": [],  # Full matrix for display
    }

    if not report_path.exists():
        result["verified"] = False
        result["summary"] = f"Report not found: {report_path}"
        return result

    try:
        with report_path.open(encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        result["verified"] = False
        result["summary"] = f"Invalid JSON in report: {e}"
        return result

    tools_configured = report.get("tools_configured", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}

    # Run validation to get warnings about proof
    rules = ValidationRules(consistency_only=True)
    validation = validate_report(report, rules, reports_dir=reports_dir)

    # Process each tool
    all_tools = set(tools_configured.keys()) | set(tools_ran.keys())
    for tool in sorted(all_tools):
        configured = tools_configured.get(tool, False)
        ran = tools_ran.get(tool, False)
        success = tools_success.get(tool, False)

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
            tool_entry["status"] = "drift"
            tool_entry["issue"] = "Configured but did not run"
            result["drift"].append({"tool": tool, "message": "Configured but did not run"})
            result["verified"] = False
        elif ran and success:
            tool_entry["status"] = "passed"
            result["passed"].append(tool)
        elif ran and not success:
            tool_entry["status"] = "failed"
            tool_entry["issue"] = "Ran but failed"
            result["failures"].append({"tool": tool, "message": "Ran but failed"})
            result["verified"] = False

        result["tool_matrix"].append(tool_entry)

    # Check validation warnings for "no proof" issues
    for warning in validation.warnings:
        if "no proof found" in warning.lower():
            # Extract tool name from warning
            for tool in all_tools:
                if f"'{tool}'" in warning:
                    result["no_proof"].append({"tool": tool, "message": warning})
                    result["verified"] = False
                    # Update matrix entry
                    for entry in result["tool_matrix"]:
                        if entry["tool"] == tool and entry["status"] == "passed":
                            entry["status"] = "no_proof"
                            entry["issue"] = "Ran but no metrics/artifacts found"
                    break

    # Also check for empty artifact warnings
    for warning in validation.warnings:
        if "empty output files" in warning.lower():
            for tool in all_tools:
                if f"'{tool}'" in warning:
                    if not any(p["tool"] == tool for p in result["no_proof"]):
                        result["no_proof"].append({"tool": tool, "message": warning})
                        result["verified"] = False
                    break

    # Generate summary
    total = len(result["tool_matrix"])
    passed = len(result["passed"])
    drift_count = len(result["drift"])
    no_proof_count = len(result["no_proof"])
    fail_count = len(result["failures"])
    skip_count = len(result["skipped"])

    if result["verified"]:
        result["summary"] = f"All {passed} configured tools verified (ran with proof)"
    else:
        issues = []
        if drift_count:
            issues.append(f"{drift_count} configured but didn't run")
        if no_proof_count:
            issues.append(f"{no_proof_count} ran but no proof")
        if fail_count:
            issues.append(f"{fail_count} failed")
        result["summary"] = f"Tool verification: {', '.join(issues)}"

    result["counts"] = {
        "total": total,
        "passed": passed,
        "drift": drift_count,
        "no_proof": no_proof_count,
        "failures": fail_count,
        "skipped": skip_count,
    }

    return result


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

    # Tool matrix table
    lines.append("")
    lines.append("| Tool | Configured | Ran | Success | Status |")
    lines.append("|------|------------|-----|---------|--------|")
    for entry in verify_result.get("tool_matrix", []):
        configured = "yes" if entry["configured"] else "no"
        ran = "yes" if entry["ran"] else "no"
        success = "yes" if entry["success"] else "no"
        status = entry["status"].upper()
        lines.append(f"| {entry['tool']} | {configured} | {ran} | {success} | {status} |")

    lines.append("")
    counts = verify_result.get("counts", {})
    lines.append(f"Total: {counts.get('total', 0)} tools")
    lines.append(f"  Passed: {counts.get('passed', 0)}")
    lines.append(f"  Drift (configured but didn't run): {counts.get('drift', 0)}")
    lines.append(f"  No proof (ran but no metrics/artifacts): {counts.get('no_proof', 0)}")
    lines.append(f"  Failed: {counts.get('failures', 0)}")
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
    # Backward compatibility
    "_format_verify_tools_output",
    "_verify_tools_from_report",
]
