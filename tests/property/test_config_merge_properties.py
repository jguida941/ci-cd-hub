"""Property-based tests for config merge operations using Hypothesis.

These tests verify algebraic properties of deep_merge and config
building functions, catching edge cases that unit tests might miss.
"""

# TEST-METRICS:

from __future__ import annotations

import copy
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.config.merge import build_effective_config, deep_merge

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for simple leaf values
simple_value_strategy = st.one_of(
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.text(max_size=20),
    st.none(),
)

# Strategy for nested dictionaries (for merge testing)
nested_dict_strategy = st.recursive(
    st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=8),
        values=simple_value_strategy,
        max_size=3,
    ),
    lambda children: st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=8),
        values=children,
        max_size=3,
    ),
    max_leaves=10,
)


# Strategy for disjoint key dictionaries
@st.composite
def disjoint_dicts(draw: st.DrawFn) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate two dictionaries with no overlapping keys."""
    # Use different prefixes to ensure disjoint keys
    d1 = draw(
        st.dictionaries(
            keys=st.text(alphabet="abc", min_size=1, max_size=4).map(lambda s: f"a_{s}"),
            values=simple_value_strategy,
            max_size=3,
        )
    )
    d2 = draw(
        st.dictionaries(
            keys=st.text(alphabet="xyz", min_size=1, max_size=4).map(lambda s: f"z_{s}"),
            values=simple_value_strategy,
            max_size=3,
        )
    )
    return d1, d2


# Strategy for flat dictionaries (no nesting)
flat_dict_strategy = st.dictionaries(
    keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=6),
    values=simple_value_strategy,
    max_size=5,
)

# Strategy for config-like structures
config_like_strategy = st.fixed_dictionaries(
    {},
    optional={
        "language": st.sampled_from(["python", "java"]),
        "python": st.fixed_dictionaries(
            {},
            optional={
                "tools": st.dictionaries(
                    keys=st.sampled_from(["pytest", "ruff", "bandit"]),
                    values=st.booleans(),
                    max_size=2,
                )
            },
        ),
        "thresholds": st.fixed_dictionaries(
            {},
            optional={
                "coverage_min": st.integers(min_value=0, max_value=100),
                "mutation_score_min": st.integers(min_value=0, max_value=100),
            },
        ),
    },
)


# =============================================================================
# deep_merge Algebraic Property Tests
# =============================================================================


class TestDeepMergeAlgebraicProperties:
    """Tests for algebraic properties of deep_merge."""

    @given(d=nested_dict_strategy)
    @settings(max_examples=50)
    def test_left_identity(self, d: dict[str, Any]) -> None:
        """Property: merge({}, d) == d (empty dict is left identity)."""
        result = deep_merge({}, d)
        assert result == d

    @given(d=nested_dict_strategy)
    @settings(max_examples=50)
    def test_right_identity(self, d: dict[str, Any]) -> None:
        """Property: merge(d, {}) == d (empty dict is right identity)."""
        result = deep_merge(d, {})
        assert result == d

    @given(d1=flat_dict_strategy, d2=flat_dict_strategy)
    @settings(max_examples=50)
    def test_disjoint_merge_is_union(self, d1: dict[str, Any], d2: dict[str, Any]) -> None:
        """Property: for disjoint keys, merge contains all keys from both."""
        result = deep_merge(d1, d2)

        # All keys from d1 that aren't in d2 should be present
        for key in d1:
            assert key in result

        # All keys from d2 should be present
        for key in d2:
            assert key in result
            assert result[key] == d2[key]  # d2 takes precedence

    @given(d1=nested_dict_strategy, d2=nested_dict_strategy)
    @settings(max_examples=50)
    def test_always_returns_dict(self, d1: dict[str, Any], d2: dict[str, Any]) -> None:
        """Property: merge always returns a dict."""
        result = deep_merge(d1, d2)
        assert isinstance(result, dict)


class TestDeepMergeOverrideProperties:
    """Tests for override behavior of deep_merge."""

    @given(
        key=st.text(alphabet="abc", min_size=1, max_size=4),
        base_value=st.integers(),
        overlay_value=st.integers(),
    )
    @settings(max_examples=50)
    def test_overlay_wins_for_same_key(self, key: str, base_value: int, overlay_value: int) -> None:
        """Property: overlay value takes precedence for matching keys."""
        base = {key: base_value}
        overlay = {key: overlay_value}
        result = deep_merge(base, overlay)
        assert result[key] == overlay_value

    @given(
        key=st.text(alphabet="abc", min_size=1, max_size=4),
        nested_key=st.text(alphabet="xyz", min_size=1, max_size=4),
        base_value=st.integers(),
        overlay_value=st.integers(),
    )
    @settings(max_examples=50)
    def test_nested_overlay_wins(self, key: str, nested_key: str, base_value: int, overlay_value: int) -> None:
        """Property: nested overlay values take precedence."""
        base = {key: {nested_key: base_value}}
        overlay = {key: {nested_key: overlay_value}}
        result = deep_merge(base, overlay)
        assert result[key][nested_key] == overlay_value

    @given(
        key=st.text(alphabet="abc", min_size=1, max_size=4),
        base_nested_key=st.text(alphabet="xyz", min_size=1, max_size=4).map(lambda s: f"base_{s}"),
        overlay_nested_key=st.text(alphabet="xyz", min_size=1, max_size=4).map(lambda s: f"over_{s}"),
        base_value=st.integers(),
        overlay_value=st.integers(),
    )
    @settings(max_examples=50)
    def test_nested_merge_preserves_sibling_keys(
        self, key: str, base_nested_key: str, overlay_nested_key: str, base_value: int, overlay_value: int
    ) -> None:
        """Property: merging nested dicts preserves sibling keys from base."""
        base = {key: {base_nested_key: base_value}}
        overlay = {key: {overlay_nested_key: overlay_value}}
        result = deep_merge(base, overlay)

        assert base_nested_key in result[key]
        assert overlay_nested_key in result[key]
        assert result[key][base_nested_key] == base_value
        assert result[key][overlay_nested_key] == overlay_value


class TestDeepMergeImmutabilityProperties:
    """Tests for immutability guarantees of deep_merge."""

    @given(d1=nested_dict_strategy, d2=nested_dict_strategy)
    @settings(max_examples=50)
    def test_base_not_modified(self, d1: dict[str, Any], d2: dict[str, Any]) -> None:
        """Property: base dict is not modified by merge."""
        original = copy.deepcopy(d1)
        deep_merge(d1, d2)
        assert d1 == original

    @given(d1=nested_dict_strategy, d2=nested_dict_strategy)
    @settings(max_examples=50)
    def test_overlay_not_modified(self, d1: dict[str, Any], d2: dict[str, Any]) -> None:
        """Property: overlay dict is not modified by merge."""
        original = copy.deepcopy(d2)
        deep_merge(d1, d2)
        assert d2 == original

    @given(
        key=st.text(alphabet="abc", min_size=1, max_size=4),
        value=st.integers(),
    )
    @settings(max_examples=50)
    def test_result_not_shared_with_inputs(self, key: str, value: int) -> None:
        """Property: modifying result doesn't affect inputs."""
        base = {key: {"nested": value}}
        overlay = {}

        result = deep_merge(base, overlay)
        result[key]["nested"] = value + 1  # Modify result

        # Original should be unchanged
        assert base[key]["nested"] == value


