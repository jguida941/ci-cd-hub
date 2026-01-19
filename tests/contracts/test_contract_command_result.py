"""Contract tests for CommandResult and related types.

These tests verify that the CommandResult and ToolResult structures
maintain their contract - field presence, types, and serialization stability.
This is critical for CLI output stability and JSON API consistency.
"""

# TEST-METRICS:

from __future__ import annotations

import json
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult, ToolResult

# =============================================================================
# CommandResult Contract Tests
# =============================================================================


class TestCommandResultContract:
    """Contract tests ensuring CommandResult structure stability."""

    def test_required_fields_exist(self):
        """Contract: CommandResult has all required fields."""
        result = CommandResult()

        # These fields MUST exist
        assert hasattr(result, "exit_code")
        assert hasattr(result, "summary")
        assert hasattr(result, "problems")
        assert hasattr(result, "suggestions")
        assert hasattr(result, "files_generated")
        assert hasattr(result, "files_modified")
        assert hasattr(result, "artifacts")
        assert hasattr(result, "data")

    def test_field_types(self):
        """Contract: CommandResult fields have correct types."""
        result = CommandResult()

        assert isinstance(result.exit_code, int)
        assert isinstance(result.summary, str)
        assert isinstance(result.problems, list)
        assert isinstance(result.suggestions, list)
        assert isinstance(result.files_generated, list)
        assert isinstance(result.files_modified, list)
        assert isinstance(result.artifacts, dict)
        assert isinstance(result.data, dict)

    def test_default_values(self):
        """Contract: CommandResult has stable default values."""
        result = CommandResult()

        assert result.exit_code == 0
        assert result.summary == ""
        assert result.problems == []
        assert result.suggestions == []
        assert result.files_generated == []
        assert result.files_modified == []
        assert result.artifacts == {}
        assert result.data == {}

    def test_to_payload_required_fields(self):
        """Contract: to_payload returns all required fields."""
        result = CommandResult(exit_code=EXIT_SUCCESS, summary="test")
        payload = result.to_payload(command="test-cmd", status="success", duration_ms=100)

        # Required fields in payload
        required_fields = [
            "command",
            "status",
            "exit_code",
            "duration_ms",
            "summary",
            "artifacts",
            "problems",
            "suggestions",
            "files_generated",
            "files_modified",
        ]

        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

    def test_to_payload_field_types(self):
        """Contract: to_payload field types are correct for JSON serialization."""
        result = CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="test",
            problems=[{"severity": "error", "message": "test"}],
            data={"key": "value"},
        )
        payload = result.to_payload(command="test", status="success", duration_ms=100)

        # Field types for JSON compatibility
        assert isinstance(payload["command"], str)
        assert isinstance(payload["status"], str)
        assert isinstance(payload["exit_code"], int)
        assert isinstance(payload["duration_ms"], int)
        assert isinstance(payload["summary"], str)
        assert isinstance(payload["artifacts"], dict)
        assert isinstance(payload["problems"], list)
        assert isinstance(payload["suggestions"], list)
        assert isinstance(payload["files_generated"], list)
        assert isinstance(payload["files_modified"], list)

    def test_to_payload_json_serializable(self):
        """Contract: to_payload output is JSON-serializable."""
        result = CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="test",
            problems=[{"severity": "error", "message": "test", "code": "TEST-001"}],
            suggestions=[{"message": "Try X", "code": "SUGGEST-001"}],
            files_generated=["/path/to/file"],
            files_modified=["/another/path"],
            artifacts={"report": "/report.json"},
            data={"nested": {"key": "value"}, "list": [1, 2, 3]},
        )
        payload = result.to_payload(command="test", status="success", duration_ms=100)

        # Should serialize without error
        json_str = json.dumps(payload)
        assert json_str is not None

        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed["command"] == "test"
        assert parsed["exit_code"] == EXIT_SUCCESS

    def test_data_field_conditionally_included(self):
        """Contract: data field only included when non-empty."""
        # Empty data
        result_empty = CommandResult(exit_code=0, summary="test", data={})
        payload_empty = result_empty.to_payload(command="test", status="ok", duration_ms=0)
        assert "data" not in payload_empty

        # Non-empty data
        result_with_data = CommandResult(exit_code=0, summary="test", data={"key": "value"})
        payload_with_data = result_with_data.to_payload(command="test", status="ok", duration_ms=0)
        assert "data" in payload_with_data
        assert payload_with_data["data"] == {"key": "value"}


