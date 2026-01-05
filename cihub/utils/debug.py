"""Debug helpers for CLI diagnostics."""

from __future__ import annotations

import sys
from typing import Iterable, Mapping, TextIO

from cihub.utils.env import env_bool


def debug_context_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True if CIHUB_DEBUG_CONTEXT is enabled."""
    return env_bool("CIHUB_DEBUG_CONTEXT", default=False, env=env)


def emit_debug_context(
    title: str,
    entries: Iterable[tuple[str, str | None]],
    *,
    env: Mapping[str, str] | None = None,
    file: TextIO | None = None,
) -> None:
    """Emit a compact debug context block to stderr when enabled."""
    if not debug_context_enabled(env=env):
        return
    output = file or sys.stderr
    lines = [f"[cihub debug] {title}"]
    for key, value in entries:
        if value is None:
            continue
        text = str(value)
        if not text:
            continue
        lines.append(f"  {key}: {text}")
    output.write("\n".join(lines) + "\n")
