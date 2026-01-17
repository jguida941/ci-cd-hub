"""Tests for triage detection functions.

Tests cover:
- detect_test_count_regression: Test count drop detection
- detect_flaky_patterns: Flaky test pattern analysis
- detect_gate_changes: Gate status change tracking
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cihub.services.triage.detection import (
    detect_flaky_patterns,
    detect_gate_changes,
    detect_test_count_regression,
)
from cihub.services.triage.types import TEST_COUNT_DROP_THRESHOLD


# =============================================================================
# detect_test_count_regression Tests
# =============================================================================


class TestDetectTestCountRegression:
    """Tests for detect_test_count_regression function."""

    def test_no_history_file_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty list when history file doesn't exist."""
        history_path = tmp_path / "nonexistent.jsonl"

        result = detect_test_count_regression(history_path, current_count=100)

        assert result == []

    def test_current_count_zero_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty list when current count is zero."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"tests_total": 100}\n')

        result = detect_test_count_regression(history_path, current_count=0)

        assert result == []

    def test_empty_history_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty list when history file is empty."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text("")

        result = detect_test_count_regression(history_path, current_count=100)

        assert result == []

    def test_previous_count_zero_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty list when previous count is zero."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"tests_total": 0}\n')

        result = detect_test_count_regression(history_path, current_count=100)

        assert result == []

    def test_no_regression_below_threshold(self, tmp_path: Path) -> None:
        """No warning when drop is below threshold."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"tests_total": 100}\n')

        # Drop of 5% (below 10% threshold)
        result = detect_test_count_regression(history_path, current_count=95)

        assert result == []

    def test_detects_regression_above_threshold(self, tmp_path: Path) -> None:
        """Detects regression when drop exceeds threshold."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"tests_total": 100}\n')

        # Drop of 15% (above 10% threshold)
        result = detect_test_count_regression(history_path, current_count=85)

        assert len(result) == 1
        assert result[0]["type"] == "test_count_regression"
        assert result[0]["severity"] == "warning"
        assert result[0]["previous_count"] == 100
        assert result[0]["current_count"] == 85
        assert result[0]["drop_percentage"] == 15.0
        assert "dropped" in result[0]["message"].lower()

    def test_exact_threshold_no_regression(self, tmp_path: Path) -> None:
        """No warning when drop is exactly at threshold."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"tests_total": 100}\n')

        # Exactly 10% drop (at threshold, not above)
        result = detect_test_count_regression(history_path, current_count=90)

        assert result == []

    def test_uses_most_recent_entry(self, tmp_path: Path) -> None:
        """Uses the most recent entry from history."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"tests_total": 50}',
            '{"tests_total": 75}',
            '{"tests_total": 100}',  # Most recent
        ]
        history_path.write_text("\n".join(entries))

        # 20% drop from 100 (most recent)
        result = detect_test_count_regression(history_path, current_count=80)

        assert len(result) == 1
        assert result[0]["previous_count"] == 100

    def test_handles_malformed_json(self, tmp_path: Path) -> None:
        """Handles malformed JSON gracefully."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text("not valid json\n")

        result = detect_test_count_regression(history_path, current_count=100)

        assert result == []

    def test_handles_missing_tests_total_key(self, tmp_path: Path) -> None:
        """Handles missing tests_total key."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"other_key": 100}\n')

        result = detect_test_count_regression(history_path, current_count=80)

        assert result == []

    def test_warning_includes_hint(self, tmp_path: Path) -> None:
        """Warning includes helpful hint."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"tests_total": 100}\n')

        result = detect_test_count_regression(history_path, current_count=80)

        assert "hint" in result[0]
        assert "cihub triage" in result[0]["hint"]


# =============================================================================
# detect_flaky_patterns Tests
# =============================================================================


class TestDetectFlakyPatterns:
    """Tests for detect_flaky_patterns function."""

    def test_no_history_file(self, tmp_path: Path) -> None:
        """Returns default result when no history file."""
        history_path = tmp_path / "nonexistent.jsonl"

        result = detect_flaky_patterns(history_path)

        assert result["flakiness_score"] == 0.0
        assert result["runs_analyzed"] == 0
        assert result["suspected_flaky"] is False
        assert "No history available" in result["recommendation"]

    def test_insufficient_runs(self, tmp_path: Path) -> None:
        """Returns early when insufficient runs for analysis."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"overall_status": "success", "failure_count": 0}',
            '{"overall_status": "failed", "failure_count": 1}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert result["runs_analyzed"] == 2
        assert "Need at least 5 runs" in result["recommendation"]

    def test_stable_all_passing(self, tmp_path: Path) -> None:
        """Low flakiness score when all runs pass."""
        history_path = tmp_path / "history.jsonl"
        entries = ['{"overall_status": "success", "failure_count": 0}'] * 10
        history_path.write_text("\n".join(entries))

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert result["flakiness_score"] == 0.0
        assert result["state_changes"] == 0
        assert result["suspected_flaky"] is False
        assert "appears stable" in result["recommendation"]

    def test_stable_all_failing(self, tmp_path: Path) -> None:
        """Low flakiness score when all runs fail consistently."""
        history_path = tmp_path / "history.jsonl"
        entries = ['{"overall_status": "failed", "failure_count": 1}'] * 10
        history_path.write_text("\n".join(entries))

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert result["flakiness_score"] == 0.0
        assert result["state_changes"] == 0
        assert result["suspected_flaky"] is False

    def test_detects_high_flakiness(self, tmp_path: Path) -> None:
        """Detects high flakiness when runs alternate pass/fail."""
        history_path = tmp_path / "history.jsonl"
        # Alternating pattern: pass, fail, pass, fail, pass
        entries = [
            '{"overall_status": "success", "failure_count": 0}',
            '{"overall_status": "failed", "failure_count": 1}',
            '{"overall_status": "success", "failure_count": 0}',
            '{"overall_status": "failed", "failure_count": 1}',
            '{"overall_status": "success", "failure_count": 0}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert result["flakiness_score"] > 30  # High flakiness
        assert result["state_changes"] == 4
        assert result["suspected_flaky"] is True
        assert "Flaky behavior detected" in result["recommendation"]

    def test_detects_failure_count_variance(self, tmp_path: Path) -> None:
        """Detects flakiness from high failure count variance."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"overall_status": "failed", "failure_count": 1}',
            '{"overall_status": "failed", "failure_count": 5}',
            '{"overall_status": "failed", "failure_count": 2}',
            '{"overall_status": "failed", "failure_count": 10}',
            '{"overall_status": "failed", "failure_count": 1}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert result["suspected_flaky"] is True
        assert any("variance" in d.lower() for d in result["details"])

    def test_includes_recent_history(self, tmp_path: Path) -> None:
        """Result includes recent history summary."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"overall_status": "success", "failure_count": 0}',
            '{"overall_status": "success", "failure_count": 0}',
            '{"overall_status": "failed", "failure_count": 1}',
            '{"overall_status": "success", "failure_count": 0}',
            '{"overall_status": "success", "failure_count": 0}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert "recent_history" in result
        # Full words used: "pass" and "fail" concatenated
        assert result["recent_history"] == "passpassfailpasspass"

    def test_handles_malformed_json(self, tmp_path: Path) -> None:
        """Handles malformed JSON gracefully."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text("invalid json\n" * 10)

        result = detect_flaky_patterns(history_path, min_runs=5)

        assert "Error analyzing" in result["recommendation"]


# =============================================================================
# detect_gate_changes Tests
# =============================================================================


class TestDetectGateChanges:
    """Tests for detect_gate_changes function."""

    def test_no_history_file(self, tmp_path: Path) -> None:
        """Returns default result when no history file."""
        history_path = tmp_path / "nonexistent.jsonl"

        result = detect_gate_changes(history_path)

        assert result["runs_analyzed"] == 0
        assert result["new_failures"] == []
        assert result["fixed_gates"] == []
        assert "No history available" in result["summary"]

    def test_insufficient_runs(self, tmp_path: Path) -> None:
        """Returns early when insufficient runs."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text('{"gate_failures": ["pytest"]}\n')

        result = detect_gate_changes(history_path, min_runs=2)

        assert result["runs_analyzed"] == 1
        assert "Need at least 2 runs" in result["summary"]

    def test_detects_new_failures(self, tmp_path: Path) -> None:
        """Detects newly failing gates.

        A gate is considered "new failure" when:
        - It has been tracked for at least min_runs entries
        - It's failing in recent runs
        - No failures in "older" history (>3 entries back)

        Since gates only enter history when they first fail,
        a new failure is one that started failing recently (within 3 runs)
        and has been consistently failing since.
        """
        history_path = tmp_path / "history.jsonl"
        # "ruff" appears and fails in the first 2 runs, making it:
        # - Observed for >= min_runs (2)
        # - Failing in recent entries
        # - No "older" history (since total entries <= 3)
        entries = [
            '{"gate_failures": ["ruff"]}',  # ruff starts failing
            '{"gate_failures": ["ruff"]}',  # ruff still failing
        ]
        history_path.write_text("\n".join(entries))

        result = detect_gate_changes(history_path, min_runs=2)

        assert "ruff" in result["new_failures"]
        assert "New failures: ruff" in result["summary"]

    def test_detects_fixed_gates(self, tmp_path: Path) -> None:
        """Detects recently fixed gates."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"gate_failures": ["pytest"]}',  # Failing
            '{"gate_failures": ["pytest"]}',  # Failing
            '{"gate_failures": ["pytest"]}',  # Failing
            '{"gate_failures": []}',  # Fixed
        ]
        history_path.write_text("\n".join(entries))

        result = detect_gate_changes(history_path, min_runs=2)

        assert "pytest" in result["fixed_gates"]
        assert "Fixed gates: pytest" in result["summary"]

    def test_detects_recurring_failures(self, tmp_path: Path) -> None:
        """Detects gates that fail repeatedly."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"gate_failures": ["bandit"]}',
            '{"gate_failures": ["bandit"]}',
            '{"gate_failures": []}',
            '{"gate_failures": ["bandit"]}',
            '{"gate_failures": ["bandit"]}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_gate_changes(history_path, min_runs=2)

        recurring_names = [r["gate"] for r in result["recurring_failures"]]
        assert "bandit" in recurring_names
        # Fail rate should be 80% (4/5)
        bandit_info = next(r for r in result["recurring_failures"] if r["gate"] == "bandit")
        assert bandit_info["fail_rate"] == 80.0

    def test_tracks_gate_history(self, tmp_path: Path) -> None:
        """Tracks per-gate history."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"gate_failures": ["pytest"]}',
            '{"gate_failures": []}',
            '{"gate_failures": ["pytest"]}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_gate_changes(history_path, min_runs=2)

        assert "pytest" in result["gate_history"]
        assert result["gate_history"]["pytest"] == ["fail", "pass", "fail"]

    def test_no_changes_summary(self, tmp_path: Path) -> None:
        """Summary indicates no changes when stable."""
        history_path = tmp_path / "history.jsonl"
        entries = [
            '{"gate_failures": []}',
            '{"gate_failures": []}',
            '{"gate_failures": []}',
        ]
        history_path.write_text("\n".join(entries))

        result = detect_gate_changes(history_path, min_runs=2)

        assert "No significant gate changes" in result["summary"]

    def test_handles_malformed_json(self, tmp_path: Path) -> None:
        """Handles malformed JSON gracefully."""
        history_path = tmp_path / "history.jsonl"
        history_path.write_text("invalid\n" * 5)

        result = detect_gate_changes(history_path, min_runs=2)

        assert "Error analyzing" in result["summary"]


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_threshold_is_reasonable(self) -> None:
        """TEST_COUNT_DROP_THRESHOLD is reasonable (5-20%)."""
        assert 0.05 <= TEST_COUNT_DROP_THRESHOLD <= 0.20
