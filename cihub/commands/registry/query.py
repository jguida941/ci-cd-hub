"""Registry query commands (read-only operations)."""

from __future__ import annotations

import argparse

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.registry_service import (
    get_repo_config,
    list_repos,
    load_registry,
)
from cihub.types import CommandResult


def _cmd_list(args: argparse.Namespace) -> CommandResult:
    """List all repos with their tiers."""
    registry = load_registry()
    repos = list_repos(registry)

    # Filter by tier if specified
    tier_filter = getattr(args, "tier", None)
    if tier_filter:
        repos = [r for r in repos if r["tier"] == tier_filter]

    if not repos:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="No repos found" + (f" for tier '{tier_filter}'" if tier_filter else ""),
            data={"repos": [], "count": 0},
        )

    # Format for display
    lines = []
    for repo in repos:
        override_marker = "*" if repo.get("has_threshold_overrides") else " "
        eff = repo["effective"]
        lines.append(
            f"{repo['name']:<30} {repo['tier']:<10}{override_marker} "
            f"cov>={eff['coverage_min']:>3}% mut>={eff['mutation_score_min']:>3}% "
            f"crit<={eff['max_critical_vulns']} high<={eff['max_high_vulns']}"
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(repos)} repos" + (f" in tier '{tier_filter}'" if tier_filter else ""),
        data={
            "repos": repos,
            "count": len(repos),
            "raw_output": "\n".join(lines),
        },
    )


def _cmd_show(args: argparse.Namespace) -> CommandResult:
    """Show detailed config for a repo."""
    repo_name = args.repo
    registry = load_registry()
    config = get_repo_config(registry, repo_name)

    if config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repo not found: {repo_name}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repo '{repo_name}' not in registry",
                    "code": "CIHUB-REGISTRY-NOT-FOUND",
                }
            ],
        )

    # Format for display
    lines = [
        f"Repository: {config['name']}",
        f"Tier: {config['tier']}",
        f"Description: {config['description'] or '-'}",
        "",
        "Effective Settings:",
        f"  coverage_min:        {config['effective']['coverage_min']}%",
        f"  mutation_score_min:  {config['effective']['mutation_score_min']}%",
        f"  max_critical_vulns:  {config['effective']['max_critical_vulns']}",
        f"  max_high_vulns:      {config['effective']['max_high_vulns']}",
    ]

    if config["overrides"]:
        lines.extend(
            [
                "",
                "Overrides (from tier defaults):",
            ]
        )
        for key, value in config["overrides"].items():
            tier_val = config["tier_defaults"].get(key, "?")
            lines.append(f"  {key}: {tier_val} -> {value}")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Config for {repo_name} (tier: {config['tier']})",
        data={
            **config,
            "raw_output": "\n".join(lines),
        },
    )
