"""Tests for cihub.core.gate_specs module."""

# TEST-METRICS:
#   Coverage: 97.5%

from __future__ import annotations

import pytest

from cihub.core.gate_specs import (
    JAVA_THRESHOLDS,
    JAVA_TOOL_KEYS,
    JAVA_TOOLS,
    PYTHON_THRESHOLDS,
    PYTHON_TOOL_KEYS,
    PYTHON_TOOLS,
    Category,
    Comparator,
    ThresholdSpec,
    ToolSpec,
    evaluate_threshold,
    get_metric_value,
    get_threshold_spec_by_key,
    get_thresholds,
    get_tool_keys,
    get_tools,
    threshold_rows,
    tool_rows,
)


class TestThresholdSpec:
    """Tests for ThresholdSpec dataclass."""

    def test_threshold_spec_is_frozen(self) -> None:
        spec = ThresholdSpec(
            label="Test",
            key="test_key",
            unit="%",
            comparator=Comparator.GTE,
            metric_key="test_metric",
            failure_template="failed",
        )
        with pytest.raises(AttributeError):
            spec.label = "Modified"  # type: ignore[misc]


class TestToolSpec:
    """Tests for ToolSpec dataclass."""

    def test_tool_spec_is_frozen(self) -> None:
        spec = ToolSpec(Category.TESTING, "Test", "test")
        with pytest.raises(AttributeError):
            spec.label = "Modified"  # type: ignore[misc]


class TestGetThresholds:
    """Tests for get_thresholds function."""

    def test_returns_python_thresholds(self) -> None:
        result = get_thresholds("python")
        assert result == PYTHON_THRESHOLDS

    def test_returns_java_thresholds(self) -> None:
        result = get_thresholds("java")
        assert result == JAVA_THRESHOLDS

    def test_defaults_to_python_for_unknown(self) -> None:
        result = get_thresholds("unknown")
        assert result == PYTHON_THRESHOLDS


class TestGetTools:
    """Tests for get_tools function."""

    def test_returns_python_tools(self) -> None:
        result = get_tools("python")
        assert result == PYTHON_TOOLS

    def test_returns_java_tools(self) -> None:
        result = get_tools("java")
        assert result == JAVA_TOOLS


class TestGetToolKeys:
    """Tests for get_tool_keys function."""

    def test_returns_python_tool_keys(self) -> None:
        result = get_tool_keys("python")
        assert result == PYTHON_TOOL_KEYS

    def test_returns_java_tool_keys(self) -> None:
        result = get_tool_keys("java")
        assert result == JAVA_TOOL_KEYS

    def test_python_tool_keys_include_sbom_and_hypothesis(self) -> None:
        keys = get_tool_keys("python")
        assert "sbom" in keys
        assert "hypothesis" in keys

    def test_java_tool_keys_include_sbom_but_exclude_build_placeholder(self) -> None:
        keys = get_tool_keys("java")
        assert "sbom" in keys
        assert "__build__" not in keys


class TestThresholdRows:
    """Tests for threshold_rows function."""

    def test_returns_tuple_format(self) -> None:
        rows = threshold_rows("python")
        assert isinstance(rows, list)
        assert len(rows) > 0
        # Each row should be (label, key, unit)
        for row in rows:
            assert len(row) == 3
            assert isinstance(row[0], str)
            assert isinstance(row[1], str)
            assert isinstance(row[2], str)

    def test_contains_expected_python_thresholds(self) -> None:
        rows = threshold_rows("python")
        keys = [row[1] for row in rows]
        assert "coverage_min" in keys
        assert "mutation_score_min" in keys
        assert "trivy_cvss_fail" in keys
        assert "max_ruff_errors" in keys

    def test_contains_expected_java_thresholds(self) -> None:
        rows = threshold_rows("java")
        keys = [row[1] for row in rows]
        assert "coverage_min" in keys
        assert "owasp_cvss_fail" in keys
        assert "max_checkstyle_errors" in keys
        assert "max_spotbugs_bugs" in keys


