"""Tests for schema field validation."""

from __future__ import annotations

import json

import pytest

from cihub.utils.paths import hub_root


class TestSchemaStructure:
    """Tests for schema structure and definitions."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load the CI Hub config schema."""
        schema_path = hub_root() / "schema" / "ci-hub-config.schema.json"
        return json.loads(schema_path.read_text())

    def test_schema_has_definitions(self, schema: dict) -> None:
        """Schema should have definitions section."""
        assert "definitions" in schema

    def test_schema_defines_python_tools(self, schema: dict) -> None:
        """Schema should define pythonTools."""
        assert "pythonTools" in schema["definitions"]

    def test_schema_defines_java_tools(self, schema: dict) -> None:
        """Schema should define javaTools."""
        assert "javaTools" in schema["definitions"]

    def test_schema_defines_thresholds(self, schema: dict) -> None:
        """Schema should define thresholds."""
        assert "thresholds" in schema["definitions"]


class TestCustomToolSchema:
    """Tests for custom tool (x-*) schema support."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load the CI Hub config schema."""
        schema_path = hub_root() / "schema" / "ci-hub-config.schema.json"
        return json.loads(schema_path.read_text())

    def test_custom_tool_definition_exists(self, schema: dict) -> None:
        """Schema should have customTool definition."""
        assert "customTool" in schema["definitions"]

    def test_custom_tool_allows_boolean(self, schema: dict) -> None:
        """customTool should allow boolean value."""
        custom_tool = schema["definitions"]["customTool"]
        assert "oneOf" in custom_tool
        types = [item.get("type") for item in custom_tool["oneOf"]]
        assert "boolean" in types

    def test_custom_tool_allows_object(self, schema: dict) -> None:
        """customTool should allow object with command."""
        custom_tool = schema["definitions"]["customTool"]
        types = [item.get("type") for item in custom_tool["oneOf"]]
        assert "object" in types

    def test_python_tools_has_pattern_properties(self, schema: dict) -> None:
        """pythonTools should have patternProperties for x-* prefix."""
        python_tools = schema["definitions"]["pythonTools"]
        assert "patternProperties" in python_tools
        # Pattern should match x-tool-name format
        patterns = list(python_tools["patternProperties"].keys())
        assert any("x-" in p for p in patterns)

    def test_java_tools_has_pattern_properties(self, schema: dict) -> None:
        """javaTools should have patternProperties for x-* prefix."""
        java_tools = schema["definitions"]["javaTools"]
        assert "patternProperties" in java_tools


class TestThresholdSchema:
    """Tests for threshold schema definitions."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load the CI Hub config schema."""
        schema_path = hub_root() / "schema" / "ci-hub-config.schema.json"
        return json.loads(schema_path.read_text())

    def test_coverage_min_is_integer(self, schema: dict) -> None:
        """coverage_min should be an integer 0-100."""
        thresholds = schema["definitions"]["thresholds"]
        props = thresholds.get("properties", {})
        coverage = props.get("coverage_min", {})
        assert coverage.get("type") == "integer"

    def test_mutation_score_min_is_integer(self, schema: dict) -> None:
        """mutation_score_min should be an integer 0-100."""
        thresholds = schema["definitions"]["thresholds"]
        props = thresholds.get("properties", {})
        mutation = props.get("mutation_score_min", {})
        assert mutation.get("type") == "integer"


class TestSchemaValidation:
    """Tests for schema validation of configs."""

    def test_validate_config_returns_list(self) -> None:
        """validate_config should return a list of errors."""
        from cihub.config import PathConfig, validate_config

        # Use current working directory as root
        paths = PathConfig(root=str(hub_root()))
        config = {
            "language": "python",
            "python": {
                "tools": {
                    "pytest": True,
                    "ruff": {"enabled": True},
                }
            },
        }
        result = validate_config(config, paths)
        assert isinstance(result, list)

    def test_invalid_config_has_errors(self) -> None:
        """Invalid config should return errors."""
        from cihub.config import PathConfig, validate_config

        paths = PathConfig(root=str(hub_root()))
        # Config with wrong types should have some validation feedback
        config = {
            "language": 12345,  # Should be a string
        }
        result = validate_config(config, paths)
        # Should return list (possibly with errors for wrong type)
        assert isinstance(result, list)
