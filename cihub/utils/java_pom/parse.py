"""Pure POM parsing and XML utilities.

This module contains low-level XML parsing, POM structure extraction,
and matching helpers. No business logic or config dependencies.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import defusedxml.ElementTree as ET  # Secure XML parsing (prevents XXE)

if TYPE_CHECKING:
    pass

# ============================================================================
# Constants - Tool plugin/dependency mappings
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


# ============================================================================
# Matching Helpers
# ============================================================================


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
