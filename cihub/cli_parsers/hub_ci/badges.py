"""Parser setup for hub-ci badge subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import add_output_args


def add_badges_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add badge-related subcommand parsers.

    Subcommands: badges, badges-commit, outputs
    """
    hub_ci_badges = hub_ci_sub.add_parser("badges", help="Generate or validate CI badges")
    hub_ci_badges.add_argument(
        "--check",
        action="store_true",
        help="Validate badges match current metrics",
    )
    hub_ci_badges.add_argument(
        "--config",
        help="Config file to read reports.badges.enabled from (defaults to config/defaults.yaml)",
    )
    hub_ci_badges.add_argument("--output-dir", help="Output directory for badges")
    hub_ci_badges.add_argument(
        "--artifacts-dir",
        help="Directory containing bandit/pip-audit/zizmor artifacts",
    )
    hub_ci_badges.add_argument("--ruff-issues", type=int, help="Ruff issue count")
    hub_ci_badges.add_argument("--mutation-score", type=float, help="Mutation score")
    hub_ci_badges.add_argument("--mypy-errors", type=int, help="Mypy error count")
    hub_ci_badges.add_argument("--black-issues", type=int, help="Black issue count")
    hub_ci_badges.add_argument(
        "--black-status",
        choices=["clean", "failed", "n/a"],
        help="Black formatter status",
    )
    hub_ci_badges.add_argument("--zizmor-sarif", help="Path to zizmor SARIF file")
    add_json_flag(hub_ci_badges)

    hub_ci_badges_commit = hub_ci_sub.add_parser(
        "badges-commit",
        help="Commit and push badge updates",
    )
    add_json_flag(hub_ci_badges_commit)

    hub_ci_outputs = hub_ci_sub.add_parser("outputs", help="Emit hub CI toggle outputs")
    hub_ci_outputs.add_argument(
        "--repo",
        help="Repository name for config lookup (default: $CIHUB_REPO or $GITHUB_REPOSITORY name)",
    )
    hub_ci_outputs.add_argument(
        "--config",
        help="Override: direct path to config file (bypasses repo config merge)",
    )
    add_output_args(hub_ci_outputs)
    add_json_flag(hub_ci_outputs)
