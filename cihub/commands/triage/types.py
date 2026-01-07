"""Type definitions, constants, and helpers for triage command."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from cihub.services.triage_service import (
    CATEGORY_BY_TOOL,
    SEVERITY_BY_CATEGORY,
    TriageBundle,
    _build_markdown,
)

# Maximum errors to include in triage bundle (prevents huge payloads)
MAX_ERRORS_IN_TRIAGE = 20

# Severity ordering (lower = more severe)
SEVERITY_ORDER = {"blocker": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class TriageFilterConfig:
    """Configuration for filtering triage results."""

    min_severity: str | None = None
    category: str | None = None


def build_meta(args: argparse.Namespace) -> dict[str, object]:
    """Build metadata dict from command arguments."""
    return {
        "command": "cihub triage",
        "args": [str(arg) for arg in vars(args).values() if arg is not None],
    }


def filter_bundle(
    bundle: TriageBundle,
    min_severity: str | None,
    category: str | None,
) -> TriageBundle:
    """Filter triage bundle failures by severity and/or category.

    Args:
        bundle: Original TriageBundle
        min_severity: Minimum severity level (blocker > high > medium > low)
        category: Category filter (workflow, security, test, lint, docs, build, cihub)

    Returns:
        New TriageBundle with filtered failures
    """
    if not min_severity and not category:
        return bundle

    # Filter failures
    original_failures = bundle.triage.get("failures", [])
    filtered_failures = []

    for failure in original_failures:
        # Check severity filter
        if min_severity:
            failure_severity = failure.get("severity", "low")
            if SEVERITY_ORDER.get(failure_severity, 99) > SEVERITY_ORDER.get(min_severity, 99):
                continue

        # Check category filter
        if category:
            failure_category = failure.get("category", "")
            if failure_category != category:
                continue

        filtered_failures.append(failure)

    # Create new triage dict with filtered failures
    new_triage = dict(bundle.triage)
    new_triage["failures"] = filtered_failures
    new_triage["summary"] = dict(new_triage.get("summary", {}))
    new_triage["summary"]["failure_count"] = len(filtered_failures)

    # Add filter metadata
    new_triage["filters_applied"] = {
        "min_severity": min_severity,
        "category": category,
        "original_failure_count": len(original_failures),
        "filtered_failure_count": len(filtered_failures),
    }

    # Create new priority dict with filtered failures
    new_priority = dict(bundle.priority)
    new_priority["failures"] = filtered_failures
    new_priority["failure_count"] = len(filtered_failures)

    # Regenerate markdown with filtered data
    new_markdown = _build_markdown(new_triage)

    return TriageBundle(
        triage=new_triage,
        priority=new_priority,
        markdown=new_markdown,
        history_entry=bundle.history_entry,  # Keep original history entry
    )


# Re-export commonly used items
__all__ = [
    "CATEGORY_BY_TOOL",
    "MAX_ERRORS_IN_TRIAGE",
    "SEVERITY_BY_CATEGORY",
    "SEVERITY_ORDER",
    "TriageBundle",
    "TriageFilterConfig",
    "build_meta",
    "filter_bundle",
]
