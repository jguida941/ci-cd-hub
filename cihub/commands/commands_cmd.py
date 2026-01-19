"""Command registry command handlers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Iterable

from cihub import __version__
from cihub.cli_parsers.builder import build_parser
from cihub.exit_codes import EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult
from cihub.utils.paths import hub_root
from cihub.wizard import HAS_WIZARD

SCHEMA_SOURCE = "schema/ci-hub-config.schema.json"


@dataclass(frozen=True, slots=True)
class CommandOption:
    flags: list[str]
    help: str
    dest: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "flags": self.flags,
            "help": self.help,
            "dest": self.dest,
        }


@dataclass(frozen=True, slots=True)
class CommandEntry:
    path: list[str]
    command: str
    help: str
    options: list[CommandOption]
    supports_json: bool
    supports_json_runtime: bool
    supports_wizard: bool
    supports_interactive: bool
    is_group: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "command": self.command,
            "help": self.help,
            "options": [option.to_payload() for option in self.options],
            "supports_json": self.supports_json,
            "supports_json_runtime": self.supports_json_runtime,
            "supports_wizard": self.supports_wizard,
            "supports_interactive": self.supports_interactive,
            "is_group": self.is_group,
        }


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action.choices
    return {}


def _subparser_help(parser: argparse.ArgumentParser) -> dict[str, str]:
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return {sub.dest: sub.help or "" for sub in action._get_subactions()}  # noqa: SLF001
    return {}


def _option_entries(parser: argparse.ArgumentParser) -> list[CommandOption]:
    options: list[CommandOption] = []
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            continue
        if not action.option_strings:
            continue
        if "--help" in action.option_strings:
            continue
        flags = list(action.option_strings)
        help_text = action.help or ""
        dest = getattr(action, "dest", "")
        options.append(CommandOption(flags=flags, help=help_text, dest=dest))
    return options


def _supports_flag(parser: argparse.ArgumentParser, flag: str) -> bool:
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if flag in getattr(action, "option_strings", []):
            return True
    return False


def _command_key(path: list[str]) -> str:
    return " ".join(path)


def _is_interactive_command(path: list[str]) -> bool:
    return _command_key(path) in {"setup", "config edit"}


def _json_runtime_supported(path: list[str], supports_json: bool) -> bool:
    if not supports_json:
        return False
    return _command_key(path) not in {"setup"}


def _collect_commands(
    parser: argparse.ArgumentParser,
    prefix: list[str] | None = None,
) -> Iterable[CommandEntry]:
    prefix = prefix or []
    subparsers = _subparsers(parser)
    if not subparsers:
        return []

    help_map = _subparser_help(parser)
    entries: list[CommandEntry] = []

    for name, child in subparsers.items():
        path = [*prefix, name]
        child_help = help_map.get(name) or (child.description or "")
        options = _option_entries(child)
        supports_json = _supports_flag(child, "--json")
        supports_wizard = _supports_flag(child, "--wizard")
        supports_interactive_flag = _supports_flag(child, "--interactive")
        is_group = bool(_subparsers(child))
        supports_interactive = supports_wizard or supports_interactive_flag or _is_interactive_command(path)
        supports_json_runtime = _json_runtime_supported(path, supports_json)

        entries.append(
            CommandEntry(
                path=path,
                command=" ".join(path),
                help=child_help,
                options=options,
                supports_json=supports_json,
                supports_json_runtime=supports_json_runtime,
                supports_wizard=supports_wizard,
                supports_interactive=supports_interactive,
                is_group=is_group,
            )
        )

        if is_group:
            entries.extend(_collect_commands(child, path))

    return entries


def _schema_metadata() -> dict[str, str]:
    schema_path = hub_root() / SCHEMA_SOURCE
    schema_id = ""
    if schema_path.exists():
        try:
            import json

            schema_id = json.loads(schema_path.read_text(encoding="utf-8")).get("$id", "")
        except Exception:
            schema_id = ""
    return {
        "id": schema_id,
        "path": str(schema_path),
    }


def cmd_commands_list(_: argparse.Namespace) -> CommandResult:
    parser = build_parser()
    entries = list(_collect_commands(parser))
    leaf_entries = [entry for entry in entries if not entry.is_group]
    raw_output = "\n".join(entry.command for entry in leaf_entries)

    data = {
        "commands": [entry.to_payload() for entry in entries],
        "command_count": len(entries),
        "leaf_command_count": len(leaf_entries),
        "schema": _schema_metadata(),
        "wizard": {"available": HAS_WIZARD},
        "cli_version": __version__,
        "raw_output": raw_output,
    }
    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="Command registry generated",
        data=data,
    )


def cmd_commands(args: argparse.Namespace) -> CommandResult:
    if args.subcommand == "list":
        return cmd_commands_list(args)

    return CommandResult(exit_code=EXIT_USAGE, summary=f"Unknown subcommand: {args.subcommand}")
