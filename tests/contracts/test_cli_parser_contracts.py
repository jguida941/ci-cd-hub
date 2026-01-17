"""Contract tests for CLI parser wiring."""

# TEST-METRICS:

from __future__ import annotations

import argparse

from cihub.cli import build_parser

DELEGATED_SUBCOMMAND_ROOTS = {"dispatch", "hub", "hub-ci", "profile", "registry", "repo", "threshold", "tool"}
EXPECTED_JSON_PATHS = {
    "ai-loop",
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
    "dispatch watch",
    "docs audit",
    "docs check",
    "docs generate",
    "docs links",
    "docs stale",
    "doctor",
    "fix",
    "fix-deps",
    "fix-gradle",
    "fix-pom",
    "hub config load",
    "hub config set",
    "hub config show",
    "hub-ci",
    "hub-ci actionlint",
    "hub-ci actionlint-install",
    "hub-ci badges",
    "hub-ci badges-commit",
    "hub-ci bandit",
    "hub-ci black",
    "hub-ci codeql-build",
    "hub-ci coverage-verify",
    "hub-ci docker-compose-check",
    "hub-ci enforce",
    "hub-ci enforce-command-result",
    "hub-ci gitleaks-summary",
    "hub-ci kyverno-install",
    "hub-ci kyverno-test",
    "hub-ci kyverno-validate",
    "hub-ci license-check",
    "hub-ci mutmut",
    "hub-ci mypy",
    "hub-ci outputs",
    "hub-ci pip-audit",
    "hub-ci pytest-summary",
    "hub-ci quarantine-check",
    "hub-ci release-parse-tag",
    "hub-ci release-update-tag",
    "hub-ci repo-check",
    "hub-ci ruff",
    "hub-ci ruff-format",
    "hub-ci security-bandit",
    "hub-ci security-owasp",
    "hub-ci security-pip-audit",
    "hub-ci security-ruff",
    "hub-ci smoke-java-build",
    "hub-ci smoke-java-checkstyle",
    "hub-ci smoke-java-coverage",
    "hub-ci smoke-java-spotbugs",
    "hub-ci smoke-java-tests",
    "hub-ci smoke-python-black",
    "hub-ci smoke-python-install",
    "hub-ci smoke-python-ruff",
    "hub-ci smoke-python-tests",
    "hub-ci source-check",
    "hub-ci summary",
    "hub-ci syntax-check",
    "hub-ci test-metrics",
    "hub-ci thresholds",
    "hub-ci trivy-install",
    "hub-ci trivy-summary",
    "hub-ci validate-configs",
    "hub-ci validate-profiles",
    "hub-ci validate-triage",
    "hub-ci verify-matrix-keys",
    "hub-ci yamllint",
    "hub-ci zizmor-check",
    "hub-ci zizmor-run",
    "init",
    "new",
    "preflight",
    "profile",
    "profile create",
    "profile delete",
    "profile edit",
    "profile export",
    "profile import",
    "profile list",
    "profile show",
    "profile validate",
    "registry",
    "registry add",
    "registry bootstrap",
    "registry diff",
    "registry export",
    "registry import",
    "registry list",
    "registry remove",
    "registry set",
    "registry show",
    "registry sync",
    "repo",
    "repo clone",
    "repo list",
    "repo migrate",
    "repo show",
    "repo update",
    "repo verify-connectivity",
    "report",
    "report aggregate",
    "report build",
    "report dashboard",
    "report outputs",
    "report summary",
    "report validate",
    "run",
    "scaffold",
    "setup",
    "setup-nvd",
    "setup-secrets",
    "smoke",
    "smoke-validate",
    "sync-templates",
    "threshold",
    "threshold compare",
    "threshold get",
    "threshold list",
    "threshold reset",
    "threshold set",
    "tool",
    "tool configure",
    "tool disable",
    "tool enable",
    "tool info",
    "tool list",
    "tool status",
    "tool validate",
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
