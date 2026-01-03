"""Environment variable utilities."""

from __future__ import annotations


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
