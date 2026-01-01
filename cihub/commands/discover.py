"""Discover command handler - matrix generation for hub-run-all.yml."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cihub.cli import CommandResult, hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import DiscoveryFilters, discover_repositories


def cmd_discover(args: argparse.Namespace) -> int | CommandResult:
    """Generate matrix from config/repos/*.yaml for GitHub Actions.

    Uses the discovery service for core logic; this function handles
    CLI-specific output formatting (prints, GITHUB_OUTPUT, CommandResult).
    """
    hub = Path(args.hub_root).resolve() if args.hub_root else hub_root()
    json_mode = getattr(args, "json", False)

    # Parse filters from CLI args
    run_group_filter = getattr(args, "run_group", "") or ""
    filter_groups = [g.strip() for g in run_group_filter.split(",") if g.strip()]

    repo_filter = getattr(args, "repos", "") or ""
    filter_repos = [r.strip() for r in repo_filter.split(",") if r.strip()]

    filters = DiscoveryFilters(run_groups=filter_groups, repos=filter_repos)

    # Call service
    result = discover_repositories(hub, filters)

    # Handle service errors
    if not result.success:
        message = result.errors[0] if result.errors else "Discovery failed"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": m} for m in result.errors],
            )
        print(f"Error: {message}")
        return EXIT_FAILURE

    # Emit warnings (for CI visibility)
    for warning in result.warnings:
        print(f"::warning::{warning}")

    # Convert to matrix format
    entries = [e.to_matrix_entry() for e in result.entries]
    matrix = {"include": entries}

    # Output to GITHUB_OUTPUT if requested
    if args.github_output:
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(f"matrix={json.dumps(matrix)}\n")
                handle.write(f"count={len(entries)}\n")
        else:
            print("Warning: --github-output specified but GITHUB_OUTPUT not set")

    if not entries:
        message = "No repositories found after filtering."
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(f"Error: {message}")
        return EXIT_FAILURE

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Found {len(entries)} repositories",
            data={"matrix": matrix, "count": len(entries)},
        )

    # Print summary
    print(f"Found {len(entries)} repositories")
    for entry in result.entries:
        subdir_info = f" subdir={entry.subdir}" if entry.subdir else ""
        print(
            f"- {entry.full} ({entry.language}) "
            f"run_group={entry.run_group}{subdir_info}"
        )

    if not args.github_output:
        # Print matrix as JSON if not writing to GITHUB_OUTPUT
        print(json.dumps(matrix, indent=2))

    return EXIT_SUCCESS
