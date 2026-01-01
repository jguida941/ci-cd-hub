"""Snapshot tests for CLI summary commands.

These tests verify that summary output doesn't drift from expected format.
Each summary command has fixed inputs and expected output (snapshots).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from textwrap import dedent
from unittest import mock

from cihub.commands.report import (
    _kyverno_summary,
    _orchestrator_load_summary,
    _orchestrator_trigger_summary,
    _security_overall_summary,
    _security_repo_summary,
    _security_zap_summary,
    _smoke_overall_summary,
    _smoke_repo_summary,
    cmd_report,
)

# =============================================================================
# Security Summary Tests
# =============================================================================


class TestSecurityOverallSummary:
    """Tests for security-summary --mode overall."""

    def test_snapshot_matches_expected(self) -> None:
        """Verify overall security summary matches expected format."""
        args = argparse.Namespace(
            repo_count="5",
            run_number="123",
        )
        result = _security_overall_summary(args)

        expected = dedent("""\
            # Security & Supply Chain Summary

            **Repositories Scanned:** 5
            **Run:** #123

            ## Tools Executed

            | Tool | Purpose |
            |------|---------|
            | CodeQL | Static Application Security Testing (SAST) |
            | SBOM | Software Bill of Materials generation |
            | pip-audit / OWASP | Dependency vulnerability scanning |
            | Bandit / Ruff-S | Python security linting |
            | ZAP | Dynamic Application Security Testing (DAST) |""")

        assert result == expected


class TestSecurityRepoSummary:
    """Tests for security-summary --mode repo."""

    def test_python_repo_summary(self) -> None:
        """Verify Python repo security summary format."""
        args = argparse.Namespace(
            repo="my-python-repo",
            language="python",
            has_source="true",
            pip_audit_vulns="0",
            bandit_high="0",
            ruff_issues="2",
            owasp_critical="0",
            owasp_high="0",
        )
        result = _security_repo_summary(args)

        assert "# Security & Supply Chain: my-python-repo" in result
        assert "**Language:** python" in result
        assert "| pip-audit | 0 vulns | - |" in result
        assert "| bandit | 0 high severity | - |" in result
        assert "| ruff-security | 2 issues | - |" in result
        assert "| codeql | Complete | - |" in result
        assert "| sbom | Generated | - |" in result

    def test_java_repo_summary(self) -> None:
        """Verify Java repo security summary format."""
        args = argparse.Namespace(
            repo="my-java-repo",
            language="java",
            has_source="true",
            pip_audit_vulns="0",
            bandit_high="0",
            ruff_issues="0",
            owasp_critical="1",
            owasp_high="3",
        )
        result = _security_repo_summary(args)

        assert "# Security & Supply Chain: my-java-repo" in result
        assert "**Language:** java" in result
        assert "| OWASP | 1 critical, 3 high | - |" in result
        assert "| codeql | Complete | - |" in result

    def test_no_source_code_skips_codeql(self) -> None:
        """Verify CodeQL is skipped when no source code present."""
        args = argparse.Namespace(
            repo="empty-repo",
            language="python",
            has_source="false",
            pip_audit_vulns="0",
            bandit_high="0",
            ruff_issues="0",
            owasp_critical="0",
            owasp_high="0",
        )
        result = _security_repo_summary(args)

        assert "| codeql | Skipped (no source code) | - |" in result


class TestSecurityZapSummary:
    """Tests for security-summary --mode zap."""

    def test_zap_skipped_no_repo(self) -> None:
        """Verify ZAP skipped message when repo checkout failed."""
        args = argparse.Namespace(
            repo="broken-repo",
            repo_present="false",
            run_zap="true",
            has_docker="true",
        )
        result = _security_zap_summary(args)

        assert "## ZAP DAST Scan: broken-repo" in result
        assert "Skipped - Repo checkout failed" in result

    def test_zap_skipped_no_run_flag(self) -> None:
        """Verify ZAP skipped when run_zap is false."""
        args = argparse.Namespace(
            repo="test-repo",
            repo_present="true",
            run_zap="false",
            has_docker="true",
        )
        result = _security_zap_summary(args)

        assert "Skipped - run_zap input is false" in result

    def test_zap_skipped_no_docker(self) -> None:
        """Verify ZAP skipped when no docker-compose.yml."""
        args = argparse.Namespace(
            repo="test-repo",
            repo_present="true",
            run_zap="true",
            has_docker="false",
        )
        result = _security_zap_summary(args)

        assert "Skipped - No docker-compose.yml found" in result

    def test_zap_completed(self) -> None:
        """Verify ZAP completed message when all conditions met."""
        args = argparse.Namespace(
            repo="web-app",
            repo_present="true",
            run_zap="true",
            has_docker="true",
        )
        result = _security_zap_summary(args)

        assert "## ZAP DAST Scan: web-app" in result
        assert "Scan completed. See artifacts for detailed report." in result


# =============================================================================
# Smoke Summary Tests
# =============================================================================


class TestSmokeOverallSummary:
    """Tests for smoke-summary --mode overall."""

    def test_snapshot_matches_expected(self) -> None:
        """Verify overall smoke summary matches expected format."""
        args = argparse.Namespace(
            repo_count="3",
            run_number="456",
            event_name="push",
            test_result="success",
        )
        result = _smoke_overall_summary(args)

        expected = dedent("""\
            # Smoke Test Summary

            **Total Test Repositories:** 3
            **Run Number:** #456
            **Trigger:** push
            **Status:** PASSED

            ---

            ## What Was Tested

            The smoke test validates core hub functionality:

            - Repository discovery and configuration loading
            - Language detection (Java and Python)
            - Core tool execution (coverage, linting, style checks)
            - Artifact generation and upload
            - Summary report generation""")

        assert result == expected

    def test_failed_status(self) -> None:
        """Verify FAILED status is shown correctly."""
        args = argparse.Namespace(
            repo_count="2",
            run_number="789",
            event_name="workflow_dispatch",
            test_result="failure",
        )
        result = _smoke_overall_summary(args)

        assert "**Status:** FAILED" in result


class TestSmokeRepoSummary:
    """Tests for smoke-summary --mode repo."""

    def test_python_repo_summary(self) -> None:
        """Verify Python smoke test summary format."""
        args = argparse.Namespace(
            owner="test-org",
            repo="python-app",
            branch="main",
            language="python",
            config="smoke-test-python.yaml",
            tests_total=42,
            tests_failed=0,
            coverage="85",
            ruff_errors=0,
            ruff_security=0,
            black_issues=0,
            checkstyle_violations=0,
            spotbugs_issues=0,
            coverage_lines="0 / 0",
        )
        result = _smoke_repo_summary(args)

        assert "# Smoke Test Results: test-org/python-app" in result
        assert "**Branch:** `main`" in result
        assert "**Language:** `python`" in result
        assert "## Python Smoke Test Results" in result
        assert "| **Unit Tests** | 42 passed | PASS |" in result
        assert "| **Coverage (pytest-cov)** | 85%" in result
        assert "**PASS** - Core Python tools executed successfully" in result

    def test_java_repo_summary(self) -> None:
        """Verify Java smoke test summary format."""
        args = argparse.Namespace(
            owner="test-org",
            repo="java-app",
            branch="develop",
            language="java",
            config="smoke-test-java.yaml",
            tests_total=100,
            tests_failed=2,
            coverage="72",
            coverage_lines="500 / 694",
            checkstyle_violations=5,
            spotbugs_issues=1,
            ruff_errors=0,
            ruff_security=0,
            black_issues=0,
        )
        result = _smoke_repo_summary(args)

        assert "# Smoke Test Results: test-org/java-app" in result
        assert "## Java Smoke Test Results" in result
        assert "| **Unit Tests** | 100 executed | PASS |" in result
        assert "| **Test Failures** | 2 failed | WARN |" in result
        assert "| **Coverage (JaCoCo)** | 72%" in result
        assert "| **Checkstyle** | 5 violations | WARN |" in result
        assert "| **SpotBugs** | 1 potential bugs | WARN |" in result
        assert "**Coverage Details:** 500 / 694 instructions covered" in result


# =============================================================================
# Kyverno Summary Tests
# =============================================================================


class TestKyvernoSummary:
    """Tests for kyverno-summary."""

    def test_snapshot_with_policies_dir(self, tmp_path: Path) -> None:
        """Verify Kyverno summary lists policies from directory."""
        # Create test policy files
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "block-pull-request.yaml").touch()
        (policies_dir / "require-referrers.yaml").touch()
        (policies_dir / "secretless.yml").touch()

        args = argparse.Namespace(
            policies_dir=str(policies_dir),
            validated="3",
            failed="0",
            run_tests="false",
            title="# Kyverno Policy Validation",
        )
        result = _kyverno_summary(args)

        assert "# Kyverno Policy Validation" in result
        assert "| Policies Validated | 3 |" in result
        assert "| Validation Failures | 0 |" in result
        assert "| Tests Run | false |" in result
        assert f"`{policies_dir}`" in result
        assert "| `block-pull-request.yaml` | Validated |" in result
        assert "| `require-referrers.yaml` | Validated |" in result
        assert "| `secretless.yml` | Validated |" in result

    def test_summary_without_policies_dir(self) -> None:
        """Verify Kyverno summary works when policies dir doesn't exist."""
        args = argparse.Namespace(
            policies_dir="/nonexistent/path",
            validated="0",
            failed="0",
            run_tests="false",
            title="# Kyverno Policy Validation (Hub)",
        )
        result = _kyverno_summary(args)

        assert "# Kyverno Policy Validation (Hub)" in result
        assert "| Policies Validated | 0 |" in result
        # Should not have a policies table since dir doesn't exist
        assert "| Policy | Status |" not in result


