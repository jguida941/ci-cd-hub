"""Registry modification commands (single-repo operations)."""

from __future__ import annotations

import argparse
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.registry_service import (
    load_registry,
    save_registry,
    set_repo_override,
    set_repo_tier,
)
from cihub.types import CommandResult
from cihub.utils.paths import hub_root


def _wizard_add() -> CommandResult:
    """Interactive wizard for adding a repo to the registry.

    Sources available tiers from registry (CLI as source of truth).
    """
    try:
        import questionary

        from cihub.wizard.core import WizardCancelled, _check_cancelled
        from cihub.wizard.styles import get_style
    except ImportError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="questionary not installed (pip install questionary)",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode requires questionary",
                    "code": "CIHUB-REGISTRY-NO-QUESTIONARY",
                }
            ],
        )

    try:
        registry = load_registry()
        available_tiers = list(registry.get("tiers", {}).keys())
        existing_repos = list(registry.get("repos", {}).keys())

        # Prompt for repo name (key in registry)
        repo_name: str = _check_cancelled(
            questionary.text(
                "Repository name (registry key):",
                style=get_style(),
            ).ask(),
            "Repository name",
        )

        if not repo_name.strip():
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary="Repository name cannot be empty",
                problems=[
                    {
                        "severity": "error",
                        "message": "Repository name is required",
                        "code": "CIHUB-REGISTRY-EMPTY-NAME",
                    }
                ],
            )

        repo_name = repo_name.strip()
        if repo_name in existing_repos:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repo already exists: {repo_name}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repo '{repo_name}' already in registry. Use 'registry set' to modify.",
                        "code": "CIHUB-REGISTRY-EXISTS",
                    }
                ],
            )

        # Prompt for tier (select from available)
        tier: str = _check_cancelled(
            questionary.select(
                "Select tier:",
                choices=available_tiers or ["standard"],
                default="standard" if "standard" in available_tiers else None,
                style=get_style(),
            ).ask(),
            "Tier selection",
        )

        # Prompt for description (optional)
        description: str = _check_cancelled(
            questionary.text(
                "Description (optional):",
                default="",
                style=get_style(),
            ).ask(),
            "Description",
        )

        # Prompt for owner (optional)
        owner: str = _check_cancelled(
            questionary.text(
                "GitHub owner/org (optional):",
                default="",
                style=get_style(),
            ).ask(),
            "Owner",
        )

        # Prompt for repo name override if owner provided
        name_override: str = ""
        if owner.strip():
            name_override = _check_cancelled(
                questionary.text(
                    "GitHub repo name (optional, defaults to registry key):",
                    default=repo_name,
                    style=get_style(),
                ).ask(),
                "Repo name override",
            )

        # Prompt for language (optional but enables sync)
        language_choice: str = _check_cancelled(
            questionary.select(
                "Repository language (enables config sync):",
                choices=["(none)", "python", "java"],
                default="(none)",
                style=get_style(),
            ).ask(),
            "Language selection",
        )
        language = language_choice if language_choice != "(none)" else None

        # Build args namespace and call _cmd_add
        args = argparse.Namespace(
            repo=repo_name,
            tier=tier,
            description=description.strip() or None,
            owner=owner.strip() or None,
            name=name_override.strip() or None,
            language=language,
        )
        return _cmd_add(args)

    except WizardCancelled:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Wizard cancelled",
            data={"cancelled": True},
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
                problems=[
                    {
                        "severity": "error",
                        "message": str(exc),
                        "code": "CIHUB-REGISTRY-INVALID-TIER",
                    }
                ],
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
            problems=[
                {
                    "severity": "error",
                    "message": "Specify --tier or an override (--coverage, --mutation, --vulns-max)",
                    "code": "CIHUB-REGISTRY-NO-CHANGES",
                }
            ],
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