class TestToolRows:
    """Tests for tool_rows function."""

    def test_returns_tuple_format(self) -> None:
        rows = tool_rows("python")
        assert isinstance(rows, list)
        assert len(rows) > 0
        # Each row should be (category, label, key)
        for row in rows:
            assert len(row) == 3
            assert isinstance(row[0], str)
            assert isinstance(row[1], str)
            assert isinstance(row[2], str)

    def test_contains_expected_python_tools(self) -> None:
        rows = tool_rows("python")
        keys = [row[2] for row in rows]
        assert "pytest" in keys
        assert "ruff" in keys
        assert "bandit" in keys
        assert "trivy" in keys

    def test_contains_expected_java_tools(self) -> None:
        rows = tool_rows("java")
        keys = [row[2] for row in rows]
        assert "__build__" in keys
        assert "jacoco" in keys
        assert "checkstyle" in keys
        assert "owasp" in keys


class TestEvaluateThreshold:
    """Tests for evaluate_threshold function."""

    def test_gte_comparator_passes_when_above(self) -> None:
        spec = ThresholdSpec(
            label="Coverage",
            key="coverage_min",
            unit="%",
            comparator=Comparator.GTE,
            metric_key="coverage",
            failure_template="coverage {value}% < {threshold}%",
        )
        passed, msg = evaluate_threshold(spec, 80, 70)
        assert passed is True
        assert msg is None

    def test_gte_comparator_fails_when_below(self) -> None:
        spec = ThresholdSpec(
            label="Coverage",
            key="coverage_min",
            unit="%",
            comparator=Comparator.GTE,
            metric_key="coverage",
            failure_template="coverage {value}% < {threshold}%",
        )
        passed, msg = evaluate_threshold(spec, 60, 70)
        assert passed is False
        assert msg == "coverage 60% < 70%"

    def test_lte_comparator_passes_when_below(self) -> None:
        spec = ThresholdSpec(
            label="Max Errors",
            key="max_errors",
            unit="",
            comparator=Comparator.LTE,
            metric_key="errors",
            failure_template="errors {value} > {threshold}",
        )
        passed, msg = evaluate_threshold(spec, 5, 10)
        assert passed is True
        assert msg is None

    def test_lte_comparator_fails_when_above(self) -> None:
        spec = ThresholdSpec(
            label="Max Errors",
            key="max_errors",
            unit="",
            comparator=Comparator.LTE,
            metric_key="errors",
            failure_template="errors {value} > {threshold}",
        )
        passed, msg = evaluate_threshold(spec, 15, 10)
        assert passed is False
        assert msg == "errors 15 > 10"

    def test_cvss_comparator_passes_when_below(self) -> None:
        spec = ThresholdSpec(
            label="CVSS Fail",
            key="cvss_fail",
            unit="",
            comparator=Comparator.CVSS,
            metric_key="max_cvss",
            failure_template="max CVSS {value:.1f} >= {threshold:.1f}",
        )
        passed, msg = evaluate_threshold(spec, 6.5, 7.0)
        assert passed is True
        assert msg is None

    def test_cvss_comparator_fails_when_at_or_above(self) -> None:
        spec = ThresholdSpec(
            label="CVSS Fail",
            key="cvss_fail",
            unit="",
            comparator=Comparator.CVSS,
            metric_key="max_cvss",
            failure_template="max CVSS {value:.1f} >= {threshold:.1f}",
        )
        passed, msg = evaluate_threshold(spec, 7.5, 7.0)
        assert passed is False
        assert msg == "max CVSS 7.5 >= 7.0"

    def test_cvss_comparator_skipped_when_threshold_zero(self) -> None:
        spec = ThresholdSpec(
            label="CVSS Fail",
            key="cvss_fail",
            unit="",
            comparator=Comparator.CVSS,
            metric_key="max_cvss",
            failure_template="max CVSS {value:.1f} >= {threshold:.1f}",
        )
        passed, msg = evaluate_threshold(spec, 9.0, 0.0)
        assert passed is True
        assert msg is None


