"""Shared argument factories for CLI parsers.

This module eliminates 36+ duplicate argument definitions by providing
reusable factory functions for common CLI patterns.

Usage:
    from cihub.cli_parsers.common import add_output_args, add_summary_args

    parser = subparsers.add_parser("my-command", help="My command")
    add_output_args(parser)  # Adds --output and --github-output
    add_summary_args(parser)  # Adds --summary

★ Insight ─────────────────────────────────────
Why factory functions instead of inheritance/mixins?
1. argparse doesn't support parser inheritance cleanly
2. Factory functions compose - call multiple for different combos
3. Easy to test: just verify arguments exist on mock parser
─────────────────────────────────────────────────
"""

from __future__ import annotations

from argparse import ArgumentParser


def add_output_args(
    parser: ArgumentParser,
    *,
    output_help: str = "Write outputs to file",
    include_github_output: bool = True,
) -> None:
    """Add standard --output and --github-output arguments.

    Args:
        parser: The argparse parser/subparser to add arguments to.
        output_help: Custom help text for --output (default: "Write outputs to file").
        include_github_output: Whether to include --github-output flag (default: True).

    Example:
        >>> parser = ArgumentParser()
        >>> add_output_args(parser)
        >>> args = parser.parse_args(["--output", "out.txt"])
        >>> args.output
        'out.txt'
    """
    parser.add_argument("--output", help=output_help)
    if include_github_output:
        parser.add_argument(
            "--github-output",
            action="store_true",
            help="Write outputs to GITHUB_OUTPUT",
        )


def add_summary_args(
    parser: ArgumentParser,
    *,
    summary_help: str = "Write summary to file",
) -> None:
    """Add standard --summary argument.

    Args:
        parser: The argparse parser/subparser to add arguments to.
        summary_help: Custom help text for --summary.

    Example:
        >>> parser = ArgumentParser()
        >>> add_summary_args(parser)
        >>> args = parser.parse_args(["--summary", "summary.md"])
        >>> args.summary
        'summary.md'
    """
    parser.add_argument("--summary", help=summary_help)


def add_repo_args(
    parser: ArgumentParser,
    *,
    required: bool = False,
    default: str | None = ".",
    help_text: str = "Path to repo",
) -> None:
    """Add standard --repo argument.

    Args:
        parser: The argparse parser/subparser to add arguments to.
        required: Whether --repo is required (default: False).
        default: Default value when not required (default: ".").
        help_text: Custom help text.

    Example:
        >>> parser = ArgumentParser()
        >>> add_repo_args(parser)
        >>> args = parser.parse_args([])
        >>> args.repo
        '.'
    """
    if required:
        parser.add_argument("--repo", required=True, help=help_text)
    else:
        full_help = f"{help_text} (default: {default})" if default else help_text
        parser.add_argument("--repo", default=default, help=full_help)


def add_report_args(
    parser: ArgumentParser,
    *,
    required: bool = False,
    default: str | None = None,
    help_text: str = "Path to report.json",
) -> None:
    """Add standard --report argument.

    Args:
        parser: The argparse parser/subparser to add arguments to.
        required: Whether --report is required (default: False).
        default: Default value when not required.
        help_text: Custom help text.

    Example:
        >>> parser = ArgumentParser()
        >>> add_report_args(parser, required=True)
        >>> # --report is now required
    """
    if required:
        parser.add_argument("--report", required=True, help=help_text)
    else:
        parser.add_argument("--report", default=default, help=help_text)


def add_path_args(
    parser: ArgumentParser,
    *,
    default: str = "repo",
    help_text: str = "Repo path",
) -> None:
    """Add standard --path argument (for repo checkout paths).

    Args:
        parser: The argparse parser/subparser to add arguments to.
        default: Default value (default: "repo").
        help_text: Custom help text.
    """
    parser.add_argument("--path", default=default, help=help_text)


def add_output_dir_args(
    parser: ArgumentParser,
    *,
    default: str = ".",
    help_text: str = "Output directory",
) -> None:
    """Add standard --output-dir argument.

    Args:
        parser: The argparse parser/subparser to add arguments to.
        default: Default value (default: ".").
        help_text: Custom help text.
    """
    parser.add_argument("--output-dir", default=default, help=help_text)


def add_ai_flags(parser: ArgumentParser) -> None:
    """Add standard --ai/--no-ai arguments for optional AI enhancement."""
    parser.add_argument(
        "--ai",
        action="store_true",
        default=False,
        help="Enable AI-assisted analysis (requires Claude CLI)",
    )
    parser.add_argument(
        "--no-ai",
        action="store_false",
        dest="ai",
        help="Disable AI assistance",
    )


# =============================================================================
# Composite Helpers (common combinations)
# =============================================================================


def add_ci_output_args(parser: ArgumentParser) -> None:
    """Add both --output and --summary for CI commands.

    This is a common pattern for hub-ci subcommands that produce
    both machine-readable outputs and human-readable summaries.
    """
    add_output_args(parser)
    add_summary_args(parser)


def add_tool_runner_args(
    parser: ArgumentParser,
    *,
    path_default: str = "repo",
) -> None:
    """Add standard arguments for tool runner commands.

    Adds: --path, --output, --github-output

    Args:
        parser: The argparse parser/subparser to add arguments to.
        path_default: Default value for --path.
    """
    add_path_args(parser, default=path_default)
    add_output_args(parser)


# =============================================================================
# See Also References
# =============================================================================

# Mapping of command names to related commands for help epilogs
SEE_ALSO: dict[str, list[str]] = {
    # Core workflow
    "detect": ["init", "preflight", "scaffold"],
    "preflight": ["detect", "check", "smoke"],
    "doctor": ["preflight", "check"],
    "scaffold": ["smoke", "init", "detect"],
    "smoke": ["scaffold", "check", "ci"],
    "check": ["smoke", "verify", "ci", "preflight"],
    "verify": ["check", "sync-templates", "ci"],
    "ci": ["check", "run", "report", "triage"],
    "run": ["ci", "tool list"],
    # Reporting & triage
    "report": ["ci", "triage"],
    "triage": ["ci", "report"],
    # Registry management
    "registry": ["profile", "tool", "threshold", "repo"],
    "profile": ["registry", "tool", "threshold"],
    "tool": ["registry", "profile", "run"],
    "threshold": ["registry", "profile"],
    "repo": ["registry", "config"],
    # Init & setup
    "init": ["detect", "scaffold", "update", "setup"],
    "update": ["init", "validate"],
    "validate": ["init", "check"],
    "setup": ["init", "setup-secrets", "setup-nvd"],
    "setup-secrets": ["setup", "setup-nvd"],
    "setup-nvd": ["setup", "setup-secrets"],
    # Documentation
    "docs": ["adr"],
    "adr": ["docs"],
    # Hub management
    "hub": ["registry", "hub-ci"],
    "hub-ci": ["hub", "ci", "triage"],
    "config": ["registry", "hub"],
    # Fix commands
    "fix": ["fix-pom", "fix-deps", "fix-gradle"],
    "fix-pom": ["fix", "fix-deps"],
    "fix-deps": ["fix", "fix-pom"],
    "fix-gradle": ["fix"],
}


def see_also_epilog(command: str) -> str | None:
    """Generate a See Also epilog for a command.

    Args:
        command: The command name to get related commands for.

    Returns:
        Formatted epilog string, or None if no related commands.

    Example:
        >>> see_also_epilog("smoke")
        'See also: scaffold, check, ci'
    """
    related = SEE_ALSO.get(command)
    if not related:
        return None
    return f"See also: {', '.join(related)}"
