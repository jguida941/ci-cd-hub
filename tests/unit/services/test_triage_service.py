"""Tests for triage bundle generation."""

# TEST-METRICS:
#   Coverage: 93.2%

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cihub.services.triage_service import (
    TRIAGE_SCHEMA_VERSION,
    ToolStatus,
    aggregate_triage_bundles,
    build_tool_evidence,
    detect_flaky_patterns,
    generate_triage_bundle,
    validate_artifact_evidence,
    write_triage_bundle,
)


def _write_report(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_report(
    repo: str = "acme/widgets",
    tools_configured: dict[str, bool] | None = None,
    tools_ran: dict[str, bool] | None = None,
    tools_success: dict[str, bool] | None = None,
    tools_require_run: dict[str, bool] | None = None,
    tool_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Helper to create test reports."""
    return {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": "0.0.0-test",
            "workflow_ref": "test",
            "generated_at": "2024-01-01T00:00:00Z",
        },
        "repository": repo,
        "branch": "main",
        "run_id": "123",
        "run_number": "1",
        "commit": "a" * 40,
        "timestamp": "2024-01-01T00:00:00Z",
        "python_version": "3.12",
        "tools_configured": tools_configured or {},
        "tools_ran": tools_ran or {},
        "tools_success": tools_success or {},
        "tools_require_run": tools_require_run or {},
        "tool_metrics": tool_metrics or {},
        "results": {
            "tests_passed": 10,
            "tests_failed": 0,
            "coverage": 80,
            "mutation_score": 0,
            "critical_vulns": 0,
            "high_vulns": 0,
            "medium_vulns": 0,
        },
        "environment": {"workdir": "."},
    }


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
    assert bundle.triage["schema_version"] == TRIAGE_SCHEMA_VERSION
    failures = bundle.triage["failures"]
    assert any(failure["tool"] == "ruff" for failure in failures)


def test_generate_triage_missing_report(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    bundle = generate_triage_bundle(output_dir)
    failures = bundle.triage["failures"]
    assert failures
    assert failures[0]["tool"] == "cihub"
    assert failures[0]["reason"] in {"missing_report", "invalid_report"}


def test_optional_skip_does_not_fail_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / ".cihub"
    report_path = output_dir / "report.json"
    report = _make_report(
        tools_configured={"mypy": True},
        tools_ran={"mypy": False},
        tools_success={},
        tools_require_run={"mypy": False},
    )
    _write_report(report_path, report)

    bundle = generate_triage_bundle(output_dir, report_path=report_path)

    assert bundle.triage["summary"]["overall_status"] == "passed"
    assert bundle.triage["summary"]["failure_count"] == 0
    assert bundle.triage["summary"]["skipped_count"] == 1


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


def test_detect_test_count_regression(tmp_path: Path) -> None:
    """Detect test count drops >10% between runs (Issue 16)."""
    from cihub.services.triage_service import detect_test_count_regression

    history_path = tmp_path / "history.jsonl"

    # No history file = no warnings
    warnings = detect_test_count_regression(history_path, 100)
    assert warnings == []

    # Create history with 100 tests
    history_path.write_text(
        json.dumps({"tests_total": 100, "timestamp": "2024-01-01"}) + "\n",
        encoding="utf-8",
    )

    # Same count = no warning
    warnings = detect_test_count_regression(history_path, 100)
    assert len(warnings) == 0

    # 5% drop = no warning (below threshold)
    warnings = detect_test_count_regression(history_path, 95)
    assert len(warnings) == 0

    # 15% drop = warning
    warnings = detect_test_count_regression(history_path, 85)
    assert len(warnings) == 1
    assert warnings[0]["type"] == "test_count_regression"
    assert warnings[0]["severity"] == "warning"
    assert warnings[0]["previous_count"] == 100
    assert warnings[0]["current_count"] == 85
    assert "15" in warnings[0]["message"]  # 15% drop

    # 50% drop = warning
    warnings = detect_test_count_regression(history_path, 50)
    assert len(warnings) == 1
    assert warnings[0]["drop_percentage"] == 50.0


def test_history_entry_includes_test_counts(tmp_path: Path) -> None:
    """History entry includes test counts for trend analysis (Issue 16)."""
    output_dir = tmp_path / ".cihub"
    report_path = output_dir / "report.json"
    report = {
        "schema_version": "2.0",
        "repository": "acme/widgets",
        "branch": "main",
        "commit": "deadbeef",
        "results": {
            "tests_passed": 100,
            "tests_failed": 5,
            "tests_skipped": 3,
            "coverage": 85.5,
            "mutation_score": 72.0,
        },
        "tools_configured": {"pytest": True, "ruff": True},
        "tools_ran": {"pytest": True, "ruff": True},
        "tools_success": {"pytest": False, "ruff": True},
        "environment": {"workdir": "."},
    }
    _write_report(report_path, report)

    bundle = generate_triage_bundle(output_dir, report_path=report_path)

    # Verify history entry contains test counts
    entry = bundle.history_entry
    assert entry["tests_total"] == 108  # 100 + 5 + 3
    assert entry["tests_passed"] == 100
    assert entry["tests_failed"] == 5
    assert entry["tests_skipped"] == 3
    assert entry["coverage"] == 85.5
    assert entry["mutation_score"] == 72.0
    # Tool counts
    assert entry["tools_configured"] == 2
    assert entry["tools_ran"] == 2
    assert entry["tools_passed"] >= 1  # At least ruff passed
    assert entry["tools_failed"] >= 0


# =============================================================================
# Tool Evidence Tests
# =============================================================================


class TestToolEvidence:
    """Tests for build_tool_evidence function."""

    def test_passed_tool_has_correct_status(self) -> None:
        """Tool that ran and succeeded should be PASSED."""
        report = _make_report(
            tools_configured={"ruff": True},
            tools_ran={"ruff": True},
            tools_success={"ruff": True},
        )
        evidence = build_tool_evidence(report)
        ruff_evidence = next(e for e in evidence if e.tool == "ruff")

        assert ruff_evidence.status == ToolStatus.PASSED
        assert ruff_evidence.configured is True
        assert ruff_evidence.ran is True
        assert ruff_evidence.success is True
        assert "successfully" in ruff_evidence.explanation

    def test_failed_tool_has_correct_status(self) -> None:
        """Tool that ran but failed should be FAILED."""
        report = _make_report(
            tools_configured={"ruff": True},
            tools_ran={"ruff": True},
            tools_success={"ruff": False},
        )
        evidence = build_tool_evidence(report)
        ruff_evidence = next(e for e in evidence if e.tool == "ruff")

        assert ruff_evidence.status == ToolStatus.FAILED
        assert ruff_evidence.ran is True
        assert ruff_evidence.success is False
        assert "failed" in ruff_evidence.explanation.lower()

    def test_unknown_tool_status_when_success_missing(self, tmp_path: Path) -> None:
        """Tool that ran without tools_success should be UNKNOWN and not fail summary."""
        output_dir = tmp_path / ".cihub"
        report_path = output_dir / "report.json"
        report = _make_report(
            tools_configured={"ruff": True},
            tools_ran={"ruff": True},
            tools_success={},
        )
        _write_report(report_path, report)

        bundle = generate_triage_bundle(output_dir, report_path=report_path)

        ruff_evidence = next(e for e in bundle.triage["tool_evidence"] if e["tool"] == "ruff")
        assert ruff_evidence["status"] == ToolStatus.UNKNOWN.value
        assert ruff_evidence["success"] is None
        assert bundle.triage["summary"]["overall_status"] == "passed"
        assert bundle.triage["summary"]["failure_count"] == 0
        assert any(
            warning.get("type") == "missing_tool_success"
            for warning in bundle.triage.get("warnings", [])
        )

    def test_skipped_tool_has_correct_status(self) -> None:
        """Tool configured but not ran (no require_run) should be SKIPPED."""
        report = _make_report(
            tools_configured={"mypy": True},
            tools_ran={"mypy": False},
            tools_success={},
            tools_require_run={"mypy": False},
        )
        evidence = build_tool_evidence(report)
        mypy_evidence = next(e for e in evidence if e.tool == "mypy")

        assert mypy_evidence.status == ToolStatus.SKIPPED
        assert mypy_evidence.configured is True
        assert mypy_evidence.ran is False
        assert "skipped" in mypy_evidence.explanation.lower()

    def test_required_not_run_has_correct_status(self) -> None:
        """Tool with require_run=true that didn't run should be REQUIRED_NOT_RUN."""
        report = _make_report(
            tools_configured={"bandit": True},
            tools_ran={"bandit": False},
            tools_success={},
            tools_require_run={"bandit": True},
        )
        evidence = build_tool_evidence(report)
        bandit_evidence = next(e for e in evidence if e.tool == "bandit")

        assert bandit_evidence.status == ToolStatus.REQUIRED_NOT_RUN
        assert bandit_evidence.require_run is True
        assert bandit_evidence.ran is False
        assert "HARD FAIL" in bandit_evidence.explanation

    def test_evidence_includes_metrics(self) -> None:
        """Evidence should include relevant metrics for the tool."""
        report = _make_report(
            tools_configured={"ruff": True},
            tools_ran={"ruff": True},
            tools_success={"ruff": True},
            tool_metrics={"ruff_errors": 0},
        )
        evidence = build_tool_evidence(report)
        ruff_evidence = next(e for e in evidence if e.tool == "ruff")

        assert "ruff_errors" in ruff_evidence.metrics
        assert ruff_evidence.metrics["ruff_errors"] == 0

    def test_triage_includes_tool_evidence(self, tmp_path: Path) -> None:
        """Triage bundle should include tool_evidence section."""
        output_dir = tmp_path / ".cihub"
        report_path = output_dir / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "pytest": True},
            tools_ran={"ruff": True, "pytest": True},
            tools_success={"ruff": False, "pytest": True},
        )
        _write_report(report_path, report)

        bundle = generate_triage_bundle(output_dir, report_path=report_path)

        assert "tool_evidence" in bundle.triage
        tool_evidence = bundle.triage["tool_evidence"]
        assert len(tool_evidence) == 2
        assert any(e["tool"] == "ruff" and e["status"] == "failed" for e in tool_evidence)
        assert any(e["tool"] == "pytest" and e["status"] == "passed" for e in tool_evidence)