# =============================================================================
# Orchestrator Summary Tests
# =============================================================================


class TestOrchestratorLoadSummary:
    """Tests for orchestrator-summary --mode load-config."""

    def test_snapshot_matches_expected(self) -> None:
        """Verify load-config summary matches expected format."""
        args = argparse.Namespace(repo_count="10")
        result = _orchestrator_load_summary(args)

        expected = dedent("""\
            ## Hub Orchestrator

            **Repositories to build:** 10""")

        assert result == expected


class TestOrchestratorTriggerSummary:
    """Tests for orchestrator-summary --mode trigger-record."""

    def test_snapshot_matches_expected(self) -> None:
        """Verify trigger-record summary matches expected format."""
        args = argparse.Namespace(
            repo="my-service",
            owner="acme-corp",
            language="java",
            branch="main",
            workflow_id="hub-ci.yml",
            run_id="12345678",
            status="Triggered",
        )
        result = _orchestrator_trigger_summary(args)

        expected = dedent("""\
            ## my-service

            - **Owner:** acme-corp
            - **Language:** java
            - **Branch:** main
            - **Workflow:** hub-ci.yml
            - **Run ID:** 12345678
            - **Status:** Triggered""")

        assert result == expected

    def test_pending_run_id(self) -> None:
        """Verify 'pending' is shown when run_id is empty."""
        args = argparse.Namespace(
            repo="test-repo",
            owner="test-org",
            language="python",
            branch="develop",
            workflow_id="hub-ci.yml",
            run_id="",
            status="Dispatched",
        )
        result = _orchestrator_trigger_summary(args)

        assert "- **Run ID:** pending" in result


