"""Helpers for reading hub config/repos metadata."""

from __future__ import annotations

import sys

from cihub.config.io import load_yaml_file
from cihub.utils.paths import hub_root


def get_connected_repos(
    only_dispatch_enabled: bool = True,
    language_filter: str | None = None,
) -> list[str]:
    """Get unique repos from hub config/repos/*.yaml."""
    repos_dir = hub_root() / "config" / "repos"
    seen: set[str] = set()
    repos: list[str] = []
    for cfg_file in repos_dir.rglob("*.yaml"):
        if cfg_file.name.endswith(".disabled"):
            continue
        try:
            data = load_yaml_file(cfg_file)
            repo = data.get("repo", {})
            if only_dispatch_enabled and repo.get("dispatch_enabled", True) is False:
                continue
            if language_filter:
                repo_lang = repo.get("language", "")
                if repo_lang != language_filter:
                    continue
            owner = repo.get("owner", "")
            name = repo.get("name", "")
            if owner and name:
                full = f"{owner}/{name}"
                if full not in seen:
                    seen.add(full)
                    repos.append(full)
        except Exception as exc:
            print(f"Warning: failed to read {cfg_file}: {exc}", file=sys.stderr)
    return repos


def get_repo_entries(
    only_dispatch_enabled: bool = True,
) -> list[dict[str, str]]:
    """Return repo metadata from config/repos/*.yaml."""
    repos_dir = hub_root() / "config" / "repos"
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for cfg_file in repos_dir.rglob("*.yaml"):
        if cfg_file.name.endswith(".disabled"):
            continue
        try:
            data = load_yaml_file(cfg_file)
            repo = data.get("repo", {})
            if only_dispatch_enabled and repo.get("dispatch_enabled", True) is False:
                continue
            owner = repo.get("owner", "")
            name = repo.get("name", "")
            if not owner or not name:
                continue
            full = f"{owner}/{name}"
            dispatch_workflow = repo.get("dispatch_workflow") or "hub-ci.yml"
            # Deduplicate by (repo, dispatch_workflow) to allow syncing
            # multiple workflow files for repos with both Java and Python configs
            key = f"{full}:{dispatch_workflow}"
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "full": full,
                    "language": repo.get("language", ""),
                    "dispatch_workflow": dispatch_workflow,
                    "default_branch": repo.get("default_branch", "main"),
                }
            )
        except Exception as exc:
            print(f"Warning: failed to read {cfg_file}: {exc}", file=sys.stderr)
            continue
    return entries
