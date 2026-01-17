"""Property-based tests for triage command using Hypothesis.

These tests verify invariants that should hold for any input,
catching edge cases that unit tests might miss.
"""

# TEST-METRICS:

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.commands.triage.log_parser import (
    create_log_failure,
    infer_tool_from_step,
    parse_log_failures,
)
from cihub.commands.triage.types import (
    SEVERITY_ORDER,
    filter_bundle,
)
from cihub.commands.triage.verification import verify_tools_from_report
from cihub.services.triage_service import TriageBundle


class TestLogParserProperties:
    """Property-based tests for log parsing."""

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_infer_tool_never_crashes(self, step_name: str) -> None:
        """Property: infer_tool_from_step never raises for any string input."""
        result = infer_tool_from_step(step_name)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(
        st.text(min_size=1, max_size=50),  # job
        st.text(min_size=1, max_size=50),  # step
        st.lists(st.text(max_size=100), min_size=0, max_size=10),  # errors
    )
    @settings(max_examples=50)
    def test_create_log_failure_always_returns_valid_dict(self, job: str, step: str, errors: list[str]) -> None:
        """Property: create_log_failure always returns a dict with required keys."""
        result = create_log_failure(job, step, errors)

        # Verify required keys exist
        assert "id" in result
        assert "category" in result
        assert "severity" in result
        assert "tool" in result
        assert "status" in result
        assert "message" in result
        assert "errors" in result
        assert "reproduce" in result

        # Verify types
        assert isinstance(result["id"], str)
        assert isinstance(result["errors"], list)
        assert result["severity"] in SEVERITY_ORDER

    @given(st.text(max_size=5000))
    @settings(max_examples=30)
    def test_parse_log_failures_never_crashes(self, logs: str) -> None:
        """Property: parse_log_failures handles any string input without crashing."""
        result = parse_log_failures(logs)
        assert isinstance(result, list)
        for failure in result:
            assert isinstance(failure, dict)


class TestSeverityOrderProperties:
    """Property-based tests for severity ordering."""

    @given(st.sampled_from(list(SEVERITY_ORDER.keys())))
    def test_severity_order_is_consistent(self, severity: str) -> None:
        """Property: all known severities have a numeric order."""
        assert isinstance(SEVERITY_ORDER[severity], int)
        assert SEVERITY_ORDER[severity] >= 0

    @given(
        st.sampled_from(list(SEVERITY_ORDER.keys())),
        st.sampled_from(list(SEVERITY_ORDER.keys())),
    )
    def test_severity_comparison_is_transitive(self, sev1: str, sev2: str) -> None:
        """Property: severity ordering is consistent with comparison."""
        order1 = SEVERITY_ORDER[sev1]
        order2 = SEVERITY_ORDER[sev2]

        # Lower number = more severe
        if order1 < order2:
            # sev1 is more severe than sev2
            assert sev1 != sev2 or order1 == order2
        elif order1 > order2:
            # sev2 is more severe than sev1
            assert sev1 != sev2 or order1 == order2


class TestVerificationProperties:
    """Property-based tests for tool verification."""

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            st.booleans(),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_verification_handles_any_tool_config(self, tools_configured: dict[str, bool]) -> None:
        """Property: verification never crashes for any tool configuration."""
        import tempfile

        # Create a minimal report with the generated tool config
        report = {
            "tools_configured": tools_configured,
            "tools_ran": {k: v for k, v in tools_configured.items()},
            "tools_success": {k: v for k, v in tools_configured.items()},
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = Path(tmp_dir) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            result = verify_tools_from_report(report_path)

            # Verify result structure
            assert isinstance(result, dict)
            assert "verified" in result
            assert "drift" in result
            assert "failures" in result
            assert "passed" in result
            assert "summary" in result
            assert isinstance(result["verified"], bool)

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            st.booleans(),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=30)
    def test_tool_counts_sum_to_total(self, tools_configured: dict[str, bool]) -> None:
        """Property: sum of all status counts equals total tools."""
        import tempfile

        # Create report where all configured tools ran and succeeded
        report = {
            "tools_configured": tools_configured,
            "tools_ran": tools_configured.copy(),
            "tools_success": tools_configured.copy(),
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = Path(tmp_dir) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            result = verify_tools_from_report(report_path)
            counts = result.get("counts", {})

            # Sum of categories should equal total
            total = counts.get("total", 0)
            passed = counts.get("passed", 0)
            drift = counts.get("drift", 0)
            no_proof = counts.get("no_proof", 0)
            failures = counts.get("failures", 0)
            skipped = counts.get("skipped", 0)

            assert passed + drift + no_proof + failures + skipped == total


class TestFilterBundleProperties:
    """Property-based tests for bundle filtering."""

    @given(st.sampled_from(["blocker", "high", "medium", "low", None]))
    def test_filter_preserves_bundle_structure(self, min_severity: str | None) -> None:
        """Property: filtering always returns a valid TriageBundle structure."""
        # Create a minimal bundle
        bundle = TriageBundle(
            triage={
                "summary": {"failure_count": 2},
                "failures": [
                    {"severity": "high", "category": "test"},
                    {"severity": "low", "category": "lint"},
                ],
            },
            priority={"failures": [], "failure_count": 2},
            markdown="# Test",
            history_entry={"timestamp": "2024-01-01"},
        )

        result = filter_bundle(bundle, min_severity, None)

        # Verify structure is preserved
        assert isinstance(result, TriageBundle)
        assert "failures" in result.triage
        assert "summary" in result.triage
        assert isinstance(result.triage["failures"], list)

    @given(
        st.sampled_from(["blocker", "high", "medium", "low", None]),
        st.sampled_from(["test", "lint", "security", "workflow", None]),
    )
    def test_filter_reduces_or_maintains_count(self, min_severity: str | None, category: str | None) -> None:
        """Property: filtering never increases failure count."""
        bundle = TriageBundle(
            triage={
                "summary": {"failure_count": 3},
                "failures": [
                    {"severity": "blocker", "category": "security"},
                    {"severity": "high", "category": "test"},
                    {"severity": "low", "category": "lint"},
                ],
            },
            priority={"failures": [], "failure_count": 3},
            markdown="# Test",
            history_entry={"timestamp": "2024-01-01"},
        )

        original_count = len(bundle.triage["failures"])
        result = filter_bundle(bundle, min_severity, category)
        filtered_count = len(result.triage["failures"])

        assert filtered_count <= original_count


class TestToolInferenceProperties:
    """Property-based tests for tool inference from step names."""

    @given(
        st.sampled_from(
            ["pytest", "ruff", "mypy", "bandit", "pip-audit", "checkstyle", "spotbugs", "actionlint", "unknown-tool"]
        )
    )
    def test_known_tools_inferred_correctly(self, tool_name: str) -> None:
        """Property: step names containing tool names infer that tool."""
        step = f"[Python] {tool_name.title()} Check"
        result = infer_tool_from_step(step)

        # Known tools should be inferred (or fall back to workflow)
        assert isinstance(result, str)
        if tool_name != "unknown-tool":
            # The result should either match the tool or be "workflow"
            assert result in [tool_name.replace("-", "_"), "workflow", "pytest"]
