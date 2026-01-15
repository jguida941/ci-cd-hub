"""Registry synchronization commands (registry <-> configs)."""

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.registry_service import (
    bootstrap_from_configs,
    compute_diff,
    load_registry,
    sync_to_configs,
)
from cihub.types import CommandResult
from cihub.utils.paths import hub_root

from ._utils import _derive_hub_root_from_configs_dir


def _cmd_diff(args: argparse.Namespace) -> CommandResult:
    """Show drift from tier defaults vs actual configs."""
    configs_arg = Path(args.configs_dir) if args.configs_dir else hub_root() / "config" / "repos"

    hub_root_for_target = _derive_hub_root_from_configs_dir(configs_arg)
    if args.configs_dir and hub_root_for_target is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unable to derive hub root from --configs-dir: {configs_arg}",
            problems=[
                {
                    "severity": "error",
                    "message": (
                        "Expected --configs-dir to point at <hub>/config or "
                        "<hub>/config/repos (or be within a hub root)."
                    ),
                    "code": "CIHUB-REGISTRY-CONFIGS-DIR-NO-HUB-ROOT",
                }
            ],
            suggestions=[
                {"message": "Pass --configs-dir <hub>/config/repos (recommended)."},
                {"message": "Or run the command from the target hub checkout so default paths apply."},
            ],
        )
    hub_root_for_target = hub_root_for_target or hub_root()
    if args.configs_dir:
        # Allow --configs-dir to be <hub>/config or <hub>/config/repos (or any path within hub root).
        if configs_arg.name == "repos" and configs_arg.parent.name == "config":
            configs_dir = configs_arg
        else:
            configs_dir = hub_root_for_target / "config" / "repos"
    else:
        configs_dir = configs_arg

    if not configs_dir.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Configs directory not found: {configs_dir}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Directory not found: {configs_dir}",
                    "code": "CIHUB-REGISTRY-DIR-NOT-FOUND",
                }
            ],
        )
    registry_path = hub_root_for_target / "config" / "registry.json"
    if args.configs_dir and not registry_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Registry file not found: {registry_path}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Missing registry.json in derived hub root: {registry_path}",
                    "code": "CIHUB-REGISTRY-NO-REGISTRY-FILE",
                }
            ],
            suggestions=[
                {
                    "message": f"Create {registry_path} (see schema/registry.schema.json) "
                    "or copy it from your hub checkout."
                },
                {"message": "Then rerun cihub registry diff/sync."},
            ],
        )
    registry = load_registry(registry_path=registry_path)

    # Build repo_paths if --repos-root provided (for .ci-hub.yml override detection)
    repo_paths: dict[str, Path] | None = None
    repos_root_warnings: list[dict[str, str]] = []
    repos_root = getattr(args, "repos_root", None)
    if repos_root:
        repos_root_path = Path(repos_root)
        if not repos_root_path.exists():
            repos_root_warnings.append(
                {
                    "severity": "warning",
                    "message": f"--repos-root path does not exist: {repos_root_path}",
                    "code": "CIHUB-REGISTRY-REPOS-ROOT-MISSING",
                }
            )
        else:
            repo_paths = {}
            for repo_name in registry.get("repos", {}).keys():
                repo_dir = repos_root_path / repo_name
                if repo_dir.is_dir():
                    repo_paths[repo_name] = repo_dir
            if not repo_paths:
                repos_root_warnings.append(
                    {
                        "severity": "warning",
                        "message": f"--repos-root has no matching repo directories: {repos_root_path}",
                        "code": "CIHUB-REGISTRY-REPOS-ROOT-EMPTY",
                    }
                )

    diffs = compute_diff(
        registry,
        configs_dir,
        hub_root_path=hub_root_for_target,
        repo_paths=repo_paths,
    )

    if not diffs:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="All repos in sync with registry",
            data={"diffs": [], "count": 0},
            problems=repos_root_warnings if repos_root_warnings else [],
        )

    # Format for display
    lines = []
    for diff in diffs:
        lines.append(
            f"{diff['repo']}: {diff['field']} (registry: {diff['registry_value']}, actual: {diff['actual_value']})"
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(diffs)} difference(s)",
        data={
            "diffs": diffs,
            "count": len(diffs),
            "raw_output": "\n".join(lines),
        },
        problems=repos_root_warnings if repos_root_warnings else [],
    )


