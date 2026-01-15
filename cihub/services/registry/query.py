"""Query operations for registry data.

Handles listing repos, getting repo config, and setting repo properties.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cihub.services.registry import _paths as _registry_paths
from cihub.services.registry.diff import _normalize_config_fragment
from cihub.services.registry.normalize import _resolve_repo_language
from cihub.services.registry.thresholds import (
    _DEFAULT_THRESHOLDS,
    _compute_all_effective_thresholds,
    _normalize_threshold_dict_inplace,
)


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
        if has_config_thresholds and repo_fragment_thresholds is not None:
            combined_overrides.update(repo_fragment_thresholds)
        combined_overrides.update(overrides)

        tier_defaults = tier_threshold_defaults.get(tier_name, {})

        # Compute effective settings for ALL threshold fields (profile/tier/repo baselines + overrides)
        effective = _compute_all_effective_thresholds(combined_overrides, tier_defaults)

        repo_language = _resolve_repo_language(config) if isinstance(config, dict) else None

        result.append(
            {
                "name": name,
                "tier": tier_name,
                "description": config.get("description", ""),
                "language": repo_language,
                "config": config.get("config", {}),
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

        paths = PathConfig(str(hub_root_path or _registry_paths.get_hub_root()))
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

    # Compute effective settings for ALL threshold fields
    effective = _compute_all_effective_thresholds(combined_overrides, tier_defaults)

    # Compute tier defaults (what the repo would have with no overrides)
    tier_defaults_computed = _compute_all_effective_thresholds({}, tier_defaults)

    repo_language = _resolve_repo_language(config) if isinstance(config, dict) else None

    return {
        "name": repo_name,
        "tier": tier_name,
        "tier_defaults": tier_defaults_computed,
        "overrides": overrides,
        "effective": effective,
        "description": config.get("description", ""),
        "language": repo_language,
        "config": config.get("config", {}),
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
    value: int | float,
) -> dict[str, Any]:
    """Set an override value for a repo.

    Args:
        registry: Registry dict (modified in place)
        repo_name: Name of the repo
        key: Override key - accepts all schema threshold keys plus legacy aliases.
             Schema keys: coverage_min, mutation_score_min, max_critical_vulns,
                          max_high_vulns, max_pip_audit_vulns, owasp_cvss_fail,
                          trivy_cvss_fail, max_semgrep_findings, max_ruff_errors,
                          max_black_issues, max_isort_issues, max_checkstyle_errors,
                          max_spotbugs_bugs, max_pmd_violations
             Legacy keys: coverage, mutation, vulns_max
        value: Override value

    Returns:
        Updated repo config
    """
    # All schema-aligned threshold keys
    schema_keys = set(_DEFAULT_THRESHOLDS.keys())
    # Legacy key aliases for backward compatibility
    legacy_keys = {"coverage", "mutation", "vulns_max"}
    valid_keys = schema_keys | legacy_keys

    if key not in valid_keys:
        raise ValueError(f"Invalid override key: {key}. Valid: {', '.join(sorted(valid_keys))}")

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
