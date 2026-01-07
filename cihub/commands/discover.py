"""Discover command handler - matrix generation for hub-run-all.yml."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import DiscoveryFilters, discover_repositories
from cihub.types import CommandResult
from cihub.utils.paths import hub_root


def cmd_discover(args: argparse.Namespace) -> CommandResult:
    """Generate matrix from config/repos/*.yaml for GitHub Actions.

    Uses the discovery service for core logic; this function handles
    CLI-specific output formatting and returns CommandResult.

    Always returns CommandResult for consistent output handling.
    """
    hub = Path(args.hub_root).resolve() if args.hub_root else hub_root()
    items: list[str] = []  # Human-readable output
    problems: list[dict[str, str]] = []

    # Parse filters from CLI args
    run_group_filter = getattr(args, "run_group", "") or ""
    filter_groups = [g.strip() for g in run_group_filter.split(",") if g.strip()]

    repo_filter = getattr(args, "repos", "") or ""
    filter_repos = [r.strip() for r in repo_filter.split(",") if r.strip()]

    central_only = bool(getattr(args, "central_only", False))
    dispatch_only = bool(getattr(args, "dispatch_only", False))
    if central_only and dispatch_only:
        message = "Choose only one: --central-only or --dispatch-only"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

    use_central_runner = True if central_only else False if dispatch_only else None
    filters = DiscoveryFilters(
        run_groups=filter_groups,
        repos=filter_repos,
        use_central_runner=use_central_runner,
    )

    # Call service
    result = discover_repositories(hub, filters)

    # Handle service errors
    if not result.success:
        message = result.errors[0] if result.errors else "Discovery failed"
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": m} for m in result.errors],
        )

    # Collect warnings (for CI visibility)
    warnings: list[str] = []
    for warning in result.warnings:
        warnings.append(warning)
        items.append(f"::warning::{warning}")

    # Convert to matrix format
    entries = [e.to_matrix_entry() for e in result.entries]
    matrix = {"include": entries}

    # Check for empty results BEFORE writing to GITHUB_OUTPUT
    if not entries:
        message = "No repositories found after filtering."
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

    # Output to GITHUB_OUTPUT if requested (only after validation)
    github_output_written = False
    if args.github_output:
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(f"matrix={json.dumps(matrix)}\n")
                handle.write(f"count={len(entries)}\n")
            github_output_written = True
        else:
            problems.append(
                {
                    "severity": "warning",
                    "message": "--github-output specified but GITHUB_OUTPUT not set",
                }
            )
            items.append("Warning: --github-output specified but GITHUB_OUTPUT not set")

    # Build summary output
    items.append(f"Found {len(entries)} repositories")
    for entry in result.entries:
        subdir_info = f" subdir={entry.subdir}" if entry.subdir else ""
        items.append(f"- {entry.full} ({entry.language}) run_group={entry.run_group}{subdir_info}")

    # Include matrix JSON in output if not writing to GITHUB_OUTPUT
    raw_output = ""
    if not args.github_output:
        raw_output = json.dumps(matrix, indent=2)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(entries)} repositories",
        problems=problems,
        data={
            "matrix": matrix,
            "count": len(entries),
            "items": items,
            "raw_output": raw_output,
            "warnings": warnings,
            "github_output_written": github_output_written,
        },
    )
