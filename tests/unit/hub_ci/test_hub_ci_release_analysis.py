"""Tests for hub_ci release analysis and validation commands.

Split from test_hub_ci_release.py for better organization.
Tests: cmd_actionlint, cmd_trivy_summary, cmd_kyverno_validate, cmd_kyverno_test,
       cmd_gitleaks_summary, cmd_pytest_summary, cmd_summary, cmd_enforce
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.commands.hub_ci.release import (
    cmd_actionlint,
    cmd_enforce,
    cmd_gitleaks_summary,
    cmd_kyverno_test,
    cmd_kyverno_validate,
    cmd_pytest_summary,
    cmd_summary,
    cmd_trivy_summary,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


@pytest.fixture
def mock_args() -> argparse.Namespace:
    """Create a mock argparse namespace with common attributes."""
    args = argparse.Namespace()
    args.github_step_summary = None
    args.github_output = None
    return args


# =============================================================================
# cmd_actionlint Tests
# =============================================================================


class TestCmdActionlint:
    """Tests for cmd_actionlint function."""

    @patch("cihub.commands.hub_ci.release.safe_run")
    @patch("shutil.which")
    def test_actionlint_success(
        self, mock_which: MagicMock, mock_safe_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test successful actionlint run with no issues."""
        mock_which.return_value = "/usr/local/bin/actionlint"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_safe_run.return_value = mock_proc

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = False

        result = cmd_actionlint(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "passed" in result.summary.lower()

    @patch("shutil.which")
    def test_actionlint_not_found(self, mock_which: MagicMock, mock_args: argparse.Namespace):
        """Test actionlint failure when binary not found."""
        mock_which.return_value = None

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = False

        result = cmd_actionlint(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert "not found" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release.safe_run")
    @patch("shutil.which")
    def test_actionlint_with_issues(
        self, mock_which: MagicMock, mock_safe_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test actionlint with workflow issues."""
        mock_which.return_value = "/usr/local/bin/actionlint"
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ".github/workflows/ci.yml:10:5: error\n.github/workflows/ci.yml:20:10: warning"
        mock_safe_run.return_value = mock_proc

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = False

        result = cmd_actionlint(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["issues"] == 2

    @patch("cihub.commands.hub_ci.release.safe_run")
    @patch("shutil.which")
    def test_actionlint_with_reviewdog(
        self, mock_which: MagicMock, mock_safe_run: MagicMock, mock_args: argparse.Namespace
    ):
        """Test actionlint with reviewdog integration."""
        mock_which.side_effect = lambda x: {
            "actionlint": "/usr/local/bin/actionlint",
            "reviewdog": "/usr/local/bin/reviewdog",
        }.get(x)

        actionlint_proc = MagicMock()
        actionlint_proc.returncode = 0
        actionlint_proc.stdout = ""

        reviewdog_proc = MagicMock()
        reviewdog_proc.returncode = 0

        mock_safe_run.side_effect = [actionlint_proc, reviewdog_proc]

        mock_args.bin = None
        mock_args.workflow = ".github/workflows/"
        mock_args.reviewdog = True

        result = cmd_actionlint(mock_args)

        assert result.data["reviewdog"] is True


# =============================================================================
# cmd_trivy_summary Tests
# =============================================================================


class TestCmdTrivySummary:
    """Tests for cmd_trivy_summary function."""

    def test_trivy_summary_no_files(self, mock_args: argparse.Namespace):
        """Test trivy summary with no input files."""
        mock_args.fs_json = None
        mock_args.config_json = None
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["total_critical"] == 0
        assert result.data["total_high"] == 0

    def test_trivy_summary_with_vulnerabilities(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test trivy summary parses vulnerabilities correctly."""
        fs_json = tmp_path / "trivy-fs.json"
        fs_json.write_text(
            json.dumps({
                "Results": [
                    {
                        "Vulnerabilities": [
                            {"Severity": "CRITICAL"},
                            {"Severity": "HIGH"},
                            {"Severity": "HIGH"},
                            {"Severity": "MEDIUM"},
                        ]
                    }
                ]
            }),
            encoding="utf-8",
        )

        mock_args.fs_json = str(fs_json)
        mock_args.config_json = None
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.data["fs_critical"] == 1
        assert result.data["fs_high"] == 2

    def test_trivy_summary_with_misconfigurations(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test trivy summary parses misconfigurations correctly."""
        config_json = tmp_path / "trivy-config.json"
        config_json.write_text(
            json.dumps({
                "Results": [
                    {
                        "Misconfigurations": [
                            {"Severity": "CRITICAL"},
                            {"Severity": "CRITICAL"},
                            {"Severity": "HIGH"},
                        ]
                    }
                ]
            }),
            encoding="utf-8",
        )

        mock_args.fs_json = None
        mock_args.config_json = str(config_json)
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.data["config_critical"] == 2
        assert result.data["config_high"] == 1

    def test_trivy_summary_invalid_json(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test trivy summary handles invalid JSON gracefully."""
        fs_json = tmp_path / "trivy-fs.json"
        fs_json.write_text("not json", encoding="utf-8")

        mock_args.fs_json = str(fs_json)
        mock_args.config_json = None
        mock_args.github_output = False
        mock_args.github_summary = False

        result = cmd_trivy_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(result.problems) > 0


# =============================================================================
# cmd_kyverno_validate Tests
# =============================================================================


class TestCmdKyvernoValidate:
    """Tests for cmd_kyverno_validate function."""

    def test_validate_no_policies_dir(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test validation when policies directory doesn't exist."""
        mock_args.policies_dir = str(tmp_path / "nonexistent")
        mock_args.templates_dir = None
        mock_args.bin = None

        result = cmd_kyverno_validate(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "no policies found" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release._kyverno_apply")
    def test_validate_success(
        self, mock_apply: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test successful policy validation."""
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy1.yaml").write_text("policy: test", encoding="utf-8")

        mock_apply.return_value = "policy validated successfully"

        mock_args.policies_dir = str(policies_dir)
        mock_args.templates_dir = None
        mock_args.bin = None

        result = cmd_kyverno_validate(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["validated"] >= 1

    @patch("cihub.commands.hub_ci.release._kyverno_apply")
    def test_validate_with_failures(
        self, mock_apply: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test validation with policy failures."""
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy1.yaml").write_text("policy: test", encoding="utf-8")

        mock_apply.return_value = "error: invalid policy"

        mock_args.policies_dir = str(policies_dir)
        mock_args.templates_dir = None
        mock_args.bin = None

        result = cmd_kyverno_validate(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["failed"] >= 1


# =============================================================================
# cmd_kyverno_test Tests
# =============================================================================


class TestCmdKyvernoTest:
    """Tests for cmd_kyverno_test function."""

    def test_test_no_fixtures_dir(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test when fixtures directory doesn't exist."""
        mock_args.policies_dir = str(tmp_path / "policies")
        mock_args.fixtures_dir = str(tmp_path / "nonexistent")
        mock_args.fail_on_warn = False
        mock_args.bin = None

        result = cmd_kyverno_test(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert "skipped" in result.summary.lower()

    @patch("cihub.commands.hub_ci.release._kyverno_apply")
    def test_test_pass(
        self, mock_apply: MagicMock, tmp_path: Path, mock_args: argparse.Namespace
    ):
        """Test policy test with passing results."""
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        (policies_dir / "policy1.yaml").write_text("policy: test", encoding="utf-8")

        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "fixture1.yaml").write_text("resource: test", encoding="utf-8")

        mock_apply.return_value = "pass: 1"

        mock_args.policies_dir = str(policies_dir)
        mock_args.fixtures_dir = str(fixtures_dir)
        mock_args.fail_on_warn = False
        mock_args.bin = None

        result = cmd_kyverno_test(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["tested"] >= 1


# =============================================================================
# cmd_gitleaks_summary Tests
# =============================================================================


class TestCmdGitleaksSummary:
    """Tests for cmd_gitleaks_summary function."""

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_gitleaks_summary_success(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test gitleaks summary with success outcome."""
        mock_run.side_effect = [
            MagicMock(stdout="100"),  # rev-list count
            MagicMock(stdout="file1.py\nfile2.py"),  # ls-files
        ]

        mock_args.outcome = "success"

        result = cmd_gitleaks_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["result"] == "PASS"

    @patch("cihub.commands.hub_ci.release._run_command")
    def test_gitleaks_summary_failure(self, mock_run: MagicMock, mock_args: argparse.Namespace):
        """Test gitleaks summary with failure outcome."""
        mock_run.side_effect = [
            MagicMock(stdout="50"),
            MagicMock(stdout="file1.py"),
        ]

        mock_args.outcome = "failure"

        result = cmd_gitleaks_summary(mock_args)

        assert result.data["result"] == "FAIL"


# =============================================================================
# cmd_pytest_summary Tests
# =============================================================================


class TestCmdPytestSummary:
    """Tests for cmd_pytest_summary function."""

    def test_pytest_summary_no_files(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pytest summary when files don't exist."""
        mock_args.junit_xml = str(tmp_path / "nonexistent.xml")
        mock_args.coverage_xml = str(tmp_path / "nonexistent.xml")
        mock_args.coverage_min = 70

        result = cmd_pytest_summary(mock_args)

        assert result.data["tests_total"] == 0

    def test_pytest_summary_with_results(self, tmp_path: Path, mock_args: argparse.Namespace):
        """Test pytest summary with test results."""
        junit_xml = tmp_path / "test-results.xml"
        junit_xml.write_text(
            """<?xml version="1.0" encoding="utf-8"?>
            <testsuite tests="10" failures="1" errors="0" skipped="2">
            </testsuite>""",
            encoding="utf-8",
        )

        coverage_xml = tmp_path / "coverage.xml"
        coverage_xml.write_text(
            """<?xml version="1.0" encoding="utf-8"?>
            <coverage line-rate="0.85" lines-covered="850" lines-valid="1000">
            </coverage>""",
            encoding="utf-8",
        )

        mock_args.junit_xml = str(junit_xml)
        mock_args.coverage_xml = str(coverage_xml)
        mock_args.coverage_min = 70

        result = cmd_pytest_summary(mock_args)

        assert result.data["tests_total"] == 10
        assert result.data["tests_failed"] == 1
        assert result.data["tests_skipped"] == 2
        assert result.data["coverage_pct"] == 85


# =============================================================================
# cmd_summary Tests
# =============================================================================


class TestCmdSummary:
    """Tests for cmd_summary function."""

    def test_summary_all_success(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test summary with all successful results."""
        env_vars = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        result = cmd_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["has_issues"] is False

    def test_summary_with_failures(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test summary with some failures."""
        monkeypatch.setenv("RESULT_LINT", "failure")

        result = cmd_summary(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["has_issues"] is True


# =============================================================================
# cmd_enforce Tests
# =============================================================================


class TestCmdEnforce:
    """Tests for cmd_enforce function."""

    def test_enforce_all_pass(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test enforce with all checks passing."""
        env_vars = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_LINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        result = cmd_enforce(mock_args)

        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["failed"]) == 0

    def test_enforce_with_failure(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test enforce with some checks failing."""
        monkeypatch.setenv("RESULT_LINT", "failure")
        monkeypatch.setenv("RESULT_TYPECHECK", "failure")

        result = cmd_enforce(mock_args)

        assert result.exit_code == EXIT_FAILURE
        assert len(result.data["failed"]) >= 1

    def test_enforce_skipped_allowed(self, mock_args: argparse.Namespace, monkeypatch: pytest.MonkeyPatch):
        """Test enforce allows skipped checks."""
        monkeypatch.setenv("RESULT_MUTATION", "skipped")

        result = cmd_enforce(mock_args)

        assert result.exit_code == EXIT_SUCCESS
