"""Tests for AI loop suggestion patterns."""

from __future__ import annotations

from cihub.services.ai.patterns import collect_suggestions


def test_collect_suggestions_includes_tool_and_problem() -> None:
    failures = [
        {
            "tool": "ruff",
            "status": "failed",
            "reason": "tool_failed",
            "message": "Tool 'ruff' failed",
        }
    ]
    problems = [
        {
            "severity": "error",
            "message": "requirements.txt failed",
            "code": "CIHUB-CI-DEPS",
        }
    ]

    suggestions = collect_suggestions(problems, failures)
    codes = {item["code"] for item in suggestions}

    assert "CIHUB-AI-TOOL-RUFF" in codes
    assert "CIHUB-AI-CI-DEPS" in codes


def test_collect_suggestions_for_required_not_run() -> None:
    failures = [
        {
            "tool": "pytest",
            "status": "required_not_run",
            "reason": "tool_required_not_run",
            "message": "Tool 'pytest' was required but did not run",
        }
    ]

    suggestions = collect_suggestions([], failures)
    messages = [item["message"] for item in suggestions]

    assert any("required tool did not run" in message for message in messages)
