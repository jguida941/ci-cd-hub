"""Core business logic modules for cihub.

This package contains the core algorithms and data processing logic
that are independent of CLI and service layers.
"""

from __future__ import annotations

# Re-export modules and symbols for convenience
from cihub.core import aggregation, badges, ci_report, ci_runner, reporting
from cihub.core.correlation import (
    download_artifact,
    extract_correlation_id_from_artifact,
    find_run_by_correlation_id,
    generate_correlation_id,
    validate_correlation_id,
)

__all__ = [
    "aggregation",
    "badges",
    "ci_report",
    "ci_runner",
    "reporting",
    # correlation
    "download_artifact",
    "extract_correlation_id_from_artifact",
    "find_run_by_correlation_id",
    "generate_correlation_id",
    "validate_correlation_id",
]
