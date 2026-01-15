"""CLI parser for repo management commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_repo_commands(
    subparsers: argparse._SubParsersAction,  # noqa: SLF001
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    """Add repo management commands to the CLI."""
    repo = subparsers.add_parser(
        "repo",
        help="Manage repositories in the registry",
        epilog=see_also_epilog("repo"),
    )
    add_json_flag(repo)
    repo.set_defaults(func=handlers.cmd_repo)

    repo_sub = repo.add_subparsers(dest="subcommand", required=True)

    # repo list [--language] [--tier] [--format]
    list_parser = repo_sub.add_parser(
        "list",
        help="List repositories in the registry",
    )
    add_json_flag(list_parser)
    list_parser.add_argument(
        "--language",
        choices=["python", "java"],
        help="Filter by language",
    )
    list_parser.add_argument(
        "--tier",
        metavar="NAME",
        help="Filter by tier",
    )
    list_parser.add_argument(
        "--with-overrides",
        action="store_true",
        help="Only show repos with threshold overrides",
    )

    # repo show <name>
    show_parser = repo_sub.add_parser(
        "show",
        help="Show detailed repository information",
    )
    add_json_flag(show_parser)
    show_parser.add_argument(
        "name",
        help="Repository name",
    )
    show_parser.add_argument(
        "--effective",
        action="store_true",
        help="Show effective configuration (with tier/profile inheritance)",
    )

    # repo update <name> [--owner] [--default-branch] [--language] [--tier] [--dispatch-enabled]
    update_parser = repo_sub.add_parser(
        "update",
        help="Update repository metadata",
    )
    add_json_flag(update_parser)
    update_parser.add_argument(
        "name",
        nargs="?",
        help="Repository name",
    )
    update_parser.add_argument(
        "--wizard",
        action="store_true",
        help="Interactive mode - select repo and fields to update",
    )
    update_parser.add_argument(
        "--owner",
        metavar="ORG",
        help="Set repository owner (GitHub org/user)",
    )
    update_parser.add_argument(
        "--repo-name",
        metavar="NAME",
        help="Set repository name (if different from config key)",
    )
    update_parser.add_argument(
        "--default-branch",
        "--branch",  # backward-compatible alias
        metavar="BRANCH",
        dest="default_branch",
        help="Set default branch",
    )
    update_parser.add_argument(
        "--language",
        choices=["python", "java"],
        help="Set repository language",
    )
    update_parser.add_argument(
        "--tier",
        metavar="NAME",
        help="Set repository tier",
    )
    update_parser.add_argument(
        "--dispatch-enabled",
        choices=["true", "false"],
        help="Enable/disable dispatch for this repo",
    )
    update_parser.add_argument(
        "--description",
        metavar="TEXT",
        help="Set repository description",
    )

    # repo migrate <from> <to> [--delete-source]
    migrate_parser = repo_sub.add_parser(
        "migrate",
        help="Migrate/rename a repository entry",
    )
    add_json_flag(migrate_parser)
    migrate_parser.add_argument(
        "source",
        help="Source repository name",
    )
    migrate_parser.add_argument(
        "dest",
        help="Destination repository name",
    )
    migrate_parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete source after migration (rename)",
    )
    migrate_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination if it exists",
    )

    # repo clone <source> <dest>
    clone_parser = repo_sub.add_parser(
        "clone",
        help="Clone a repository configuration",
    )
    add_json_flag(clone_parser)
    clone_parser.add_argument(
        "source",
        help="Source repository name",
    )
    clone_parser.add_argument(
        "dest",
        help="Destination repository name",
    )
    clone_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination if it exists",
    )

    # repo verify-connectivity <name>
    verify_parser = repo_sub.add_parser(
        "verify-connectivity",
        help="Verify GitHub connectivity for a repository",
    )
    add_json_flag(verify_parser)
    verify_parser.add_argument(
        "name",
        help="Repository name",
    )
    verify_parser.add_argument(
        "--check-workflows",
        action="store_true",
        help="Also verify workflow file existence",
    )
