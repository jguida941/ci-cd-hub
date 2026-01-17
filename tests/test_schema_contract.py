"""Schema contract tests - ensure code output matches JSON schemas.

These tests prevent drift between:
1. Report builders (ci_report.py) → cihub/data/schema/ci-report.v2.json
2. Config loaders → cihub/data/schema/ci-hub-config.schema.json

If code emits fields not in schema (or vice versa), tests fail immediately.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema
import pytest

from cihub.core.ci_report import RunContext, build_java_report, build_python_report
from cihub.core.gate_specs import get_thresholds
from cihub.tools.registry import JAVA_TOOLS, PYTHON_TOOLS
from cihub.utils.paths import hub_root

SCHEMA_DIR = hub_root() / "schema"
REPORT_SCHEMA_PATH = SCHEMA_DIR / "ci-report.v2.json"
CONFIG_SCHEMA_PATH = SCHEMA_DIR / "ci-hub-config.schema.json"
TRIAGE_SCHEMA_PATH = SCHEMA_DIR / "triage.schema.json"


@pytest.fixture
def report_schema() -> dict[str, Any]:
    """Load the ci-report.v2.json schema."""
    return json.loads(REPORT_SCHEMA_PATH.read_text())


@pytest.fixture
def config_schema() -> dict[str, Any]:
    """Load the ci-hub-config.schema.json schema."""
    return json.loads(CONFIG_SCHEMA_PATH.read_text())


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample RunContext for report building."""
    return RunContext(
        repository="test/repo",
        branch="main",
        run_id="12345",
        run_number="1",
        commit="a" * 40,
        correlation_id="corr-123",
        workflow_ref="test/workflow@main",
        workdir=".",
        build_tool="maven",
        retention_days=30,
        project_type="single-module",
        docker_compose_file=None,
        docker_health_endpoint=None,
    )


@pytest.fixture
def sample_python_config() -> dict[str, Any]:
    """Sample Python config for report building."""
    return {
        "python": {
            "version": "3.12",
            "tools": {
                "pytest": {"enabled": True},
                "ruff": {"enabled": True},
                "bandit": {"enabled": True},
                "trivy": {"enabled": True},
            },
        },
        "thresholds": {
            "coverage_min": 70,
            "mutation_score_min": 60,
            "trivy_cvss_fail": 7.0,
        },
    }


@pytest.fixture
def sample_java_config() -> dict[str, Any]:
    """Sample Java config for report building."""
    return {
        "java": {
            "version": "21",
            "tools": {
                "jacoco": {"enabled": True},
                "checkstyle": {"enabled": True},
                "owasp": {"enabled": True},
                "trivy": {"enabled": True},
            },
        },
        "thresholds": {
            "coverage_min": 70,
            "mutation_score_min": 60,
            "owasp_cvss_fail": 7.0,
            "trivy_cvss_fail": 7.0,
        },
    }


