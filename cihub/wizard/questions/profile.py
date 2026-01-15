"""Profile selection wizard questions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import questionary
import yaml

from cihub.wizard.styles import get_style

if TYPE_CHECKING:
    from pathlib import Path


# Fallback profile metadata for profiles that don't have _metadata in YAML
# New profiles should define _metadata in their YAML files instead
_FALLBACK_PROFILE_INFO: dict[str, dict[str, str]] = {
    "fast": {
        "description": "Quick CI with essential tools",
        "tools": "pytest, ruff, black, bandit, pip-audit",
        "runtime": "~5 min",
    },
    "quality": {
        "description": "Full quality checks with mutation testing",
        "tools": "fast + mypy, mutmut",
        "runtime": "~20 min",
    },
    "security": {
        "description": "Security-focused scanning",
        "tools": "bandit, pip-audit, semgrep, trivy, codeql",
        "runtime": "~30 min",
    },
    "minimal": {
        "description": "Bare minimum CI",
        "tools": "pytest, ruff",
        "runtime": "~2 min",
    },
    "compliance": {
        "description": "Strict compliance requirements",
        "tools": "security + stricter thresholds",
        "runtime": "~30 min",
    },
    "coverage-gate": {
        "description": "High coverage/mutation requirements",
        "tools": "quality + higher thresholds",
        "runtime": "~25 min",
    },
}

# Backward-compatible alias for tests and legacy code
# New code should use get_profile_info() which reads from YAML _metadata sections
PROFILE_INFO = _FALLBACK_PROFILE_INFO


def _load_profile_metadata(profile_path: "Path") -> dict[str, str]:
    """Load metadata from a profile YAML file.

    Looks for a _metadata section in the profile file. Falls back to
    _FALLBACK_PROFILE_INFO for backward compatibility.

    Args:
        profile_path: Path to the profile YAML file

    Returns:
        Dict with description, tools, runtime keys
    """
    try:
        with open(profile_path, encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
        if "_metadata" in content and isinstance(content["_metadata"], dict):
            return content["_metadata"]
    except (OSError, yaml.YAMLError):
        pass
    return {}


def get_profile_info(name: str, profile_path: "Path | None" = None) -> dict[str, str]:
    """Get profile metadata (description, tools, runtime).

    Sources metadata from profile YAML _metadata section first,
    then falls back to _FALLBACK_PROFILE_INFO for known profiles.

    Args:
        name: Profile base name (e.g., 'fast', 'quality')
        profile_path: Optional path to the profile YAML file

    Returns:
        Dict with description, tools, runtime keys
    """
    # Try to load from YAML _metadata section first (CLI as source of truth)
    if profile_path is not None:
        metadata = _load_profile_metadata(profile_path)
        if metadata:
            return metadata

    # Fall back to known profiles
    return _FALLBACK_PROFILE_INFO.get(name, {})


def get_available_profiles(language: str, profiles_dir: Path | None = None) -> list[str]:
    """Get list of available profiles for a language.

    Scans profiles directory to find actual profiles (CLI source of truth).

    Args:
        language: 'python' or 'java'
        profiles_dir: Optional path to profiles directory

    Returns:
        List of profile base names (without language prefix)
    """
    if profiles_dir is None:
        from cihub.utils.paths import hub_root

        profiles_dir = hub_root() / "templates" / "profiles"

    # Scan directory for actual profiles instead of hard-coded list
    profiles = []
    prefix = f"{language}-"
    if profiles_dir.exists():
        for profile_file in profiles_dir.glob(f"{prefix}*.yaml"):
            # Extract profile name from filename (e.g., python-fast.yaml -> fast)
            name = profile_file.stem[len(prefix) :]
            # Skip tier profiles (those are threshold-only, not tool profiles)
            if name.startswith("tier-"):
                continue
            profiles.append(name)

    # Sort with recommended profiles first
    priority = {"fast": 0, "quality": 1, "security": 2, "minimal": 3, "compliance": 4, "coverage-gate": 5}
    profiles.sort(key=lambda p: (priority.get(p, 100), p))

    return profiles


def select_profile(
    language: str,
    *,
    profiles_dir: "Path | None" = None,
    allow_skip: bool = True,
) -> str | None:
    """Prompt user to select a CI profile.

    Args:
        language: 'python' or 'java'
        profiles_dir: Optional path to profiles directory
        allow_skip: Whether to allow skipping profile selection

    Returns:
        Profile name (e.g., 'fast') or None if skipped/cancelled
    """

    if profiles_dir is None:
        from cihub.utils.paths import hub_root

        profiles_dir = hub_root() / "templates" / "profiles"

    available = get_available_profiles(language, profiles_dir)

    if not available:
        return None

    # Build choices with descriptions (load metadata from files)
    choices: list[dict[str, str | None]] = []
    prefix = f"{language}-"

    # Recommended first
    if "fast" in available:
        profile_path = profiles_dir / f"{prefix}fast.yaml"
        info = get_profile_info("fast", profile_path)
        choices.append(
            {
                "name": f"Fast (Recommended) - {info.get('description', '')} ({info.get('runtime', '')})",
                "value": "fast",
            }
        )

    # Other profiles
    for name in available:
        if name == "fast":
            continue
        profile_path = profiles_dir / f"{prefix}{name}.yaml"
        info = get_profile_info(name, profile_path)
        display = f"{name.title()} - {info.get('description', '')} ({info.get('runtime', '')})"
        choices.append({"name": display, "value": name})

    if allow_skip:
        choices.append(
            {
                "name": "Start from scratch - Configure each tool individually",
                "value": None,
            }
        )

    result = questionary.select(
        "Select a CI profile (determines default tool selection):",
        choices=choices,
        style=get_style(),
    ).ask()

    return result if result is None else str(result)


def select_tier() -> str:
    """Prompt user to select a quality tier.

    Returns:
        Tier name: 'strict', 'standard', or 'relaxed'
    """
    choices = [
        {
            "name": "Standard (Recommended) - Balanced quality gates (coverage 70%, mutation 70%)",
            "value": "standard",
        },
        {
            "name": "Strict - High quality requirements (coverage 85%, mutation 80%, zero vulns)",
            "value": "strict",
        },
        {
            "name": "Relaxed - Permissive for legacy codebases (coverage 50%, mutation 40%)",
            "value": "relaxed",
        },
    ]

    result = questionary.select(
        "Select a quality tier (determines threshold defaults):",
        choices=choices,
        style=get_style(),
    ).ask()

    return result or "standard"
