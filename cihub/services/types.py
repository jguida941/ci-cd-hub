"""Shared types for the services layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class RunCIOptions:
    """Configuration options for run_ci().

    Consolidates the 10 keyword parameters into a single immutable object.
    Use dataclasses.replace() to create modified copies.

    Example:
        # Default options
        opts = RunCIOptions()

        # Customized options
        opts = RunCIOptions(
            output_dir=Path(".cihub"),
            install_deps=True,
            correlation_id="abc-123",
        )

        # From CLI args
        opts = RunCIOptions.from_args(args)

        # Modify existing options
        new_opts = dataclasses.replace(opts, install_deps=False)
    """

    # Path options
    output_dir: Path | None = None
    report_path: Path | None = None
    summary_path: Path | None = None
    workdir: str | None = None

    # Boolean options
    install_deps: bool = False
    no_summary: bool = False
    write_github_summary: bool | None = None

    # String options
    correlation_id: str | None = None
    config_from_hub: str | None = None

    # Environment mapping (immutable via tuple conversion internally)
    env: Mapping[str, str] | None = None

    @classmethod
    def from_args(cls, args: Any) -> "RunCIOptions":
        """Create options from argparse namespace.

        Args:
            args: argparse.Namespace with CLI arguments

        Returns:
            RunCIOptions configured from CLI args
        """
        return cls(
            output_dir=Path(args.output_dir) if getattr(args, "output_dir", None) else None,
            report_path=Path(args.report) if getattr(args, "report", None) else None,
            summary_path=Path(args.summary) if getattr(args, "summary", None) else None,
            workdir=getattr(args, "workdir", None),
            install_deps=getattr(args, "install_deps", False),
            no_summary=getattr(args, "no_summary", False),
            write_github_summary=getattr(args, "write_github_summary", None),
            correlation_id=getattr(args, "correlation_id", None),
            config_from_hub=getattr(args, "config_from_hub", None),
        )


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
    use_central_runner: bool = True

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

    @property
    def config_basename_safe(self) -> str:
        """Safe basename for filenames/artifacts (slashes replaced)."""
        return self.config_basename.replace("/", "-")

    def to_matrix_entry(self) -> dict[str, Any]:
        """Convert to GitHub Actions matrix entry format.

        Flattens tools and thresholds into top-level keys.
        """
        entry: dict[str, Any] = {
            "config_basename": self.config_basename,
            "config_basename_safe": self.config_basename_safe,
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
            "use_central_runner": self.use_central_runner,
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
