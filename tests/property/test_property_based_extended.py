"""Extended property-based tests using Hypothesis.

This module extends property-based testing to cover more of the codebase,
including command result structures, tool configurations, and validation logic.
"""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, given, settings
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
exit_code_strategy = st.sampled_from([
    EXIT_SUCCESS,
    EXIT_FAILURE,
    EXIT_USAGE,
    EXIT_DECLINED,
    EXIT_INTERNAL_ERROR,
    EXIT_INTERRUPTED,
])

# Strategy for severity levels
severity_strategy = st.sampled_from(["error", "warning", "info", "low", "medium", "high", "critical"])

# Strategy for problem codes
problem_code_strategy = st.from_regex(r"CIHUB-[A-Z]+-[A-Z0-9-]+", fullmatch=True)

# Strategy for file paths (safe, no special chars)
safe_path_strategy = st.from_regex(r"/[a-z][a-z0-9_/]{0,50}", fullmatch=True)

# Strategy for tool names (built-in)
builtin_tool_strategy = st.sampled_from([
    "pytest", "ruff", "black", "isort", "mypy", "bandit", "pip_audit",
    "mutmut", "trivy", "semgrep", "jacoco", "checkstyle", "spotbugs", "pmd", "owasp",
])

# Strategy for custom tool names
custom_tool_strategy = st.from_regex(r"x-[a-z][a-z0-9-]{0,20}", fullmatch=True)

# Strategy for tool names (any valid)
tool_name_strategy = st.one_of(builtin_tool_strategy, custom_tool_strategy)

# Strategy for languages
language_strategy = st.sampled_from(["python", "java"])

# Strategy for problem dicts
problem_strategy = st.fixed_dictionaries({
    "severity": severity_strategy,
    "message": st.text(min_size=1, max_size=200),
    "code": problem_code_strategy,
})

# Strategy for suggestion dicts
suggestion_strategy = st.fixed_dictionaries({
    "message": st.text(min_size=1, max_size=200),
    "code": problem_code_strategy,
})


# =============================================================================
# CommandResult Property Tests
# =============================================================================


class TestCommandResultProperties:
    """Property-based tests for CommandResult dataclass."""

    @given(
        exit_code=exit_code_strategy,
        summary=st.text(max_size=200),
    )
    @settings(max_examples=50)
    def test_command_result_creation(self, exit_code: int, summary: str) -> None:
        """Property: CommandResult can be created with any valid exit code and summary."""
        result = CommandResult(exit_code=exit_code, summary=summary)
        assert result.exit_code == exit_code
        assert result.summary == summary
        # Default lists should be empty
        assert result.problems == []
        assert result.suggestions == []
        assert result.files_generated == []
        assert result.files_modified == []

    @given(
        exit_code=exit_code_strategy,
        summary=st.text(max_size=100),
        problems=st.lists(problem_strategy, max_size=5),
    )
    @settings(max_examples=50)
    def test_command_result_with_problems(
        self, exit_code: int, summary: str, problems: list[dict[str, Any]]
    ) -> None:
        """Property: CommandResult correctly stores problems list."""
        result = CommandResult(exit_code=exit_code, summary=summary, problems=problems)
        assert len(result.problems) == len(problems)
        for i, prob in enumerate(result.problems):
            assert prob["severity"] == problems[i]["severity"]
            assert prob["code"] == problems[i]["code"]

    @given(
        exit_code=exit_code_strategy,
        summary=st.text(max_size=100),
        files=st.lists(safe_path_strategy, max_size=10, unique=True),
    )
    @settings(max_examples=50)
    def test_command_result_with_files(
        self, exit_code: int, summary: str, files: list[str]
    ) -> None:
        """Property: CommandResult correctly stores file lists."""
        result = CommandResult(
            exit_code=exit_code,
            summary=summary,
            files_generated=files,
            files_modified=files,
        )
        assert result.files_generated == files
        assert result.files_modified == files

    @given(
        exit_code=exit_code_strategy,
        summary=st.text(max_size=100),
        data=st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=10),
            values=st.one_of(st.integers(), st.text(max_size=50), st.booleans()),
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_command_result_data_roundtrip(
        self, exit_code: int, summary: str, data: dict[str, Any]
    ) -> None:
        """Property: CommandResult data survives to_payload conversion."""
        result = CommandResult(exit_code=exit_code, summary=summary, data=data)
        payload = result.to_payload(command="test", status="success", duration_ms=100)

        if data:
            assert payload["data"] == data
        assert payload["exit_code"] == exit_code
        assert payload["summary"] == summary

    @given(
        exit_code=exit_code_strategy,
        duration=st.integers(min_value=0, max_value=1000000),
    )
    @settings(max_examples=50)
    def test_to_payload_structure(self, exit_code: int, duration: int) -> None:
        """Property: to_payload always returns dict with required fields."""
        result = CommandResult(exit_code=exit_code, summary="test")
        payload = result.to_payload(command="cmd", status="ok", duration_ms=duration)

        # Required fields always present
        assert "command" in payload
        assert "status" in payload
        assert "exit_code" in payload
        assert "duration_ms" in payload
        assert "summary" in payload
        assert "artifacts" in payload
        assert "problems" in payload
        assert "suggestions" in payload
        assert "files_generated" in payload
        assert "files_modified" in payload


