"""Registry command implementation for centralized repo configuration."""

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.registry_service import (
    compute_diff,
    get_repo_config,
    list_repos,
    load_registry,
    save_registry,
    set_repo_override,
    set_repo_tier,
    sync_to_configs,
)
from cihub.types import CommandResult
from cihub.utils.paths import hub_root


def cmd_registry(args: argparse.Namespace) -> CommandResult:
    """Dispatch registry subcommands."""
    subcommand = getattr(args, "subcommand", None)

    handlers = {
        "list": _cmd_list,
        "show": _cmd_show,
        "set": _cmd_set,
        "diff": _cmd_diff,
        "sync": _cmd_sync,
        "add": _cmd_add,
    }

    handler = handlers.get(subcommand)
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown registry subcommand: {subcommand}",
            problems=[{
                "severity": "error",
                "message": f"Unknown subcommand '{subcommand}'",
                "code": "CIHUB-REGISTRY-UNKNOWN-SUBCOMMAND",
            }],
        )

    return handler(args)


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
        override_marker = "*" if repo["has_overrides"] else " "
        eff = repo["effective"]
        lines.append(
            f"{repo['name']:<30} {repo['tier']:<10}{override_marker} "
            f"cov={eff['coverage']:>3}% mut={eff['mutation']:>3}% vuln<={eff['vulns_max']}"
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
            problems=[{
                "severity": "error",
                "message": f"Repo '{repo_name}' not in registry",
                "code": "CIHUB-REGISTRY-NOT-FOUND",
            }],
        )

    # Format for display
    lines = [
        f"Repository: {config['name']}",
        f"Tier: {config['tier']}",
        f"Description: {config['description'] or '-'}",
        "",
        "Effective Settings:",
        f"  coverage:  {config['effective']['coverage']}%",
        f"  mutation:  {config['effective']['mutation']}%",
        f"  vulns_max: {config['effective']['vulns_max']}",
    ]

    if config["overrides"]:
        lines.extend([
            "",
            "Overrides (from tier defaults):",
        ])
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


def _cmd_set(args: argparse.Namespace) -> CommandResult:
    """Set tier or override for a repo."""
    repo_name = args.repo
    registry = load_registry()

    changes = []

    # Handle --tier
    if args.tier:
        try:
            set_repo_tier(registry, repo_name, args.tier)
            changes.append(f"tier={args.tier}")
        except ValueError as exc:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=str(exc),
                problems=[{
                    "severity": "error",
                    "message": str(exc),
                    "code": "CIHUB-REGISTRY-INVALID-TIER",
                }],
            )

    # Handle overrides
    if args.coverage is not None:
        set_repo_override(registry, repo_name, "coverage", args.coverage)
        changes.append(f"coverage={args.coverage}")

    if args.mutation is not None:
        set_repo_override(registry, repo_name, "mutation", args.mutation)
        changes.append(f"mutation={args.mutation}")

    if getattr(args, "vulns_max", None) is not None:
        set_repo_override(registry, repo_name, "vulns_max", args.vulns_max)
        changes.append(f"vulns_max={args.vulns_max}")

    if not changes:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="No changes specified",
            problems=[{
                "severity": "error",
                "message": "Specify --tier or an override (--coverage, --mutation, --vulns-max)",
                "code": "CIHUB-REGISTRY-NO-CHANGES",
            }],
        )

    # Save changes
    save_registry(registry)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Updated {repo_name}: {', '.join(changes)}",
        data={
            "repo": repo_name,
            "changes": changes,
        },
        files_modified=["config/registry.json"],
    )


def _cmd_diff(args: argparse.Namespace) -> CommandResult:
    """Show drift from tier defaults vs actual configs."""
    registry = load_registry()

    configs_dir = Path(args.configs_dir) if args.configs_dir else hub_root() / "config" / "repos"
    if not configs_dir.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Configs directory not found: {configs_dir}",
            problems=[{
                "severity": "error",
                "message": f"Directory not found: {configs_dir}",
                "code": "CIHUB-REGISTRY-DIR-NOT-FOUND",
            }],
        )

    diffs = compute_diff(registry, configs_dir)

    if not diffs:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="All repos in sync with registry",
            data={"diffs": [], "count": 0},
        )

    # Format for display
    lines = []
    for diff in diffs:
        lines.append(
            f"{diff['repo']}: {diff['field']} "
            f"(registry: {diff['registry_value']}, actual: {diff['actual_value']})"
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(diffs)} difference(s)",
        data={
            "diffs": diffs,
            "count": len(diffs),
            "raw_output": "\n".join(lines),
        },
    )


def _cmd_sync(args: argparse.Namespace) -> CommandResult:
    """Sync registry settings to repo configs."""
    registry = load_registry()

    configs_dir = Path(args.configs_dir) if args.configs_dir else hub_root() / "config" / "repos"
    if not configs_dir.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Configs directory not found: {configs_dir}",
            problems=[{
                "severity": "error",
                "message": f"Directory not found: {configs_dir}",
                "code": "CIHUB-REGISTRY-DIR-NOT-FOUND",
            }],
        )

    dry_run = args.dry_run or not args.yes

    changes = sync_to_configs(registry, configs_dir, dry_run=dry_run)

    # Count actual changes
    updates = [c for c in changes if c["action"] in ("updated", "would_update")]
    skips = [c for c in changes if c["action"] == "skip"]
    unchanged = [c for c in changes if c["action"] == "unchanged"]

    if dry_run:
        summary = f"Would update {len(updates)} repo(s)"
    else:
        summary = f"Updated {len(updates)} repo(s)"

    # Format for display
    lines = []
    if updates:
        lines.append("Changes:")
        for change in updates:
            for field, old, new in change.get("fields", []):
                lines.append(f"  {change['repo']}: {field} {old} -> {new}")
    if skips:
        lines.append("Skipped:")
        for change in skips:
            lines.append(f"  {change['repo']}: {change['reason']}")
    if unchanged:
        lines.append(f"Unchanged: {len(unchanged)} repo(s)")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data={
            "changes": changes,
            "updated_count": len(updates),
            "skipped_count": len(skips),
            "unchanged_count": len(unchanged),
            "dry_run": dry_run,
            "raw_output": "\n".join(lines),
        },
        files_modified=[str(configs_dir / f"{c['repo']}.yaml") for c in updates] if not dry_run else [],
    )


def _cmd_add(args: argparse.Namespace) -> CommandResult:
    """Add a new repo to the registry."""
    repo_name = args.repo
    tier = args.tier
    description = args.description

    registry = load_registry()

    # Check if repo already exists
    if repo_name in registry.get("repos", {}):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repo already exists: {repo_name}",
            problems=[{
                "severity": "error",
                "message": f"Repo '{repo_name}' already in registry. Use 'registry set' to modify.",
                "code": "CIHUB-REGISTRY-EXISTS",
            }],
        )

    # Validate tier
    if tier not in registry.get("tiers", {}):
        available = ", ".join(registry.get("tiers", {}).keys())
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown tier: {tier}",
            problems=[{
                "severity": "error",
                "message": f"Unknown tier '{tier}'. Available: {available}",
                "code": "CIHUB-REGISTRY-INVALID-TIER",
            }],
        )

    # Add repo
    repos = registry.setdefault("repos", {})
    repos[repo_name] = {"tier": tier}
    if description:
        repos[repo_name]["description"] = description

    save_registry(registry)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Added {repo_name} to registry (tier: {tier})",
        data={
            "repo": repo_name,
            "tier": tier,
            "description": description,
        },
        files_modified=["config/registry.json"],
    )
