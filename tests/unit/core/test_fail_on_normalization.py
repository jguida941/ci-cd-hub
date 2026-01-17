"""Tests for fail_on_* normalization helpers.

These tests validate the fail_on_* helper functions and ensure
schema-code alignment for fail_on_* defaults.
"""

# TEST-METRICS:

from __future__ import annotations

import json

import pytest

from cihub.config.normalize import (
    _FAIL_ON_DEFAULTS,
    _FAIL_ON_KEY_MAP,
    _TOOL_FAIL_ON_DEFAULTS,
    get_fail_on_cvss,
    get_fail_on_flag,
)
from cihub.utils.paths import hub_root


# =============================================================================
# get_fail_on_flag Tests
# =============================================================================


class TestGetFailOnFlag:
    """Tests for get_fail_on_flag helper."""

    @pytest.mark.parametrize(
        "tool,language,flag,expected",
        [
            # Bandit severity flags - Python
            ("bandit", "python", "fail_on_high", True),
            ("bandit", "python", "fail_on_medium", False),
            ("bandit", "python", "fail_on_low", False),
            # Trivy severity flags - Python
            ("trivy", "python", "fail_on_critical", False),
            ("trivy", "python", "fail_on_high", False),
            # Trivy severity flags - Java
            ("trivy", "java", "fail_on_critical", False),
            ("trivy", "java", "fail_on_high", False),
            # Docker missing compose - both languages
            ("docker", "python", "fail_on_missing_compose", False),
            ("docker", "java", "fail_on_missing_compose", False),
        ],
        ids=[
            "bandit_high_default",
            "bandit_medium_default",
            "bandit_low_default",
            "trivy_critical_python",
            "trivy_high_python",
            "trivy_critical_java",
            "trivy_high_java",
            "docker_missing_python",
            "docker_missing_java",
        ],
    )
    def test_defaults_align_with_schema(
        self, tool: str, language: str, flag: str, expected: bool
    ) -> None:
        """Default values should match schema defaults."""
        config: dict = {}  # Empty config uses defaults
        result = get_fail_on_flag(config, tool, language, flag)
        assert result == expected

    @pytest.mark.parametrize(
        "tool,language,expected",
        [
            ("codeql", "python", True),
            ("codeql", "java", True),
            ("docker", "python", True),
            ("docker", "java", True),
            ("ruff", "python", True),
            ("spotbugs", "java", True),
            ("checkstyle", "java", True),
            ("pmd", "java", False),  # PMD defaults to False
            ("semgrep", "python", False),
            ("semgrep", "java", False),
            ("black", "python", False),
            ("isort", "python", False),
            ("pip_audit", "python", True),
        ],
        ids=[
            "codeql_python",
            "codeql_java",
            "docker_python",
            "docker_java",
            "ruff_python",
            "spotbugs_java",
            "checkstyle_java",
            "pmd_java",
            "semgrep_python",
            "semgrep_java",
            "black_python",
            "isort_python",
            "pip_audit_python",
        ],
    )
    def test_canonical_mapping_defaults(
        self, tool: str, language: str, expected: bool
    ) -> None:
        """Canonical mapping should return correct defaults."""
        config: dict = {}
        result = get_fail_on_flag(config, tool, language)
        assert result == expected

    def test_config_overrides_default(self) -> None:
        """Config value should override default."""
        config = {
            "python": {
                "tools": {
                    "bandit": {
                        "enabled": True,
                        "fail_on_high": False,  # Override default True
                    }
                }
            }
        }
        result = get_fail_on_flag(config, "bandit", "python", "fail_on_high")
        assert result is False

    def test_explicit_default_override(self) -> None:
        """Explicit default parameter should override schema default."""
        config: dict = {}
        result = get_fail_on_flag(
            config, "trivy", "python", "fail_on_critical", default=True
        )
        assert result is True  # Explicit default wins over schema default (False)

    def test_boolean_tool_config(self) -> None:
        """Boolean tool config should still work."""
        config = {"python": {"tools": {"bandit": True}}}  # Boolean shorthand
        result = get_fail_on_flag(config, "bandit", "python", "fail_on_high")
        # Boolean True means enabled; fail_on defaults still apply
        assert result is True  # Default for fail_on_high

    def test_missing_language_block(self) -> None:
        """Missing language block should use defaults."""
        config = {"java": {"tools": {}}}  # No python block
        result = get_fail_on_flag(config, "bandit", "python", "fail_on_high")
        assert result is True  # Default

    def test_missing_tools_block(self) -> None:
        """Missing tools block should use defaults."""
        config = {"python": {"version": "3.12"}}  # No tools block
        result = get_fail_on_flag(config, "bandit", "python", "fail_on_high")
        assert result is True  # Default

    def test_unknown_tool_returns_true(self) -> None:
        """Unknown tool without flag returns True (fail-safe default)."""
        config: dict = {}
        result = get_fail_on_flag(config, "unknown_tool", "python")
        assert result is True


# =============================================================================
# get_fail_on_cvss Tests
# =============================================================================


