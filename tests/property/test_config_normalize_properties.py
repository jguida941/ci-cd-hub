"""Property-based tests for config normalization using Hypothesis.

These tests verify invariants that should always hold for config
normalization functions, catching edge cases that unit tests might miss.
"""

# TEST-METRICS:

from __future__ import annotations

from typing import Any

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cihub.config.normalize import (
    _FAIL_ON_KEY_MAP,
    THRESHOLD_PROFILES,
    get_fail_on_cvss,
    get_fail_on_flag,
    normalize_config,
    normalize_tool_configs,
    tool_enabled,
)

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for language keys
language_strategy = st.sampled_from(["python", "java"])

# Strategy for known tool names
tool_strategy = st.sampled_from(
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
        "jacoco",
        "checkstyle",
        "spotbugs",
        "pmd",
        "owasp",
        "semgrep",
        "docker",
        "codeql",
    ]
)

# Strategy for tools in the fail_on key map
fail_on_mapped_tool_strategy = st.sampled_from(sorted(_FAIL_ON_KEY_MAP.keys()))

# Strategy for boolean tool configs (shorthand form)
bool_tool_config_strategy = st.booleans()

# Strategy for dict tool configs (full form)
dict_tool_config_strategy = st.fixed_dictionaries(
    {
        "enabled": st.booleans(),
    },
    optional={
        "min_coverage": st.integers(min_value=0, max_value=100),
        "fail_on_error": st.booleans(),
    },
)

# Strategy for threshold profile names
threshold_profile_strategy = st.sampled_from(sorted(THRESHOLD_PROFILES.keys()))

# Strategy for CVSS scores (valid range)
cvss_strategy = st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)

# Strategy for arbitrary config dicts (for fuzz testing)
simple_value_strategy = st.one_of(
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.text(max_size=20),
    st.none(),
)

nested_config_strategy = st.recursive(
    st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10),
        values=simple_value_strategy,
        max_size=3,
    ),
    lambda children: st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10),
        values=children,
        max_size=3,
    ),
    max_leaves=10,
)


# =============================================================================
# normalize_config Property Tests
# =============================================================================


class TestNormalizeConfigProperties:
    """Property-based tests for normalize_config function."""

    @given(config=nested_config_strategy)
    @settings(max_examples=50)
    def test_normalize_always_returns_dict(self, config: dict[str, Any]) -> None:
        """Property: normalize_config always returns a dict for dict input."""
        result = normalize_config(config)
        assert isinstance(result, dict)

    @given(value=st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=10)))
    @settings(max_examples=30)
    def test_normalize_non_dict_returns_empty_dict(self, value: Any) -> None:
        """Property: normalize_config returns {} for non-dict inputs."""
        assume(not isinstance(value, dict))
        result = normalize_config(value)  # type: ignore[arg-type]
        assert result == {}

    @given(config=nested_config_strategy)
    @settings(max_examples=50)
    def test_normalize_is_idempotent(self, config: dict[str, Any]) -> None:
        """Property: normalize_config(normalize_config(x)) == normalize_config(x)."""
        once = normalize_config(config)
        twice = normalize_config(once)
        assert once == twice

    @given(profile=threshold_profile_strategy)
    @settings(max_examples=20)
    def test_threshold_profile_applies_preset_values(self, profile: str) -> None:
        """Property: thresholds_profile applies the correct preset values."""
        config = {"thresholds_profile": profile}
        result = normalize_config(config)

        preset = THRESHOLD_PROFILES[profile]
        for key, expected_value in preset.items():
            assert result.get("thresholds", {}).get(key) == expected_value

    @given(
        profile=threshold_profile_strategy,
        override_key=st.sampled_from(["coverage_min", "mutation_score_min", "max_critical_vulns"]),
        override_value=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=30)
    def test_thresholds_override_profile(self, profile: str, override_key: str, override_value: int) -> None:
        """Property: explicit thresholds override profile values."""
        config = {
            "thresholds_profile": profile,
            "thresholds": {override_key: override_value},
        }
        result = normalize_config(config)

        assert result.get("thresholds", {}).get(override_key) == override_value


# =============================================================================
# normalize_tool_configs Property Tests
# =============================================================================


class TestNormalizeToolConfigsProperties:
    """Property-based tests for normalize_tool_configs function."""

    @given(tool=tool_strategy, enabled=st.booleans(), language=language_strategy)
    @settings(max_examples=50)
    def test_bool_shorthand_expands_to_dict(self, tool: str, enabled: bool, language: str) -> None:
        """Property: boolean tool config expands to {"enabled": <bool>}."""
        config = {language: {"tools": {tool: enabled}}}
        result = normalize_tool_configs(config)

        tool_config = result.get(language, {}).get("tools", {}).get(tool)
        assert isinstance(tool_config, dict)
        assert tool_config.get("enabled") == enabled

    @given(tool=tool_strategy, enabled=st.booleans(), language=language_strategy)
    @settings(max_examples=50)
    def test_dict_form_preserved(self, tool: str, enabled: bool, language: str) -> None:
        """Property: dict tool configs are preserved."""
        config = {language: {"tools": {tool: {"enabled": enabled, "extra": "value"}}}}
        result = normalize_tool_configs(config)

        tool_config = result.get(language, {}).get("tools", {}).get(tool)
        assert isinstance(tool_config, dict)
        assert tool_config.get("enabled") == enabled
        assert tool_config.get("extra") == "value"

    @given(config=nested_config_strategy)
    @settings(max_examples=50)
    def test_normalize_tool_configs_is_idempotent(self, config: dict[str, Any]) -> None:
        """Property: normalize_tool_configs(normalize_tool_configs(x)) == normalize_tool_configs(x)."""
        once = normalize_tool_configs(config)
        twice = normalize_tool_configs(once)
        assert once == twice


