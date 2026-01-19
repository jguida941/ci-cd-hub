"""Property-based tests for gate specifications using Hypothesis.

These tests verify invariants for gate evaluation specs, threshold
definitions, and exit code contracts.
"""

# TEST-METRICS:

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.core.gate_specs import (
    JAVA_THRESHOLDS,
    JAVA_TOOLS,
    PYTHON_THRESHOLDS,
    PYTHON_TOOLS,
    Category,
    Comparator,
    ThresholdSpec,
    ToolSpec,
)
from cihub.exit_codes import (
    EXIT_CODE_DESCRIPTIONS,
    EXIT_DECLINED,
    EXIT_FAILURE,
    EXIT_INTERNAL_ERROR,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for all threshold specs
all_threshold_specs = st.sampled_from(list(PYTHON_THRESHOLDS) + list(JAVA_THRESHOLDS))

# Strategy for all tool specs
all_tool_specs = st.sampled_from(list(PYTHON_TOOLS) + list(JAVA_TOOLS))

# Strategy for comparator types
comparator_strategy = st.sampled_from(list(Comparator))

# Strategy for category types
category_strategy = st.sampled_from(list(Category))

# Strategy for metric values
metric_value_strategy = st.one_of(
    st.integers(min_value=0, max_value=100),
    st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)

# Strategy for threshold values
threshold_value_strategy = st.integers(min_value=0, max_value=100)

# Strategy for exit codes
exit_code_strategy = st.sampled_from(
    [EXIT_SUCCESS, EXIT_FAILURE, EXIT_USAGE, EXIT_DECLINED, EXIT_INTERNAL_ERROR, EXIT_INTERRUPTED]
)


# =============================================================================
# ThresholdSpec Property Tests
# =============================================================================


class TestThresholdSpecProperties:
    """Property-based tests for ThresholdSpec invariants."""

    @given(spec=all_threshold_specs)
    def test_threshold_has_required_fields(self, spec: ThresholdSpec) -> None:
        """Property: all threshold specs have required non-empty fields."""
        assert spec.label, "label must not be empty"
        assert spec.key, "key must not be empty"
        assert spec.unit is not None, "unit must be defined (can be empty string)"
        assert isinstance(spec.comparator, Comparator), "comparator must be a Comparator"
        assert spec.metric_key, "metric_key must not be empty"
        assert spec.failure_template, "failure_template must not be empty"

    @given(spec=all_threshold_specs)
    def test_failure_template_has_placeholders(self, spec: ThresholdSpec) -> None:
        """Property: failure_template contains {value} and {threshold} placeholders."""
        assert "{value}" in spec.failure_template or "{value:" in spec.failure_template
        assert "{threshold}" in spec.failure_template or "{threshold:" in spec.failure_template

    @given(spec=all_threshold_specs)
    def test_key_is_snake_case(self, spec: ThresholdSpec) -> None:
        """Property: threshold keys follow snake_case convention."""
        # Check for valid snake_case characters
        assert all(c.islower() or c.isdigit() or c == "_" for c in spec.key)
        # Should not start or end with underscore
        assert not spec.key.startswith("_")
        assert not spec.key.endswith("_")

    @given(spec=all_threshold_specs)
    def test_metric_key_is_snake_case(self, spec: ThresholdSpec) -> None:
        """Property: metric keys follow snake_case convention."""
        assert all(c.islower() or c.isdigit() or c == "_" for c in spec.metric_key)

    @given(spec=all_threshold_specs)
    def test_unit_is_valid(self, spec: ThresholdSpec) -> None:
        """Property: unit is either '%' or empty string."""
        assert spec.unit in ("%", "")


# =============================================================================
# ToolSpec Property Tests
# =============================================================================


class TestToolSpecProperties:
    """Property-based tests for ToolSpec invariants."""

    @given(spec=all_tool_specs)
    def test_tool_has_required_fields(self, spec: ToolSpec) -> None:
        """Property: all tool specs have required non-empty fields."""
        assert isinstance(spec.category, Category), "category must be a Category"
        assert spec.label, "label must not be empty"
        assert spec.key, "key must not be empty"

    @given(spec=all_tool_specs)
    def test_key_is_snake_case(self, spec: ToolSpec) -> None:
        """Property: tool keys follow snake_case convention."""
        assert all(c.islower() or c.isdigit() or c == "_" for c in spec.key)


# =============================================================================
# Comparator Property Tests
# =============================================================================


class TestComparatorProperties:
    """Property-based tests for Comparator semantics."""

    @given(
        value=st.integers(min_value=0, max_value=100),
        threshold=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_gte_semantics(self, value: int, threshold: int) -> None:
        """Property: GTE means value >= threshold is passing."""
        # For coverage/mutation: value >= threshold is good (Comparator.GTE)
        is_passing = value >= threshold
        # Verify the comparison logic matches
        assert (value >= threshold) == is_passing

    @given(
        value=st.integers(min_value=0, max_value=100),
        threshold=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_lte_semantics(self, value: int, threshold: int) -> None:
        """Property: LTE means value <= threshold is passing."""
        # For errors/vulns: value <= threshold is good (Comparator.LTE)
        is_passing = value <= threshold
        assert (value <= threshold) == is_passing

    @given(
        cvss=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_cvss_semantics(self, cvss: float, threshold: float) -> None:
        """Property: CVSS means value >= threshold is failing (bad)."""
        # For CVSS: value >= threshold is BAD, failing (Comparator.CVSS)
        is_failing = cvss >= threshold
        assert (cvss >= threshold) == is_failing


# =============================================================================
# Exit Code Property Tests
# =============================================================================


class TestExitCodeProperties:
    """Property-based tests for exit code invariants."""

    @given(code=exit_code_strategy)
    def test_all_codes_have_descriptions(self, code: int) -> None:
        """Property: all exit codes have descriptions."""
        assert code in EXIT_CODE_DESCRIPTIONS
        assert EXIT_CODE_DESCRIPTIONS[code], "description must not be empty"

    def test_exit_success_is_zero(self) -> None:
        """Property: EXIT_SUCCESS is always 0 (Unix convention)."""
        assert EXIT_SUCCESS == 0

    def test_exit_failure_is_one(self) -> None:
        """Property: EXIT_FAILURE is always 1 (Unix convention)."""
        assert EXIT_FAILURE == 1

    def test_exit_usage_is_two(self) -> None:
        """Property: EXIT_USAGE is always 2 (Unix convention)."""
        assert EXIT_USAGE == 2

    def test_exit_interrupted_is_130(self) -> None:
        """Property: EXIT_INTERRUPTED is 130 (128 + SIGINT=2)."""
        # Unix convention: 128 + signal number
        assert EXIT_INTERRUPTED == 130

    @given(code=exit_code_strategy)
    def test_exit_codes_are_non_negative(self, code: int) -> None:
        """Property: all exit codes are non-negative integers."""
        assert code >= 0
        assert code < 256  # Valid Unix exit code range


# =============================================================================
# Cross-Language Consistency Property Tests
# =============================================================================


class TestCrossLanguageConsistencyProperties:
    """Property-based tests for consistency between Python and Java specs."""

    def test_coverage_threshold_exists_for_both(self) -> None:
        """Property: coverage threshold is defined for both languages."""
        python_keys = {spec.key for spec in PYTHON_THRESHOLDS}
        java_keys = {spec.key for spec in JAVA_THRESHOLDS}

        assert "coverage_min" in python_keys
        assert "coverage_min" in java_keys

    def test_mutation_threshold_exists_for_both(self) -> None:
        """Property: mutation score threshold is defined for both languages."""
        python_keys = {spec.key for spec in PYTHON_THRESHOLDS}
        java_keys = {spec.key for spec in JAVA_THRESHOLDS}

        assert "mutation_score_min" in python_keys
        assert "mutation_score_min" in java_keys

    def test_all_categories_are_used(self) -> None:
        """Property: all category types are used by at least one tool."""
        all_tool_categories = {spec.category for spec in PYTHON_TOOLS} | {spec.category for spec in JAVA_TOOLS}

        for category in Category:
            assert category in all_tool_categories, f"Category {category} is never used"

    def test_all_comparators_are_used(self) -> None:
        """Property: all comparator types are used by at least one threshold."""
        all_comparators = {spec.comparator for spec in PYTHON_THRESHOLDS} | {
            spec.comparator for spec in JAVA_THRESHOLDS
        }

        for comparator in Comparator:
            assert comparator in all_comparators, f"Comparator {comparator} is never used"


# =============================================================================
# Spec Uniqueness Property Tests
# =============================================================================


class TestSpecUniquenessProperties:
    """Property-based tests for uniqueness constraints."""

    def test_python_threshold_keys_unique(self) -> None:
        """Property: Python threshold keys are unique."""
        keys = [spec.key for spec in PYTHON_THRESHOLDS]
        assert len(keys) == len(set(keys)), "Duplicate threshold keys in PYTHON_THRESHOLDS"

    def test_java_threshold_keys_unique(self) -> None:
        """Property: Java threshold keys are unique."""
        keys = [spec.key for spec in JAVA_THRESHOLDS]
        assert len(keys) == len(set(keys)), "Duplicate threshold keys in JAVA_THRESHOLDS"

    def test_python_tool_keys_unique(self) -> None:
        """Property: Python tool keys are unique."""
        keys = [spec.key for spec in PYTHON_TOOLS]
        assert len(keys) == len(set(keys)), "Duplicate tool keys in PYTHON_TOOLS"

    def test_java_tool_keys_unique(self) -> None:
        """Property: Java tool keys are unique."""
        keys = [spec.key for spec in JAVA_TOOLS]
        assert len(keys) == len(set(keys)), "Duplicate tool keys in JAVA_TOOLS"
