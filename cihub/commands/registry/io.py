"""Registry I/O commands (bulk export/import operations)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.registry_service import (
    load_registry,
    save_registry,
)
from cihub.types import CommandResult


def _cmd_export(args: argparse.Namespace) -> CommandResult:
    """Export registry to a JSON file for backup."""
    output_path = Path(args.output)
    pretty = getattr(args, "pretty", False)

    # Load current registry
    registry = load_registry()

    # Write to output file
    try:
        indent = 2 if pretty else None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(registry, indent=indent), encoding="utf-8")
    except OSError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Failed to write export file: {exc}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Failed to write to {output_path}: {exc}",
                    "code": "CIHUB-REGISTRY-EXPORT-ERROR",
                }
            ],
        )

    # Count repos for summary
    repo_count = len(registry.get("repos", {}))
    tier_count = len(registry.get("tiers", {}))

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Exported registry to {output_path} ({repo_count} repos, {tier_count} tiers)",
        data={
            "output_path": str(output_path),
            "repo_count": repo_count,
            "tier_count": tier_count,
        },
        files_modified=[str(output_path)],
    )


def _cmd_import(args: argparse.Namespace) -> CommandResult:
    """Import registry from a JSON backup file."""
    input_path = Path(args.file)
    merge_mode = getattr(args, "merge", False)
    replace_mode = getattr(args, "replace", False)
    dry_run = getattr(args, "dry_run", False)

    # Validate mode flags
    if merge_mode and replace_mode:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Cannot use both --merge and --replace",
            problems=[
                {
                    "severity": "error",
                    "message": "Specify either --merge or --replace, not both",
                    "code": "CIHUB-REGISTRY-IMPORT-CONFLICT",
                }
            ],
        )

    if not merge_mode and not replace_mode:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Must specify --merge or --replace",
            problems=[
                {
                    "severity": "error",
                    "message": "Specify --merge to add/update repos, or --replace to overwrite entirely",
                    "code": "CIHUB-REGISTRY-IMPORT-MODE-REQUIRED",
                }
            ],
            suggestions=[
                {"message": "--merge: Add new repos, update existing with imported values"},
                {"message": "--replace: Completely replace registry with imported data"},
            ],
        )

    # Read input file
    if not input_path.exists():
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Import file not found: {input_path}",
            problems=[
                {
                    "severity": "error",
                    "message": f"File not found: {input_path}",
                    "code": "CIHUB-REGISTRY-IMPORT-NOT-FOUND",
                }
            ],
        )

    try:
        import_data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid JSON in import file: {exc}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Invalid JSON: {exc}",
                    "code": "CIHUB-REGISTRY-IMPORT-PARSE-ERROR",
                }
            ],
        )

    # Validate import data has expected structure
    if not isinstance(import_data, dict):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Import file must contain a JSON object",
            problems=[
                {
                    "severity": "error",
                    "message": "Expected JSON object with 'repos' and 'tiers' keys",
                    "code": "CIHUB-REGISTRY-IMPORT-INVALID",
                }
            ],
        )

    # Guard against malformed repos/tiers (must be dicts)
    import_repos = import_data.get("repos")
    import_tiers = import_data.get("tiers")

    if import_repos is not None and not isinstance(import_repos, dict):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Invalid import: 'repos' must be an object",
            problems=[
                {
                    "severity": "error",
                    "message": f"'repos' field must be a JSON object, got {type(import_repos).__name__}",
                    "code": "CIHUB-REGISTRY-IMPORT-INVALID-REPOS",
                }
            ],
        )

    if import_tiers is not None and not isinstance(import_tiers, dict):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Invalid import: 'tiers' must be an object",
            problems=[
                {
                    "severity": "error",
                    "message": f"'tiers' field must be a JSON object, got {type(import_tiers).__name__}",
                    "code": "CIHUB-REGISTRY-IMPORT-INVALID-TIERS",
                }
            ],
        )

    # Ensure required keys for replace mode
    if replace_mode:
        missing_keys = []
        if "schema_version" not in import_data:
            missing_keys.append("schema_version")
        if "tiers" not in import_data:
            missing_keys.append("tiers")
        if "repos" not in import_data:
            missing_keys.append("repos")

        if missing_keys:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Invalid import for --replace: missing {', '.join(missing_keys)}",
                problems=[
                    {
                        "severity": "error",
                        "message": "Replace mode requires a complete registry with: schema_version, tiers, repos",
                        "code": "CIHUB-REGISTRY-IMPORT-INCOMPLETE",
                    }
                ],
            )

    # Default to empty dicts if not present
    import_repos = import_repos or {}
    import_tiers = import_tiers or {}

    # Load current registry
    current_registry = load_registry()
    current_repos = current_registry.get("repos", {})

    # Calculate changes
    added_repos: list[str] = []
    updated_repos: list[str] = []
    unchanged_repos: list[str] = []

    if replace_mode:
        # Replace mode: just count what's different
        for repo_name in import_repos:
            if repo_name not in current_repos:
                added_repos.append(repo_name)
            elif import_repos[repo_name] != current_repos.get(repo_name):
                updated_repos.append(repo_name)
            else:
                unchanged_repos.append(repo_name)
        removed_repos = [r for r in current_repos if r not in import_repos]
    else:
        # Merge mode: add new, update existing, keep unmentioned
        removed_repos = []
        for repo_name, repo_data in import_repos.items():
            if repo_name not in current_repos:
                added_repos.append(repo_name)
            elif repo_data != current_repos.get(repo_name):
                updated_repos.append(repo_name)
            else:
                unchanged_repos.append(repo_name)

    # Apply changes if not dry-run
    if not dry_run:
        if replace_mode:
            # Replace entire registry
            new_registry = import_data
        else:
            # Merge: update current registry with import data
            new_registry = current_registry.copy()
            new_registry["repos"] = current_repos.copy()
            new_registry["repos"].update(import_repos)
            if import_tiers:
                new_registry["tiers"] = import_tiers

        save_registry(new_registry)

    # Build summary
    changes = []
    if added_repos:
        changes.append(f"added {len(added_repos)}")
    if updated_repos:
        changes.append(f"updated {len(updated_repos)}")
    if removed_repos:
        changes.append(f"removed {len(removed_repos)}")

    if dry_run:
        prefix = "Would import: "
    else:
        prefix = "Imported: "

    if changes:
        summary = prefix + ", ".join(changes) + " repo(s)"
    else:
        summary = "No changes" + (" would be made" if dry_run else " made")

    # Format output
    lines = []
    if added_repos:
        lines.append(f"{'Would add' if dry_run else 'Added'}:")
        for repo in sorted(added_repos):
            lines.append(f"  {repo}")
    if updated_repos:
        lines.append(f"{'Would update' if dry_run else 'Updated'}:")
        for repo in sorted(updated_repos):
            lines.append(f"  {repo}")
    if removed_repos:
        lines.append(f"{'Would remove' if dry_run else 'Removed'}:")
        for repo in sorted(removed_repos):
            lines.append(f"  {repo}")
    if unchanged_repos:
        lines.append(f"Unchanged: {len(unchanged_repos)} repo(s)")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data={
            "added": added_repos,
            "added_count": len(added_repos),
            "updated": updated_repos,
            "updated_count": len(updated_repos),
            "removed": removed_repos if replace_mode else [],
            "removed_count": len(removed_repos) if replace_mode else 0,
            "unchanged_count": len(unchanged_repos),
            "mode": "replace" if replace_mode else "merge",
            "dry_run": dry_run,
            "raw_output": "\n".join(lines),
        },
        files_modified=(
            ["config/registry.json"] if not dry_run and (added_repos or updated_repos or removed_repos) else []
        ),
    )
