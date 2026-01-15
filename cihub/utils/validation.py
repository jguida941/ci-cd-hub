"""Common validation functions for CLI commands."""

from __future__ import annotations

import re

# Pattern for valid profile names (alphanumeric, hyphens, underscores)
_PROFILE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_profile_name(name: str) -> str | None:
    """Validate profile name to prevent path traversal.

    Returns error message if invalid, None if valid.
    """
    if not name:
        return "Profile name cannot be empty"
    if "/" in name or "\\" in name:
        return "Profile name cannot contain path separators"
    if ".." in name:
        return "Profile name cannot contain '..'"
    if name.startswith("."):
        return "Profile name cannot start with '.'"
    # Only allow alphanumeric, dash, underscore
    if not _PROFILE_NAME_PATTERN.match(name):
        return "Profile name can only contain letters, numbers, dashes, and underscores"
    return None
