"""Sync operations between registry and config files.

Handles syncing registry settings to repo config files and bootstrapping from existing configs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cihub.services.registry import _paths as _registry_paths
from cihub.services.registry.diff import (
    _diff_objects,
    _get_managed_config_top_level_keys,
    _merge_config_layers,
    _normalize_config_fragment,
)
from cihub.services.registry.io import load_registry, save_registry
from cihub.services.registry.query import list_repos
from cihub.services.registry.thresholds import (
    _DEFAULT_THRESHOLDS,
    _normalize_threshold_dict_inplace,
)


def sync_to_configs(
    registry: dict[str, Any],
    configs_dir: Path,
    *,
    dry_run: bool = True,
    hub_root_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Sync registry settings to repo config files.

    Args:
        registry: Registry dict
        configs_dir: Path to config/repos/ directory
        dry_run: If True, report what would change without modifying files

    Returns:
        List of changes (applied or would-be-applied)
    """
    import copy

    import yaml  # Only needed for write

    from cihub.config.io import load_yaml_file

    changes = []
    repos_info = list_repos(registry, hub_root_path=hub_root_path)
    tiers = registry.get("tiers", {})
    repos = registry.get("repos", {})
    if not isinstance(tiers, dict):
        tiers = {}
    if not isinstance(repos, dict):
        repos = {}

    tier_fragments: dict[str, dict[str, Any]] = {}
    from cihub.config.io import load_profile
    from cihub.config.paths import PathConfig

    paths = PathConfig(str(hub_root_path or _registry_paths.get_hub_root()))
    for tier_name, tier_cfg in tiers.items():
        if isinstance(tier_cfg, dict):
            profile_cfg: dict[str, Any] = {}
            profile_name = tier_cfg.get("profile")
            if isinstance(profile_name, str) and profile_name:
                profile_cfg = _normalize_config_fragment(load_profile(paths, profile_name))
            tier_cfg_fragment = _normalize_config_fragment(tier_cfg.get("config"))
            tier_fragments[tier_name] = _merge_config_layers([profile_cfg, tier_cfg_fragment])

    for repo_info in repos_info:
        repo_name = repo_info["name"]
        effective = repo_info["effective"]
        tier_name = repo_info["tier"]

        config_path = configs_dir / f"{repo_name}.yaml"
        is_new_file = not config_path.exists()

        if is_new_file:
            # Guard: Only create new configs if registry has essential fields
            # (repo.owner, repo.name, language) to produce a schema-valid config
            # Note: language can be at top-level OR in config.repo.language (canonical after normalization)
            repo_cfg = repos.get(repo_name, {})
            if not isinstance(repo_cfg, dict):
                repo_cfg = {}
            # Defensive: config may be null in malformed entries
            config_block = repo_cfg.get("config")
            if not isinstance(config_block, dict):
                config_block = {}
            repo_block = config_block.get("repo")
            if not isinstance(repo_block, dict):
                repo_block = {}
            has_owner = bool(repo_block.get("owner"))
            has_name = bool(repo_block.get("name"))
            # Check both top-level language and config.repo.language (canonical location)
            top_level_lang = repo_cfg.get("language")
            repo_lang = repo_block.get("language")
            has_language = bool(top_level_lang or repo_lang)

            if not (has_owner and has_name and has_language):
                missing = []
                if not has_owner:
                    missing.append("repo.owner")
                if not has_name:
                    missing.append("repo.name")
                if not has_language:
                    missing.append("language")
                changes.append(
                    {
                        "repo": repo_name,
                        "action": "skip",
                        "reason": f"missing required fields: {', '.join(missing)}",
                    }
                )
                continue

            # Start with an empty config that will be populated from registry
            config = {}
            before_config = {}
        else:
            try:
                config = load_yaml_file(config_path)
            except Exception as exc:  # noqa: BLE001
                changes.append(
                    {
                        "repo": repo_name,
                        "action": "skip",
                        "reason": f"failed to load: {exc}",
                    }
                )
                continue
            before_config = copy.deepcopy(config)

        # Apply tier/repo config fragments (sparse managedConfig).
        repo_cfg = repos.get(repo_name)
        repo_fragment: dict[str, Any] = {}
        if isinstance(repo_cfg, dict):
            repo_fragment = _normalize_config_fragment(repo_cfg.get("config"))
        tier_fragment = tier_fragments.get(tier_name, {})
        merged_fragment = _merge_config_layers([tier_fragment, repo_fragment])
        if merged_fragment:
            # IMPORTANT: Do NOT normalize the entire config file here.
            # Registry sync must be allowlist-driven; normalizing the full config can
            # rewrite unrelated/unmanaged keys (e.g., tool booleans -> objects).
            from cihub.config.merge import deep_merge

            config = deep_merge(config, merged_fragment)

        # Update thresholds - sync ALL threshold fields from effective config
        thresholds = config.setdefault("thresholds", {})
        if not isinstance(thresholds, dict):
            thresholds = {}
            config["thresholds"] = thresholds

        # Clean up legacy (schema-incompatible) keys if they exist.
        # Note: Both "mutation" and "mutation_score" are legacy aliases for "mutation_score_min"
        for legacy_key in ("coverage", "mutation", "mutation_score", "vulns_max"):
            if legacy_key in thresholds:
                thresholds.pop(legacy_key, None)

        # Sync all threshold fields from registry-computed effective values
        for key, default_val in _DEFAULT_THRESHOLDS.items():
            if thresholds.get(key, default_val) != effective[key]:
                thresholds[key] = effective[key]

        # Ensure language is set consistently (both top-level and repo.language)
        # For new files, language may come from registry top-level or config.repo.language
        repo_block = config.get("repo")
        if not isinstance(repo_block, dict):
            repo_block = {}
            config["repo"] = repo_block

        # Get language from repo.language or registry top-level
        repo_cfg = repos.get(repo_name)
        registry_lang = repo_cfg.get("language") if isinstance(repo_cfg, dict) else None
        repo_lang = repo_block.get("language")
        effective_lang = repo_lang or registry_lang

        if effective_lang:
            # Set both top-level and repo.language for consistency
            config["language"] = effective_lang
            if not repo_lang:
                repo_block["language"] = effective_lang

        repo_changes = _diff_objects(before_config, config, prefix="")

        if not repo_changes and not is_new_file:
            changes.append(
                {
                    "repo": repo_name,
                    "action": "unchanged",
                    "reason": "already in sync",
                }
            )
            continue

        if not dry_run:
            # Ensure parent directory exists for new files
            if is_new_file:
                config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Distinguish "created" from "updated"
        if is_new_file:
            action = "created" if not dry_run else "would_create"
        else:
            action = "updated" if not dry_run else "would_update"

        changes.append(
            {
                "repo": repo_name,
                "action": action,
                "fields": repo_changes,
            }
        )

    return changes


