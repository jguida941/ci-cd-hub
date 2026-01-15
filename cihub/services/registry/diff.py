"""Diff computation for registry vs actual repo configs.

Handles computing differences between registry settings and actual config files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.services.registry import _paths as _registry_paths
from cihub.services.registry.thresholds import (
    _DEFAULT_THRESHOLDS,
    _normalize_threshold_dict_inplace,
)


def _normalize_config_fragment(fragment: Any) -> dict[str, Any]:
    """Normalize a config fragment without expanding thresholds profiles.

    NOTE: This is used for registry-managed *fragments* (sparse storage). We avoid
    writing derived/defaulted keys into fragments when possible.
    """
    from cihub.config.normalize import normalize_config

    if not isinstance(fragment, dict):
        return {}

    original_thresholds = fragment.get("thresholds")
    original_has_trivy_cvss = isinstance(original_thresholds, dict) and "trivy_cvss_fail" in original_thresholds
    original_has_owasp_cvss = isinstance(original_thresholds, dict) and "owasp_cvss_fail" in original_thresholds

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
    return bool(a == b)


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

    paths = PathConfig(str(hub_root_path or _registry_paths.get_hub_root()))
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


def _get_managed_config_top_level_keys(*, hub_root_path: Path | None = None) -> set[str]:
    """Return the registry-managed top-level config keys (allowlist).

    Source of truth: schema/registry.schema.json $defs.managedConfig.properties.
    """
    root = hub_root_path or _registry_paths.get_hub_root()
    schema_path = root / "schema" / "registry.schema.json"
    try:
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
        defs = raw.get("$defs", {})
        managed = defs.get("managedConfig", {})
        props = managed.get("properties", {})
        if isinstance(props, dict) and props:
            return set(props.keys())
    except Exception:  # noqa: S110, BLE001
        pass  # Schema read may fail, use fallback

    # Conservative fallback (keeps diff usable even if schema missing).
    return {
        "version",
        "language",
        "repo",
        "python",
        "java",
        "thresholds",
        "gates",
        "reports",
        "notifications",
        "harden_runner",
        "thresholds_profile",
        "cihub",
    }


def _get_config_schema_top_level_keys(*, hub_root_path: Path | None = None) -> tuple[set[str], str | None]:
    """Return (schema_top_level_keys, error_message)."""
    root = hub_root_path or _registry_paths.get_hub_root()
    schema_path = root / "schema" / "ci-hub-config.schema.json"
    if not schema_path.exists():
        return set(), f"Config schema not found: {schema_path}"
    try:
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return set(), f"Failed to load config schema {schema_path}: {exc}"
    props = raw.get("properties", {})
    if not isinstance(props, dict) or not props:
        return set(), f"Config schema has no top-level properties: {schema_path}"
    return set(props.keys()), None


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


def _compute_repo_local_config_overrides(
    repo_name: str,
    repo_local_config: dict[str, Any],
    expected_config: dict[str, Any],
    managed_keys: set[str],
) -> list[dict[str, Any]]:
    """Detect .ci-hub.yml overrides of registry-managed config.

    Args:
        repo_name: Name of the repository
        repo_local_config: Parsed .ci-hub.yml content
        expected_config: Expected config from registry (tier + repo fragments)
        managed_keys: Set of registry-managed top-level keys

    Returns:
        List of diff entries for values overridden by .ci-hub.yml
    """
    diffs: list[dict[str, Any]] = []

    for key in sorted(repo_local_config.keys()):
        if key not in managed_keys:
            # Not a registry-managed key - skip (repo can have custom keys)
            continue

        local_value = repo_local_config.get(key)
        expected_value = expected_config.get(key)

        if local_value is None:
            continue

        # For nested dicts, compute field-level diffs
        if isinstance(local_value, dict) and isinstance(expected_value, dict):
            for sub_key, sub_local in local_value.items():
                sub_expected = expected_value.get(sub_key)
                if sub_local != sub_expected:
                    diffs.append(
                        {
                            "repo": repo_name,
                            "field": f"ci-hub-yml.{key}.{sub_key}",
                            "registry_value": sub_expected,
                            "actual_value": sub_local,
                            "severity": "info",  # Overrides are expected, just surfacing them
                        }
                    )
        elif local_value != expected_value:
            diffs.append(
                {
                    "repo": repo_name,
                    "field": f"ci-hub-yml.{key}",
                    "registry_value": expected_value,
                    "actual_value": local_value,
                    "severity": "info",  # Overrides are expected, just surfacing them
                }
            )

    return diffs


def compute_diff(
    registry: dict[str, Any],
    configs_dir: Path,
    *,
    hub_root_path: Path | None = None,
    repo_paths: dict[str, Path] | None = None,
) -> list[dict[str, Any]]:
    """Compare registry against actual repo configs.

    Args:
        registry: Registry dict
        configs_dir: Path to config/repos/ directory
        hub_root_path: Optional path to hub root (for loading profiles/schemas)
        repo_paths: Optional mapping of repo_name -> path to cloned repo dir.
                    When provided, reads each repo's .ci-hub.yml and reports overrides.

    Returns:
        List of diff entries with:
        - repo: repo name
        - field: which setting differs
        - registry_value: expected from registry
        - actual_value: found in repo config
        - severity: error/warning/info
    """
    from cihub.config.io import load_yaml_file  # Avoid circular import
    from cihub.services.registry.sync import sync_to_configs

    diffs: list[dict[str, Any]] = []
    diffs.extend(_compute_sparse_config_fragment_diffs(registry, hub_root_path=hub_root_path))

    repos = registry.get("repos", {})
    if not isinstance(repos, dict):
        repos = {}
    for repo_name, repo_cfg in repos.items():
        if isinstance(repo_cfg, dict):
            diffs.extend(_compute_repo_metadata_drift(repo_name, repo_cfg))

    # Phase 2.4 (full drift): detect orphan config files and unmanaged top-level keys
    # in config/repos/*.yaml that are not in the registry-managed allowlist.
    managed_top_level_keys = _get_managed_config_top_level_keys(hub_root_path=hub_root_path)
    config_schema_top_level_keys, schema_error = _get_config_schema_top_level_keys(hub_root_path=hub_root_path)
    if schema_error:
        diffs.append(
            {
                "repo": "<hub>",
                "field": "schema",
                "registry_value": "loaded",
                "actual_value": schema_error,
                "severity": "error",
            }
        )
    registry_repo_names = set(repos.keys())
    failed_load: set[str] = set()
    for config_path in sorted(configs_dir.rglob("*.yaml")):
        try:
            rel = config_path.relative_to(configs_dir)
            repo_name = rel.with_suffix("").as_posix()
        except Exception:  # noqa: BLE001
            repo_name = config_path.stem
        if repo_name not in registry_repo_names:
            diffs.append(
                {
                    "repo": repo_name,
                    "field": "registry_entry",
                    "registry_value": "missing",
                    "actual_value": "config_file_present",
                    "severity": "warning",
                }
            )
        try:
            actual = load_yaml_file(config_path)
        except Exception as exc:  # noqa: BLE001
            diffs.append(
                {
                    "repo": repo_name,
                    "field": "config_file",
                    "registry_value": "valid",
                    "actual_value": f"error: {exc}",
                    "severity": "error",
                }
            )
            failed_load.add(repo_name)
            continue
        if not isinstance(actual, dict):
            continue
        for key in sorted(actual.keys()):
            if key not in config_schema_top_level_keys and not schema_error:
                diffs.append(
                    {
                        "repo": repo_name,
                        "field": f"unknown_key.{key}",
                        "registry_value": "schema_invalid",
                        "actual_value": "present",
                        "severity": "error",
                    }
                )
            elif key not in managed_top_level_keys:
                diffs.append(
                    {
                        "repo": repo_name,
                        "field": f"unmanaged_key.{key}",
                        "registry_value": "not_managed",
                        "actual_value": "present",
                        "severity": "warning",
                    }
                )

    # Phase 2.4: non-threshold managedConfig drift. Reuse the sync engine in dry-run mode
    # to compute the intended on-disk state across allowlisted keys.
    for change in sync_to_configs(registry, configs_dir, dry_run=True, hub_root_path=hub_root_path):
        if change.get("action") == "skip":
            reason = change.get("reason", "skipped")
            repo_name = change.get("repo", "<unknown>")
            if repo_name in failed_load:
                # Avoid duplicate config_file drift entries; orphan scan already surfaced it.
                continue
            severity = "error" if "failed to load" in str(reason) else "warning"
            diffs.append(
                {
                    "repo": repo_name,
                    "field": "config_file",
                    "registry_value": "present",
                    "actual_value": reason,
                    "severity": severity,
                }
            )
            continue
        action = change.get("action")
        if action not in ("would_update", "would_create"):
            continue
        repo_name = change.get("repo", "<unknown>")
        # For would_create, report that config file would be created
        if action == "would_create":
            diffs.append(
                {
                    "repo": repo_name,
                    "field": "config_file",
                    "registry_value": "would_create",
                    "actual_value": "missing",
                    "severity": "warning",
                }
            )
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

    # Phase 2.4: Detect .ci-hub.yml overrides when repo_paths are provided
    if repo_paths:
        from cihub.config.io import load_defaults, load_profile
        from cihub.config.paths import PathConfig

        paths = PathConfig(str(hub_root_path or _registry_paths.get_hub_root()))
        tiers = registry.get("tiers", {})
        if not isinstance(tiers, dict):
            tiers = {}
        repos_dict = registry.get("repos", {})
        if not isinstance(repos_dict, dict):
            repos_dict = {}

        # Load defaults once (base layer for expected config)
        defaults_cfg = _normalize_config_fragment(load_defaults(paths))

        for repo_name, repo_path in repo_paths.items():
            ci_hub_yml_path = repo_path / ".ci-hub.yml"
            if not ci_hub_yml_path.exists():
                continue

            try:
                repo_local_config_raw = load_yaml_file(ci_hub_yml_path)
            except Exception as exc:  # noqa: BLE001
                diffs.append(
                    {
                        "repo": repo_name,
                        "field": "ci-hub-yml",
                        "registry_value": "valid",
                        "actual_value": f"error: {exc}",
                        "severity": "error",
                    }
                )
                continue

            if not isinstance(repo_local_config_raw, dict):
                continue

            # Normalize .ci-hub.yml content (same rules as registry fragments)
            repo_local_config = _normalize_config_fragment(repo_local_config_raw)

            # Build expected config from: defaults + profile + tier fragment + repo fragment + overrides
            repo_cfg = repos_dict.get(repo_name, {})
            if not isinstance(repo_cfg, dict):
                repo_cfg = {}
            tier_name = repo_cfg.get("tier", "standard")
            tier_cfg = tiers.get(tier_name, {})
            if not isinstance(tier_cfg, dict):
                tier_cfg = {}

            # Load tier profile
            profile_cfg: dict[str, Any] = {}
            profile_name = tier_cfg.get("profile")
            if isinstance(profile_name, str) and profile_name:
                profile_cfg = _normalize_config_fragment(load_profile(paths, profile_name))

            # Extract repo-level explicit overrides (repos.<name>.overrides) and normalize
            repo_overrides = repo_cfg.get("overrides", {})
            if not isinstance(repo_overrides, dict):
                repo_overrides = {}
            # Normalize legacy keys in repo overrides (coverage->coverage_min, etc.)
            _normalize_threshold_dict_inplace(repo_overrides)

            # Build tier fragment with tier-level threshold keys merged in
            tier_fragment = _normalize_config_fragment(tier_cfg.get("config"))
            # Extract tier-level threshold keys (direct on tier, not in tier.config)
            # These are part of the tier layer, not overrides applied at the end
            tier_thresholds = tier_fragment.setdefault("thresholds", {})
            for key in _DEFAULT_THRESHOLDS:
                if key in tier_cfg and key not in tier_thresholds:
                    # Only add if not already in tier.config.thresholds (config takes precedence)
                    tier_thresholds[key] = tier_cfg[key]

            # Merge fragments: defaults -> profile -> tier (with tier thresholds) -> repo
            repo_fragment = _normalize_config_fragment(repo_cfg.get("config"))
            expected_config = _merge_config_layers(
                [
                    defaults_cfg,
                    profile_cfg,
                    tier_fragment,
                    repo_fragment,
                ]
            )

            # Apply repo explicit overrides last (highest precedence)
            expected_thresholds = expected_config.setdefault("thresholds", {})
            if isinstance(expected_thresholds, dict):
                expected_thresholds.update(repo_overrides)

            # Mirror sync behavior: derive top-level language from repo metadata when absent.
            if "language" not in expected_config:
                derived_lang = None
                repo_meta = expected_config.get("repo")
                if isinstance(repo_meta, dict):
                    derived_lang = repo_meta.get("language")
                if not derived_lang:
                    legacy_lang = repo_cfg.get("language")
                    if isinstance(legacy_lang, str):
                        derived_lang = legacy_lang
                if derived_lang:
                    expected_config["language"] = derived_lang

            # Compute overrides
            diffs.extend(
                _compute_repo_local_config_overrides(
                    repo_name,
                    repo_local_config,
                    expected_config,
                    managed_top_level_keys,
                )
            )

    return diffs
