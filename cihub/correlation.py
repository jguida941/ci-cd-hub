"""Correlation helpers for hub orchestration.

This is a facade module that re-exports from cihub.core.correlation
for backward compatibility. New code should import from cihub.core.correlation.
"""

from __future__ import annotations

# Re-export request for mock.patch compatibility (tests patch cihub.correlation.request.urlopen)
from urllib import request

from cihub.core.correlation import (
    download_artifact,
    extract_correlation_id_from_artifact,
    find_run_by_correlation_id,
    generate_correlation_id,
    validate_correlation_id,
)

__all__ = [
    "download_artifact",
    "extract_correlation_id_from_artifact",
    "find_run_by_correlation_id",
    "generate_correlation_id",
    "validate_correlation_id",
    "request",  # For mock.patch compatibility
]
