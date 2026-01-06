"""Schema loading and validation utilities for CI/CD Hub config."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from cihub.config.paths import PathConfig


def get_schema(paths: PathConfig) -> dict[str, Any]:
    """Load the CI Hub config schema.

    Args:
        paths: PathConfig instance.

    Returns:
        Parsed JSON schema as a dict.
    """
    schema_path = Path(paths.schema_dir) / "ci-hub-config.schema.json"
    with schema_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Schema at {schema_path} is not a JSON object")
    return data


def validate_config(config: dict[str, Any], paths: PathConfig) -> list[str]:
    """Validate a config dict against the CI Hub schema.

    Args:
        config: Configuration data to validate.
        paths: PathConfig instance.

    Returns:
        Sorted list of validation error strings.
    """
    schema = get_schema(paths)
    validator = Draft7Validator(schema)
    errors: list[str] = []
    for err in validator.iter_errors(config):
        path = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return sorted(errors)


# Threshold sanity check limits - warn when exceeding these
_THRESHOLD_LIMITS: dict[str, tuple[int, str]] = {
    "max_critical_vulns": (0, "Critical vulnerabilities should not be allowed (max 0)"),
    "max_high_vulns": (2, "High vulnerabilities threshold seems permissive (recommended: ≤2)"),
}


def check_threshold_sanity(config: dict[str, Any]) -> list[str]:
    """Check for permissive thresholds that may indicate misconfiguration.

    This performs sanity checks on threshold values to warn when they seem
    too permissive for production use. Does not fail validation, just warns.

    Args:
        config: Configuration data to check.

    Returns:
        List of warning strings (empty if all thresholds seem reasonable).
    """
    warnings: list[str] = []

    # Check global thresholds
    thresholds = config.get("thresholds", {})
    for key, (limit, message) in _THRESHOLD_LIMITS.items():
        value = thresholds.get(key)
        if value is not None and value > limit:
            warnings.append(f"thresholds.{key}={value}: {message}")

    # Check Java tool thresholds
    java_tools = config.get("java", {}).get("tools", {})
    owasp = java_tools.get("owasp", {})
    fail_on_cvss = owasp.get("fail_on_cvss")
    if fail_on_cvss is not None and fail_on_cvss > 9:
        warnings.append(
            f"java.tools.owasp.fail_on_cvss={fail_on_cvss}: "
            "CVSS threshold > 9 means only critical vulns fail (recommended: 7)"
        )

    # Check Python tool thresholds
    python_tools = config.get("python", {}).get("tools", {})
    pytest_cfg = python_tools.get("pytest", {})
    min_coverage = pytest_cfg.get("min_coverage")
    if min_coverage is not None and min_coverage < 50:
        warnings.append(
            f"python.tools.pytest.min_coverage={min_coverage}: Coverage threshold < 50% seems low (recommended: ≥70%)"
        )

    return warnings


def validate_config_with_sanity(
    config: dict[str, Any],
    paths: PathConfig,
) -> tuple[list[str], list[str]]:
    """Validate config and check threshold sanity.

    Args:
        config: Configuration data to validate.
        paths: PathConfig instance.

    Returns:
        Tuple of (errors, warnings).
    """
    errors = validate_config(config, paths)
    warnings = check_threshold_sanity(config)
    return errors, warnings
