"""Tests for tool registry consistency.

These tests ensure tool definitions don't drift across files.
The registry should be the single source of truth.
"""

# TEST-METRICS:

from __future__ import annotations


class TestToolRegistryConsistency:
    """Verify tool registry is consistent across all consumers."""

    def test_python_tool_metrics_match_tools_list(self) -> None:
        """PYTHON_TOOL_METRICS keys must match PYTHON_TOOLS list."""
        from cihub.tools.registry import PYTHON_TOOL_METRICS, PYTHON_TOOLS

        metrics_keys = set(PYTHON_TOOL_METRICS.keys())
        tools_set = set(PYTHON_TOOLS)

        assert metrics_keys == tools_set, (
            f"PYTHON_TOOL_METRICS keys don't match PYTHON_TOOLS.\n"
            f"In metrics but not tools: {metrics_keys - tools_set}\n"
            f"In tools but not metrics: {tools_set - metrics_keys}"
        )

    def test_java_tool_metrics_match_tools_list(self) -> None:
        """JAVA_TOOL_METRICS keys must match JAVA_TOOLS list."""
        from cihub.tools.registry import JAVA_TOOL_METRICS, JAVA_TOOLS

        metrics_keys = set(JAVA_TOOL_METRICS.keys())
        tools_set = set(JAVA_TOOLS)

        assert metrics_keys == tools_set, (
            f"JAVA_TOOL_METRICS keys don't match JAVA_TOOLS.\n"
            f"In metrics but not tools: {metrics_keys - tools_set}\n"
            f"In tools but not metrics: {tools_set - metrics_keys}"
        )

    def test_python_summary_map_covers_tools(self) -> None:
        """PYTHON_SUMMARY_MAP values must be subset of PYTHON_TOOLS."""
        from cihub.tools.registry import PYTHON_SUMMARY_MAP, PYTHON_TOOLS

        summary_tools = set(PYTHON_SUMMARY_MAP.values())
        tools_set = set(PYTHON_TOOLS)

        assert summary_tools <= tools_set, f"PYTHON_SUMMARY_MAP references unknown tools: {summary_tools - tools_set}"

    def test_java_summary_map_covers_tools(self) -> None:
        """JAVA_SUMMARY_MAP values must be subset of JAVA_TOOLS."""
        from cihub.tools.registry import JAVA_SUMMARY_MAP, JAVA_TOOLS

        summary_tools = set(JAVA_SUMMARY_MAP.values())
        tools_set = set(JAVA_TOOLS)

        assert summary_tools <= tools_set, f"JAVA_SUMMARY_MAP references unknown tools: {summary_tools - tools_set}"

    def test_tool_keys_cover_all_run_flags(self) -> None:
        """TOOL_KEYS must include run_* flags for all tools."""
        from cihub.tools.registry import JAVA_TOOLS, PYTHON_TOOLS, TOOL_KEYS

        # Build expected run_* keys from tool names
        expected_run_keys = set()
        for tool in PYTHON_TOOLS:
            expected_run_keys.add(f"run_{tool}")
        for tool in JAVA_TOOLS:
            expected_run_keys.add(f"run_{tool}")

        actual_run_keys = {k for k in TOOL_KEYS if k.startswith("run_")}

        # Check that expected keys are in TOOL_KEYS
        # Note: TOOL_KEYS may have additional keys like use_nvd_api_key
        missing = expected_run_keys - actual_run_keys
        assert not missing, f"TOOL_KEYS missing run_* keys for tools: {missing}"

    def test_python_artifacts_subset_of_tools(self) -> None:
        """PYTHON_ARTIFACTS keys should be subset of PYTHON_TOOLS."""
        from cihub.tools.registry import PYTHON_ARTIFACTS, PYTHON_TOOLS

        artifact_keys = set(PYTHON_ARTIFACTS.keys())
        tools_set = set(PYTHON_TOOLS)

        # Artifacts may not cover all tools (some don't produce artifacts)
        unknown = artifact_keys - tools_set
        assert not unknown, f"PYTHON_ARTIFACTS has unknown tools: {unknown}"

    def test_java_artifacts_subset_of_tools(self) -> None:
        """JAVA_ARTIFACTS keys should be subset of JAVA_TOOLS."""
        from cihub.tools.registry import JAVA_ARTIFACTS, JAVA_TOOLS

        artifact_keys = set(JAVA_ARTIFACTS.keys())
        tools_set = set(JAVA_TOOLS)

        # Artifacts may not cover all tools (some don't produce artifacts)
        unknown = artifact_keys - tools_set
        assert not unknown, f"JAVA_ARTIFACTS has unknown tools: {unknown}"

    def test_lint_metrics_are_valid_tool_metrics(self) -> None:
        """LINT_METRICS should be derivable from TOOL_METRICS."""
        from cihub.tools.registry import (
            JAVA_LINT_METRICS,
            JAVA_TOOL_METRICS,
            PYTHON_LINT_METRICS,
            PYTHON_TOOL_METRICS,
        )

        # Collect all metric names from tool metrics
        python_metric_names = set()
        for metrics in PYTHON_TOOL_METRICS.values():
            for m in metrics:
                # Extract the metric name from paths like "tool_metrics.ruff_errors"
                if "." in m:
                    python_metric_names.add(m.split(".")[-1])

        java_metric_names = set()
        for metrics in JAVA_TOOL_METRICS.values():
            for m in metrics:
                if "." in m:
                    java_metric_names.add(m.split(".")[-1])

        # Lint metrics should be in the collected metrics
        for lint in PYTHON_LINT_METRICS:
            assert lint in python_metric_names, f"Python lint metric '{lint}' not in tool metrics"

        for lint in JAVA_LINT_METRICS:
            assert lint in java_metric_names, f"Java lint metric '{lint}' not in tool metrics"


