"""Java POM file parsing, validation, and manipulation.

This package provides a clean separation of concerns:
- parse.py: Pure XML/POM parsing (no business logic)
- rules.py: Policy/validation (config-driven checks)
- apply.py: Mutations/writes (snippet application)

All public symbols are re-exported here for backward compatibility.
"""

from __future__ import annotations

# Apply layer - mutations and writes
from cihub.utils.java_pom.apply import (
    insert_dependencies_into_pom,
    insert_plugins_into_pom,
    load_dependency_snippets,
    load_plugin_snippets,
)

# Parse layer - pure parsing, no config dependencies
from cihub.utils.java_pom.parse import (
    JAVA_TOOL_DEPENDENCIES,
    JAVA_TOOL_PLUGINS,
    dependency_matches,
    elem_text,
    find_tag_spans,
    get_xml_namespace,
    indent_block,
    line_indent,
    ns_tag,
    parse_pom_dependencies,
    parse_pom_modules,
    parse_pom_plugins,
    parse_xml_file,
    parse_xml_text,
    plugin_matches,
)

# Rules layer - config-driven validation
from cihub.utils.java_pom.rules import (
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    get_java_tool_flags,
)

__all__ = [
    # Constants
    "JAVA_TOOL_DEPENDENCIES",
    "JAVA_TOOL_PLUGINS",
    # Parse layer
    "dependency_matches",
    "elem_text",
    "find_tag_spans",
    "get_xml_namespace",
    "indent_block",
    "line_indent",
    "ns_tag",
    "parse_pom_dependencies",
    "parse_pom_modules",
    "parse_pom_plugins",
    "parse_xml_file",
    "parse_xml_text",
    "plugin_matches",
    # Rules layer
    "collect_java_dependency_warnings",
    "collect_java_pom_warnings",
    "get_java_tool_flags",
    # Apply layer
    "insert_dependencies_into_pom",
    "insert_plugins_into_pom",
    "load_dependency_snippets",
    "load_plugin_snippets",
]
