"""Parser setup for hub-ci commands.

This package organizes hub-ci subcommand parsers by family:
- validation: syntax-check, yamllint, repo-check, source-check, validate-*, etc.
- python_tools: ruff, black, mypy, mutmut, coverage-verify
- security: bandit, pip-audit, security-*
- java_tools: codeql-build, smoke-java-*
- smoke: smoke-python-*
- badges: badges, badges-commit, outputs
- release: actionlint, kyverno-*, trivy-*, zizmor-*, release-*, pytest-summary, etc.
- test_metrics: test-metrics wrapper

Each family module exports a single `add_*_parsers(hub_ci_sub, add_json_flag)` function.
"""

from __future__ import annotations

from cihub.cli_parsers.types import CommandHandlers

from .badges import add_badges_parsers
from .java_tools import add_java_tools_parsers
from .python_tools import add_python_tools_parsers
from .release import add_release_parsers
from .security import add_security_parsers
from .smoke import add_smoke_parsers
from .test_metrics import add_test_metrics_parsers
from .thresholds import add_thresholds_parsers
from .validation import add_validation_parsers


def add_hub_ci_commands(subparsers, add_json_flag, handlers: CommandHandlers) -> None:
    """Add hub-ci command and all subcommands.

    This function serves as the orchestrator, delegating to family-specific
    parser modules while maintaining a stable CLI surface.
    """
    hub_ci = subparsers.add_parser("hub-ci", help="Hub production CI helpers")
    add_json_flag(hub_ci)  # Add --json flag at parent level for all subcommands
    hub_ci.set_defaults(func=handlers.cmd_hub_ci)
    hub_ci_sub = hub_ci.add_subparsers(dest="subcommand", required=True)

    # Register parsers from each family module
    # Order matches original file for easier diff comparison
    add_release_parsers(hub_ci_sub, add_json_flag)  # actionlint, kyverno, trivy, zizmor, release, pytest-summary
    add_validation_parsers(hub_ci_sub, add_json_flag)  # syntax-check, yamllint, repo-check, validate-*
    add_security_parsers(hub_ci_sub, add_json_flag)  # security-*, bandit, pip-audit
    add_java_tools_parsers(hub_ci_sub, add_json_flag)  # codeql-build, smoke-java-*
    add_smoke_parsers(hub_ci_sub, add_json_flag)  # smoke-python-*
    add_python_tools_parsers(hub_ci_sub, add_json_flag)  # ruff, black, mypy, mutmut
    add_test_metrics_parsers(hub_ci_sub, add_json_flag)  # test-metrics
    add_badges_parsers(hub_ci_sub, add_json_flag)  # badges, badges-commit, outputs
    add_thresholds_parsers(hub_ci_sub, add_json_flag)  # thresholds


__all__ = ["add_hub_ci_commands"]
