"""GitHub Actions output context helpers.

This module provides the OutputContext dataclass for managing GitHub Actions
output and summary file paths. It consolidates the scattered 2-step pattern
(resolve path + write) into a single, clean API.

Usage:
    # From CLI args:
    ctx = OutputContext.from_args(args)
    ctx.write_outputs({"key": "value"})
    ctx.write_summary("## Summary\\n...")

    # Direct construction:
    ctx = OutputContext(output_path="out.txt", github_output=True)
    ctx.write_outputs({"status": "pass"})
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OutputContext:
    """Context for GitHub Actions outputs and summaries.

    This dataclass encapsulates the output configuration for GitHub Actions
    workflows, providing a clean API for writing outputs and summaries.

    Attributes:
        output_path: Explicit path to write outputs (takes precedence over env).
        github_output: If True, write to GITHUB_OUTPUT env var path.
        summary_path: Explicit path to write summary (takes precedence over env).
        github_summary: If True, write to GITHUB_STEP_SUMMARY env var path.
    """

    output_path: str | None = None
    github_output: bool = False
    summary_path: str | None = None
    github_summary: bool = False

    @classmethod
    def from_args(cls, args: Any) -> OutputContext:
        """Create OutputContext from argparse namespace.

        Safely extracts output-related attributes from args, using None/False
        as defaults for missing attributes.

        Args:
            args: Argparse namespace with optional output/summary attributes.

        Returns:
            OutputContext configured from the args.
        """
        return cls(
            output_path=getattr(args, "output", None),
            github_output=getattr(args, "github_output", False),
            summary_path=getattr(args, "summary", None),
            github_summary=getattr(args, "github_summary", False),
        )

    def _resolve_output_path(self) -> Path | None:
        """Resolve the effective output path."""
        if self.output_path:
            return Path(self.output_path)
        if self.github_output:
            env_path = os.environ.get("GITHUB_OUTPUT")
            return Path(env_path) if env_path else None
        return None

    def _resolve_summary_path(self) -> Path | None:
        """Resolve the effective summary path."""
        if self.summary_path:
            return Path(self.summary_path)
        if self.github_summary:
            env_path = os.environ.get("GITHUB_STEP_SUMMARY")
            return Path(env_path) if env_path else None
        return None

    def write_outputs(self, values: dict[str, str]) -> None:
        """Write key=value pairs to the resolved output path.

        If no path is resolved (neither explicit path nor GITHUB_OUTPUT),
        the values are printed to stdout.

        Args:
            values: Dictionary of key=value pairs to write.
        """
        resolved = self._resolve_output_path()
        if resolved is None:
            for key, value in values.items():
                print(f"{key}={value}")
            return
        with open(resolved, "a", encoding="utf-8") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")

    def write_summary(self, text: str) -> None:
        """Append markdown text to the resolved summary path.

        If no path is resolved (neither explicit path nor GITHUB_STEP_SUMMARY),
        the text is printed to stdout.

        Args:
            text: Markdown text to append to summary.
        """
        resolved = self._resolve_summary_path()
        if resolved is None:
            print(text)
            return
        with open(resolved, "a", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")

    def has_output(self) -> bool:
        """Check if outputs will be written to a file (not stdout)."""
        return self._resolve_output_path() is not None

    def has_summary(self) -> bool:
        """Check if summary will be written to a file (not stdout)."""
        return self._resolve_summary_path() is not None
