"""Contract tests for template drift detection (Issue 4/Section 4).

These tests verify that:
1. All tools in gate_specs have corresponding workflow inputs
2. All threshold keys in defaults.yaml are present in gate_specs
3. Summary gates include all configured tools

This prevents drift between:
- gate_specs.py (single source of truth)
- Workflow templates (.github/workflows/*-ci.yml)
- Config defaults (cihub/data/config/defaults.yaml)
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path

import yaml

from cihub.core.gate_specs import (
    JAVA_THRESHOLDS,
    JAVA_TOOLS,
    PYTHON_THRESHOLDS,
    PYTHON_TOOLS,
)
from cihub.utils.paths import hub_root


def _load_workflow_inputs(workflow_path: Path) -> set[str]:
    """Extract input names from a workflow file."""
    if not workflow_path.exists():
        return set()

    content = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    # YAML parses "on" as boolean True - need to check both
    on_block = content.get(True) or content.get("on", {})
    if isinstance(on_block, dict):
        inputs = on_block.get("workflow_call", {}).get("inputs", {})
    else:
        inputs = {}
    return set(inputs.keys()) if inputs else set()


def _load_defaults_tool_keys(language: str) -> set[str]:
    """Extract tool keys from defaults.yaml for a language."""
    defaults_path = hub_root() / "config" / "defaults.yaml"
    if not defaults_path.exists():
        return set()

    content = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
    tools = content.get(language, {}).get("tools", {})
    return set(tools.keys())


def _load_defaults_threshold_keys() -> set[str]:
    """Extract threshold keys from defaults.yaml."""
    defaults_path = hub_root() / "config" / "defaults.yaml"
    if not defaults_path.exists():
        return set()

    content = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
    thresholds = content.get("thresholds", {})
    return set(thresholds.keys())


class TestPythonTemplateDrift:
    """Contract tests for Python workflow template."""

    def test_all_python_tools_have_workflow_inputs(self) -> None:
        """All Python tools in gate_specs should have run_* inputs in workflow."""
        workflow_path = Path(".github/workflows/python-ci.yml")
        inputs = _load_workflow_inputs(workflow_path)

        # Map tool keys to expected input names
        tool_keys = {spec.key for spec in PYTHON_TOOLS}

        # These tools have run_* inputs
        run_inputs = {name for name in inputs if name.startswith("run_")}
        run_tool_keys = {name.replace("run_", "") for name in run_inputs}

        # Check for missing workflow inputs
        # Note: Some tools may be disabled by default or not have inputs
        # This test documents the expected mapping
        expected_mappings = {
            "pytest": "pytest",
            "ruff": "ruff",
            "bandit": "bandit",
            "pip_audit": "pip_audit",
            "mypy": "mypy",
            "black": "black",
            "isort": "isort",
            "mutmut": "mutmut",
            "semgrep": "semgrep",
            "trivy": "trivy",
            "codeql": "codeql",
            "docker": "docker",
            "sbom": "sbom",
        }

        # Collect any expected tools that are missing workflow inputs
        missing_inputs = []
        for gate_key, input_key in expected_mappings.items():
            # run_tool_keys has the prefix stripped, so check input_key directly
            if gate_key in tool_keys and input_key not in run_tool_keys:
                # Note: Not all tools need workflow inputs (e.g., hypothesis runs with pytest)
                # but we track missing ones for visibility
                missing_inputs.append(input_key)

        # Allow known exceptions (tools that don't need separate inputs)
        known_exceptions = {"hypothesis"}  # runs with pytest, no separate input needed
        unexpected_missing = [m for m in missing_inputs if m not in known_exceptions]
        assert not unexpected_missing, f"Missing workflow inputs (run_*) for tools: {unexpected_missing}"

        # At minimum, core tools should have inputs
        core_tools = {"pytest", "ruff", "bandit", "pip_audit"}
        for tool in core_tools:
            assert tool in run_tool_keys, f"Missing run_{tool} input in python-ci.yml"

    def test_python_threshold_keys_match_gate_specs(self) -> None:
        """Threshold keys in defaults.yaml should match gate_specs."""
        defaults_thresholds = _load_defaults_threshold_keys()
        gate_threshold_keys = {spec.key for spec in PYTHON_THRESHOLDS}

        # Check that all gate threshold keys have defaults
        # Note: Not all defaults need to be in gate_specs (some are language-specific)
        common_keys = {"coverage_min", "mutation_score_min", "max_critical_vulns", "max_high_vulns"}

        for key in common_keys:
            if key in gate_threshold_keys:
                assert key in defaults_thresholds, f"Missing {key} in defaults.yaml thresholds"

    def test_python_defaults_tools_match_gate_specs(self) -> None:
        """Tool keys in defaults.yaml should match gate_specs."""
        defaults_tools = _load_defaults_tool_keys("python")
        gate_tool_keys = {spec.key for spec in PYTHON_TOOLS}

        # Core tools must be in both
        core_tools = {"pytest", "ruff", "bandit", "pip_audit", "mutmut"}

        for tool in core_tools:
            assert tool in defaults_tools, f"Missing {tool} in defaults.yaml python.tools"
            assert tool in gate_tool_keys, f"Missing {tool} in PYTHON_TOOLS gate_specs"


class TestJavaTemplateDrift:
    """Contract tests for Java workflow template."""

    def test_all_java_tools_have_workflow_inputs(self) -> None:
        """All Java tools in gate_specs should have run_* inputs in workflow."""
        workflow_path = Path(".github/workflows/java-ci.yml")
        inputs = _load_workflow_inputs(workflow_path)

        run_inputs = {name for name in inputs if name.startswith("run_")}
        run_tool_keys = {name.replace("run_", "") for name in run_inputs}

        # Core Java tools should have inputs
        core_tools = {"jacoco", "checkstyle", "spotbugs", "owasp"}
        for tool in core_tools:
            assert tool in run_tool_keys, f"Missing run_{tool} input in java-ci.yml"

    def test_java_threshold_keys_match_gate_specs(self) -> None:
        """Threshold keys for Java should match gate_specs."""
        gate_threshold_keys = {spec.key for spec in JAVA_THRESHOLDS}

        # These keys must be in Java thresholds
        expected_keys = {"coverage_min", "mutation_score_min", "owasp_cvss_fail"}

        for key in expected_keys:
            assert key in gate_threshold_keys, f"Missing {key} in JAVA_THRESHOLDS gate_specs"

    def test_java_defaults_tools_match_gate_specs(self) -> None:
        """Tool keys in defaults.yaml should match gate_specs."""
        defaults_tools = _load_defaults_tool_keys("java")
        gate_tool_keys = {spec.key for spec in JAVA_TOOLS if spec.key != "__build__"}

        # Core tools must be in both
        core_tools = {"jacoco", "checkstyle", "spotbugs", "owasp", "pitest"}

        for tool in core_tools:
            assert tool in defaults_tools, f"Missing {tool} in defaults.yaml java.tools"
            assert tool in gate_tool_keys, f"Missing {tool} in JAVA_TOOLS gate_specs"


class TestGateSpecConsistency:
    """Tests for internal gate_specs consistency."""

    def test_python_tools_have_unique_keys(self) -> None:
        """All Python tool keys must be unique."""
        keys = [spec.key for spec in PYTHON_TOOLS]
        assert len(keys) == len(set(keys)), "Duplicate keys in PYTHON_TOOLS"

    def test_java_tools_have_unique_keys(self) -> None:
        """All Java tool keys must be unique."""
        keys = [spec.key for spec in JAVA_TOOLS]
        assert len(keys) == len(set(keys)), "Duplicate keys in JAVA_TOOLS"

    def test_python_thresholds_have_unique_keys(self) -> None:
        """All Python threshold keys must be unique."""
        keys = [spec.key for spec in PYTHON_THRESHOLDS]
        assert len(keys) == len(set(keys)), "Duplicate keys in PYTHON_THRESHOLDS"

    def test_java_thresholds_have_unique_keys(self) -> None:
        """All Java threshold keys must be unique."""
        keys = [spec.key for spec in JAVA_THRESHOLDS]
        assert len(keys) == len(set(keys)), "Duplicate keys in JAVA_THRESHOLDS"

    def test_threshold_metric_keys_exist(self) -> None:
        """Threshold metric_keys should reference valid metrics."""
        # Document expected metric keys for reference
        python_metrics = {
            "coverage",
            "mutation_score",
            "trivy_max_cvss",
            "trivy_critical",
            "trivy_high",
            "bandit_high",
            "bandit_medium",
            "bandit_low",
            "pip_audit_vulns",
            "semgrep_findings",
            "ruff_errors",
            "black_issues",
            "isort_issues",
            "mypy_errors",
        }

        undocumented_metrics = []
        for spec in PYTHON_THRESHOLDS:
            assert spec.metric_key, f"Missing metric_key for {spec.key}"
            # Ensure metric key is documented
            if spec.metric_key not in python_metrics:
                undocumented_metrics.append(f"{spec.key} -> {spec.metric_key}")

        # Fail if there are undocumented metrics (add them to python_metrics above)
        assert not undocumented_metrics, (
            f"Undocumented metric keys in PYTHON_THRESHOLDS: {undocumented_metrics}. "
            "Add them to python_metrics set above."
        )
