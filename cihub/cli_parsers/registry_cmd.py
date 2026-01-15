"""Parser setup for registry commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
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
        epilog=see_also_epilog("registry"),
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
    diff.add_argument(
        "--configs-dir",
        help="Path to config/repos/ (or <hub>/config or any path within a hub root)",
    )
    diff.add_argument(
        "--repos-root",
        help="Root directory containing cloned repos (detects .ci-hub.yml overrides)",
    )

    # registry sync
    sync = registry_sub.add_parser("sync", help="Sync registry settings to repo configs")
    sync.add_argument(
        "--configs-dir",
        help="Path to config/repos/ (or <hub>/config or any path within a hub root)",
    )
    sync.add_argument("--dry-run", action="store_true", help="Show what would change without modifying files")
    sync.add_argument("--yes", action="store_true", help="Apply changes without confirmation")

    # registry add <repo>
    add_cmd = registry_sub.add_parser("add", help="Add a new repo to the registry")
    add_cmd.add_argument("repo", nargs="?", help="Repository name")
    add_cmd.add_argument("--wizard", action="store_true", help="Interactive mode")
    add_cmd.add_argument("--tier", default="standard", help="Initial tier (default: standard)")
    add_cmd.add_argument("--description", help="Repository description")
    add_cmd.add_argument("--owner", help="Repository owner (GitHub org/user)")
    add_cmd.add_argument("--name", help="Repository name (defaults to repo argument; requires --owner)")
    add_cmd.add_argument(
        "--language",
        choices=["java", "python"],
        help="Repository language (enables sync to create config files)",
    )

    # registry remove <repo>
    remove_cmd = registry_sub.add_parser("remove", help="Remove a repo from the registry")
    remove_cmd.add_argument("repo", help="Repository name to remove")
    remove_cmd.add_argument(
        "--delete-config",
        action="store_true",
        help="Also delete the config/repos/<repo>.yaml file",
    )
    remove_cmd.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # registry bootstrap - import config/repos into registry
    bootstrap = registry_sub.add_parser(
        "bootstrap",
        help="Import existing config/repos/*.yaml into registry",
    )
    bootstrap.add_argument(
        "--configs-dir",
        help="Path to config/repos/ directory to import from",
    )
    bootstrap.add_argument(
        "--tier",
        default="standard",
        help="Default tier for imported repos (default: standard)",
    )
    bootstrap.add_argument(
        "--strategy",
        choices=["merge", "replace", "prefer-registry", "prefer-config"],
        default="merge",
        help="Conflict strategy when repo already in registry (default: merge)",
    )
    bootstrap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying registry",
    )
    bootstrap.add_argument(
        "--include-thresholds",
        action="store_true",
        help="Import threshold values from config files as overrides",
    )

    # registry export - export registry to a JSON file
    export_cmd = registry_sub.add_parser(
        "export",
        help="Export registry to a JSON file for backup",
    )
    export_cmd.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output file path (e.g., backup.json)",
    )
    export_cmd.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation",
    )

    # registry import - import registry from a JSON file
    import_cmd = registry_sub.add_parser(
        "import",
        help="Import registry from a JSON backup file",
    )
    import_cmd.add_argument(
        "--file",
        "-f",
        required=True,
        help="Input file path (e.g., backup.json)",
    )
    import_cmd.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing registry (add new repos, update existing)",
    )
    import_cmd.add_argument(
        "--replace",
        action="store_true",
        help="Replace entire registry with imported data",
    )
    import_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying registry",
    )

    # Support `cihub registry <subcommand> --json` (not only `cihub registry --json <subcommand>`).
    # This keeps JSON invocation consistent for TypeScript wrapper callers that append --json.
    for subparser in registry_sub.choices.values():
        add_json_flag(subparser)
