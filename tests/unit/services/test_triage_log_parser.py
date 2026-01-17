"""Unit tests for triage log parser utilities."""

# TEST-METRICS:

from __future__ import annotations

from cihub.commands.triage.log_parser import create_log_failure, resolve_unknown_steps
from cihub.services.triage_service import CATEGORY_BY_TOOL


def test_resolve_unknown_steps_updates_step_and_tool() -> None:
    failures = [
        create_log_failure(
            job="Unit Tests",
            step="UNKNOWN STEP",
            errors=["boom"],
            run_id="123",
            repo="owner/repo",
        )
    ]
    jobs = [
        {
            "name": "Unit Tests",
            "conclusion": "failure",
            "steps": [
                {"name": "Install deps", "conclusion": "success"},
                {"name": "Run pytest", "conclusion": "failure"},
            ],
        }
    ]

    updated, resolved = resolve_unknown_steps(failures, jobs)

    assert resolved == 1
    assert updated[0]["step"] == "Run pytest"
    assert updated[0]["tool"] == "pytest"
    assert updated[0]["category"] == CATEGORY_BY_TOOL["pytest"]


def test_resolve_unknown_steps_no_match_keeps_failure() -> None:
    failures = [
        create_log_failure(
            job="Unit Tests",
            step="UNKNOWN STEP",
            errors=["boom"],
            run_id="123",
            repo="owner/repo",
        )
    ]
    jobs = [
        {
            "name": "Other Job",
            "conclusion": "failure",
            "steps": [
                {"name": "Install deps", "conclusion": "success"},
            ],
        }
    ]

    updated, resolved = resolve_unknown_steps(failures, jobs)

    assert resolved == 0
    assert updated[0]["step"] == "UNKNOWN STEP"
