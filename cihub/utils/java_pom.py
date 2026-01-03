"""Java POM file parsing and manipulation utilities.

This module provides functions for parsing Maven POM files, detecting
missing plugins/dependencies, and manipulating POM content.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # Secure XML parsing (prevents XXE)

from cihub.utils.paths import hub_root

# ============================================================================
# Constants
# ============================================================================

JAVA_TOOL_PLUGINS = {
    "jacoco": ("org.jacoco", "jacoco-maven-plugin"),
    "checkstyle": ("org.apache.maven.plugins", "maven-checkstyle-plugin"),
    "spotbugs": ("com.github.spotbugs", "spotbugs-maven-plugin"),
    "pmd": ("org.apache.maven.plugins", "maven-pmd-plugin"),
    "owasp": ("org.owasp", "dependency-check-maven"),
    "pitest": ("org.pitest", "pitest-maven"),
}

JAVA_TOOL_DEPENDENCIES = {
    "jqwik": ("net.jqwik", "jqwik"),
}


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
# XML Helpers
# ============================================================================


def get_xml_namespace(root: ET.Element) -> str:
    """Extract the XML namespace from an element's tag."""
    tag = root.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}")[0][1:]
    return ""


def ns_tag(namespace: str, tag: str) -> str:
    """Create a namespaced tag for ElementTree queries."""
    if not namespace:
        return tag
    return f"{{{namespace}}}{tag}"


def elem_text(elem: ET.Element | None) -> str:
    """Safely extract text from an XML element."""
    if elem is None:
        return ""
    text = elem.text
    if not isinstance(text, str):
        return ""
    return text.strip()


def parse_xml_text(text: str) -> ET.Element:
    """Parse XML text securely (prevents XXE attacks)."""
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("disallowed DTD")
    return ET.fromstring(text)


def parse_xml_file(path: Path) -> ET.Element:
    """Parse an XML file securely."""
    return parse_xml_text(path.read_text(encoding="utf-8"))


# ============================================================================
# String/Text Helpers
# ============================================================================


def line_indent(text: str, index: int) -> str:
    """Get the indentation of the line containing the given index."""
    line_start = text.rfind("\n", 0, index) + 1
    match = re.match(r"[ \t]*", text[line_start:])
    return match.group(0) if match else ""


def indent_block(block: str, indent: str) -> str:
    """Indent a block of text with the given prefix."""
    block = textwrap.dedent(block).strip("\n")
    lines = block.splitlines()
    return "\n".join((indent + line) if line.strip() else line for line in lines)


def find_tag_spans(text: str, tag: str) -> list[tuple[int, int]]:
    """Find all spans of a given XML tag in text."""
    spans: list[tuple[int, int]] = []
    for match in re.finditer(rf"<{tag}[^>]*>", text):
        close = text.find(f"</{tag}>", match.end())
        if close == -1:
            continue
        spans.append((match.start(), close + len(f"</{tag}>")))
    return spans


# ============================================================================
# POM Parsing
# ============================================================================


def parse_pom_plugins(
    pom_path: Path,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], bool, str | None]:
    """Parse plugins from a POM file.

    Returns:
        Tuple of (plugins, plugins_mgmt, has_modules, error)
    """
    try:
        root = parse_xml_file(pom_path)
    except (ET.ParseError, ValueError) as exc:
        return set(), set(), False, f"Invalid pom.xml: {exc}"

    namespace = get_xml_namespace(root)

    def find_child(parent: ET.Element | None, tag: str) -> ET.Element | None:
        if parent is None:
            return None
        return parent.find(ns_tag(namespace, tag))

    def plugin_ids(parent: ET.Element | None) -> set[tuple[str, str]]:
        ids: set[tuple[str, str]] = set()
        if parent is None:
            return ids
        for plugin in parent.findall(ns_tag(namespace, "plugin")):
            group_id = elem_text(plugin.find(ns_tag(namespace, "groupId")))
            artifact_id = elem_text(plugin.find(ns_tag(namespace, "artifactId")))
            if artifact_id:
                ids.add((group_id, artifact_id))
        return ids

    build = find_child(root, "build")
    plugins = plugin_ids(find_child(build, "plugins"))

    plugin_mgmt = find_child(build, "pluginManagement")
    plugins_mgmt = plugin_ids(find_child(plugin_mgmt, "plugins"))

    has_modules = find_child(root, "modules") is not None
    return plugins, plugins_mgmt, has_modules, None


