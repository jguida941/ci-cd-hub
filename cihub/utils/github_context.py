"""GitHub Actions context helpers.

This module provides the GitHubContext dataclass for managing GitHub Actions
environment variables, output files, and summary files. It consolidates:
1. All GITHUB_* environment variable access
2. Output file writing (GITHUB_OUTPUT)
3. Summary file writing (GITHUB_STEP_SUMMARY)

Usage:
    # From environment (for reading GitHub context):
    ctx = GitHubContext.from_env()
    if ctx.is_ci:
        print(f"Running in CI: {ctx.repository}@{ctx.sha[:7]}")

    # From CLI args (for output writing):
    ctx = GitHubContext.from_args(args)
    ctx.write_outputs({"key": "value"})
    ctx.write_summary("## Summary\\n...")

    # Combined (read env + configure outputs):
    ctx = GitHubContext.from_env().with_output_config(args)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from cihub.utils.filesystem import FileSystem, RealFileSystem

if TYPE_CHECKING:
    pass


@dataclass
class GitHubContext:
    """Unified GitHub Actions context - environment + outputs + summaries.

    This dataclass encapsulates all GitHub Actions environment variables and
    provides a clean API for writing outputs and summaries. It replaces the
    scattered os.environ.get("GITHUB_*") calls throughout the codebase.

    Attributes:
        # Environment variables (read from GITHUB_*)
        repository: GITHUB_REPOSITORY (e.g., "owner/repo")
        ref: GITHUB_REF (e.g., "refs/heads/main")
        ref_name: GITHUB_REF_NAME (e.g., "main")
        sha: GITHUB_SHA (commit hash)
        run_id: GITHUB_RUN_ID (unique run identifier)
        run_number: GITHUB_RUN_NUMBER (incrementing run number)
        actor: GITHUB_ACTOR (user who triggered the workflow)
        event_name: GITHUB_EVENT_NAME (e.g., "push", "pull_request")
        workspace: GITHUB_WORKSPACE (checkout directory)
        workflow_ref: GITHUB_WORKFLOW_REF (workflow file reference)
        token: GITHUB_TOKEN or GH_TOKEN (for API authentication)

        # Output configuration
        output_path: Explicit path to write outputs (takes precedence over env).
        github_output: If True, write to GITHUB_OUTPUT env var path.
        summary_path: Explicit path to write summary (takes precedence over env).
        github_summary: If True, write to GITHUB_STEP_SUMMARY env var path.
    """

    # GitHub environment variables
    repository: str | None = None
    ref: str | None = None
    ref_name: str | None = None
    sha: str | None = None
    run_id: str | None = None
    run_number: str | None = None
    actor: str | None = None
    event_name: str | None = None
    workspace: Path | None = None
    workflow_ref: str | None = None
    token: str | None = None

    # Output configuration (from original OutputContext)
    output_path: str | None = None
    github_output: bool = False
    summary_path: str | None = None
    github_summary: bool = False
    json_mode: bool = False
    filesystem: FileSystem = field(default_factory=RealFileSystem)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> GitHubContext:
        """Create context from environment variables.

        Args:
            env: Environment mapping to read from. Defaults to os.environ.

        Returns:
            GitHubContext populated from GITHUB_* environment variables.
        """
        env = env if env is not None else os.environ
        workspace_str = env.get("GITHUB_WORKSPACE")
        return cls(
            repository=env.get("GITHUB_REPOSITORY"),
            ref=env.get("GITHUB_REF"),
            ref_name=env.get("GITHUB_REF_NAME"),
            sha=env.get("GITHUB_SHA"),
            run_id=env.get("GITHUB_RUN_ID"),
            run_number=env.get("GITHUB_RUN_NUMBER"),
            actor=env.get("GITHUB_ACTOR"),
            event_name=env.get("GITHUB_EVENT_NAME"),
            workspace=Path(workspace_str) if workspace_str else None,
            workflow_ref=env.get("GITHUB_WORKFLOW_REF"),
            token=env.get("GITHUB_TOKEN") or env.get("GH_TOKEN"),
        )

    @classmethod
    def from_args(cls, args: Any) -> GitHubContext:
        """Create context from argparse namespace.

        This creates a context configured for output writing. For a full
        context with environment variables, use from_env().with_output_config().

        Args:
            args: Argparse namespace with optional output/summary attributes.

        Returns:
            GitHubContext configured from the args (output config only).
        """
        return cls(
            output_path=getattr(args, "output", None),
            github_output=getattr(args, "github_output", False),
            summary_path=getattr(args, "summary", None),
            github_summary=getattr(args, "github_summary", False),
            json_mode=getattr(args, "json", False),
        )

    def with_output_config(
        self,
        args: Any = None,
        *,
        output_path: str | None = None,
        github_output: bool | None = None,
        summary_path: str | None = None,
        github_summary: bool | None = None,
    ) -> GitHubContext:
        """Return a new context with output configuration added.

        This allows combining environment context with output config:
            ctx = GitHubContext.from_env().with_output_config(args)

        Args:
            args: Optional argparse namespace to extract output config from.
            output_path: Explicit output path override.
            github_output: Whether to use GITHUB_OUTPUT.
            summary_path: Explicit summary path override.
            github_summary: Whether to use GITHUB_STEP_SUMMARY.

        Returns:
            New GitHubContext with output configuration merged.
        """
        updates: dict[str, Any] = {}
        if args is not None:
            updates["output_path"] = getattr(args, "output", None)
            updates["github_output"] = getattr(args, "github_output", False)
            updates["summary_path"] = getattr(args, "summary", None)
            updates["github_summary"] = getattr(args, "github_summary", False)
            updates["json_mode"] = getattr(args, "json", False)
        if output_path is not None:
            updates["output_path"] = output_path
        if github_output is not None:
            updates["github_output"] = github_output
        if summary_path is not None:
            updates["summary_path"] = summary_path
        if github_summary is not None:
            updates["github_summary"] = github_summary
        return replace(self, **updates)

    @property
    def is_ci(self) -> bool:
        """Check if running in GitHub Actions CI environment."""
        return self.run_id is not None

    @property
    def owner_repo(self) -> tuple[str, str] | None:
        """Split repository into (owner, repo) tuple.

        Returns:
            Tuple of (owner, repo) if repository is set and contains '/'.
            None otherwise.
        """
        if self.repository and "/" in self.repository:
            owner, repo = self.repository.split("/", 1)
            return (owner, repo)
        return None

    @property
    def owner(self) -> str | None:
        """Get repository owner."""
        parts = self.owner_repo
        return parts[0] if parts else None

    @property
    def repo(self) -> str | None:
        """Get repository name (without owner)."""
        parts = self.owner_repo
        return parts[1] if parts else None

    @property
    def short_sha(self) -> str | None:
        """Get short (7-char) commit SHA."""
        return self.sha[:7] if self.sha else None

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
            # In JSON mode, stdout must remain JSON-only. Outputs should be captured in
            # CommandResult.data by the command, or written to GITHUB_OUTPUT.
            if self.json_mode:
                return
            for key, value in values.items():
                print(f"{key}={value}")
            return
        output_text = "".join(f"{key}={value}\n" for key, value in values.items())
        self.filesystem.append_text(resolved, output_text)

    def write_summary(self, text: str) -> None:
        """Append markdown text to the resolved summary path.

        If no path is resolved (neither explicit path nor GITHUB_STEP_SUMMARY),
        the text is printed to stdout.

        Args:
            text: Markdown text to append to summary.
        """
        resolved = self._resolve_summary_path()
        if resolved is None:
            # In JSON mode, stdout must remain JSON-only. Summaries should be captured in
            # CommandResult.summary/data by the command, or written to GITHUB_STEP_SUMMARY.
            if self.json_mode:
                return
            print(text)
            return
        summary_text = text if text.endswith("\n") else f"{text}\n"
        self.filesystem.append_text(resolved, summary_text)

    def has_output(self) -> bool:
        """Check if outputs will be written to a file (not stdout)."""
        return self._resolve_output_path() is not None

    def has_summary(self) -> bool:
        """Check if summary will be written to a file (not stdout)."""
        return self._resolve_summary_path() is not None


# Backward compatibility alias
OutputContext = GitHubContext
