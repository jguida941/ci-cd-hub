"""Environment variable utilities."""

from __future__ import annotations

import os
from typing import Mapping


def _parse_env_bool(value: str | None) -> bool | None:
    """Parse a string as a boolean, returning None if not recognized.

    Accepts: true/false, 1/0, yes/no, y/n, on/off (case-insensitive).
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def env_bool(name: str, default: bool = False, env: Mapping[str, str] | None = None) -> bool:
    """Read a boolean environment variable with a fallback default."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    parsed = _parse_env_bool(env_map.get(name))
    return default if parsed is None else parsed


def env_str(name: str, default: str | None = None, env: Mapping[str, str] | None = None) -> str | None:
    """Read a string environment variable with a fallback default."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    value = env_map.get(name)
    if value is None:
        return default
    return value
