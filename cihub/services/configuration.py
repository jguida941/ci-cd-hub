"""Config service helpers for GUI/programmatic access."""

from __future__ import annotations

import io
from contextlib import redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.config.loader import ConfigValidationError, load_config
from cihub.services.types import ServiceResult
from cihub.utils.paths import hub_root


@dataclass
class ConfigLoadResult(ServiceResult):
    """Result of loading a repo config from the hub."""

    config: dict[str, Any] = field(default_factory=dict)


def load_repo_config(
    repo_name: str,
    hub_root: Path,
    repo_config_path: Path | None = None,
) -> ConfigLoadResult:
    """Load a repo config with validation and captured warnings."""
    stderr_capture = io.StringIO()
    warnings: list[str] = []

    try:
        with redirect_stderr(stderr_capture):
            cfg = load_config(
                repo_name=repo_name,
                hub_root=hub_root,
                repo_config_path=repo_config_path,
                exit_on_validation_error=False,
            )
    except ConfigValidationError as exc:
        errors = [f"{repo_name}: validation failed ({exc})"]
        stderr_output = stderr_capture.getvalue().strip()
        if stderr_output:
            errors.extend(f"{repo_name}: {line}" for line in stderr_output.splitlines())
        return ConfigLoadResult(success=False, errors=errors, warnings=warnings)
    except Exception as exc:
        errors = [f"{repo_name}: failed to load ({exc})"]
        stderr_output = stderr_capture.getvalue().strip()
        if stderr_output:
            errors.extend(f"{repo_name}: {line}" for line in stderr_output.splitlines())
        return ConfigLoadResult(success=False, errors=errors, warnings=warnings)

    stderr_output = stderr_capture.getvalue().strip()
    if stderr_output:
        warnings.extend(f"{repo_name}: {line}" for line in stderr_output.splitlines())

    return ConfigLoadResult(success=True, warnings=warnings, config=cfg)


def load_effective_config(repo_path: Path) -> dict[str, Any]:
    """Load defaults + repo .ci-hub.yml with schema validation."""
    config = load_config(
        repo_name=repo_path.name,
        hub_root=hub_root(),
        repo_config_path=repo_path / ".ci-hub.yml",
        exit_on_validation_error=False,
    )
    config.pop("_meta", None)
    return config