# =============================================================================
# build_effective_config Property Tests
# =============================================================================


class TestBuildEffectiveConfigProperties:
    """Property-based tests for build_effective_config function."""

    @given(defaults=config_like_strategy)
    @settings(max_examples=50)
    def test_always_returns_dict(self, defaults: dict[str, Any]) -> None:
        """Property: build_effective_config always returns a dict."""
        result = build_effective_config(defaults)
        assert isinstance(result, dict)

    @given(
        defaults=config_like_strategy,
        profile=config_like_strategy,
        repo=config_like_strategy,
    )
    @settings(max_examples=30)
    def test_repo_config_highest_priority(
        self,
        defaults: dict[str, Any],
        profile: dict[str, Any],
        repo: dict[str, Any],
    ) -> None:
        """Property: repo config values take highest priority."""
        # Use distinct keys to verify priority
        defaults_with_key = {**defaults, "test_key": "from_defaults"}
        profile_with_key = {**profile, "test_key": "from_profile"}
        repo_with_key = {**repo, "test_key": "from_repo"}

        result = build_effective_config(defaults_with_key, profile_with_key, repo_with_key)
        assert result.get("test_key") == "from_repo"

    @given(
        defaults=config_like_strategy,
        profile=config_like_strategy,
    )
    @settings(max_examples=30)
    def test_profile_over_defaults(self, defaults: dict[str, Any], profile: dict[str, Any]) -> None:
        """Property: profile values override defaults."""
        defaults_with_key = {**defaults, "test_key": "from_defaults"}
        profile_with_key = {**profile, "test_key": "from_profile"}

        result = build_effective_config(defaults_with_key, profile_with_key, None)
        assert result.get("test_key") == "from_profile"

    @given(defaults=config_like_strategy)
    @settings(max_examples=30)
    def test_none_layers_ignored(self, defaults: dict[str, Any]) -> None:
        """Property: None profile and repo_config are safely ignored."""
        result1 = build_effective_config(defaults, None, None)
        result2 = build_effective_config(defaults)

        # Should produce same results (modulo normalization which is deterministic)
        assert result1.keys() == result2.keys()


# =============================================================================
# Merge with Lists Property Tests
# =============================================================================


class TestMergeWithListsProperties:
    """Tests for deep_merge behavior with list values."""

    @given(
        key=st.text(alphabet="abc", min_size=1, max_size=4),
        base_list=st.lists(st.integers(), max_size=5),
        overlay_list=st.lists(st.integers(), max_size=5),
    )
    @settings(max_examples=50)
    def test_lists_are_replaced_not_merged(self, key: str, base_list: list[int], overlay_list: list[int]) -> None:
        """Property: list values are replaced, not merged/concatenated."""
        base = {key: base_list}
        overlay = {key: overlay_list}
        result = deep_merge(base, overlay)

        # Overlay list should completely replace base list
        assert result[key] == overlay_list

    @given(
        key=st.text(alphabet="abc", min_size=1, max_size=4),
        base_list=st.lists(st.integers(), max_size=5),
    )
    @settings(max_examples=50)
    def test_base_list_preserved_if_not_overridden(self, key: str, base_list: list[int]) -> None:
        """Property: base list is preserved if overlay doesn't have the key."""
        base = {key: base_list}
        overlay = {"other_key": "value"}
        result = deep_merge(base, overlay)

        assert result[key] == base_list
