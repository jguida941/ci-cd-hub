"""Repo command implementation for repository management."""

from __future__ import annotations

import argparse
import copy
import re
import shutil
import subprocess
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.types import CommandResult

# Pattern for valid GitHub owner/repo names (alphanumeric, hyphens, underscores, dots)
_GITHUB_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _validate_github_name(name: str) -> bool:
    """Validate a GitHub owner or repo name to prevent command injection.

    GitHub names can only contain alphanumeric characters, hyphens, underscores, and dots.
    """
    return bool(_GITHUB_NAME_PATTERN.match(name)) and len(name) <= 100


def _get_gh_executable() -> str | None:
    """Get the full path to the gh CLI executable."""
    return shutil.which("gh")


def cmd_repo(args: argparse.Namespace) -> CommandResult:
    """Dispatch repo subcommands."""
    subcommand: str | None = getattr(args, "subcommand", None)

    handlers = {
        "list": _cmd_list,
        "show": _cmd_show,
        "update": _cmd_update,
        "migrate": _cmd_migrate,
        "clone": _cmd_clone,
        "verify-connectivity": _cmd_verify_connectivity,
    }

    handler = handlers.get(subcommand or "")
    if handler is None:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=f"Unknown repo subcommand: {subcommand}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Unknown subcommand '{subcommand}'",
                    "code": "CIHUB-REPO-UNKNOWN-SUBCOMMAND",
                }
            ],
        )

    return handler(args)


def _cmd_list(args: argparse.Namespace) -> CommandResult:
    """List repositories in the registry."""
    language = getattr(args, "language", None)
    tier_filter = getattr(args, "tier", None)
    with_overrides = getattr(args, "with_overrides", False)

    from cihub.services.registry_service import list_repos, load_registry

    registry = load_registry()
    repos = list_repos(registry)

    # Apply filters
    if language:
        repos = [r for r in repos if r.get("language") == language]
    if tier_filter:
        repos = [r for r in repos if r.get("tier") == tier_filter]
    if with_overrides:
        repos = [r for r in repos if r.get("has_threshold_overrides", False)]

    if not repos:
        filter_parts = []
        if language:
            filter_parts.append(f"language={language}")
        if tier_filter:
            filter_parts.append(f"tier={tier_filter}")
        if with_overrides:
            filter_parts.append("with-overrides")
        filter_str = f" (filters: {', '.join(filter_parts)})" if filter_parts else ""
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No repositories found{filter_str}",
            data={"repos": [], "count": 0},
        )

    # Summarize by tier and language
    tiers = set(r.get("tier", "unknown") for r in repos)
    languages = set(r.get("language") for r in repos if r.get("language"))

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Found {len(repos)} repo(s) across {len(tiers)} tier(s)",
        data={
            "repos": repos,
            "count": len(repos),
            "tiers": sorted(tiers),
            "languages": sorted(languages),
        },
    )


def _cmd_show(args: argparse.Namespace) -> CommandResult:
    """Show detailed repository information."""
    name = args.name
    effective = getattr(args, "effective", False)

    from cihub.services.registry_service import get_repo_config, load_registry

    registry = load_registry()
    repo_config = get_repo_config(registry, name)

    if repo_config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{name}' not found in registry",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{name}' not in registry",
                    "code": "CIHUB-REPO-NOT-FOUND",
                }
            ],
        )

    if effective:
        # Include effective thresholds in the output
        summary = f"Repository '{name}' (effective config)"
    else:
        summary = f"Repository '{name}'"

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data=repo_config,
    )


