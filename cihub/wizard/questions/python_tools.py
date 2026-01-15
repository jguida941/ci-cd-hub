"""Python tool selection prompts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import questionary

from cihub.tools.registry import PYTHON_TOOLS, get_custom_tools_from_config
from cihub.wizard.core import _check_cancelled
from cihub.wizard.styles import get_style


def configure_python_tools(defaults: dict) -> dict[str, Any]:
    """Prompt to enable/disable Python tools.

    Sources tool list from cihub.tools.registry (CLI source of truth).
    Also includes any custom x-* tools defined in the config.

    Args:
        defaults: Defaults config (expects python.tools).

    Returns:
        Tool config dict with updated enabled flags.
    """
    raw_tools = deepcopy(defaults.get("python", {}).get("tools", {}))
    tools: dict[str, Any] = raw_tools if isinstance(raw_tools, dict) else {}

    # Get all tools: built-in from registry + custom from config
    all_tools = list(PYTHON_TOOLS)
    custom_tools = get_custom_tools_from_config(defaults, "python")
    all_tools.extend(sorted(custom_tools.keys()))

    for tool in all_tools:
        tool_cfg = tools.get(tool)
        if not isinstance(tool_cfg, dict):
            # Initialize config for tools not yet in defaults
            tool_cfg = {"enabled": False}
            tools[tool] = tool_cfg
        enabled = tool_cfg.get("enabled", False)
        # Show custom tool indicator
        label = f"Enable {tool}?" if tool in PYTHON_TOOLS else f"Enable {tool} (custom)?"
        answer: bool = _check_cancelled(
            questionary.confirm(
                label,
                default=bool(enabled),
                style=get_style(),
            ).ask(),
            f"{tool} toggle",
        )
        tool_cfg["enabled"] = bool(answer)
    return tools
