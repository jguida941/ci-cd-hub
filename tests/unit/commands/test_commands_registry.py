"""Tests for the commands registry CLI."""

# TEST-METRICS:

from __future__ import annotations

import argparse

from cihub.commands.commands_cmd import cmd_commands


def test_commands_list_includes_core_commands() -> None:
    args = argparse.Namespace(subcommand="list")
    result = cmd_commands(args)

    assert result.exit_code == 0
    assert result.data is not None

    commands = result.data.get("commands", [])
    command_strings = {entry["command"] for entry in commands}

    assert "check" in command_strings
    assert "report summary" in command_strings
    assert "commands list" in command_strings


def test_commands_list_metadata_present() -> None:
    args = argparse.Namespace(subcommand="list")
    result = cmd_commands(args)

    assert result.exit_code == 0
    assert result.data is not None
    assert result.data.get("schema")
    assert "cli_version" in result.data
    assert "wizard" in result.data
    assert result.data.get("leaf_command_count", 0) > 0
