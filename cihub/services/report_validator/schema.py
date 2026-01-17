"""JSON Schema validation for CI reports.

This module handles validation of CI reports against the JSON schema definition.
The schema is loaded from cihub/data/schema/ci-report.v2.json.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema

from cihub.utils.paths import hub_root

# Path to the JSON schema file (uses hub_root() for PyPI compatibility)
_SCHEMA_PATH = hub_root() / "schema" / "ci-report.v2.json"
_SCHEMA_CACHE: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    """Load and cache the JSON schema.

    Returns:
        The parsed JSON schema dictionary.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        json.JSONDecodeError: If schema file contains invalid JSON.
    """
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        with _SCHEMA_PATH.open(encoding="utf-8") as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


def validate_against_schema(report: dict[str, Any]) -> list[str]:
    """Validate report against JSON schema.

    Args:
        report: Report dict to validate.

    Returns:
        List of schema validation errors (empty if valid).
    """
    schema = _load_schema()
    errors: list[str] = []

    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(report):
        # Format error path for clarity
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"Schema error at '{path}': {error.message}")

    return errors
