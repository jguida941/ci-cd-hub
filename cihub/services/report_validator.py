"""Report validation service - validates report.json structure and content."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from cihub.services.types import ServiceResult
from cihub.tools.registry import (
    JAVA_ARTIFACTS,
    JAVA_LINT_METRICS,
    JAVA_SECURITY_METRICS,
    JAVA_SUMMARY_MAP,
    JAVA_TOOL_METRICS,
    PYTHON_ARTIFACTS,
    PYTHON_LINT_METRICS,
    PYTHON_SECURITY_METRICS,
    PYTHON_SUMMARY_MAP,
    PYTHON_TOOL_METRICS,
)

# Path to the JSON schema file (relative to package root)
_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schema" / "ci-report.v2.json"
_SCHEMA_CACHE: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    """Load and cache the JSON schema."""
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        _SCHEMA_CACHE = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE


def validate_against_schema(report: dict[str, Any]) -> list[str]:
    """Validate report against JSON schema.

    Args:
        report: Report dict to validate.

    Returns:
        List of schema validation errors (empty if valid).
    """
    schema = _load_schema()
    errors: list[str] = []

    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(report):
        # Format error path for clarity
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"Schema error at '{path}': {error.message}")

    return errors


@dataclass
class ValidationRules:
    """Rules for report validation."""

    expect_clean: bool = True  # Expect no issues (vs expect_issues for failing fixtures)
    coverage_min: int = 70
    strict: bool = False  # Fail on warnings
    validate_schema: bool = False  # Validate against JSON schema
    consistency_only: bool = False  # Validate structure/consistency only (no clean/issue expectations)


@dataclass
class ValidationResult(ServiceResult):
    """Result of report validation."""

    language: str | None = None
    schema_errors: list[str] = field(default_factory=list)
    threshold_violations: list[str] = field(default_factory=list)
    tool_warnings: list[str] = field(default_factory=list)
    debug_messages: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """Report is valid if no errors."""
        return len(self.errors) == 0


def _get_nested(data: dict, path: str) -> Any:
    """Get nested value using dot notation (e.g., 'results.coverage')."""
    keys = path.split(".")
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return None


def _parse_summary_tools(
    summary_text: str,
) -> tuple[dict[str, bool], dict[str, bool], dict[str, bool]]:
    """Parse Tools Enabled table, returning (configured, ran, success) dicts."""
    lines = summary_text.splitlines()
    in_tools = False
    configured: dict[str, bool] = {}
    ran: dict[str, bool] = {}
    success: dict[str, bool] = {}
    for line in lines:
        if line.strip() == "## Tools Enabled":
            in_tools = True
            continue
        if in_tools and line.startswith("## "):
            break
        if not in_tools:
            continue
        if "|" not in line:
            continue
        if line.strip().startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[1].lower() == "tool" or cells[2].lower() in ("enabled", "configured"):
            continue
        tool = cells[1]
        if len(cells) >= 5:
            conf_val = _parse_bool(cells[2])
            ran_val = _parse_bool(cells[3])
            success_val = _parse_bool(cells[4])
            if conf_val is not None:
                configured[tool] = conf_val
            if ran_val is not None:
                ran[tool] = ran_val
            if success_val is not None:
                success[tool] = success_val
        elif len(cells) >= 4:
            conf_val = _parse_bool(cells[2])
            ran_val = _parse_bool(cells[3])
            if conf_val is not None:
                configured[tool] = conf_val
            if ran_val is not None:
                ran[tool] = ran_val
                success[tool] = ran_val
        else:
            enabled = _parse_bool(cells[2])
            if enabled is not None:
                configured[tool] = enabled
                ran[tool] = enabled
                success[tool] = enabled
    return configured, ran, success


def _iter_existing_patterns(root: Path, patterns: Iterable[str]) -> bool:
    """Check if any files matching patterns exist in root directory."""
    for pattern in patterns:
        if list(root.glob(pattern)):
            return True
    return False


def _check_artifacts_non_empty(root: Path, patterns: Iterable[str]) -> tuple[bool, list[str]]:
    """Check if artifacts exist AND are non-empty.

    Returns:
        tuple: (all_non_empty, list of empty file paths)
    """
    empty_files: list[str] = []
    found_any = False

    for pattern in patterns:
        for path in root.glob(pattern):
            found_any = True
            if path.is_file():
                try:
                    size = path.stat().st_size
                    if size == 0:
                        empty_files.append(str(path))
                except OSError:
                    empty_files.append(f"{path} (unreadable)")

    return found_any and len(empty_files) == 0, empty_files


def _compare_summary(
    summary_configured: dict[str, bool],
    summary_ran: dict[str, bool],
    tools_configured: dict[str, Any],
    tools_ran: dict[str, Any],
    mapping: dict[str, str],
) -> list[str]:
    warnings: list[str] = []
    for label, key in mapping.items():
        if tools_configured and key in tools_configured:
            expected_conf = bool(tools_configured.get(key))
            if label in summary_configured:
                actual_conf = summary_configured[label]
                if actual_conf != expected_conf:
                    warnings.append(f"configured mismatch for {label}: summary={actual_conf} report={expected_conf}")

        if key not in tools_ran:
            warnings.append(f"report.json missing tools_ran.{key}")
            continue
        expected_ran = bool(tools_ran.get(key))
        if label not in summary_ran:
            warnings.append(f"summary missing tool row: {label}")
            continue
        actual_ran = summary_ran[label]
        if actual_ran != expected_ran:
            warnings.append(f"ran mismatch for {label}: summary={actual_ran} report={expected_ran}")
    return warnings


def _check_metrics_exist(
    report: dict[str, Any],
    tool: str,
    metric_paths: list[str],
) -> tuple[bool, list[str]]:
    """Check if expected metrics exist for a tool."""
    if not metric_paths:
        return True, [f"Debug: {tool} has no metrics, trusting step outcome"]

    found_metrics = []
    for path in metric_paths:
        value = _get_nested(report, path)
        if value is not None:
            found_metrics.append(f"{path}={value}")

    if found_metrics:
        return True, [f"Debug: {tool} verified via metrics: {', '.join(found_metrics)}"]
    return False, [f"Debug: {tool} missing expected metrics: {metric_paths}"]


def _compare_configured_vs_ran(
    tools_configured: dict[str, Any],
    tools_ran: dict[str, Any],
) -> list[str]:
    """Check for drift between configured and ran tools."""
    warnings: list[str] = []
    for tool, configured in tools_configured.items():
        if tool not in tools_ran:
            continue
        ran = tools_ran.get(tool, False)
        if configured and not ran:
            warnings.append(f"DRIFT: '{tool}' was configured=true but did NOT run (ran=false)")
    return warnings


def _validate_tool_execution(
    report: dict[str, Any],
    tools_ran: dict[str, Any],
    tools_success: dict[str, Any],
    metrics_map: dict[str, list[str]],
    artifact_map: dict[str, list[str]] | None = None,
    reports_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Validate that tools that ran have expected metrics."""
    warnings: list[str] = []
    debug: list[str] = []

    for tool, metric_paths in metrics_map.items():
        ran = bool(tools_ran.get(tool))
        succeeded = bool(tools_success.get(tool))

        if not ran:
            debug.append(f"Debug: {tool} did not run, skipping validation")
            continue

        metrics_found, metric_debug = _check_metrics_exist(report, tool, metric_paths)
        debug.extend(metric_debug)

        if metrics_found:
            if artifact_map and reports_dir and tool in artifact_map:
                patterns = artifact_map[tool]
                if patterns:
                    exists = _iter_existing_patterns(reports_dir, patterns)
                    if not exists:
                        debug.append(
                            f"Debug: {tool} has metrics but missing artifacts "
                            f"(patterns: {patterns}) - metrics take precedence"
                        )
                    else:
                        # Check artifacts are non-empty even if metrics exist
                        non_empty, empty_files = _check_artifacts_non_empty(reports_dir, patterns)
                        if empty_files:
                            warnings.append(f"tool '{tool}' has empty output files: {', '.join(empty_files)}")
            continue

        if artifact_map and reports_dir and tool in artifact_map:
            patterns = artifact_map[tool]
            if patterns and _iter_existing_patterns(reports_dir, patterns):
                # Check if artifacts are non-empty before trusting them
                non_empty, empty_files = _check_artifacts_non_empty(reports_dir, patterns)
                if non_empty:
                    debug.append(
                        f"Debug: {tool} missing metrics but non-empty artifacts found - "
                        "consider adding metrics for primary validation"
                    )
                    continue
                else:
                    # Artifacts exist but are empty - don't trust them
                    warnings.append(
                        f"tool '{tool}' has empty output files (cannot trust tools_success): {', '.join(empty_files)}"
                    )
                    # Fall through to "no proof found" if succeeded

        if succeeded:
            warnings.append(
                f"tool '{tool}' marked as ran+success but no proof found (expected metrics: {metric_paths})"
            )
        else:
            debug.append(f"Debug: {tool} ran but failed, no metrics expected")

    return warnings, debug