def _wizard_update() -> CommandResult:
    """Interactive wizard for updating repository metadata.

    Sources available repos and tiers from registry (CLI as source of truth).
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
                    "code": "CIHUB-REPO-NO-QUESTIONARY",
                }
            ],
        )

    try:
        from cihub.services.registry_service import get_repo_config, list_repos, load_registry

        registry = load_registry()
        repos = list_repos(registry)
        repo_names = sorted([r.get("name", r.get("repo", "unknown")) for r in repos])
        tier_names = sorted(registry.get("tiers", {}).keys())

        if not repo_names:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="No repositories in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": "Registry has no repos. Add repos first with 'registry add'.",
                        "code": "CIHUB-REPO-NO-REPOS",
                    }
                ],
            )

        # Select repository
        selected_repo: str = _check_cancelled(
            questionary.select(
                "Select repository to update:",
                choices=repo_names,
                style=get_style(),
            ).ask(),
            "Repository selection",
        )

        # Get current config
        repo_config = get_repo_config(registry, selected_repo)
        if repo_config is None:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Repository '{selected_repo}' not found",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Repository '{selected_repo}' not in registry",
                        "code": "CIHUB-REPO-NOT-FOUND",
                    }
                ],
            )

        config = repo_config.get("config", {})
        repo_block = config.get("repo", {})
        current_tier = repo_config.get("tier", "standard")
        current_desc = repo_config.get("description", "")
        current_owner = repo_block.get("owner", "")
        current_name = repo_block.get("name", "")
        current_branch = repo_block.get("default_branch", "main")
        current_lang = repo_block.get("language", "")
        current_dispatch = repo_block.get("dispatch_enabled", False)

        # Select fields to update (multi-select)
        field_choices = [
            questionary.Choice(title=f"Tier (current: {current_tier})", value="tier"),
            questionary.Choice(title=f"Description (current: {current_desc or '(none)'})", value="description"),
            questionary.Choice(title=f"Owner (current: {current_owner or '(none)'})", value="owner"),
            questionary.Choice(title=f"Repo name (current: {current_name or '(none)'})", value="repo_name"),
            questionary.Choice(title=f"Default branch (current: {current_branch})", value="default_branch"),
            questionary.Choice(title=f"Language (current: {current_lang or '(none)'})", value="language"),
            questionary.Choice(title=f"Dispatch enabled (current: {current_dispatch})", value="dispatch_enabled"),
        ]

        selected_fields: list[str] = _check_cancelled(
            questionary.checkbox(
                "Select fields to update:",
                choices=field_choices,
                style=get_style(),
            ).ask(),
            "Field selection",
        )

        if not selected_fields:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="No fields selected",
                data={"cancelled": True},
            )

        # Build args with selected fields
        args = argparse.Namespace(
            name=selected_repo,
            owner=None,
            repo_name=None,
            default_branch=None,
            language=None,
            tier=None,
            dispatch_enabled=None,
            description=None,
        )

        # Prompt for each selected field
        if "tier" in selected_fields:
            new_tier: str = _check_cancelled(
                questionary.select(
                    "Select new tier:",
                    choices=tier_names or ["standard"],
                    default=current_tier if current_tier in tier_names else None,
                    style=get_style(),
                ).ask(),
                "Tier selection",
            )
            args.tier = new_tier

        if "description" in selected_fields:
            new_desc: str = _check_cancelled(
                questionary.text(
                    "Enter description:",
                    default=current_desc,
                    style=get_style(),
                ).ask(),
                "Description input",
            )
            args.description = new_desc

        if "owner" in selected_fields:
            new_owner: str = _check_cancelled(
                questionary.text(
                    "Enter owner (GitHub org/user):",
                    default=current_owner,
                    style=get_style(),
                ).ask(),
                "Owner input",
            )
            args.owner = new_owner.strip() or None

        if "repo_name" in selected_fields:
            new_name: str = _check_cancelled(
                questionary.text(
                    "Enter repo name:",
                    default=current_name or selected_repo,
                    style=get_style(),
                ).ask(),
                "Repo name input",
            )
            args.repo_name = new_name.strip() or None

        if "default_branch" in selected_fields:
            new_branch: str = _check_cancelled(
                questionary.text(
                    "Enter default branch:",
                    default=current_branch,
                    style=get_style(),
                ).ask(),
                "Branch input",
            )
            args.default_branch = new_branch.strip() or None

        if "language" in selected_fields:
            new_lang: str = _check_cancelled(
                questionary.select(
                    "Select language:",
                    choices=["(none)", "python", "java"],
                    default=current_lang if current_lang in ["python", "java"] else "(none)",
                    style=get_style(),
                ).ask(),
                "Language selection",
            )
            args.language = new_lang if new_lang != "(none)" else None

        if "dispatch_enabled" in selected_fields:
            new_dispatch: bool = _check_cancelled(
                questionary.confirm(
                    "Enable dispatch?",
                    default=current_dispatch,
                    style=get_style(),
                ).ask(),
                "Dispatch selection",
            )
            args.dispatch_enabled = "true" if new_dispatch else "false"

        return _do_update(args)

    except WizardCancelled:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Wizard cancelled",
            data={"cancelled": True},
        )


def _cmd_update(args: argparse.Namespace) -> CommandResult:
    """Update repository metadata."""
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
                    "code": "CIHUB-REPO-WIZARD-JSON",
                }
            ],
        )

    # Wizard mode
    if wizard:
        return _wizard_update()

    return _do_update(args)


def _do_update(args: argparse.Namespace) -> CommandResult:
    """Internal update implementation (shared by CLI and wizard)."""
    name = args.name
    if not name:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Repository name required (or use --wizard)",
            problems=[
                {
                    "severity": "error",
                    "message": "Repository name is required. Use --wizard for interactive mode.",
                    "code": "CIHUB-REPO-NO-NAME",
                }
            ],
        )

    owner = getattr(args, "owner", None)
    repo_name = getattr(args, "repo_name", None)
    default_branch = getattr(args, "default_branch", None)
    language = getattr(args, "language", None)
    tier = getattr(args, "tier", None)
    dispatch_enabled = getattr(args, "dispatch_enabled", None)
    description = getattr(args, "description", None)

    from cihub.services.registry_service import (
        _get_registry_path,
        get_repo_config,
        load_registry,
        save_registry,
    )

    registry = load_registry()
    repo_config = get_repo_config(registry, name)

    if repo_config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{name}' not found in registry",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{name}' not in registry",
                    "code": "CIHUB-REPO-NOT-FOUND",
                }
            ],
        )

    changes = []
    repo_entry = registry["repos"][name]

    # Update tier (top-level)
    if tier:
        tiers = registry.get("tiers", {})
        if tier not in tiers:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Tier '{tier}' not found in registry",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Tier '{tier}' not in registry. Available: {', '.join(tiers.keys())}",
                        "code": "CIHUB-REPO-TIER-NOT-FOUND",
                    }
                ],
            )
        old_tier = repo_entry.get("tier", "standard")
        if old_tier != tier:
            repo_entry["tier"] = tier
            changes.append(f"tier: {old_tier} → {tier}")

    # Update description (top-level)
    if description is not None:
        old_desc = repo_entry.get("description", "")
        if old_desc != description:
            repo_entry["description"] = description
            changes.append(f"description: '{old_desc}' → '{description}'")

    # Ensure config block exists for metadata
    if "config" not in repo_entry:
        repo_entry["config"] = {}
    config = repo_entry["config"]

    # Ensure repo block exists
    if "repo" not in config:
        config["repo"] = {}
    repo_block = config["repo"]

    # Validate owner/name dependency: if setting one without the other already existing
    existing_owner = repo_block.get("owner")
    existing_name = repo_block.get("name")

    if owner is not None and repo_name is None and existing_name is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Cannot set owner without name",
            problems=[
                {
                    "severity": "error",
                    "message": "Setting --owner requires --repo-name (schema dependency: owner requires name)",
                    "code": "CIHUB-REPO-OWNER-NEEDS-NAME",
                }
            ],
        )

    if repo_name is not None and owner is None and existing_owner is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Cannot set repo name without owner",
            problems=[
                {
                    "severity": "error",
                    "message": "Setting --repo-name requires --owner (schema dependency: name requires owner)",
                    "code": "CIHUB-REPO-NAME-NEEDS-OWNER",
                }
            ],
        )

    # Update owner
    if owner is not None:
        old_owner = repo_block.get("owner", "")
        if old_owner != owner:
            repo_block["owner"] = owner
            changes.append(f"owner: '{old_owner}' → '{owner}'")

    # Update repo name
    if repo_name is not None:
        old_name = repo_block.get("name", "")
        if old_name != repo_name:
            repo_block["name"] = repo_name
            changes.append(f"repo.name: '{old_name}' → '{repo_name}'")

    # Update default_branch
    if default_branch is not None:
        old_branch = repo_block.get("default_branch", "main")
        if old_branch != default_branch:
            repo_block["default_branch"] = default_branch
            changes.append(f"default_branch: '{old_branch}' → '{default_branch}'")

    # Update language (in config.repo.language - canonical location)
    if language is not None:
        old_lang = repo_block.get("language", "")
        if old_lang != language:
            repo_block["language"] = language
            changes.append(f"language: '{old_lang}' → '{language}'")

    # Update dispatch_enabled
    if dispatch_enabled is not None:
        enabled = dispatch_enabled.lower() == "true"
        old_enabled = repo_block.get("dispatch_enabled", False)
        if old_enabled != enabled:
            repo_block["dispatch_enabled"] = enabled
            changes.append(f"dispatch_enabled: {old_enabled} → {enabled}")

    if not changes:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"No changes made to repository '{name}'",
            data={"name": name, "changes": []},
        )

    save_registry(registry)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Updated repository '{name}' ({len(changes)} change(s))",
        data={"name": name, "changes": changes},
        files_modified=[str(_get_registry_path())],
    )


def _cmd_migrate(args: argparse.Namespace) -> CommandResult:
    """Migrate/rename a repository entry."""
    source = args.source
    dest = args.dest
    delete_source = getattr(args, "delete_source", False)
    force = getattr(args, "force", False)

    from cihub.services.registry_service import (
        _get_registry_path,
        load_registry,
        save_registry,
    )

    registry = load_registry()
    repos = registry.get("repos", {})

    # Check source exists
    if source not in repos:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Source repository '{source}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{source}' not in registry",
                    "code": "CIHUB-REPO-NOT-FOUND",
                }
            ],
        )

    # Check dest doesn't exist (unless force)
    if dest in repos and not force:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Destination repository '{dest}' already exists (use --force)",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{dest}' already exists",
                    "code": "CIHUB-REPO-EXISTS",
                }
            ],
        )

    # Deep copy source to dest (always use deepcopy to avoid shared nested dicts)
    source_config = copy.deepcopy(repos[source])
    repos[dest] = source_config

    # Delete source if requested
    if delete_source:
        del repos[source]
        action = "renamed"
    else:
        action = "copied"

    save_registry(registry)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Repository '{source}' {action} to '{dest}'",
        data={
            "source": source,
            "dest": dest,
            "action": action,
            "source_deleted": delete_source,
        },
        files_modified=[str(_get_registry_path())],
    )


def _cmd_clone(args: argparse.Namespace) -> CommandResult:
    """Clone a repository configuration."""
    source = args.source
    dest = args.dest
    force = getattr(args, "force", False)

    from cihub.services.registry_service import (
        _get_registry_path,
        load_registry,
        save_registry,
    )

    registry = load_registry()
    repos = registry.get("repos", {})

    # Check source exists
    if source not in repos:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Source repository '{source}' not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{source}' not in registry",
                    "code": "CIHUB-REPO-NOT-FOUND",
                }
            ],
        )

    # Check dest doesn't exist (unless force)
    if dest in repos and not force:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Destination repository '{dest}' already exists (use --force)",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{dest}' already exists",
                    "code": "CIHUB-REPO-EXISTS",
                }
            ],
        )

    # Deep copy source to dest
    source_config = copy.deepcopy(repos[source])
    repos[dest] = source_config

    save_registry(registry)

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Cloned repository '{source}' to '{dest}'",
        data={"source": source, "dest": dest},
        files_modified=[str(_get_registry_path())],
    )


def _cmd_verify_connectivity(args: argparse.Namespace) -> CommandResult:
    """Verify GitHub connectivity for a repository."""
    name = args.name
    check_workflows = getattr(args, "check_workflows", False)

    from cihub.services.registry_service import get_repo_config, load_registry

    registry = load_registry()
    repo_config = get_repo_config(registry, name)

    if repo_config is None:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{name}' not found in registry",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repository '{name}' not in registry",
                    "code": "CIHUB-REPO-NOT-FOUND",
                }
            ],
        )

    # Get owner and repo name
    config = repo_config.get("config", {})
    repo_block = config.get("repo", {})
    owner = repo_block.get("owner")
    repo_name = repo_block.get("name", name)

    if not owner:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Repository '{name}' has no owner configured",
            problems=[
                {
                    "severity": "error",
                    "message": "Cannot verify connectivity without owner. Use 'repo update --owner'",
                    "code": "CIHUB-REPO-NO-OWNER",
                }
            ],
        )

    # Validate owner and repo_name to prevent command injection
    if not _validate_github_name(owner):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid owner name: {owner}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Owner '{owner}' contains invalid characters",
                    "code": "CIHUB-REPO-INVALID-OWNER",
                }
            ],
        )
    if not _validate_github_name(repo_name):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Invalid repo name: {repo_name}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Repo name '{repo_name}' contains invalid characters",
                    "code": "CIHUB-REPO-INVALID-NAME",
                }
            ],
        )

    # Get full path to gh CLI
    gh_path = _get_gh_executable()
    if not gh_path:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="GitHub CLI (gh) not found",
            problems=[
                {
                    "severity": "error",
                    "message": "Install GitHub CLI: https://cli.github.com/",
                    "code": "CIHUB-REPO-NO-GH-CLI",
                }
            ],
        )

    # Use gh CLI to verify repo exists
    full_repo = f"{owner}/{repo_name}"
    checks: list[dict[str, Any]] = []

    # Check repo exists (inputs validated above, using full executable path)
    try:
        result = subprocess.run(  # noqa: S603 - inputs validated by _validate_github_name
            [gh_path, "repo", "view", full_repo, "--json", "name,owner"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            checks.append(
                {
                    "check": "repo_exists",
                    "status": "pass",
                    "message": f"Repository {full_repo} exists",
                }
            )
        else:
            checks.append(
                {
                    "check": "repo_exists",
                    "status": "fail",
                    "message": f"Repository {full_repo} not found or not accessible",
                    "error": result.stderr.strip(),
                }
            )
    except subprocess.TimeoutExpired:
        checks.append(
            {
                "check": "repo_exists",
                "status": "fail",
                "message": "Timeout checking repository",
            }
        )

    # Check workflows if requested (inputs validated above, using full executable path)
    if check_workflows and checks[0]["status"] == "pass":
        try:
            result = subprocess.run(  # noqa: S603 - inputs validated by _validate_github_name
                [gh_path, "api", f"repos/{full_repo}/contents/.github/workflows"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                import json

                workflows = json.loads(result.stdout)
                workflow_names = [w["name"] for w in workflows if w["name"].endswith(".yml")]
                checks.append(
                    {
                        "check": "workflows_exist",
                        "status": "pass",
                        "message": f"Found {len(workflow_names)} workflow file(s)",
                        "workflows": workflow_names,
                    }
                )
            else:
                checks.append(
                    {
                        "check": "workflows_exist",
                        "status": "warn",
                        "message": "No .github/workflows directory found",
                    }
                )
        except Exception as e:
            checks.append(
                {
                    "check": "workflows_exist",
                    "status": "fail",
                    "message": f"Error checking workflows: {e}",
                }
            )

    # Determine overall status
    failed = [c for c in checks if c["status"] == "fail"]
    warnings = [c for c in checks if c["status"] == "warn"]

    if failed:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Connectivity check failed for '{name}'",
            data={"name": name, "repo": full_repo, "checks": checks},
            problems=[
                {
                    "severity": "error",
                    "message": c["message"],
                    "code": "CIHUB-REPO-CONNECTIVITY-FAIL",
                }
                for c in failed
            ],
        )

    if warnings:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Connectivity check passed with warnings for '{name}'",
            data={"name": name, "repo": full_repo, "checks": checks},
            problems=[
                {
                    "severity": "warning",
                    "message": c["message"],
                    "code": "CIHUB-REPO-CONNECTIVITY-WARN",
                }
                for c in warnings
            ],
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS,
        summary=f"Connectivity check passed for '{name}' ({full_repo})",
        data={"name": name, "repo": full_repo, "checks": checks},
    )
