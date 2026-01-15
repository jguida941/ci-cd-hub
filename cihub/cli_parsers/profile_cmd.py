"""Parser setup for profile management commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_profile_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    """Add profile command and subcommands.

    Profile commands manage CI profiles (tool enablement presets).
    Profiles are stored in templates/profiles/<name>.yaml.
    """
    profile = subparsers.add_parser(
        "profile",
        help="Manage CI profiles (tool enablement presets)",
        epilog=see_also_epilog("profile"),
    )
    add_json_flag(profile)
    profile.set_defaults(func=handlers.cmd_profile)
    profile_sub = profile.add_subparsers(dest="subcommand", required=True)

    # profile list
    list_cmd = profile_sub.add_parser("list", help="List available profiles")
    list_cmd.add_argument(
        "--language",
        choices=["python", "java"],
        help="Filter by language (python or java)",
    )
    list_cmd.add_argument(
        "--type",
        choices=["language", "tier"],
        help="Filter by profile type (language or tier)",
    )

    # profile show <name>
    show = profile_sub.add_parser("show", help="Show profile details")
    show.add_argument("name", help="Profile name (e.g., python-fast, tier-strict)")
    show.add_argument(
        "--effective",
        action="store_true",
        help="Show effective config after merging with defaults",
    )

    # profile create <name>
    create = profile_sub.add_parser("create", help="Create a new profile")
    create.add_argument("name", help="Profile name (e.g., my-team-python)")
    create.add_argument(
        "--language",
        choices=["python", "java"],
        help="Target language for the profile",
    )
    create.add_argument(
        "--from-profile",
        metavar="PROFILE",
        help="Base profile to copy from",
    )
    create.add_argument(
        "--from-repo",
        metavar="REPO",
        help="Extract profile from existing repo config",
    )
    create.add_argument(
        "--description",
        help="Profile description",
    )
    create.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing profile",
    )

    # profile edit <name>
    edit = profile_sub.add_parser("edit", help="Edit an existing profile")
    edit.add_argument("name", help="Profile name to edit")
    edit.add_argument(
        "--wizard",
        action="store_true",
        help="Use interactive wizard for editing",
    )
    edit.add_argument(
        "--enable",
        nargs="+",
        metavar="TOOL",
        help="Enable tools (e.g., --enable mypy mutmut)",
    )
    edit.add_argument(
        "--disable",
        nargs="+",
        metavar="TOOL",
        help="Disable tools (e.g., --disable trivy codeql)",
    )
    edit.add_argument(
        "--set",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        dest="settings",
        help="Set tool setting (e.g., --set pytest.min_coverage 80)",
    )

    # profile delete <name>
    delete = profile_sub.add_parser("delete", help="Delete a profile")
    delete.add_argument("name", help="Profile name to delete")
    delete.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # profile export <name>
    export_cmd = profile_sub.add_parser("export", help="Export profile to a file")
    export_cmd.add_argument("name", help="Profile name to export")
    export_cmd.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output file path (e.g., my-profile.yaml)",
    )

    # profile import
    import_cmd = profile_sub.add_parser("import", help="Import profile from a file")
    import_cmd.add_argument(
        "--file",
        "-f",
        required=True,
        help="Input file path (e.g., my-profile.yaml)",
    )
    import_cmd.add_argument(
        "--name",
        help="Name for the imported profile (defaults to filename)",
    )
    import_cmd.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing profile with same name",
    )

    # profile validate <name>
    validate = profile_sub.add_parser("validate", help="Validate a profile")
    validate.add_argument("name", help="Profile name to validate")
    validate.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (unknown tools, deprecated settings)",
    )

    # Support `cihub profile <subcommand> --json` (not only `cihub profile --json <subcommand>`).
    # This keeps JSON invocation consistent for TypeScript wrapper callers that append --json.
    for subparser in profile_sub.choices.values():
        add_json_flag(subparser)