class TestGetFailOnCvss:
    """Tests for get_fail_on_cvss helper."""

    @pytest.mark.parametrize(
        "tool,language,expected",
        [
            ("owasp", "java", 7.0),
            ("trivy", "java", 7.0),
            ("trivy", "python", 7.0),
        ],
        ids=["owasp_java", "trivy_java", "trivy_python"],
    )
    def test_default_cvss_threshold(
        self, tool: str, language: str, expected: float
    ) -> None:
        """Default CVSS threshold should be 7.0 (aligned with schema)."""
        config: dict = {}
        result = get_fail_on_cvss(config, tool, language)
        assert result == expected

    def test_config_overrides_default(self) -> None:
        """Config value should override default."""
        config = {
            "java": {
                "tools": {
                    "owasp": {
                        "enabled": True,
                        "fail_on_cvss": 9.0,
                    }
                }
            }
        }
        result = get_fail_on_cvss(config, "owasp", "java")
        assert result == 9.0

    def test_explicit_default_override(self) -> None:
        """Explicit default parameter should work."""
        config: dict = {}
        result = get_fail_on_cvss(config, "trivy", "python", default=8.5)
        assert result == 8.5

    def test_integer_value_returned_as_float(self) -> None:
        """Integer config value should be returned as float."""
        config = {
            "java": {
                "tools": {
                    "owasp": {
                        "fail_on_cvss": 8,  # Integer
                    }
                }
            }
        }
        result = get_fail_on_cvss(config, "owasp", "java")
        assert result == 8.0
        assert isinstance(result, float)

    def test_missing_language_block(self) -> None:
        """Missing language block should use default."""
        config = {"python": {}}
        result = get_fail_on_cvss(config, "owasp", "java")
        assert result == 7.0


# =============================================================================
# Schema-Code Alignment Tests
# =============================================================================


class TestSchemaCodeAlignment:
    """Tests to ensure schema defaults match code defaults."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load the CI Hub config schema."""
        schema_path = hub_root() / "schema" / "ci-hub-config.schema.json"
        return json.loads(schema_path.read_text())

    def _get_schema_tool_default(
        self, schema: dict, definition: str, tool: str, field: str
    ) -> bool | int | float | None:
        """Extract default value from schema for a tool field."""
        tools_def = schema.get("definitions", {}).get(definition, {})
        props = tools_def.get("properties", {})
        tool_schema = props.get(tool, {})

        # Handle oneOf pattern (boolean | object)
        if "oneOf" in tool_schema:
            for option in tool_schema["oneOf"]:
                if option.get("type") == "object":
                    tool_props = option.get("properties", {})
                    field_schema = tool_props.get(field, {})
                    return field_schema.get("default")
        return None

    @pytest.mark.parametrize(
        "tool,field,code_default",
        [
            ("bandit", "fail_on_high", True),
            ("bandit", "fail_on_medium", False),
            ("bandit", "fail_on_low", False),
            ("black", "fail_on_format_issues", False),
            ("isort", "fail_on_issues", False),
            ("pip_audit", "fail_on_vuln", True),
            ("ruff", "fail_on_error", True),
            ("trivy", "fail_on_critical", False),
            ("trivy", "fail_on_high", False),
        ],
        ids=[
            "bandit_high",
            "bandit_medium",
            "bandit_low",
            "black_format",
            "isort_issues",
            "pip_audit_vuln",
            "ruff_error",
            "trivy_critical",
            "trivy_high",
        ],
    )
    def test_python_tools_schema_alignment(
        self, schema: dict, tool: str, field: str, code_default: bool
    ) -> None:
        """Python tool fail_on_* defaults should match schema."""
        schema_default = self._get_schema_tool_default(
            schema, "pythonTools", tool, field
        )
        assert (
            schema_default == code_default
        ), f"Schema default for {tool}.{field} ({schema_default}) != code default ({code_default})"

    @pytest.mark.parametrize(
        "tool,field,code_default",
        [
            ("checkstyle", "fail_on_violation", True),
            ("pmd", "fail_on_violation", False),
            ("spotbugs", "fail_on_error", True),
            ("trivy", "fail_on_critical", False),
            ("trivy", "fail_on_high", False),
            ("owasp", "fail_on_cvss", 7),
        ],
        ids=[
            "checkstyle_violation",
            "pmd_violation",
            "spotbugs_error",
            "trivy_critical",
            "trivy_high",
            "owasp_cvss",
        ],
    )
    def test_java_tools_schema_alignment(
        self, schema: dict, tool: str, field: str, code_default: bool | int
    ) -> None:
        """Java tool fail_on_* defaults should match schema."""
        schema_default = self._get_schema_tool_default(
            schema, "javaTools", tool, field
        )
        assert (
            schema_default == code_default
        ), f"Schema default for {tool}.{field} ({schema_default}) != code default ({code_default})"


# =============================================================================
# Mapping Completeness Tests
# =============================================================================


class TestMappingCompleteness:
    """Tests to ensure fail_on_* mappings are complete."""

    def test_all_mapped_tools_have_defaults(self) -> None:
        """Every tool in _FAIL_ON_KEY_MAP should have a corresponding default."""
        for tool, flag_key in _FAIL_ON_KEY_MAP.items():
            # Either general default or tool-specific default should exist
            has_default = (
                flag_key in _FAIL_ON_DEFAULTS
                or tool in _TOOL_FAIL_ON_DEFAULTS
            )
            assert has_default, f"Tool {tool} (flag: {flag_key}) has no default"

    def test_fail_on_defaults_keys_are_valid(self) -> None:
        """All keys in _FAIL_ON_DEFAULTS should be valid fail_on_* patterns."""
        for key in _FAIL_ON_DEFAULTS:
            assert key.startswith("fail_on_"), f"Invalid key: {key}"

    def test_tool_specific_defaults_reference_valid_keys(self) -> None:
        """Tool-specific defaults should reference valid fail_on_* keys."""
        for tool, defaults in _TOOL_FAIL_ON_DEFAULTS.items():
            for key in defaults:
                assert key.startswith("fail_on_"), f"Invalid key {key} for {tool}"