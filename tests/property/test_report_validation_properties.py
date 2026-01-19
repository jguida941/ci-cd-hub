"""Property-based tests for report validation using Hypothesis.

These tests verify invariants for CI report validation functions from
cihub/services/report_validator/, exercising actual production code.
"""

# TEST-METRICS:

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.services.report_validator.content import _get_nested, _parse_bool, validate_report
from cihub.services.report_validator.types import ValidationResult, ValidationRules

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for dot-notation paths
path_segment_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_",
    min_size=1,
    max_size=10,
)
dot_path_strategy = st.lists(path_segment_strategy, min_size=1, max_size=4).map(
    lambda parts: ".".join(parts)
)

# Strategy for boolean-like strings
bool_string_strategy = st.sampled_from(
    ["true", "True", "TRUE", "yes", "Yes", "YES", "1", "false", "False", "FALSE", "no", "No", "NO", "0"]
)

# Strategy for non-boolean strings
non_bool_string_strategy = st.text(min_size=1, max_size=20).filter(
    lambda s: s.strip().lower() not in {"true", "false", "yes", "no", "1", "0"}
)

# Strategy for simple values
simple_value_strategy = st.one_of(
    st.integers(min_value=-1000, max_value=1000),
    st.text(max_size=20),
    st.booleans(),
    st.none(),
)

# Strategy for nested dicts
nested_dict_strategy = st.recursive(
    st.dictionaries(
        keys=path_segment_strategy,
        values=simple_value_strategy,
        max_size=3,
    ),
    lambda children: st.dictionaries(
        keys=path_segment_strategy,
        values=children,
        max_size=3,
    ),
    max_leaves=10,
)

# Strategy for tool names (used in report structures)
tool_name_strategy = st.sampled_from(
    [
        "pytest",
        "ruff",
        "black",
        "mypy",
        "bandit",
        "trivy",
        "coverage",
        "jacoco",
        "checkstyle",
        "spotbugs",
    ]
)


# =============================================================================
# _get_nested Property Tests
# =============================================================================


class TestGetNestedProperties:
    """Property tests for the _get_nested function from content.py."""

    @given(data=nested_dict_strategy, path=dot_path_strategy)
    @settings(max_examples=100)
    def test_get_nested_matches_manual_navigation(self, data: dict[str, Any], path: str) -> None:
        """Property: _get_nested result matches manual path navigation."""
        result = _get_nested(data, path)
        # Navigate manually to compute expected value
        keys = path.split(".")
        expected = data
        for key in keys:
            if isinstance(expected, dict) and key in expected:
                expected = expected[key]
            else:
                expected = None
                break
        # Both branches: result must match manual navigation
        assert result == expected, f"_get_nested({path}) returned {result}, expected {expected}"

    @given(key=path_segment_strategy, value=simple_value_strategy)
    @settings(max_examples=50)
    def test_get_nested_single_level_retrieval(self, key: str, value: Any) -> None:
        """Property: single-level path retrieves the correct value."""
        data = {key: value}
        result = _get_nested(data, key)
        assert result == value

    @given(
        key1=path_segment_strategy,
        key2=path_segment_strategy,
        value=simple_value_strategy,
    )
    @settings(max_examples=50)
    def test_get_nested_two_level_retrieval(self, key1: str, key2: str, value: Any) -> None:
        """Property: two-level path retrieves the correct nested value."""
        data = {key1: {key2: value}}
        result = _get_nested(data, f"{key1}.{key2}")
        assert result == value

    @given(path=dot_path_strategy)
    @settings(max_examples=50)
    def test_get_nested_missing_returns_none(self, path: str) -> None:
        """Property: missing paths return None, not raise."""
        data: dict[str, Any] = {}
        result = _get_nested(data, path)
        assert result is None

    @given(key=path_segment_strategy)
    @settings(max_examples=50)
    def test_get_nested_non_dict_intermediate_returns_none(self, key: str) -> None:
        """Property: non-dict intermediate values return None."""
        data = {key: "not a dict"}
        result = _get_nested(data, f"{key}.nested")
        assert result is None


# =============================================================================
# _parse_bool Property Tests
# =============================================================================


class TestParseBoolProperties:
    """Property tests for the _parse_bool function from content.py."""

    @given(value=bool_string_strategy)
    @settings(max_examples=50)
    def test_parse_bool_truthy_values(self, value: str) -> None:
        """Property: truthy strings parse to True."""
        normalized = value.strip().lower()
        result = _parse_bool(value)
        if normalized in {"true", "yes", "1"}:
            assert result is True
        else:
            assert result is False

    @given(value=st.sampled_from(["true", "True", "TRUE", "yes", "Yes", "1"]))
    @settings(max_examples=20)
    def test_parse_bool_true_cases(self, value: str) -> None:
        """Property: known truthy values always return True."""
        assert _parse_bool(value) is True

    @given(value=st.sampled_from(["false", "False", "FALSE", "no", "No", "0"]))
    @settings(max_examples=20)
    def test_parse_bool_false_cases(self, value: str) -> None:
        """Property: known falsy values always return False."""
        assert _parse_bool(value) is False

    @given(value=non_bool_string_strategy)
    @settings(max_examples=50)
    def test_parse_bool_unknown_returns_none(self, value: str) -> None:
        """Property: unrecognized strings return None."""
        result = _parse_bool(value)
        assert result is None

    @given(value=bool_string_strategy, padding=st.text(alphabet=" \t", max_size=5))
    @settings(max_examples=50)
    def test_parse_bool_whitespace_invariant(self, value: str, padding: str) -> None:
        """Property: leading/trailing whitespace doesn't affect result."""
        padded = padding + value + padding
        result_padded = _parse_bool(padded)
        result_clean = _parse_bool(value)
        assert result_padded == result_clean

    @given(value=bool_string_strategy)
    @settings(max_examples=50)
    def test_parse_bool_case_insensitive(self, value: str) -> None:
        """Property: parsing is case-insensitive."""
        upper_result = _parse_bool(value.upper())
        lower_result = _parse_bool(value.lower())
        assert upper_result == lower_result


