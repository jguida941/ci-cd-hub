#!/usr/bin/env python3
"""Bootstrap script for installing cihub in CI environments.

This script reads .ci-hub.yml and installs cihub from the configured source.
It's designed to be curled and piped to python:

    curl -sSL https://raw.githubusercontent.com/OWNER/REPO/REF/scripts/install.py | python

The script reads install configuration from .ci-hub.yml:

    install:
      source: pypi  # Options: pypi, git, local

Environment variables (override config):
    CIHUB_INSTALL_SOURCE: pypi, git, or local
    CIHUB_HUB_REPO: owner/repo (for git/local installs)
    CIHUB_HUB_REF: branch/tag/sha (for git/local installs)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def load_config() -> dict:
    """Load .ci-hub.yml if it exists."""
    config_path = Path(".ci-hub.yml")
    if not config_path.exists():
        return {}

    try:
        # Try to use PyYAML if available
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback: simple YAML parsing for install.source
        content = config_path.read_text()
        config = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("source:"):
                value = line.split(":", 1)[1].strip().strip("'\"")
                config["install"] = {"source": value}
                break
        return config


def get_install_source(config: dict) -> str:
    """Get install source from env var or config."""
    # Environment variable takes precedence
    env_source = os.environ.get("CIHUB_INSTALL_SOURCE", "").lower()
    if env_source in ("pypi", "git", "local"):
        return env_source

    # Fall back to config
    install_config = config.get("install", {})
    if isinstance(install_config, dict):
        source = install_config.get("source", "git")
        if source in ("pypi", "git", "local"):
            return source

    # Default to git (PyPI package doesn't include schema/config/templates yet)
    return "git"


def get_hub_repo() -> str:
    """Get hub repo from env var or default."""
    return os.environ.get("CIHUB_HUB_REPO", "jguida941/ci-cd-hub")


def get_hub_ref() -> str:
    """Get hub ref from env var or default."""
    return os.environ.get("CIHUB_HUB_REF", "main")


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and optionally check for errors."""
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, check=check)  # noqa: S603


def install_from_pypi() -> int:
    """Install cihub from PyPI."""
    print("Installing cihub from PyPI...", file=sys.stderr)
    result = run_command([sys.executable, "-m", "pip", "install", "cihub[ci]"], check=False)
    return result.returncode


def install_from_git() -> int:
    """Install cihub from git repository."""
    hub_repo = get_hub_repo()
    hub_ref = get_hub_ref()
    git_url = f"git+https://github.com/{hub_repo}.git@{hub_ref}#egg=cihub[ci]"

    print(f"Installing cihub from git: {hub_repo}@{hub_ref}...", file=sys.stderr)
    result = run_command([sys.executable, "-m", "pip", "install", git_url], check=False)
    return result.returncode


def install_from_local() -> int:
    """Install cihub from local checkout (editable)."""
    hub_repo = get_hub_repo()
    hub_ref = get_hub_ref()
    hub_dir = Path("/tmp/cihub-hub")  # noqa: S108

    print(f"Installing cihub from local checkout: {hub_repo}@{hub_ref}...", file=sys.stderr)

    # Clone or update the hub repo to /tmp (outside workspace)
    if hub_dir.exists():
        # Update existing checkout
        run_command(["git", "-C", str(hub_dir), "fetch", "origin"], check=False)
        run_command(["git", "-C", str(hub_dir), "checkout", hub_ref], check=False)
        run_command(["git", "-C", str(hub_dir), "pull", "--ff-only"], check=False)
    else:
        # Fresh clone
        result = run_command([
            "git", "clone", "--depth", "1", "--branch", hub_ref,
            f"https://github.com/{hub_repo}.git", str(hub_dir)
        ], check=False)
        if result.returncode != 0:
            # Branch might not exist, try without --branch
            run_command([
                "git", "clone", f"https://github.com/{hub_repo}.git", str(hub_dir)
            ], check=False)
            run_command(["git", "-C", str(hub_dir), "checkout", hub_ref], check=False)

    # Install editable
    result = run_command([sys.executable, "-m", "pip", "install", "-e", f"{hub_dir}[ci]"], check=False)
    return result.returncode


def main() -> int:
    """Main entry point."""
    print("=== cihub bootstrap installer ===", file=sys.stderr)

    config = load_config()
    source = get_install_source(config)

    print(f"Install source: {source}", file=sys.stderr)

    if source == "pypi":
        return install_from_pypi()
    elif source == "git":
        return install_from_git()
    elif source == "local":
        return install_from_local()
    else:
        print(f"Unknown install source: {source}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
