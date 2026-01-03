from __future__ import annotations

from pathlib import Path
from unittest import mock

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.ci import run_ci


def test_run_ci_handles_load_error(tmp_path: Path) -> None:
    with mock.patch("cihub.services.ci_engine.load_ci_config", side_effect=ValueError("boom")):
        result = run_ci(tmp_path)

    assert result.success is False
    assert result.exit_code == EXIT_FAILURE
    assert result.errors


def test_run_ci_writes_report_and_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    config = {
        "language": "python",
        "repo": {"owner": "owner", "name": "repo"},
        "python": {"tools": {"pytest": {"enabled": True}}},
        "reports": {
            "github_summary": {"enabled": False, "include_metrics": False},
            "codecov": {"enabled": False},
        },
    }
    report = {"results": {}, "tool_metrics": {}, "repository": "owner/repo", "branch": "main"}

    with mock.patch("cihub.services.ci_engine.load_ci_config", return_value=config):
        with mock.patch("cihub.services.ci_engine._run_python_tools", return_value=({}, {}, {})):
            with mock.patch("cihub.services.ci_engine.build_python_report", return_value=report):
                with mock.patch("cihub.services.ci_engine._evaluate_python_gates", return_value=[]):
                    with mock.patch("cihub.services.ci_engine.render_summary", return_value="summary"):
                        result = run_ci(tmp_path, output_dir=output_dir)

    assert result.success is True
    assert result.exit_code == EXIT_SUCCESS
    assert result.report_path and result.report_path.exists()
    assert result.summary_path and result.summary_path.exists()
    assert result.summary_text == "summary"