# =============================================================================
# Toggle Audit Tests
# =============================================================================


class TestSummaryToggle:
    """Tests verifying the summary toggle is respected."""

    def test_toggle_via_env_var(self, tmp_path: Path) -> None:
        """Verify CIHUB_WRITE_GITHUB_SUMMARY env var controls summary writing."""
        from cihub.commands.report import _resolve_write_summary

        # Default should be True
        assert _resolve_write_summary(None) is True

        # Explicit flag overrides env
        assert _resolve_write_summary(True) is True
        assert _resolve_write_summary(False) is False

        # Env var controls when flag is None
        with mock.patch.dict(os.environ, {"CIHUB_WRITE_GITHUB_SUMMARY": "false"}):
            assert _resolve_write_summary(None) is False

        with mock.patch.dict(os.environ, {"CIHUB_WRITE_GITHUB_SUMMARY": "true"}):
            assert _resolve_write_summary(None) is True

        with mock.patch.dict(os.environ, {"CIHUB_WRITE_GITHUB_SUMMARY": "0"}):
            assert _resolve_write_summary(None) is False

        with mock.patch.dict(os.environ, {"CIHUB_WRITE_GITHUB_SUMMARY": "1"}):
            assert _resolve_write_summary(None) is True

    def test_github_step_summary_path_resolution(self, tmp_path: Path) -> None:
        """Verify GITHUB_STEP_SUMMARY path is used when toggle is enabled."""
        from cihub.commands.report import _resolve_summary_path

        summary_file = tmp_path / "summary.md"

        # When github_summary is False, no path returned
        assert _resolve_summary_path(None, False) is None

        # When github_summary is True and env is set, use env path
        with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            result = _resolve_summary_path(None, True)
            assert result == summary_file

        # Explicit path overrides env
        explicit_path = tmp_path / "explicit.md"
        result = _resolve_summary_path(str(explicit_path), True)
        assert result == explicit_path


class TestSummaryCliWiring:
    """Tests for summary CLI wiring via cmd_report."""

    def test_security_summary_writes_step_summary(self, tmp_path: Path, monkeypatch) -> None:
        """Verify security-summary writes to GITHUB_STEP_SUMMARY when enabled."""
        from cihub.exit_codes import EXIT_SUCCESS

        summary_path = tmp_path / "step-summary.md"
        args = argparse.Namespace(
            subcommand="security-summary",
            mode="overall",
            repo_count=2,
            run_number=7,
            summary=None,
            write_github_summary=None,
            json=False,
        )

        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
        monkeypatch.delenv("CIHUB_WRITE_GITHUB_SUMMARY", raising=False)

        result = cmd_report(args)

        assert result == EXIT_SUCCESS
        assert summary_path.exists()
        assert "# Security & Supply Chain Summary" in summary_path.read_text(encoding="utf-8")

    def test_security_summary_skips_when_disabled(self, tmp_path: Path, monkeypatch) -> None:
        """Verify security-summary does not write when toggle is disabled."""
        summary_path = tmp_path / "step-summary.md"
        args = argparse.Namespace(
            subcommand="security-summary",
            mode="overall",
            repo_count=1,
            run_number=1,
            summary=None,
            write_github_summary=None,
            json=False,
        )

        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
        monkeypatch.setenv("CIHUB_WRITE_GITHUB_SUMMARY", "false")

        cmd_report(args)

        assert not summary_path.exists()
