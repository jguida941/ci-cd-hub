"""Tests for schema sync functionality.

Tests the schema extraction, defaults/fallbacks generation, and alignment checking.
"""

# TEST-METRICS:
#   Coverage: 80.4%

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

OPTIONAL_FEATURE_KEYS = [
    "chaos",
    "canary",
    "dr_drill",
    "cache_sentinel",
    "runner_isolation",
    "supply_chain",
    "egress_control",
    "telemetry",
    "kyverno",
]


class TestSchemaExtraction:
    """Tests for schema extraction utilities."""

    def test_load_schema_returns_dict(self):
        """Schema loads successfully as a dict."""
        from cihub.config.schema_extract import load_schema

        schema = load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema or "$id" in schema

    def test_extract_all_defaults_returns_expected_keys(self):
        """extract_all_defaults returns expected top-level keys."""
        from cihub.config.schema_extract import extract_all_defaults

        defaults = extract_all_defaults()

        # Should have language sections
        assert "java" in defaults
        assert "python" in defaults

        # Should have config sections
        assert "thresholds" in defaults or "reports" in defaults

    def test_extract_java_tools(self):
        """Java tools are extracted correctly."""
        from cihub.config.schema_extract import extract_all_defaults

        defaults = extract_all_defaults()
        java = defaults.get("java", {})

        assert "tools" in java
        tools = java["tools"]

        # Should have key Java tools
        assert "jacoco" in tools
        assert "checkstyle" in tools
        assert "spotbugs" in tools

    def test_extract_python_tools(self):
        """Python tools are extracted correctly."""
        from cihub.config.schema_extract import extract_all_defaults

        defaults = extract_all_defaults()
        python = defaults.get("python", {})

        assert "tools" in python
        tools = python["tools"]

        # Should have key Python tools
        assert "pytest" in tools
        assert "ruff" in tools
        assert "bandit" in tools

    def test_generate_fallbacks_dict_returns_defaults(self):
        """generate_fallbacks_dict returns schema-derived defaults."""
        from cihub.config.schema_extract import generate_fallbacks_dict

        fallbacks = generate_fallbacks_dict()

        # Should have key sections
        assert "java" in fallbacks
        assert "python" in fallbacks
        assert "repo" in fallbacks
        assert "thresholds" in fallbacks
        assert "gates" in fallbacks

        # Should have cihub CLI config
        assert "cihub" in fallbacks

    def test_optional_feature_defaults_follow_schema(self) -> None:
        """Optional feature defaults are derived from schema."""
        from cihub.config.schema_extract import extract_all_defaults, load_schema

        schema = load_schema()
        defaults = extract_all_defaults(schema)
        for key in OPTIONAL_FEATURE_KEYS:
            prop = schema["properties"][key]
            enabled_default = None
            for option in prop.get("oneOf", []):
                if option.get("type") == "object":
                    enabled_default = option.get("properties", {}).get("enabled", {}).get("default")
                    break
            assert enabled_default is not None
            assert defaults[key]["enabled"] == enabled_default

    def test_gates_and_reports_defaults_follow_schema(self) -> None:
        """gates/reports defaults come from the schema."""
        from cihub.config.schema_extract import extract_all_defaults, load_schema

        schema = load_schema()
        defaults = extract_all_defaults(schema)

        gates_default = schema["properties"]["gates"]["properties"]["require_run_or_fail"]["default"]
        assert defaults["gates"]["require_run_or_fail"] == gates_default

        reports_default = schema["definitions"]["reports"]["properties"]["retention_days"]["default"]
        assert defaults["reports"]["retention_days"] == reports_default

    def test_hub_ci_threshold_overrides_default_follow_schema(self) -> None:
        """hub_ci threshold overrides default is derived from the schema."""
        from cihub.config.schema_extract import extract_all_defaults, load_schema

        schema = load_schema()
        defaults = extract_all_defaults(schema)

        overrides_default = (
            schema["definitions"]["hubCi"]["oneOf"][1]["properties"]["thresholds"]["properties"]["overrides"]["default"]
        )
        assert defaults["hub_ci"]["thresholds"]["overrides"] == overrides_default

    def test_fallbacks_defaults_follow_schema(self) -> None:
        """Fallback defaults are derived from the schema."""
        from cihub.config.schema_extract import generate_fallbacks_dict, load_schema

        schema = load_schema()
        fallbacks = generate_fallbacks_dict(schema)

        gates_default = schema["properties"]["gates"]["properties"]["require_run_or_fail"]["default"]
        assert fallbacks["gates"]["require_run_or_fail"] == gates_default

        reports_default = schema["definitions"]["reports"]["properties"]["retention_days"]["default"]
        assert fallbacks["reports"]["retention_days"] == reports_default

        overrides_default = (
            schema["definitions"]["hubCi"]["oneOf"][1]["properties"]["thresholds"]["properties"]["overrides"]["default"]
        )
        assert fallbacks["hub_ci"]["thresholds"]["overrides"] == overrides_default

        for key in OPTIONAL_FEATURE_KEYS:
            prop = schema["properties"][key]
            enabled_default = None
            for option in prop.get("oneOf", []):
                if option.get("type") == "object":
                    enabled_default = option.get("properties", {}).get("enabled", {}).get("default")
                    break
            assert enabled_default is not None
            assert fallbacks[key]["enabled"] == enabled_default

    def test_compare_with_current_detects_mismatch(self):
        """compare_with_current detects value differences."""
        from cihub.config.schema_extract import compare_with_current

        schema_defaults = {"foo": {"bar": 1}}
        current = {"foo": {"bar": 2}}

        drifts = compare_with_current(schema_defaults, current)
        assert len(drifts) > 0
        assert any("bar" in d for d in drifts)

    def test_compare_with_current_detects_missing_key(self):
        """compare_with_current detects missing keys."""
        from cihub.config.schema_extract import compare_with_current

        schema_defaults = {"foo": {"bar": 1, "baz": 2}}
        current = {"foo": {"bar": 1}}

        drifts = compare_with_current(schema_defaults, current)
        assert len(drifts) > 0
        assert any("baz" in d for d in drifts)

    def test_compare_with_current_passes_on_match(self):
        """compare_with_current returns empty list when aligned."""
        from cihub.config.schema_extract import compare_with_current

        data = {"foo": {"bar": 1}}
        drifts = compare_with_current(data, data)
        assert drifts == []


