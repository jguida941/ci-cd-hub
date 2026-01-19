"""Registry service for centralized repo configuration management.

Provides tier-based configuration with per-repo overrides.

This module is a thin shim for backward compatibility.
All functionality has been moved to the cihub.services.registry package.
"""

from __future__ import annotations

# Re-export everything from the registry package for backward compatibility.
# Covers thresholds, diffs, normalization, path utilities, query, I/O, and sync helpers.
from cihub.services.registry import (
    _DEFAULT_THRESHOLDS,
    _FLOAT_THRESHOLD_KEYS,
    _as_int,
    _as_number,
    _collect_sparse_config_diffs,
    _compute_all_effective_thresholds,
    _compute_repo_local_config_overrides,
    _compute_repo_metadata_drift,
    _compute_sparse_config_fragment_diffs,
    _diff_objects,
    _get_config_schema_top_level_keys,
    _get_managed_config_top_level_keys,
    _get_registry_path,
    _get_threshold_value,
    _merge_config_layers,
    _normalize_config_fragment,
    _normalize_registry_inplace,
    _normalize_repo_metadata_inplace,
    _normalize_threshold_dict_inplace,
    _resolve_repo_language,
    _values_equal,
    bootstrap_from_configs,
    compute_diff,
    get_repo_config,
    hub_root,
    list_repos,
    load_registry,
    save_registry,
    set_repo_override,
    set_repo_tier,
    sync_to_configs,
)

__all__ = [
    # Utilities (for test monkeypatching backward compat)
    "hub_root",
    # I/O
    "load_registry",
    "save_registry",
    "_get_registry_path",
    # Normalization
    "_normalize_repo_metadata_inplace",
    "_resolve_repo_language",
    "_normalize_registry_inplace",
    # Thresholds
    "_DEFAULT_THRESHOLDS",
    "_FLOAT_THRESHOLD_KEYS",
    "_as_int",
    "_as_number",
    "_get_threshold_value",
    "_compute_all_effective_thresholds",
    "_normalize_threshold_dict_inplace",
    # Diff
    "_normalize_config_fragment",
    "_merge_config_layers",
    "_values_equal",
    "_collect_sparse_config_diffs",
    "_diff_objects",
    "_compute_sparse_config_fragment_diffs",
    "_get_managed_config_top_level_keys",
    "_get_config_schema_top_level_keys",
    "_compute_repo_metadata_drift",
    "_compute_repo_local_config_overrides",
    "compute_diff",
    # Sync
    "sync_to_configs",
    "bootstrap_from_configs",
    # Query
    "list_repos",
    "get_repo_config",
    "set_repo_tier",
    "set_repo_override",
]
