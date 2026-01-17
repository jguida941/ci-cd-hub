"""Tests for CI engine gate evaluation functions.

Split from test_ci_engine.py for better organization.
Tests: _build_context, _evaluate_python_gates, _evaluate_java_gates,
       require_run_or_fail, backward compat runner imports
"""

# TEST-METRICS:

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cihub.services.ci_engine import (
    _build_context,
    _check_require_run_or_fail,
    _evaluate_java_gates,
    _evaluate_python_gates,
    _tool_requires_run_or_fail,
)


class TestBuildContext:
    """Tests for _build_context function."""

    def test_builds_context_from_config(self, tmp_path: Path) -> None:
        # default_branch from config is used when GITHUB_REF_NAME is not set
        config = {"repo": {"owner": "myorg", "name": "myrepo", "default_branch": "main"}}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.services.ci_engine.gates.get_git_branch", return_value="develop"):
                ctx = _build_context(tmp_path, config, ".", None)

        # Config default_branch takes precedence over git_branch when no env var
        assert ctx.branch == "main"
        assert ctx.workdir == "."

    def test_uses_github_env_vars(self, tmp_path: Path) -> None:
        config: dict = {}
        env = {
            "GITHUB_REPOSITORY": "org/repo",
            "GITHUB_REF_NAME": "feature-branch",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_SHA": "abc123",
        }
        with patch.dict(os.environ, env, clear=True):
            ctx = _build_context(tmp_path, config, "src", "corr-123")

        assert ctx.branch == "feature-branch"
        assert ctx.run_id == "12345"
        assert ctx.commit == "abc123"
        assert ctx.correlation_id == "corr-123"


