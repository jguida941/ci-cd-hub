"""Report validation helpers for CI engine.

This module handles self-validation of CI reports against schema
and consistency rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def _self_validate_report(
    report: dict[str, Any],
    summary_text: str,
    output_dir: Path,
    problems: list[dict[str, Any]],
    env_map: Mapping[str, str],
) -> None:
    """Self-validate the generated report against schema and consistency rules.

    This is a production invariant check that catches contradictions between
    the artifacts we just wrote (report/summary) and the report contract.

    Consistency-only validation (not gate policy): it should not invent quality
    thresholds. The goal is to catch drift/contradictions like:
    - Summary Tools table says ran=true but report.tools_ran says false
    - Report is missing required structural fields

    Schema validation is enforced in CI (GITHUB_ACTIONS) and reported as a
    warning locally when git metadata may be unavailable.

    Args:
        report: The generated CI report dict
        summary_text: The rendered summary markdown text
        output_dir: Directory where report artifacts are written
        problems: List to append validation problems to (mutated in place)
        env_map: Environment variable mapping
    """
    try:
        from cihub.services.report_validator import (
            ValidationRules,
            validate_against_schema,
            validate_report,
        )

        schema_errors = validate_against_schema(report)
        schema_severity = "error" if env_map.get("GITHUB_ACTIONS") else "warning"
        for msg in schema_errors:
            problems.append(
                {
                    "severity": schema_severity,
                    "message": msg,
                    "code": "CIHUB-CI-REPORT-SCHEMA",
                }
            )

        validation = validate_report(
            report,
            ValidationRules(consistency_only=True, strict=False, validate_schema=False),
            summary_text=summary_text,
            reports_dir=output_dir,
        )
        for msg in validation.errors:
            problems.append(
                {
                    "severity": "error",
                    "message": msg,
                    "code": "CIHUB-CI-REPORT-SELF-VALIDATE",
                }
            )

        # Escalate summary/report mismatches to errors (hard contradictions).
        for msg in validation.warnings:
            lowered = msg.lower()
            is_contradiction = (
                "configured mismatch" in lowered
                or "ran mismatch" in lowered
                or "summary missing tool row" in lowered
                or "report.json missing tools_ran" in lowered
            )
            problems.append(
                {
                    "severity": "error" if is_contradiction else "warning",
                    "message": msg,
                    "code": "CIHUB-CI-REPORT-SELF-VALIDATE",
                }
            )
    except Exception as exc:  # noqa: BLE001 - best effort: surface and fail-safe
        problems.append(
            {
                "severity": "error",
                "message": f"self-validation failed: {exc}",
                "code": "CIHUB-CI-REPORT-SELF-VALIDATE",
            }
        )
