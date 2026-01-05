"""Tests for CLI argument factory functions.

These tests verify that the shared argument factories correctly add
arguments to parsers, eliminating 36+ duplicate definitions.

★ Insight ─────────────────────────────────────
Test design follows the parameterized pattern from test_language_strategies.py:
1. Test each factory function adds expected arguments
2. Test argument properties (required, default, help text)
3. Use fixtures for parser setup to reduce boilerplate
─────────────────────────────────────────────────
"""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Any, Callable

import pytest

from cihub.cli_parsers.common import (
    add_ci_output_args,
    add_output_args,
    add_output_dir_args,
    add_path_args,
    add_repo_args,
    add_report_args,
    add_summary_args,
    add_tool_runner_args,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def parser() -> ArgumentParser:
    """Fresh ArgumentParser for each test."""
    return ArgumentParser(prog="test")


def get_action(parser: ArgumentParser, dest: str):
    """Get an action by destination name from a parser."""
    for action in parser._actions:
        if action.dest == dest:
            return action
    return None


# =============================================================================
# Parameterized Factory Tests
# =============================================================================


class TestArgumentFactories:
    """Parameterized tests for all argument factory functions."""

    @pytest.mark.parametrize(
        "factory,expected_dests",
        [
            (add_output_args, ["output", "github_output"]),
            (add_summary_args, ["summary"]),
            (add_repo_args, ["repo"]),
            (add_report_args, ["report"]),
            (add_path_args, ["path"]),
            (add_output_dir_args, ["output_dir"]),
            (add_ci_output_args, ["output", "github_output", "summary"]),
            (add_tool_runner_args, ["path", "output", "github_output"]),
        ],
        ids=[
            "output_args",
            "summary_args",
            "repo_args",
            "report_args",
            "path_args",
            "output_dir_args",
            "ci_output_args",
            "tool_runner_args",
        ],
    )
    def test_factory_adds_expected_arguments(
        self, parser: ArgumentParser, factory: Callable, expected_dests: list[str]
    ) -> None:
        """Property: each factory adds its expected argument destinations."""
        factory(parser)

        actual_dests = {a.dest for a in parser._actions if a.dest != "help"}
        for dest in expected_dests:
            assert dest in actual_dests, f"Expected {dest} in {actual_dests}"

    @pytest.mark.parametrize(
        "factory,dest,expected_default",
        [
            (add_repo_args, "repo", "."),
            (add_path_args, "path", "repo"),
            (add_output_dir_args, "output_dir", "."),
            (add_output_args, "output", None),
            (add_summary_args, "summary", None),
        ],
        ids=["repo", "path", "output_dir", "output", "summary"],
    )
    def test_factory_default_values(
        self,
        parser: ArgumentParser,
        factory: Callable,
        dest: str,
        expected_default: Any,
    ) -> None:
        """Property: factories set correct default values."""
        factory(parser)
        action = get_action(parser, dest)
        assert action is not None
        assert action.default == expected_default


class TestOutputArgsFactory:
    """Tests for add_output_args with various options."""

    def test_output_args_default(self, parser: ArgumentParser) -> None:
        """Default add_output_args adds both --output and --github-output."""
        add_output_args(parser)

        output = get_action(parser, "output")
        github_output = get_action(parser, "github_output")

        assert output is not None
        assert github_output is not None
        assert output.help == "Write outputs to file"
        assert github_output.const is True  # store_true action

    def test_output_args_custom_help(self, parser: ArgumentParser) -> None:
        """Custom help text is applied to --output."""
        add_output_args(parser, output_help="Custom output help")
        output = get_action(parser, "output")
        assert output.help == "Custom output help"

    def test_output_args_without_github_output(self, parser: ArgumentParser) -> None:
        """include_github_output=False omits --github-output."""
        add_output_args(parser, include_github_output=False)

        output = get_action(parser, "output")
        github_output = get_action(parser, "github_output")

        assert output is not None
        assert github_output is None


class TestRepoArgsFactory:
    """Tests for add_repo_args with required and default options."""

    @pytest.mark.parametrize(
        "required,default,expected_required",
        [
            (False, ".", False),
            (True, None, True),
            (False, "repo", False),
        ],
        ids=["optional_dot", "required", "optional_repo"],
    )
    def test_repo_args_required_handling(
        self,
        parser: ArgumentParser,
        required: bool,
        default: str | None,
        expected_required: bool,
    ) -> None:
        """Property: required flag controls whether --repo is mandatory."""
        add_repo_args(parser, required=required, default=default)
        action = get_action(parser, "repo")
        assert action.required == expected_required

    def test_repo_args_help_includes_default(self, parser: ArgumentParser) -> None:
        """Help text includes default value when not required."""
        add_repo_args(parser, default=".")
        action = get_action(parser, "repo")
        assert "(default: .)" in action.help


class TestReportArgsFactory:
    """Tests for add_report_args."""

    def test_report_args_required(self, parser: ArgumentParser) -> None:
        """required=True makes --report mandatory."""
        add_report_args(parser, required=True)
        action = get_action(parser, "report")
        assert action.required is True

    def test_report_args_optional_with_default(self, parser: ArgumentParser) -> None:
        """Optional report with custom default."""
        add_report_args(parser, default="report.json")
        action = get_action(parser, "report")
        assert action.required is False
        assert action.default == "report.json"


class TestCompositeFactories:
    """Tests for composite factory functions."""

    def test_ci_output_args_adds_all(self, parser: ArgumentParser) -> None:
        """add_ci_output_args adds output, github_output, and summary."""
        add_ci_output_args(parser)
        dests = {a.dest for a in parser._actions}
        assert "output" in dests
        assert "github_output" in dests
        assert "summary" in dests

    def test_tool_runner_args_custom_path(self, parser: ArgumentParser) -> None:
        """add_tool_runner_args respects path_default parameter."""
        add_tool_runner_args(parser, path_default=".")
        action = get_action(parser, "path")
        assert action.default == "."


# =============================================================================
# Integration Tests: Verify parseable arguments
# =============================================================================


class TestArgumentParsing:
    """Integration tests that verify arguments can be parsed."""

    @pytest.mark.parametrize(
        "factory,args,expected",
        [
            (add_output_args, ["--output", "out.txt"], {"output": "out.txt"}),
            (add_output_args, ["--github-output"], {"github_output": True}),
            (add_summary_args, ["--summary", "summary.md"], {"summary": "summary.md"}),
            (add_repo_args, ["--repo", "/path/to/repo"], {"repo": "/path/to/repo"}),
            (add_repo_args, [], {"repo": "."}),  # default
            (add_path_args, [], {"path": "repo"}),  # default
        ],
        ids=[
            "output_value",
            "github_output_flag",
            "summary_value",
            "repo_value",
            "repo_default",
            "path_default",
        ],
    )
    def test_parse_args(
        self,
        parser: ArgumentParser,
        factory: Callable,
        args: list[str],
        expected: dict[str, Any],
    ) -> None:
        """Property: factories create parseable arguments with correct values."""
        factory(parser)
        parsed = parser.parse_args(args)
        for key, value in expected.items():
            assert getattr(parsed, key) == value