@pytest.fixture
def sample_tool_results() -> dict[str, dict[str, Any]]:
    """Sample tool results with all metric types."""
    return {
        "pytest": {
            "success": True,
            "metrics": {
                "tests_passed": 100,
                "tests_failed": 0,
                "tests_skipped": 5,
                "tests_runtime_seconds": 12.5,
                "coverage": 85,
                "coverage_lines_covered": 850,
                "coverage_lines_total": 1000,
            },
        },
        "mutmut": {
            "success": True,
            "metrics": {
                "mutation_score": 75,
                "mutation_killed": 75,
                "mutation_survived": 25,
            },
        },
        "ruff": {"success": True, "metrics": {"ruff_errors": 0}},
        "mypy": {"success": True, "metrics": {"mypy_errors": 0}},
        "bandit": {
            "success": True,
            "metrics": {"bandit_high": 0, "bandit_medium": 0, "bandit_low": 1},
        },
        "black": {"success": True, "metrics": {"black_issues": 0}},
        "isort": {"success": True, "metrics": {"isort_issues": 0}},
        "pip_audit": {"success": True, "metrics": {"pip_audit_vulns": 0}},
        "semgrep": {"success": True, "metrics": {"semgrep_findings": 0}},
        "trivy": {
            "success": True,
            "metrics": {
                "trivy_critical": 0,
                "trivy_high": 1,
                "trivy_medium": 2,
                "trivy_low": 3,
                "trivy_max_cvss": 6.5,
            },
        },
        "docker": {
            "success": True,
            "metrics": {"docker_missing_compose": False, "docker_health_ok": True},
        },
        "build": {
            "success": True,
            "metrics": {
                "tests_passed": 50,
                "tests_failed": 0,
                "tests_skipped": 2,
                "tests_runtime_seconds": 30.0,
            },
        },
        "jacoco": {
            "success": True,
            "metrics": {
                "coverage": 80,
                "coverage_lines_covered": 800,
                "coverage_lines_total": 1000,
            },
        },
        "pitest": {
            "success": True,
            "metrics": {
                "mutation_score": 70,
                "mutation_killed": 70,
                "mutation_survived": 30,
            },
        },
        "checkstyle": {"success": True, "metrics": {"checkstyle_issues": 0}},
        "spotbugs": {"success": True, "metrics": {"spotbugs_issues": 0}},
        "pmd": {"success": True, "metrics": {"pmd_violations": 0}},
        "owasp": {
            "success": True,
            "metrics": {
                "owasp_critical": 0,
                "owasp_high": 1,
                "owasp_medium": 2,
                "owasp_low": 3,
                "owasp_max_cvss": 7.2,
            },
        },
    }


@pytest.fixture
def sample_tools_configured() -> dict[str, bool]:
    """Sample tools_configured dict."""
    return {
        "pytest": True,
        "ruff": True,
        "bandit": True,
        "pip_audit": True,
        "mypy": True,
        "black": True,
        "isort": True,
        "mutmut": True,
        "semgrep": True,
        "trivy": True,
        "docker": True,
        "codeql": False,
        "sbom": False,
        "jacoco": True,
        "checkstyle": True,
        "spotbugs": True,
        "pmd": True,
        "owasp": True,
        "pitest": True,
        "jqwik": False,
    }


@pytest.fixture
def sample_tools_ran() -> dict[str, bool]:
    """Sample tools_ran dict."""
    return {
        "pytest": True,
        "ruff": True,
        "bandit": True,
        "pip_audit": True,
        "mypy": True,
        "black": True,
        "isort": True,
        "mutmut": True,
        "semgrep": True,
        "trivy": True,
        "docker": True,
        "codeql": False,
        "sbom": False,
        "build": True,
        "jacoco": True,
        "checkstyle": True,
        "spotbugs": True,
        "pmd": True,
        "owasp": True,
        "pitest": True,
        "jqwik": False,
    }


@pytest.fixture
def sample_tools_success() -> dict[str, bool]:
    """Sample tools_success dict."""
    return {
        "pytest": True,
        "ruff": True,
        "bandit": True,
        "pip_audit": True,
        "mypy": True,
        "black": True,
        "isort": True,
        "mutmut": True,
        "semgrep": True,
        "trivy": True,
        "docker": True,
        "codeql": False,
        "sbom": False,
        "build": True,
        "jacoco": True,
        "checkstyle": True,
        "spotbugs": True,
        "pmd": True,
        "owasp": True,
        "pitest": True,
        "jqwik": False,
    }