def parse_pom_modules(pom_path: Path) -> tuple[list[str], str | None]:
    """Parse module list from a POM file.

    Returns:
        Tuple of (modules, error)
    """
    try:
        root = parse_xml_file(pom_path)
    except (ET.ParseError, ValueError) as exc:
        return [], f"Invalid pom.xml: {exc}"

    namespace = get_xml_namespace(root)
    modules_elem = root.find(ns_tag(namespace, "modules"))
    modules: list[str] = []
    if modules_elem is None:
        return modules, None
    for module in modules_elem.findall(ns_tag(namespace, "module")):
        if module.text:
            modules.append(module.text.strip())
    return modules, None


def parse_pom_dependencies(
    pom_path: Path,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], str | None]:
    """Parse dependencies from a POM file.

    Returns:
        Tuple of (deps, deps_mgmt, error)
    """
    try:
        root = parse_xml_file(pom_path)
    except (ET.ParseError, ValueError) as exc:
        return set(), set(), f"Invalid pom.xml: {exc}"

    namespace = get_xml_namespace(root)

    def deps_from(parent: ET.Element | None) -> set[tuple[str, str]]:
        deps: set[tuple[str, str]] = set()
        if parent is None:
            return deps
        for dep in parent.findall(ns_tag(namespace, "dependency")):
            group_id = elem_text(dep.find(ns_tag(namespace, "groupId")))
            artifact_id = elem_text(dep.find(ns_tag(namespace, "artifactId")))
            if artifact_id:
                deps.add((group_id, artifact_id))
        return deps

    deps = deps_from(root.find(ns_tag(namespace, "dependencies")))
    dep_mgmt = root.find(ns_tag(namespace, "dependencyManagement"))
    deps_mgmt = set()
    if dep_mgmt is not None:
        deps_mgmt = deps_from(dep_mgmt.find(ns_tag(namespace, "dependencies")))
    return deps, deps_mgmt, None


def plugin_matches(plugins: set[tuple[str, str]], group_id: str, artifact_id: str) -> bool:
    """Check if a plugin is in the set."""
    for group, artifact in plugins:
        if artifact != artifact_id:
            continue
        if not group or group == group_id:
            return True
    return False


def dependency_matches(dependencies: set[tuple[str, str]], group_id: str, artifact_id: str) -> bool:
    """Check if a dependency is in the set."""
    for group, artifact in dependencies:
        if artifact != artifact_id:
            continue
        if not group or group == group_id:
            return True
    return False


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
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        warnings.append("pom.xml not found")
        return warnings, missing_plugins

    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "maven":
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
    pom_path = root_path / "pom.xml"
    if not pom_path.exists():
        return warnings, missing

    build_tool = config.get("java", {}).get("build_tool", "maven")
    if build_tool != "maven":
        return warnings, missing

    modules, error = parse_pom_modules(pom_path)
    if error:
        warnings.append(error)
        return warnings, missing

    targets: list[Path] = []
    if modules:
        for module in modules:
            module_pom = root_path / module / "pom.xml"
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


# ============================================================================
# Snippet Loading
# ============================================================================


def load_plugin_snippets() -> dict[tuple[str, str], str]:
    """Load plugin snippets from the templates directory."""
    snippets_path = hub_root() / "templates" / "java" / "pom-plugins.xml"
    content = snippets_path.read_text(encoding="utf-8")
    blocks = re.findall(r"<plugin>.*?</plugin>", content, flags=re.DOTALL)
    snippets: dict[tuple[str, str], str] = {}
    for block in blocks:
        try:
            elem = parse_xml_text(block)
        except (ET.ParseError, ValueError):
            continue
        group_id = elem_text(elem.find("groupId"))
        artifact_id = elem_text(elem.find("artifactId"))
        if artifact_id:
            snippets[(group_id, artifact_id)] = block.strip()
    return snippets