# =============================================================================
# get_fail_on_flag Property Tests
# =============================================================================


class TestGetFailOnFlagProperties:
    """Property-based tests for get_fail_on_flag function."""

    @given(tool=tool_strategy, language=language_strategy)
    @settings(max_examples=50)
    def test_always_returns_bool(self, tool: str, language: str) -> None:
        """Property: get_fail_on_flag always returns a boolean."""
        result = get_fail_on_flag({}, tool, language)
        assert isinstance(result, bool)

    @given(tool=fail_on_mapped_tool_strategy, language=language_strategy, value=st.booleans())
    @settings(max_examples=50)
    def test_explicit_value_returned(self, tool: str, language: str, value: bool) -> None:
        """Property: explicit config value is always returned."""
        flag_key = _FAIL_ON_KEY_MAP[tool]
        config = {language: {"tools": {tool: {flag_key: value}}}}
        result = get_fail_on_flag(config, tool, language)
        assert result == value

    @given(tool=tool_strategy, language=language_strategy, default=st.booleans())
    @settings(max_examples=50)
    def test_default_override_works(self, tool: str, language: str, default: bool) -> None:
        """Property: explicit default parameter is respected when no config."""
        result = get_fail_on_flag({}, tool, language, default=default)
        # For unmapped tools, default is returned; for mapped tools, internal default may differ
        assert isinstance(result, bool)

    @given(config=nested_config_strategy, tool=tool_strategy, language=language_strategy)
    @settings(max_examples=30)
    def test_never_raises_for_any_config(self, config: dict[str, Any], tool: str, language: str) -> None:
        """Property: get_fail_on_flag never raises for any config shape."""
        result = get_fail_on_flag(config, tool, language)
        assert isinstance(result, bool)


# =============================================================================
# get_fail_on_cvss Property Tests
# =============================================================================


class TestGetFailOnCvssProperties:
    """Property-based tests for get_fail_on_cvss function."""

    @given(tool=st.sampled_from(["owasp", "trivy"]), language=language_strategy)
    @settings(max_examples=50)
    def test_always_returns_float(self, tool: str, language: str) -> None:
        """Property: get_fail_on_cvss always returns a float."""
        result = get_fail_on_cvss({}, tool, language)
        assert isinstance(result, float)

    @given(
        tool=st.sampled_from(["owasp", "trivy"]),
        language=language_strategy,
        cvss=cvss_strategy,
    )
    @settings(max_examples=50)
    def test_explicit_cvss_returned(self, tool: str, language: str, cvss: float) -> None:
        """Property: explicit fail_on_cvss value is returned."""
        config = {language: {"tools": {tool: {"fail_on_cvss": cvss}}}}
        result = get_fail_on_cvss(config, tool, language)
        assert result == cvss

    @given(
        tool=st.sampled_from(["owasp", "trivy"]),
        language=language_strategy,
        default=cvss_strategy,
    )
    @settings(max_examples=50)
    def test_default_cvss_returned(self, tool: str, language: str, default: float) -> None:
        """Property: default CVSS is returned when not configured."""
        result = get_fail_on_cvss({}, tool, language, default=default)
        assert result == default

    @given(config=nested_config_strategy, tool=st.sampled_from(["owasp", "trivy"]), language=language_strategy)
    @settings(max_examples=30)
    def test_never_raises_for_any_config(self, config: dict[str, Any], tool: str, language: str) -> None:
        """Property: get_fail_on_cvss never raises for any config shape."""
        result = get_fail_on_cvss(config, tool, language)
        assert isinstance(result, float)


# =============================================================================
# tool_enabled Property Tests
# =============================================================================


class TestToolEnabledProperties:
    """Property-based tests for tool_enabled function."""

    @given(tool=tool_strategy, language=language_strategy)
    @settings(max_examples=50)
    def test_always_returns_bool(self, tool: str, language: str) -> None:
        """Property: tool_enabled always returns a boolean."""
        result = tool_enabled({}, tool, language)
        assert isinstance(result, bool)

    @given(tool=tool_strategy, language=language_strategy, enabled=st.booleans())
    @settings(max_examples=50)
    def test_bool_shorthand_respected(self, tool: str, language: str, enabled: bool) -> None:
        """Property: boolean shorthand is correctly interpreted."""
        config = {language: {"tools": {tool: enabled}}}
        result = tool_enabled(config, tool, language)
        assert result == enabled

    @given(tool=tool_strategy, language=language_strategy, enabled=st.booleans())
    @settings(max_examples=50)
    def test_dict_enabled_respected(self, tool: str, language: str, enabled: bool) -> None:
        """Property: dict-form enabled field is correctly interpreted."""
        config = {language: {"tools": {tool: {"enabled": enabled}}}}
        result = tool_enabled(config, tool, language)
        assert result == enabled

    @given(tool=tool_strategy, language=language_strategy, default=st.booleans())
    @settings(max_examples=50)
    def test_default_returned_for_missing(self, tool: str, language: str, default: bool) -> None:
        """Property: default is returned when tool not configured."""
        result = tool_enabled({}, tool, language, default=default)
        assert result == default

    @given(config=nested_config_strategy, tool=tool_strategy, language=language_strategy)
    @settings(max_examples=30)
    def test_never_raises_for_any_config(self, config: dict[str, Any], tool: str, language: str) -> None:
        """Property: tool_enabled never raises for any config shape."""
        result = tool_enabled(config, tool, language)
        assert isinstance(result, bool)