class TestReportSchemaContract:
    """Validate that report builders emit schema-compliant JSON."""

    def test_python_report_validates_against_schema(
        self,
        report_schema: dict[str, Any],
        sample_python_config: dict[str, Any],
        sample_tool_results: dict[str, dict[str, Any]],
        sample_tools_configured: dict[str, bool],
        sample_tools_ran: dict[str, bool],
        sample_tools_success: dict[str, bool],
        sample_context: RunContext,
    ) -> None:
        """Python report must validate against ci-report.v2.json schema."""
        thresholds = sample_python_config.get("thresholds", {})

        report = build_python_report(
            config=sample_python_config,
            tool_results=sample_tool_results,
            tools_configured=sample_tools_configured,
            tools_ran=sample_tools_ran,
            tools_success=sample_tools_success,
            thresholds=thresholds,
            context=sample_context,
            tools_require_run={"pytest": True, "bandit": True},
        )

        # This will raise ValidationError if report doesn't match schema
        jsonschema.validate(instance=report, schema=report_schema)

    def test_java_report_validates_against_schema(
        self,
        report_schema: dict[str, Any],
        sample_java_config: dict[str, Any],
        sample_tool_results: dict[str, dict[str, Any]],
        sample_tools_configured: dict[str, bool],
        sample_tools_ran: dict[str, bool],
        sample_tools_success: dict[str, bool],
        sample_context: RunContext,
    ) -> None:
        """Java report must validate against ci-report.v2.json schema."""
        thresholds = sample_java_config.get("thresholds", {})

        report = build_java_report(
            config=sample_java_config,
            tool_results=sample_tool_results,
            tools_configured=sample_tools_configured,
            tools_ran=sample_tools_ran,
            tools_success=sample_tools_success,
            thresholds=thresholds,
            context=sample_context,
            tools_require_run={"jacoco": True, "owasp": True},
        )

        # This will raise ValidationError if report doesn't match schema
        jsonschema.validate(instance=report, schema=report_schema)

    def test_schema_requires_all_mandatory_fields(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """Verify schema enforces required fields."""
        incomplete_report = {"schema_version": "2.0"}

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(instance=incomplete_report, schema=report_schema)

        # Should complain about missing required fields
        assert "required" in str(exc_info.value) or "is a required property" in str(exc_info.value)

    def test_schema_rejects_unknown_fields_in_tool_metrics(
        self,
        report_schema: dict[str, Any],
        sample_python_config: dict[str, Any],
        sample_tool_results: dict[str, dict[str, Any]],
        sample_tools_configured: dict[str, bool],
        sample_tools_ran: dict[str, bool],
        sample_tools_success: dict[str, bool],
        sample_context: RunContext,
    ) -> None:
        """Schema should reject unknown fields (additionalProperties: false)."""
        thresholds = sample_python_config.get("thresholds", {})

        report = build_python_report(
            config=sample_python_config,
            tool_results=sample_tool_results,
            tools_configured=sample_tools_configured,
            tools_ran=sample_tools_ran,
            tools_success=sample_tools_success,
            thresholds=thresholds,
            context=sample_context,
        )

        # Add an unknown field
        report["tool_metrics"]["unknown_new_field"] = 999

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(instance=report, schema=report_schema)

        assert "additional" in str(exc_info.value).lower()

    def test_schema_allows_custom_tools_in_status_maps(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """Schema should allow x-* custom tools in tools_ran/configured/success maps."""
        # Minimal valid report with custom tool
        report = {
            "schema_version": "2.0",
            "metadata": {
                "workflow_version": "1.0.0",
                "workflow_ref": "test/workflow@main",
                "generated_at": "2026-01-12T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2026-01-12T00:00:00Z",
            "results": {
                "coverage": 80,
                "mutation_score": 70,
                "tests_passed": 100,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": {
                "pytest": True,
                "x-my-custom-linter": True,  # Custom tool
                "x-internal_tool": True,  # Another custom tool
            },
            "tools_configured": {
                "pytest": True,
                "x-my-custom-linter": True,
            },
            "tools_success": {
                "pytest": True,
                "x-my-custom-linter": True,
            },
        }

        # Should NOT raise - custom x-* tools are allowed
        jsonschema.validate(instance=report, schema=report_schema)

    def test_schema_rejects_invalid_custom_tool_names(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """Schema should reject custom tools without x- prefix."""
        report = {
            "schema_version": "2.0",
            "metadata": {
                "workflow_version": "1.0.0",
                "workflow_ref": "test/workflow@main",
                "generated_at": "2026-01-12T00:00:00Z",
            },
            "repository": "test/repo",
            "run_id": "123",
            "run_number": "1",
            "commit": "a" * 40,
            "branch": "main",
            "timestamp": "2026-01-12T00:00:00Z",
            "results": {
                "coverage": 80,
                "mutation_score": 70,
                "tests_passed": 100,
                "tests_failed": 0,
                "critical_vulns": 0,
                "high_vulns": 0,
                "medium_vulns": 0,
            },
            "tool_metrics": {},
            "tools_ran": {
                "pytest": True,
                "my-custom-linter": True,  # Missing x- prefix - should fail
            },
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=report_schema)


class TestSchemaCompleteness:
    """Ensure schemas cover all fields emitted by code."""

    def test_tool_metrics_schema_covers_all_python_metrics(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """All Python tool_metrics keys must be in schema."""
        schema_metrics = set(report_schema["properties"]["tool_metrics"]["properties"].keys())

        # These are all the metrics Python reports can emit
        expected_python_metrics = {
            "ruff_errors",
            "mypy_errors",
            "bandit_high",
            "bandit_medium",
            "bandit_low",
            "black_issues",
            "isort_issues",
            "pip_audit_vulns",
            "semgrep_findings",
            "trivy_critical",
            "trivy_high",
            "trivy_medium",
            "trivy_low",
            "trivy_max_cvss",
            "docker_missing_compose",
            "docker_health_ok",
        }

        missing = expected_python_metrics - schema_metrics
        assert not missing, f"Schema missing Python metrics: {missing}"

    def test_tool_metrics_schema_covers_all_java_metrics(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """All Java tool_metrics keys must be in schema."""
        schema_metrics = set(report_schema["properties"]["tool_metrics"]["properties"].keys())

        # These are all the metrics Java reports can emit
        expected_java_metrics = {
            "checkstyle_issues",
            "spotbugs_issues",
            "pmd_violations",
            "owasp_critical",
            "owasp_high",
            "owasp_medium",
            "owasp_low",
            "owasp_max_cvss",
            "semgrep_findings",
            "trivy_critical",
            "trivy_high",
            "trivy_medium",
            "trivy_low",
            "trivy_max_cvss",
            "docker_missing_compose",
            "docker_health_ok",
        }

        missing = expected_java_metrics - schema_metrics
        assert not missing, f"Schema missing Java metrics: {missing}"

    def test_tools_ran_schema_covers_all_tools(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """All tool keys must be in tools_ran schema."""
        # tools_ran now uses $ref to definitions/toolStatusMap
        tools_ran = report_schema["properties"]["tools_ran"]
        if "allOf" in tools_ran:
            # Follow the $ref: "#/definitions/toolStatusMap"
            schema_tools = set(report_schema["definitions"]["toolStatusMap"]["properties"].keys())
        else:
            # Legacy: direct properties
            schema_tools = set(tools_ran["properties"].keys())

        # Union of tool keys across languages, plus special-case build.
        expected_tools = set(PYTHON_TOOLS) | set(JAVA_TOOLS) | {"build"}

        missing = expected_tools - schema_tools
        assert not missing, f"Schema missing tools: {missing}"

    def test_thresholds_schema_covers_all_gate_specs(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """All threshold keys defined in gate_specs must be allowed by the schema."""
        schema_thresholds = set(report_schema["properties"]["thresholds"]["properties"].keys())
        expected_thresholds = {s.key for s in get_thresholds("python")} | {s.key for s in get_thresholds("java")}
        missing = expected_thresholds - schema_thresholds
        assert not missing, f"Schema missing thresholds: {missing}"

    def test_tools_require_run_exists_in_schema(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """tools_require_run must exist in schema."""
        assert "tools_require_run" in report_schema["properties"], (
            "Schema missing tools_require_run - require_run_or_fail policy won't work!"
        )

    def test_cvss_fields_exist_in_schema(
        self,
        report_schema: dict[str, Any],
    ) -> None:
        """CVSS enforcement fields must exist in schema."""
        tool_metrics = report_schema["properties"]["tool_metrics"]["properties"]
        thresholds = report_schema["properties"]["thresholds"]["properties"]

        # Metrics
        assert "owasp_max_cvss" in tool_metrics, "Schema missing owasp_max_cvss"
        assert "trivy_max_cvss" in tool_metrics, "Schema missing trivy_max_cvss"

        # Thresholds
        assert "owasp_cvss_fail" in thresholds, "Schema missing owasp_cvss_fail"
        assert "trivy_cvss_fail" in thresholds, "Schema missing trivy_cvss_fail"


class TestConfigSchemaContract:
    """Validate config schema covers required fields."""

    def test_gates_section_exists(
        self,
        config_schema: dict[str, Any],
    ) -> None:
        """gates section must exist for require_run_or_fail policy."""
        assert "gates" in config_schema["properties"], (
            "Config schema missing 'gates' section - require_run_or_fail won't work!"
        )

    def test_gates_has_require_run_or_fail(
        self,
        config_schema: dict[str, Any],
    ) -> None:
        """gates.require_run_or_fail must exist."""
        gates = config_schema["properties"]["gates"]["properties"]
        assert "require_run_or_fail" in gates, "Config schema missing gates.require_run_or_fail"

    def test_gates_has_tool_defaults(
        self,
        config_schema: dict[str, Any],
    ) -> None:
        """gates.tool_defaults must exist with per-tool settings."""
        gates = config_schema["properties"]["gates"]["properties"]
        assert "tool_defaults" in gates, "Config schema missing gates.tool_defaults"

        tool_defaults = gates["tool_defaults"]["properties"]
        # Keep schema tool defaults in lock-step with the tool registry.
        expected_tools = set(PYTHON_TOOLS) | set(JAVA_TOOLS)

        for tool in expected_tools:
            assert tool in tool_defaults, f"gates.tool_defaults missing {tool}"


class TestHardenRunnerSchemaContract:
    """Validate harden_runner configuration in schema."""

    @pytest.fixture
    def minimal_python_config(self) -> dict[str, Any]:
        """Minimal valid Python config for harden_runner tests."""
        return {
            "language": "python",
            "repo": {"owner": "test", "name": "test-repo"},
            "python": {"version": "3.12"},
        }

    def test_harden_runner_exists_in_schema(
        self,
        config_schema: dict[str, Any],
    ) -> None:
        """harden_runner section must exist in schema."""
        assert "harden_runner" in config_schema["properties"], (
            "Config schema missing 'harden_runner' section for workflow security"
        )

    def test_harden_runner_accepts_boolean(
        self,
        config_schema: dict[str, Any],
        minimal_python_config: dict[str, Any],
    ) -> None:
        """harden_runner: true/false should validate."""
        validator = jsonschema.Draft7Validator(config_schema)

        # Boolean true should be valid
        config_true = {**minimal_python_config, "harden_runner": True}
        errors = list(validator.iter_errors(config_true))
        assert not errors, f"harden_runner: true should be valid: {errors}"

        # Boolean false should be valid
        config_false = {**minimal_python_config, "harden_runner": False}
        errors = list(validator.iter_errors(config_false))
        assert not errors, f"harden_runner: false should be valid: {errors}"

    def test_harden_runner_accepts_policy_object(
        self,
        config_schema: dict[str, Any],
        minimal_python_config: dict[str, Any],
    ) -> None:
        """harden_runner: {policy: "audit|block|disabled"} should validate."""
        validator = jsonschema.Draft7Validator(config_schema)

        for policy in ["audit", "block", "disabled"]:
            config = {**minimal_python_config, "harden_runner": {"policy": policy}}
            errors = list(validator.iter_errors(config))
            assert not errors, f"harden_runner.policy: {policy} should be valid: {errors}"

    def test_harden_runner_rejects_invalid_policy(
        self,
        config_schema: dict[str, Any],
        minimal_python_config: dict[str, Any],
    ) -> None:
        """harden_runner: {policy: "invalid"} should fail validation."""
        validator = jsonschema.Draft7Validator(config_schema)

        config = {**minimal_python_config, "harden_runner": {"policy": "invalid"}}
        errors = list(validator.iter_errors(config))
        assert errors, "harden_runner.policy: 'invalid' should fail validation"


@pytest.fixture
def triage_schema() -> dict[str, Any]:
    """Load the triage.schema.json schema."""
    return json.loads(TRIAGE_SCHEMA_PATH.read_text())


class TestTriageSchemaContract:
    """Validate triage bundle output against schema."""

    def test_triage_schema_exists(self) -> None:
        """Ensure triage schema file exists."""
        assert TRIAGE_SCHEMA_PATH.exists(), f"Missing schema: {TRIAGE_SCHEMA_PATH}"

    def test_triage_schema_is_valid_json(self) -> None:
        """Triage schema must be valid JSON."""
        content = TRIAGE_SCHEMA_PATH.read_text()
        json.loads(content)  # Will raise if invalid

    def test_sample_triage_validates(self, triage_schema: dict[str, Any]) -> None:
        """Sample triage bundle must validate against schema."""
        sample_triage = {
            "schema_version": "cihub-triage-v2",
            "generated_at": "2026-01-06T12:00:00Z",
            "run": {
                "correlation_id": "test-123",
                "repo": "test/repo",
                "commit_sha": "abc123",
                "branch": "main",
            },
            "paths": {
                "output_dir": "/tmp/test",
                "report_path": "/tmp/test/report.json",
                "summary_path": "/tmp/test/summary.md",
            },
            "summary": {
                "overall_status": "passed",
                "failure_count": 0,
                "warning_count": 0,
            },
            "tool_evidence": [
                {
                    "tool": "pytest",
                    "configured": True,
                    "ran": True,
                    "require_run": True,
                    "success": True,
                    "status": "passed",
                    "explanation": "Tests passed",
                    "metrics": {"tests_passed": 100},
                    "has_artifacts": True,
                }
            ],
            "evidence_issues": [],
            "failures": [],
            "warnings": [],
            "notes": [],
        }

        # This will raise ValidationError if bundle doesn't match schema
        jsonschema.validate(instance=sample_triage, schema=triage_schema)

    def test_triage_schema_requires_mandatory_fields(self, triage_schema: dict[str, Any]) -> None:
        """Verify schema enforces required fields."""
        incomplete = {"schema_version": "cihub-triage-v2"}

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=incomplete, schema=triage_schema)

    def test_triage_schema_validates_schema_version_pattern(self, triage_schema: dict[str, Any]) -> None:
        """schema_version must match pattern cihub-triage-vN."""
        invalid = {
            "schema_version": "wrong-format",  # Invalid pattern
            "generated_at": "2026-01-06T12:00:00Z",
            "run": {},
            "summary": {"overall_status": "passed", "failure_count": 0},
            "failures": [],
        }

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(instance=invalid, schema=triage_schema)

        assert "pattern" in str(exc_info.value).lower()

    def test_triage_schema_validates_overall_status_enum(self, triage_schema: dict[str, Any]) -> None:
        """overall_status must be a valid enum value (passed/failed/success/failure)."""
        invalid = {
            "schema_version": "cihub-triage-v2",
            "generated_at": "2026-01-06T12:00:00Z",
            "run": {},
            "summary": {"overall_status": "unknown", "failure_count": 0},  # Invalid
            "failures": [],
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=triage_schema)

    def test_triage_schema_validates_severity_enum(self, triage_schema: dict[str, Any]) -> None:
        """failure severity must be in allowed enum."""
        invalid = {
            "schema_version": "cihub-triage-v2",
            "generated_at": "2026-01-06T12:00:00Z",
            "run": {},
            "summary": {"overall_status": "failed", "failure_count": 1},
            "failures": [
                {
                    "id": "test:failed",
                    "tool": "test",
                    "status": "failed",
                    "severity": "critical",  # Invalid - should be blocker/high/medium/low
                    "category": "test",
                }
            ],
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=triage_schema)
