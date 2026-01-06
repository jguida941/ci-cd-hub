"""Path configuration for CI/CD Hub."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _validate_name(name: str, kind: str, *, allow_slash: bool = False) -> str:
    """Validate a name doesn't contain path traversal sequences.

    Args:
        name: The name to validate (repo name, profile name, etc.)
        kind: Description for error messages (e.g., "repo", "profile")
        allow_slash: If True, allow forward slashes (for "owner/repo" format)

    Returns:
        The validated name.

    Raises:
        ValueError: If the name contains path traversal sequences.
    """
    # Always block parent directory traversal and backslashes
    if ".." in name or "\\" in name:
        raise ValueError(f"Invalid {kind} name: {name!r} (path traversal not allowed)")
    # Block leading slash (absolute path) and slash unless explicitly allowed
    if name.startswith("/"):
        raise ValueError(f"Invalid {kind} name: {name!r} (path traversal not allowed)")
    if "/" in name and not allow_slash:
        raise ValueError(f"Invalid {kind} name: {name!r} (path traversal not allowed)")
    return name


@dataclass(frozen=True, slots=True)
class PathConfig:
    """Configuration paths for CI Hub."""

    root: str

    @property
    def config_dir(self) -> str:
        """Return the config directory path."""
        return os.path.join(self.root, "config")

    @property
    def repos_dir(self) -> str:
        """Return the repos config directory path."""
        return os.path.join(self.config_dir, "repos")

    @property
    def defaults_file(self) -> str:
        """Return the defaults.yaml file path."""
        return os.path.join(self.config_dir, "defaults.yaml")

    @property
    def profiles_dir(self) -> str:
        """Return the profiles directory path."""
        return os.path.join(self.root, "templates", "profiles")

    @property
    def schema_dir(self) -> str:
        """Return the schema directory path."""
        return os.path.join(self.root, "schema")

    def repo_file(self, repo: str) -> str:
        """Return the path for a specific repo config file.

        Args:
            repo: Repository name (without .yaml extension).
                  Can be in "owner/repo" format (creates subdirectory).

        Returns:
            Path to the repo config file.

        Raises:
            ValueError: If repo name contains path traversal sequences.
        """
        # Repos can be "owner/repo" format, so allow slash but block traversal
        _validate_name(repo, "repo", allow_slash=True)
        return os.path.join(self.repos_dir, f"{repo}.yaml")

    def profile_file(self, profile: str) -> str:
        """Return the path for a specific profile file.

        Args:
            profile: Profile name (without .yaml extension).

        Returns:
            Path to the profile file.

        Raises:
            ValueError: If profile name contains path traversal sequences.
        """
        _validate_name(profile, "profile")
        return os.path.join(self.profiles_dir, f"{profile}.yaml")
