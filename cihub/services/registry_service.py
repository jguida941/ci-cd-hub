"""Registry service for centralized repo configuration management.

Provides tier-based configuration with per-repo overrides.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.utils.paths import hub_root


_DEFAULT_THRESHOLDS: dict[str, int] = {
    "coverage_min": 70,
    "mutation_score_min": 70,
    "max_critical_vulns": 0,
    "max_high_vulns": 0,
}


def _as_int(value: Any) -> int | None:
    """Coerce JSON-ish values to int, returning None if not coercible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def _get_threshold_value(
    overrides: dict[str, Any],
    tier_defaults: dict[str, Any],
    *,
    key: str,
) -> int:
    """Get effective threshold value from overrides/tier defaults with legacy support."""
    legacy_key: str | None = None
    if key == "coverage_min":
        legacy_key = "coverage"
    elif key == "mutation_score_min":
        legacy_key = "mutation"
    elif key in ("max_critical_vulns", "max_high_vulns"):
        legacy_key = "vulns_max"

    # Overrides win
    val = _as_int(overrides.get(key))
    if val is not None:
        return val
    if legacy_key:
        legacy_val = _as_int(overrides.get(legacy_key))
        if legacy_val is not None:
            return legacy_val

    # Then tier defaults
    val = _as_int(tier_defaults.get(key))
    if val is not None:
        return val
    if legacy_key:
        legacy_val = _as_int(tier_defaults.get(legacy_key))
        if legacy_val is not None:
            return legacy_val

    # Fall back to schema defaults
    return _DEFAULT_THRESHOLDS[key]


def _normalize_threshold_dict_inplace(data: dict[str, Any]) -> None:
    """Normalize legacy threshold keys to schema keys in a dict (in place)."""
    # coverage -> coverage_min
    if "coverage_min" not in data and "coverage" in data:
        data["coverage_min"] = data["coverage"]
    data.pop("coverage", None)

    # mutation -> mutation_score_min
    if "mutation_score_min" not in data and "mutation" in data:
        data["mutation_score_min"] = data["mutation"]
    data.pop("mutation", None)

    # vulns_max -> max_{critical,high}_vulns
    if "vulns_max" in data:
        vulns_max = data.get("vulns_max")
        if "max_critical_vulns" not in data:
            data["max_critical_vulns"] = vulns_max
        if "max_high_vulns" not in data:
            data["max_high_vulns"] = vulns_max
    data.pop("vulns_max", None)


def _normalize_repo_metadata_inplace(repo_cfg: dict[str, Any]) -> None:
    """Normalize duplicated repo metadata fields to a single canonical location.

    Contract (SYSTEM_INTEGRATION_PLAN.md):
    - `repo_cfg["config"]["repo"]` is canonical when present
    - top-level `repo_cfg["language"]` / `repo_cfg["dispatch_enabled"]` are legacy/back-compat
    - if both are present and equal, drop the legacy copy to keep storage sparse
    - if both are present and differ, keep both (diff should surface drift)
    """
    config = repo_cfg.get("config")
    if not isinstance(config, dict):
        return
    repo_block = config.get("repo")
    if not isinstance(repo_block, dict):
        return

    for key in ("language", "dispatch_enabled"):
        if key in repo_cfg and key in repo_block and repo_cfg.get(key) == repo_block.get(key):
            repo_cfg.pop(key, None)


