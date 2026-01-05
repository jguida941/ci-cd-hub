"""Triage bundle generation service.

This package provides structured failure triage for CI runs.
It produces machine-readable (JSON) and human-readable (Markdown)
bundles for debugging failed builds.

Module structure:
- types: Data models (ToolStatus, ToolEvidence, TriageBundle, etc.)
- evidence: Tool evidence building and validation
- detection: Flaky test and regression detection
- generation: Bundle generation (in triage_service.py for now)

Re-exports all public API from submodules for backward compatibility.
"""

from __future__ import annotations

from .detection import (
    detect_flaky_patterns,
    detect_gate_changes,
    detect_test_count_regression,
)
from .evidence import (
    build_tool_evidence,
    validate_artifact_evidence,
)
from .types import (
    CATEGORY_BY_TOOL,
    CATEGORY_ORDER,
    MULTI_TRIAGE_SCHEMA_VERSION,
    PRIORITY_SCHEMA_VERSION,
    SEVERITY_BY_CATEGORY,
    SEVERITY_ORDER,
    TEST_COUNT_DROP_THRESHOLD,
    TRIAGE_SCHEMA_VERSION,
    MultiTriageResult,
    ToolEvidence,
    ToolStatus,
    TriageBundle,
)

# The remaining functions are still in triage_service.py
# They will be migrated in future commits:
# - aggregate_triage_bundles
# - generate_triage_bundle
# - write_triage_bundle

__all__ = [
    # Types
    "ToolStatus",
    "ToolEvidence",
    "MultiTriageResult",
    "TriageBundle",
    # Constants
    "TRIAGE_SCHEMA_VERSION",
    "PRIORITY_SCHEMA_VERSION",
    "MULTI_TRIAGE_SCHEMA_VERSION",
    "TEST_COUNT_DROP_THRESHOLD",
    "SEVERITY_ORDER",
    "CATEGORY_ORDER",
    "CATEGORY_BY_TOOL",
    "SEVERITY_BY_CATEGORY",
    # Evidence
    "build_tool_evidence",
    "validate_artifact_evidence",
    # Detection
    "detect_flaky_patterns",
    "detect_gate_changes",
    "detect_test_count_regression",
]
