"""Parser setup for hub-ci Python smoke test subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import (
    add_output_args,
    add_path_args,
)


def add_smoke_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add Python smoke test subcommand parsers.

    Subcommands: smoke-python-install, smoke-python-tests,
    smoke-python-ruff, smoke-python-black
    """
    hub_ci_smoke_python_install = hub_ci_sub.add_parser(
        "smoke-python-install",
        help="Install dependencies for Python smoke tests",
    )
    add_path_args(hub_ci_smoke_python_install)
    add_json_flag(hub_ci_smoke_python_install)

    hub_ci_smoke_python_tests = hub_ci_sub.add_parser(
        "smoke-python-tests",
        help="Run Python smoke tests and extract metrics",
    )
    add_path_args(hub_ci_smoke_python_tests)
    hub_ci_smoke_python_tests.add_argument(
        "--output-file",
        default="test-output.txt",
        help="Output file for pytest logs",
    )
    add_output_args(hub_ci_smoke_python_tests)
    add_json_flag(hub_ci_smoke_python_tests)

    hub_ci_smoke_python_ruff = hub_ci_sub.add_parser(
        "smoke-python-ruff",
        help="Run Ruff for Python smoke tests",
    )
    add_path_args(hub_ci_smoke_python_ruff)
    hub_ci_smoke_python_ruff.add_argument(
        "--report",
        default="ruff-report.json",
        help="Output report path (relative to repo)",
    )
    add_output_args(hub_ci_smoke_python_ruff)
    add_json_flag(hub_ci_smoke_python_ruff)

    hub_ci_smoke_python_black = hub_ci_sub.add_parser(
        "smoke-python-black",
        help="Run Black for Python smoke tests",
    )
    add_path_args(hub_ci_smoke_python_black)
    hub_ci_smoke_python_black.add_argument(
        "--output-file",
        default="black-output.txt",
        help="Output file for Black logs",
    )
    add_output_args(hub_ci_smoke_python_black)
    add_json_flag(hub_ci_smoke_python_black)
