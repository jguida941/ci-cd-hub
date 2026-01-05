"""Contract tests for CLI parser wiring."""

from __future__ import annotations

import argparse

from cihub.cli import build_parser

DELEGATED_SUBCOMMAND_ROOTS = {"dispatch", "hub-ci"}
EXPECTED_JSON_PATHS = {
    "adr check",
    "adr list",
    "adr new",
    "check",
    "ci",
    "config",
    "config apply-profile",
    "config disable",
    "config edit",
    "config enable",
    "config set",
    "config show",
    "config-outputs",
    "detect",
    "discover",
    "dispatch metadata",
    "dispatch trigger",
    "docs check",
    "docs generate",
    "docs links",
    "doctor",
    "fix-deps",
    "fix-pom",
    "init",
    "hub-ci",
    "new",
    "preflight",
    "report",
    "report aggregate",
    "report build",
    "report dashboard",
    "report outputs",
    "report summary",
    "report validate",
    "run",
    "scaffold",
    "setup-nvd",
    "setup-secrets",
    "smoke",
    "smoke-validate",
    "sync-templates",
    "triage",
    "update",
    "validate",
    "verify",
}


def _collect_parsers(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                path = prefix + (name,)
                yield path, subparser
                yield from _collect_parsers(subparser, path)


def _has_flag(parser: argparse.ArgumentParser, flag: str) -> bool:
    for action in parser._actions:
        if getattr(action, "option_strings", None) and flag in action.option_strings:
            return True
    return False


def test_top_level_commands_have_handlers() -> None:
    parser = build_parser()
    for path, subparser in _collect_parsers(parser):
        if len(path) == 1:
            assert subparser.get_default("func") is not None, f"Missing handler for {' '.join(path)}"


def test_subcommands_have_handlers_unless_delegated() -> None:
    parser = build_parser()
    for path, subparser in _collect_parsers(parser):
        if len(path) < 2:
            continue
        if path[0] in DELEGATED_SUBCOMMAND_ROOTS:
            continue
        assert subparser.get_default("func") is not None, f"Missing handler for {' '.join(path)}"


def test_json_flag_paths_unchanged() -> None:
    parser = build_parser()
    actual = set()
    for path, subparser in _collect_parsers(parser):
        if _has_flag(subparser, "--json"):
            actual.add(" ".join(path))
    assert actual == EXPECTED_JSON_PATHS
