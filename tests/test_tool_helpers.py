"""Tests for tool execution helpers (ensure_executable, load_json_report, run_tool_with_json_report).

This module tests the Phase 2 consolidation helpers for:
- Making files executable
- Loading JSON reports with error handling
- Running tools that produce JSON output
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.commands.hub_ci import (
    ToolResult,
    ensure_executable,
    load_json_report,
    run_tool_with_json_report,
)

# ============================================================================
# ToolResult Dataclass Tests
# ============================================================================


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self) -> None:
        """ToolResult correctly represents a successful tool run."""
        result = ToolResult(
            tool="test-tool",
            success=True,
            returncode=0,
            stdout="output",
            stderr="",
            json_data={"key": "value"},
            json_error=None,
            report_path=Path("/path/to/report.json"),
        )
        assert result.success is True
        assert result.returncode == 0
        assert result.json_data == {"key": "value"}
        assert result.json_error is None
        assert result.tool == "test-tool"

    def test_failure_result(self) -> None:
        """ToolResult correctly represents a failed tool run."""
        result = ToolResult(
            tool="failing-tool",
            success=False,
            returncode=1,
            stdout="",
            stderr="error message",
            json_data=None,
            json_error="Invalid JSON",
            report_path=None,
        )
        assert result.success is False
        assert result.returncode == 1
        assert result.json_error == "Invalid JSON"
        assert result.tool == "failing-tool"

    def test_defaults(self) -> None:
        """ToolResult has correct defaults for optional fields."""
        result = ToolResult(tool="minimal", success=True, returncode=0, stdout="", stderr="")
        assert result.json_data is None
        assert result.json_error is None
        assert result.report_path is None
        assert result.tool == "minimal"


# ============================================================================
# ensure_executable Tests
# ============================================================================


class TestEnsureExecutable:
    """Tests for ensure_executable() helper."""

    def test_makes_file_executable(self, tmp_path: Path) -> None:
        """ensure_executable adds execute permission to existing file."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/bash\necho hello")
        # Remove execute permission
        script.chmod(0o644)
        assert not os.access(script, os.X_OK)

        result = ensure_executable(script)

        assert result is True
        assert os.access(script, os.X_OK)

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        """ensure_executable returns False for non-existent file."""
        missing = tmp_path / "missing.sh"
        result = ensure_executable(missing)
        assert result is False

    def test_preserves_existing_permissions(self, tmp_path: Path) -> None:
        """ensure_executable preserves read/write permissions while adding execute."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o640)  # rw-r-----

        ensure_executable(script)

        mode = script.stat().st_mode
        assert mode & stat.S_IRUSR  # Owner read preserved
        assert mode & stat.S_IWUSR  # Owner write preserved
        assert mode & stat.S_IXUSR  # Execute added

    def test_idempotent(self, tmp_path: Path) -> None:
        """ensure_executable can be called multiple times safely."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/bash")

        ensure_executable(script)
        mode1 = script.stat().st_mode
        ensure_executable(script)
        mode2 = script.stat().st_mode

        assert mode1 == mode2


# ============================================================================
# load_json_report Tests
# ============================================================================


class TestLoadJsonReport:
    """Tests for load_json_report() helper."""

    @pytest.mark.parametrize(
        "content,expected_data",
        [
            ('{"key": "value"}', {"key": "value"}),
            ("[]", []),
            ('{"results": [1, 2, 3]}', {"results": [1, 2, 3]}),
            ("null", None),
            ("123", 123),
            ('"string"', "string"),
        ],
        ids=["dict", "empty_list", "nested", "null", "number", "string"],
    )
    def test_parses_valid_json(
        self, tmp_path: Path, content: str, expected_data: Any
    ) -> None:
        """load_json_report parses various valid JSON formats."""
        report = tmp_path / "report.json"
        report.write_text(content, encoding="utf-8")

        data, error = load_json_report(report)

        assert data == expected_data
        assert error is None

    @pytest.mark.parametrize(
        "content",
        [
            "{invalid json}",
            "{'single': 'quotes'}",
            "{missing: quotes}",
            "",
        ],
        ids=["invalid_syntax", "single_quotes", "unquoted_keys", "empty"],
    )
    def test_returns_error_for_invalid_json(
        self, tmp_path: Path, content: str
    ) -> None:
        """load_json_report returns error for invalid JSON."""
        report = tmp_path / "report.json"
        report.write_text(content, encoding="utf-8")

        data, error = load_json_report(report, default=[])

        assert data == []
        assert error is not None
        assert "Invalid JSON" in error

    def test_returns_error_for_missing_file(self, tmp_path: Path) -> None:
        """load_json_report returns error when file doesn't exist."""
        missing = tmp_path / "missing.json"

        data, error = load_json_report(missing, default={"fallback": True})

        assert data == {"fallback": True}
        assert error is not None
        assert "File not found" in error

    @pytest.mark.parametrize(
        "default",
        [None, [], {}, {"default": "value"}, 0, ""],
        ids=["none", "list", "dict", "populated_dict", "zero", "empty_string"],
    )
    def test_returns_default_on_error(
        self, tmp_path: Path, default: Any
    ) -> None:
        """load_json_report returns specified default on any error."""
        missing = tmp_path / "missing.json"

        data, _ = load_json_report(missing, default=default)

        assert data == default


