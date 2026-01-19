"""Project detection utilities.

This module provides utilities for detecting project characteristics:
- Repository name resolution from config, environment, or git remote
- Java project type detection (Maven single/multi-module, Gradle)

These functions are used across multiple modules (ci_engine, report commands)
and are consolidated here to avoid duplication.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from cihub.utils.git import get_git_remote, parse_repo_from_remote
from cihub.utils.github_context import GitHubContext


def get_repo_name(config: dict[str, Any], repo_path: Path) -> str:
    """Resolve repository name from environment, config, or git remote.

    Resolution order:
    1. GITHUB_REPOSITORY environment variable (e.g., "owner/repo")
    2. Config repo.owner and repo.name fields
    3. Git remote URL parsing

    Args:
        config: Configuration dictionary with optional repo.owner/repo.name
        repo_path: Path to the repository root

    Returns:
        Repository name in "owner/repo" format, or empty string if not found
    """
    # 1. Environment variable (GitHub Actions)
    ctx = GitHubContext.from_env()
    if ctx.repository:
        return ctx.repository

    # 2. Config file
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    owner = repo_info.get("owner")
    name = repo_info.get("name")
    if owner and name:
        return f"{owner}/{name}"

    # 3. Git remote
    remote = get_git_remote(repo_path)
    if remote:
        parsed = parse_repo_from_remote(remote)
        if parsed[0] and parsed[1]:
            return f"{parsed[0]}/{parsed[1]}"

    return ""


def detect_java_project_type(workdir: Path) -> str:
    """Detect Java project type based on build system files.

    Examines the directory for Maven (pom.xml) or Gradle (build.gradle)
    files and determines if it's a single or multi-module project.

    Args:
        workdir: Path to the Java project directory

    Returns:
        One of:
        - "Multi-module (N modules)" for Maven with <modules> section
        - "Multi-module" for Gradle with settings.gradle
        - "Single module" for single-module Maven or Gradle
        - "Unknown" if no build system detected
    """
    # Check Maven
    pom = workdir / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "<modules>" in content:
            modules = len(re.findall(r"<module>.*?</module>", content))
            return f"Multi-module ({modules} modules)" if modules else "Multi-module"
        return "Single module"

    # Check Gradle
    settings_gradle = workdir / "settings.gradle"
    settings_kts = workdir / "settings.gradle.kts"
    if settings_gradle.exists() or settings_kts.exists():
        return "Multi-module"
    if (workdir / "build.gradle").exists() or (workdir / "build.gradle.kts").exists():
        return "Single module"

    return "Unknown"


# Backward compatibility aliases with underscore prefix
# These match the original function names used in helper modules
_get_repo_name = get_repo_name
_detect_java_project_type = detect_java_project_type
