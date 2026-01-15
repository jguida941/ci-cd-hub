"""CLI parser for threshold management commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_threshold_commands(
    subparsers: argparse._SubParsersAction,  # noqa: SLF001
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    """Add threshold management commands to the CLI."""
    threshold = subparsers.add_parser(
        "threshold",
        help="Manage CI thresholds (coverage, mutation, security limits)",
        epilog=see_also_epilog("threshold"),
    )
    add_json_flag(threshold)
    threshold.set_defaults(func=handlers.cmd_threshold)

    threshold_sub = threshold.add_subparsers(dest="subcommand", required=True)

    # threshold get [<key>] [--repo <name>] [--effective]
    get_parser = threshold_sub.add_parser(
        "get",
        help="Get threshold value(s)",
    )
    add_json_flag(get_parser)
    get_parser.add_argument(
        "key",
        nargs="?",
        help="Threshold key (e.g., coverage_min, max_critical_vulns). Omit for all.",
    )
    get_parser.add_argument(
        "--repo",
        metavar="NAME",
        help="Get threshold for specific repo",
    )
    get_parser.add_argument(
        "--tier",
        metavar="NAME",
        help="Get threshold for specific tier",
    )
    get_parser.add_argument(
        "--effective",
        action="store_true",
        help="Show effective value (with tier/profile inheritance)",
    )

    # threshold set <key> <value> [--repo <name>] [--tier <name>] [--all-repos]
    set_parser = threshold_sub.add_parser(
        "set",
        help="Set a threshold value",
    )
    add_json_flag(set_parser)
    set_parser.add_argument(
        "key",
        nargs="?",
        help="Threshold key (e.g., coverage_min, max_critical_vulns)",
    )
    set_parser.add_argument(
        "value",
        nargs="?",
        help="Threshold value (integer or float for CVSS thresholds)",
    )
    set_parser.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode - select key and value",
    )
    set_parser.add_argument(
        "--repo",
        metavar="NAME",
        help="Set threshold for specific repo (as override)",
    )
    set_parser.add_argument(
        "--tier",
        metavar="NAME",
        help="Set threshold for specific tier",
    )
    set_parser.add_argument(
        "--all-repos",
        action="store_true",
        help="Set threshold for all repos as overrides",
    )

    # threshold list [--category <cat>] [--repo <name>]
    list_parser = threshold_sub.add_parser(
        "list",
        help="List all threshold keys with defaults and descriptions",
    )
    add_json_flag(list_parser)
    list_parser.add_argument(
        "--category",
        choices=["coverage", "security", "lint", "mutation"],
        help="Filter by threshold category",
    )
    list_parser.add_argument(
        "--repo",
        metavar="NAME",
        help="Show thresholds for specific repo",
    )
    list_parser.add_argument(
        "--diff",
        action="store_true",
        help="Show only non-default values",
    )

    # threshold reset [<key>] [--repo <name>] [--tier <name>]
    reset_parser = threshold_sub.add_parser(
        "reset",
        help="Reset threshold(s) to default",
    )
    add_json_flag(reset_parser)
    reset_parser.add_argument(
        "key",
        nargs="?",
        help="Threshold key to reset. Omit for all.",
    )
    reset_parser.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode - select threshold and target",
    )
    reset_parser.add_argument(
        "--repo",
        metavar="NAME",
        help="Reset threshold for specific repo",
    )
    reset_parser.add_argument(
        "--tier",
        metavar="NAME",
        help="Reset threshold for specific tier",
    )
    reset_parser.add_argument(
        "--all-repos",
        action="store_true",
        help="Reset threshold for all repos",
    )

    # threshold compare <repo1> <repo2>
    compare_parser = threshold_sub.add_parser(
        "compare",
        help="Compare thresholds between two repos",
    )
    add_json_flag(compare_parser)
    compare_parser.add_argument(
        "repo1",
        help="First repo name",
    )
    compare_parser.add_argument(
        "repo2",
        help="Second repo name",
    )
    compare_parser.add_argument(
        "--effective",
        action="store_true",
        help="Compare effective values (with tier/profile inheritance)",
    )
