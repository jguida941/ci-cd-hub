"""Config policy helpers for init/update."""

from __future__ import annotations

from typing import Any


def _config_requires_git_install(config: dict[str, Any]) -> bool:
    repo_cfg = config.get("repo") if isinstance(config.get("repo"), dict) else {}
    targets = repo_cfg.get("targets")
    if isinstance(targets, list) and targets:
        return True

    python_cfg = config.get("python") if isinstance(config.get("python"), dict) else {}
    tools_cfg = python_cfg.get("tools") if isinstance(python_cfg.get("tools"), dict) else {}
    pytest_cfg = tools_cfg.get("pytest")
    if isinstance(pytest_cfg, dict):
        if pytest_cfg.get("args") or pytest_cfg.get("env"):
            return True

    return False


def ensure_git_install_source(config: dict[str, Any], install_from: str | None = None) -> bool:
    """Force install.source=git when config needs features not yet in PyPI."""
    if install_from and install_from != "pypi":
        return False
    if not _config_requires_git_install(config):
        return False

    install_cfg = config.get("install")
    if isinstance(install_cfg, dict):
        if install_cfg.get("source") == "git":
            return False
        install_cfg["source"] = "git"
        config["install"] = install_cfg
        return True
    if isinstance(install_cfg, str):
        if install_cfg == "git":
            return False
    config["install"] = {"source": "git"}
    return True