def load_dependency_snippets() -> dict[tuple[str, str], str]:
    """Load dependency snippets from the templates directory."""
    snippets_path = hub_root() / "templates" / "java" / "pom-dependencies.xml"
    content = snippets_path.read_text(encoding="utf-8")
    blocks = re.findall(r"<dependency>.*?</dependency>", content, flags=re.DOTALL)
    snippets: dict[tuple[str, str], str] = {}
    for block in blocks:
        try:
            elem = parse_xml_text(block)
        except (ET.ParseError, ValueError):
            continue
        group_id = elem_text(elem.find("groupId"))
        artifact_id = elem_text(elem.find("artifactId"))
        if artifact_id:
            snippets[(group_id, artifact_id)] = block.strip()
    return snippets


# ============================================================================
# POM Insertion
# ============================================================================


def insert_plugins_into_pom(pom_text: str, plugin_block: str) -> tuple[str, bool]:
    """Insert plugins into a POM file's text.

    Returns:
        Tuple of (updated_text, success)
    """
    build_match = re.search(r"<build[^>]*>", pom_text)
    if build_match:
        build_close = pom_text.find("</build>", build_match.end())
        if build_close == -1:
            return pom_text, False
        build_section = pom_text[build_match.end() : build_close]
        plugins_match = re.search(r"<plugins[^>]*>", build_section)
        if plugins_match:
            plugins_close = build_section.find("</plugins>", plugins_match.end())
            if plugins_close == -1:
                return pom_text, False
            plugins_index = build_match.end() + plugins_match.start()
            plugins_indent = line_indent(pom_text, plugins_index)
            plugin_indent = plugins_indent + "  "
            block = indent_block(plugin_block, plugin_indent)
            insert_at = build_match.end() + plugins_close
            insert_text = f"\n{block}\n{plugins_indent}"
            return pom_text[:insert_at] + insert_text + pom_text[insert_at:], True

        build_indent = line_indent(pom_text, build_match.start())
        plugins_indent = build_indent + "  "
        plugin_indent = plugins_indent + "  "
        block = indent_block(plugin_block, plugin_indent)
        insert_at = build_close
        plugins_block = f"\n{plugins_indent}<plugins>\n{block}\n{plugins_indent}</plugins>\n{build_indent}"
        return pom_text[:insert_at] + plugins_block + pom_text[insert_at:], True

    project_close = pom_text.find("</project>")
    if project_close == -1:
        return pom_text, False
    project_indent = line_indent(pom_text, project_close)
    build_indent = project_indent + "  "
    plugins_indent = build_indent + "  "
    plugin_indent = plugins_indent + "  "
    block = indent_block(plugin_block, plugin_indent)
    build_block = (
        f"\n{build_indent}<build>\n{plugins_indent}<plugins>\n{block}\n"
        f"{plugins_indent}</plugins>\n{build_indent}</build>\n{project_indent}"
    )
    return pom_text[:project_close] + build_block + pom_text[project_close:], True


def insert_dependencies_into_pom(pom_text: str, dependency_block: str) -> tuple[str, bool]:
    """Insert dependencies into a POM file's text.

    Returns:
        Tuple of (updated_text, success)
    """
    dep_mgmt_spans = find_tag_spans(pom_text, "dependencyManagement")
    build_spans = find_tag_spans(pom_text, "build")

    def in_spans(index: int, spans: list[tuple[int, int]]) -> bool:
        return any(start <= index < end for start, end in spans)

    for match in re.finditer(r"<dependencies[^>]*>", pom_text):
        if in_spans(match.start(), dep_mgmt_spans) or in_spans(match.start(), build_spans):
            continue
        deps_close = pom_text.find("</dependencies>", match.end())
        if deps_close == -1:
            return pom_text, False
        deps_indent = line_indent(pom_text, match.start())
        dep_indent = deps_indent + "  "
        block = indent_block(dependency_block, dep_indent)
        insert_at = deps_close
        insert_text = f"\n{block}\n{deps_indent}"
        return pom_text[:insert_at] + insert_text + pom_text[insert_at:], True

    project_close = pom_text.find("</project>")
    if project_close == -1:
        return pom_text, False
    project_indent = line_indent(pom_text, project_close)
    deps_indent = project_indent + "  "
    dep_indent = deps_indent + "  "
    block = indent_block(dependency_block, dep_indent)
    deps_block = f"\n{deps_indent}<dependencies>\n{block}\n{deps_indent}</dependencies>\n{project_indent}"
    return pom_text[:project_close] + deps_block + pom_text[project_close:], True
