"""Property-based tests for CLI output structures using Hypothesis.

These tests verify invariants for CommandResult, ToolResult, exit codes,
and CLI output formatting.
"""

# TEST-METRICS:

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.exit_codes import (
    EXIT_DECLINED,
    EXIT_FAILURE,
    EXIT_INTERNAL_ERROR,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from cihub.types import CommandResult, ToolResult

# =============================================================================
# Strategy Definitions
# =============================================================================

# Strategy for valid exit codes
exit_code_strategy = st.sampled_from(
    [EXIT_SUCCESS, EXIT_FAILURE, EXIT_USAGE, EXIT_DECLINED, EXIT_INTERNAL_ERROR, EXIT_INTERRUPTED]
)

# Strategy for command names
command_name_strategy = st.sampled_from(
    [
        "check",
        "ci",
        "detect",
        "init",
        "triage",
        "verify",
        "validate",
        "config",
        "docs",
        "hub-ci",
        "report",
        "scaffold",
        "smoke",
    ]
)

# Strategy for message strings
message_strategy = st.text(min_size=0, max_size=200)

# Strategy for problem entries
problem_strategy = st.fixed_dictionaries(
    {
        "message": st.text(min_size=1, max_size=100),
        "severity": st.sampled_from(["error", "warning", "info"]),
    },
    optional={
        "file": st.text(min_size=1, max_size=50),
        "line": st.integers(min_value=1, max_value=10000),
    },
)

# Strategy for suggestion entries
suggestion_strategy = st.text(min_size=1, max_size=200)

# Strategy for file paths in output
file_path_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789/_-.",
    min_size=1,
    max_size=50,
)


# =============================================================================
# CommandResult Property Tests
# =============================================================================


class TestCommandResultCreationProperties:
    """Property tests for CommandResult creation."""

    @given(exit_code=exit_code_strategy)
    @settings(max_examples=50)
    def test_exit_code_preserved(self, exit_code: int) -> None:
        """Property: exit_code field is always preserved."""
        result = CommandResult(exit_code=exit_code)
        assert result.exit_code == exit_code

    @given(summary=message_strategy)
    @settings(max_examples=50)
    def test_summary_field_preserved(self, summary: str) -> None:
        """Property: summary field is always preserved."""
        result = CommandResult(summary=summary)
        assert result.summary == summary

    @given(
        exit_code=exit_code_strategy,
        summary=message_strategy,
        data=st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=10),
            values=st.one_of(st.integers(), st.text(max_size=20), st.booleans()),
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_data_field_preserved(self, exit_code: int, summary: str, data: dict[str, Any]) -> None:
        """Property: data field is preserved."""
        result = CommandResult(exit_code=exit_code, summary=summary, data=data)
        assert result.data == data