def bootstrap_from_configs(
    configs_dir: Path,
    *,
    default_tier: str = "standard",
    strategy: str = "merge",
    dry_run: bool = True,
    include_thresholds: bool = False,
    hub_root_path: Path | None = None,
) -> dict[str, Any]:
    """Import existing config/repos/*.yaml files into the registry.

    Args:
        configs_dir: Path to config/repos/ directory
        default_tier: Default tier for imported repos
        strategy: Conflict strategy (merge, replace, prefer-registry, prefer-config)
        dry_run: If True, report what would change without modifying registry
        include_thresholds: If True, import threshold values as overrides
        hub_root_path: Optional hub root path for loading registry

    Returns:
        Dict with:
        - imported: list of repo names imported
        - skipped: list of {repo, reason} for skipped repos
        - conflicts: list of {repo, field, registry_value, config_value} conflicts
        - dry_run: bool
    """
    from cihub.config.io import load_yaml_file

    root = hub_root_path or _registry_paths.get_hub_root()
    registry = load_registry(registry_path=root / "config" / "registry.json")

    repos = registry.setdefault("repos", {})
    tiers = registry.get("tiers", {})
    if not isinstance(repos, dict):
        repos = {}
        registry["repos"] = repos
    if not isinstance(tiers, dict):
        tiers = {}

    managed_fragment_keys = _get_managed_config_top_level_keys(hub_root_path=hub_root_path)
    managed_fragment_keys.discard("thresholds")
    managed_fragment_keys.discard("language")

    tier_threshold_defaults: dict[str, dict[str, Any]] = {}
    if include_thresholds and isinstance(tiers, dict):
        from cihub.config.io import load_profile
        from cihub.config.paths import PathConfig

        paths = PathConfig(str(hub_root_path or _registry_paths.get_hub_root()))
        for tier_name, tier_cfg in tiers.items():
            if not isinstance(tier_cfg, dict):
                continue
            profile_cfg: dict[str, Any] = {}
            profile_name = tier_cfg.get("profile")
            if isinstance(profile_name, str) and profile_name:
                profile_cfg = _normalize_config_fragment(load_profile(paths, profile_name))
            tier_fragment = _normalize_config_fragment(tier_cfg.get("config"))
            defaults_for_tier: dict[str, Any] = {}
            if isinstance(profile_cfg.get("thresholds"), dict):
                defaults_for_tier.update(profile_cfg["thresholds"])
            if isinstance(tier_fragment.get("thresholds"), dict):
                defaults_for_tier.update(tier_fragment["thresholds"])
            for key in _DEFAULT_THRESHOLDS:
                if key in tier_cfg:
                    defaults_for_tier[key] = tier_cfg.get(key)
            tier_threshold_defaults[tier_name] = defaults_for_tier

    # Validate default tier exists
    if default_tier not in tiers:
        return {
            "imported": [],
            "skipped": [],
            "conflicts": [],
            "error": f"Tier '{default_tier}' not found in registry. Available: {list(tiers.keys())}",
            "dry_run": dry_run,
        }

    imported: list[str] = []
    skipped: list[dict[str, str]] = []
    conflicts: list[dict[str, Any]] = []

    def _should_include_fragment_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return True
        if isinstance(value, (dict, list, tuple, set, str)):
            return bool(value)
        return True

    def _collect_fragment_conflicts(
        repo_name: str,
        existing_fragment: dict[str, Any],
        incoming_fragment: dict[str, Any],
        *,
        prefix: str,
    ) -> list[dict[str, Any]]:
        fragment_conflicts: list[dict[str, Any]] = []
        for key, incoming_val in incoming_fragment.items():
            if key not in existing_fragment:
                continue
            existing_val = existing_fragment.get(key)
            if isinstance(existing_val, dict) and isinstance(incoming_val, dict):
                for sub_key, sub_val in incoming_val.items():
                    if sub_key not in existing_val:
                        continue
                    existing_sub = existing_val.get(sub_key)
                    if existing_sub != sub_val:
                        fragment_conflicts.append(
                            {
                                "repo": repo_name,
                                "field": f"{prefix}{key}.{sub_key}",
                                "registry_value": existing_sub,
                                "config_value": sub_val,
                                "resolution": "kept registry value",
                            }
                        )
            elif existing_val != incoming_val:
                fragment_conflicts.append(
                    {
                        "repo": repo_name,
                        "field": f"{prefix}{key}",
                        "registry_value": existing_val,
                        "config_value": incoming_val,
                        "resolution": "kept registry value",
                    }
                )
        return fragment_conflicts

    for config_path in sorted(configs_dir.rglob("*.yaml")):
        try:
            rel = config_path.relative_to(configs_dir)
            repo_name = rel.with_suffix("").as_posix()
        except Exception:  # noqa: BLE001
            repo_name = config_path.stem

        # Load config file
        try:
            config = load_yaml_file(config_path)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"repo": repo_name, "reason": f"failed to load: {exc}"})
            continue

        if not isinstance(config, dict):
            skipped.append({"repo": repo_name, "reason": "not a valid YAML dict"})
            continue

        repo_block = config.get("repo", {})
        repo_lang = None
        if isinstance(repo_block, dict):
            repo_lang = repo_block.get("language")
        config_lang = repo_lang or config.get("language")

        config_fragment: dict[str, Any] = {}
        for key in sorted(managed_fragment_keys):
            if key not in config:
                continue
            value = config[key]
            if _should_include_fragment_value(value):
                config_fragment[key] = value
        config_fragment = _normalize_config_fragment(config_fragment)

        # Check if already in registry
        existing = repos.get(repo_name)
        if existing is not None:
            if strategy == "replace":
                # Replace entirely - use config's implied tier (default_tier)
                default_tier_for_repo = default_tier
                existing = {}  # Clear existing to replace entirely
            elif strategy == "prefer-registry":
                # Skip - keep existing
                skipped.append({"repo": repo_name, "reason": "already in registry (prefer-registry)"})
                continue
            elif strategy == "prefer-config":
                # Replace with config values but use existing tier if present
                if isinstance(existing, dict) and existing.get("tier"):
                    default_tier_for_repo = existing["tier"]
                else:
                    default_tier_for_repo = default_tier
                existing = {}  # Clear to rebuild from config
            else:  # merge (default)
                # Detect conflicts and merge
                if isinstance(existing, dict):
                    existing_tier = existing.get("tier")
                    if existing_tier and existing_tier != default_tier:
                        conflicts.append(
                            {
                                "repo": repo_name,
                                "field": "tier",
                                "registry_value": existing_tier,
                                "config_value": default_tier,
                                "resolution": "kept registry value",
                            }
                        )
                        # Keep existing tier when merging
                        default_tier_for_repo = existing_tier
                    else:
                        default_tier_for_repo = default_tier

                    # Detect language conflicts (legacy top-level vs config)
                    existing_lang = existing.get("language")
                    if not existing_lang and isinstance(existing.get("config"), dict):
                        existing_repo = existing["config"].get("repo")
                        if isinstance(existing_repo, dict):
                            existing_lang = existing_repo.get("language")
                    if existing_lang and config_lang and existing_lang != config_lang:
                        conflicts.append(
                            {
                                "repo": repo_name,
                                "field": "language",
                                "registry_value": existing_lang,
                                "config_value": config_lang,
                                "resolution": "kept registry value",
                            }
                        )

                    if config_fragment:
                        existing_fragment = _normalize_config_fragment(existing.get("config"))
                        conflicts.extend(
                            _collect_fragment_conflicts(
                                repo_name,
                                existing_fragment,
                                config_fragment,
                                prefix="config.",
                            )
                        )

                    # Detect override conflicts (if both have overrides)
                    existing_overrides = existing.get("overrides", {})
                    config_thresholds_check = config.get("thresholds", {})
                    if isinstance(existing_overrides, dict) and isinstance(config_thresholds_check, dict):
                        config_thresholds_check = dict(config_thresholds_check)
                        _normalize_threshold_dict_inplace(config_thresholds_check)
                        for key in existing_overrides:
                            if key in config_thresholds_check:
                                existing_val = existing_overrides[key]
                                config_val = config_thresholds_check[key]
                                if existing_val != config_val:
                                    conflicts.append(
                                        {
                                            "repo": repo_name,
                                            "field": f"overrides.{key}",
                                            "registry_value": existing_val,
                                            "config_value": config_val,
                                            "resolution": "kept registry value",
                                        }
                                    )
                else:
                    default_tier_for_repo = default_tier
        else:
            default_tier_for_repo = default_tier
            existing = {}

        # Build new registry entry
        new_entry: dict[str, Any] = {"tier": default_tier_for_repo}

        # Extract language from config
        if config_lang and not repo_lang:
            new_entry["language"] = config_lang

        # Extract description
        if isinstance(repo_block, dict) and repo_block.get("description"):
            new_entry["description"] = repo_block["description"]

        if config_fragment:
            new_entry["config"] = config_fragment

        # Optionally import thresholds as overrides (sparse - only non-default values)
        if include_thresholds:
            config_thresholds = config.get("thresholds", {})
            if isinstance(config_thresholds, dict):
                config_thresholds = dict(config_thresholds)
                _normalize_threshold_dict_inplace(config_thresholds)

                # Get tier defaults to compare against (sparse storage)
                tier_thresholds = tier_threshold_defaults.get(default_tier_for_repo, {})

                overrides: dict[str, Any] = {}
                for key in _DEFAULT_THRESHOLDS:
                    if key in config_thresholds:
                        config_val = config_thresholds[key]
                        tier_val = tier_thresholds.get(key, _DEFAULT_THRESHOLDS[key])
                        # Only store if different from tier default
                        if config_val != tier_val:
                            overrides[key] = config_val
                if overrides:
                    new_entry["overrides"] = overrides

        # Merge with existing if strategy is merge
        if strategy == "merge" and isinstance(existing, dict):
            # Preserve existing overrides if not importing new ones
            if not include_thresholds and existing.get("overrides"):
                new_entry["overrides"] = existing["overrides"]
            # Merge existing config fragment with imported one
            if existing.get("config"):
                existing_config = existing["config"]
                if "config" in new_entry:
                    # New config takes precedence, but preserve unset keys from existing
                    merged_config = dict(existing_config)
                    merged_config.update(new_entry["config"])
                    new_entry["config"] = merged_config
                else:
                    new_entry["config"] = existing_config

        repos[repo_name] = new_entry
        imported.append(repo_name)

    # Save registry if not dry run
    if not dry_run and imported:
        save_registry(registry, registry_path=root / "config" / "registry.json")

    return {
        "imported": imported,
        "skipped": skipped,
        "conflicts": conflicts,
        "dry_run": dry_run,
    }
