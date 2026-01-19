"""Parser setup for hub-ci validation subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import (
    add_output_args,
    add_path_args,
    add_summary_args,
)


def add_validation_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add validation-related subcommand parsers.

    Subcommands: syntax-check, yamllint, repo-check, source-check,
    docker-compose-check, validate-configs, validate-profiles, validate-triage,
    verify-matrix-keys, quarantine-check, enforce-command-result
    """
    hub_ci_syntax = hub_ci_sub.add_parser(
        "syntax-check",
        help="Compile Python files to catch syntax errors",
    )
    hub_ci_syntax.add_argument("--root", default=".", help="Root directory")
    hub_ci_syntax.add_argument(
        "--paths",
        nargs="+",
        default=["scripts", "cihub"],
        help="Paths to check (files or directories)",
    )
    add_json_flag(hub_ci_syntax)

    hub_ci_yamllint = hub_ci_sub.add_parser(
        "yamllint",
        help="Lint YAML files (hub defaults, repo configs, profiles)",
    )
    hub_ci_yamllint.add_argument(
        "--config",
        help='yamllint config string (passed to -d). Default: "{extends: relaxed, rules: {line-length: disable}}"',
    )
    hub_ci_yamllint.add_argument(
        "paths",
        nargs="*",
        default=["config/defaults.yaml", "config/repos/", "templates/profiles/"],
        help="Paths to lint",
    )
    add_output_args(hub_ci_yamllint)
    add_json_flag(hub_ci_yamllint)

    hub_ci_repo_check = hub_ci_sub.add_parser(
        "repo-check",
        help="Check if a repo checkout is present",
    )
    add_path_args(hub_ci_repo_check)
    hub_ci_repo_check.add_argument("--owner", help="Repo owner (for warnings)")
    hub_ci_repo_check.add_argument("--name", help="Repo name (for warnings)")
    add_output_args(hub_ci_repo_check)
    add_json_flag(hub_ci_repo_check)

    hub_ci_source_check = hub_ci_sub.add_parser(
        "source-check",
        help="Detect source files for a repo",
    )
    add_path_args(hub_ci_source_check)
    hub_ci_source_check.add_argument("--language", required=True, help="Repo language")
    add_output_args(hub_ci_source_check)
    add_json_flag(hub_ci_source_check)

    hub_ci_docker_check = hub_ci_sub.add_parser(
        "docker-compose-check",
        help="Check for docker-compose files in a repo",
    )
    add_path_args(hub_ci_docker_check)
    add_output_args(hub_ci_docker_check)
    add_json_flag(hub_ci_docker_check)

    hub_ci_validate_configs = hub_ci_sub.add_parser(
        "validate-configs",
        help="Validate hub repo config files",
    )
    hub_ci_validate_configs.add_argument("--configs-dir", help="Directory containing config repos")
    hub_ci_validate_configs.add_argument(
        "--repo",
        help="Validate a single repo config by name (e.g., fixtures-python-passing)",
    )
    add_json_flag(hub_ci_validate_configs)

    hub_ci_validate_profiles = hub_ci_sub.add_parser(
        "validate-profiles",
        help="Validate profile YAML files",
    )
    hub_ci_validate_profiles.add_argument("--profiles-dir", help="Directory containing profiles")
    add_json_flag(hub_ci_validate_profiles)

    hub_ci_validate_triage = hub_ci_sub.add_parser(
        "validate-triage",
        help="Validate triage.json against the triage schema",
    )
    hub_ci_validate_triage.add_argument(
        "--triage-file",
        default=".cihub/triage.json",
        help="Path to triage.json file (default: .cihub/triage.json)",
    )
    add_json_flag(hub_ci_validate_triage)

    _hub_ci_verify_matrix = hub_ci_sub.add_parser(  # noqa: F841
        "verify-matrix-keys",
        help="Verify hub-run-all.yml matrix keys match discover.py output",
    )
    add_json_flag(_hub_ci_verify_matrix)

    hub_ci_quarantine = hub_ci_sub.add_parser(
        "quarantine-check",
        help="Fail if any file imports from _quarantine",
    )
    hub_ci_quarantine.add_argument(
        "--path",
        help="Root directory to scan (default: hub root)",
    )
    add_json_flag(hub_ci_quarantine)

    hub_ci_enforce_cmd_result = hub_ci_sub.add_parser(
        "enforce-command-result",
        help="Enforce CommandResult pattern - fail if too many print() calls in commands/ (ADR-0042)",
    )
    hub_ci_enforce_cmd_result.add_argument(
        "--path",
        help="Root directory to scan (default: hub root)",
    )
    hub_ci_enforce_cmd_result.add_argument(
        "--max-allowed",
        type=int,
        default=0,
        help="Maximum allowed print() calls in cihub/commands/ (default: 0)",
    )
    add_summary_args(hub_ci_enforce_cmd_result)
    hub_ci_enforce_cmd_result.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_enforce_cmd_result)
