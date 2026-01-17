"""POM policy/rules evaluation.

This module evaluates POM files against CI configuration requirements,
detecting missing plugins and dependencies based on enabled tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .parse import (
    JAVA_TOOL_DEPENDENCIES,
    JAVA_TOOL_PLUGINS,
    dependency_matches,
    parse_pom_dependencies,
    parse_pom_modules,
    parse_pom_plugins,
    plugin_matches,
)

# ============================================================================
# Tool Configuration
# ============================================================================


def get_java_tool_flags(config: dict[str, Any]) -> dict[str, bool]:
    """Get enabled status for Java tools per ADR-0017 defaults."""
    tools = config.get("java", {}).get("tools", {})
    # Defaults per ADR-0017: Core tools enabled, expensive tools disabled
    defaults = {
        "jacoco": True,
        "checkstyle": True,
        "spotbugs": True,
        "pmd": True,
        "owasp": True,
        "pitest": True,
        "jqwik": False,  # opt-in
        "semgrep": False,  # expensive
        "trivy": False,  # expensive
        "codeql": False,  # expensive
        "docker": False,  # requires Dockerfile
    }
    enabled: dict[str, bool] = {}
    for tool, default in defaults.items():
        enabled[tool] = tools.get(tool, {}).get("enabled", default)
    return enabled


# ============================================================================
# Warning Collection
# ============================================================================


def collect_java_pom_warnings(repo_path: Path, config: dict[str, Any]) -> tuple[list[str], list[tuple[str, str]]]:
    """Collect warnings about missing plugins in POM file.

    Returns:
        Tuple of (warnings, missing_plugins)
    """
    warnings: list[str] = []
    missing_plugins: list[tuple[str, str]] = []

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path

    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "maven":
        return warnings, missing_plugins

    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        warnings.append("pom.xml not found")
        return warnings, missing_plugins

    plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom_path)
    if error:
        warnings.append(error)
        return warnings, missing_plugins

    tool_flags = get_java_tool_flags(config)
    checkstyle_config = config.get("java", {}).get("tools", {}).get("checkstyle", {}).get("config_file")
    if checkstyle_config:
        config_path = repo_path / checkstyle_config
        if not config_path.exists():
            alt_path = root_path / checkstyle_config
            if not alt_path.exists():
                warnings.append(f"checkstyle config file not found: {checkstyle_config}")
    for tool, enabled in tool_flags.items():
        if tool not in JAVA_TOOL_PLUGINS or not enabled:
            continue
        group_id, artifact_id = JAVA_TOOL_PLUGINS[tool]
        if plugin_matches(plugins, group_id, artifact_id):
            continue
        if plugin_matches(plugins_mgmt, group_id, artifact_id):
            warnings.append(f"pom.xml: {tool} plugin is only in <pluginManagement>; move to <build><plugins>")
        else:
            warnings.append(f"pom.xml: missing plugin for enabled tool '{tool}' ({group_id}:{artifact_id})")
        missing_plugins.append((group_id, artifact_id))

    if has_modules and missing_plugins:
        warnings.append("pom.xml: multi-module project detected; add plugins to parent <build><plugins>")

    return warnings, missing_plugins


def collect_java_dependency_warnings(
    repo_path: Path, config: dict[str, Any]
) -> tuple[list[str], list[tuple[Path, tuple[str, str]]]]:
    """Collect warnings about missing dependencies in POM files.

    Returns:
        Tuple of (warnings, missing)
    """
    warnings: list[str] = []
    missing: list[tuple[Path, tuple[str, str]]] = []

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "maven":
        return warnings, missing

    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        return warnings, missing

    modules, error = parse_pom_modules(pom_path)
    if error:
        warnings.append(error)
        return warnings, missing

    targets: list[Path] = []
    if modules:
        for module in modules:
            # Validate module path doesn't escape root (path traversal protection)
            if ".." in module or module.startswith("/") or "\\" in module:
                warnings.append(f"Invalid module path (traversal blocked): {module}")
                continue
            module_pom = root_path / module / "pom.xml"
            # Double-check resolved path is within root_path
            try:
                module_pom.resolve().relative_to(root_path.resolve())
            except ValueError:
                warnings.append(f"Module path escapes root directory: {module}")
                continue
            if module_pom.exists():
                targets.append(module_pom)
            else:
                warnings.append(f"pom.xml not found for module: {module}")
    else:
        targets.append(pom_path)

    tool_flags = get_java_tool_flags(config)
    for tool, dep in JAVA_TOOL_DEPENDENCIES.items():
        if not tool_flags.get(tool, False):
            continue
        group_id, artifact_id = dep
        for target in targets:
            deps, deps_mgmt, error = parse_pom_dependencies(target)
            if error:
                warnings.append(f"{target}: {error}")
                continue
            if dependency_matches(deps, group_id, artifact_id):
                continue
            if dependency_matches(deps_mgmt, group_id, artifact_id):
                warnings.append(f"{target}: {tool} dependency only in <dependencyManagement>; add to <dependencies>")
            else:
                warnings.append(f"{target}: missing dependency for enabled tool '{tool}' ({group_id}:{artifact_id})")
            missing.append((target, (group_id, artifact_id)))

    return warnings, missing