def _compute_repo_metadata_drift(repo_name: str, repo_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect drift between legacy top-level repo metadata and canonical config.repo."""
    config = repo_cfg.get("config")
    if not isinstance(config, dict):
        return []
    repo_block = config.get("repo")
    if not isinstance(repo_block, dict):
        return []

    diffs: list[dict[str, Any]] = []

    top_lang = repo_cfg.get("language")
    cfg_lang = repo_block.get("language")
    if isinstance(top_lang, str) and isinstance(cfg_lang, str) and top_lang != cfg_lang:
        diffs.append(
            {
                "repo": repo_name,
                "field": "repo.language",
                "registry_value": cfg_lang,  # canonical
                "actual_value": top_lang,  # legacy
                "severity": "warning",
            }
        )

    top_dispatch = repo_cfg.get("dispatch_enabled")
    cfg_dispatch = repo_block.get("dispatch_enabled")
    if isinstance(top_dispatch, bool) and isinstance(cfg_dispatch, bool) and top_dispatch != cfg_dispatch:
        diffs.append(
            {
                "repo": repo_name,
                "field": "repo.dispatch_enabled",
                "registry_value": cfg_dispatch,  # canonical
                "actual_value": top_dispatch,  # legacy
                "severity": "warning",
            }
        )

    return diffs


def _normalize_registry_inplace(registry: dict[str, Any]) -> None:
    """Normalize legacy registry storage keys to schema-aligned keys.

    This keeps backward compatibility (legacy keys still accepted), but ensures any
    registry written back to disk uses schema-aligned key names.
    """
    tiers = registry.get("tiers")
    if isinstance(tiers, dict):
        for tier in tiers.values():
            if isinstance(tier, dict):
                _normalize_threshold_dict_inplace(tier)

    repos = registry.get("repos")
    if isinstance(repos, dict):
        for repo_cfg in repos.values():
            if not isinstance(repo_cfg, dict):
                continue
            overrides = repo_cfg.get("overrides")
            if isinstance(overrides, dict):
                _normalize_threshold_dict_inplace(overrides)
            _normalize_repo_metadata_inplace(repo_cfg)


def _get_registry_path() -> Path:
    """Get the path to the registry file."""
    return hub_root() / "config" / "registry.json"


def load_registry(registry_path: Path | None = None) -> dict[str, Any]:
    """Load the registry from disk.

    Args:
        registry_path: Path to registry.json (defaults to config/registry.json)

    Returns:
        Parsed registry dict
    """
    path = registry_path or _get_registry_path()
    if not path.exists():
        return {"schema_version": "cihub-registry-v1", "tiers": {}, "repos": {}}

    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        _normalize_registry_inplace(data)
        return data


def save_registry(registry: dict[str, Any], registry_path: Path | None = None) -> None:
    """Save the registry to disk.

    Args:
        registry: Registry dict to save
        registry_path: Path to registry.json (defaults to config/registry.json)
    """
    path = registry_path or _get_registry_path()
    _normalize_registry_inplace(registry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def list_repos(registry: dict[str, Any], *, hub_root_path: Path | None = None) -> list[dict[str, Any]]:
    """List all repos with their tiers and effective settings.

    Returns:
        List of repo info dicts with:
        - name: repo name
        - tier: tier name
        - effective: dict of effective thresholds (tier + overrides)
    """
    tiers = registry.get("tiers", {})
    repos = registry.get("repos", {})
    result = []

    # Precompute tier threshold baselines (defaults + optional profile + tier config fragment + legacy tier keys)
    tier_threshold_defaults: dict[str, dict[str, Any]] = {}
    if isinstance(tiers, dict):
        from cihub.config.io import load_profile
        from cihub.config.paths import PathConfig

        paths = PathConfig(str(hub_root_path or hub_root()))
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

            # Legacy tier threshold keys (top-level) override profile/tier fragment thresholds.
            for key in _DEFAULT_THRESHOLDS:
                if key in tier_cfg:
                    defaults_for_tier[key] = tier_cfg.get(key)

            tier_threshold_defaults[tier_name] = defaults_for_tier

    for name, config in repos.items():
        tier_name = config.get("tier", "standard")
        overrides = config.get("overrides", {})
        if not isinstance(overrides, dict):
            overrides = {}

        # Include repo config fragment thresholds as a baseline, overridden by explicit overrides.
        repo_fragment = _normalize_config_fragment(config.get("config") if isinstance(config, dict) else None)
        combined_overrides: dict[str, Any] = {}
        repo_fragment_thresholds = repo_fragment.get("thresholds")
        has_config_thresholds = isinstance(repo_fragment_thresholds, dict) and bool(repo_fragment_thresholds)
        if has_config_thresholds:
            combined_overrides.update(repo_fragment_thresholds)
        combined_overrides.update(overrides)

        tier_defaults = tier_threshold_defaults.get(tier_name, {})

        # Compute effective settings (profile/tier/repo baselines + overrides)
        effective = {
            "coverage_min": _get_threshold_value(combined_overrides, tier_defaults, key="coverage_min"),
            "mutation_score_min": _get_threshold_value(combined_overrides, tier_defaults, key="mutation_score_min"),
            "max_critical_vulns": _get_threshold_value(combined_overrides, tier_defaults, key="max_critical_vulns"),
            "max_high_vulns": _get_threshold_value(combined_overrides, tier_defaults, key="max_high_vulns"),
        }

        result.append(
            {
                "name": name,
                "tier": tier_name,
                "description": config.get("description", ""),
                "effective": effective,
                # Back-compat: explicit overrides only.
                "has_overrides": bool(overrides),
                # New: any per-repo threshold config (explicit overrides OR managedConfig.thresholds).
                "has_threshold_overrides": bool(overrides) or has_config_thresholds,
                "has_config_thresholds": has_config_thresholds,
            }
        )

    return sorted(result, key=lambda x: x["name"])


def get_repo_config(
    registry: dict[str, Any], repo_name: str, *, hub_root_path: Path | None = None
) -> dict[str, Any] | None:
    """Get detailed configuration for a specific repo.

    Args:
        registry: Registry dict
        repo_name: Name of the repo

    Returns:
        Detailed config dict or None if not found
    """
    repos = registry.get("repos", {})
    if repo_name not in repos:
        return None

    config = repos[repo_name]
    tier_name = config.get("tier", "standard")
    tier_cfg = registry.get("tiers", {}).get(tier_name, {})
    if not isinstance(tier_cfg, dict):
        tier_cfg = {}

    profile_cfg: dict[str, Any] = {}
    profile_name = tier_cfg.get("profile")
    if isinstance(profile_name, str) and profile_name:
        from cihub.config.io import load_profile
        from cihub.config.paths import PathConfig

        paths = PathConfig(str(hub_root_path or hub_root()))
        profile_cfg = _normalize_config_fragment(load_profile(paths, profile_name))

    tier_fragment = _normalize_config_fragment(tier_cfg.get("config"))
    tier_defaults: dict[str, Any] = {}
    if isinstance(profile_cfg.get("thresholds"), dict):
        tier_defaults.update(profile_cfg["thresholds"])
    if isinstance(tier_fragment.get("thresholds"), dict):
        tier_defaults.update(tier_fragment["thresholds"])
    for key in _DEFAULT_THRESHOLDS:
        if key in tier_cfg:
            tier_defaults[key] = tier_cfg.get(key)

    overrides = config.get("overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}

    repo_fragment = _normalize_config_fragment(config.get("config") if isinstance(config, dict) else None)
    combined_overrides: dict[str, Any] = {}
    if isinstance(repo_fragment.get("thresholds"), dict):
        combined_overrides.update(repo_fragment["thresholds"])
    combined_overrides.update(overrides)

    # Compute effective settings
    effective = {
        "coverage_min": _get_threshold_value(combined_overrides, tier_defaults, key="coverage_min"),
        "mutation_score_min": _get_threshold_value(
            combined_overrides, tier_defaults, key="mutation_score_min"
        ),
        "max_critical_vulns": _get_threshold_value(combined_overrides, tier_defaults, key="max_critical_vulns"),
        "max_high_vulns": _get_threshold_value(combined_overrides, tier_defaults, key="max_high_vulns"),
    }

    return {
        "name": repo_name,
        "tier": tier_name,
        "tier_defaults": {
            "coverage_min": _get_threshold_value({}, tier_defaults, key="coverage_min"),
            "mutation_score_min": _get_threshold_value({}, tier_defaults, key="mutation_score_min"),
            "max_critical_vulns": _get_threshold_value({}, tier_defaults, key="max_critical_vulns"),
            "max_high_vulns": _get_threshold_value({}, tier_defaults, key="max_high_vulns"),
        },
        "overrides": overrides,
        "effective": effective,
        "description": config.get("description", ""),
    }


def set_repo_tier(
    registry: dict[str, Any],
    repo_name: str,
    tier: str,
) -> dict[str, Any]:
    """Set the tier for a repo.

    Args:
        registry: Registry dict (modified in place)
        repo_name: Name of the repo
        tier: Tier name to assign

    Returns:
        Updated repo config
    """
    tiers = registry.get("tiers", {})
    if tier not in tiers:
        raise ValueError(f"Unknown tier: {tier}. Available: {', '.join(tiers.keys())}")

    repos = registry.setdefault("repos", {})
    if repo_name not in repos:
        repos[repo_name] = {}

    repos[repo_name]["tier"] = tier
    result: dict[str, Any] = repos[repo_name]
    return result


def set_repo_override(
    registry: dict[str, Any],
    repo_name: str,
    key: str,
    value: int,
) -> dict[str, Any]:
    """Set an override value for a repo.

    Args:
        registry: Registry dict (modified in place)
        repo_name: Name of the repo
        key: Override key (coverage/mutation/vulns_max) or schema key
             (coverage_min/mutation_score_min/max_{critical,high}_vulns)
        value: Override value

    Returns:
        Updated repo config
    """
    valid_keys = {
        # Legacy keys (CLI flags still use these)
        "coverage",
        "mutation",
        "vulns_max",
        # Schema-aligned keys (preferred storage)
        "coverage_min",
        "mutation_score_min",
        "max_critical_vulns",
        "max_high_vulns",
    }
    if key not in valid_keys:
        raise ValueError(f"Invalid override key: {key}. Valid: {', '.join(valid_keys)}")

    repos = registry.setdefault("repos", {})
    if repo_name not in repos:
        repos[repo_name] = {"tier": "standard"}

    overrides = repos[repo_name].setdefault("overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
        repos[repo_name]["overrides"] = overrides

    # Store schema-aligned keys (keep legacy keys accepted for backward compatibility).
    if key == "coverage":
        overrides["coverage_min"] = value
    elif key == "mutation":
        overrides["mutation_score_min"] = value
    elif key == "vulns_max":
        overrides["max_critical_vulns"] = value
        overrides["max_high_vulns"] = value
    else:
        overrides[key] = value

    # Clean up any legacy keys left behind.
    _normalize_threshold_dict_inplace(overrides)
    result: dict[str, Any] = repos[repo_name]
    return result


def _normalize_config_fragment(fragment: Any) -> dict[str, Any]:
    """Normalize a config fragment without expanding thresholds profiles.

    NOTE: This is used for registry-managed *fragments* (sparse storage). We avoid
    writing derived/defaulted keys into fragments when possible.
    """
    from cihub.config.normalize import normalize_config

    if not isinstance(fragment, dict):
        return {}

    original_thresholds = fragment.get("thresholds")
    original_has_trivy_cvss = (
        isinstance(original_thresholds, dict) and "trivy_cvss_fail" in original_thresholds
    )
    original_has_owasp_cvss = (
        isinstance(original_thresholds, dict) and "owasp_cvss_fail" in original_thresholds
    )

    normalized = normalize_config(fragment, apply_thresholds_profile=False)

    # Avoid CVSS fallback expansion in fragments: normalize_config() will add
    # thresholds.trivy_cvss_fail when only thresholds.owasp_cvss_fail exists.
    thresholds = normalized.get("thresholds")
    if (
        isinstance(thresholds, dict)
        and original_has_owasp_cvss
        and not original_has_trivy_cvss
        and "trivy_cvss_fail" in thresholds
    ):
        thresholds.pop("trivy_cvss_fail", None)

    return normalized


def _merge_config_layers(layers: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge normalized config layers (later layers win)."""
    from cihub.config.merge import deep_merge

    merged: dict[str, Any] = {}
    for layer in layers:
        if layer:
            merged = deep_merge(merged, layer)
    return _normalize_config_fragment(merged)


def _values_equal(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        return False
    return a == b


def _collect_sparse_config_diffs(
    fragment: dict[str, Any],
    baseline: dict[str, Any],
    prefix: str,
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    if not fragment or not baseline:
        return diffs

    for key, value in fragment.items():
        if key not in baseline:
            continue
        base_val = baseline.get(key)
        if isinstance(value, dict) and isinstance(base_val, dict):
            diffs.extend(_collect_sparse_config_diffs(value, base_val, f"{prefix}{key}."))
            continue
        if _values_equal(value, base_val):
            diffs.append(
                {
                    "field": f"{prefix}{key}",
                    "registry_value": value,
                    "actual_value": base_val,
                    "severity": "warning",
                }
            )

    return diffs


def _diff_objects(before: Any, after: Any, prefix: str = "") -> list[tuple[str, Any, Any]]:
    """Compute a deterministic deep diff of JSON-ish objects.

    Returns a list of (field_path, old, new) tuples.
    """
    changes: list[tuple[str, Any, Any]] = []

    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            path = f"{prefix}{key}"
            if key not in before:
                changes.append((path, None, after.get(key)))
                continue
            if key not in after:
                changes.append((path, before.get(key), None))
                continue
            b = before.get(key)
            a = after.get(key)
            if isinstance(b, dict) and isinstance(a, dict):
                changes.extend(_diff_objects(b, a, prefix=f"{path}."))
                continue
            if isinstance(b, list) and isinstance(a, list):
                if not _values_equal(b, a):
                    changes.append((path, b, a))
                continue
            if not _values_equal(b, a):
                changes.append((path, b, a))
        return changes

    if isinstance(before, list) and isinstance(after, list):
        if not _values_equal(before, after):
            changes.append((prefix.rstrip("."), before, after))
        return changes

    if not _values_equal(before, after):
        changes.append((prefix.rstrip("."), before, after))
    return changes


def _compute_sparse_config_fragment_diffs(
    registry: dict[str, Any], *, hub_root_path: Path | None = None
) -> list[dict[str, Any]]:
    """Detect non-sparse config fragments stored in the registry."""
    from cihub.config.io import load_defaults, load_profile
    from cihub.config.paths import PathConfig

    paths = PathConfig(str(hub_root_path or hub_root()))
    defaults = _normalize_config_fragment(load_defaults(paths))

    diffs: list[dict[str, Any]] = []
    tiers = registry.get("tiers", {})
    repos = registry.get("repos", {})
    if not isinstance(tiers, dict):
        tiers = {}
    if not isinstance(repos, dict):
        repos = {}

    tier_context: dict[str, dict[str, Any]] = {}
    for tier_name, tier_cfg in tiers.items():
        if not isinstance(tier_cfg, dict):
            continue
        profile_name = tier_cfg.get("profile")
        profile_config: dict[str, Any] = {}
        if isinstance(profile_name, str) and profile_name:
            profile_config = _normalize_config_fragment(load_profile(paths, profile_name))
        tier_config = _normalize_config_fragment(tier_cfg.get("config"))

        tier_baseline = _merge_config_layers([defaults, profile_config])
        repo_baseline = _merge_config_layers([defaults, profile_config, tier_config])
        tier_context[tier_name] = {
            "tier_baseline": tier_baseline,
            "repo_baseline": repo_baseline,
        }

        for diff in _collect_sparse_config_diffs(tier_config, tier_baseline, "sparse.config."):
            diff["repo"] = f"tier:{tier_name}"
            diffs.append(diff)

    for repo_name, repo_cfg in repos.items():
        if not isinstance(repo_cfg, dict):
            continue
        repo_config = _normalize_config_fragment(repo_cfg.get("config"))
        if not repo_config:
            continue
        tier_name = repo_cfg.get("tier", "standard")
        baseline = defaults
        if tier_name in tier_context:
            baseline = tier_context[tier_name]["repo_baseline"]
        for diff in _collect_sparse_config_diffs(repo_config, baseline, "sparse.config."):
            diff["repo"] = repo_name
            diffs.append(diff)

    return diffs


def compute_diff(
    registry: dict[str, Any], configs_dir: Path, *, hub_root_path: Path | None = None
) -> list[dict[str, Any]]:
    """Compare registry against actual repo configs.

    Args:
        registry: Registry dict
        configs_dir: Path to config/repos/ directory

    Returns:
        List of diff entries with:
        - repo: repo name
        - field: which setting differs
        - registry_value: expected from registry
        - actual_value: found in repo config
    """
    from cihub.config.io import load_yaml_file  # Avoid circular import

    diffs: list[dict[str, Any]] = []
    diffs.extend(_compute_sparse_config_fragment_diffs(registry, hub_root_path=hub_root_path))

    repos = registry.get("repos", {})
    if not isinstance(repos, dict):
        repos = {}
    for repo_name, repo_cfg in repos.items():
        if isinstance(repo_cfg, dict):
            diffs.extend(_compute_repo_metadata_drift(repo_name, repo_cfg))

    # Phase 2.4: non-threshold managedConfig drift. Reuse the sync engine in dry-run mode
    # to compute the intended on-disk state across allowlisted keys.
    for change in sync_to_configs(registry, configs_dir, dry_run=True, hub_root_path=hub_root_path):
        if change.get("action") == "skip":
            reason = change.get("reason", "skipped")
            severity = "error" if "failed to load" in str(reason) else "warning"
            diffs.append(
                {
                    "repo": change.get("repo", "<unknown>"),
                    "field": "config_file",
                    "registry_value": "present",
                    "actual_value": reason,
                    "severity": severity,
                }
            )
            continue
        if change.get("action") != "would_update":
            continue
        repo_name = change.get("repo", "<unknown>")
        for field, old, new in change.get("fields", []):
            diffs.append(
                {
                    "repo": repo_name,
                    "field": field,
                    "registry_value": new,
                    "actual_value": old,
                    "severity": "warning",
                }
            )

    return diffs


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
    import yaml  # Only needed for write
    import copy

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

    paths = PathConfig(str(hub_root_path or hub_root()))
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
        if not config_path.exists():
            changes.append(
                {
                    "repo": repo_name,
                    "action": "skip",
                    "reason": "config file not found",
                }
            )
            continue

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

        # Update thresholds
        thresholds = config.setdefault("thresholds", {})
        if not isinstance(thresholds, dict):
            thresholds = {}
            config["thresholds"] = thresholds

        # Clean up legacy (schema-incompatible) keys if they exist.
        for legacy_key in ("coverage", "mutation_score", "vulns_max"):
            if legacy_key in thresholds:
                thresholds.pop(legacy_key, None)

        if thresholds.get("coverage_min", 70) != effective["coverage_min"]:
            thresholds["coverage_min"] = effective["coverage_min"]

        if thresholds.get("mutation_score_min", 70) != effective["mutation_score_min"]:
            thresholds["mutation_score_min"] = effective["mutation_score_min"]

        if thresholds.get("max_critical_vulns", 0) != effective["max_critical_vulns"]:
            thresholds["max_critical_vulns"] = effective["max_critical_vulns"]

        if thresholds.get("max_high_vulns", 0) != effective["max_high_vulns"]:
            thresholds["max_high_vulns"] = effective["max_high_vulns"]

        # Keep top-level language consistent with repo.language when present.
        repo_block = config.get("repo")
        if isinstance(repo_block, dict) and isinstance(repo_block.get("language"), str):
            config["language"] = repo_block["language"]

        repo_changes = _diff_objects(before_config, config, prefix="")

        if not repo_changes:
            changes.append(
                {
                    "repo": repo_name,
                    "action": "unchanged",
                    "reason": "already in sync",
                }
            )
            continue

        if not dry_run:
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        changes.append(
            {
                "repo": repo_name,
                "action": "updated" if not dry_run else "would_update",
                "fields": repo_changes,
            }
        )

    return changes