def _cmd_add(args: argparse.Namespace) -> CommandResult:
    """Add a new repo to the registry."""
    wizard = getattr(args, "wizard", False)
    json_mode = getattr(args, "json", False)

    # JSON-purity: reject --json with --wizard
    if json_mode and wizard:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--wizard is not supported with --json",
            problems=[
                {
                    "severity": "error",
                    "message": "Interactive mode (--wizard) cannot be used with --json output",
                    "code": "CIHUB-REGISTRY-WIZARD-JSON",
                }
            ],
        )

    # Wizard mode
    if wizard:
        return _wizard_add()

    repo_name = args.repo
    if not repo_name:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Repository name required (or use --wizard)",
            problems=[
                {
                    "severity": "error",
                    "message": "Repository name is required. Use --wizard for interactive mode.",
                    "code": "CIHUB-REGISTRY-NO-NAME",
                }
            ],
        )

    tier = args.tier
    description = args.description
    owner = getattr(args, "owner", None)
    name = getattr(args, "name", None) or repo_name  # Default to repo argument
    language = getattr(args, "language", None)

    registry = load_registry()

    # Check if repo already exists
    if repo_name in registry.get("repos", {}):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repo already exists: {repo_name}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repo '{repo_name}' already in registry. Use 'registry set' to modify.",
                    "code": "CIHUB-REGISTRY-EXISTS",
                }
            ],
        )

    # Validate tier
    if tier not in registry.get("tiers", {}):
        available = ", ".join(registry.get("tiers", {}).keys())
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown tier: {tier}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown tier '{tier}'. Available: {available}",
                    "code": "CIHUB-REGISTRY-INVALID-TIER",
                }
            ],
        )

    # Schema contract: owner/name are both-or-none (registry.schema.json dependencies)
    has_explicit_name = name != repo_name
    if has_explicit_name and not owner:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="--name requires --owner",
            problems=[
                {
                    "severity": "error",
                    "message": "--name requires --owner (schema enforces owner/name as both-or-none)",
                    "code": "CIHUB-REGISTRY-NAME-REQUIRES-OWNER",
                }
            ],
            suggestions=[{"message": "Add --owner <org> to specify the repository owner"}],
        )

    # Add repo
    repos = registry.setdefault("repos", {})
    entry: dict[str, Any] = {"tier": tier}
    if description:
        entry["description"] = description

    # Add language at top-level (legacy/back-compat; config.repo.language is canonical)
    # Normalization on save will drop this if it equals config.repo.language
    if language:
        entry["language"] = language

    # Add repo metadata to config.repo if owner or language is provided
    # This enables sync_to_configs to create valid YAML files when all required fields present
    # Note: name is only persisted when owner is also present (schema constraint)
    if owner or language:
        config_block: dict[str, Any] = {}
        repo_block: dict[str, Any] = {}
        if owner:
            repo_block["owner"] = owner
            repo_block["name"] = name  # Always include name when owner is present
        if language:
            repo_block["language"] = language
        if repo_block:
            config_block["repo"] = repo_block
        if config_block:
            entry["config"] = config_block

    repos[repo_name] = entry
    save_registry(registry)

    # Determine if sync can create config files
    can_sync = bool(owner and name and language)
    sync_hint = "" if can_sync else " (add --owner --language to enable sync)"

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Added {repo_name} to registry (tier: {tier}){sync_hint}",
        data={
            "repo": repo_name,
            "tier": tier,
            "description": description,
            "owner": owner,
            "name": name,
            "language": language,
            "can_sync": can_sync,
        },
        files_modified=["config/registry.json"],
    )


def _cmd_remove(args: argparse.Namespace) -> CommandResult:
    """Remove a repo from the registry."""
    repo_name = args.repo
    delete_config = getattr(args, "delete_config", False)
    skip_confirm = getattr(args, "yes", False)

    registry = load_registry()
    repos = registry.get("repos", {})

    # Check if repo exists
    if repo_name not in repos:
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

    # Get config file path (for optional deletion)
    config_file = hub_root() / "config" / "repos" / f"{repo_name}.yaml"
    config_exists = config_file.exists()

    # Interactive confirmation unless --yes
    if not skip_confirm:
        # Return a result indicating confirmation is needed
        # (In non-interactive/JSON mode, require --yes)
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Confirmation required to remove {repo_name}",
            problems=[
                {
                    "severity": "warning",
                    "message": f"Use --yes to confirm removal of '{repo_name}' from registry",
                    "code": "CIHUB-REGISTRY-CONFIRM-REQUIRED",
                }
            ],
            data={
                "repo": repo_name,
                "config_exists": config_exists,
                "would_delete_config": delete_config and config_exists,
            },
            suggestions=[
                {"message": f"Run: cihub registry remove {repo_name} --yes"},
            ]
            + (
                [{"message": f"Run: cihub registry remove {repo_name} --yes --delete-config"}]
                if config_exists and not delete_config
                else []
            ),
        )

    # Remove from registry
    del repos[repo_name]
    save_registry(registry)

    files_modified = ["config/registry.json"]
    config_deleted = False
    deleted_config_path: str | None = None

    # Optionally delete config file
    if delete_config and config_exists:
        deleted_config_path = str(config_file.relative_to(hub_root()))
        config_file.unlink()
        config_deleted = True

    summary_parts = [f"Removed {repo_name} from registry"]
    if config_deleted:
        summary_parts.append(f"deleted {deleted_config_path}")

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary="; ".join(summary_parts),
        data={
            "repo": repo_name,
            "config_deleted": config_deleted,
            "deleted_config_path": deleted_config_path,
        },
        files_modified=files_modified,
    )
