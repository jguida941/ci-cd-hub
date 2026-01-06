"""Tool evidence building and validation functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import CATEGORY_BY_TOOL, SEVERITY_BY_CATEGORY, ToolEvidence, ToolStatus


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON from a file, returning None if invalid."""
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _load_tool_outputs(tool_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all tool output JSON files from a directory."""
    outputs: dict[str, dict[str, Any]] = {}
    if not tool_dir.exists():
        return outputs
    for path in tool_dir.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        tool = str(data.get("tool") or path.stem)
        outputs[tool] = data
    return outputs


def _format_list(values: list[str]) -> str:
    """Format a list as comma-separated string."""
    return ", ".join(values) if values else "-"


def _normalize_category(tool: str) -> str:
    """Get category for a tool."""
    return CATEGORY_BY_TOOL.get(tool, "cihub")


def _severity_for(category: str) -> str:
    """Get severity for a category."""
    return SEVERITY_BY_CATEGORY.get(category, "medium")


def _tool_env_name(tool: str) -> str:
    """Get environment variable name for a tool toggle."""
    return f"CIHUB_RUN_{tool.replace('-', '_').upper()}"


def _tool_artifacts(output_dir: Path, tool: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    """Collect artifact paths for a tool."""
    artifacts: list[dict[str, str]] = []
    tool_outputs = output_dir / "tool-outputs"
    seen: set[str] = set()

    def _add(path: Path | str, kind: str) -> None:
        path_str = str(path)
        if not path_str or path_str in seen:
            return
        seen.add(path_str)
        artifacts.append({"path": path_str, "kind": kind})

    json_path = tool_outputs / f"{tool}.json"
    if json_path.exists():
        _add(json_path, "tool_result")

    stdout_path = tool_outputs / f"{tool}.stdout.log"
    stderr_path = tool_outputs / f"{tool}.stderr.log"
    if stdout_path.exists():
        _add(stdout_path, "stdout")
    if stderr_path.exists():
        _add(stderr_path, "stderr")

    for key, value in (payload.get("artifacts") or {}).items():
        if not value:
            continue
        _add(value, key)

    return artifacts


def _get_nested(data: dict, path: str) -> Any:
    """Get nested value using dot notation (e.g., 'results.coverage')."""
    keys = path.split(".")
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _get_tool_metrics(report: dict[str, Any], tool: str, language: str) -> dict[str, Any]:
    """Get relevant metrics for a tool from the report."""
    from cihub.tools.registry import JAVA_TOOL_METRICS, PYTHON_TOOL_METRICS

    metrics_map = PYTHON_TOOL_METRICS if language == "python" else JAVA_TOOL_METRICS
    metric_paths = metrics_map.get(tool, [])

    metrics: dict[str, Any] = {}
    for path in metric_paths:
        value = _get_nested(report, path)
        if value is not None:
            # Use the last part of the path as the key
            key = path.split(".")[-1]
            metrics[key] = value

    return metrics


def _check_tool_has_artifacts(output_dir: Path, tool: str) -> bool:
    """Check if a tool has any artifact files."""
    tool_outputs = output_dir / "tool-outputs"
    if not tool_outputs.exists():
        return False

    # Check for common artifact patterns
    patterns = [
        f"{tool}.json",
        f"{tool}.stdout.log",
        f"{tool}-report.*",
        f"*{tool}*",
    ]

    for pattern in patterns:
        if list(tool_outputs.glob(pattern)):
            return True

    return False


def build_tool_evidence(
    report: dict[str, Any],
    output_dir: Path | None = None,
) -> list[ToolEvidence]:
    """Build evidence for all tools in a report.

    This provides per-tool explainability for artifact-first triage.
    Each tool gets a status and human-readable explanation of why.
    """
    # Detect language
    if "java_version" in report:
        language = "java"
    elif "python_version" in report:
        language = "python"
    else:
        language = "python"  # Default

    tools_configured = report.get("tools_configured", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}
    tools_require_run = report.get("tools_require_run", {}) or {}

    # Get all tools (union of all dicts)
    all_tools = set(tools_configured.keys()) | set(tools_ran.keys()) | set(tools_success.keys())

    evidence_list: list[ToolEvidence] = []

    for tool in sorted(all_tools):
        configured = bool(tools_configured.get(tool, False))
        ran = bool(tools_ran.get(tool, False))
        require_run = bool(tools_require_run.get(tool, False))
        success = tools_success.get(tool) if ran else None

        # Determine status and explanation
        if not configured:
            status = ToolStatus.NOT_CONFIGURED
            explanation = f"Tool '{tool}' was not enabled in configuration"
        elif configured and not ran and require_run:
            status = ToolStatus.REQUIRED_NOT_RUN
            explanation = f"Tool '{tool}' was required (require_run_or_fail=true) but did not run - HARD FAIL"
        elif configured and not ran:
            status = ToolStatus.SKIPPED
            explanation = f"Tool '{tool}' was configured but skipped (optional, no require_run)"
        elif ran and success:
            status = ToolStatus.PASSED
            explanation = f"Tool '{tool}' ran successfully and passed all thresholds"
        else:
            status = ToolStatus.FAILED
            explanation = f"Tool '{tool}' ran but failed (threshold violation or execution error)"

        # Get metrics and artifact info
        metrics = _get_tool_metrics(report, tool, language)
        has_artifacts = _check_tool_has_artifacts(output_dir, tool) if output_dir else False

        evidence_list.append(
            ToolEvidence(
                tool=tool,
                configured=configured,
                ran=ran,
                require_run=require_run,
                success=success,
                status=status,
                explanation=explanation,
                metrics=metrics,
                has_artifacts=has_artifacts,
            )
        )

    return evidence_list


def validate_artifact_evidence(
    report: dict[str, Any],
    output_dir: Path,
    run_schema_validation: bool = True,
) -> list[dict[str, Any]]:
    """Validate that tools marked as ran have actual evidence (metrics or artifacts).

    Also optionally runs JSON schema validation and report consistency checks.

    Args:
        report: Report dict to validate.
        output_dir: Directory containing tool outputs.
        run_schema_validation: If True, run JSON schema validation on the report.

    Returns a list of validation issues found.
    """
    from cihub.services.report_validator import (
        ValidationRules,
        validate_against_schema,
        validate_report,
    )

    issues: list[dict[str, Any]] = []

    # 1. JSON Schema validation (detects schema drift)
    if run_schema_validation:
        schema_errors = validate_against_schema(report)
        for error in schema_errors:
            issues.append(
                {
                    "tool": "schema",
                    "severity": "error",
                    "issue": "schema_violation",
                    "message": error,
                }
            )

    # 2. Report consistency validation (strict mode)
    try:
        thresholds = report.get("thresholds", {}) if isinstance(report.get("thresholds"), dict) else {}
        coverage_min = thresholds.get("coverage_min")
        if isinstance(coverage_min, (int, float)):
            coverage_min_value = int(coverage_min)
        elif isinstance(coverage_min, str) and coverage_min.strip().isdigit():
            coverage_min_value = int(coverage_min.strip())
        else:
            # Avoid false errors: if the report doesn't include an effective threshold,
            # fall back to 0 so we don't invent a policy.
            coverage_min_value = 0
        validation_result = validate_report(
            report,
            ValidationRules(
                # This is an evidence/consistency pass for triage: validate invariants and
                # structural consistency without re-enforcing gate policy (coverage, tests,
                # require_run_or_fail, etc). Gate failures are already surfaced via
                # tools_success/tools_require_run and tool_evidence.
                expect_clean=True,
                strict=False,  # strict changes success semantics only; we collect warnings separately
                validate_schema=False,
                consistency_only=True,
                coverage_min=coverage_min_value,
            ),
        )
        for error in validation_result.errors:
            issues.append(
                {
                    "tool": "validator",
                    "severity": "error",
                    "issue": "validation_error",
                    "message": error,
                }
            )
        for warning in validation_result.warnings:
            issues.append(
                {
                    "tool": "validator",
                    "severity": "warning",
                    "issue": "validation_warning",
                    "message": warning,
                }
            )
    except Exception as e:  # noqa: BLE001 - surface validation errors
        issues.append(
            {
                "tool": "validator",
                "severity": "error",
                "issue": "validation_failed",
                "message": f"Report validation failed: {e}",
            }
        )

    # 3. Per-tool evidence checks
    language = "java" if "java_version" in report else "python"
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}

    for tool, ran in tools_ran.items():
        if not ran:
            continue

        metrics = _get_tool_metrics(report, tool, language)
        has_artifacts = _check_tool_has_artifacts(output_dir, tool)
        success = tools_success.get(tool, False)

        # Tools that ran successfully should have either metrics or artifacts
        if success and not metrics and not has_artifacts:
            issues.append(
                {
                    "tool": tool,
                    "severity": "warning",
                    "issue": "no_evidence",
                    "message": f"Tool '{tool}' marked as ran+success but has no metrics or artifacts",
                }
            )

        # Tools that ran but failed might not have metrics, but should have artifacts
        if not success and not has_artifacts:
            issues.append(
                {
                    "tool": tool,
                    "severity": "info",
                    "issue": "no_failure_artifacts",
                    "message": f"Tool '{tool}' failed but has no artifact files for debugging",
                }
            )

    return issues
