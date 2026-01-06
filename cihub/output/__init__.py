"""Output rendering package for cihub CLI.

This package provides the OutputRenderer abstraction that centralizes ALL output
formatting. Commands return CommandResult with structured data, and the renderer
decides how to display it based on the output mode (human vs JSON vs AI).

Architecture:
    Command → CommandResult(data={...}) → Renderer → output string

Usage:
    from cihub.output import get_renderer

    renderer = get_renderer(json_mode=args.json, ai_mode=args.ai)
    output = renderer.render(result, command_name, duration_ms)
    print(output)
"""

from __future__ import annotations

from cihub.output.renderers import (
    AIRenderer,
    HumanRenderer,
    JsonRenderer,
    OutputRenderer,
    get_renderer,
)

__all__ = [
    "OutputRenderer",
    "HumanRenderer",
    "JsonRenderer",
    "AIRenderer",
    "get_renderer",
]