class TestEvaluatePythonGates:
    """Tests for _evaluate_python_gates function."""

    def test_detects_test_failures(self) -> None:
        report = {"results": {"tests_failed": 5}}
        thresholds: dict = {}
        tools_configured = {"pytest": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "pytest failures detected" in failures

    def test_detects_coverage_below_threshold(self) -> None:
        report = {"results": {"coverage": 60}}
        thresholds = {"coverage_min": 80}
        tools_configured = {"pytest": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        # float() conversion means 60 becomes 60.0
        assert any("coverage 60" in f and "< 80" in f for f in failures)

    def test_detects_mutation_score_below_threshold(self) -> None:
        report = {"results": {"mutation_score": 50}}
        thresholds = {"mutation_score_min": 70}
        tools_configured = {"mutmut": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        # float() conversion means 50 becomes 50.0
        assert any("mutation score 50" in f and "< 70" in f for f in failures)

    def test_detects_ruff_errors(self) -> None:
        report = {"tool_metrics": {"ruff_errors": 10}}
        thresholds = {"max_ruff_errors": 0}
        tools_configured = {"ruff": True}
        config = {"python": {"tools": {"ruff": {"fail_on_error": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("ruff errors" in f for f in failures)

    def test_detects_bandit_high_vulns(self) -> None:
        report = {"tool_metrics": {"bandit_high": 3}}
        thresholds = {"max_high_vulns": 0}
        tools_configured = {"bandit": True}
        config = {"python": {"tools": {"bandit": {"fail_on_high": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("bandit high" in f for f in failures)

    def test_detects_bandit_medium_vulns_when_enabled(self) -> None:
        report = {"tool_metrics": {"bandit_medium": 2}}
        thresholds = {"max_high_vulns": 0}
        tools_configured = {"bandit": True}
        config = {"python": {"tools": {"bandit": {"fail_on_medium": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("bandit medium" in f for f in failures)

    def test_detects_bandit_low_vulns_when_enabled(self) -> None:
        report = {"tool_metrics": {"bandit_low": 1}}
        thresholds = {"max_high_vulns": 0}
        tools_configured = {"bandit": True}
        config = {"python": {"tools": {"bandit": {"fail_on_low": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("bandit low" in f for f in failures)

    def test_detects_codeql_failure(self) -> None:
        report = {"tools_ran": {"codeql": True}, "tools_success": {"codeql": False}}
        thresholds: dict = {}
        tools_configured = {"codeql": True}
        config = {"python": {"tools": {"codeql": {"fail_on_error": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "codeql failed" in failures

    def test_detects_hypothesis_not_run(self) -> None:
        """Hypothesis gate should fail when configured but didn't run."""
        report = {"tools_ran": {"hypothesis": False}, "tools_success": {"hypothesis": False}}
        thresholds: dict = {}
        tools_configured = {"hypothesis": True}
        config = {"python": {"tools": {"hypothesis": {"fail_on_error": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "hypothesis did not run" in failures

    def test_detects_hypothesis_failure(self) -> None:
        """Hypothesis gate should fail when ran but failed."""
        report = {"tools_ran": {"hypothesis": True}, "tools_success": {"hypothesis": False}}
        thresholds: dict = {}
        tools_configured = {"hypothesis": True}
        config = {"python": {"tools": {"hypothesis": {"fail_on_error": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "hypothesis failed" in failures

    def test_hypothesis_skipped_when_fail_on_error_false(self) -> None:
        """Hypothesis gate should not fail when fail_on_error is false."""
        report = {"tools_ran": {"hypothesis": False}, "tools_success": {"hypothesis": False}}
        thresholds: dict = {}
        tools_configured = {"hypothesis": True}
        config = {"python": {"tools": {"hypothesis": {"fail_on_error": False}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "hypothesis did not run" not in failures
        assert "hypothesis failed" not in failures

    def test_detects_docker_not_run(self) -> None:
        report = {"tools_ran": {"docker": False}, "tools_success": {"docker": False}}
        thresholds: dict = {}
        tools_configured = {"docker": True}
        config = {"python": {"tools": {"docker": {"fail_on_error": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "docker did not run" in failures

    def test_skips_missing_compose_when_toggle_off(self) -> None:
        report = {
            "tool_metrics": {"docker_missing_compose": True},
            "tools_ran": {"docker": False},
            "tools_success": {"docker": False},
        }
        thresholds: dict = {}
        tools_configured = {"docker": True}
        config = {"python": {"tools": {"docker": {"fail_on_error": True, "fail_on_missing_compose": False}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "docker compose file missing" not in failures
        assert "docker did not run" not in failures

    def test_fails_on_missing_compose_when_enabled(self) -> None:
        report = {
            "tool_metrics": {"docker_missing_compose": True},
            "tools_ran": {"docker": False},
            "tools_success": {"docker": False},
        }
        thresholds: dict = {}
        tools_configured = {"docker": True}
        config = {"python": {"tools": {"docker": {"fail_on_missing_compose": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "docker compose file missing" in failures

    def test_no_failures_when_all_pass(self) -> None:
        report = {
            "results": {"coverage": 90, "tests_failed": 0, "tests_passed": 10},
            "tool_metrics": {"ruff_errors": 0},
        }
        thresholds = {"coverage_min": 80}
        tools_configured = {"pytest": True, "ruff": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert len(failures) == 0

    def test_fails_when_no_tests_ran(self) -> None:
        """Issue 12: CI gates should fail when tests_total == 0."""
        report = {"results": {"tests_passed": 0, "tests_failed": 0, "tests_skipped": 0}}
        thresholds: dict = {}
        tools_configured = {"pytest": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "no tests ran - cannot verify quality" in failures

    def test_passes_with_only_passed_tests(self) -> None:
        """Issue 12: Tests should pass when tests ran successfully."""
        report = {"results": {"tests_passed": 5, "tests_failed": 0, "tests_skipped": 0}}
        thresholds: dict = {}
        tools_configured = {"pytest": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "no tests ran - cannot verify quality" not in failures
        assert "pytest failures detected" not in failures

    def test_trivy_cvss_enforcement_fails_above_threshold(self) -> None:
        """Issue 3: CVSS enforcement should fail when max CVSS >= threshold."""
        report = {
            "results": {"tests_passed": 1, "tests_failed": 0, "tests_skipped": 0},
            "tool_metrics": {"trivy_max_cvss": 9.1},
            "tools_ran": {"trivy": True},
        }
        thresholds = {"trivy_cvss_fail": 7.0}
        tools_configured = {"trivy": True}
        config: dict = {"python": {"tools": {"trivy": {"fail_on_critical": False, "fail_on_high": False}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("trivy max CVSS 9.1 >= 7.0" in f for f in failures)

    def test_trivy_cvss_enforcement_passes_below_threshold(self) -> None:
        """Issue 3: CVSS enforcement should pass when max CVSS < threshold."""
        report = {
            "results": {"tests_passed": 1, "tests_failed": 0, "tests_skipped": 0},
            "tool_metrics": {"trivy_max_cvss": 5.5},
            "tools_ran": {"trivy": True},
        }
        thresholds = {"trivy_cvss_fail": 7.0}
        tools_configured = {"trivy": True}
        config: dict = {"python": {"tools": {"trivy": {"fail_on_critical": False, "fail_on_high": False}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert not any("trivy max CVSS" in f for f in failures)

    def test_trivy_cvss_enforcement_skipped_when_threshold_zero(self) -> None:
        """Issue 3: CVSS enforcement should be skipped when threshold is 0 or not set."""
        report = {
            "results": {"tests_passed": 1, "tests_failed": 0, "tests_skipped": 0},
            "tool_metrics": {"trivy_max_cvss": 9.1},
            "tools_ran": {"trivy": True},
        }
        thresholds: dict = {}  # No CVSS threshold set
        tools_configured = {"trivy": True}
        config: dict = {"python": {"tools": {"trivy": {"fail_on_critical": False, "fail_on_high": False}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert not any("trivy max CVSS" in f for f in failures)


class TestEvaluateJavaGates:
    """Tests for _evaluate_java_gates function."""

    def test_detects_test_failures(self) -> None:
        report = {"results": {"tests_failed": 2}}
        thresholds: dict = {}
        tools_configured: dict = {}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "test failures detected" in failures

    def test_detects_coverage_below_threshold(self) -> None:
        report = {"results": {"coverage": 50}}
        thresholds = {"coverage_min": 70}
        tools_configured = {"jacoco": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        # float() conversion means 50 becomes 50.0
        assert any("coverage 50" in f and "< 70" in f for f in failures)

    def test_detects_checkstyle_issues(self) -> None:
        report = {"tool_metrics": {"checkstyle_issues": 15}}
        thresholds = {"max_checkstyle_errors": 0}
        tools_configured = {"checkstyle": True}
        config = {"java": {"tools": {"checkstyle": {"fail_on_violation": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("checkstyle issues" in f for f in failures)

    def test_detects_spotbugs_issues(self) -> None:
        report = {"tool_metrics": {"spotbugs_issues": 5}}
        thresholds = {"max_spotbugs_bugs": 0}
        tools_configured = {"spotbugs": True}
        config = {"java": {"tools": {"spotbugs": {"fail_on_error": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("spotbugs issues" in f for f in failures)

    def test_detects_owasp_vulns(self) -> None:
        report = {"tool_metrics": {"owasp_critical": 1, "owasp_high": 2}}
        thresholds = {"max_critical_vulns": 0, "max_high_vulns": 0}
        tools_configured = {"owasp": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        # Gate specs produce separate failure messages for critical and high
        assert any("owasp critical" in f for f in failures)
        assert any("owasp high" in f for f in failures)

    def test_detects_codeql_not_run(self) -> None:
        report = {"tools_ran": {"codeql": False}, "tools_success": {"codeql": False}}
        thresholds: dict = {}
        tools_configured = {"codeql": True}
        config = {"java": {"tools": {"codeql": {"fail_on_error": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "codeql did not run" in failures

    def test_detects_jqwik_not_run(self) -> None:
        """jqwik gate should fail when configured but didn't run."""
        report = {"tools_ran": {"jqwik": False}, "tools_success": {"jqwik": False}}
        thresholds: dict = {}
        tools_configured = {"jqwik": True}
        config = {"java": {"tools": {"jqwik": {"fail_on_error": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "jqwik did not run" in failures

    def test_detects_jqwik_failure(self) -> None:
        """jqwik gate should fail when ran but failed."""
        report = {"tools_ran": {"jqwik": True}, "tools_success": {"jqwik": False}}
        thresholds: dict = {}
        tools_configured = {"jqwik": True}
        config = {"java": {"tools": {"jqwik": {"fail_on_error": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "jqwik failed" in failures

    def test_jqwik_skipped_when_fail_on_error_false(self) -> None:
        """jqwik gate should not fail when fail_on_error is false."""
        report = {"tools_ran": {"jqwik": False}, "tools_success": {"jqwik": False}}
        thresholds: dict = {}
        tools_configured = {"jqwik": True}
        config = {"java": {"tools": {"jqwik": {"fail_on_error": False}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "jqwik did not run" not in failures
        assert "jqwik failed" not in failures

    def test_detects_docker_failure(self) -> None:
        report = {"tools_ran": {"docker": True}, "tools_success": {"docker": False}}
        thresholds: dict = {}
        tools_configured = {"docker": True}
        config = {"java": {"tools": {"docker": {"fail_on_error": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "docker failed" in failures

    def test_java_skips_missing_compose_when_toggle_off(self) -> None:
        report = {
            "tool_metrics": {"docker_missing_compose": True},
            "tools_ran": {"docker": False},
            "tools_success": {"docker": False},
        }
        thresholds: dict = {}
        tools_configured = {"docker": True}
        config = {"java": {"tools": {"docker": {"fail_on_error": True, "fail_on_missing_compose": False}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "docker compose file missing" not in failures
        assert "docker did not run" not in failures

    def test_java_fails_on_missing_compose_when_enabled(self) -> None:
        report = {
            "tool_metrics": {"docker_missing_compose": True},
            "tools_ran": {"docker": False},
            "tools_success": {"docker": False},
        }
        thresholds: dict = {}
        tools_configured = {"docker": True}
        config = {"java": {"tools": {"docker": {"fail_on_missing_compose": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "docker compose file missing" in failures

    def test_no_failures_when_all_pass(self) -> None:
        report = {"results": {"coverage": 85, "tests_failed": 0, "tests_passed": 10}, "tool_metrics": {}}
        thresholds = {"coverage_min": 70}
        tools_configured = {"jacoco": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert len(failures) == 0

    def test_fails_when_no_tests_ran(self) -> None:
        """Issue 12: CI gates should fail when tests_total == 0."""
        report = {"results": {"tests_passed": 0, "tests_failed": 0, "tests_skipped": 0}}
        thresholds: dict = {}
        tools_configured: dict = {}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "no tests ran - cannot verify quality" in failures

    def test_passes_with_only_passed_tests(self) -> None:
        """Issue 12: Tests should pass when tests ran successfully."""
        report = {"results": {"tests_passed": 5, "tests_failed": 0, "tests_skipped": 0}}
        thresholds: dict = {}
        tools_configured: dict = {}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "no tests ran - cannot verify quality" not in failures
        assert "test failures detected" not in failures

    def test_owasp_cvss_enforcement_fails_above_threshold(self) -> None:
        """Issue 3: OWASP CVSS enforcement should fail when max CVSS >= threshold."""
        report = {
            "results": {"tests_passed": 1, "tests_failed": 0, "tests_skipped": 0},
            "tool_metrics": {"owasp_max_cvss": 9.8},
            "tools_ran": {"owasp": True},
        }
        thresholds = {"owasp_cvss_fail": 7.0}
        tools_configured = {"owasp": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("owasp max CVSS 9.8 >= 7.0" in f for f in failures)

    def test_owasp_cvss_enforcement_passes_below_threshold(self) -> None:
        """Issue 3: OWASP CVSS enforcement should pass when max CVSS < threshold."""
        report = {
            "results": {"tests_passed": 1, "tests_failed": 0, "tests_skipped": 0},
            "tool_metrics": {"owasp_max_cvss": 6.5},
            "tools_ran": {"owasp": True},
        }
        thresholds = {"owasp_cvss_fail": 7.0}
        tools_configured = {"owasp": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert not any("owasp max CVSS" in f for f in failures)

    def test_trivy_cvss_enforcement_java_fails_above_threshold(self) -> None:
        """Issue 3: Trivy CVSS enforcement for Java should fail when max CVSS >= threshold."""
        report = {
            "results": {"tests_passed": 1, "tests_failed": 0, "tests_skipped": 0},
            "tool_metrics": {"trivy_max_cvss": 8.5},
            "tools_ran": {"trivy": True},
        }
        thresholds = {"trivy_cvss_fail": 7.0}
        tools_configured = {"trivy": True}
        config: dict = {"java": {"tools": {"trivy": {"fail_on_critical": False, "fail_on_high": False}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("trivy max CVSS 8.5 >= 7.0" in f for f in failures)


class TestRequireRunOrFail:
    """Tests for require_run_or_fail policy."""

    def test_tool_requires_run_per_tool_setting(self) -> None:
        """Per-tool setting takes precedence."""
        config = {
            "python": {"tools": {"pytest": {"require_run_or_fail": True}}},
            "gates": {"require_run_or_fail": False},
        }
        assert _tool_requires_run_or_fail("pytest", config, "python") is True

    def test_tool_requires_run_global_default(self) -> None:
        """Global default applies when no per-tool setting."""
        config = {
            "python": {"tools": {"pytest": {"enabled": True}}},
            "gates": {"require_run_or_fail": True},
        }
        assert _tool_requires_run_or_fail("pytest", config, "python") is True

    def test_tool_requires_run_tool_default(self) -> None:
        """Tool default applies when set in gates.tool_defaults."""
        config = {
            "python": {"tools": {}},
            "gates": {
                "require_run_or_fail": False,
                "tool_defaults": {"pytest": True},
            },
        }
        assert _tool_requires_run_or_fail("pytest", config, "python") is True

    def test_tool_requires_run_fallback_false(self) -> None:
        """Falls back to false when nothing configured."""
        config: dict = {}
        assert _tool_requires_run_or_fail("pytest", config, "python") is False

    def test_check_require_run_or_fail_not_configured(self) -> None:
        """No failure when tool is not configured."""
        tools_configured: dict = {}
        tools_ran: dict = {}
        config = {"gates": {"tool_defaults": {"pytest": True}}}
        result = _check_require_run_or_fail("pytest", tools_configured, tools_ran, config, "python")
        assert result is None

    def test_check_require_run_or_fail_ran(self) -> None:
        """No failure when tool ran."""
        tools_configured = {"pytest": True}
        tools_ran = {"pytest": True}
        config = {"gates": {"tool_defaults": {"pytest": True}}}
        result = _check_require_run_or_fail("pytest", tools_configured, tools_ran, config, "python")
        assert result is None

    def test_check_require_run_or_fail_not_ran_required(self) -> None:
        """Failure when tool required but didn't run."""
        tools_configured = {"pytest": True}
        tools_ran = {"pytest": False}
        config = {"gates": {"tool_defaults": {"pytest": True}}}
        result = _check_require_run_or_fail("pytest", tools_configured, tools_ran, config, "python")
        assert result is not None
        assert "require_run_or_fail=true" in result

    def test_check_require_run_or_fail_not_ran_optional(self) -> None:
        """No failure when optional tool didn't run."""
        tools_configured = {"mutmut": True}
        tools_ran = {"mutmut": False}
        config = {"gates": {"tool_defaults": {"mutmut": False}}}
        result = _check_require_run_or_fail("mutmut", tools_configured, tools_ran, config, "python")
        assert result is None

    def test_python_gates_require_run_or_fail_integration(self) -> None:
        """Integration test: gates fail when required tool didn't run."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0},
            "tools_ran": {"pytest": True, "bandit": False},
            "tools_success": {"pytest": True},
            "tool_metrics": {},
        }
        thresholds: dict = {}
        tools_configured = {"pytest": True, "bandit": True}
        config = {
            "python": {"tools": {"bandit": {"require_run_or_fail": True}}},
            "gates": {"require_run_or_fail": False},
        }

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("bandit configured but did not run" in f for f in failures)

    def test_java_gates_require_run_or_fail_integration(self) -> None:
        """Integration test: Java gates fail when required tool didn't run."""
        report = {
            "results": {"tests_passed": 10, "tests_failed": 0},
            "tools_ran": {"jacoco": True, "owasp": False},
            "tools_success": {"jacoco": True},
            "tool_metrics": {},
        }
        thresholds: dict = {}
        tools_configured = {"jacoco": True, "owasp": True}
        config = {
            "java": {"tools": {"owasp": {"require_run_or_fail": True}}},
            "gates": {"require_run_or_fail": False},
        }

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("owasp configured but did not run" in f for f in failures)


class TestBackwardCompatRunnerImports:
    """Tests for run_* backward-compatibility imports via __getattr__.

    These tests ensure the dynamic attribute access in ci_engine/__init__.py
    correctly provides run_pytest, run_ruff, etc. as callables. If
    _RUNNER_COMPAT_MAP or registry entries drift, these tests will catch it.
    """

    def test_run_pytest_is_callable(self) -> None:
        """run_pytest should be importable and callable."""
        from cihub.services.ci_engine import run_pytest

        assert callable(run_pytest), "run_pytest should be a callable"

    def test_run_ruff_is_callable(self) -> None:
        """run_ruff should be importable and callable."""
        from cihub.services.ci_engine import run_ruff

        assert callable(run_ruff), "run_ruff should be a callable"

    def test_run_jacoco_is_callable(self) -> None:
        """run_jacoco should be importable and callable."""
        from cihub.services.ci_engine import run_jacoco

        assert callable(run_jacoco), "run_jacoco should be a callable"

    def test_run_checkstyle_is_callable(self) -> None:
        """run_checkstyle should be importable and callable."""
        from cihub.services.ci_engine import run_checkstyle

        assert callable(run_checkstyle), "run_checkstyle should be a callable"

    def test_missing_runner_raises_attribute_error(self) -> None:
        """Missing runner should raise AttributeError with helpful message."""
        import cihub.services.ci_engine as ci_engine

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = ci_engine.run_nonexistent_tool

    def test_python_runners_dict_is_copy(self) -> None:
        """PYTHON_RUNNERS should return a copy to prevent mutation."""
        from cihub.services.ci_engine import PYTHON_RUNNERS

        original_len = len(PYTHON_RUNNERS)
        PYTHON_RUNNERS["test_key"] = lambda: None
        # Re-import should not have the mutation
        from cihub.services import ci_engine

        fresh_runners = ci_engine.PYTHON_RUNNERS
        assert "test_key" not in fresh_runners
        assert len(fresh_runners) == original_len

    def test_java_runners_dict_is_copy(self) -> None:
        """JAVA_RUNNERS should return a copy to prevent mutation."""
        from cihub.services.ci_engine import JAVA_RUNNERS

        original_len = len(JAVA_RUNNERS)
        JAVA_RUNNERS["test_key"] = lambda: None
        # Re-import should not have the mutation
        from cihub.services import ci_engine

        fresh_runners = ci_engine.JAVA_RUNNERS
        assert "test_key" not in fresh_runners
        assert len(fresh_runners) == original_len
