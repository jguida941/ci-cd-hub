"""Helpers for config input overrides."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.config.io import ConfigParseError, load_yaml_file


class ConfigInputError(ValueError):
    """Raised when config override input cannot be parsed."""


def load_config_override(
    config_json: str | None,
    config_file: str | None,
) -> dict[str, Any] | None:
    """Load a config override from JSON string or YAML/JSON file.

    Returns None when no override is provided.
    """
    if config_json and config_file:
        raise ConfigInputError("Use either --config-json or --config-file (not both)")

    if not config_json and not config_file:
        return None

    if config_json:
        try:
            payload = json.loads(config_json)
        except json.JSONDecodeError as exc:
            raise ConfigInputError(f"Invalid JSON for --config-json: {exc}") from exc
    else:
        if config_file is None:
            raise ConfigInputError("Config file path is required")
        path = Path(config_file)
        if not path.exists():
            raise ConfigInputError(f"Config file not found: {path}")
        try:
            payload = load_yaml_file(path)
        except ConfigParseError as exc:
            raise ConfigInputError(str(exc)) from exc

    if not isinstance(payload, dict):
        raise ConfigInputError("Config override must be a JSON/YAML object")

    return payload
