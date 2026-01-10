"""Discovery service - reads repo configs and generates workflow matrix."""

from __future__ import annotations

import io
import re
from contextlib import redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.services.types import RepoEntry, ServiceResult
from cihub.tools.registry import THRESHOLD_KEYS, TOOL_KEYS

# Safe character pattern for repo metadata (prevents shell injection)
_SAFE_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

# Re-export with underscore names for backward compatibility
_TOOL_KEYS = TOOL_KEYS
_THRESHOLD_KEYS = THRESHOLD_KEYS


@dataclass(frozen=True, slots=True)
class DiscoveryFilters:
    """Filters for repository discovery."""

    run_groups: list[str] = field(default_factory=list)
    repos: list[str] = field(default_factory=list)
    use_central_runner: bool | None = None


@dataclass
class DiscoveryResult(ServiceResult):
    """Result of repository discovery."""

    entries: list[RepoEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of discovered repositories."""
        return len(self.entries)

    def to_matrix(self) -> dict[str, Any]:
        """Convert to GitHub Actions matrix format."""
        return {
            "matrix": {"include": [e.to_matrix_entry() for e in self.entries]},
            "count": self.count,
        }


def _sanitize_subdir(subdir: str) -> str:
    """Replace / with - in subdir to make it safe for artifact names."""
    return subdir.replace("/", "-")


def _load_single_repo(config_file: Path, hub_root: Path) -> tuple[RepoEntry | None, list[str]]:
    """Load a single repo config file.

    Captures any stderr output as warnings (no prints to terminal).

    Returns:
        (RepoEntry, warnings) on success
        (None, [error_message]) on failure
    """
    # Import here to avoid circular imports
    from cihub.config.loader import (
        ConfigValidationError,
        generate_workflow_inputs,
        load_config,
    )

    repos_dir = hub_root / "config" / "repos"
    try:
        repo_basename = config_file.relative_to(repos_dir).with_suffix("").as_posix()
    except Exception:  # noqa: BLE001
        repo_basename = config_file.stem
    captured_warnings: list[str] = []

    # Capture any stderr output from loader
    stderr_capture = io.StringIO()
    try:
        with redirect_stderr(stderr_capture):
            cfg = load_config(
                repo_name=repo_basename,
                hub_root=hub_root,
                exit_on_validation_error=False,
            )
    except ConfigValidationError as exc:
        # Preserve any stderr output as context
        stderr_output = stderr_capture.getvalue().strip()
        error_details = [f"{repo_basename}: validation failed ({exc})"]
        if stderr_output:
            error_details.extend(f"{repo_basename}: {line}" for line in stderr_output.splitlines())
        return None, error_details
    except SystemExit:
        stderr_output = stderr_capture.getvalue().strip()
        error_details = [f"{repo_basename}: validation aborted"]
        if stderr_output:
            error_details.extend(f"{repo_basename}: {line}" for line in stderr_output.splitlines())
        return None, error_details
    except Exception as exc:
        stderr_output = stderr_capture.getvalue().strip()
        error_details = [f"{repo_basename}: failed to load ({exc})"]
        if stderr_output:
            error_details.extend(f"{repo_basename}: {line}" for line in stderr_output.splitlines())
        return None, error_details

    # Collect any warnings printed during successful loading
    stderr_output = stderr_capture.getvalue().strip()
    if stderr_output:
        for line in stderr_output.splitlines():
            captured_warnings.append(f"{repo_basename}: {line}")

    repo_info = cfg.get("repo", {})
    owner = repo_info.get("owner")
    name = repo_info.get("name") or repo_basename
    language = repo_info.get("language") or cfg.get("language")
    subdir = repo_info.get("subdir", "")
    branch = repo_info.get("default_branch", "main")

    if not (owner and name and language):
        return None, [f"{repo_basename}: missing repo.owner/name/language"]

    # Validate all values are safe
    unsafe_fields = [
        ("owner", owner),
        ("name", name),
        ("subdir", subdir),
        ("branch", branch),
    ]
    if any(not _SAFE_RE.match(str(value)) for _, value in unsafe_fields if value):
        return None, [f"{repo_basename}: unsafe repo metadata"]

    inputs = generate_workflow_inputs(cfg)
    run_group = repo_info.get("run_group") or cfg.get("run_group") or "full"
    retention_days = cfg.get("reports", {}).get("retention_days")

    # Extract tool flags
    tools = {key: inputs[key] for key in _TOOL_KEYS if key in inputs}

    # Extract thresholds
    thresholds: dict[str, int | float | None] = {key: inputs[key] for key in _THRESHOLD_KEYS if key in inputs}

    entry = RepoEntry(
        config_basename=repo_basename,
        name=name,
        owner=owner,
        language=language,
        branch=branch,
        subdir=subdir,
        subdir_safe=_sanitize_subdir(subdir) if subdir else "",
        run_group=run_group,
        dispatch_enabled=repo_info.get("dispatch_enabled", True),
        dispatch_workflow=repo_info.get("dispatch_workflow", "hub-ci.yml"),
        use_central_runner=repo_info.get("use_central_runner", True),
        tools=tools,
        thresholds=thresholds,
        java_version=inputs.get("java_version"),
        python_version=inputs.get("python_version"),
        build_tool=inputs.get("build_tool"),
        retention_days=retention_days,
        write_github_summary=inputs.get("write_github_summary", True),
    )

    return entry, captured_warnings


def discover_repositories(
    hub_root: Path,
    filters: DiscoveryFilters | None = None,
) -> DiscoveryResult:
    """Discover all configured repositories.

    Captures all loader output as warnings (no prints to terminal).

    Args:
        hub_root: Path to hub-release root directory.
        filters: Optional filters to apply (run_groups, repos).

    Returns:
        DiscoveryResult with list of RepoEntry objects.
    """
    filters = filters or DiscoveryFilters()
    repos_dir = hub_root / "config" / "repos"

    if not repos_dir.exists():
        return DiscoveryResult(
            success=False,
            entries=[],
            errors=[f"Repos directory not found: {repos_dir}"],
        )

    entries: list[RepoEntry] = []
    all_warnings: list[str] = []

    for config_file in sorted(repos_dir.rglob("*.yaml")):
        entry, repo_warnings = _load_single_repo(config_file, hub_root)

        # Collect warnings from this repo
        all_warnings.extend(repo_warnings)

        if entry is None:
            continue

        # Apply repo filter
        if filters.repos:
            if not any(entry.name == r or entry.full == r or entry.config_basename == r for r in filters.repos):
                continue

        # Apply run_group filter
        if filters.run_groups and entry.run_group not in filters.run_groups:
            continue

        # Apply use_central_runner filter
        if filters.use_central_runner is not None and entry.use_central_runner != filters.use_central_runner:
            continue

        entries.append(entry)

    return DiscoveryResult(
        success=True,
        entries=entries,
        warnings=all_warnings,
    )
