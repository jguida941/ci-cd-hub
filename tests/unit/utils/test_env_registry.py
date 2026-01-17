"""Tests for environment variable registry (cihub/utils/env_registry.py).

Tests cover:
- EnvVarDef dataclass structure and immutability
- Registry lookup functions
- Category filtering
- Consistency with actual environment variable usage
"""

from __future__ import annotations

import pytest

from cihub.utils.env_registry import (
    CATEGORY_ORDER,
    ENV_REGISTRY,
    EnvVarDef,
    get_all_env_vars,
    get_env_var,
    get_env_vars_by_category,
)


# =============================================================================
# EnvVarDef Dataclass Tests
# =============================================================================


class TestEnvVarDef:
    """Tests for EnvVarDef dataclass."""

    def test_envvardef_is_frozen(self) -> None:
        """EnvVarDef instances are immutable."""
        env_var = EnvVarDef(
            name="TEST_VAR",
            var_type="bool",
            default="false",
            category="Debug",
            description="Test variable",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            env_var.name = "NEW_NAME"  # type: ignore[misc]

    def test_envvardef_has_required_fields(self) -> None:
        """EnvVarDef has all required fields."""
        env_var = EnvVarDef(
            name="TEST_VAR",
            var_type="string",
            default="default_value",
            category="Auth",
            description="A test variable",
        )

        assert env_var.name == "TEST_VAR"
        assert env_var.var_type == "string"
        assert env_var.default == "default_value"
        assert env_var.category == "Auth"
        assert env_var.description == "A test variable"

    def test_envvardef_valid_var_types(self) -> None:
        """EnvVarDef accepts valid var_type values."""
        for var_type in ["bool", "string", "int"]:
            env_var = EnvVarDef(
                name="TEST",
                var_type=var_type,  # type: ignore[arg-type]
                default="",
                category="Debug",
                description="test",
            )
            assert env_var.var_type == var_type

    def test_envvardef_valid_categories(self) -> None:
        """EnvVarDef accepts valid category values."""
        valid_categories = ["Debug", "Report", "Auth", "Context", "Notify", "Tools"]
        for category in valid_categories:
            env_var = EnvVarDef(
                name="TEST",
                var_type="bool",
                default="",
                category=category,  # type: ignore[arg-type]
                description="test",
            )
            assert env_var.category == category


# =============================================================================
# Registry Lookup Tests
# =============================================================================


class TestEnvRegistry:
    """Tests for ENV_REGISTRY dictionary."""

    def test_registry_is_dict(self) -> None:
        """ENV_REGISTRY is a dictionary."""
        assert isinstance(ENV_REGISTRY, dict)

    def test_registry_not_empty(self) -> None:
        """ENV_REGISTRY contains environment variables."""
        assert len(ENV_REGISTRY) > 0

    def test_registry_keys_are_strings(self) -> None:
        """ENV_REGISTRY keys are variable names (strings)."""
        for key in ENV_REGISTRY:
            assert isinstance(key, str)

    def test_registry_values_are_envvardef(self) -> None:
        """ENV_REGISTRY values are EnvVarDef instances."""
        for value in ENV_REGISTRY.values():
            assert isinstance(value, EnvVarDef)

    def test_registry_key_matches_name(self) -> None:
        """Registry key matches the EnvVarDef.name field."""
        for key, value in ENV_REGISTRY.items():
            assert key == value.name


class TestGetEnvVar:
    """Tests for get_env_var lookup function."""

    def test_returns_envvardef_for_known_var(self) -> None:
        """get_env_var returns EnvVarDef for known variable."""
        result = get_env_var("CIHUB_DEBUG")

        assert result is not None
        assert isinstance(result, EnvVarDef)
        assert result.name == "CIHUB_DEBUG"

    def test_returns_none_for_unknown_var(self) -> None:
        """get_env_var returns None for unknown variable."""
        result = get_env_var("NONEXISTENT_VARIABLE_XYZ")

        assert result is None

    def test_is_case_sensitive(self) -> None:
        """get_env_var lookup is case sensitive."""
        result_upper = get_env_var("CIHUB_DEBUG")
        result_lower = get_env_var("cihub_debug")

        assert result_upper is not None
        assert result_lower is None


class TestGetAllEnvVars:
    """Tests for get_all_env_vars function."""

    def test_returns_list(self) -> None:
        """get_all_env_vars returns a list."""
        result = get_all_env_vars()

        assert isinstance(result, list)

    def test_returns_all_variables(self) -> None:
        """get_all_env_vars returns all registered variables."""
        result = get_all_env_vars()

        assert len(result) == len(ENV_REGISTRY)

    def test_returns_envvardef_instances(self) -> None:
        """get_all_env_vars returns EnvVarDef instances."""
        result = get_all_env_vars()

        for item in result:
            assert isinstance(item, EnvVarDef)

    def test_returns_new_list_each_call(self) -> None:
        """get_all_env_vars returns a new list each call (safe to modify)."""
        result1 = get_all_env_vars()
        result2 = get_all_env_vars()

        assert result1 is not result2


class TestGetEnvVarsByCategory:
    """Tests for get_env_vars_by_category function."""

    def test_returns_list(self) -> None:
        """get_env_vars_by_category returns a list."""
        result = get_env_vars_by_category("Debug")

        assert isinstance(result, list)

    def test_filters_by_category(self) -> None:
        """get_env_vars_by_category only returns vars of specified category."""
        result = get_env_vars_by_category("Debug")

        for env_var in result:
            assert env_var.category == "Debug"

    def test_returns_empty_for_unknown_category(self) -> None:
        """get_env_vars_by_category returns empty list for unknown category."""
        result = get_env_vars_by_category("NonexistentCategory")

        assert result == []

    def test_debug_category_has_variables(self) -> None:
        """Debug category contains expected variables."""
        result = get_env_vars_by_category("Debug")

        names = [v.name for v in result]
        assert "CIHUB_DEBUG" in names
        assert "CIHUB_VERBOSE" in names

    def test_auth_category_has_variables(self) -> None:
        """Auth category contains expected variables."""
        result = get_env_vars_by_category("Auth")

        names = [v.name for v in result]
        assert "GH_TOKEN" in names or "GITHUB_TOKEN" in names


# =============================================================================
# Category Order Tests
# =============================================================================


class TestCategoryOrder:
    """Tests for CATEGORY_ORDER list."""

    def test_category_order_is_list(self) -> None:
        """CATEGORY_ORDER is a list."""
        assert isinstance(CATEGORY_ORDER, list)

    def test_category_order_not_empty(self) -> None:
        """CATEGORY_ORDER contains categories."""
        assert len(CATEGORY_ORDER) > 0

    def test_category_order_contains_expected_categories(self) -> None:
        """CATEGORY_ORDER contains all expected categories."""
        expected = {"Debug", "Report", "Auth", "Context", "Notify", "Tools"}

        assert set(CATEGORY_ORDER) == expected

    def test_all_registered_categories_in_order(self) -> None:
        """All categories used in registry are in CATEGORY_ORDER."""
        all_vars = get_all_env_vars()
        used_categories = {v.category for v in all_vars}

        for category in used_categories:
            assert category in CATEGORY_ORDER


# =============================================================================
# Specific Environment Variable Tests
# =============================================================================


class TestKnownEnvironmentVariables:
    """Tests for specific known environment variables."""

    def test_cihub_debug_exists(self) -> None:
        """CIHUB_DEBUG is registered."""
        env_var = get_env_var("CIHUB_DEBUG")

        assert env_var is not None
        assert env_var.var_type == "bool"
        assert env_var.default == "false"
        assert env_var.category == "Debug"

    def test_cihub_verbose_exists(self) -> None:
        """CIHUB_VERBOSE is registered."""
        env_var = get_env_var("CIHUB_VERBOSE")

        assert env_var is not None
        assert env_var.var_type == "bool"
        assert env_var.category == "Debug"

    def test_cihub_emit_triage_exists(self) -> None:
        """CIHUB_EMIT_TRIAGE is registered."""
        env_var = get_env_var("CIHUB_EMIT_TRIAGE")

        assert env_var is not None
        assert env_var.var_type == "bool"
        assert env_var.category == "Debug"

    def test_gh_token_exists(self) -> None:
        """GH_TOKEN is registered."""
        env_var = get_env_var("GH_TOKEN")

        assert env_var is not None
        assert env_var.var_type == "string"
        assert env_var.category == "Auth"

    def test_github_token_exists(self) -> None:
        """GITHUB_TOKEN is registered."""
        env_var = get_env_var("GITHUB_TOKEN")

        assert env_var is not None
        assert env_var.var_type == "string"
        assert env_var.category == "Auth"

    def test_cihub_write_github_summary_exists(self) -> None:
        """CIHUB_WRITE_GITHUB_SUMMARY is registered."""
        env_var = get_env_var("CIHUB_WRITE_GITHUB_SUMMARY")

        assert env_var is not None
        assert env_var.var_type == "bool"
        assert env_var.category == "Report"

    def test_cihub_owner_exists(self) -> None:
        """CIHUB_OWNER is registered."""
        env_var = get_env_var("CIHUB_OWNER")

        assert env_var is not None
        assert env_var.var_type == "string"
        assert env_var.category == "Context"

    def test_cihub_repo_exists(self) -> None:
        """CIHUB_REPO is registered."""
        env_var = get_env_var("CIHUB_REPO")

        assert env_var is not None
        assert env_var.var_type == "string"
        assert env_var.category == "Context"


# =============================================================================
# Documentation Generation Compatibility Tests
# =============================================================================


class TestDocumentationCompatibility:
    """Tests ensuring registry is compatible with documentation generation."""

    def test_all_vars_have_non_empty_description(self) -> None:
        """All variables have non-empty descriptions."""
        for env_var in get_all_env_vars():
            assert env_var.description, f"{env_var.name} has empty description"
            assert len(env_var.description) > 10, f"{env_var.name} description too short"

    def test_all_vars_have_valid_category(self) -> None:
        """All variables have valid categories."""
        for env_var in get_all_env_vars():
            assert env_var.category in CATEGORY_ORDER, (
                f"{env_var.name} has invalid category: {env_var.category}"
            )

    def test_all_vars_have_valid_type(self) -> None:
        """All variables have valid var_type."""
        valid_types = {"bool", "string", "int"}
        for env_var in get_all_env_vars():
            assert env_var.var_type in valid_types, (
                f"{env_var.name} has invalid type: {env_var.var_type}"
            )

    def test_env_var_names_follow_convention(self) -> None:
        """Environment variable names follow UPPERCASE_WITH_UNDERSCORES convention."""
        for env_var in get_all_env_vars():
            # Skip wildcard pattern vars like CIHUB_RUN_*
            if "*" in env_var.name:
                continue
            assert env_var.name == env_var.name.upper(), (
                f"{env_var.name} should be uppercase"
            )
            assert " " not in env_var.name, f"{env_var.name} should not contain spaces"
