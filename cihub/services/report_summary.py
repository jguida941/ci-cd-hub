"""Report summary service for GUI/programmatic access."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.reporting import load_report, render_summary
from cihub.services.types import ServiceResult


@dataclass
class ReportSummaryResult(ServiceResult):
    """Result of rendering a report summary."""

    summary_text: str = ""
    report: dict[str, Any] = field(default_factory=dict)
    report_path: Path | None = None


def render_summary_from_report(
    report: dict[str, Any],
    *,
    include_metrics: bool = True,
) -> ReportSummaryResult:
    """Render a summary from report data."""
    try:
        summary = render_summary(report, include_metrics=include_metrics)
    except Exception as exc:
        return ReportSummaryResult(success=False, errors=[str(exc)])
    return ReportSummaryResult(success=True, summary_text=summary, report=report)


def render_summary_from_path(
    report_path: Path,
    *,
    include_metrics: bool = True,
) -> ReportSummaryResult:
    """Render a summary from a report.json path."""
    try:
        report = load_report(report_path)
        summary = render_summary(report, include_metrics=include_metrics)
    except Exception as exc:
        return ReportSummaryResult(success=False, errors=[str(exc)], report_path=report_path)
    return ReportSummaryResult(
        success=True,
        summary_text=summary,
        report=report,
        report_path=report_path,
    )
