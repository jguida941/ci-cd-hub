"""Parser setup for command registry commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_commands_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    commands = subparsers.add_parser("commands", help="Command registry helpers")
    commands.set_defaults(func=handlers.cmd_commands)
    commands_sub = commands.add_subparsers(dest="subcommand", required=True)

    commands_list = commands_sub.add_parser("list", help="List CLI commands and metadata")
    add_json_flag(commands_list)
    commands_list.set_defaults(func=handlers.cmd_commands)
