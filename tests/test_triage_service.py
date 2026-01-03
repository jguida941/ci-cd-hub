"""Tests for triage bundle generation."""

from __future__ import annotations

import json
from pathlib import Path

from cihub.services.triage_service import generate_triage_bundle, write_triage_bundle


def _write_report(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_generate_triage_from_report(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    report_path = output_dir / "report.json"
    report = {
        "schema_version": "2.0",
        "repository": "acme/widgets",
        "branch": "main",
        "commit": "deadbeef",
        "tools_configured": {"ruff": True, "pytest": True},
        "tools_ran": {"ruff": True, "pytest": True},
        "tools_success": {"ruff": False, "pytest": True},
        "environment": {"workdir": "."},
    }
    _write_report(report_path, report)

    bundle = generate_triage_bundle(output_dir, report_path=report_path)
    assert bundle.triage["schema_version"] == "cihub-triage-v1"
    failures = bundle.triage["failures"]
    assert any(failure["tool"] == "ruff" for failure in failures)


def test_generate_triage_missing_report(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    bundle = generate_triage_bundle(output_dir)
    failures = bundle.triage["failures"]
    assert failures
    assert failures[0]["tool"] == "cihub"
    assert failures[0]["reason"] in {"missing_report", "invalid_report"}


def test_priority_ordering_prefers_security(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    report_path = output_dir / "report.json"
    report = {
        "schema_version": "2.0",
        "repository": "acme/widgets",
        "branch": "main",
        "commit": "deadbeef",
        "tools_configured": {"bandit": True, "ruff": True},
        "tools_ran": {"bandit": True, "ruff": True},
        "tools_success": {"bandit": False, "ruff": False},
        "environment": {"workdir": "."},
    }
    _write_report(report_path, report)

    bundle = generate_triage_bundle(output_dir, report_path=report_path)
    failures = bundle.priority["failures"]
    assert failures[0]["tool"] == "bandit"


def test_history_appends_lines(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    report_path = output_dir / "report.json"
    report = {
        "schema_version": "2.0",
        "repository": "acme/widgets",
        "branch": "main",
        "commit": "deadbeef",
        "tools_configured": {"ruff": True},
        "tools_ran": {"ruff": True},
        "tools_success": {"ruff": True},
        "environment": {"workdir": "."},
    }
    _write_report(report_path, report)

    bundle = generate_triage_bundle(output_dir, report_path=report_path)
    write_triage_bundle(bundle, output_dir)
    write_triage_bundle(bundle, output_dir)

    history_path = output_dir / "history.jsonl"
    lines = history_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