class TestToolRegistryOrdering:
    """Verify tool list ordering is preserved."""

    def test_python_tools_order_stable(self) -> None:
        """PYTHON_TOOLS order must not change (affects workflow inputs)."""
        from cihub.tools.registry import PYTHON_TOOLS

        # The order is significant for workflow inputs
        expected_order = [
            "pytest",
            "ruff",
            "black",
            "isort",
            "mypy",
            "bandit",
            "pip_audit",
            "sbom",
            "semgrep",
            "trivy",
            "codeql",
            "docker",
            "hypothesis",
            "mutmut",
        ]
        assert PYTHON_TOOLS == expected_order

    def test_java_tools_order_stable(self) -> None:
        """JAVA_TOOLS order must not change (affects workflow inputs)."""
        from cihub.tools.registry import JAVA_TOOLS

        expected_order = [
            "jacoco",
            "pitest",
            "jqwik",
            "checkstyle",
            "spotbugs",
            "pmd",
            "owasp",
            "semgrep",
            "trivy",
            "codeql",
            "sbom",
            "docker",
        ]
        assert JAVA_TOOLS == expected_order


class TestRegistryImportsWork:
    """Verify registry imports are accessible from expected locations."""

    def test_ci_engine_imports_from_registry(self) -> None:
        """ci_engine.py should import tool lists from registry."""
        from cihub.services import ci_engine
        from cihub.tools.registry import JAVA_TOOLS, PYTHON_TOOLS

        # The module should use the same objects from registry
        assert ci_engine.PYTHON_TOOLS is PYTHON_TOOLS
        assert ci_engine.JAVA_TOOLS is JAVA_TOOLS

    def test_discovery_re_exports_tool_keys(self) -> None:
        """discovery.py should re-export _TOOL_KEYS for backward compat."""
        from cihub.services.discovery import _THRESHOLD_KEYS, _TOOL_KEYS
        from cihub.tools.registry import THRESHOLD_KEYS, TOOL_KEYS

        # Re-exports should reference the same objects
        assert _TOOL_KEYS is TOOL_KEYS
        assert _THRESHOLD_KEYS is THRESHOLD_KEYS

    def test_report_validator_imports_from_registry(self) -> None:
        """report_validator package should import metrics from registry."""
        from cihub.services import report_validator
        from cihub.tools.registry import JAVA_TOOL_METRICS, PYTHON_TOOL_METRICS

        # The module should use the same objects from registry
        assert report_validator.PYTHON_TOOL_METRICS is PYTHON_TOOL_METRICS
        assert report_validator.JAVA_TOOL_METRICS is JAVA_TOOL_METRICS


