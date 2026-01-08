"""Java Gradle file parsing and manipulation utilities.

This module provides functions for parsing Gradle build files, detecting
missing plugins, and manipulating build.gradle content.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

from cihub.utils.paths import hub_root

# ============================================================================
# Constants
# ============================================================================

# Map of tool name to Gradle plugin ID
GRADLE_TOOL_PLUGINS = {
    "jacoco": "jacoco",
    "checkstyle": "checkstyle",
    "spotbugs": "com.github.spotbugs",
    "pmd": "pmd",
    "owasp": "org.owasp.dependencycheck",
    "pitest": "info.solidsoft.pitest",
}


# ============================================================================
# Tool Configuration
# ============================================================================


def get_gradle_tool_flags(config: dict[str, Any]) -> dict[str, bool]:
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
# Gradle Parsing
# ============================================================================


def parse_gradle_plugins(build_path: Path) -> tuple[set[str], str | None]:
    """Parse plugins from a Gradle build file.

    Returns:
        Tuple of (plugin_ids, error)
    """
    if not build_path.exists():
        return set(), f"build.gradle not found: {build_path}"

    try:
        content = build_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return set(), f"Error reading {build_path}: {exc}"

    plugins: set[str] = set()

    # Match plugins block
    plugins_block = re.search(r"plugins\s*\{([^}]*)\}", content, re.DOTALL)
    if plugins_block:
        block_content = plugins_block.group(1)
        # Match plugin declarations:
        # id 'plugin-id'
        # id 'plugin-id' version 'x.y.z'
        # id("plugin-id")
        # id("plugin-id") version "x.y.z"
        for match in re.finditer(r"id\s*[('\"]([^'\"]+)['\"]", block_content):
            plugins.add(match.group(1))

    # Also check for apply plugin syntax (legacy)
    for match in re.finditer(r"apply\s+plugin:\s*['\"]([^'\"]+)['\"]", content):
        plugins.add(match.group(1))

    return plugins, None


def find_plugins_block(content: str) -> tuple[int, int] | None:
    """Find the plugins block in Gradle content.

    Returns:
        Tuple of (start_index, end_index) or None if not found
    """
    match = re.search(r"plugins\s*\{", content)
    if not match:
        return None

    # Find matching closing brace
    start = match.end()
    depth = 1
    for i, char in enumerate(content[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return (match.start(), i + 1)

    return None


def find_insertion_point_for_config(content: str) -> int:
    """Find the best place to insert configuration blocks.

    Returns the index after the plugins block, or at the end of file.
    """
    plugins_span = find_plugins_block(content)
    if plugins_span:
        # Insert after plugins block
        end_idx = plugins_span[1]
        # Skip any trailing whitespace/newlines
        while end_idx < len(content) and content[end_idx] in " \t\n":
            end_idx += 1
        return end_idx

    # No plugins block, find after repositories or at start
    repos_match = re.search(r"repositories\s*\{[^}]*\}", content, re.DOTALL)
    if repos_match:
        end_idx = repos_match.end()
        while end_idx < len(content) and content[end_idx] in " \t\n":
            end_idx += 1
        return end_idx

    # Insert at beginning (after any comments)
    first_code = re.search(r"^\s*[^/\s*]", content, re.MULTILINE)
    return first_code.start() if first_code else 0


# ============================================================================
# Warning Collection
# ============================================================================


def collect_gradle_warnings(repo_path: Path, config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Collect warnings about missing plugins in Gradle build file.

    Returns:
        Tuple of (warnings, missing_plugin_ids)
    """
    warnings: list[str] = []
    missing_plugins: list[str] = []

    subdir = config.get("repo", {}).get("subdir") or ""
    root_path = repo_path / subdir if subdir else repo_path
    build_path = root_path / "build.gradle"

    if not build_path.exists():
        # Check for Kotlin DSL
        kotlin_path = root_path / "build.gradle.kts"
        if kotlin_path.exists():
            warnings.append("Kotlin DSL (build.gradle.kts) detected; fix-gradle only supports Groovy DSL")
            return warnings, missing_plugins
        warnings.append("build.gradle not found")
        return warnings, missing_plugins

    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "gradle":
        return warnings, missing_plugins

    declared_plugins, error = parse_gradle_plugins(build_path)
    if error:
        warnings.append(error)
        return warnings, missing_plugins

    tool_flags = get_gradle_tool_flags(config)

    for tool, enabled in tool_flags.items():
        if tool not in GRADLE_TOOL_PLUGINS or not enabled:
            continue
        plugin_id = GRADLE_TOOL_PLUGINS[tool]
        if plugin_id not in declared_plugins:
            warnings.append(f"build.gradle: missing plugin for enabled tool '{tool}' ({plugin_id})")
            missing_plugins.append(plugin_id)

    return warnings, missing_plugins


# ============================================================================
# Snippet Loading
# ============================================================================


def load_gradle_plugin_snippets() -> dict[str, str]:
    """Load plugin declaration snippets from the templates directory.

    Returns:
        Dict mapping plugin_id to plugin declaration line
    """
    snippets_path = hub_root() / "templates" / "java" / "gradle-plugins.groovy"
    if not snippets_path.exists():
        return {}

    content = snippets_path.read_text(encoding="utf-8")
    snippets: dict[str, str] = {}

    # Parse // @plugin:<plugin-id> markers
    current_plugin: str | None = None
    lines = content.splitlines()

    for line in lines:
        marker_match = re.match(r"^\s*//\s*@plugin:(.+)$", line)
        if marker_match:
            current_plugin = marker_match.group(1).strip()
            continue

        if current_plugin and line.strip().startswith("id "):
            # Found the plugin declaration line
            snippets[current_plugin] = line.strip()
            current_plugin = None

    return snippets


