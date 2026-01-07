"""Registry service for centralized repo configuration management.

Provides tier-based configuration with per-repo overrides.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.utils.paths import hub_root


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
        return json.load(f)


def save_registry(registry: dict[str, Any], registry_path: Path | None = None) -> None:
    """Save the registry to disk.

    Args:
        registry: Registry dict to save
        registry_path: Path to registry.json (defaults to config/registry.json)
    """
    path = registry_path or _get_registry_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def list_repos(registry: dict[str, Any]) -> list[dict[str, Any]]:
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

    for name, config in repos.items():
        tier_name = config.get("tier", "standard")
        tier_defaults = tiers.get(tier_name, {})
        overrides = config.get("overrides", {})

        # Compute effective settings (tier defaults + overrides)
        effective = {
            "coverage": overrides.get("coverage", tier_defaults.get("coverage", 70)),
            "mutation": overrides.get("mutation", tier_defaults.get("mutation", 70)),
            "vulns_max": overrides.get("vulns_max", tier_defaults.get("vulns_max", 0)),
        }

        result.append({
            "name": name,
            "tier": tier_name,
            "description": config.get("description", ""),
            "effective": effective,
            "has_overrides": bool(overrides),
        })

    return sorted(result, key=lambda x: x["name"])


def get_repo_config(registry: dict[str, Any], repo_name: str) -> dict[str, Any] | None:
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
    tier_defaults = registry.get("tiers", {}).get(tier_name, {})
    overrides = config.get("overrides", {})

    # Compute effective settings
    effective = {
        "coverage": overrides.get("coverage", tier_defaults.get("coverage", 70)),
        "mutation": overrides.get("mutation", tier_defaults.get("mutation", 70)),
        "vulns_max": overrides.get("vulns_max", tier_defaults.get("vulns_max", 0)),
    }

    return {
        "name": repo_name,
        "tier": tier_name,
        "tier_defaults": {
            "coverage": tier_defaults.get("coverage", 70),
            "mutation": tier_defaults.get("mutation", 70),
            "vulns_max": tier_defaults.get("vulns_max", 0),
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
    return repos[repo_name]


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
        key: Override key (coverage, mutation, vulns_max)
        value: Override value

    Returns:
        Updated repo config
    """
    valid_keys = {"coverage", "mutation", "vulns_max"}
    if key not in valid_keys:
        raise ValueError(f"Invalid override key: {key}. Valid: {', '.join(valid_keys)}")

    repos = registry.setdefault("repos", {})
    if repo_name not in repos:
        repos[repo_name] = {"tier": "standard"}

    overrides = repos[repo_name].setdefault("overrides", {})
    overrides[key] = value
    return repos[repo_name]


def compute_diff(registry: dict[str, Any], configs_dir: Path) -> list[dict[str, Any]]:
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

    diffs = []
    repos_info = list_repos(registry)

    for repo_info in repos_info:
        repo_name = repo_info["name"]
        effective = repo_info["effective"]

        # Try to load actual repo config
        config_path = configs_dir / f"{repo_name}.yaml"
        if not config_path.exists():
            diffs.append({
                "repo": repo_name,
                "field": "config_file",
                "registry_value": "present",
                "actual_value": "missing",
                "severity": "warning",
            })
            continue

        try:
            actual = load_yaml_file(config_path)
        except Exception as exc:  # noqa: BLE001
            diffs.append({
                "repo": repo_name,
                "field": "config_file",
                "registry_value": "valid",
                "actual_value": f"error: {exc}",
                "severity": "error",
            })
            continue

        # Compare thresholds
        thresholds = actual.get("thresholds", {})

        if thresholds.get("coverage", 70) != effective["coverage"]:
            diffs.append({
                "repo": repo_name,
                "field": "coverage",
                "registry_value": effective["coverage"],
                "actual_value": thresholds.get("coverage", 70),
                "severity": "warning",
            })

        if thresholds.get("mutation_score", 70) != effective["mutation"]:
            diffs.append({
                "repo": repo_name,
                "field": "mutation",
                "registry_value": effective["mutation"],
                "actual_value": thresholds.get("mutation_score", 70),
                "severity": "warning",
            })

        if thresholds.get("vulns_max", 0) != effective["vulns_max"]:
            diffs.append({
                "repo": repo_name,
                "field": "vulns_max",
                "registry_value": effective["vulns_max"],
                "actual_value": thresholds.get("vulns_max", 0),
                "severity": "warning",
            })

    return diffs


def sync_to_configs(
    registry: dict[str, Any],
    configs_dir: Path,
    *,
    dry_run: bool = True,
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

    from cihub.config.io import load_yaml_file

    changes = []
    repos_info = list_repos(registry)

    for repo_info in repos_info:
        repo_name = repo_info["name"]
        effective = repo_info["effective"]

        config_path = configs_dir / f"{repo_name}.yaml"
        if not config_path.exists():
            changes.append({
                "repo": repo_name,
                "action": "skip",
                "reason": "config file not found",
            })
            continue

        try:
            config = load_yaml_file(config_path)
        except Exception as exc:  # noqa: BLE001
            changes.append({
                "repo": repo_name,
                "action": "skip",
                "reason": f"failed to load: {exc}",
            })
            continue

        # Update thresholds
        thresholds = config.setdefault("thresholds", {})
        repo_changes = []

        if thresholds.get("coverage", 70) != effective["coverage"]:
            repo_changes.append(("coverage", thresholds.get("coverage", 70), effective["coverage"]))
            thresholds["coverage"] = effective["coverage"]

        if thresholds.get("mutation_score", 70) != effective["mutation"]:
            repo_changes.append(("mutation_score", thresholds.get("mutation_score", 70), effective["mutation"]))
            thresholds["mutation_score"] = effective["mutation"]

        if thresholds.get("vulns_max", 0) != effective["vulns_max"]:
            repo_changes.append(("vulns_max", thresholds.get("vulns_max", 0), effective["vulns_max"]))
            thresholds["vulns_max"] = effective["vulns_max"]

        if not repo_changes:
            changes.append({
                "repo": repo_name,
                "action": "unchanged",
                "reason": "already in sync",
            })
            continue

        if not dry_run:
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        changes.append({
            "repo": repo_name,
            "action": "updated" if not dry_run else "would_update",
            "fields": repo_changes,
        })

    return changes