def validate_report(
    report: dict[str, Any],
    rules: ValidationRules | None = None,
    summary_text: str | None = None,
    reports_dir: Path | None = None,
) -> ValidationResult:
    """Validate a CI report.

    Args:
        report: Report dict to validate.
        rules: Validation rules (defaults to expect clean build).

    Returns:
        ValidationResult with errors, warnings, and debug info.
    """
    rules = rules or ValidationRules()
    errors: list[str] = []
    warnings: list[str] = []
    debug_messages: list[str] = []
    schema_errors: list[str] = []

    # 0. JSON Schema validation (if enabled)
    if rules.validate_schema:
        schema_errors = validate_against_schema(report)
        errors.extend(schema_errors)

    # Detect language
    if "java_version" in report:
        language = "java"
    elif "python_version" in report:
        language = "python"
    else:
        errors.append("Unable to determine language (missing java_version/python_version)")
        language = None

    # 1. Schema version
    schema_version = report.get("schema_version")
    if schema_version != "2.0":
        errors.append(f"schema_version is '{schema_version}', expected '2.0'")

    # 2. Test results (skip policy expectations in consistency_only mode)
    results = report.get("results", {}) or {}
    if not rules.consistency_only:
        tests_passed = results.get("tests_passed")
        tests_failed = results.get("tests_failed", 0)

        if tests_passed is None:
            errors.append("results.tests_passed is null - tests may not have run")
        elif tests_passed == 0 and rules.expect_clean:
            errors.append("tests_passed is 0 - at least some tests should pass")

        if rules.expect_clean:
            if tests_failed is None:
                errors.append("results.tests_failed is null")
            elif tests_failed > 0:
                errors.append(f"tests_failed is {tests_failed}, expected 0 for clean build")

    # 3. Coverage (skip policy expectations in consistency_only mode)
    if not rules.consistency_only:
        coverage = results.get("coverage")
        if coverage is None:
            errors.append("results.coverage is null")
        elif rules.expect_clean and coverage < rules.coverage_min:
            errors.append(f"coverage is {coverage}%, expected >= {rules.coverage_min}%")

    # 4. tools_ran
    tools_ran = report.get("tools_ran", {})
    if not isinstance(tools_ran, dict):
        errors.append("tools_ran is not an object")
        tools_ran = {}
    elif len(tools_ran) == 0:
        errors.append("tools_ran is empty - no tools recorded")

    tools_configured = report.get("tools_configured", {}) or {}
    tools_success = report.get("tools_success", {}) or {}

    summary_success: dict[str, bool] = {}
    effective_success = dict(tools_success)

    if summary_text and language:
        summary_configured, summary_ran, summary_success = _parse_summary_tools(summary_text)
        mapping = JAVA_SUMMARY_MAP if language == "java" else PYTHON_SUMMARY_MAP
        warnings.extend(_compare_summary(summary_configured, summary_ran, tools_configured, tools_ran, mapping))

        for label, key in mapping.items():
            if key not in effective_success and label in summary_success:
                effective_success[key] = summary_success[label]

    # Check configured vs ran drift
    if tools_configured:
        warnings.extend(_compare_configured_vs_ran(tools_configured, tools_ran))

    # Check tools_require_run - if tool was configured, required, but didn't run = error
    #
    # NOTE: In consistency-only mode we intentionally skip policy enforcement checks
    # (like require_run_or_fail) because they are represented elsewhere (gates/triage)
    # and would otherwise double-count failures.
    if not rules.consistency_only:
        tools_require_run = report.get("tools_require_run", {}) or {}
        for tool, configured in tools_configured.items():
            if not configured:
                continue
            ran = tools_ran.get(tool, False)
            required = tools_require_run.get(tool, False)
            if not ran and required:
                errors.append(
                    (
                        f"REQUIRED TOOL NOT RUN: '{tool}' was configured and required "
                        "(require_run_or_fail=true) but did not run"
                    )
                )

    # 5. Validate tool execution
    tool_metrics = report.get("tool_metrics", {}) or {}
    if language:
        metrics_map = PYTHON_TOOL_METRICS if language == "python" else JAVA_TOOL_METRICS
        artifact_map = PYTHON_ARTIFACTS if language == "python" else JAVA_ARTIFACTS
        tool_warnings, tool_debug = _validate_tool_execution(
            report=report,
            tools_ran=tools_ran,
            tools_success=effective_success,
            metrics_map=metrics_map,
            artifact_map=artifact_map,
            reports_dir=reports_dir,
        )
        warnings.extend(tool_warnings)
        debug_messages.extend(tool_debug)

    # 6. Clean build checks (lint/security metrics must be 0)
    if (not rules.consistency_only) and rules.expect_clean and language:
        lint_metrics = PYTHON_LINT_METRICS if language == "python" else JAVA_LINT_METRICS
        security_metrics = PYTHON_SECURITY_METRICS if language == "python" else JAVA_SECURITY_METRICS

        for metric in lint_metrics + security_metrics:
            val = tool_metrics.get(metric, 0)
            if val is None:
                val = 0
            if val > 0:
                errors.append(f"tool_metrics.{metric} is {val}, expected 0 for clean build")

    # 7. Issue detection for failing fixtures
    if (not rules.consistency_only) and (not rules.expect_clean) and language:
        lint_metrics = PYTHON_LINT_METRICS if language == "python" else JAVA_LINT_METRICS
        total_issues = sum(tool_metrics.get(m, 0) or 0 for m in lint_metrics)
        if total_issues == 0:
            errors.append("No lint issues detected - failing fixture MUST have issues")

    # 8. Threshold completeness check (Issue Section 7)
    # Warn when core thresholds are missing (will render as "-" in summary)
    thresholds = report.get("thresholds", {}) or {}
    core_thresholds = ["coverage_min", "mutation_score_min"]
    for key in core_thresholds:
        if key not in thresholds or thresholds[key] is None:
            warnings.append(f"Missing threshold '{key}' - will render as '-' in summary")

    # Determine success based on errors and strict mode
    success = len(errors) == 0
    if rules.strict and warnings:
        success = False

    return ValidationResult(
        success=success,
        language=language,
        errors=errors,
        warnings=warnings,
        schema_errors=schema_errors if schema_errors else [e for e in errors if "schema" in e.lower()],
        threshold_violations=[e for e in errors if "coverage" in e or "expected 0" in e],
        tool_warnings=warnings,
        debug_messages=debug_messages,
    )


def validate_report_file(
    report_path: Path,
    rules: ValidationRules | None = None,
    summary_path: Path | None = None,
    reports_dir: Path | None = None,
) -> ValidationResult:
    """Validate a report.json file.

    Convenience wrapper that loads the file first.

    Args:
        report_path: Path to report.json file.
        rules: Validation rules.
        summary_path: Optional summary.md path for cross-checks.
        reports_dir: Optional reports directory for artifact fallback checks.

    Returns:
        ValidationResult with errors, warnings, and debug info.
    """
    import json

    if not report_path.exists():
        return ValidationResult(
            success=False,
            errors=[f"Report file not found: {report_path}"],
        )

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidationResult(
            success=False,
            errors=[f"Invalid JSON in report: {exc}"],
        )

    summary_text = None
    if summary_path:
        if summary_path.exists():
            summary_text = summary_path.read_text(encoding="utf-8")
        else:
            return ValidationResult(
                success=False,
                errors=[f"summary file not found: {summary_path}"],
            )

    return validate_report(
        report,
        rules,
        summary_text=summary_text,
        reports_dir=reports_dir,
    )