class TestArtifactEvidence:
    """Tests for validate_artifact_evidence function."""

    def test_no_issues_when_metrics_present(self, tmp_path: Path) -> None:
        """No issues when tool has metrics."""
        report = _make_report(
            tools_ran={"ruff": True},
            tools_success={"ruff": True},
            tool_metrics={"ruff_errors": 0},
        )
        # Disable schema validation for this test (partial report)
        issues = validate_artifact_evidence(report, tmp_path, run_schema_validation=False)

        # ruff should have no issues since it has metrics
        ruff_issues = [i for i in issues if i["tool"] == "ruff"]
        assert len(ruff_issues) == 0

    def test_warning_when_no_metrics_or_artifacts(self, tmp_path: Path) -> None:
        """Warning when tool marked success but has no evidence."""
        report = _make_report(
            tools_ran={"sbom": True},  # sbom has no metrics defined
            tools_success={"sbom": True},
            tool_metrics={},
        )
        # Disable schema validation for this test (partial report)
        issues = validate_artifact_evidence(report, tmp_path, run_schema_validation=False)

        sbom_issues = [i for i in issues if i["tool"] == "sbom"]
        assert len(sbom_issues) == 1
        assert sbom_issues[0]["issue"] == "no_evidence"

    def test_info_when_failed_tool_has_no_artifacts(self, tmp_path: Path) -> None:
        """Info when failed tool has no artifacts for debugging."""
        report = _make_report(
            tools_ran={"bandit": True},
            tools_success={"bandit": False},
            tool_metrics={},  # No metrics
        )
        issues = validate_artifact_evidence(report, tmp_path, run_schema_validation=False)

        bandit_issues = [i for i in issues if i["tool"] == "bandit"]
        assert len(bandit_issues) == 1
        assert bandit_issues[0]["issue"] == "no_failure_artifacts"
        assert bandit_issues[0]["severity"] == "info"

    def test_runs_schema_validation_by_default(self, tmp_path: Path) -> None:
        """Schema validation runs by default and catches invalid reports."""
        report = {
            "schema_version": "9.9",  # Invalid version
            "python_version": "3.12",
            "tools_ran": {},
            "tools_success": {},
        }
        issues = validate_artifact_evidence(report, tmp_path, run_schema_validation=True)

        schema_issues = [i for i in issues if i["tool"] == "schema"]
        assert len(schema_issues) > 0
        assert schema_issues[0]["severity"] == "error"
        assert schema_issues[0]["issue"] == "schema_violation"

    def test_runs_report_validation_consistency_only(self, tmp_path: Path) -> None:
        """Report validation runs (consistency-only) and catches structural issues."""
        report = {
            "schema_version": "2.0",
            "python_version": "3.12",
            "tools_ran": {},  # Invalid: no tools recorded
            "tools_success": {},
        }

        issues = validate_artifact_evidence(report, tmp_path, run_schema_validation=False)

        validator_issues = [i for i in issues if i["tool"] == "validator" and i["severity"] == "error"]
        assert any("tools_ran is empty" in str(i.get("message", "")) for i in validator_issues)