def set_nested_value(config: dict[str, Any], path: str, value: Any) -> None:
    """Set a nested config value using dot-delimited path."""
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ValueError("Empty path")
    cursor = config
    for key in parts[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[parts[-1]] = value


def resolve_tool_path(
    config: dict[str, Any],
    defaults: dict[str, Any],
    tool: str,
) -> str:
    """Resolve tool path for enable/disable operations."""
    language = None
    repo_block = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    if repo_block.get("language"):
        language = repo_block.get("language")
    elif config.get("language"):
        language = config.get("language")

    java_tools = defaults.get("java", {}).get("tools", {}) or {}
    python_tools = defaults.get("python", {}).get("tools", {}) or {}

    if language == "java":
        if tool not in java_tools:
            raise ValueError(f"Unknown tool: {tool}")
        return f"java.tools.{tool}.enabled"
    if language == "python":
        if tool not in python_tools:
            raise ValueError(f"Unknown tool: {tool}")
        return f"python.tools.{tool}.enabled"

    java_has = tool in java_tools
    python_has = tool in python_tools
    if java_has and not python_has:
        return f"java.tools.{tool}.enabled"
    if python_has and not java_has:
        return f"python.tools.{tool}.enabled"
    if java_has and python_has:
        raise ValueError("Tool exists in both java and python; set repo.language first")
    raise ValueError(f"Unknown tool: {tool}")


def set_tool_enabled(
    config: dict[str, Any],
    defaults: dict[str, Any],
    tool: str,
    enabled: bool,
) -> str:
    """Enable/disable a tool and return the resolved path."""
    tool_path = resolve_tool_path(config, defaults, tool)
    set_nested_value(config, tool_path, enabled)
    return tool_path


# ---------------------------------------------------------------------------
# Registry-Integrated Configuration Management
# ---------------------------------------------------------------------------
# These functions provide the shared service layer for wizard and CLI commands.
# Instead of writing directly to config/repos/*.yaml, they route through the
# registry to maintain registry as the source of truth.
# ---------------------------------------------------------------------------


@dataclass
class CreateRepoResult(ServiceResult):
    """Result of creating a repo through the registry."""

    repo_name: str = ""
    registry_entry: dict[str, Any] = field(default_factory=dict)
    config_file_path: str = ""
    synced: bool = False


def extract_registry_entry_from_config(
    config: dict[str, Any],
    *,
    tier: str = "standard",
    hub_root_path: Path | None = None,
) -> dict[str, Any]:
    """Extract a registry entry from a full wizard/CLI config dict.

    This extracts:
    - tier (from parameter, defaults to "standard")
    - language (from repo.language or top-level)
    - description (from repo.description)
    - managed config fragments (gates, reports, notifications, harden_runner, etc.)
    - threshold overrides (sparse - only non-default values)

    Args:
        config: Full config dict from wizard or CLI
        tier: Tier to assign (strict/standard/relaxed)
        hub_root_path: Optional hub root for loading defaults

    Returns:
        Registry entry dict suitable for repos.<name>
    """
    from cihub.config.io import load_defaults
    from cihub.config.paths import PathConfig
    from cihub.services.registry_service import (
        _get_managed_config_top_level_keys,
        load_registry,
    )

    root = hub_root_path or hub_root()
    paths = PathConfig(str(root))

    entry: dict[str, Any] = {"tier": tier}

    # Extract language
    repo_block = config.get("repo", {})
    if isinstance(repo_block, dict):
        lang = repo_block.get("language")
        if lang:
            entry["language"] = lang
        desc = repo_block.get("description")
        if desc:
            entry["description"] = desc
    if "language" not in entry and config.get("language"):
        entry["language"] = config["language"]

    # Extract managed config fragments (excluding thresholds and language)
    managed_keys = _get_managed_config_top_level_keys(hub_root_path=root)
    managed_keys.discard("thresholds")
    managed_keys.discard("language")

    config_fragment: dict[str, Any] = {}
    for key in sorted(managed_keys):
        if key in config and config[key]:
            val = config[key]
            # Skip empty dicts/lists
            if isinstance(val, (dict, list)) and not val:
                continue
            config_fragment[key] = val

    if config_fragment:
        entry["config"] = config_fragment

    # Extract threshold overrides (sparse - only values differing from tier defaults)
    config_thresholds = config.get("thresholds", {})
    if isinstance(config_thresholds, dict) and config_thresholds:
        from cihub.config.io import load_profile
        from cihub.services.registry_service import _DEFAULT_THRESHOLDS

        # Load tier defaults to compare against
        registry = load_registry(registry_path=root / "config" / "registry.json")
        tiers = registry.get("tiers", {})
        tier_cfg = tiers.get(tier, {}) if isinstance(tiers, dict) else {}

        # Build tier threshold defaults from: global defaults → tier profile → tier config
        defaults_cfg = load_defaults(paths)
        tier_thresholds: dict[str, Any] = {}

        # Start with global defaults
        global_defaults = defaults_cfg.get("thresholds", {})
        if isinstance(global_defaults, dict):
            tier_thresholds.update(global_defaults)

        # Apply tier profile thresholds (e.g., tier-strict.yaml)
        if isinstance(tier_cfg, dict):
            profile_name = tier_cfg.get("profile")
            if isinstance(profile_name, str) and profile_name:
                profile_cfg = load_profile(paths, profile_name)
                if isinstance(profile_cfg, dict):
                    profile_thresholds = profile_cfg.get("thresholds", {})
                    if isinstance(profile_thresholds, dict):
                        tier_thresholds.update(profile_thresholds)

            # Apply tier config fragment thresholds
            tier_fragment = tier_cfg.get("config", {})
            if isinstance(tier_fragment, dict):
                frag_thresholds = tier_fragment.get("thresholds", {})
                if isinstance(frag_thresholds, dict):
                    tier_thresholds.update(frag_thresholds)

            # Also check tier-level threshold fields
            for key in _DEFAULT_THRESHOLDS:
                if key in tier_cfg:
                    tier_thresholds[key] = tier_cfg[key]

        # Only store overrides that differ from tier defaults
        overrides: dict[str, Any] = {}
        for key in _DEFAULT_THRESHOLDS:
            if key in config_thresholds:
                config_val = config_thresholds[key]
                tier_val = tier_thresholds.get(key)
                if config_val != tier_val:
                    overrides[key] = config_val

        if overrides:
            entry["overrides"] = overrides

    return entry


def create_repo_via_registry(
    repo_name: str,
    config: dict[str, Any],
    *,
    tier: str = "standard",
    sync: bool = True,
    dry_run: bool = False,
    hub_root_path: Path | None = None,
) -> CreateRepoResult:
    """Create a new repo by adding to registry and syncing to config/repos.

    This is the shared service layer for wizard and CLI commands.
    Instead of writing directly to config/repos/*.yaml, it:
    1. Extracts registry entry from config
    2. Adds to registry.json
    3. Syncs to config/repos/*.yaml (unless dry_run)

    Args:
        repo_name: Name of the repo (becomes registry key and config file name)
        config: Full config dict from wizard or CLI
        tier: Tier to assign (strict/standard/relaxed)
        sync: Whether to sync to config/repos after registry update
        dry_run: If True, don't write any files
        hub_root_path: Optional hub root path

    Returns:
        CreateRepoResult with registry entry and sync status
    """
    from cihub.services.registry_service import (
        load_registry,
        save_registry,
        sync_to_configs,
    )

    root = hub_root_path or hub_root()
    registry_path = root / "config" / "registry.json"
    configs_dir = root / "config" / "repos"

    # Check if repo already exists
    registry = load_registry(registry_path=registry_path)
    repos = registry.get("repos", {})
    if not isinstance(repos, dict):
        repos = {}
        registry["repos"] = repos

    if repo_name in repos:
        return CreateRepoResult(
            success=False,
            errors=[f"Repo '{repo_name}' already exists in registry"],
            repo_name=repo_name,
        )

    # Extract registry entry from config
    entry = extract_registry_entry_from_config(config, tier=tier, hub_root_path=root)

    if dry_run:
        return CreateRepoResult(
            success=True,
            repo_name=repo_name,
            registry_entry=entry,
            config_file_path=str(configs_dir / f"{repo_name}.yaml"),
            synced=False,
        )

    # Add to registry
    repos[repo_name] = entry
    save_registry(registry, registry_path=registry_path)

    # Sync to config/repos
    synced = False
    config_file_path = str(configs_dir / f"{repo_name}.yaml")
    if sync:
        # sync_to_configs returns list of changes, not dict
        changes = sync_to_configs(
            registry,
            configs_dir,
            dry_run=False,
            hub_root_path=root,
        )
        # Only count as synced if action was create/update (not skip)
        synced = repo_name in [c.get("repo") for c in changes if c.get("action") != "skip"]
        if not synced:
            # Sync may not report change if config matches
            synced = (configs_dir / f"{repo_name}.yaml").exists()

    return CreateRepoResult(
        success=True,
        repo_name=repo_name,
        registry_entry=entry,
        config_file_path=config_file_path,
        synced=synced,
    )


def update_repo_via_registry(
    repo_name: str,
    config: dict[str, Any],
    *,
    tier: str | None = None,
    sync: bool = True,
    dry_run: bool = False,
    hub_root_path: Path | None = None,
) -> CreateRepoResult:
    """Update an existing repo by modifying registry and syncing.

    Args:
        repo_name: Name of the repo to update
        config: New config dict from wizard or CLI
        tier: New tier (if None, keeps existing)
        sync: Whether to sync to config/repos after registry update
        dry_run: If True, don't write any files
        hub_root_path: Optional hub root path

    Returns:
        CreateRepoResult with updated registry entry and sync status
    """
    from cihub.services.registry_service import (
        load_registry,
        save_registry,
        sync_to_configs,
    )

    root = hub_root_path or hub_root()
    registry_path = root / "config" / "registry.json"
    configs_dir = root / "config" / "repos"

    # Load existing registry
    registry = load_registry(registry_path=registry_path)
    repos = registry.get("repos", {})
    if not isinstance(repos, dict):
        repos = {}
        registry["repos"] = repos

    if repo_name not in repos:
        return CreateRepoResult(
            success=False,
            errors=[f"Repo '{repo_name}' not found in registry"],
            repo_name=repo_name,
        )

    # Get existing tier if not specified
    existing = repos[repo_name]
    if tier is None:
        tier = existing.get("tier", "standard") if isinstance(existing, dict) else "standard"

    # Extract new registry entry from config
    entry = extract_registry_entry_from_config(config, tier=tier, hub_root_path=root)

    if dry_run:
        return CreateRepoResult(
            success=True,
            repo_name=repo_name,
            registry_entry=entry,
            config_file_path=str(configs_dir / f"{repo_name}.yaml"),
            synced=False,
        )

    # Update registry
    repos[repo_name] = entry
    save_registry(registry, registry_path=registry_path)

    # Sync to config/repos
    synced = False
    config_file_path = str(configs_dir / f"{repo_name}.yaml")
    if sync:
        changes = sync_to_configs(
            registry,
            configs_dir,
            dry_run=False,
            hub_root_path=root,
        )
        # Only count as synced if action was create/update (not skip)
        synced = repo_name in [c.get("repo") for c in changes if c.get("action") != "skip"]
        if not synced:
            # Sync may not report change if config already matches
            synced = (configs_dir / f"{repo_name}.yaml").exists()

    return CreateRepoResult(
        success=True,
        repo_name=repo_name,
        registry_entry=entry,
        config_file_path=config_file_path,
        synced=synced,
    )
