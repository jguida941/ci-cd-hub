"""Report validation service - validates report.json structure and content.

This package provides validation for CI reports, split into logical modules:
- types.py: ValidationRules and ValidationResult dataclasses
- schema.py: JSON schema validation
- artifact.py: Tool output artifact validation
- content.py: Report content validation logic

All public symbols are re-exported from this __init__.py for backward compatibility.
Import patterns like `from cihub.services.report_validator import validate_report`
continue to work unchanged.

Example:
    from cihub.services.report_validator import (
        ValidationRules,
        ValidationResult,
        validate_report,
        validate_report_file,
        validate_against_schema,
    )

    report = {"schema_version": "2.0", ...}
    result = validate_report(report, ValidationRules(expect_clean=True))
    if not result.success:
        print(f"Validation failed: {result.errors}")
"""

from __future__ import annotations

# Re-export registry constants for backward compatibility
# (the old module imported these and external code may rely on them)
from cihub.tools.registry import (
    JAVA_ARTIFACTS,
    JAVA_LINT_METRICS,
    JAVA_SECURITY_METRICS,
    JAVA_SUMMARY_MAP,
    JAVA_TOOL_METRICS,
    PYTHON_ARTIFACTS,
    PYTHON_LINT_METRICS,
    PYTHON_SECURITY_METRICS,
    PYTHON_SUMMARY_MAP,
    PYTHON_TOOL_METRICS,
)

# Re-export artifact helpers (private but used by some internal code)
from .artifact import check_artifacts_non_empty, iter_existing_patterns

# Re-export content validation (main API)
from .content import validate_report, validate_report_file

# Re-export schema validation
from .schema import validate_against_schema

# Re-export types
from .types import ValidationResult, ValidationRules

# Backward compatibility: expose private functions with underscore prefix
# These are used by internal code that imports them directly
_iter_existing_patterns = iter_existing_patterns
_check_artifacts_non_empty = check_artifacts_non_empty

__all__ = [
    # Public API
    "ValidationRules",
    "ValidationResult",
    "validate_report",
    "validate_report_file",
    "validate_against_schema",
    # Private helpers (exposed for backward compat)
    "iter_existing_patterns",
    "check_artifacts_non_empty",
    "_iter_existing_patterns",
    "_check_artifacts_non_empty",
    # Registry constants (backward compat)
    "PYTHON_TOOL_METRICS",
    "JAVA_TOOL_METRICS",
    "PYTHON_ARTIFACTS",
    "JAVA_ARTIFACTS",
    "PYTHON_LINT_METRICS",
    "JAVA_LINT_METRICS",
    "PYTHON_SECURITY_METRICS",
    "JAVA_SECURITY_METRICS",
    "PYTHON_SUMMARY_MAP",
    "JAVA_SUMMARY_MAP",
]
