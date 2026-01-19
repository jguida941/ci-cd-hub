"""Enhance CommandResult with AI analysis.

This is the main entry point for AI enhancement.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from cihub.ai.claude_client import invoke_claude, is_ai_available
from cihub.ai.context import build_context

if TYPE_CHECKING:
    from cihub.types import CommandResult


def _resolve_provider() -> str:
    provider = os.getenv("CIHUB_AI_PROVIDER", "claude")
    if not provider:
        return "claude"
    return provider.strip().lower()


def enhance_result(
    result: "CommandResult",
    *,
    mode: str = "analyze",
) -> "CommandResult":
    """Enhance a CommandResult with AI analysis.

    Args:
        result: The CommandResult to enhance.
        mode: Enhancement mode ("analyze", "fix", "explain").

    Returns:
        Enhanced CommandResult with AI suggestions added.
    """
    provider = _resolve_provider()
    if provider != "claude":
        result.suggestions.append(
            {
                "message": f"AI provider '{provider}' is not supported (set CIHUB_AI_PROVIDER=claude).",
                "source": "cihub",
            }
        )
        return result

    if not is_ai_available(provider):
        result.suggestions.append(
            {
                "message": "AI enhancement unavailable (Claude CLI not found).",
                "source": "cihub",
            }
        )
        return result

    context = build_context(result)

    if mode == "analyze":
        prompt = f"""Analyze this CI/CD failure and suggest fixes.

{context}

Provide:
1. Root cause (1 sentence)
2. Specific fix steps (numbered list)
3. Prevention tip (1 sentence)

Be concise and actionable."""
    elif mode == "explain":
        prompt = f"""Explain this CI/CD result in plain language.

{context}

Explain what happened and what the user should do next.
Use simple language, no jargon."""
    elif mode == "fix":
        prompt = f"""Suggest specific code/config fixes for these issues.

{context}

For each problem, provide the exact fix (file path, line, change)."""
    else:
        prompt = f"Analyze: {context}"

    response = invoke_claude(prompt)
    if response and "result" in response:
        result.data["ai_analysis"] = response["result"]
        result.suggestions.append(
            {
                "message": response["result"],
                "source": "claude",
                "mode": mode,
            }
        )

    return result