class TestMultiTriageAggregation:
    """Tests for aggregate_triage_bundles function."""

    def test_aggregates_multiple_bundles(self, tmp_path: Path) -> None:
        """Aggregates multiple triage bundles into summary."""
        # Create two report directories
        repo1_dir = tmp_path / "repo1" / ".cihub"
        repo2_dir = tmp_path / "repo2" / ".cihub"

        report1 = _make_report(
            repo="acme/repo1",
            tools_configured={"ruff": True},
            tools_ran={"ruff": True},
            tools_success={"ruff": True},
        )
        report2 = _make_report(
            repo="acme/repo2",
            tools_configured={"ruff": True, "bandit": True},
            tools_ran={"ruff": True, "bandit": True},
            tools_success={"ruff": False, "bandit": False},
        )

        _write_report(repo1_dir / "report.json", report1)
        _write_report(repo2_dir / "report.json", report2)

        bundle1 = generate_triage_bundle(repo1_dir)
        bundle2 = generate_triage_bundle(repo2_dir)

        result = aggregate_triage_bundles([bundle1, bundle2])

        assert result.repo_count == 2
        assert result.passed_count == 1
        assert result.failed_count == 1
        assert "acme/repo1" in [r["repo"] for r in result.repos]
        assert "acme/repo2" in [r["repo"] for r in result.repos]

    def test_success_status_counts_as_passed(self, tmp_path: Path) -> None:
        """Treat success status as passed in aggregation."""
        repo_dir = tmp_path / "repo1" / ".cihub"
        report = _make_report(
            repo="acme/widgets",
            tools_configured={"ruff": True},
            tools_ran={"ruff": True},
            tools_success={"ruff": True},
        )
        _write_report(repo_dir / "report.json", report)

        bundle = generate_triage_bundle(repo_dir)
        bundle.triage["summary"]["overall_status"] = "success"

        result = aggregate_triage_bundles([bundle])

        assert result.passed_count == 1
        assert result.failed_count == 0
        assert "| acme/widgets | passed |" in result.summary_markdown

    def test_failures_by_tool_aggregation(self, tmp_path: Path) -> None:
        """Tracks which repos failed for each tool."""
        repo1_dir = tmp_path / "repo1" / ".cihub"
        repo2_dir = tmp_path / "repo2" / ".cihub"
        repo3_dir = tmp_path / "repo3" / ".cihub"

        # repo1: ruff fails
        # repo2: ruff and bandit fail
        # repo3: all pass
        _write_report(
            repo1_dir / "report.json",
            _make_report(
                repo="acme/repo1",
                tools_configured={"ruff": True},
                tools_ran={"ruff": True},
                tools_success={"ruff": False},
            ),
        )
        _write_report(
            repo2_dir / "report.json",
            _make_report(
                repo="acme/repo2",
                tools_configured={"ruff": True, "bandit": True},
                tools_ran={"ruff": True, "bandit": True},
                tools_success={"ruff": False, "bandit": False},
            ),
        )
        _write_report(
            repo3_dir / "report.json",
            _make_report(
                repo="acme/repo3",
                tools_configured={"ruff": True},
                tools_ran={"ruff": True},
                tools_success={"ruff": True},
            ),
        )

        bundles = [
            generate_triage_bundle(repo1_dir),
            generate_triage_bundle(repo2_dir),
            generate_triage_bundle(repo3_dir),
        ]
        result = aggregate_triage_bundles(bundles)

        # ruff failed in 2 repos
        assert "ruff" in result.failures_by_tool
        assert len(result.failures_by_tool["ruff"]) == 2

        # bandit failed in 1 repo
        assert "bandit" in result.failures_by_tool
        assert len(result.failures_by_tool["bandit"]) == 1

    def test_summary_markdown_generation(self, tmp_path: Path) -> None:
        """Generates readable markdown summary."""
        repo1_dir = tmp_path / "repo1" / ".cihub"
        _write_report(
            repo1_dir / "report.json",
            _make_report(
                repo="acme/repo1",
                tools_configured={"ruff": True},
                tools_ran={"ruff": True},
                tools_success={"ruff": False},
            ),
        )

        bundles = [generate_triage_bundle(repo1_dir)]
        result = aggregate_triage_bundles(bundles)

        assert "# Multi-Repo Triage Summary" in result.summary_markdown
        assert "Total Repos" in result.summary_markdown
        assert "acme/repo1" in result.summary_markdown

    def test_required_not_run_counted_in_summary(self, tmp_path: Path) -> None:
        """Required not run tools are counted in triage summary."""
        output_dir = tmp_path / ".cihub"
        report_path = output_dir / "report.json"
        report = _make_report(
            tools_configured={"bandit": True, "pytest": True},
            tools_ran={"bandit": False, "pytest": True},
            tools_success={"pytest": True},
            tools_require_run={"bandit": True},
        )
        _write_report(report_path, report)

        bundle = generate_triage_bundle(output_dir, report_path=report_path)

        assert bundle.triage["summary"]["required_not_run_count"] == 1
        assert bundle.triage["summary"]["overall_status"] == "failed"
        # failure_count=1: tool evidence (required_not_run). Validation runs in consistency_only
        # mode which skips require_run_or_fail checks to avoid double-counting.
        assert bundle.triage["summary"]["failure_count"] == 1
        assert any(
            f.get("tool") == "bandit" and f.get("status") == "required_not_run" for f in bundle.triage["failures"]
        )


