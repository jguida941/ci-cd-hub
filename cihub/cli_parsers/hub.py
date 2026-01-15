"""Parser setup for hub operational commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.common import see_also_epilog
from cihub.cli_parsers.types import CommandHandlers


def add_hub_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    """Add hub operational settings commands.

    Commands:
        hub config show   - Display current hub settings
        hub config set    - Update a hub setting
        hub config load   - Load settings and output for GitHub Actions
    """
    hub = subparsers.add_parser(
        "hub",
        help="Manage hub operational settings (config/hub-settings.yaml)",
        epilog=see_also_epilog("hub"),
    )
    hub_sub = hub.add_subparsers(dest="hub_subcommand")
    hub.set_defaults(func=handlers.cmd_hub)

    # hub config subcommand group
    hub_config = hub_sub.add_parser(
        "config",
        help="Manage hub operational settings",
    )
    hub_config_sub = hub_config.add_subparsers(dest="config_subcommand")
    hub_config.set_defaults(func=handlers.cmd_hub)

    # hub config show
    hub_config_show = hub_config_sub.add_parser(
        "show",
        help="Display current hub settings",
    )
    add_json_flag(hub_config_show)
    hub_config_show.set_defaults(func=handlers.cmd_hub)

    # hub config set
    hub_config_set = hub_config_sub.add_parser(
        "set",
        help="Update a hub setting (e.g., execution.skip_mutation true)",
    )
    add_json_flag(hub_config_set)
    hub_config_set.add_argument(
        "path",
        help="Dot path to setting (e.g., execution.skip_mutation, debug.enabled)",
    )
    hub_config_set.add_argument(
        "value",
        help="Value to set (true, false, audit, block, disabled)",
    )
    hub_config_set.set_defaults(func=handlers.cmd_hub)

    # hub config load
    hub_config_load = hub_config_sub.add_parser(
        "load",
        help="Load settings and output for GitHub Actions workflows",
    )
    add_json_flag(hub_config_load)
    hub_config_load.add_argument(
        "--github-output",
        action="store_true",
        help="Write settings to GITHUB_OUTPUT for workflow use",
    )
    # Override arguments - allow workflow inputs to override config file values
    # Empty strings are ignored (only non-empty values override)
    hub_config_load.add_argument(
        "--override-skip-mutation",
        dest="override_skip_mutation",
        default="",
        help="Override execution.skip_mutation (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-write-summary",
        dest="override_write_summary",
        default="",
        help="Override execution.write_github_summary (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-include-details",
        dest="override_include_details",
        default="",
        help="Override execution.include_details (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-debug",
        dest="override_debug",
        default="",
        help="Override debug.enabled (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-verbose",
        dest="override_verbose",
        default="",
        help="Override debug.verbose (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-debug-context",
        dest="override_debug_context",
        default="",
        help="Override debug.debug_context (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-emit-triage",
        dest="override_emit_triage",
        default="",
        help="Override debug.emit_triage (empty=use config)",
    )
    hub_config_load.add_argument(
        "--override-harden-runner-policy",
        dest="override_harden_runner_policy",
        default="",
        help="Override security.harden_runner.policy (empty=use config)",
    )
    hub_config_load.set_defaults(func=handlers.cmd_hub)
