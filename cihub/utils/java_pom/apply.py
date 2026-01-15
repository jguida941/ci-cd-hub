"""POM mutation and snippet application.

This module handles loading plugin/dependency snippets from templates
and inserting them into POM files.
"""

from __future__ import annotations

import re

import defusedxml.ElementTree as ET

from cihub.utils.paths import hub_root

from .parse import (
    elem_text,
    find_tag_spans,
    indent_block,
    line_indent,
    parse_xml_text,
)

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
