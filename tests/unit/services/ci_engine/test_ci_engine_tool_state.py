"""Tests for CI engine tool state management functions.

Split from test_ci_engine.py for better organization.
Tests: _tool_enabled, _tool_gate_enabled, _get_env_name, _get_env_value,
       _warn_reserved_features, _set_tool_enabled, _apply_force_all_tools
"""

from __future__ import annotations

from cihub.services.ci_engine import (
    JAVA_TOOLS,
    PYTHON_TOOLS,
    _apply_force_all_tools,
    _get_env_name,
    _get_env_value,
    _set_tool_enabled,
    _tool_enabled,
    _tool_gate_enabled,
    _warn_reserved_features,
)


class TestToolEnabled:
    """Tests for _tool_enabled function."""

    def test_enabled_with_bool_true(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        assert _tool_enabled(config, "pytest", "python") is True

    def test_disabled_with_bool_false(self) -> None:
        config = {"python": {"tools": {"pytest": False}}}
        assert _tool_enabled(config, "pytest", "python") is False

    def test_enabled_with_dict(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_enabled(config, "pytest", "python") is True

    def test_disabled_with_dict(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": False}}}}
        assert _tool_enabled(config, "pytest", "python") is False

    def test_missing_tool(self) -> None:
        config = {"python": {"tools": {}}}
        assert _tool_enabled(config, "pytest", "python") is False


class TestToolGateEnabled:
    """Tests for _tool_gate_enabled function - gate configuration."""

    def test_python_ruff_gate(self) -> None:
        config = {"python": {"tools": {"ruff": {"fail_on_error": False}}}}
        assert _tool_gate_enabled(config, "ruff", "python") is False

    def test_python_black_gate(self) -> None:
        config = {"python": {"tools": {"black": {"fail_on_format_issues": False}}}}
        assert _tool_gate_enabled(config, "black", "python") is False

    def test_python_isort_gate(self) -> None:
        config = {"python": {"tools": {"isort": {"fail_on_issues": False}}}}
        assert _tool_gate_enabled(config, "isort", "python") is False

    def test_python_bandit_gate(self) -> None:
        config = {"python": {"tools": {"bandit": {"fail_on_high": False}}}}
        assert _tool_gate_enabled(config, "bandit", "python") is False

    def test_python_bandit_gate_medium_enabled(self) -> None:
        config = {"python": {"tools": {"bandit": {"fail_on_high": False, "fail_on_medium": True}}}}
        assert _tool_gate_enabled(config, "bandit", "python") is True

    def test_python_bandit_gate_low_enabled(self) -> None:
        config = {"python": {"tools": {"bandit": {"fail_on_low": True}}}}
        assert _tool_gate_enabled(config, "bandit", "python") is True

    def test_python_pip_audit_gate(self) -> None:
        config = {"python": {"tools": {"pip_audit": {"fail_on_vuln": False}}}}
        assert _tool_gate_enabled(config, "pip_audit", "python") is False

    def test_python_semgrep_gate(self) -> None:
        config = {"python": {"tools": {"semgrep": {"fail_on_findings": False}}}}
        assert _tool_gate_enabled(config, "semgrep", "python") is False

    def test_python_trivy_gate_critical(self) -> None:
        config = {"python": {"tools": {"trivy": {"fail_on_critical": False, "fail_on_high": False}}}}
        assert _tool_gate_enabled(config, "trivy", "python") is False

    def test_java_checkstyle_gate(self) -> None:
        config = {"java": {"tools": {"checkstyle": {"fail_on_violation": False}}}}
        assert _tool_gate_enabled(config, "checkstyle", "java") is False

    def test_java_spotbugs_gate(self) -> None:
        config = {"java": {"tools": {"spotbugs": {"fail_on_error": False}}}}
        assert _tool_gate_enabled(config, "spotbugs", "java") is False

    def test_java_pmd_gate(self) -> None:
        config = {"java": {"tools": {"pmd": {"fail_on_violation": False}}}}
        assert _tool_gate_enabled(config, "pmd", "java") is False

    def test_defaults_to_true(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_gate_enabled(config, "pytest", "python") is True

    def test_non_dict_entry_returns_true(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        assert _tool_gate_enabled(config, "pytest", "python") is True


class TestGetEnvName:
    """Tests for _get_env_name function."""

    def test_returns_config_value(self) -> None:
        config = {"mykey": "MY_ENV_VAR"}
        result = _get_env_name(config, "mykey", "DEFAULT")
        assert result == "MY_ENV_VAR"

    def test_returns_default_when_missing(self) -> None:
        config: dict = {}
        result = _get_env_name(config, "mykey", "DEFAULT")
        assert result == "DEFAULT"

    def test_strips_whitespace(self) -> None:
        config = {"mykey": "  MY_VAR  "}
        result = _get_env_name(config, "mykey", "DEFAULT")
        assert result == "MY_VAR"


class TestGetEnvValue:
    """Tests for _get_env_value function."""

    def test_returns_primary_value(self) -> None:
        env = {"PRIMARY": "value1", "FALLBACK": "value2"}
        result = _get_env_value(env, "PRIMARY", ["FALLBACK"])
        assert result == "value1"

    def test_returns_fallback_when_primary_missing(self) -> None:
        env = {"FALLBACK": "value2"}
        result = _get_env_value(env, "PRIMARY", ["FALLBACK"])
        assert result == "value2"

    def test_returns_none_when_no_match(self) -> None:
        env: dict = {}
        result = _get_env_value(env, "PRIMARY", ["FALLBACK"])
        assert result is None


class TestWarnReservedFeatures:
    """Tests for _warn_reserved_features function."""

    def test_warns_for_enabled_dict(self) -> None:
        config = {"chaos": {"enabled": True}}
        problems: list = []
        _warn_reserved_features(config, problems)
        assert len(problems) == 1
        assert "CIHUB-CI-RESERVED-FEATURE" in problems[0]["code"]

    def test_warns_for_enabled_bool(self) -> None:
        config = {"dr_drill": True}
        problems: list = []
        _warn_reserved_features(config, problems)
        assert len(problems) == 1

    def test_no_warning_for_disabled(self) -> None:
        config = {"chaos": {"enabled": False}}
        problems: list = []
        _warn_reserved_features(config, problems)
        assert len(problems) == 0


class TestSetToolEnabled:
    """Tests for _set_tool_enabled function."""

    def test_sets_enabled_on_dict_entry(self) -> None:
        config = {"python": {"tools": {"pytest": {"min_coverage": 80}}}}
        _set_tool_enabled(config, "python", "pytest", False)
        assert config["python"]["tools"]["pytest"]["enabled"] is False

    def test_creates_dict_for_non_dict_entry(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        _set_tool_enabled(config, "python", "pytest", False)
        assert config["python"]["tools"]["pytest"]["enabled"] is False

    def test_creates_structure_from_scratch(self) -> None:
        config: dict = {}
        _set_tool_enabled(config, "python", "pytest", True)
        assert config["python"]["tools"]["pytest"]["enabled"] is True


class TestApplyForceAllTools:
    """Tests for _apply_force_all_tools function."""

    def test_enables_all_python_tools(self) -> None:
        config = {"repo": {"force_all_tools": True}, "python": {"tools": {}}}
        _apply_force_all_tools(config, "python")
        for tool in PYTHON_TOOLS:
            assert config["python"]["tools"][tool]["enabled"] is True

    def test_enables_all_java_tools(self) -> None:
        config = {"repo": {"force_all_tools": True}, "java": {"tools": {}}}
        _apply_force_all_tools(config, "java")
        for tool in JAVA_TOOLS:
            assert config["java"]["tools"][tool]["enabled"] is True

    def test_does_nothing_when_disabled(self) -> None:
        config = {"repo": {"force_all_tools": False}, "python": {"tools": {}}}
        _apply_force_all_tools(config, "python")
        assert config["python"]["tools"] == {}