def load_gradle_config_snippets() -> dict[str, str]:
    """Load plugin configuration snippets from the templates directory.

    Returns:
        Dict mapping plugin_id to configuration block
    """
    snippets_path = hub_root() / "templates" / "java" / "gradle-plugins.groovy"
    if not snippets_path.exists():
        return {}

    content = snippets_path.read_text(encoding="utf-8")
    snippets: dict[str, str] = {}

    # Parse // @config:<plugin-id> markers
    current_config: str | None = None
    config_lines: list[str] = []
    lines = content.splitlines()

    for line in lines:
        marker_match = re.match(r"^\s*//\s*@config:(.+)$", line)
        if marker_match:
            # Save previous config if any
            if current_config and config_lines:
                snippets[current_config] = "\n".join(config_lines).strip()
            current_config = marker_match.group(1).strip()
            config_lines = []
            continue

        if current_config:
            # Check if we hit a new marker or end
            if line.strip().startswith("// @"):
                if config_lines:
                    snippets[current_config] = "\n".join(config_lines).strip()
                current_config = None
                config_lines = []
            elif line.strip().startswith("/*"):
                # End at comment block
                if config_lines:
                    snippets[current_config] = "\n".join(config_lines).strip()
                current_config = None
                config_lines = []
            elif line.strip() or config_lines:  # Skip leading empty lines
                config_lines.append(line)

    # Save last config
    if current_config and config_lines:
        snippets[current_config] = "\n".join(config_lines).strip()

    return snippets


# ============================================================================
# Build File Modification
# ============================================================================


def insert_plugins_into_gradle(content: str, plugin_ids: list[str], snippets: dict[str, str]) -> tuple[str, bool]:
    """Insert plugin declarations into a Gradle build file.

    Returns:
        Tuple of (updated_content, success)
    """
    if not plugin_ids:
        return content, True

    # Build plugin lines to insert
    plugin_lines = []
    for plugin_id in plugin_ids:
        if plugin_id in snippets:
            plugin_lines.append(f"    {snippets[plugin_id]}")
        else:
            # Fallback: generate basic plugin declaration
            if "." in plugin_id:
                # External plugin needs version (use placeholder)
                plugin_lines.append(f"    id '{plugin_id}' version 'FIXME'")
            else:
                # Core Gradle plugin
                plugin_lines.append(f"    id '{plugin_id}'")

    plugins_block = find_plugins_block(content)

    if plugins_block:
        # Insert into existing plugins block
        start, end = plugins_block
        # Find position just before closing brace
        insert_pos = end - 1
        # Skip whitespace before closing brace
        while insert_pos > start and content[insert_pos - 1] in " \t\n":
            insert_pos -= 1

        # Get indentation of existing plugins
        block_content = content[start:end]
        indent_match = re.search(r"\n(\s+)id\s", block_content)
        if indent_match:
            indent = indent_match.group(1)
            plugin_lines = [line.replace("    ", indent) for line in plugin_lines]

        insert_text = "\n" + "\n".join(plugin_lines)
        updated = content[:insert_pos] + insert_text + content[insert_pos:]
        return updated, True
    else:
        # Create new plugins block at the beginning
        plugins_block_text = "plugins {\n" + "\n".join(plugin_lines) + "\n}\n\n"

        # Find where to insert (after any buildscript block, before other content)
        buildscript_match = re.search(r"buildscript\s*\{", content)
        if buildscript_match:
            # Find end of buildscript block
            depth = 1
            pos = buildscript_match.end()
            while pos < len(content) and depth > 0:
                if content[pos] == "{":
                    depth += 1
                elif content[pos] == "}":
                    depth -= 1
                pos += 1
            # Skip whitespace after buildscript
            while pos < len(content) and content[pos] in " \t\n":
                pos += 1
            updated = content[:pos] + plugins_block_text + content[pos:]
        else:
            # Insert at beginning (after any leading comments)
            first_code = re.search(r"^(?!//)(?!/\*).", content, re.MULTILINE)
            if first_code:
                pos = first_code.start()
                updated = content[:pos] + plugins_block_text + content[pos:]
            else:
                updated = plugins_block_text + content

        return updated, True


def insert_configs_into_gradle(content: str, plugin_ids: list[str], snippets: dict[str, str]) -> tuple[str, bool]:
    """Insert plugin configuration blocks into a Gradle build file.

    Returns:
        Tuple of (updated_content, success)
    """
    if not plugin_ids:
        return content, True

    # Build config blocks to insert
    config_blocks = []
    for plugin_id in plugin_ids:
        if plugin_id in snippets:
            config_blocks.append(snippets[plugin_id])

    if not config_blocks:
        return content, True

    # Find insertion point
    insert_pos = find_insertion_point_for_config(content)

    # Dedent and format config blocks
    formatted_blocks = []
    for block in config_blocks:
        # Ensure consistent formatting
        block = textwrap.dedent(block).strip()
        formatted_blocks.append(block)

    config_text = "\n\n" + "\n\n".join(formatted_blocks) + "\n"

    updated = content[:insert_pos] + config_text + content[insert_pos:]
    return updated, True