class TestCommandResultProblemsProperties:
    """Property tests for CommandResult problems handling."""

    @given(problems=st.lists(problem_strategy, min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_problems_always_list(self, problems: list[dict[str, Any]]) -> None:
        """Property: problems is always a list."""
        result = CommandResult(problems=problems)
        assert isinstance(result.problems, list)
        assert len(result.problems) == len(problems)

    @given(problems=st.lists(problem_strategy, min_size=1, max_size=5))
    @settings(max_examples=50)
    def test_problems_have_required_fields(self, problems: list[dict[str, Any]]) -> None:
        """Property: problem entries have required message and severity."""
        result = CommandResult(exit_code=EXIT_FAILURE, problems=problems)
        for problem in result.problems:
            assert "message" in problem
            assert "severity" in problem


class TestCommandResultSuggestionsProperties:
    """Property tests for CommandResult suggestions handling."""

    @given(suggestions=st.lists(problem_strategy, min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_suggestions_always_list(self, suggestions: list[dict[str, Any]]) -> None:
        """Property: suggestions is always a list (of dicts)."""
        result = CommandResult(suggestions=suggestions)
        assert isinstance(result.suggestions, list)
        assert len(result.suggestions) == len(suggestions)

    @given(
        suggestions=st.lists(problem_strategy, min_size=0, max_size=5),
        problems=st.lists(problem_strategy, min_size=0, max_size=5),
    )
    @settings(max_examples=50)
    def test_suggestions_and_problems_independent(
        self, suggestions: list[dict[str, Any]], problems: list[dict[str, Any]]
    ) -> None:
        """Property: suggestions and problems are independent lists."""
        result = CommandResult(problems=problems, suggestions=suggestions)
        assert len(result.problems) == len(problems)
        assert len(result.suggestions) == len(suggestions)


class TestCommandResultFilesProperties:
    """Property tests for CommandResult files handling."""

    @given(files=st.lists(file_path_strategy, min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_files_modified_always_list(self, files: list[str]) -> None:
        """Property: files_modified is always a list."""
        result = CommandResult(files_modified=files)
        assert isinstance(result.files_modified, list)
        assert len(result.files_modified) == len(files)

    @given(files=st.lists(file_path_strategy, min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_files_generated_always_list(self, files: list[str]) -> None:
        """Property: files_generated is always a list."""
        result = CommandResult(files_generated=files)
        assert isinstance(result.files_generated, list)
        assert len(result.files_generated) == len(files)


class TestCommandResultExitCodeProperties:
    """Property tests for CommandResult exit code semantics."""

    def test_default_exit_code_is_success(self) -> None:
        """Property: default exit_code is EXIT_SUCCESS (0)."""
        result = CommandResult()
        assert result.exit_code == EXIT_SUCCESS

    @given(exit_code=exit_code_strategy)
    @settings(max_examples=50)
    def test_exit_code_in_valid_range(self, exit_code: int) -> None:
        """Property: exit codes are in valid range."""
        result = CommandResult(exit_code=exit_code)
        assert 0 <= result.exit_code < 256


class TestCommandResultPayloadProperties:
    """Property tests for CommandResult to_payload serialization."""

    @given(
        exit_code=exit_code_strategy,
        summary=message_strategy,
    )
    @settings(max_examples=50)
    def test_to_payload_returns_dict(self, exit_code: int, summary: str) -> None:
        """Property: to_payload always returns a dict."""
        result = CommandResult(exit_code=exit_code, summary=summary)
        payload = result.to_payload(command="test", status="success", duration_ms=100)
        assert isinstance(payload, dict)

    @given(
        exit_code=exit_code_strategy,
        summary=message_strategy,
        problems=st.lists(problem_strategy, min_size=0, max_size=3),
    )
    @settings(max_examples=50)
    def test_payload_has_required_keys(self, exit_code: int, summary: str, problems: list[dict[str, Any]]) -> None:
        """Property: payload has required keys."""
        result = CommandResult(exit_code=exit_code, summary=summary, problems=problems)
        payload = result.to_payload(command="test", status="success", duration_ms=100)

        assert "command" in payload
        assert "status" in payload
        assert "exit_code" in payload
        assert "summary" in payload
        assert "problems" in payload
        assert "suggestions" in payload

    @given(exit_code=exit_code_strategy)
    @settings(max_examples=50)
    def test_payload_exit_code_matches_result(self, exit_code: int) -> None:
        """Property: payload exit_code matches result exit_code."""
        result = CommandResult(exit_code=exit_code)
        payload = result.to_payload(command="test", status="success", duration_ms=100)
        assert payload["exit_code"] == exit_code


class TestCommandResultIdempotencyProperties:
    """Property tests for CommandResult idempotency."""

    @given(
        exit_code=exit_code_strategy,
        summary=message_strategy,
        problems=st.lists(problem_strategy, min_size=0, max_size=3),
    )
    @settings(max_examples=30)
    def test_payload_serialization_idempotent(
        self, exit_code: int, summary: str, problems: list[dict[str, Any]]
    ) -> None:
        """Property: serializing twice gives same result."""
        result = CommandResult(exit_code=exit_code, summary=summary, problems=problems)
        payload1 = result.to_payload(command="test", status="success", duration_ms=100)
        payload2 = result.to_payload(command="test", status="success", duration_ms=100)
        assert payload1 == payload2


# =============================================================================
# ToolResult Property Tests
# =============================================================================


class TestToolResultProperties:
    """Property tests for ToolResult structure."""

    @given(
        tool=command_name_strategy,
        success=st.booleans(),
        returncode=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=50)
    def test_tool_result_fields_preserved(self, tool: str, success: bool, returncode: int) -> None:
        """Property: ToolResult fields are preserved."""
        result = ToolResult(tool=tool, success=success, returncode=returncode)
        assert result.tool == tool
        assert result.success == success
        assert result.returncode == returncode

    @given(
        tool=command_name_strategy,
        success=st.booleans(),
        metrics=st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=10),
            values=st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_tool_result_metrics_preserved(self, tool: str, success: bool, metrics: dict[str, Any]) -> None:
        """Property: ToolResult metrics are preserved."""
        result = ToolResult(tool=tool, success=success, metrics=metrics)
        assert result.metrics == metrics

    @given(tool=command_name_strategy, ran=st.booleans())
    @settings(max_examples=50)
    def test_tool_result_ran_field(self, tool: str, ran: bool) -> None:
        """Property: ToolResult ran field is preserved."""
        result = ToolResult(tool=tool, success=True, ran=ran)
        assert result.ran == ran
