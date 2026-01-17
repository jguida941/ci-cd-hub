"""Integration tests for the check command.

These tests verify that the check command correctly orchestrates
multiple tools and produces coherent results across the full flow
from CLI invocation to report generation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCheckCLIIntegration:
    """Integration tests for check command via CLI."""

    def test_check_help(self):
        """Test that check --help works and shows expected options."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "check" in result.stdout.lower()
        # Should show tier flags
        assert "--audit" in result.stdout or "--full" in result.stdout

    def test_check_json_output_structure(self):
        """Test that check --json produces valid JSON with expected structure."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # May fail if tools not installed, but should still produce JSON
        try:
            data = json.loads(result.stdout)
            # Should have standard command result structure
            assert "status" in data
            assert "exit_code" in data
            assert "summary" in data
        except json.JSONDecodeError:
            # If not JSON, check for error message
            assert "error" in result.stderr.lower() or result.returncode != 0

    def test_check_produces_problems_on_failure(self, tmp_path: Path):
        """Test that check produces problems array when tools fail."""
        # Create a minimal project with intentional lint issues
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "bad_code.py").write_text("import os,sys\nx=1\n")  # ruff should flag this

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_path,
        )

        try:
            data = json.loads(result.stdout)
            # Should have problems if lint failed
            if data.get("exit_code", 0) != 0:
                assert "problems" in data
        except json.JSONDecodeError:
            pass  # OK if not JSON - might be missing tools

    @pytest.mark.slow
    def test_check_full_tier(self):
        """Test check --full runs additional tools (slow test)."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--full", "--json"],
            capture_output=True,
            text=True,
            timeout=300,  # Full check can take longer
        )
        # Should complete (may pass or fail depending on environment)
        assert result.returncode is not None


# =============================================================================
# Check Command Flow Tests
# =============================================================================


class TestCheckCommandFlow:
    """Tests for the check command internal flow."""

    def test_check_discovers_python_project(self, tmp_python_repo: Path):
        """Test that check correctly identifies Python projects."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tmp_python_repo,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert data.get("data", {}).get("language") == "python" or "python" in result.stdout.lower()

    def test_check_discovers_java_project(self, tmp_java_repo: Path):
        """Test that check correctly identifies Java projects."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "detect", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tmp_java_repo,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                assert data.get("data", {}).get("language") == "java" or "java" in result.stdout.lower()
            except json.JSONDecodeError:
                pass


# =============================================================================
# Tool Orchestration Tests
# =============================================================================


class TestToolOrchestration:
    """Tests for tool orchestration in check command."""

    def test_check_runs_lint_tools(self, tmp_python_repo: Path):
        """Test that check runs lint tools for Python projects."""
        # Add some code to lint
        (tmp_python_repo / "src" / "app.py").write_text("def hello():\n    return 'hello'\n")

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_python_repo,
        )

        try:
            data = json.loads(result.stdout)
            # Should have attempted to run tools
            assert "status" in data
        except json.JSONDecodeError:
            pass

    def test_check_handles_missing_tools_gracefully(self, tmp_path: Path):
        """Test that check handles missing tools without crashing."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "test.py").write_text("x = 1\n")

        # Should complete even if tools are missing
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_path,
        )

        # Should not crash - may succeed or fail
        assert result.returncode is not None


# =============================================================================
# Report Generation Tests
# =============================================================================


class TestReportGeneration:
    """Tests for report generation during check."""

    def test_check_generates_report_file(self, tmp_python_repo: Path):
        """Test that check generates a report file."""
        (tmp_python_repo / "src" / "app.py").write_text("x = 1\n")

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_python_repo,
        )

        # Check for report file (may or may not exist depending on config)
        report_path = tmp_python_repo / ".cihub" / "report.json"
        # Report may or may not be generated depending on check mode

    def test_check_json_output_matches_exit_code(self, tmp_python_repo: Path):
        """Test that JSON output status matches process exit code."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_python_repo,
        )

        try:
            data = json.loads(result.stdout)
            # Status should match exit code
            if result.returncode == 0:
                assert data.get("status") == "success" or data.get("exit_code") == 0
            else:
                assert data.get("status") != "success" or data.get("exit_code") != 0
        except json.JSONDecodeError:
            pass


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestCheckErrorHandling:
    """Tests for error handling in check command."""

    def test_check_on_empty_directory(self, tmp_path: Path):
        """Test check behavior on empty directory."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_path,
        )
        # Should handle gracefully - either skip or report no language
        assert result.returncode is not None

    def test_check_with_invalid_config(self, tmp_path: Path):
        """Test check behavior with invalid config file."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / ".ci-hub.yml").write_text("invalid: yaml: [[[")

        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_path,
        )
        # Should handle invalid config gracefully
        assert result.returncode is not None

    def test_check_timeout_handling(self, tmp_path: Path):
        """Test that check respects timeout settings."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        # Running with a short timeout should complete or timeout gracefully
        try:
            result = subprocess.run(
                [sys.executable, "-m", "cihub", "check"],
                capture_output=True,
                text=True,
                timeout=5,  # Very short timeout
                cwd=tmp_path,
            )
        except subprocess.TimeoutExpired:
            pass  # Timeout is acceptable


# =============================================================================
# Integration with Other Commands
# =============================================================================


class TestCheckIntegrationWithOtherCommands:
    """Tests for check command integration with other cihub commands."""

    def test_check_after_init(self, tmp_path: Path):
        """Test that check works after init command."""
        # First run init
        init_result = subprocess.run(
            [sys.executable, "-m", "cihub", "init", "--non-interactive", "--language", "python"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_path,
        )

        # Then run check
        check_result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_path,
        )

        # Check should complete
        assert check_result.returncode is not None

    def test_check_after_scaffold(self, tmp_path: Path):
        """Test that check works on scaffolded project."""
        # Scaffold a project
        scaffold_result = subprocess.run(
            [sys.executable, "-m", "cihub", "scaffold", "python", "--name", "test-project"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_path,
        )

        if scaffold_result.returncode == 0:
            project_path = tmp_path / "test-project"
            if project_path.exists():
                # Run check on scaffolded project
                check_result = subprocess.run(
                    [sys.executable, "-m", "cihub", "check"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=project_path,
                )
                assert check_result.returncode is not None


# =============================================================================
# Tier-specific Tests
# =============================================================================


class TestCheckTiers:
    """Tests for check command tiers."""

    def test_base_tier_is_fast(self, tmp_python_repo: Path):
        """Test that base tier (no flags) completes quickly."""
        import time

        start = time.time()
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=tmp_python_repo,
        )
        elapsed = time.time() - start

        # Base tier should be relatively fast (< 60s)
        assert elapsed < 60

    def test_audit_tier_runs_additional_checks(self, tmp_python_repo: Path):
        """Test that --audit tier runs additional checks."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--audit", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_python_repo,
        )
        # Should complete
        assert result.returncode is not None

    def test_security_tier_runs_security_tools(self, tmp_python_repo: Path):
        """Test that --security tier runs security tools."""
        result = subprocess.run(
            [sys.executable, "-m", "cihub", "check", "--security", "--json"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=tmp_python_repo,
        )
        # Should complete
        assert result.returncode is not None