class TestGetThresholdSpecByKey:
    """Tests for get_threshold_spec_by_key function."""

    def test_finds_python_coverage_min(self) -> None:
        spec = get_threshold_spec_by_key("python", "coverage_min")
        assert spec is not None
        assert spec.key == "coverage_min"
        assert spec.comparator == Comparator.GTE

    def test_finds_java_owasp_cvss_fail(self) -> None:
        spec = get_threshold_spec_by_key("java", "owasp_cvss_fail")
        assert spec is not None
        assert spec.key == "owasp_cvss_fail"
        assert spec.comparator == Comparator.CVSS

    def test_returns_none_for_unknown_key(self) -> None:
        spec = get_threshold_spec_by_key("python", "nonexistent_key")
        assert spec is None


class TestGetMetricValue:
    """Tests for get_metric_value function."""

    def test_gets_value_from_tool_metrics(self) -> None:
        spec = ThresholdSpec(
            label="Errors",
            key="max_errors",
            unit="",
            comparator=Comparator.LTE,
            metric_key="ruff_errors",
            failure_template="errors {value}",
        )
        value = get_metric_value(spec, {}, {"ruff_errors": 5})
        assert value == 5

    def test_gets_value_from_results(self) -> None:
        spec = ThresholdSpec(
            label="Coverage",
            key="coverage_min",
            unit="%",
            comparator=Comparator.GTE,
            metric_key="coverage",
            failure_template="coverage {value}%",
        )
        value = get_metric_value(spec, {"coverage": 85}, {})
        assert value == 85

    def test_returns_zero_for_missing(self) -> None:
        spec = ThresholdSpec(
            label="Test",
            key="test",
            unit="",
            comparator=Comparator.LTE,
            metric_key="missing",
            failure_template="test",
        )
        value = get_metric_value(spec, {}, {})
        assert value == 0

    def test_converts_string_to_int(self) -> None:
        spec = ThresholdSpec(
            label="Test",
            key="test",
            unit="",
            comparator=Comparator.LTE,
            metric_key="count",
            failure_template="test",
        )
        value = get_metric_value(spec, {}, {"count": "10"})
        assert value == 10

    def test_converts_string_to_float(self) -> None:
        spec = ThresholdSpec(
            label="Test",
            key="test",
            unit="",
            comparator=Comparator.CVSS,
            metric_key="score",
            failure_template="test",
        )
        value = get_metric_value(spec, {}, {"score": "7.5"})
        assert value == 7.5


class TestRegistryConsistency:
    """Tests to ensure registry definitions are consistent."""

    def test_python_thresholds_have_required_fields(self) -> None:
        for spec in PYTHON_THRESHOLDS:
            assert spec.label
            assert spec.key
            assert spec.metric_key
            assert spec.failure_template

    def test_java_thresholds_have_required_fields(self) -> None:
        for spec in JAVA_THRESHOLDS:
            assert spec.label
            assert spec.key
            assert spec.metric_key
            assert spec.failure_template

    def test_python_tools_have_valid_categories(self) -> None:
        for spec in PYTHON_TOOLS:
            assert isinstance(spec.category, Category)
            assert spec.label
            assert spec.key

    def test_java_tools_have_valid_categories(self) -> None:
        for spec in JAVA_TOOLS:
            assert isinstance(spec.category, Category)
            assert spec.label
            assert spec.key

    def test_tool_keys_are_subset_of_tool_specs(self) -> None:
        python_spec_keys = {s.key for s in PYTHON_TOOLS}
        for key in PYTHON_TOOL_KEYS:
            # Tool keys should exist in tools OR be internal (like build)
            assert key in python_spec_keys or key in ["build"]

        java_spec_keys = {s.key for s in JAVA_TOOLS}
        for key in JAVA_TOOL_KEYS:
            assert key in java_spec_keys or key in ["build", "__build__"]
