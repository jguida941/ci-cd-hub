"""Parser setup for hub-ci Java tool subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import (
    add_output_args,
    add_path_args,
)


def add_java_tools_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add Java tool subcommand parsers.

    Subcommands: codeql-build, smoke-java-build, smoke-java-tests,
    smoke-java-coverage, smoke-java-checkstyle, smoke-java-spotbugs
    """
    hub_ci_codeql_build = hub_ci_sub.add_parser(
        "codeql-build",
        help="Run Java build for CodeQL analysis",
    )
    add_path_args(hub_ci_codeql_build)
    add_json_flag(hub_ci_codeql_build)

    hub_ci_smoke_java_build = hub_ci_sub.add_parser(
        "smoke-java-build",
        help="Run Java smoke build/test",
    )
    add_path_args(hub_ci_smoke_java_build)
    add_json_flag(hub_ci_smoke_java_build)

    hub_ci_smoke_java_tests = hub_ci_sub.add_parser(
        "smoke-java-tests",
        help="Extract Java smoke test results",
    )
    add_path_args(hub_ci_smoke_java_tests)
    add_output_args(hub_ci_smoke_java_tests)
    add_json_flag(hub_ci_smoke_java_tests)

    hub_ci_smoke_java_coverage = hub_ci_sub.add_parser(
        "smoke-java-coverage",
        help="Extract Java smoke coverage metrics",
    )
    add_path_args(hub_ci_smoke_java_coverage)
    add_output_args(hub_ci_smoke_java_coverage)
    add_json_flag(hub_ci_smoke_java_coverage)

    hub_ci_smoke_java_checkstyle = hub_ci_sub.add_parser(
        "smoke-java-checkstyle",
        help="Run Checkstyle and extract violations",
    )
    add_path_args(hub_ci_smoke_java_checkstyle)
    add_output_args(hub_ci_smoke_java_checkstyle)
    add_json_flag(hub_ci_smoke_java_checkstyle)

    hub_ci_smoke_java_spotbugs = hub_ci_sub.add_parser(
        "smoke-java-spotbugs",
        help="Run SpotBugs and extract issues",
    )
    add_path_args(hub_ci_smoke_java_spotbugs)
    add_output_args(hub_ci_smoke_java_spotbugs)
    add_json_flag(hub_ci_smoke_java_spotbugs)
