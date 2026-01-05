"""Core aggregation helpers for hub orchestration."""

from __future__ import annotations

from .artifacts import fetch_and_validate_artifact
from .github_api import GitHubAPI
from .metrics import extract_metrics_from_report
from .render import aggregate_results, generate_details_markdown, generate_summary_markdown
from .runner import load_thresholds, poll_run_completion, run_aggregation, run_reports_aggregation
from .status import (
    _artifact_name_from_report,
    _config_from_artifact_name,
    _run_status_for_invalid_report,
    _run_status_from_report,
    _status_from_report,
    create_run_status,
    load_dispatch_metadata,
)

__all__ = [
    "GitHubAPI",
    "load_dispatch_metadata",
    "create_run_status",
    "_artifact_name_from_report",
    "_config_from_artifact_name",
    "_status_from_report",
    "_run_status_from_report",
    "_run_status_for_invalid_report",
    "poll_run_completion",
    "extract_metrics_from_report",
    "fetch_and_validate_artifact",
    "aggregate_results",
    "generate_details_markdown",
    "generate_summary_markdown",
    "load_thresholds",
    "run_aggregation",
    "run_reports_aggregation",
]
