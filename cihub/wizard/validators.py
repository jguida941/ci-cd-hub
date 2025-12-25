"""Input validators for wizard prompts."""

from __future__ import annotations

import re

SEMVER_RE = re.compile(r"^\d+(?:\.\d+){0,2}$")
PACKAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
REPO_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_percentage(value: str) -> bool | str:
    """Validate a 0-100 integer percentage."""
    try:
        parsed = int(value)
    except ValueError:
        return "Enter a whole number (0-100)."
    if 0 <= parsed <= 100:
        return True
    return "Enter a value between 0 and 100."


def validate_version(value: str) -> bool | str:
    """Validate a simple semver-ish version string."""
    if SEMVER_RE.match(value):
        return True
    return "Enter a version like 3, 3.11, or 3.11.2."


def validate_package_name(value: str) -> bool | str:
    """Validate a package name string."""
    if PACKAGE_RE.match(value):
        return True
    return "Use letters, numbers, ., -, or _."


def validate_repo_name(value: str) -> bool | str:
    """Validate a repo name string."""
    if REPO_RE.match(value):
        return True
    return "Use letters, numbers, ., -, or _."
