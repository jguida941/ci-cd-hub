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
from typing import Optional


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
    default: Optional[str] = ".",
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
    default: Optional[str] = None,
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