class TestToolAdapters:
    """Tests for tool adapter registry (Part 5.3)."""

    def test_get_tool_adapter_returns_adapter(self) -> None:
        """get_tool_adapter returns adapter for known tools."""
        from cihub.tools.registry import get_tool_adapter

        adapter = get_tool_adapter("pytest", "python")
        assert adapter is not None
        assert adapter.name == "pytest"
        assert adapter.language == "python"

    def test_get_tool_adapter_returns_none_for_unknown(self) -> None:
        """get_tool_adapter returns None for unknown tools."""
        from cihub.tools.registry import get_tool_adapter

        assert get_tool_adapter("unknown_tool", "python") is None
        assert get_tool_adapter("pytest", "unknown_language") is None

    def test_get_tool_runner_args_pytest(self) -> None:
        """pytest adapter extracts fail_fast from config."""
        from cihub.tools.registry import get_tool_runner_args

        config = {"python": {"tools": {"pytest": {"fail_fast": True}}}}
        args = get_tool_runner_args(config, "pytest", "python")
        assert args == {"fail_fast": True}

    def test_get_tool_runner_args_mutmut(self) -> None:
        """mutmut adapter converts timeout_minutes to seconds."""
        from cihub.tools.registry import get_tool_runner_args

        config = {"python": {"tools": {"mutmut": {"timeout_minutes": 30}}}}
        args = get_tool_runner_args(config, "mutmut", "python")
        assert args == {"timeout_seconds": 1800}

    def test_get_tool_runner_args_docker(self) -> None:
        """docker adapter extracts compose_file, health_endpoint, health_timeout."""
        from cihub.tools.registry import get_tool_runner_args

        config = {
            "python": {
                "tools": {
                    "docker": {
                        "compose_file": "docker-compose.test.yml",
                        "health_endpoint": "/health",
                        "health_timeout": 120,
                    }
                }
            }
        }
        args = get_tool_runner_args(config, "docker", "python")
        assert args == {
            "compose_file": "docker-compose.test.yml",
            "health_endpoint": "/health",
            "health_timeout": 120,
        }

    def test_get_tool_runner_args_unknown_tool_returns_empty(self) -> None:
        """Unknown tools return empty dict for runner args."""
        from cihub.tools.registry import get_tool_runner_args

        args = get_tool_runner_args({}, "unknown", "python")
        assert args == {}

    def test_is_tool_gate_enabled_default_true(self) -> None:
        """Unknown tools default to gate enabled."""
        from cihub.tools.registry import is_tool_gate_enabled

        assert is_tool_gate_enabled({}, "unknown_tool", "python") is True

    def test_is_tool_gate_enabled_ruff(self) -> None:
        """ruff gate respects fail_on_error config."""
        from cihub.tools.registry import is_tool_gate_enabled

        # Default: enabled
        assert is_tool_gate_enabled({}, "ruff", "python") is True

        # Explicitly disabled
        config = {"python": {"tools": {"ruff": {"fail_on_error": False}}}}
        assert is_tool_gate_enabled(config, "ruff", "python") is False

    def test_is_tool_gate_enabled_bandit_per_key_defaults(self) -> None:
        """bandit gate uses per-key defaults (high=True, medium=False, low=False)."""
        from cihub.tools.registry import is_tool_gate_enabled

        # Default: high is True, so gate is enabled
        assert is_tool_gate_enabled({}, "bandit", "python") is True

        # Disable high only -> gate disabled (medium/low default False)
        config = {"python": {"tools": {"bandit": {"fail_on_high": False}}}}
        assert is_tool_gate_enabled(config, "bandit", "python") is False

        # Enable medium -> gate enabled
        config = {"python": {"tools": {"bandit": {"fail_on_high": False, "fail_on_medium": True}}}}
        assert is_tool_gate_enabled(config, "bandit", "python") is True

    def test_java_owasp_adapter_includes_build_tool_flag(self) -> None:
        """Java OWASP adapter includes needs_build_tool and use_nvd_api_key."""
        from cihub.tools.registry import get_tool_runner_args

        config = {"java": {"tools": {"owasp": {"use_nvd_api_key": False}}}}
        args = get_tool_runner_args(config, "owasp", "java")
        assert args["needs_build_tool"] is True
        assert args["use_nvd_api_key"] is False
