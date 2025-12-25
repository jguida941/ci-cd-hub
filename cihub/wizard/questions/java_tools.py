"""Java tool selection prompts."""

from __future__ import annotations

from copy import deepcopy

import questionary

from cihub.wizard.styles import get_style

JAVA_TOOL_ORDER = [
    "jacoco",
    "checkstyle",
    "spotbugs",
    "pmd",
    "owasp",
    "pitest",
    "jqwik",
    "semgrep",
    "trivy",
    "codeql",
    "docker",
]


def configure_java_tools(defaults: dict) -> dict:
    """Prompt to enable/disable Java tools.

    Args:
        defaults: Defaults config (expects java.tools).

    Returns:
        Tool config dict with updated enabled flags.
    """
    tools = deepcopy(defaults.get("java", {}).get("tools", {}))
    for tool in JAVA_TOOL_ORDER:
        if tool not in tools:
            continue
        enabled = tools[tool].get("enabled", False)
        answer = questionary.confirm(
            f"Enable {tool}?",
            default=bool(enabled),
            style=get_style(),
        ).ask()
        tools[tool]["enabled"] = bool(answer)
    return tools
