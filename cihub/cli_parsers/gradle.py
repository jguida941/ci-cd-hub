"""Parser setup for Gradle helper commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_gradle_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    fix_gradle = subparsers.add_parser(
        "fix-gradle",
        help="Add missing Gradle plugins to build.gradle for Java repos",
    )
    add_json_flag(fix_gradle)
    fix_gradle.add_argument("--repo", required=True, help="Path to repo")
    fix_gradle.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default: dry-run diff)",
    )
    fix_gradle.add_argument(
        "--with-configs",
        action="store_true",
        help="Also insert plugin configuration blocks",
    )
    fix_gradle.set_defaults(func=handlers.cmd_fix_gradle)
