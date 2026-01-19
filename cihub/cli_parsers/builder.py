"""CLI parser construction helpers."""

from __future__ import annotations

import argparse
import inspect
from typing import Any

from cihub import __version__
from cihub.cli_parsers.registry import register_parser_groups
from cihub.cli_parsers.types import CommandHandlers


def _noop_handler(_: argparse.Namespace) -> int:
    return 0


def _default_handlers() -> CommandHandlers:
    return CommandHandlers(
        cmd_detect=_noop_handler,
        cmd_preflight=_noop_handler,
        cmd_scaffold=_noop_handler,
        cmd_smoke=_noop_handler,
        cmd_smoke_validate=_noop_handler,
        cmd_check=_noop_handler,
        cmd_verify=_noop_handler,
        cmd_ci=_noop_handler,
        cmd_ai_loop=_noop_handler,
        cmd_run=_noop_handler,
        cmd_report=_noop_handler,
        cmd_triage=_noop_handler,
        cmd_commands=_noop_handler,
        cmd_docs=_noop_handler,
        cmd_docs_links=_noop_handler,
        cmd_docs_stale=_noop_handler,
        cmd_docs_audit=_noop_handler,
        cmd_adr=_noop_handler,
        cmd_config_outputs=_noop_handler,
        cmd_discover=_noop_handler,
        cmd_dispatch=_noop_handler,
        cmd_hub_ci=_noop_handler,
        cmd_new=_noop_handler,
        cmd_init=_noop_handler,
        cmd_update=_noop_handler,
        cmd_validate=_noop_handler,
        cmd_setup_secrets=_noop_handler,
        cmd_setup_nvd=_noop_handler,
        cmd_fix_pom=_noop_handler,
        cmd_fix_deps=_noop_handler,
        cmd_fix_gradle=_noop_handler,
        cmd_sync_templates=_noop_handler,
        cmd_config=_noop_handler,
        cmd_fix=_noop_handler,
        cmd_registry=_noop_handler,
        cmd_profile=_noop_handler,
        cmd_tool=_noop_handler,
        cmd_hub=_noop_handler,
        cmd_setup=_noop_handler,
        cmd_threshold=_noop_handler,
        cmd_repo=_noop_handler,
    )


def build_parser(handlers: CommandHandlers | None = None) -> argparse.ArgumentParser:
    parser_kwargs: dict[str, Any] = {"prog": "cihub", "description": "CI/CD Hub CLI"}
    if "color" in inspect.signature(argparse.ArgumentParser).parameters:
        parser_kwargs["color"] = False
    parser = argparse.ArgumentParser(**parser_kwargs)
    parser.add_argument("--version", action="version", version=f"cihub {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--json",
            action="store_true",
            help="Output machine-readable JSON",
        )

    register_parser_groups(subparsers, add_json_flag, handlers or _default_handlers())
    return parser
