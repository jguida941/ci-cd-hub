"""Registry service for centralized repo configuration management.

Provides tier-based configuration with per-repo overrides.

This package re-exports all public functions for backward compatibility.
"""

from __future__ import annotations

# Path utilities (for test monkeypatching)
# NOTE: Tests may monkeypatch cihub.services.registry_service.hub_root or
# cihub.services.registry._paths.hub_root. Both should work since submodules
# access _paths.hub_root at call time via module attribute lookup.
from cihub.services.registry._paths import hub_root

# Diff functions
from cihub.services.registry.diff import (
    _collect_sparse_config_diffs,
    _compute_repo_local_config_overrides,
    _compute_repo_metadata_drift,
    _compute_sparse_config_fragment_diffs,
    _diff_objects,
    _get_config_schema_top_level_keys,
    _get_managed_config_top_level_keys,
    _merge_config_layers,
    _normalize_config_fragment,
    _values_equal,
    compute_diff,
)

# I/O operations
from cihub.services.registry.io import (
    _get_registry_path,
    load_registry,
    save_registry,
)

# Normalization functions
from cihub.services.registry.normalize import (
    _normalize_registry_inplace,
    _normalize_repo_metadata_inplace,
    _resolve_repo_language,
)

# Query functions
from cihub.services.registry.query import (
    get_repo_config,
    list_repos,
    set_repo_override,
    set_repo_tier,
)

# Sync functions
from cihub.services.registry.sync import (
    bootstrap_from_configs,
    sync_to_configs,
)

# Threshold functions
from cihub.services.registry.thresholds import (
    _DEFAULT_THRESHOLDS,
    _FLOAT_THRESHOLD_KEYS,
    _as_int,
    _as_number,
    _compute_all_effective_thresholds,
    _get_threshold_value,
    _normalize_threshold_dict_inplace,
)

__all__ = [
    # Path utilities
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
