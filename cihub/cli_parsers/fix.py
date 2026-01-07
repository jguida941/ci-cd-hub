"""Parser setup for fix command."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import add_repo_args
from cihub.cli_parsers.types import CommandHandlers


def add_fix_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    fix = subparsers.add_parser(
        "fix",
        help="Run auto-fixers or report issues for manual review",
    )
    add_repo_args(fix)
    add_json_flag(fix)
    fix.set_defaults(func=handlers.cmd_fix)

    # Mutually exclusive: --safe or --report
    mode_group = fix.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--safe",
        action="store_true",
        help="Run all auto-fixers (ruff --fix, black, isort for Python; spotless for Java)",
    )
    mode_group.add_argument(
        "--report",
        action="store_true",
        help="Run all analyzers and report issues for manual review",
    )

    # AI output mode (only valid with --report)
    fix.add_argument(
        "--ai",
        action="store_true",
        help="Generate AI-consumable markdown report (with --report)",
    )

    # Dry run (only valid with --safe)
    fix.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes (with --safe)",
    )