def _cmd_sync(args: argparse.Namespace) -> CommandResult:
    """Sync registry settings to repo configs."""
    configs_arg = Path(args.configs_dir) if args.configs_dir else hub_root() / "config" / "repos"

    hub_root_for_target = _derive_hub_root_from_configs_dir(configs_arg)
    if args.configs_dir and hub_root_for_target is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unable to derive hub root from --configs-dir: {configs_arg}",
            problems=[
                {
                    "severity": "error",
                    "message": (
                        "Expected --configs-dir to point at <hub>/config or "
                        "<hub>/config/repos (or be within a hub root)."
                    ),
                    "code": "CIHUB-REGISTRY-CONFIGS-DIR-NO-HUB-ROOT",
                }
            ],
            suggestions=[
                {"message": "Pass --configs-dir <hub>/config/repos (recommended)."},
                {"message": "Or run the command from the target hub checkout so default paths apply."},
            ],
        )
    hub_root_for_target = hub_root_for_target or hub_root()
    if args.configs_dir:
        if configs_arg.name == "repos" and configs_arg.parent.name == "config":
            configs_dir = configs_arg
        else:
            configs_dir = hub_root_for_target / "config" / "repos"
    else:
        configs_dir = configs_arg

    if not configs_dir.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Configs directory not found: {configs_dir}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Directory not found: {configs_dir}",
                    "code": "CIHUB-REGISTRY-DIR-NOT-FOUND",
                }
            ],
        )
    registry_path = hub_root_for_target / "config" / "registry.json"
    if args.configs_dir and not registry_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Registry file not found: {registry_path}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Missing registry.json in derived hub root: {registry_path}",
                    "code": "CIHUB-REGISTRY-NO-REGISTRY-FILE",
                }
            ],
            suggestions=[
                {
                    "message": f"Create {registry_path} (see schema/registry.schema.json) "
                    "or copy it from your hub checkout."
                },
                {"message": "Then rerun cihub registry diff/sync."},
            ],
        )
    registry = load_registry(registry_path=registry_path)
    dry_run = args.dry_run or not args.yes

    changes = sync_to_configs(registry, configs_dir, dry_run=dry_run, hub_root_path=hub_root_for_target)

    # Count actual changes (including created/would_create)
    updates = [c for c in changes if c["action"] in ("updated", "would_update")]
    creates = [c for c in changes if c["action"] in ("created", "would_create")]
    skips = [c for c in changes if c["action"] == "skip"]
    unchanged = [c for c in changes if c["action"] == "unchanged"]

    # Build summary
    parts = []
    if dry_run:
        if updates:
            parts.append(f"would update {len(updates)}")
        if creates:
            parts.append(f"would create {len(creates)}")
        summary = f"Would sync: {', '.join(parts)} repo(s)" if parts else "No changes needed"
    else:
        if updates:
            parts.append(f"updated {len(updates)}")
        if creates:
            parts.append(f"created {len(creates)}")
        summary = f"Synced: {', '.join(parts)} repo(s)" if parts else "No changes made"

    # Format for display
    lines = []
    if creates:
        lines.append("Created:" if not dry_run else "Would create:")
        for change in creates:
            lines.append(f"  {change['repo']}")
    if updates:
        lines.append("Changes:" if not dry_run else "Would change:")
        for change in updates:
            for field, old, new in change.get("fields", []):
                lines.append(f"  {change['repo']}: {field} {old} -> {new}")
    if skips:
        lines.append("Skipped:")
        for change in skips:
            lines.append(f"  {change['repo']}: {change['reason']}")
    if unchanged:
        lines.append(f"Unchanged: {len(unchanged)} repo(s)")

    # Combine updates and creates for files_modified
    modified_repos = updates + creates

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data={
            "changes": changes,
            "updated_count": len(updates),
            "created_count": len(creates),
            "skipped_count": len(skips),
            "unchanged_count": len(unchanged),
            "dry_run": dry_run,
            "raw_output": "\n".join(lines),
        },
        files_modified=[str(configs_dir / f"{c['repo']}.yaml") for c in modified_repos] if not dry_run else [],
    )


def _cmd_bootstrap(args: argparse.Namespace) -> CommandResult:
    """Import existing config/repos/*.yaml files into the registry."""
    configs_arg = Path(args.configs_dir) if args.configs_dir else hub_root() / "config" / "repos"

    hub_root_for_target = _derive_hub_root_from_configs_dir(configs_arg)
    if args.configs_dir and hub_root_for_target is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unable to derive hub root from --configs-dir: {configs_arg}",
            problems=[
                {
                    "severity": "error",
                    "message": "Expected --configs-dir to point at <hub>/config/repos.",
                    "code": "CIHUB-REGISTRY-CONFIGS-DIR-NO-HUB-ROOT",
                }
            ],
        )
    hub_root_for_target = hub_root_for_target or hub_root()

    if args.configs_dir:
        if configs_arg.name == "repos" and configs_arg.parent.name == "config":
            configs_dir = configs_arg
        else:
            configs_dir = hub_root_for_target / "config" / "repos"
    else:
        configs_dir = configs_arg

    if not configs_dir.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Configs directory not found: {configs_dir}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Directory not found: {configs_dir}",
                    "code": "CIHUB-REGISTRY-DIR-NOT-FOUND",
                }
            ],
        )

    result = bootstrap_from_configs(
        configs_dir,
        default_tier=args.tier,
        strategy=args.strategy,
        dry_run=args.dry_run,
        include_thresholds=args.include_thresholds,
        hub_root_path=hub_root_for_target,
    )

    # Check for error
    if result.get("error"):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=result["error"],
            problems=[
                {
                    "severity": "error",
                    "message": result["error"],
                    "code": "CIHUB-REGISTRY-BOOTSTRAP-ERROR",
                }
            ],
        )

    imported = result["imported"]
    skipped = result["skipped"]
    conflicts = result["conflicts"]
    dry_run = result["dry_run"]

    # Format summary
    if dry_run:
        summary = f"Would import {len(imported)} repo(s)"
    else:
        summary = f"Imported {len(imported)} repo(s)"

    if skipped:
        summary += f", skipped {len(skipped)}"
    if conflicts:
        summary += f", {len(conflicts)} conflict(s) detected"

    # Format output
    lines = []
    if imported:
        lines.append("Imported:" if not dry_run else "Would import:")
        for repo in imported:
            lines.append(f"  {repo}")
    if skipped:
        lines.append("Skipped:")
        for skip in skipped:
            lines.append(f"  {skip['repo']}: {skip['reason']}")
    if conflicts:
        lines.append("Conflicts:")
        for conflict in conflicts:
            lines.append(
                f"  {conflict['repo']}.{conflict['field']}: "
                f"registry={conflict['registry_value']}, config={conflict['config_value']} "
                f"({conflict['resolution']})"
            )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data={
            "imported": imported,
            "imported_count": len(imported),
            "skipped": skipped,
            "skipped_count": len(skipped),
            "conflicts": conflicts,
            "conflicts_count": len(conflicts),
            "dry_run": dry_run,
            "raw_output": "\n".join(lines),
        },
        files_modified=["config/registry.json"] if not dry_run and imported else [],
    )