class TestSchemaSync:
    """Tests for schema sync commands."""

    def test_check_schema_alignment_returns_command_result(self):
        """check_schema_alignment returns proper CommandResult."""
        from cihub.commands.schema_sync import check_schema_alignment
        from cihub.types import CommandResult

        result = check_schema_alignment()
        assert isinstance(result, CommandResult)
        assert result.exit_code in (0, 1)

    def test_generate_defaults_yaml_dry_run(self):
        """generate_defaults_yaml dry run produces content."""
        from cihub.commands.schema_sync import generate_defaults_yaml

        result = generate_defaults_yaml(dry_run=True)
        assert result.exit_code == 0
        assert "content" in result.data
        assert "keys" in result.data

    def test_generate_fallbacks_py_dry_run(self):
        """generate_fallbacks_py dry run produces content."""
        from cihub.commands.schema_sync import generate_fallbacks_py

        result = generate_fallbacks_py(dry_run=True)
        assert result.exit_code == 0
        assert "content" in result.data
        assert "FALLBACK_DEFAULTS" in result.data["content"]

    def test_format_python_dict_escapes_strings(self) -> None:
        """_format_python_dict escapes quotes/backslashes/newlines."""
        from cihub.commands.schema_sync import _format_python_dict

        # Test that quotes, backslashes, and newlines are properly escaped
        # Input: literal quote, single backslash, actual newline
        payload = {"message": 'line "one"\\two\nthree'}
        module = f"FALLBACK_DEFAULTS = {_format_python_dict(payload)}"
        namespace: dict[str, object] = {}
        exec(module, namespace)
        # After round-trip through code generation and exec, should match original
        assert namespace["FALLBACK_DEFAULTS"] == payload

    def test_generate_defaults_yaml_writes_file(self, tmp_path: Path):
        """generate_defaults_yaml writes valid YAML."""
        import yaml

        from cihub.commands.schema_sync import generate_defaults_yaml

        output_path = tmp_path / "defaults.yaml"
        result = generate_defaults_yaml(output_path=output_path)

        assert result.exit_code == 0
        assert output_path.exists()

        # Verify valid YAML
        content = yaml.safe_load(output_path.read_text())
        assert isinstance(content, dict)
        assert "java" in content or "python" in content

    def test_generate_fallbacks_py_writes_file(self, tmp_path: Path):
        """generate_fallbacks_py writes valid Python."""
        from cihub.commands.schema_sync import generate_fallbacks_py

        output_path = tmp_path / "fallbacks.py"
        result = generate_fallbacks_py(output_path=output_path)

        assert result.exit_code == 0
        assert output_path.exists()

        # Verify it's importable Python
        content = output_path.read_text()
        assert "FALLBACK_DEFAULTS" in content
        assert "dict[str, Any]" in content

        # Compile to verify syntax
        compile(content, str(output_path), "exec")

    def test_run_schema_sync_routes_correctly(self):
        """run_schema_sync routes to correct subcommand."""
        from cihub.commands.schema_sync import run_schema_sync

        # check subcommand
        result = run_schema_sync("check")
        assert result.exit_code in (0, 1)

        # generate-defaults dry run
        result = run_schema_sync("generate-defaults", dry_run=True)
        assert result.exit_code == 0
        assert "content" in result.data

        # unknown subcommand
        result = run_schema_sync("invalid")
        assert result.exit_code == 1

    def test_run_schema_sync_with_output_path(self, tmp_path: Path):
        """run_schema_sync respects output path."""
        from cihub.commands.schema_sync import run_schema_sync

        output_path = tmp_path / "custom_defaults.yaml"
        result = run_schema_sync("generate-defaults", output=output_path)

        assert result.exit_code == 0
        assert output_path.exists()


