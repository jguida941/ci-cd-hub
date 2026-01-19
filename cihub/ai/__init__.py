"""CIHub AI Enhancement Module.

This module provides optional AI enhancement for CLI commands.
AI is never required - commands work fully without it.
"""

from __future__ import annotations

from cihub.ai.claude_client import invoke_claude, is_ai_available
from cihub.ai.context import build_context
from cihub.ai.enhance import enhance_result

__all__ = [
    "enhance_result",
    "build_context",
    "is_ai_available",
    "invoke_claude",
]
