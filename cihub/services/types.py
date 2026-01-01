"""Shared types for the services layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceResult:
    """Base result type for all services.

    Not frozen to allow inheritance by mutable result types.
    """

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RepoEntry:
    """Single repository configuration entry for workflow dispatch.

    This represents the flattened config used by hub-run-all.yml matrix.
    Not frozen because we build it incrementally from config loading.
    """

    config_basename: str
    name: str
    owner: str
    language: str
    branch: str
    subdir: str = ""
    subdir_safe: str = ""
    run_group: str = "full"
    dispatch_enabled: bool = True
    dispatch_workflow: str = "hub-ci.yml"

    # Tool flags (run_*)
    tools: dict[str, bool] = field(default_factory=dict)

    # Thresholds (coverage_min, max_*, etc.)
    thresholds: dict[str, int | float | None] = field(default_factory=dict)

    # Language-specific settings
    java_version: str | None = None
    python_version: str | None = None
    build_tool: str | None = None
    retention_days: int | None = None
    write_github_summary: bool = True

    @property
    def full(self) -> str:
        """Full repository name (owner/name)."""
        return f"{self.owner}/{self.name}"

    def to_matrix_entry(self) -> dict[str, Any]:
        """Convert to GitHub Actions matrix entry format.

        Flattens tools and thresholds into top-level keys.
        """
        entry: dict[str, Any] = {
            "config_basename": self.config_basename,
            "name": self.name,
            "owner": self.owner,
            "language": self.language,
            "branch": self.branch,
            "default_branch": self.branch,
            "subdir": self.subdir,
            "subdir_safe": self.subdir_safe,
            "run_group": self.run_group,
            "dispatch_enabled": self.dispatch_enabled,
            "dispatch_workflow": self.dispatch_workflow,
            "write_github_summary": self.write_github_summary,
        }

        # Add language-specific fields
        if self.java_version:
            entry["java_version"] = self.java_version
        if self.python_version:
            entry["python_version"] = self.python_version
        if self.build_tool:
            entry["build_tool"] = self.build_tool
        if self.retention_days is not None:
            entry["retention_days"] = self.retention_days

        # Flatten tools and thresholds
        entry.update(self.tools)
        entry.update(self.thresholds)

        return entry
