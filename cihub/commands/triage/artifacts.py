"""Artifact finding and processing utilities for triage.

This module provides functions for locating and processing
CI artifacts like report.json files and tool outputs.
"""

from __future__ import annotations

from pathlib import Path


def find_report_in_artifacts(artifacts_dir: Path) -> Path | None:
    """Find first report.json in downloaded artifacts (may be nested in subdirs).

    Args:
        artifacts_dir: Root directory containing downloaded artifacts

    Returns:
        Path to first report.json found, or None if not found
    """
    for report_path in artifacts_dir.rglob("report.json"):
        return report_path
    return None


def find_all_reports_in_artifacts(artifacts_dir: Path) -> list[Path]:
    """Find all report.json files in downloaded artifacts.

    Useful for orchestrator runs that produce multiple reports
    (one per repository).

    Args:
        artifacts_dir: Root directory containing downloaded artifacts

    Returns:
        Sorted list of paths to all report.json files found
    """
    return sorted(artifacts_dir.rglob("report.json"), key=lambda p: str(p))


def find_tool_outputs_in_artifacts(artifacts_dir: Path) -> Path | None:
    """Find tool-outputs directory in downloaded artifacts.

    Tool outputs directory contains raw output from CI tools
    (ruff-report.json, pytest.xml, etc.)

    Args:
        artifacts_dir: Root directory containing downloaded artifacts

    Returns:
        Path to tool-outputs directory, or None if not found
    """
    for tool_outputs in artifacts_dir.rglob("tool-outputs"):
        if tool_outputs.is_dir():
            return tool_outputs
    return None


def get_reports_dir_from_report(report_path: Path) -> Path:
    """Get the reports directory from a report.json path.

    The reports directory is typically the parent of report.json
    and contains tool output files.

    Args:
        report_path: Path to report.json

    Returns:
        Parent directory of report.json
    """
    return report_path.parent


def find_artifact_by_pattern(artifacts_dir: Path, pattern: str) -> list[Path]:
    """Find artifacts matching a glob pattern.

    Args:
        artifacts_dir: Root directory to search
        pattern: Glob pattern to match (e.g., "*.json", "**/ruff-report.json")

    Returns:
        List of matching paths, sorted alphabetically
    """
    return sorted(artifacts_dir.rglob(pattern), key=lambda p: str(p))


__all__ = [
    "find_all_reports_in_artifacts",
    "find_artifact_by_pattern",
    "find_report_in_artifacts",
    "find_tool_outputs_in_artifacts",
    "get_reports_dir_from_report",
]
