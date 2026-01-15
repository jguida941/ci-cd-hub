"""Parser setup for hub-ci Python tool subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import (
    add_output_args,
    add_output_dir_args,
    add_path_args,
    add_summary_args,
)


def add_python_tools_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add Python tool subcommand parsers.

    Subcommands: ruff, ruff-format, black, mypy, mutmut, coverage-verify
    """
    hub_ci_ruff = hub_ci_sub.add_parser("ruff", help="Run ruff and emit issue count")
    add_path_args(hub_ci_ruff, default=".", help_text="Path to lint")
    hub_ci_ruff.add_argument("--force-exclude", action="store_true", help="Force ruff exclude rules")
    add_output_args(hub_ci_ruff)
    add_json_flag(hub_ci_ruff)

    hub_ci_ruff_format = hub_ci_sub.add_parser(
        "ruff-format",
        help="Run ruff formatter in check mode (fails if formatting is needed)",
    )
    add_path_args(hub_ci_ruff_format, default=".", help_text="Path to format check")
    hub_ci_ruff_format.add_argument("--force-exclude", action="store_true", help="Force ruff exclude rules")
    add_output_args(hub_ci_ruff_format)
    add_json_flag(hub_ci_ruff_format)

    hub_ci_black = hub_ci_sub.add_parser("black", help="Run black and emit issue count")
    add_path_args(hub_ci_black, default=".", help_text="Path to check")
    add_output_args(hub_ci_black)
    add_json_flag(hub_ci_black)

    hub_ci_mypy = hub_ci_sub.add_parser("mypy", help="Run mypy type checking")
    add_path_args(hub_ci_mypy, default="cihub", help_text="Path to type check")
    hub_ci_mypy.add_argument(
        "--no-ignore-missing-imports",
        action="store_false",
        dest="ignore_missing_imports",
        help="Do not ignore missing imports (default: ignore missing imports)",
    )
    hub_ci_mypy.add_argument(
        "--no-show-error-codes",
        action="store_false",
        dest="show_error_codes",
        help="Do not show error codes (default: show error codes)",
    )
    add_output_args(hub_ci_mypy)
    add_json_flag(hub_ci_mypy)

    hub_ci_mutmut = hub_ci_sub.add_parser("mutmut", help="Run mutmut and emit summary outputs")
    hub_ci_mutmut.add_argument("--workdir", default=".", help="Workdir to scan")
    add_output_dir_args(hub_ci_mutmut, help_text="Directory for mutmut logs")
    hub_ci_mutmut.add_argument(
        "--min-mutation-score",
        "--min-score",
        dest="min_mutation_score",
        type=int,
        default=70,
        help="Minimum mutation score",
    )
    add_output_args(hub_ci_mutmut)
    add_summary_args(hub_ci_mutmut)
    hub_ci_mutmut.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_mutmut)

    hub_ci_coverage_verify = hub_ci_sub.add_parser(
        "coverage-verify",
        help="Verify coverage database exists and is readable for mutation testing",
    )
    hub_ci_coverage_verify.add_argument(
        "--coverage-file",
        default=".coverage",
        help="Path to coverage database file",
    )
    add_output_args(hub_ci_coverage_verify)
    add_summary_args(hub_ci_coverage_verify)
    hub_ci_coverage_verify.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_coverage_verify)