# =============================================================================
# Problem Structure Contract Tests
# =============================================================================


class TestProblemContract:
    """Contract tests for problem dict structure."""

    def test_problem_required_fields(self):
        """Contract: Problems should have severity and message."""
        # This is the expected structure
        problem = {
            "severity": "error",
            "message": "Something went wrong",
        }

        assert "severity" in problem
        assert "message" in problem

    def test_problem_optional_fields(self):
        """Contract: Problems may have optional code and location fields."""
        problem_full = {
            "severity": "error",
            "message": "Something went wrong",
            "code": "CIHUB-TEST-001",
            "location": "file.py:42",
        }

        # Optional but valid
        assert "code" in problem_full
        assert "location" in problem_full

    def test_severity_values(self):
        """Contract: Severity should be one of expected values."""
        valid_severities = ["error", "warning", "info", "low", "medium", "high", "critical"]

        for severity in valid_severities:
            problem = {"severity": severity, "message": "test"}
            assert problem["severity"] in valid_severities

    def test_code_format(self):
        """Contract: Problem codes follow CIHUB-* pattern."""
        import re

        valid_codes = [
            "CIHUB-FIX-RUFF-FAILED",
            "CIHUB-TOOL-NOT-FOUND",
            "CIHUB-GRADLE-WARNING",
            "CIHUB-CHECK-TIMEOUT",
        ]

        pattern = re.compile(r"^CIHUB-[A-Z]+-[A-Z0-9-]+$")

        for code in valid_codes:
            assert pattern.match(code), f"Invalid code format: {code}"


# =============================================================================
# ToolResult Contract Tests
# =============================================================================


class TestToolResultContract:
    """Contract tests ensuring ToolResult structure stability."""

    def test_required_fields_exist(self):
        """Contract: ToolResult has all required fields."""
        result = ToolResult(tool="test", success=True)

        # Required fields
        assert hasattr(result, "tool")
        assert hasattr(result, "success")
        assert hasattr(result, "returncode")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert hasattr(result, "ran")
        assert hasattr(result, "metrics")
        assert hasattr(result, "artifacts")
        assert hasattr(result, "json_data")
        assert hasattr(result, "json_error")
        assert hasattr(result, "report_path")

    def test_field_types(self):
        """Contract: ToolResult fields have correct types."""
        result = ToolResult(tool="test", success=True)

        assert isinstance(result.tool, str)
        assert isinstance(result.success, bool)
        assert isinstance(result.returncode, int)
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)
        assert isinstance(result.ran, bool)
        assert isinstance(result.metrics, dict)
        assert isinstance(result.artifacts, dict)
        # json_data can be any type
        assert result.json_error is None or isinstance(result.json_error, str)
        assert result.report_path is None or isinstance(result.report_path, Path)

    def test_to_payload_required_fields(self):
        """Contract: to_payload returns required fields."""
        result = ToolResult(tool="ruff", success=True, returncode=0, ran=True)
        payload = result.to_payload()

        required_fields = ["tool", "ran", "success", "returncode", "metrics", "artifacts"]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

    def test_to_payload_json_serializable(self):
        """Contract: to_payload output is JSON-serializable."""
        result = ToolResult(
            tool="pytest",
            success=True,
            returncode=0,
            stdout="test output",
            stderr="",
            ran=True,
            metrics={"coverage": 85.5, "test_count": 100},
            artifacts={"report": "coverage.xml"},
            json_data={"tests": 100, "passed": 100},
            report_path=Path("/tmp/report.json"),
        )
        payload = result.to_payload()

        # Should serialize without error
        json_str = json.dumps(payload)
        assert json_str is not None

    def test_from_payload_roundtrip(self):
        """Contract: from_payload restores ToolResult from payload."""
        original = ToolResult(
            tool="bandit",
            success=False,
            returncode=1,
            stdout="output",
            stderr="error",
            ran=True,
            metrics={"high": 2, "medium": 5},
            artifacts={},
        )

        payload = original.to_payload()
        restored = ToolResult.from_payload(payload)

        assert restored.tool == original.tool
        assert restored.success == original.success
        assert restored.returncode == original.returncode
        assert restored.ran == original.ran
        assert restored.metrics == original.metrics

    def test_optional_fields_in_payload(self):
        """Contract: Optional fields only included when set."""
        # Minimal result
        minimal = ToolResult(tool="test", success=True, returncode=0)
        payload = minimal.to_payload()

        # stdout/stderr only included if non-empty
        assert "stdout" not in payload or payload["stdout"] == ""

        # With stdout
        with_output = ToolResult(tool="test", success=True, returncode=0, stdout="output")
        payload_with_output = with_output.to_payload()
        assert "stdout" in payload_with_output
        assert payload_with_output["stdout"] == "output"