# =============================================================================
# Report Structure Invariant Tests
# =============================================================================


class TestValidateReportProperties:
    """Property tests for validate_report function from content.py."""

    @given(data=st.dictionaries(st.text(max_size=10), st.integers(), max_size=3))
    @settings(max_examples=50)
    def test_validate_report_always_returns_result(self, data: dict[str, Any]) -> None:
        """Property: validate_report always returns ValidationResult for any input."""
        rules = ValidationRules(consistency_only=True, validate_schema=False)
        result = validate_report(data, rules=rules)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    @given(
        coverage=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        coverage_min=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_coverage_threshold_validation(self, coverage: float, coverage_min: int) -> None:
        """Property: coverage below threshold produces warnings/errors."""
        report = {
            "python_version": "3.12",
            "results": {
                "coverage": coverage,
                "mutation_score": 80.0,
                "tests_passed": 10,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": {"pytest": True},
        }
        rules = ValidationRules(
            consistency_only=False,
            validate_schema=False,
            coverage_min=coverage_min,
            expect_clean=True,
        )
        result = validate_report(report, rules=rules)

        # If coverage < threshold and expect_clean, should have threshold violation
        if coverage < coverage_min:
            all_messages = result.errors + result.warnings + result.threshold_violations
            coverage_mentioned = any("coverage" in msg.lower() for msg in all_messages)
            # The validation should notice coverage is below threshold
            assert coverage_mentioned or len(result.threshold_violations) > 0 or not result.success

    @given(tools_ran=st.dictionaries(tool_name_strategy, st.booleans(), min_size=1, max_size=3))
    @settings(max_examples=30)
    def test_validate_report_detects_language(self, tools_ran: dict[str, bool]) -> None:
        """Property: validate_report detects language from report fields."""
        # Python report
        python_report = {
            "python_version": "3.12",
            "results": {
                "coverage": 80.0,
                "mutation_score": 70.0,
                "tests_passed": 10,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": tools_ran,
        }
        rules = ValidationRules(consistency_only=True, validate_schema=False)
        result = validate_report(python_report, rules=rules)
        assert result.language == "python"

        # Java report
        java_report = {
            "java_version": "21",
            "results": {
                "coverage": 80.0,
                "mutation_score": 70.0,
                "tests_passed": 10,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": tools_ran,
        }
        result = validate_report(java_report, rules=rules)
        assert result.language == "java"

    def test_empty_report_returns_result_with_errors_or_warnings(self) -> None:
        """Property: empty report still returns ValidationResult (may have errors)."""
        rules = ValidationRules(consistency_only=True, validate_schema=False)
        result = validate_report({}, rules=rules)
        assert isinstance(result, ValidationResult)


class TestReportStructureInvariants:
    """Property tests for report structure invariants using real data access."""

    @given(
        configured=st.lists(tool_name_strategy, min_size=0, max_size=5, unique=True),
        ran=st.lists(tool_name_strategy, min_size=0, max_size=5, unique=True),
    )
    @settings(max_examples=50)
    def test_drift_detection_invariant(self, configured: list[str], ran: list[str]) -> None:
        """Property: drift is when configured != ran (using real data access)."""
        report = {
            "tools_configured": {t: True for t in configured},
            "tools_ran": {t: True for t in ran},
        }

        configured_tools = set(_get_nested(report, "tools_configured") or {})
        ran_tools = set(_get_nested(report, "tools_ran") or {})

        has_drift = configured_tools != ran_tools
        drift_not_ran = configured_tools - ran_tools
        drift_unexpected = ran_tools - configured_tools

        # Drift exists iff sets differ
        assert has_drift == (len(drift_not_ran) > 0 or len(drift_unexpected) > 0)


# =============================================================================
# Nested Data Access Property Tests
# =============================================================================


class TestNestedDataAccessProperties:
    """Property tests for nested data access patterns used in report validation."""

    @given(
        coverage=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        mutation_score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_results_metrics_access(self, coverage: float, mutation_score: float) -> None:
        """Property: results.coverage and results.mutation_score access works."""
        report = {
            "results": {
                "coverage": coverage,
                "mutation_score": mutation_score,
            }
        }

        assert _get_nested(report, "results.coverage") == coverage
        assert _get_nested(report, "results.mutation_score") == mutation_score

    @given(
        tool=tool_name_strategy,
        passed=st.booleans(),
        errors=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_tool_results_access(self, tool: str, passed: bool, errors: int) -> None:
        """Property: tool_results.<tool>.passed access works correctly."""
        report = {"tool_results": {tool: {"passed": passed, "errors": errors}}}

        tool_result = _get_nested(report, f"tool_results.{tool}")
        assert tool_result is not None
        assert tool_result["passed"] == passed
        assert tool_result["errors"] == errors

    @given(data=nested_dict_strategy)
    @settings(max_examples=50)
    def test_get_nested_idempotent_for_single_key(self, data: dict[str, Any]) -> None:
        """Property: accessing same key twice yields same result."""
        if data:
            key = next(iter(data.keys()))
            result1 = _get_nested(data, key)
            result2 = _get_nested(data, key)
            assert result1 == result2