class TestLoadJsonReportPropertyBased:
    """Property-based tests for load_json_report."""

    @given(data=st.dictionaries(st.text(min_size=1, max_size=10), st.integers()))
    @settings(max_examples=50)
    def test_roundtrip_dict(self, data: dict[str, int]) -> None:
        """Property: Any serializable dict can be loaded back."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            report = Path(tmpdir) / "report.json"
            report.write_text(json.dumps(data), encoding="utf-8")

            loaded, error = load_json_report(report)

            assert error is None
            assert loaded == data

    @given(data=st.lists(st.integers(), max_size=20))
    @settings(max_examples=50)
    def test_roundtrip_list(self, data: list[int]) -> None:
        """Property: Any serializable list can be loaded back."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            report = Path(tmpdir) / "report.json"
            report.write_text(json.dumps(data), encoding="utf-8")

            loaded, error = load_json_report(report)

            assert error is None
            assert loaded == data


# ============================================================================
# run_tool_with_json_report Tests
# ============================================================================


class TestRunToolWithJsonReport:
    """Tests for run_tool_with_json_report() helper."""

    def test_successful_tool_with_json(self, tmp_path: Path) -> None:
        """run_tool_with_json_report handles successful tool producing JSON."""
        report = tmp_path / "report.json"
        # Use echo to create a simple JSON file
        result = run_tool_with_json_report(
            cmd=["python", "-c", f"import json; json.dump({{'key': 'value'}}, open('{report}', 'w'))"],
            cwd=tmp_path,
            report_path=report,
        )

        assert result.success is True
        assert result.returncode == 0
        assert result.json_data == {"key": "value"}
        assert result.json_error is None

    def test_tool_with_missing_report_no_default(self, tmp_path: Path) -> None:
        """run_tool_with_json_report fails when report missing and no default."""
        report = tmp_path / "report.json"
        result = run_tool_with_json_report(
            cmd=["python", "-c", "pass"],  # Command that creates nothing
            cwd=tmp_path,
            report_path=report,
            default_on_missing=None,
        )

        assert result.success is False
        assert result.json_data is None
        assert "did not create report" in (result.json_error or "")

    def test_tool_with_missing_report_with_default(self, tmp_path: Path) -> None:
        """run_tool_with_json_report creates fallback when report missing."""
        report = tmp_path / "report.json"
        result = run_tool_with_json_report(
            cmd=["python", "-c", "pass"],
            cwd=tmp_path,
            report_path=report,
            default_on_missing='{"results": []}',
        )

        assert report.exists()
        assert result.json_data == {"results": []}

    def test_tool_failure_preserves_json(self, tmp_path: Path) -> None:
        """run_tool_with_json_report parses JSON even when tool fails."""
        report = tmp_path / "report.json"
        # Create report first, then run failing command
        report.write_text('{"error": "found"}', encoding="utf-8")

        result = run_tool_with_json_report(
            cmd=["python", "-c", "import sys; sys.exit(1)"],
            cwd=tmp_path,
            report_path=report,
        )

        assert result.success is False  # Tool failed
        assert result.returncode == 1
        assert result.json_data == {"error": "found"}  # But JSON was parsed

    def test_invalid_json_in_report(self, tmp_path: Path) -> None:
        """run_tool_with_json_report handles invalid JSON in report."""
        report = tmp_path / "report.json"
        report.write_text("{invalid json}", encoding="utf-8")

        result = run_tool_with_json_report(
            cmd=["python", "-c", "pass"],
            cwd=tmp_path,
            report_path=report,
        )

        assert result.success is False
        assert result.json_data is None
        assert "Invalid JSON" in (result.json_error or "")

    def test_captures_stdout_stderr(self, tmp_path: Path) -> None:
        """run_tool_with_json_report captures tool output."""
        report = tmp_path / "report.json"
        report.write_text("{}", encoding="utf-8")

        result = run_tool_with_json_report(
            cmd=["python", "-c", "import sys; print('stdout'); print('stderr', file=sys.stderr)"],
            cwd=tmp_path,
            report_path=report,
        )

        assert "stdout" in result.stdout
        assert "stderr" in result.stderr

    def test_env_passed_to_subprocess(self, tmp_path: Path) -> None:
        """run_tool_with_json_report passes env to subprocess."""
        report = tmp_path / "report.json"
        # Python code to write env var to JSON
        py_code = (
            "import os, json; "
            f"json.dump({{'val': os.environ.get('TEST_VAR')}}, open('{report}', 'w'))"
        )

        result = run_tool_with_json_report(
            cmd=["python", "-c", py_code],
            cwd=tmp_path,
            report_path=report,
            env={**os.environ, "TEST_VAR": "custom_value"},
        )

        assert result.json_data == {"val": "custom_value"}


