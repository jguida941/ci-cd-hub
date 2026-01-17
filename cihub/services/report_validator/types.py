"""Report validation types - dataclasses for validation rules and results.

This module contains the ValidationRules and ValidationResult dataclasses
used throughout the report validation system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cihub.services.types import ServiceResult


@dataclass
class ValidationRules:
    """Rules for report validation.

    Attributes:
        expect_clean: Expect no issues (vs expect_issues for failing fixtures)
        coverage_min: Minimum required coverage percentage
        strict: Fail on warnings (not just errors)
        validate_schema: Validate against JSON schema
        consistency_only: Validate structure/consistency only (no clean/issue expectations)
    """

    expect_clean: bool = True
    coverage_min: int = 70
    strict: bool = False
    validate_schema: bool = False
    consistency_only: bool = False


@dataclass
class ValidationResult(ServiceResult):
    """Result of report validation.

    Extends ServiceResult with report-specific fields for language detection,
    schema errors, threshold violations, and debug messages.
    """

    language: str | None = None
    schema_errors: list[str] = field(default_factory=list)
    threshold_violations: list[str] = field(default_factory=list)
    tool_warnings: list[str] = field(default_factory=list)
    debug_messages: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """Report is valid if no errors."""
        return len(self.errors) == 0
