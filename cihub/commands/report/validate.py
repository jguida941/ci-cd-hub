"""Report validation commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import ValidationRules, validate_report
from cihub.types import CommandResult


def _validate_report(args: argparse.Namespace) -> CommandResult:
    """Validate report.json structure and content.

    Returns CommandResult with:
    - summary: Pass/fail status
    - problems: List of errors and warnings with severity
    - data: Debug messages and validation details
    """
    report_path = Path(args.report)
    if not report_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Report file not found: {report_path}",
        )

    try:
        with report_path.open(encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid JSON in report: {exc}",
        )

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
        validate_schema=bool(getattr(args, "schema", False)),
    )
    result = validate_report(
        report,
        rules,
        summary_text=summary_text,
        reports_dir=reports_dir,
    )

    errors.extend(result.errors)
    warnings = list(result.warnings)

    # Build problems list with severity
    problems: list[dict[str, Any]] = []
    for err in errors:
        problems.append({"severity": "error", "message": err})
    for warn in warnings:
        problems.append({"severity": "warning", "message": warn})

    # Build data with debug info if requested
    data: dict[str, Any] = {
        "error_count": len(errors),
        "warning_count": len(warnings),
    }

    if getattr(args, "debug", False) and result.debug_messages:
        data["debug_messages"] = result.debug_messages

    # Determine exit code and summary
    if errors:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Validation FAILED: {len(errors)} errors, {len(warnings)} warnings",
            problems=problems,
            data=data,
        )

    if warnings and rules.strict:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Validation FAILED (strict mode): {len(warnings)} warnings treated as errors",
            problems=problems,
            data=data,
        )

    if warnings:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Validation PASSED with {len(warnings)} warnings",
            problems=problems,
            data=data,
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Validation PASSED",
        data=data,
    )
