"""Shared types for CLI parser builders."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable

from cihub.types import CommandResult

CommandHandler = Callable[[argparse.Namespace], int | CommandResult]


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandHandlers:
    cmd_detect: CommandHandler
    cmd_preflight: CommandHandler
    cmd_scaffold: CommandHandler
    cmd_smoke: CommandHandler
    cmd_smoke_validate: CommandHandler
    cmd_check: CommandHandler
    cmd_verify: CommandHandler
    cmd_ci: CommandHandler
    cmd_ai_loop: CommandHandler
    cmd_run: CommandHandler
    cmd_report: CommandHandler
    cmd_triage: CommandHandler
    cmd_commands: CommandHandler
    cmd_docs: CommandHandler
    cmd_docs_links: CommandHandler
    cmd_docs_stale: CommandHandler
    cmd_docs_audit: CommandHandler
    cmd_adr: CommandHandler
    cmd_config_outputs: CommandHandler
    cmd_discover: CommandHandler
    cmd_dispatch: CommandHandler
    cmd_hub_ci: CommandHandler
    cmd_new: CommandHandler
    cmd_init: CommandHandler
    cmd_update: CommandHandler
    cmd_validate: CommandHandler
    cmd_setup_secrets: CommandHandler
    cmd_setup_nvd: CommandHandler
    cmd_fix_pom: CommandHandler
    cmd_fix_deps: CommandHandler
    cmd_fix_gradle: CommandHandler
    cmd_sync_templates: CommandHandler
    cmd_config: CommandHandler
    cmd_fix: CommandHandler
    cmd_registry: CommandHandler
    cmd_profile: CommandHandler
    cmd_tool: CommandHandler
    cmd_threshold: CommandHandler
    cmd_repo: CommandHandler
    cmd_hub: CommandHandler
    cmd_setup: CommandHandler
