"""Property-based tests for schema validation using Hypothesis.

These tests verify invariants for the validate_against_schema function
from cihub/services/report_validator/schema.py.
"""

# TEST-METRICS:

from __future__ import annotations

import json
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.services.report_validator.schema import validate_against_schema
from cihub.utils.paths import hub_root


def _load_tool_metrics_keys() -> frozenset[str]:
    """Load valid tool_metrics keys from the JSON schema to prevent drift."""
    schema_path = hub_root() / "schema" / "ci-report.v2.json"
    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    tool_metrics_props = schema.get("properties", {}).get("tool_metrics", {}).get("properties", {})
    return frozenset(tool_metrics_props.keys())


# Load valid keys from schema (prevents drift if schema changes)
VALID_TOOL_METRICS_KEYS = _load_tool_metrics_keys()

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for valid SHA-1 commit hashes (40 hex chars)
commit_strategy = st.text(alphabet="0123456789abcdef", min_size=40, max_size=40)

# Strategy for invalid commit hashes
invalid_commit_strategy = st.one_of(
    st.text(alphabet="0123456789abcdef", min_size=1, max_size=39),  # Too short
    st.text(alphabet="0123456789abcdef", min_size=41, max_size=50),  # Too long
    st.text(alphabet="ghijklmnop", min_size=40, max_size=40),  # Invalid chars
)

# Strategy for ISO datetime strings
datetime_strategy = st.datetimes().map(lambda dt: dt.isoformat() + "Z")

# Strategy for tool names
tool_name_strategy = st.sampled_from(
    ["pytest", "ruff", "bandit", "mypy", "black", "trivy", "jacoco", "checkstyle"]
)

# Strategy for tool boolean maps
tool_bool_map_strategy = st.dictionaries(
    keys=tool_name_strategy,
    values=st.booleans(),
    min_size=0,
    max_size=5,
)

# Strategy for coverage values (0-100 or null)
coverage_strategy = st.one_of(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    st.none(),
)

# Strategy for vuln counts
vuln_count_strategy = st.integers(min_value=0, max_value=1000)