class TestRemoteTriageHelpers:
    """Tests for remote triage helper functions."""

    def test_find_all_reports_in_artifacts(self, tmp_path: Path) -> None:
        """Finds all report.json files in artifact directory."""
        from cihub.commands.triage import _find_all_reports_in_artifacts

        # Create multiple report files in different subdirs
        (tmp_path / "repo1" / ".cihub").mkdir(parents=True)
        (tmp_path / "repo2" / ".cihub").mkdir(parents=True)
        (tmp_path / "repo1" / ".cihub" / "report.json").write_text("{}")
        (tmp_path / "repo2" / ".cihub" / "report.json").write_text("{}")

        reports = _find_all_reports_in_artifacts(tmp_path)

        assert len(reports) == 2
        assert all(r.name == "report.json" for r in reports)

    def test_find_all_reports_empty_dir(self, tmp_path: Path) -> None:
        """Returns empty list for directory with no reports."""
        from cihub.commands.triage import _find_all_reports_in_artifacts

        reports = _find_all_reports_in_artifacts(tmp_path)

        assert reports == []

    def test_persistent_artifact_path_structure(self, tmp_path: Path) -> None:
        """Verifies the expected persistent artifact path structure."""
        run_id = "12345678"
        output_dir = tmp_path / ".cihub"
        expected_run_dir = output_dir / "runs" / run_id
        expected_artifacts_dir = expected_run_dir / "artifacts"

        # Simulate what _generate_remote_triage_bundle creates
        expected_artifacts_dir.mkdir(parents=True, exist_ok=True)

        assert expected_run_dir.exists()
        assert expected_artifacts_dir.exists()
        assert expected_artifacts_dir.parent.name == run_id
        assert expected_artifacts_dir.parent.parent.name == "runs"


