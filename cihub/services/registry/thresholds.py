"""Threshold handling for registry configuration.

Provides threshold value coercion, computation, and normalization.
"""

from __future__ import annotations

from typing import Any

# All threshold fields from schema/ci-hub-config.schema.json#/definitions/thresholds
# These are the registry-managed threshold keys with their schema defaults.
_DEFAULT_THRESHOLDS: dict[str, int | float] = {
    # Coverage & Mutation
    "coverage_min": 70,
    "mutation_score_min": 70,
    # Security Vulnerabilities (vuln counts)
    "max_critical_vulns": 0,
    "max_high_vulns": 0,
    "max_pip_audit_vulns": 0,
    # CVSS Score Thresholds
    "owasp_cvss_fail": 7.0,
    "trivy_cvss_fail": 7.0,
    # SAST Findings
    "max_semgrep_findings": 0,
    # Python Linting
    "max_ruff_errors": 0,
    "max_black_issues": 0,
    "max_isort_issues": 0,
    # Java Linting/Static Analysis
    "max_checkstyle_errors": 0,
    "max_spotbugs_bugs": 0,
    "max_pmd_violations": 0,
}

# Keys that are integers vs floats (for type coercion)
_FLOAT_THRESHOLD_KEYS: frozenset[str] = frozenset({"owasp_cvss_fail", "trivy_cvss_fail"})


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


def _as_number(value: Any) -> int | float | None:
    """Coerce JSON-ish values to int or float, returning None if not coercible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return None
    return None


def _get_threshold_value(
    overrides: dict[str, Any],
    tier_defaults: dict[str, Any],
    *,
    key: str,
) -> int | float:
    """Get effective threshold value from overrides/tier defaults with legacy support.

    Handles both integer thresholds and float CVSS thresholds.
    """
    legacy_key: str | None = None
    if key == "coverage_min":
        legacy_key = "coverage"
    elif key == "mutation_score_min":
        legacy_key = "mutation"
    elif key in ("max_critical_vulns", "max_high_vulns"):
        legacy_key = "vulns_max"

    # Use float-aware coercion for CVSS thresholds
    coerce = _as_number if key in _FLOAT_THRESHOLD_KEYS else _as_int

    # Overrides win
    val = coerce(overrides.get(key))
    if val is not None:
        return val
    if legacy_key:
        legacy_val = coerce(overrides.get(legacy_key))
        if legacy_val is not None:
            return legacy_val

    # Then tier defaults
    val = coerce(tier_defaults.get(key))
    if val is not None:
        return val
    if legacy_key:
        legacy_val = coerce(tier_defaults.get(legacy_key))
        if legacy_val is not None:
            return legacy_val

    # Fall back to schema defaults
    return _DEFAULT_THRESHOLDS[key]


def _compute_all_effective_thresholds(
    overrides: dict[str, Any],
    tier_defaults: dict[str, Any],
) -> dict[str, int | float]:
    """Compute effective values for all threshold fields.

    Returns a dict with all 14 threshold keys and their effective values.
    """
    return {key: _get_threshold_value(overrides, tier_defaults, key=key) for key in _DEFAULT_THRESHOLDS}


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
