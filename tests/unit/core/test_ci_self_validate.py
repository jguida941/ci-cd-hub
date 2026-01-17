"""Tests for cihub ci self-validation (report/summary contradictions)."""

# TEST-METRICS:

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cihub.services.ci_engine import run_ci as run_ci_engine


@pytest.fixture
def minimal_python_config() -> dict[str, Any]:
    return {
        "language": "python",
        "repo": {"owner": "acme", "name": "demo", "language": "python"},
        "python": {"version": "3.12", "tools": {"pytest": {"enabled": False}}},
        "thresholds": {"coverage_min": 0, "mutation_score_min": 0, "max_critical_vulns": 0, "max_high_vulns": 0},
        "reports": {"github_summary": {"enabled": False}, "codecov": {"enabled": False}},
    }


def test_ci_self_validation_fails_on_summary_mismatch(
    monkeypatch,
    tmp_path: Path,
    minimal_python_config: dict[str, Any],
) -> None:
    """If render_summary drifts from report content, cihub ci must fail."""

    # Fake config load
    monkeypatch.setattr(
        "cihub.services.ci_engine.load_ci_config",
        lambda _repo_path: dict(minimal_python_config),
    )

    # Fake tool execution (no tools)
    monkeypatch.setattr(
        "cihub.services.ci_engine._run_python_tools",
        lambda *_args, **_kwargs: ({}, {"pytest": False}, {"pytest": False}),
    )

    # Force a deterministic (but intentionally contradictory) summary
    def bad_summary(_report: dict[str, Any], include_metrics: bool = True) -> str:  # noqa: FBT001, FBT002
        return "\n".join(
            [
                "## Tools Enabled",
                "| Category | Tool | Configured | Ran | Success |",
                "|----------|------|------------|-----|---------|",
                "| Testing | pytest | true | true | true |",  # contradicts tools_ran/tools_success
                "",
            ]
        )

    monkeypatch.setattr("cihub.services.ci_engine.render_summary", bad_summary)

    # Avoid schema failures due to missing git SHA in temp repos (self-validate treats schema
    # errors as warnings locally)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    result = run_ci_engine(repo_path=tmp_path)

    assert result.exit_code != 0
    assert any(p.get("code") == "CIHUB-CI-REPORT-SELF-VALIDATE" for p in result.problems)