class TestFlakyDetection:
    """Tests for flaky test pattern detection."""

    def test_detect_flaky_no_history(self, tmp_path: Path) -> None:
        """Returns appropriate message when no history exists."""
        history_path = tmp_path / "triage-history.ndjson"

        result = detect_flaky_patterns(history_path)

        assert result["runs_analyzed"] == 0
        assert result["suspected_flaky"] is False
        assert "No history available" in result["recommendation"]

    def test_detect_flaky_insufficient_runs(self, tmp_path: Path) -> None:
        """Requires minimum runs for analysis."""
        history_path = tmp_path / "triage-history.ndjson"
        # Write only 3 entries (default min is 5)
        entries = [
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "success", "failure_count": 0},
        ]
        history_path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = detect_flaky_patterns(history_path)

        assert result["runs_analyzed"] == 3
        assert "Need at least 5 runs" in result["recommendation"]

    def test_detect_flaky_stable_all_passing(self, tmp_path: Path) -> None:
        """Stable CI (all passing) has flakiness score 0."""
        history_path = tmp_path / "triage-history.ndjson"
        entries = [{"overall_status": "success", "failure_count": 0} for _ in range(10)]
        history_path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = detect_flaky_patterns(history_path)

        assert result["runs_analyzed"] == 10
        assert result["state_changes"] == 0
        assert result["flakiness_score"] == 0.0
        assert result["suspected_flaky"] is False
        assert "stable" in result["recommendation"].lower()

    def test_detect_flaky_alternating_pattern(self, tmp_path: Path) -> None:
        """Alternating pass/fail pattern indicates high flakiness."""
        history_path = tmp_path / "triage-history.ndjson"
        # Alternating pattern: pass, fail, pass, fail, pass, fail
        entries = [
            {"overall_status": "success" if i % 2 == 0 else "failure", "failure_count": 0 if i % 2 == 0 else 1}
            for i in range(6)
        ]
        history_path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = detect_flaky_patterns(history_path)

        assert result["runs_analyzed"] == 6
        assert result["state_changes"] == 5  # 5 transitions in 6 runs
        assert result["flakiness_score"] == 100.0  # Maximum flakiness
        assert result["suspected_flaky"] is True
        assert "Flaky behavior detected" in result["recommendation"]

    def test_detect_flaky_recent_history_text(self, tmp_path: Path) -> None:
        """Recent history is shown as pass/fail text string."""
        history_path = tmp_path / "triage-history.ndjson"
        entries = [
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "failure", "failure_count": 2},
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "success", "failure_count": 0},
        ]
        history_path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = detect_flaky_patterns(history_path)

        assert "recent_history" in result
        assert "pass" in result["recent_history"]
        assert "fail" in result["recent_history"]

    def test_detect_flaky_failure_count_variance(self, tmp_path: Path) -> None:
        """High variance in failure counts indicates instability."""
        history_path = tmp_path / "triage-history.ndjson"
        # All failing but with varying failure counts
        entries = [
            {"overall_status": "failure", "failure_count": 1},
            {"overall_status": "failure", "failure_count": 5},
            {"overall_status": "failure", "failure_count": 2},
            {"overall_status": "failure", "failure_count": 8},
            {"overall_status": "failure", "failure_count": 1},
        ]
        history_path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = detect_flaky_patterns(history_path)

        # No state changes (all failures) but high variance in failure counts
        assert result["state_changes"] == 0
        assert result["suspected_flaky"] is True  # Due to variance
        assert any("variance" in d.lower() for d in result["details"])


