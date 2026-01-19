"""Claude CLI subprocess wrapper.

Calls Claude Code in headless mode (-p) for AI analysis.
Falls back gracefully if Claude is not installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Mapping, cast

AI_TIMEOUT = 60
DEFAULT_PROVIDER = "claude"


def _resolve_provider(env: Mapping[str, str] | None = None) -> str:
    if env is None:
        value = os.getenv("CIHUB_AI_PROVIDER", DEFAULT_PROVIDER)
    else:
        value = env.get("CIHUB_AI_PROVIDER", DEFAULT_PROVIDER)
    if not value:
        return DEFAULT_PROVIDER
    return value.strip().lower()


def is_ai_available(provider: str | None = None, *, env: Mapping[str, str] | None = None) -> bool:
    """Check if the configured AI provider is available."""
    provider_name = (provider or _resolve_provider(env)).lower()
    if provider_name != "claude":
        return False
    return shutil.which("claude") is not None


def invoke_claude(
    prompt: str,
    *,
    output_format: str = "json",
    timeout: int = AI_TIMEOUT,
) -> dict[str, Any] | None:
    """Invoke Claude Code in headless mode.

    Args:
        prompt: The prompt to send to Claude.
        output_format: Output format ("json" or "text").
        timeout: Timeout in seconds.

    Returns:
        Parsed JSON response, or None if failed.
    """
    if not is_ai_available("claude"):
        return None
    claude_path = shutil.which("claude")
    if not claude_path:
        return None

    try:
        result = subprocess.run(  # noqa: S603 - prompt is passed as an argument to a trusted CLI (no shell)
            [claude_path, "-p", prompt, "--output-format", output_format],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None

        if output_format == "json":
            payload = json.loads(result.stdout)
            return cast(dict[str, Any], payload)
        return {"result": result.stdout}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        return None
