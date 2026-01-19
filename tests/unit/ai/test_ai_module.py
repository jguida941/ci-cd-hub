"""Unit tests for the AI module."""

# TEST-METRICS:

from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

from cihub.ai import build_context, enhance_result, is_ai_available
from cihub.ai.claude_client import invoke_claude
from cihub.types import CommandResult


def test_is_ai_available_no_claude() -> None:
    with patch.dict(os.environ, {"CIHUB_AI_PROVIDER": "claude"}):
        with patch("shutil.which", return_value=None):
            assert is_ai_available() is False


def test_is_ai_available_with_claude() -> None:
    with patch.dict(os.environ, {"CIHUB_AI_PROVIDER": "claude"}):
        with patch("shutil.which", return_value="/usr/bin/claude"):
            assert is_ai_available() is True


def test_build_context_includes_problems() -> None:
    result = CommandResult(
        exit_code=1,
        summary="Check failed",
        problems=[{"severity": "error", "message": "Ruff found 5 errors"}],
    )
    context = build_context(result)
    assert "Ruff found 5 errors" in context
    assert "error" in context


def test_enhance_result_without_claude() -> None:
    result = CommandResult(exit_code=1, summary="Failed")

    with patch("cihub.ai.enhance.is_ai_available", return_value=False):
        enhanced = enhance_result(result)

    assert any("unavailable" in s.get("message", "") for s in enhanced.suggestions)


def test_enhance_result_with_claude() -> None:
    result = CommandResult(exit_code=1, summary="Failed")
    mock_response = {"result": "Try running ruff --fix"}

    with patch("cihub.ai.enhance.is_ai_available", return_value=True):
        with patch("cihub.ai.enhance.invoke_claude", return_value=mock_response):
            enhanced = enhance_result(result)

    assert any("ruff --fix" in s.get("message", "") for s in enhanced.suggestions)
    assert enhanced.data.get("ai_analysis") == "Try running ruff --fix"


def test_enhance_result_unsupported_provider() -> None:
    result = CommandResult(exit_code=1, summary="Failed")

    with patch.dict(os.environ, {"CIHUB_AI_PROVIDER": "openai"}):
        enhanced = enhance_result(result)

    assert any("not supported" in s.get("message", "") for s in enhanced.suggestions)
    assert "ai_analysis" not in enhanced.data


def test_invoke_claude_timeout() -> None:
    with patch("shutil.which", return_value="/usr/bin/claude"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 60)):
            assert invoke_claude("test prompt") is None


def test_invoke_claude_not_installed() -> None:
    with patch.dict(os.environ, {"CIHUB_AI_PROVIDER": "claude"}):
        with patch("shutil.which", return_value=None):
            assert invoke_claude("test prompt") is None
