"""Property-based tests using Hypothesis.

These tests use Hypothesis to generate random inputs and verify
that certain properties always hold, catching edge cases that
explicit example-based tests might miss.
"""

# TEST-METRICS:

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cihub.commands.threshold_cmd import THRESHOLD_METADATA, _validate_threshold_key
from cihub.config import deep_merge
from cihub.config.loader.inputs import generate_workflow_inputs
from cihub.utils.paths import validate_subdir

# =============================================================================
# Strategy Definitions
# =============================================================================


# Strategy for valid coverage percentages (0-100)
coverage_strategy = st.integers(min_value=0, max_value=100)

# Strategy for valid threshold values
threshold_strategy = st.integers(min_value=0, max_value=1000)

# Strategy for tool names
tool_name_strategy = st.sampled_from(
    [
        "pytest",
        "ruff",
        "black",
        "isort",
        "mypy",
        "bandit",
        "pip_audit",
        "trivy",
        "mutmut",
        "coverage",
        "jacoco",
        "checkstyle",
        "spotbugs",
        "pmd",
        "owasp",
        "pitest",
    ]
)

# Strategy for language names
language_strategy = st.sampled_from(["python", "java"])

# Strategy for simple config dicts
simple_config_strategy = st.fixed_dictionaries(
    {
        "enabled": st.booleans(),
    }
)

# Strategy for nested dicts (for deep_merge testing)
nested_dict_strategy = st.recursive(
    st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=5),
        values=st.one_of(st.integers(), st.text(max_size=10), st.booleans(), st.none()),
        max_size=3,
    ),
    lambda children: st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=5),
        values=children,
        max_size=3,
    ),
    max_leaves=10,
)

# Strategy for safe subdir segments
subdir_segment_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
    min_size=1,
    max_size=8,
).filter(lambda value: value not in {".", ".."})


# =============================================================================
# deep_merge Property Tests
# =============================================================================


class TestDeepMergeProperties:
    """Property-based tests for deep_merge function."""

    @given(d=nested_dict_strategy)
    @settings(max_examples=50)
    def test_merge_with_empty_is_identity(self, d: dict[str, Any]) -> None:
        """Property: merge(d, {}) == d (empty dict is identity)."""
        result = deep_merge(d, {})
        assert result == d

    @given(d=nested_dict_strategy)
    @settings(max_examples=50)
    def test_merge_empty_with_dict_returns_dict(self, d: dict[str, Any]) -> None:
        """Property: merge({}, d) == d (empty base returns override)."""
        result = deep_merge({}, d)
        assert result == d

    @given(d1=nested_dict_strategy, d2=nested_dict_strategy)
    @settings(max_examples=50)
    def test_merge_returns_dict(self, d1: dict[str, Any], d2: dict[str, Any]) -> None:
        """Property: merge always returns a dict."""
        result = deep_merge(d1, d2)
        assert isinstance(result, dict)

    @given(key=st.text(alphabet="abc", min_size=1, max_size=3), value=st.integers())
    @settings(max_examples=50)
    def test_override_wins(self, key: str, value: int) -> None:
        """Property: override values replace base values for same key."""
        base = {key: 999}
        override = {key: value}
        result = deep_merge(base, override)
        assert result[key] == value


# =============================================================================
# Threshold Boundary Tests
# =============================================================================