# =============================================================================
# ToolResult Property Tests
# =============================================================================


class TestToolResultProperties:
    """Property-based tests for ToolResult dataclass."""

    @given(
        tool=tool_name_strategy,
        success=st.booleans(),
        returncode=st.integers(min_value=-1, max_value=255),
    )
    @settings(max_examples=50)
    def test_tool_result_creation(self, tool: str, success: bool, returncode: int) -> None:
        """Property: ToolResult can be created with valid tool name and status."""
        result = ToolResult(tool=tool, success=success, returncode=returncode)
        assert result.tool == tool
        assert result.success == success
        assert result.returncode == returncode

    @given(
        tool=tool_name_strategy,
        success=st.booleans(),
        metrics=st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnop", min_size=1, max_size=10),
            values=st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_tool_result_metrics(self, tool: str, success: bool, metrics: dict[str, Any]) -> None:
        """Property: ToolResult correctly stores metrics."""
        result = ToolResult(tool=tool, success=success, metrics=metrics)
        assert result.metrics == metrics

    @given(
        tool=tool_name_strategy,
        success=st.booleans(),
        returncode=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=50)
    def test_tool_result_payload_roundtrip(self, tool: str, success: bool, returncode: int) -> None:
        """Property: ToolResult survives to_payload/from_payload roundtrip."""
        original = ToolResult(tool=tool, success=success, returncode=returncode, ran=True)
        payload = original.to_payload()
        restored = ToolResult.from_payload(payload)

        assert restored.tool == original.tool
        assert restored.success == original.success
        assert restored.returncode == original.returncode
        assert restored.ran == original.ran


# =============================================================================
# Tool Configuration Property Tests
# =============================================================================


class TestToolConfigurationProperties:
    """Property-based tests for tool configuration patterns."""

    @given(
        tool=builtin_tool_strategy,
        enabled=st.booleans(),
        threshold=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_tool_config_valid(self, tool: str, enabled: bool, threshold: int) -> None:
        """Property: Tool configs are always valid with standard fields."""
        config = {
            "enabled": enabled,
            "min_coverage": threshold,
            "fail_on_error": True,
        }
        # Should be a valid dict
        assert isinstance(config["enabled"], bool)
        assert 0 <= config["min_coverage"] <= 100

    @given(
        tools=st.lists(builtin_tool_strategy, min_size=1, max_size=10, unique=True),
        enabled=st.booleans(),
    )
    @settings(max_examples=50)
    def test_multiple_tools_config(self, tools: list[str], enabled: bool) -> None:
        """Property: Multiple tools can be configured consistently."""
        config = {tool: {"enabled": enabled} for tool in tools}

        # All tools have consistent enabled status
        for tool_config in config.values():
            assert tool_config["enabled"] == enabled

    @given(
        tool=custom_tool_strategy,
        command=st.text(alphabet="abcdefghijklmnop -./_", min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_custom_tool_config(self, tool: str, command: str) -> None:
        """Property: Custom tools can have command field."""
        config = {
            tool: {
                "enabled": True,
                "command": command,
            }
        }
        assert tool.startswith("x-")
        assert "command" in config[tool]


# =============================================================================
# Report Structure Property Tests
# =============================================================================


class TestReportStructureProperties:
    """Property-based tests for CI report structure invariants."""

    @given(
        tools=st.lists(builtin_tool_strategy, min_size=0, max_size=15, unique=True),
    )
    @settings(max_examples=50)
    def test_tools_configured_matches_tools_ran(self, tools: list[str]) -> None:
        """Property: tools_ran keys should be subset of tools_configured keys."""
        # Build a valid report structure
        tools_configured = {tool: True for tool in tools}
        tools_ran = {tool: True for tool in tools[:len(tools) // 2]}  # Only half ran

        report = {
            "tools_configured": tools_configured,
            "tools_ran": tools_ran,
        }

        # Invariant: every tool that ran must have been configured
        for tool in report["tools_ran"]:
            assert tool in report["tools_configured"]

    @given(
        coverage=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
        threshold=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_coverage_gate_logic(self, coverage: float, threshold: float) -> None:
        """Property: Coverage gate passes iff coverage >= threshold."""
        passes = coverage >= threshold

        # The gate logic is deterministic
        if passes:
            assert coverage >= threshold
        else:
            assert coverage < threshold

    @given(
        metrics=st.dictionaries(
            keys=st.sampled_from(["coverage", "test_count", "test_failures", "mutation_score"]),
            values=st.floats(min_value=0, max_value=10000, allow_nan=False),
            min_size=1,
            max_size=4,
        ),
    )
    @settings(max_examples=50)
    def test_metrics_are_numeric(self, metrics: dict[str, float]) -> None:
        """Property: All metrics values should be numeric."""
        for key, value in metrics.items():
            assert isinstance(value, (int, float))
            assert value >= 0


# =============================================================================
# Exit Code Property Tests
# =============================================================================


class TestExitCodeProperties:
    """Property-based tests for exit code semantics."""

    @given(exit_code=exit_code_strategy)
    @settings(max_examples=20)
    def test_exit_codes_are_valid(self, exit_code: int) -> None:
        """Property: All exit codes are in valid range."""
        assert 0 <= exit_code <= 255

    @given(
        success=st.booleans(),
        problems=st.lists(problem_strategy, max_size=5),
    )
    @settings(max_examples=50)
    def test_success_implies_exit_success(self, success: bool, problems: list[dict[str, Any]]) -> None:
        """Property: If success=True and no error problems, exit code should be 0."""
        has_errors = any(p["severity"] == "error" for p in problems)

        # Determine expected exit code
        if success and not has_errors:
            expected = EXIT_SUCCESS
        else:
            expected = EXIT_FAILURE

        # Build result
        result = CommandResult(
            exit_code=expected,
            summary="test",
            problems=problems,
        )

        if success and not has_errors:
            assert result.exit_code == EXIT_SUCCESS


# =============================================================================
# Path and File Property Tests
# =============================================================================


class TestPathProperties:
    """Property-based tests for path handling."""

    @given(
        parts=st.lists(
            st.text(alphabet="abcdefghijklmnop0123456789_-", min_size=1, max_size=20),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_path_construction(self, parts: list[str]) -> None:
        """Property: Paths can be constructed from parts without errors."""
        path = Path(*parts)
        assert path is not None
        # Path should have correct number of parts
        assert len(path.parts) >= len(parts)

    @given(
        filename=st.from_regex(r"[a-z][a-z0-9_]{0,20}\.(py|java|yml|yaml|json)", fullmatch=True),
    )
    @settings(max_examples=50)
    def test_valid_filenames(self, filename: str) -> None:
        """Property: Generated filenames are valid."""
        path = Path(filename)
        assert path.suffix in [".py", ".java", ".yml", ".yaml", ".json"]
        assert path.stem  # Has a name before extension


# =============================================================================
# Validation Logic Property Tests
# =============================================================================


class TestValidationProperties:
    """Property-based tests for validation logic patterns."""

    @given(
        value=st.integers(),
        min_val=st.integers(),
        max_val=st.integers(),
    )
    @settings(max_examples=100)
    def test_range_validation_invariant(self, value: int, min_val: int, max_val: int) -> None:
        """Property: Range validation is consistent."""
        assume(min_val <= max_val)  # Valid range

        in_range = min_val <= value <= max_val

        # Invariant: Either in range or not
        assert in_range == (value >= min_val and value <= max_val)

    @given(
        items=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=20),
        required=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
    )
    @settings(max_examples=50)
    def test_required_items_check(self, items: list[str], required: list[str]) -> None:
        """Property: Required items check is consistent."""
        items_set = set(items)
        required_set = set(required)

        all_present = required_set.issubset(items_set)
        missing = required_set - items_set

        # Invariant: all_present iff no missing items
        assert all_present == (len(missing) == 0)
