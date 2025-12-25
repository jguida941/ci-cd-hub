"""Path configuration for CI/CD Hub."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
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
        """Return the path for a specific repo config file."""
        return os.path.join(self.repos_dir, f"{repo}.yaml")

    def profile_file(self, profile: str) -> str:
        """Return the path for a specific profile file."""
        return os.path.join(self.profiles_dir, f"{profile}.yaml")
