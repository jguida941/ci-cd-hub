"""AI formatter registry for --ai output mode.

Each command that supports --ai mode registers its formatter here.
The AIRenderer looks up formatters by command name.

This module uses lazy imports to avoid circular dependencies - formatters
are only imported when actually needed.

Example usage:
    formatter = get_ai_formatter("docs stale")
    if formatter:
        output = formatter(report_data)
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, cast

# Type for AI formatters: takes report data, returns markdown string
AIFormatter = Callable[[Any], str]

# Registry: command name -> (module_path, function_name)
# Uses lazy imports to avoid circular dependencies
_AI_FORMATTERS: dict[str, tuple[str, str]] = {
    "docs stale": ("cihub.commands.docs_stale.output", "format_ai_output"),
    # Future commands can register here:
    # "triage": ("cihub.commands.triage.output", "format_triage_ai"),
}


def get_ai_formatter(command: str) -> AIFormatter | None:
    """Get AI formatter for a command, with lazy import.

    Args:
        command: The command name (e.g., "docs stale", "triage")

    Returns:
        The formatter function, or None if command has no AI formatter
    """
    if command not in _AI_FORMATTERS:
        return None

    module_path, func_name = _AI_FORMATTERS[command]
    module = importlib.import_module(module_path)
    return cast(AIFormatter, getattr(module, func_name))


def has_ai_formatter(command: str) -> bool:
    """Check if a command has a registered AI formatter.

    Args:
        command: The command name

    Returns:
        True if the command has a registered formatter
    """
    return command in _AI_FORMATTERS
