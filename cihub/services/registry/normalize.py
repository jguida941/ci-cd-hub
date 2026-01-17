"""Normalization functions for registry data.

Handles legacy key normalization, metadata normalization, and config fragment normalization.
"""

from __future__ import annotations

from typing import Any

from cihub.services.registry.thresholds import _normalize_threshold_dict_inplace


def _normalize_repo_metadata_inplace(repo_cfg: dict[str, Any]) -> None:
    """Normalize duplicated repo metadata fields to a single canonical location.

    Contract (docs/development/archive/SYSTEM_INTEGRATION_PLAN.md):
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


def _resolve_repo_language(repo_cfg: dict[str, Any]) -> str | None:
    """Resolve repo language with canonical precedence."""
    config = repo_cfg.get("config")
    if isinstance(config, dict):
        repo_block = config.get("repo")
        if isinstance(repo_block, dict):
            repo_lang = repo_block.get("language")
            if isinstance(repo_lang, str) and repo_lang:
                return repo_lang
        config_lang = config.get("language")
        if isinstance(config_lang, str) and config_lang:
            return config_lang

    legacy_lang = repo_cfg.get("language")
    if isinstance(legacy_lang, str) and legacy_lang:
        return legacy_lang
    return None


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
