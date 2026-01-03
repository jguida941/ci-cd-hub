from __future__ import annotations

from pathlib import Path
from unittest import mock

from cihub.cli import CommandResult
from cihub.services.ci import run_ci


def test_run_ci_wraps_command_result(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    summary_path = tmp_path / "summary.md"
    command_result = CommandResult(
        exit_code=0,
        summary="ok",
        problems=[{"severity": "warning", "message": "warn"}],
        artifacts={"report": str(report_path), "summary": str(summary_path)},
        data={"report_path": str(report_path), "summary_path": str(summary_path)},
    )

    with mock.patch("cihub.services.ci.cmd_ci", return_value=command_result):
        result = run_ci(tmp_path)

    assert result.success is True
    assert result.report_path == report_path
    assert result.summary_path == summary_path
    assert result.errors == []
    assert result.warnings == ["warn"]


def test_run_ci_handles_non_json_result(tmp_path: Path) -> None:
    with mock.patch("cihub.services.ci.cmd_ci", return_value=1):
        result = run_ci(tmp_path)

    assert result.success is False
    assert result.exit_code == 1
    assert result.errors
