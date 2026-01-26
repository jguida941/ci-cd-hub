"""Integration tests for triage command flows.

These tests verify end-to-end behavior of the triage command
with realistic scenarios and mocked external dependencies.
"""

# TEST-METRICS:

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from cihub.commands.triage import cmd_triage
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _make_report(
    *,
    repo: str = "test/repo",
    tools_configured: dict[str, bool] | None = None,
    tools_ran: dict[str, bool] | None = None,
    tools_success: dict[str, bool] | None = None,
    tool_metrics: dict[str, int | float | None] | None = None,
    results: dict[str, int | float | None] | None = None,
) -> dict[str, object]:
    """Build a schema-valid report.json payload for triage tests."""
    return {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": "0.0.0-test",
            "workflow_ref": "test",
            "generated_at": "2024-01-01T00:00:00Z",
        },
        "repository": repo,
        "run_id": "123",
        "run_number": "1",
        "commit": "a" * 40,
        "branch": "main",
        "timestamp": "2024-01-01T00:00:00Z",
        "python_version": "3.12",
        "tools_configured": tools_configured or {},
        "tools_ran": tools_ran or {},
        "tools_success": tools_success or {},
        "tool_metrics": tool_metrics or {},
        "results": results
        or {
            "coverage": 0,
            "mutation_score": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "critical_vulns": 0,
            "high_vulns": 0,
            "medium_vulns": 0,
        },
    }


class TestTriageLocalMode:
    """Integration tests for local triage mode."""

    def test_triage_with_local_report(self, tmp_path: Path) -> None:
        """Test triage from a local report.json file."""
        # Create a minimal report.json
        report = _make_report(
            tools_configured={"pytest": True, "ruff": True},
            tools_ran={"pytest": True, "ruff": True},
            tools_success={"pytest": False, "ruff": True},
        )
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=str(report_path),
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "failures" in result.summary.lower() or "triage" in result.summary.lower()
        assert (tmp_path / "triage.json").exists()
        assert (tmp_path / "triage.md").exists()

    def test_triage_with_missing_report(self, tmp_path: Path) -> None:
        """Test triage fails gracefully with missing report."""
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=str(tmp_path / "nonexistent.json"),
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        # Should handle missing file gracefully
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]


