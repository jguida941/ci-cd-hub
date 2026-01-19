"""Registry for CLI parser groups."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.adr import add_adr_commands
from cihub.cli_parsers.commands_cmd import add_commands_commands
from cihub.cli_parsers.config import add_config_commands, add_config_outputs_command
from cihub.cli_parsers.core import add_core_commands
from cihub.cli_parsers.discover import add_discover_command
from cihub.cli_parsers.dispatch import add_dispatch_commands
from cihub.cli_parsers.docs import add_docs_commands
from cihub.cli_parsers.fix import add_fix_commands
from cihub.cli_parsers.gradle import add_gradle_commands
from cihub.cli_parsers.hub import add_hub_commands
from cihub.cli_parsers.hub_ci import add_hub_ci_commands
from cihub.cli_parsers.pom import add_pom_commands
from cihub.cli_parsers.profile_cmd import add_profile_commands
from cihub.cli_parsers.registry_cmd import add_registry_commands
from cihub.cli_parsers.repo_cmd import add_repo_commands
from cihub.cli_parsers.repo_setup import add_repo_setup_commands
from cihub.cli_parsers.report import add_report_commands
from cihub.cli_parsers.secrets import add_secrets_commands
from cihub.cli_parsers.templates import add_templates_commands
from cihub.cli_parsers.threshold_cmd import add_threshold_commands
from cihub.cli_parsers.tool_cmd import add_tool_commands
from cihub.cli_parsers.triage import add_triage_command
from cihub.cli_parsers.types import CommandHandlers

ParserGroup = Callable[  # noqa: SLF001
    [argparse._SubParsersAction, Callable[[argparse.ArgumentParser], None], CommandHandlers],
    None,
]

PARSER_GROUPS: list[ParserGroup] = [
    add_core_commands,
    add_commands_commands,
    add_report_commands,
    add_triage_command,
    add_fix_commands,
    add_docs_commands,
    add_adr_commands,
    add_config_outputs_command,
    add_discover_command,
    add_dispatch_commands,
    add_hub_commands,
    add_hub_ci_commands,
    add_repo_setup_commands,
    add_secrets_commands,
    add_pom_commands,
    add_gradle_commands,
    add_templates_commands,
    add_config_commands,
    add_registry_commands,
    add_profile_commands,
    add_tool_commands,
    add_threshold_commands,
    add_repo_commands,
]


def register_parser_groups(
    subparsers: argparse._SubParsersAction,  # noqa: SLF001
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    for group in PARSER_GROUPS:
        group(subparsers, add_json_flag, handlers)