def minimal_valid_report(
    commit: str = "a" * 40,
    timestamp: str = "2026-01-17T12:00:00Z",
    tools_ran: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a minimal valid report for testing."""
    return {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": "1.0.0",
            "workflow_ref": "main",
            "generated_at": timestamp,
        },
        "repository": "test/repo",
        "run_id": "12345",
        "run_number": "1",
        "commit": commit,
        "branch": "main",
        "timestamp": timestamp,
        "results": {
            "coverage": 80.0,
            "mutation_score": 70.0,
            "tests_passed": 100,
            "tests_failed": 0,
            "critical_vulns": 0,
            "high_vulns": 0,
            "medium_vulns": 0,
        },
        "tool_metrics": {},
        "tools_ran": tools_ran or {"pytest": True},
    }


# =============================================================================
# Schema Validation Property Tests
# =============================================================================


class TestValidateAgainstSchemaProperties:
    """Property tests for validate_against_schema function."""

    @given(data=st.dictionaries(st.text(max_size=20), st.text(max_size=20), max_size=5))
    @settings(max_examples=50)
    def test_always_returns_list(self, data: dict[str, Any]) -> None:
        """Property: validate_against_schema always returns a list."""
        result = validate_against_schema(data)
        assert isinstance(result, list)

    @given(commit=commit_strategy, timestamp=datetime_strategy)
    @settings(max_examples=30)
    def test_valid_report_returns_empty_list(self, commit: str, timestamp: str) -> None:
        """Property: valid report returns empty error list."""
        report = minimal_valid_report(commit=commit, timestamp=timestamp)
        errors = validate_against_schema(report)
        assert errors == [], f"Expected no errors for valid report, got: {errors}"

    @given(tools_ran=tool_bool_map_strategy)
    @settings(max_examples=30)
    def test_valid_tools_ran_map_accepted(self, tools_ran: dict[str, bool]) -> None:
        """Property: any valid tool boolean map is accepted in tools_ran."""
        if not tools_ran:
            tools_ran = {"pytest": True}  # Ensure non-empty for valid report
        report = minimal_valid_report(tools_ran=tools_ran)
        errors = validate_against_schema(report)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_missing_required_field_returns_errors(self) -> None:
        """Property: missing required fields produce errors."""
        # Report missing 'schema_version'
        report = minimal_valid_report()
        del report["schema_version"]
        errors = validate_against_schema(report)
        assert len(errors) > 0, "Expected errors for missing required field"
        assert any("schema_version" in e for e in errors)

    def test_wrong_schema_version_returns_errors(self) -> None:
        """Property: wrong schema_version produces errors."""
        report = minimal_valid_report()
        report["schema_version"] = "1.0"  # Wrong version
        errors = validate_against_schema(report)
        assert len(errors) > 0, "Expected errors for wrong schema_version"

    @given(commit=invalid_commit_strategy)
    @settings(max_examples=30)
    def test_invalid_commit_hash_returns_errors(self, commit: str) -> None:
        """Property: invalid commit hash format produces errors."""
        report = minimal_valid_report(commit=commit)
        errors = validate_against_schema(report)
        assert len(errors) > 0, f"Expected errors for invalid commit: {commit}"

    @given(
        coverage=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_coverage_out_of_range_returns_errors(self, coverage: float) -> None:
        """Property: coverage > 100 produces errors."""
        report = minimal_valid_report()
        report["results"]["coverage"] = coverage
        errors = validate_against_schema(report)
        assert len(errors) > 0, f"Expected errors for coverage: {coverage}"

    @given(
        coverage=st.floats(min_value=-100.0, max_value=-0.1, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_negative_coverage_returns_errors(self, coverage: float) -> None:
        """Property: negative coverage produces errors."""
        report = minimal_valid_report()
        report["results"]["coverage"] = coverage
        errors = validate_against_schema(report)
        assert len(errors) > 0, f"Expected errors for negative coverage: {coverage}"


class TestSchemaValidationIdempotency:
    """Property tests for schema validation idempotency."""

    @given(commit=commit_strategy)
    @settings(max_examples=20)
    def test_validation_is_idempotent(self, commit: str) -> None:
        """Property: validating same report twice gives same result."""
        report = minimal_valid_report(commit=commit)
        errors1 = validate_against_schema(report)
        errors2 = validate_against_schema(report)
        assert errors1 == errors2

    @given(data=st.dictionaries(st.text(max_size=10), st.integers(), max_size=3))
    @settings(max_examples=30)
    def test_invalid_report_validation_idempotent(self, data: dict[str, Any]) -> None:
        """Property: validating same invalid report twice gives same errors."""
        errors1 = validate_against_schema(data)
        errors2 = validate_against_schema(data)
        # Sort for comparison since order may vary
        assert sorted(errors1) == sorted(errors2)


class TestSchemaValidationErrorFormat:
    """Property tests for error message formatting."""

    def test_error_messages_contain_path_info(self) -> None:
        """Property: error messages include path information."""
        report = minimal_valid_report()
        # Introduce nested error
        report["results"]["coverage"] = "not a number"
        errors = validate_against_schema(report)
        assert len(errors) > 0
        # Errors should contain path like "results.coverage"
        assert any("results" in e or "coverage" in e for e in errors)

    def test_multiple_errors_all_reported(self) -> None:
        """Property: multiple errors are all reported."""
        report = minimal_valid_report()
        # Introduce multiple errors
        report["results"]["coverage"] = "invalid"
        report["results"]["mutation_score"] = "invalid"
        del report["commit"]
        errors = validate_against_schema(report)
        # Should have at least 2 errors (type errors for coverage/mutation + missing commit)
        assert len(errors) >= 2, f"Expected multiple errors, got {len(errors)}: {errors}"


class TestToolMetricsSchemaValidation:
    """Property tests for tool_metrics validation."""

    @given(
        metric_key=st.sampled_from(["ruff_errors", "mypy_errors", "bandit_high", "checkstyle_issues"]),
        value=st.one_of(st.integers(min_value=0, max_value=100), st.none()),
    )
    @settings(max_examples=30)
    def test_tool_metrics_valid_keys_accepted(self, metric_key: str, value: int | None) -> None:
        """Property: valid tool_metrics keys with integer/null values are accepted."""
        report = minimal_valid_report()
        report["tool_metrics"] = {metric_key: value}
        errors = validate_against_schema(report)
        tool_metric_errors = [e for e in errors if "tool_metrics" in e]
        assert tool_metric_errors == [], f"Unexpected tool_metrics errors: {tool_metric_errors}"

    @given(
        invalid_key=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=5, max_size=20).filter(
            lambda s: s not in VALID_TOOL_METRICS_KEYS
        )
    )
    @settings(max_examples=20)
    def test_tool_metrics_invalid_keys_rejected(self, invalid_key: str) -> None:
        """Property: unknown tool_metrics keys are rejected (additionalProperties: false)."""
        report = minimal_valid_report()
        report["tool_metrics"] = {invalid_key: 0}
        errors = validate_against_schema(report)
        # Should have an error about additional properties
        assert len(errors) > 0, f"Expected error for unknown key: {invalid_key}"