class TestRunToolWithJsonReportIntegration:
    """Integration tests simulating real tool patterns."""

    def test_bandit_pattern(self, tmp_path: Path) -> None:
        """Simulates bandit SAST tool pattern."""
        report = tmp_path / "bandit.json"
        # Simulate bandit output
        report.write_text(json.dumps({
            "results": [
                {"issue_severity": "HIGH", "issue_text": "Test issue"},
            ],
        }), encoding="utf-8")

        result = run_tool_with_json_report(
            cmd=["python", "-c", "pass"],  # Pretend bandit ran
            cwd=tmp_path,
            report_path=report,
            default_on_missing='{"results":[]}',
        )

        results = result.json_data.get("results", [])
        high_count = sum(1 for r in results if r.get("issue_severity") == "HIGH")
        assert high_count == 1

    def test_pip_audit_pattern(self, tmp_path: Path) -> None:
        """Simulates pip-audit vulnerability scan pattern."""
        report = tmp_path / "pip-audit.json"
        # Simulate pip-audit output
        report.write_text(json.dumps([
            {"name": "package1", "vulns": [{"id": "CVE-2024-001"}]},
        ]), encoding="utf-8")

        result = run_tool_with_json_report(
            cmd=["python", "-c", "pass"],
            cwd=tmp_path,
            report_path=report,
            default_on_missing="[]",
        )

        data = result.json_data or []
        vuln_count = sum(len(pkg.get("vulns", [])) for pkg in data)
        assert vuln_count == 1

    def test_ruff_pattern(self, tmp_path: Path) -> None:
        """Simulates ruff linter pattern with stdout capture."""
        report = tmp_path / "ruff.json"
        # Simulate ruff writing to file
        result = run_tool_with_json_report(
            cmd=["python", "-c", f"import json; json.dump([{{'code': 'S101'}}], open('{report}', 'w'))"],
            cwd=tmp_path,
            report_path=report,
        )

        issues = result.json_data or []
        security_issues = [i for i in issues if str(i.get("code", "")).startswith("S")]
        assert len(security_issues) == 1


# ============================================================================
# Combined Workflow Tests
# ============================================================================


class TestCombinedWorkflow:
    """Tests combining multiple helpers in realistic workflows."""

    def test_mvnw_like_workflow(self, tmp_path: Path) -> None:
        """Test Maven wrapper pattern: ensure_executable + run tool."""
        mvnw = tmp_path / "mvnw"
        mvnw.write_text("#!/bin/bash\necho hello")

        # Ensure executable
        assert ensure_executable(mvnw) is True
        assert os.access(mvnw, os.X_OK)

        # Run tool (simulated)
        report = tmp_path / "checkstyle.xml"
        report.write_text('{"violations": 0}', encoding="utf-8")

        result = run_tool_with_json_report(
            cmd=["python", "-c", "pass"],
            cwd=tmp_path,
            report_path=report,
        )

        assert result.success is True
        assert result.json_data == {"violations": 0}

    def test_missing_wrapper_workflow(self, tmp_path: Path) -> None:
        """Test workflow when wrapper doesn't exist."""
        mvnw = tmp_path / "mvnw"

        # ensure_executable returns False for missing file
        if ensure_executable(mvnw):
            pytest.fail("Should not execute when wrapper missing")

        # Workflow should handle this gracefully
        # (no tool run, but no crash either)
        assert not mvnw.exists()

    def test_multiple_reports_workflow(self, tmp_path: Path) -> None:
        """Test loading multiple reports with different formats."""
        reports = {
            "bandit": {"results": []},
            "pip_audit": [],
            "ruff": [{"code": "E501"}],
        }

        results: dict[str, Any] = {}
        for name, data in reports.items():
            report = tmp_path / f"{name}.json"
            report.write_text(json.dumps(data), encoding="utf-8")
            loaded, error = load_json_report(report)
            assert error is None
            results[name] = loaded

        assert results["bandit"]["results"] == []
        assert results["pip_audit"] == []
        assert len(results["ruff"]) == 1
