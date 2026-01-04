"""Config loading for cihub ci commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cihub.config.fallbacks import FALLBACK_DEFAULTS  # noqa: F401 - re-export
from cihub.config.loader import load_config
from cihub.utils.paths import hub_root


def load_ci_config(repo_path: Path) -> dict[str, Any]:
    local_path = repo_path / ".ci-hub.yml"
    if not local_path.exists():
        raise FileNotFoundError(f"Missing .ci-hub.yml in {repo_path}")
    config = load_config(
        repo_name=repo_path.name,
        hub_root=hub_root(),
        repo_config_path=local_path,
        exit_on_validation_error=False,
    )
    config.pop("_meta", None)
    return config


def load_hub_config(config_basename: str, repo_path: Path | None = None) -> dict[str, Any]:
    """Load config from hub's config/repos/<basename>.yaml.

    This is used by hub-run-all.yml to load config from the hub instead of
    the target repo's .ci-hub.yml. Optionally merges in repo's .ci-hub.yml
    with lower priority (hub config takes precedence for protected keys).

    Args:
        config_basename: Base name of the config file (e.g., 'fixtures-java-maven-pass')
        repo_path: Optional path to target repo for merging its .ci-hub.yml
    """
    hub = hub_root()
    hub_config_path = hub / "config" / "repos" / f"{config_basename}.yaml"
    if not hub_config_path.exists():
        raise FileNotFoundError(f"Hub config not found: {hub_config_path}")
    repo_config_path = None
    if repo_path:
        local_path = repo_path / ".ci-hub.yml"
        if local_path.exists():
            repo_config_path = local_path
    config = load_config(
        repo_name=config_basename,
        hub_root=hub,
        repo_config_path=repo_config_path,
        exit_on_validation_error=False,
    )
    config.pop("_meta", None)
    return config
