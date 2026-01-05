"""Services layer for cihub - pure Python APIs returning dataclasses.

This module provides stable APIs for CLI, GUI, and programmatic access.
"""

from cihub.services.aggregation import (
    AggregationResult,
    aggregate_from_dispatch,
    aggregate_from_reports_dir,
)
from cihub.services.ci import CiRunResult, run_ci
from cihub.services.configuration import (
    ConfigLoadResult,
    load_repo_config,
    resolve_tool_path,
    set_nested_value,
    set_tool_enabled,
)
from cihub.services.detection import detect_language, resolve_language
from cihub.services.discovery import (
    DiscoveryFilters,
    DiscoveryResult,
    discover_repositories,
)
from cihub.services.report_summary import (
    ReportSummaryResult,
    render_summary_from_path,
    render_summary_from_report,
)
from cihub.services.report_validator import (
    ValidationResult,
    ValidationRules,
    validate_against_schema,
    validate_report,
    validate_report_file,
)
from cihub.services.triage_service import (
    MultiTriageResult,
    ToolEvidence,
    ToolStatus,
    TriageBundle,
    aggregate_triage_bundles,
    build_tool_evidence,
    detect_flaky_patterns,
    detect_test_count_regression,
    generate_triage_bundle,
    validate_artifact_evidence,
    write_triage_bundle,
)
from cihub.services.types import RepoEntry, ServiceResult

__all__ = [
    # Types
    "ServiceResult",
    "RepoEntry",
    # CI
    "CiRunResult",
    "run_ci",
    # Config
    "ConfigLoadResult",
    "load_repo_config",
    "resolve_tool_path",
    "set_nested_value",
    "set_tool_enabled",
    # Detection
    "detect_language",
    "resolve_language",
    # Discovery
    "DiscoveryFilters",
    "DiscoveryResult",
    "discover_repositories",
    # Validation
    "ValidationRules",
    "ValidationResult",
    "validate_against_schema",
    "validate_report",
    "validate_report_file",
    # Summary
    "ReportSummaryResult",
    "render_summary_from_path",
    "render_summary_from_report",
    # Aggregation
    "AggregationResult",
    "aggregate_from_dispatch",
    "aggregate_from_reports_dir",
    # Triage
    "MultiTriageResult",
    "ToolEvidence",
    "ToolStatus",
    "TriageBundle",
    "aggregate_triage_bundles",
    "build_tool_evidence",
    "detect_flaky_patterns",
    "detect_test_count_regression",
    "generate_triage_bundle",
    "validate_artifact_evidence",
    "write_triage_bundle",
]