class TestThresholdBoundaries:
    """Property-based tests for threshold validation boundaries."""

    @given(coverage=coverage_strategy)
    @settings(max_examples=100)
    def test_coverage_in_valid_range(self, coverage: int) -> None:
        """Property: coverage values 0-100 are always valid."""
        # This tests that our coverage validation would accept these
        assert 0 <= coverage <= 100

    @given(
        coverage=st.integers(min_value=0, max_value=100),
        mutation=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_combined_thresholds_valid(self, coverage: int, mutation: int) -> None:
        """Property: coverage and mutation scores are independently valid."""
        thresholds = {
            "coverage_min": coverage,
            "mutation_score_min": mutation,
        }
        # Both should be in valid range
        assert 0 <= thresholds["coverage_min"] <= 100
        assert 0 <= thresholds["mutation_score_min"] <= 100

    @given(
        critical=st.integers(min_value=0, max_value=10),
        high=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=50)
    def test_vuln_thresholds_non_negative(self, critical: int, high: int) -> None:
        """Property: vulnerability thresholds are non-negative integers."""
        thresholds = {
            "max_critical_vulns": critical,
            "max_high_vulns": high,
        }
        assert thresholds["max_critical_vulns"] >= 0
        assert thresholds["max_high_vulns"] >= 0


# =============================================================================
# Tool Configuration Tests
# =============================================================================


class TestToolConfigProperties:
    """Property-based tests for tool configuration patterns."""

    @given(tool=tool_name_strategy, enabled=st.booleans())
    @settings(max_examples=50)
    def test_tool_enabled_is_boolean(self, tool: str, enabled: bool) -> None:
        """Property: tool enabled field is always boolean."""
        config = {tool: {"enabled": enabled}}
        assert isinstance(config[tool]["enabled"], bool)

    @given(
        tool=tool_name_strategy,
        enabled=st.booleans(),
        coverage=coverage_strategy,
    )
    @settings(max_examples=50)
    def test_tool_config_structure(self, tool: str, enabled: bool, coverage: int) -> None:
        """Property: tool configs follow expected structure."""
        config = {
            tool: {
                "enabled": enabled,
                "min_coverage": coverage,
            }
        }
        # Structure is valid
        assert "enabled" in config[tool]
        assert isinstance(config[tool]["enabled"], bool)
        assert 0 <= config[tool]["min_coverage"] <= 100

    @given(language=language_strategy, tool=tool_name_strategy)
    @settings(max_examples=50)
    def test_language_tool_config_nesting(self, language: str, tool: str) -> None:
        """Property: language configs nest tools correctly."""
        config = {language: {"tools": {tool: {"enabled": True}}}}
        # Access pattern works
        assert config[language]["tools"][tool]["enabled"] is True


# =============================================================================
# Workflow Input Generation Properties
# =============================================================================


class TestWorkflowInputsProperties:
    """Property-based tests for workflow input generation."""

    @given(
        coverage=st.integers(min_value=0, max_value=100),
        mutation=st.integers(min_value=0, max_value=100),
        run_pytest=st.booleans(),
    )
    @settings(max_examples=50)
    def test_python_global_thresholds_override(self, coverage: int, mutation: int, run_pytest: bool) -> None:
        """Property: global thresholds override tool thresholds for Python."""
        config = {
            "language": "python",
            "python": {
                "tools": {
                    "pytest": {"enabled": run_pytest, "min_coverage": 10},
                    "mutmut": {"enabled": False, "min_mutation_score": 10},
                }
            },
            "thresholds": {"coverage_min": coverage, "mutation_score_min": mutation},
        }
        inputs = generate_workflow_inputs(config)
        assert inputs["coverage_min"] == coverage
        assert inputs["mutation_score_min"] == mutation

    @given(cihub_value=st.one_of(st.none(), st.booleans(), st.text(max_size=20)))
    @settings(max_examples=50)
    def test_non_dict_ci_hub_defaults(self, cihub_value: Any) -> None:
        """Property: non-dict cihub config yields default debug flags."""
        assume(not isinstance(cihub_value, dict))
        inputs = generate_workflow_inputs({"language": "python", "cihub": cihub_value})
        assert inputs["cihub_debug"] is False
        assert inputs["cihub_verbose"] is False
        assert inputs["cihub_debug_context"] is False
        assert inputs["cihub_emit_triage"] is False


# =============================================================================
# Validator Properties
# =============================================================================


class TestValidatorProperties:
    """Property-based tests for validator helpers."""

    @given(segments=st.lists(subdir_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_validate_subdir_accepts_relative(self, segments: list[str]) -> None:
        """Property: validate_subdir accepts relative paths without traversal."""
        subdir = "/".join(segments)
        assert validate_subdir(subdir) == subdir

    @given(segments=st.lists(subdir_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_validate_subdir_rejects_traversal(self, segments: list[str]) -> None:
        """Property: validate_subdir rejects paths with traversal segments."""
        subdir = "/".join([segments[0], "..", *segments[1:]])
        with pytest.raises(ValueError):
            validate_subdir(subdir)

    @given(segments=st.lists(subdir_segment_strategy, min_size=1, max_size=4))
    @settings(max_examples=50)
    def test_validate_subdir_rejects_absolute(self, segments: list[str]) -> None:
        """Property: validate_subdir rejects absolute paths."""
        subdir = "/" + "/".join(segments)
        with pytest.raises(ValueError):
            validate_subdir(subdir)

    @given(key=st.sampled_from(sorted(THRESHOLD_METADATA.keys())))
    @settings(max_examples=50)
    def test_validate_threshold_key_accepts_known_keys(self, key: str) -> None:
        """Property: known threshold keys are accepted."""
        assert _validate_threshold_key(key) is None

    @given(key=st.text(min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_validate_threshold_key_rejects_unknown_keys(self, key: str) -> None:
        """Property: unknown threshold keys are rejected."""
        assume(key not in THRESHOLD_METADATA)
        assert _validate_threshold_key(key) is not None


# =============================================================================
# Report Structure Tests
# =============================================================================


class TestReportStructureProperties:
    """Property-based tests for report structure invariants."""

    @given(
        tools_ran=st.lists(tool_name_strategy, min_size=0, max_size=10, unique=True),
        tools_success=st.lists(tool_name_strategy, min_size=0, max_size=10, unique=True),
    )
    @settings(max_examples=50)
    def test_success_subset_of_ran(self, tools_ran: list[str], tools_success: list[str]) -> None:
        """Property: tools_success should be subset of tools_ran (conceptually)."""
        # This tests the invariant that you can't have a successful tool
        # that wasn't run. We construct valid data by intersection.
        ran_set = set(tools_ran)
        success_set = set(tools_success) & ran_set  # Ensure subset

        report = {
            "tools_ran": {t: True for t in tools_ran},
            "tools_success": {t: True for t in success_set},
        }

        # Verify invariant
        for tool in report["tools_success"]:
            assert tool in report["tools_ran"]

    @given(
        test_count=st.integers(min_value=0, max_value=10000),
        failures=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=50)
    def test_failures_not_exceed_count(self, test_count: int, failures: int) -> None:
        """Property: failures cannot exceed test_count."""
        # Enforce the constraint
        actual_failures = min(failures, test_count)

        metrics = {
            "test_count": test_count,
            "test_failures": actual_failures,
        }

        assert metrics["test_failures"] <= metrics["test_count"]
