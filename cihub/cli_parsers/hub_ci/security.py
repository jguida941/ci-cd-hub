"""Parser setup for hub-ci security subcommands."""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Callable

from cihub.cli_parsers.common import (
    add_output_args,
    add_path_args,
    add_summary_args,
)


def add_security_parsers(
    hub_ci_sub: _SubParsersAction,
    add_json_flag: Callable,
) -> None:
    """Add security-related subcommand parsers.

    Subcommands: security-pip-audit, security-bandit, security-ruff, security-owasp,
    bandit, pip-audit
    """
    hub_ci_security_pip_audit = hub_ci_sub.add_parser(
        "security-pip-audit",
        help="Run pip-audit for hub-security workflows",
    )
    add_path_args(hub_ci_security_pip_audit)
    hub_ci_security_pip_audit.add_argument(
        "--report",
        default="pip-audit-report.json",
        help="Output report path (relative to repo)",
    )
    hub_ci_security_pip_audit.add_argument(
        "--requirements",
        nargs="*",
        default=["requirements.txt"],
        help="Requirements files to install",
    )
    add_output_args(hub_ci_security_pip_audit)
    add_json_flag(hub_ci_security_pip_audit)

    hub_ci_security_bandit = hub_ci_sub.add_parser(
        "security-bandit",
        help="Run bandit for hub-security workflows",
    )
    add_path_args(hub_ci_security_bandit)
    hub_ci_security_bandit.add_argument(
        "--report",
        default="bandit-report.json",
        help="Output report path (relative to repo)",
    )
    add_output_args(hub_ci_security_bandit)
    add_json_flag(hub_ci_security_bandit)

    hub_ci_security_ruff = hub_ci_sub.add_parser(
        "security-ruff",
        help="Run Ruff security rules for hub-security workflows",
    )
    add_path_args(hub_ci_security_ruff)
    hub_ci_security_ruff.add_argument(
        "--report",
        default="ruff-security.json",
        help="Output report path (relative to repo)",
    )
    add_output_args(hub_ci_security_ruff)
    add_json_flag(hub_ci_security_ruff)

    hub_ci_security_owasp = hub_ci_sub.add_parser(
        "security-owasp",
        help="Run OWASP Dependency-Check for hub-security workflows",
    )
    add_path_args(hub_ci_security_owasp)
    add_output_args(hub_ci_security_owasp)
    add_json_flag(hub_ci_security_owasp)

    # Standalone security tools (hub-ci bandit, hub-ci pip-audit)
    hub_ci_bandit = hub_ci_sub.add_parser("bandit", help="Run bandit and enforce severity gates")
    hub_ci_bandit.add_argument(
        "--paths",
        nargs="+",
        default=["cihub", "scripts"],
        help="Paths to scan",
    )
    hub_ci_bandit.add_argument("--output", default="bandit.json", help="Bandit JSON output path")
    hub_ci_bandit.add_argument("--severity", default="medium", help="Bandit severity level")
    hub_ci_bandit.add_argument("--confidence", default="medium", help="Bandit confidence level")
    fail_on_high_group = hub_ci_bandit.add_mutually_exclusive_group()
    fail_on_high_group.add_argument(
        "--fail-on-high",
        action="store_true",
        dest="fail_on_high",
        help="Fail if HIGH severity issues found (default: true)",
    )
    fail_on_high_group.add_argument(
        "--no-fail-on-high",
        dest="fail_on_high",
        action="store_false",
        help="Do not fail on HIGH severity issues",
    )
    hub_ci_bandit.set_defaults(fail_on_high=True)
    hub_ci_bandit.add_argument(
        "--fail-on-medium",
        action="store_true",
        default=False,
        help="Fail if MEDIUM severity issues found (default: false)",
    )
    hub_ci_bandit.add_argument(
        "--fail-on-low",
        action="store_true",
        default=False,
        help="Fail if LOW severity issues found (default: false)",
    )
    add_summary_args(hub_ci_bandit)
    hub_ci_bandit.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_bandit)

    hub_ci_pip_audit = hub_ci_sub.add_parser("pip-audit", help="Run pip-audit and enforce vulnerability gate")
    hub_ci_pip_audit.add_argument(
        "--requirements",
        nargs="+",
        default=["requirements/requirements.txt", "requirements/requirements-dev.txt"],
        help="Requirements files",
    )
    hub_ci_pip_audit.add_argument("--output", default="pip-audit.json", help="pip-audit JSON output path")
    add_summary_args(hub_ci_pip_audit)
    hub_ci_pip_audit.add_argument(
        "--github-summary",
        action="store_true",
        help="Append summary to GITHUB_STEP_SUMMARY",
    )
    add_json_flag(hub_ci_pip_audit)