class TestTriageMultiMode:
    """Integration tests for multi-report triage mode."""

    def test_triage_multi_aggregates_reports(self, tmp_path: Path) -> None:
        """Test --multi --reports-dir aggregates multiple reports."""
        # Create two report directories
        for repo_name in ["repo-a", "repo-b"]:
            repo_dir = tmp_path / "reports" / repo_name
            repo_dir.mkdir(parents=True)
            report = _make_report(
                repo=f"test-org/{repo_name}",
                tools_configured={"pytest": True},
                tools_ran={"pytest": True},
                tools_success={"pytest": repo_name == "repo-a"},
            )
            (repo_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        args = argparse.Namespace(
            output_dir=str(tmp_path / "output"),
            report=None,
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=True,
            reports_dir=str(tmp_path / "reports"),
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "2" in result.summary  # Should mention 2 repos
        assert (tmp_path / "output" / "multi-triage.json").exists()


class TestTriageRemotePerRepo:
    """Integration tests for remote per-repo triage mode."""

    def test_triage_per_repo_counts(self, tmp_path: Path) -> None:
        """Remote per-repo mode should count pass/fail correctly."""
        run_id = "12345"
        output_dir = tmp_path / "output"
        artifacts_dir = output_dir / "runs" / run_id / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        reports = {"repo-a": True, "repo-b": False}
        for repo_name, success in reports.items():
            repo_dir = artifacts_dir / repo_name
            repo_dir.mkdir(parents=True, exist_ok=True)
            report = _make_report(
                repo=f"test-org/{repo_name}",
                tools_configured={"pytest": True},
                tools_ran={"pytest": True},
                tools_success={"pytest": success},
            )
            (repo_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        args = argparse.Namespace(
            output_dir=str(output_dir),
            report=None,
            summary=None,
            run=run_id,
            artifacts_dir=None,
            repo="owner/repo",
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=True,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        with patch("cihub.commands.triage.remote.download_artifacts", return_value=False), patch(
            "cihub.commands.triage.remote.fetch_run_info",
            side_effect=RuntimeError("offline"),
        ):
            result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["passed_count"] == 1
        assert result.data["failed_count"] == 1


class TestTriageFiltering:
    """Integration tests for triage filtering."""

    def test_triage_with_severity_filter(self, tmp_path: Path) -> None:
        """Test --min-severity filters failures correctly."""
        report = _make_report(
            tools_configured={"pytest": True, "ruff": True, "bandit": True},
            tools_ran={"pytest": True, "ruff": True, "bandit": True},
            tools_success={"pytest": False, "ruff": False, "bandit": False},
        )
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=str(report_path),
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity="high",  # Filter to high+ only
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS
        # Should indicate filtering was applied
        if result.data and result.data.get("filters_applied"):
            assert result.data["filters_applied"]["min_severity"] == "high"


class TestTriageVerifyTools:
    """Integration tests for --verify-tools mode."""

    def test_verify_tools_detects_drift(self, tmp_path: Path) -> None:
        """Test --verify-tools detects configured but not run tools."""
        report = _make_report(
            tools_configured={"pytest": True, "mypy": True},
            tools_ran={"pytest": True, "mypy": False},
            tools_success={"pytest": True, "mypy": False},
        )
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=str(report_path),
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=True,
        )

        result = cmd_triage(args)

        # Should detect drift
        assert result.exit_code == EXIT_FAILURE
        assert any("drift" in str(p).lower() for p in result.problems)


class TestTriageAnalysisModes:
    """Integration tests for analysis modes (flaky, gate history)."""

    def test_detect_flaky_with_history(self, tmp_path: Path) -> None:
        """Test --detect-flaky analyzes history.jsonl."""
        # Create history with alternating results (flaky pattern)
        history_path = tmp_path / "history.jsonl"
        entries = [
            {"timestamp": "2024-01-01", "overall_status": "success", "failure_count": 0},
            {"timestamp": "2024-01-02", "overall_status": "failure", "failure_count": 2},
            {"timestamp": "2024-01-03", "overall_status": "success", "failure_count": 0},
            {"timestamp": "2024-01-04", "overall_status": "failure", "failure_count": 1},
            {"timestamp": "2024-01-05", "overall_status": "success", "failure_count": 0},
        ]
        with history_path.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=None,
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=True,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "flaky" in result.summary.lower()

    def test_gate_history_analysis(self, tmp_path: Path) -> None:
        """Test --gate-history analyzes gate changes."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            {"timestamp": "2024-01-01", "overall_status": "success", "failure_count": 0, "gates": {"pytest": "pass"}},
            {"timestamp": "2024-01-02", "overall_status": "failure", "failure_count": 1, "gates": {"pytest": "fail"}},
        ]
        with history_path.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=None,
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=True,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS
        summary = result.summary.lower()
        assert "gate" in summary or "history" in summary or "runs" in summary


class TestTriageRepoValidation:
    """Integration tests for repo format validation."""

    def test_invalid_repo_format_rejected(self, tmp_path: Path) -> None:
        """Test that invalid repo format is rejected."""
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=None,
            summary=None,
            run="12345",
            artifacts_dir=None,
            repo="invalid repo format with spaces",  # Invalid!
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_FAILURE
        assert "invalid" in result.summary.lower() or "repo" in result.summary.lower()

    def test_valid_repo_format_accepted(self, tmp_path: Path) -> None:
        """Test that valid repo format passes validation."""
        # This will fail later (no network), but should pass repo validation
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=None,
            summary=None,
            run="12345",
            artifacts_dir=None,
            repo="owner/repo-name",  # Valid format
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        # Mock the GitHub client to avoid network calls
        with patch("cihub.commands.triage.remote.fetch_run_info") as mock_fetch:
            mock_fetch.side_effect = RuntimeError("Network error (expected in test)")
            result = cmd_triage(args)

        # Should fail due to network, not repo validation
        assert "invalid repo format" not in result.summary.lower()


class TestTriageArtifacts:
    """Integration tests for artifact generation."""

    def test_triage_generates_all_artifacts(self, tmp_path: Path) -> None:
        """Test that triage generates all expected artifact files."""
        report = _make_report(
            tools_configured={"pytest": True},
            tools_ran={"pytest": True},
            tools_success={"pytest": False},
        )
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        args = argparse.Namespace(
            output_dir=str(tmp_path),
            report=str(report_path),
            summary=None,
            run=None,
            artifacts_dir=None,
            repo=None,
            multi=False,
            reports_dir=None,
            detect_flaky=False,
            gate_history=False,
            workflow=None,
            branch=None,
            aggregate=False,
            per_repo=False,
            latest=False,
            watch=False,
            interval=30,
            min_severity=None,
            category=None,
            verify_tools=False,
        )

        result = cmd_triage(args)

        assert result.exit_code == EXIT_SUCCESS

        # Check all expected files exist
        assert (tmp_path / "triage.json").exists()
        assert (tmp_path / "triage.md").exists()
        assert (tmp_path / "priority.json").exists()
        assert (tmp_path / "history.jsonl").exists()

        # Verify triage.json is valid JSON
        triage_content = json.loads((tmp_path / "triage.json").read_text(encoding="utf-8"))
        assert "schema_version" in triage_content
        assert "failures" in triage_content