class TestIntegration:
    """Integration tests for schema sync with other modules."""

    def test_fallbacks_import_still_works(self):
        """Current fallbacks.py is still importable."""
        from cihub.config.fallbacks import FALLBACK_DEFAULTS

        assert isinstance(FALLBACK_DEFAULTS, dict)
        assert "java" in FALLBACK_DEFAULTS
        assert "python" in FALLBACK_DEFAULTS

    def test_schema_path_exists(self):
        """Schema file exists at expected location."""
        from cihub.config.schema_extract import SCHEMA_PATH

        assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"

    def test_generated_fallbacks_are_valid_python(self):
        """Generated fallbacks are syntactically valid Python."""
        from cihub.commands.schema_sync import generate_fallbacks_py

        result = generate_fallbacks_py(dry_run=True)
        content = result.data["content"]

        # Should compile without errors
        compile(content, "<generated>", "exec")

        # Should contain valid dict
        assert "FALLBACK_DEFAULTS: dict[str, Any] = {" in content

    def test_extract_respects_tool_enabled_defaults(self):
        """Tools with enabled=false default are captured."""
        from cihub.config.schema_extract import extract_all_defaults

        defaults = extract_all_defaults()

        # mutmut should be disabled by default in Python
        python_tools = defaults.get("python", {}).get("tools", {})
        if "mutmut" in python_tools:
            mutmut = python_tools["mutmut"]
            if isinstance(mutmut, dict):
                assert mutmut.get("enabled") is False

    def test_thresholds_have_expected_defaults(self):
        """Threshold defaults match expected values."""
        from cihub.config.schema_extract import extract_all_defaults

        defaults = extract_all_defaults()
        thresholds = defaults.get("thresholds", {})

        # Standard coverage/mutation thresholds
        if "coverage_min" in thresholds:
            assert thresholds["coverage_min"] == 70
        if "mutation_score_min" in thresholds:
            assert thresholds["mutation_score_min"] == 70