# =============================================================================
# Tool Verification Tests
# =============================================================================


class TestToolVerification:
    """Tests for _verify_tools_from_report function."""

    def test_verify_tools_all_passed(self, tmp_path: Path) -> None:
        """All configured tools ran and succeeded with proof (metrics)."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "pytest": True},
            tools_ran={"ruff": True, "pytest": True},
            tools_success={"ruff": True, "pytest": True},
            tool_metrics={"ruff_errors": 0},  # Provide proof for ruff
        )
        # Add pytest proof via results
        report["results"] = {"tests_passed": 10, "coverage": 80}
        _write_report(report_path, report)

        result = _verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is True
        assert len(result["passed"]) == 2
        assert len(result["drift"]) == 0
        assert len(result["failures"]) == 0
        assert "ruff" in result["passed"]
        assert "pytest" in result["passed"]

    def test_verify_tools_drift_detected(self, tmp_path: Path) -> None:
        """Detect drift when configured tool didn't run."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "mypy": True},
            tools_ran={"ruff": True, "mypy": False},
            tools_success={"ruff": True},
        )
        _write_report(report_path, report)

        result = _verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is False
        assert len(result["drift"]) == 1
        assert result["drift"][0]["tool"] == "mypy"
        assert result["counts"]["drift"] == 1
        assert result["counts"]["no_proof"] == 1

    def test_verify_tools_optional_not_counted_as_drift(self, tmp_path: Path) -> None:
        """Configured but optional tools should not fail verification."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "mypy": True},
            tools_ran={"ruff": True, "mypy": False},
            tools_success={"ruff": True},
            tools_require_run={"mypy": False},
            tool_metrics={"ruff_errors": 0},
        )
        _write_report(report_path, report)

        result = _verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is True
        assert len(result["drift"]) == 0
        assert result["optional"][0]["tool"] == "mypy"

    def test_verify_tools_failure_detected(self, tmp_path: Path) -> None:
        """Detect tool failures."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "pytest": True},
            tools_ran={"ruff": True, "pytest": True},
            tools_success={"ruff": True, "pytest": False},
        )
        _write_report(report_path, report)

        result = _verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is False
        assert len(result["failures"]) == 1
        assert result["failures"][0]["tool"] == "pytest"
        assert "failed" in result["summary"].lower()

    def test_verify_tools_skipped_not_counted_as_drift(self, tmp_path: Path) -> None:
        """Tools not configured should be skipped, not counted as drift."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "mypy": False},
            tools_ran={"ruff": True},
            tools_success={"ruff": True},
            tool_metrics={"ruff_errors": 0},  # Provide proof for ruff
        )
        _write_report(report_path, report)

        result = _verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is True
        assert "mypy" in result["skipped"]
        assert len(result["drift"]) == 0

    def test_verify_tools_report_not_found(self, tmp_path: Path) -> None:
        """Handle missing report gracefully."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "nonexistent.json"

        result = _verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is False
        assert "not found" in result["summary"].lower()

    def test_verify_tools_counts_correct(self, tmp_path: Path) -> None:
        """Verify counts are correct."""
        from cihub.commands.triage import _verify_tools_from_report

        report_path = tmp_path / "report.json"
        report = _make_report(
            tools_configured={"ruff": True, "pytest": True, "mypy": True, "bandit": False},
            tools_ran={"ruff": True, "pytest": True, "mypy": False},
            tools_success={"ruff": True, "pytest": False},
        )
        _write_report(report_path, report)

        result = _verify_tools_from_report(report_path, tmp_path)

        counts = result["counts"]
        assert counts["passed"] == 1  # ruff
        assert counts["failures"] == 1  # pytest
        assert counts["drift"] == 1  # mypy
        assert counts["optional"] == 0
        assert counts["skipped"] == 1  # bandit
