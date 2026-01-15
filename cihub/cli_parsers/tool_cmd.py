"""Parser setup for tool management commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_tool_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    """Add tool command and subcommands.

    Tool commands manage CI tools (enable/disable, configure, validate).
    Tools are defined in cihub/tools/registry.py.
    """
    tool = subparsers.add_parser(
        "tool",
        help="Manage CI tools (list, enable, disable, configure)",
        epilog=see_also_epilog("tool"),
    )
    add_json_flag(tool)
    tool.set_defaults(func=handlers.cmd_tool)
    tool_sub = tool.add_subparsers(dest="subcommand", required=True)

    # tool list
    list_cmd = tool_sub.add_parser("list", help="List available tools")
    list_cmd.add_argument(
        "--language",
        choices=["python", "java"],
        help="Filter by language",
    )
    list_cmd.add_argument(
        "--category",
        choices=["lint", "security", "test", "format", "coverage", "mutation", "container"],
        help="Filter by category",
    )
    list_cmd.add_argument(
        "--enabled-only",
        action="store_true",
        help="Show only enabled tools (requires --repo)",
    )
    list_cmd.add_argument(
        "--repo",
        metavar="NAME",
        help="Show tool status for specific repo",
    )

    # tool enable <tool>
    enable = tool_sub.add_parser("enable", help="Enable a tool")
    enable.add_argument("tool", nargs="?", help="Tool name (e.g., mypy, mutmut, trivy)")
    enable.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode - select tool and target",
    )
    enable_target = enable.add_mutually_exclusive_group()
    enable_target.add_argument(
        "--for-repo",
        metavar="NAME",
        help="Enable for specific repo only",
    )
    enable_target.add_argument(
        "--all-repos",
        action="store_true",
        help="Enable for all repos in registry",
    )
    enable_target.add_argument(
        "--profile",
        metavar="NAME",
        help="Enable in a profile instead of repo",
    )

    # tool disable <tool>
    disable = tool_sub.add_parser("disable", help="Disable a tool")
    disable.add_argument("tool", nargs="?", help="Tool name (e.g., mypy, mutmut, trivy)")
    disable.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode - select tool and target",
    )
    disable_target = disable.add_mutually_exclusive_group()
    disable_target.add_argument(
        "--for-repo",
        metavar="NAME",
        help="Disable for specific repo only",
    )
    disable_target.add_argument(
        "--all-repos",
        action="store_true",
        help="Disable for all repos in registry",
    )
    disable_target.add_argument(
        "--profile",
        metavar="NAME",
        help="Disable in a profile instead of repo",
    )

    # tool configure <tool> <param> <value>
    configure = tool_sub.add_parser("configure", help="Configure a tool setting")
    configure.add_argument("tool", nargs="?", help="Tool name (e.g., pytest, bandit)")
    configure.add_argument("param", nargs="?", help="Parameter name (e.g., min_coverage, fail_on_high)")
    configure.add_argument("value", nargs="?", help="Parameter value")
    configure.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode - select tool, parameter, value",
    )
    configure_target = configure.add_mutually_exclusive_group()
    configure_target.add_argument(
        "--repo",
        metavar="NAME",
        help="Configure for specific repo",
    )
    configure_target.add_argument(
        "--profile",
        metavar="NAME",
        help="Configure in a profile",
    )

    # tool status
    status = tool_sub.add_parser("status", help="Show tool status")
    status.add_argument(
        "--repo",
        metavar="NAME",
        help="Show status for specific repo",
    )
    status.add_argument(
        "--all",
        action="store_true",
        help="Show status for all repos",
    )
    status.add_argument(
        "--language",
        choices=["python", "java"],
        help="Filter by language",
    )

    # tool validate <tool>
    validate = tool_sub.add_parser("validate", help="Validate tool installation")
    validate.add_argument("tool", help="Tool name to validate")
    validate.add_argument(
        "--install-if-missing",
        action="store_true",
        help="Attempt to install if not found",
    )

    # tool info <tool>
    info = tool_sub.add_parser("info", help="Show detailed tool information")
    info.add_argument("tool", help="Tool name")

    # Support `cihub tool <subcommand> --json`
    for subparser in tool_sub.choices.values():
        add_json_flag(subparser)
