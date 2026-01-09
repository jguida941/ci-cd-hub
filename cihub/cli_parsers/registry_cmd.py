"""Parser setup for registry commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_registry_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    """Add registry command and subcommands."""
    registry = subparsers.add_parser(
        "registry",
        help="Centralized repo configuration management with tier system",
    )
    add_json_flag(registry)
    registry.set_defaults(func=handlers.cmd_registry)
    registry_sub = registry.add_subparsers(dest="subcommand", required=True)

    # registry list
    _list = registry_sub.add_parser("list", help="List all repos with their tiers")
    _list.add_argument("--tier", help="Filter by tier name")

    # registry show <repo>
    show = registry_sub.add_parser("show", help="Show detailed config for a repo")
    show.add_argument("repo", help="Repository name")

    # registry set <repo> --tier <tier> | --coverage N | --mutation N | --vulns-max N
    set_cmd = registry_sub.add_parser("set", help="Set tier or override for a repo")
    set_cmd.add_argument("repo", help="Repository name")
    set_cmd.add_argument("--tier", help="Set tier (strict, standard, relaxed)")
    set_cmd.add_argument("--coverage", type=int, metavar="N", help="Override coverage threshold")
    set_cmd.add_argument("--mutation", type=int, metavar="N", help="Override mutation score threshold")
    set_cmd.add_argument("--vulns-max", type=int, metavar="N", dest="vulns_max", help="Override max vulnerabilities")

    # registry diff
    diff = registry_sub.add_parser("diff", help="Show drift from tier defaults vs actual configs")
    diff.add_argument("--configs-dir", help="Path to config/repos/ directory")

    # registry sync
    sync = registry_sub.add_parser("sync", help="Sync registry settings to repo configs")
    sync.add_argument("--configs-dir", help="Path to config/repos/ directory")
    sync.add_argument("--dry-run", action="store_true", help="Show what would change without modifying files")
    sync.add_argument("--yes", action="store_true", help="Apply changes without confirmation")

    # registry add <repo>
    add_cmd = registry_sub.add_parser("add", help="Add a new repo to the registry")
    add_cmd.add_argument("repo", help="Repository name")
    add_cmd.add_argument("--tier", default="standard", help="Initial tier (default: standard)")
    add_cmd.add_argument("--description", help="Repository description")

    # Support `cihub registry <subcommand> --json` (not only `cihub registry --json <subcommand>`).
    # This keeps JSON invocation consistent for TypeScript wrapper callers that append --json.
    for subparser in registry_sub.choices.values():
        add_json_flag(subparser)
