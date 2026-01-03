"""Shared utility functions for cihub.

This module provides common utilities used across the cihub package.
All public items here should remain stable for backward compatibility.
"""

from __future__ import annotations

from cihub.utils.env import _parse_env_bool
from cihub.utils.exec_utils import resolve_executable
from cihub.utils.git import (
    GIT_REMOTE_RE,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.utils.github_api import fetch_remote_file, gh_api_json, update_remote_file
from cihub.utils.java_pom import (
    JAVA_TOOL_DEPENDENCIES,
    JAVA_TOOL_PLUGINS,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    dependency_matches,
    elem_text,
    find_tag_spans,
    get_java_tool_flags,
    get_xml_namespace,
    indent_block,
    insert_dependencies_into_pom,
    insert_plugins_into_pom,
    line_indent,
    load_dependency_snippets,
    load_plugin_snippets,
    ns_tag,
    parse_pom_dependencies,
    parse_pom_modules,
    parse_pom_plugins,
    parse_xml_file,
    parse_xml_text,
    plugin_matches,
)
from cihub.utils.paths import hub_root, validate_repo_path, validate_subdir
from cihub.utils.progress import _bar

__all__ = [
    "_parse_env_bool",
    "_bar",
    "resolve_executable",
    "GIT_REMOTE_RE",
    "get_git_branch",
    "get_git_remote",
    "parse_repo_from_remote",
    "gh_api_json",
    "fetch_remote_file",
    "update_remote_file",
    "hub_root",
    "validate_repo_path",
    "validate_subdir",
    # Java POM utilities
    "JAVA_TOOL_PLUGINS",
    "JAVA_TOOL_DEPENDENCIES",
    "get_java_tool_flags",
    "get_xml_namespace",
    "ns_tag",
    "elem_text",
    "parse_xml_text",
    "parse_xml_file",
    "line_indent",
    "indent_block",
    "find_tag_spans",
    "parse_pom_plugins",
    "parse_pom_modules",
    "parse_pom_dependencies",
    "plugin_matches",
    "dependency_matches",
    "collect_java_pom_warnings",
    "collect_java_dependency_warnings",
    "load_plugin_snippets",
    "load_dependency_snippets",
    "insert_plugins_into_pom",
    "insert_dependencies_into_pom",
]