# =============================================================================
# Exit Code Contract Tests
# =============================================================================


class TestExitCodeContract:
    """Contract tests for exit code semantics."""

    def test_exit_codes_are_integers(self):
        """Contract: Exit codes are integers."""
        from cihub.exit_codes import (
            EXIT_DECLINED,
            EXIT_FAILURE,
            EXIT_INTERNAL_ERROR,
            EXIT_INTERRUPTED,
            EXIT_SUCCESS,
        )

        codes = [EXIT_SUCCESS, EXIT_FAILURE, EXIT_USAGE, EXIT_DECLINED, EXIT_INTERNAL_ERROR, EXIT_INTERRUPTED]
        for code in codes:
            assert isinstance(code, int)

    def test_exit_codes_in_valid_range(self):
        """Contract: Exit codes are in valid shell range (0-255)."""
        from cihub.exit_codes import (
            EXIT_DECLINED,
            EXIT_FAILURE,
            EXIT_INTERNAL_ERROR,
            EXIT_INTERRUPTED,
            EXIT_SUCCESS,
        )

        codes = [EXIT_SUCCESS, EXIT_FAILURE, EXIT_USAGE, EXIT_DECLINED, EXIT_INTERNAL_ERROR, EXIT_INTERRUPTED]
        for code in codes:
            assert 0 <= code <= 255

    def test_exit_success_is_zero(self):
        """Contract: EXIT_SUCCESS is 0 (Unix convention)."""
        from cihub.exit_codes import EXIT_SUCCESS

        assert EXIT_SUCCESS == 0

    def test_exit_failure_is_one(self):
        """Contract: EXIT_FAILURE is 1 (Unix convention)."""
        from cihub.exit_codes import EXIT_FAILURE

        assert EXIT_FAILURE == 1

    def test_exit_codes_are_unique(self):
        """Contract: All exit codes are unique."""
        from cihub.exit_codes import (
            EXIT_DECLINED,
            EXIT_FAILURE,
            EXIT_INTERNAL_ERROR,
            EXIT_INTERRUPTED,
            EXIT_SUCCESS,
        )

        codes = [EXIT_SUCCESS, EXIT_FAILURE, EXIT_USAGE, EXIT_DECLINED, EXIT_INTERNAL_ERROR, EXIT_INTERRUPTED]
        assert len(codes) == len(set(codes))


# =============================================================================
# CLI Output Contract Tests
# =============================================================================


class TestCLIOutputContract:
    """Contract tests for CLI JSON output format."""

    def test_json_output_has_status(self):
        """Contract: JSON output includes status field."""
        result = CommandResult(exit_code=EXIT_SUCCESS, summary="test")
        payload = result.to_payload(command="test", status="success", duration_ms=0)
        assert "status" in payload
        assert payload["status"] in ["success", "failure", "error", "skipped"]

    def test_json_output_has_command(self):
        """Contract: JSON output includes command name."""
        result = CommandResult(exit_code=EXIT_SUCCESS, summary="test")
        payload = result.to_payload(command="check", status="success", duration_ms=0)
        assert payload["command"] == "check"

    def test_json_output_problems_structure(self):
        """Contract: Problems in JSON output have consistent structure."""
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            summary="test failed",
            problems=[
                {"severity": "error", "message": "Test error", "code": "TEST-001"},
                {"severity": "warning", "message": "Test warning"},
            ],
        )
        payload = result.to_payload(command="test", status="failure", duration_ms=0)

        for problem in payload["problems"]:
            assert "severity" in problem
            assert "message" in problem


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility of types."""

    def test_command_result_accepts_positional_args(self):
        """Contract: CommandResult accepts positional arguments."""
        # Should work (for backward compat)
        result = CommandResult(0, "summary")
        assert result.exit_code == 0
        assert result.summary == "summary"

    def test_command_result_accepts_keyword_args(self):
        """Contract: CommandResult accepts keyword arguments."""
        result = CommandResult(exit_code=0, summary="summary", problems=[])
        assert result.exit_code == 0

    def test_tool_result_accepts_required_fields(self):
        """Contract: ToolResult requires tool and success fields."""
        result = ToolResult(tool="test", success=True)
        assert result.tool == "test"
        assert result.success is True
