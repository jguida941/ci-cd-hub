"""Normalization helpers for CI/CD Hub config."""

from __future__ import annotations

import copy
from typing import Any

THRESHOLD_PROFILES: dict[str, dict[str, int]] = {
    "coverage-gate": {"coverage_min": 90, "mutation_score_min": 80},
    "security": {"max_critical_vulns": 0, "max_high_vulns": 5},
    "compliance": {"max_critical_vulns": 0, "max_high_vulns": 0},
}

_FEATURE_TOGGLES = (
    "chaos",
    "canary",
    "dr_drill",
    "egress_control",
    "cache_sentinel",
    "runner_isolation",
    "supply_chain",
    "telemetry",
    "kyverno",
    "hub_ci",
)

_NESTED_TOGGLES = (
    ("reports", "badges"),
    ("reports", "codecov"),
    ("reports", "github_summary"),
    ("notifications", "email"),
    ("notifications", "slack"),
)


def _normalize_tool_configs_inplace(config: dict[str, Any]) -> None:
    for lang in ("python", "java"):
        lang_config = config.get(lang)
        if not isinstance(lang_config, dict):
            continue
        tools = lang_config.get("tools")
        if not isinstance(tools, dict):
            continue
        for tool_name, tool_value in list(tools.items()):
            if isinstance(tool_value, bool):
                tools[tool_name] = {"enabled": tool_value}


def _normalize_enabled_sections_inplace(config: dict[str, Any]) -> None:
    for key in _FEATURE_TOGGLES:
        value = config.get(key)
        if isinstance(value, bool):
            config[key] = {"enabled": value}

    for parent_key, child_key in _NESTED_TOGGLES:
        parent = config.get(parent_key)
        if not isinstance(parent, dict):
            continue
        value = parent.get(child_key)
        if isinstance(value, bool):
            parent[child_key] = {"enabled": value}


def _apply_thresholds_profile_inplace(config: dict[str, Any]) -> None:
    profile = config.get("thresholds_profile")
    if not isinstance(profile, str) or not profile:
        return
    preset = THRESHOLD_PROFILES.get(profile)
    if not preset:
        return
    overrides = config.get("thresholds", {})
    if not isinstance(overrides, dict):
        overrides = {}
    merged = dict(preset)
    merged.update(overrides)
    config["thresholds"] = merged


def _apply_cvss_fallbacks_inplace(config: dict[str, Any]) -> None:
    thresholds = config.get("thresholds")
    if not isinstance(thresholds, dict):
        return
    if "trivy_cvss_fail" not in thresholds and "owasp_cvss_fail" in thresholds:
        thresholds["trivy_cvss_fail"] = thresholds["owasp_cvss_fail"]


def normalize_config(config: dict[str, Any], apply_thresholds_profile: bool = True) -> dict[str, Any]:
    """Normalize shorthand configs and apply threshold profiles."""
    if not isinstance(config, dict):
        return {}
    normalized = copy.deepcopy(config)
    _normalize_tool_configs_inplace(normalized)
    _normalize_enabled_sections_inplace(normalized)
    if apply_thresholds_profile:
        _apply_thresholds_profile_inplace(normalized)
    _apply_cvss_fallbacks_inplace(normalized)
    return normalized


def normalize_tool_configs(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize shorthand boolean tool configs to full object format."""
    if not isinstance(config, dict):
        return {}
    normalized = copy.deepcopy(config)
    _normalize_tool_configs_inplace(normalized)
    return normalized


def tool_enabled(
    config: dict[str, Any],
    tool: str,
    language: str,
    *,
    default: bool = False,
) -> bool:
    """Check if a tool is enabled in the config.

    This is the canonical implementation. All other `_tool_enabled` functions
    should be replaced with imports from this module.

    Args:
        config: The effective config dict
        tool: Tool key (e.g., "pytest", "bandit", "jacoco")
        language: Language key ("python" or "java")
        default: Default value if tool config is missing (default: False)

    Returns:
        True if the tool is enabled, False otherwise.

    Examples:
        >>> tool_enabled(config, "pytest", "python")
        True
        >>> tool_enabled(config, "sbom", "java", default=False)
        False
    """
    lang_block = config.get(language, {})
    if not isinstance(lang_block, dict):
        return default
    tools = lang_block.get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        enabled = entry.get("enabled")
        if isinstance(enabled, bool):
            return enabled
    return default
