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


def _normalize_deprecated_tool_fields_inplace(config: dict[str, Any]) -> None:
    """Normalize deprecated/alias tool fields to canonical names.

    This keeps backward compatibility with older configs while keeping the
    internal config model consistent for downstream consumers (inputs, gates, TS CLI).
    """
    python_cfg = config.get("python")
    if isinstance(python_cfg, dict):
        tools = python_cfg.get("tools")
        if isinstance(tools, dict):
            mutmut_cfg = tools.get("mutmut")
            if isinstance(mutmut_cfg, dict):
                # Deprecated alias: mutmut.min_score -> mutmut.min_mutation_score
                if "min_mutation_score" not in mutmut_cfg and "min_score" in mutmut_cfg:
                    mutmut_cfg["min_mutation_score"] = mutmut_cfg.get("min_score")
                mutmut_cfg.pop("min_score", None)


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
    _normalize_deprecated_tool_fields_inplace(normalized)
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


# ===========================================================================
# fail_on_* Normalization
# ===========================================================================
# Tools use various fail_on_* patterns with different naming conventions:
#
# Boolean failure flags (schema-defined):
#   - fail_on_error: Generic tool error (codeql, docker, ruff, spotbugs)
#   - fail_on_findings: SAST findings (semgrep)
#   - fail_on_violation: Style violations (checkstyle, pmd)
#   - fail_on_format_issues: Formatting issues (black)
#   - fail_on_issues: Import issues (isort)
#   - fail_on_vuln: Vulnerabilities (pip_audit)
#   - fail_on_high/medium/low: Severity levels (bandit)
#   - fail_on_critical/high: Severity levels (trivy)
#   - fail_on_missing_compose: Missing file (docker)
#
# Numeric thresholds:
#   - fail_on_cvss: CVSS score threshold (owasp, trivy)
#
# Note: Property-based testing tools (hypothesis, jqwik) don't have
# configurable fail_on_* - they simply pass or fail based on test results.
#
# These helpers provide a consistent API for accessing fail_on_* values
# while maintaining backward compatibility with existing schema naming.
# ===========================================================================

# Canonical mapping of tool -> fail_on_* key for boolean flags
# Only includes tools that have schema-defined fail_on_* fields
_FAIL_ON_KEY_MAP: dict[str, str] = {
    # Generic error flag
    "codeql": "fail_on_error",
    "docker": "fail_on_error",
    "ruff": "fail_on_error",
    "spotbugs": "fail_on_error",
    # Specific naming
    "semgrep": "fail_on_findings",
    "checkstyle": "fail_on_violation",
    "pmd": "fail_on_violation",
    "black": "fail_on_format_issues",
    "isort": "fail_on_issues",
    "pip_audit": "fail_on_vuln",
}

# Default values for fail_on_* flags (aligned with schema defaults)
_FAIL_ON_DEFAULTS: dict[str, bool] = {
    "fail_on_error": True,
    "fail_on_findings": False,
    "fail_on_violation": True,  # checkstyle default; pmd is False
    "fail_on_format_issues": False,
    "fail_on_issues": False,
    "fail_on_vuln": True,
    "fail_on_high": True,
    "fail_on_medium": False,
    "fail_on_low": False,
    "fail_on_critical": False,
    "fail_on_missing_compose": False,
}

# Tool-specific default overrides (where schema differs from _FAIL_ON_DEFAULTS)
_TOOL_FAIL_ON_DEFAULTS: dict[str, dict[str, bool]] = {
    "pmd": {"fail_on_violation": False},
    "trivy": {"fail_on_critical": False, "fail_on_high": False},
}


def get_fail_on_flag(
    config: dict[str, Any],
    tool: str,
    language: str,
    flag: str | None = None,
    *,
    default: bool | None = None,
) -> bool:
    """Get the fail_on_* flag value for a tool.

    This is the canonical way to access fail_on_* values consistently.
    It handles the various naming conventions and provides correct defaults.

    Args:
        config: The effective config dict
        tool: Tool key (e.g., "bandit", "trivy", "checkstyle")
        language: Language key ("python" or "java")
        flag: Specific flag name (e.g., "fail_on_high"). If None, uses canonical mapping.
        default: Override default value. If None, uses schema-aligned defaults.

    Returns:
        True if the flag is set to fail, False otherwise.

    Examples:
        >>> get_fail_on_flag(config, "bandit", "python", "fail_on_high")
        True
        >>> get_fail_on_flag(config, "trivy", "java", "fail_on_critical")
        False
        >>> get_fail_on_flag(config, "checkstyle", "java")  # Uses canonical mapping
        True
    """
    # Get tool config
    lang_block = config.get(language, {})
    if not isinstance(lang_block, dict):
        lang_block = {}
    tools = lang_block.get("tools", {}) or {}
    tool_cfg = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(tool_cfg, bool):
        tool_cfg = {"enabled": tool_cfg}
    if not isinstance(tool_cfg, dict):
        tool_cfg = {}

    # Determine which flag key to use
    if flag is None:
        flag = _FAIL_ON_KEY_MAP.get(tool)
        if flag is None:
            # Tool not in canonical map - return default
            return default if default is not None else True

    # Get value from config, falling back to appropriate default
    value = tool_cfg.get(flag)
    if isinstance(value, bool):
        return value

    # Determine default: check tool-specific, then general, then provided default
    if default is not None:
        return default

    tool_defaults = _TOOL_FAIL_ON_DEFAULTS.get(tool, {})
    if flag in tool_defaults:
        return tool_defaults[flag]

    return _FAIL_ON_DEFAULTS.get(flag, True)


def get_fail_on_cvss(
    config: dict[str, Any],
    tool: str,
    language: str,
    *,
    default: float = 7.0,
) -> float:
    """Get the fail_on_cvss threshold for a tool.

    Args:
        config: The effective config dict
        tool: Tool key (e.g., "owasp", "trivy")
        language: Language key ("python" or "java")
        default: Default CVSS threshold (default: 7.0)

    Returns:
        CVSS threshold value (0-10). Returns 0 to disable CVSS checks.

    Examples:
        >>> get_fail_on_cvss(config, "owasp", "java")
        7.0
        >>> get_fail_on_cvss(config, "trivy", "python", default=9.0)
        9.0
    """
    lang_block = config.get(language, {})
    if not isinstance(lang_block, dict):
        return default
    tools = lang_block.get("tools", {}) or {}
    tool_cfg = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if not isinstance(tool_cfg, dict):
        return default

    value = tool_cfg.get("fail_on_cvss")
    if isinstance(value, (int, float)):
        return float(value)
    return default


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
