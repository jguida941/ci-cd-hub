"""Unit tests for triage verification module.

Tests for tool verification logic that detects drift, failures, and missing proof.
"""

# TEST-METRICS:

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cihub.commands.triage.verification import (
    format_verify_tools_output,
    verify_tools_from_report,
    verify_tools_from_reports,
)


class TestVerifyToolsFromReport:
    """Unit tests for verify_tools_from_report function."""

    @pytest.mark.parametrize(
        "scenario,expected_status",
        [
            # Tool configured, ran, and succeeded -> passed
            (
                {
                    "tools_configured": {"pytest": True},
                    "tools_ran": {"pytest": True},
                    "tools_success": {"pytest": True},
                },
                "passed",
            ),
            # Tool configured but didn't run -> drift
            (
                {
                    "tools_configured": {"pytest": True},
                    "tools_ran": {"pytest": False},
                    "tools_success": {"pytest": False},
                },
                "drift",
            ),
            # Tool configured but optional -> optional
            (
                {
                    "tools_configured": {"pytest": True},
                    "tools_ran": {"pytest": False},
                    "tools_success": {"pytest": False},
                    "tools_require_run": {"pytest": False},
                },
                "optional",
            ),
            # Tool configured, ran, but failed -> failed
            (
                {
                    "tools_configured": {"pytest": True},
                    "tools_ran": {"pytest": True},
                    "tools_success": {"pytest": False},
                },
                "failed",
            ),
            # Tool not configured -> skipped
            (
                {
                    "tools_configured": {"pytest": False},
                    "tools_ran": {"pytest": False},
                    "tools_success": {"pytest": False},
                },
                "skipped",
            ),
        ],
    )
    def test_verify_tool_scenarios(self, scenario: dict, expected_status: str, tmp_path: Path) -> None:
        """Parameterized test for all tool states."""
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(scenario), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        # Find the tool entry in the matrix
        tool_entry = next((e for e in result["tool_matrix"] if e["tool"] == "pytest"), None)
        assert tool_entry is not None
        assert tool_entry["status"] == expected_status

    def test_verified_true_when_all_tools_pass(self, tmp_path: Path) -> None:
        """Test verified=True when all configured tools ran and succeeded."""
        report = {
            "tools_configured": {"pytest": True, "ruff": True},
            "tools_ran": {"pytest": True, "ruff": True},
            "tools_success": {"pytest": True, "ruff": True},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is True
        assert len(result["passed"]) == 2
        assert len(result["drift"]) == 0
        assert len(result["failures"]) == 0

    def test_verified_false_when_drift_detected(self, tmp_path: Path) -> None:
        """Test verified=False when configured tool didn't run."""
        report = {
            "tools_configured": {"pytest": True, "mypy": True},
            "tools_ran": {"pytest": True, "mypy": False},
            "tools_success": {"pytest": True, "mypy": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is False
        assert len(result["drift"]) == 1
        assert result["drift"][0]["tool"] == "mypy"
        assert "did not run" in result["drift"][0]["message"].lower()


class TestVerifyToolsFromReports:
    """Unit tests for verify_tools_from_reports function."""

    def test_combines_multiple_reports(self, tmp_path: Path) -> None:
        python_dir = tmp_path / "python-ci-report"
        java_dir = tmp_path / "java-ci-report"
        python_dir.mkdir()
        java_dir.mkdir()

        python_report = {
            "environment": {"workdir": "python", "language": "python"},
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
        }
        java_report = {
            "environment": {"workdir": "java", "language": "java"},
            "tools_configured": {"checkstyle": True},
            "tools_ran": {"checkstyle": False},
            "tools_success": {"checkstyle": False},
        }
        python_path = python_dir / "report.json"
        java_path = java_dir / "report.json"
        python_path.write_text(json.dumps(python_report), encoding="utf-8")
        java_path.write_text(json.dumps(java_report), encoding="utf-8")

        result = verify_tools_from_reports([python_path, java_path], tmp_path)

        assert len(result["targets"]) == 2
        assert result["counts"]["passed"] == 1
        assert result["counts"]["drift"] == 1
        assert result["verified"] is False

    def test_optional_tools_not_counted_as_drift(self, tmp_path: Path) -> None:
        """Test configured-but-optional tools do not fail verification."""
        report = {
            "tools_configured": {"pytest": True, "mypy": True},
            "tools_ran": {"pytest": True, "mypy": False},
            "tools_success": {"pytest": True, "mypy": False},
            "tools_require_run": {"mypy": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is True
        assert len(result["drift"]) == 0
        assert result["optional"][0]["tool"] == "mypy"

    def test_verified_false_when_failure_detected(self, tmp_path: Path) -> None:
        """Test verified=False when tool ran but failed."""
        report = {
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is False
        assert len(result["failures"]) == 1
        assert result["failures"][0]["tool"] == "pytest"

    def test_skipped_tools_not_counted_as_drift(self, tmp_path: Path) -> None:
        """Test that unconfigured tools are skipped, not drift."""
        report = {
            "tools_configured": {"pytest": True, "mypy": False},
            "tools_ran": {"pytest": True, "mypy": False},
            "tools_success": {"pytest": True, "mypy": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is True
        assert "mypy" in result["skipped"]
        assert len(result["drift"]) == 0

    def test_counts_are_correct(self, tmp_path: Path) -> None:
        """Test that counts dict sums correctly."""
        report = {
            "tools_configured": {
                "pytest": True,
                "ruff": True,
                "mypy": True,
                "bandit": False,
            },
            "tools_ran": {"pytest": True, "ruff": True, "mypy": False, "bandit": False},
            "tools_success": {
                "pytest": True,
                "ruff": False,
                "mypy": False,
                "bandit": False,
            },
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        counts = result["counts"]

        assert counts["total"] == 4
        assert counts["passed"] == 1  # pytest
        assert counts["failures"] == 1  # ruff (ran but failed)
        assert counts["drift"] == 1  # mypy (configured but didn't run)
        assert counts["skipped"] == 1  # bandit (not configured)
        assert counts["optional"] == 0
        assert (
            counts["passed"]
            + counts["failures"]
            + counts["drift"]
            + counts["skipped"]
            + counts["no_proof"]
            + counts["optional"]
        ) == counts["total"]

    def test_report_not_found_returns_error(self, tmp_path: Path) -> None:
        """Test handling of missing report file."""
        result = verify_tools_from_report(tmp_path / "nonexistent.json")

        assert result["verified"] is False
        assert "not found" in result["summary"].lower()

    def test_invalid_json_returns_error(self, tmp_path: Path) -> None:
        """Test handling of invalid JSON in report."""
        report_path = tmp_path / "report.json"
        report_path.write_text("not valid json {", encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is False
        assert "invalid json" in result["summary"].lower()

    def test_empty_report_returns_verified(self, tmp_path: Path) -> None:
        """Test handling of empty report (no tools)."""
        report = {
            "tools_configured": {},
            "tools_ran": {},
            "tools_success": {},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        # Empty is valid - nothing to verify
        assert result["verified"] is True
        assert result["counts"]["total"] == 0

    def test_handles_missing_tools_dicts(self, tmp_path: Path) -> None:
        """Test handling of report with missing tools_* dicts."""
        report = {"schema_version": "2.0"}  # No tools dicts
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is True
        assert result["counts"]["total"] == 0

    def test_handles_none_values_in_tools_dicts(self, tmp_path: Path) -> None:
        """Test handling of None values in tools dicts."""
        report = {
            "tools_configured": None,
            "tools_ran": None,
            "tools_success": None,
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)

        assert result["verified"] is True

    def test_handles_targets(self, tmp_path: Path) -> None:
        """Targets reports are aggregated with scoped messages."""
        report = {
            "targets": [
                {
                    "slug": "python-src",
                    "language": "python",
                    "subdir": "python",
                    "report": {
                        "tools_configured": {"pytest": True},
                        "tools_ran": {"pytest": True},
                        "tools_success": {"pytest": True},
                    },
                },
                {
                    "slug": "java-app",
                    "language": "java",
                    "subdir": "java",
                    "report": {
                        "tools_configured": {"checkstyle": True},
                        "tools_ran": {"checkstyle": False},
                        "tools_success": {"checkstyle": False},
                    },
                },
            ]
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path, tmp_path)

        assert result["verified"] is False
        assert result["targets"]
        assert any("[java-app]" in item["message"] for item in result["drift"])


class TestFormatVerifyToolsOutput:
    """Unit tests for format_verify_tools_output function."""

    def test_formats_tool_matrix_table(self, tmp_path: Path) -> None:
        """Test that output includes formatted table."""
        report = {
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "Tool Verification Report" in output
        assert "| Tool |" in output
        assert "pytest" in output

    def test_formats_targets_table(self, tmp_path: Path) -> None:
        """Target reports include scoped sections."""
        report = {
            "targets": [
                {
                    "slug": "python-src",
                    "language": "python",
                    "subdir": "python",
                    "report": {
                        "tools_configured": {"pytest": True},
                        "tools_ran": {"pytest": True},
                        "tools_success": {"pytest": True},
                    },
                }
            ]
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "Target:" in output
        assert "python-src" in output

    def test_shows_drift_section_when_present(self, tmp_path: Path) -> None:
        """Test drift section appears when tools have drift."""
        report = {
            "tools_configured": {"mypy": True},
            "tools_ran": {"mypy": False},
            "tools_success": {"mypy": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "DRIFT" in output
        assert "mypy" in output

    def test_shows_optional_section_when_present(self, tmp_path: Path) -> None:
        """Test optional section appears when tools are optional."""
        report = {
            "tools_configured": {"mypy": True},
            "tools_ran": {"mypy": False},
            "tools_success": {"mypy": False},
            "tools_require_run": {"mypy": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "OPTIONAL" in output
        assert "mypy" in output

    def test_shows_failures_section_when_present(self, tmp_path: Path) -> None:
        """Test failures section appears when tools failed."""
        report = {
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": False},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "FAILED" in output
        assert "pytest" in output

    def test_shows_summary_line(self, tmp_path: Path) -> None:
        """Test summary line appears at end."""
        report = {
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        result = verify_tools_from_report(report_path)
        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "Summary:" in output

    def test_empty_result_formats_correctly(self) -> None:
        """Test formatting of empty verification result."""
        result = {
            "verified": True,
            "drift": [],
            "no_proof": [],
            "failures": [],
            "passed": [],
            "skipped": [],
            "summary": "No tools to verify",
            "tool_matrix": [],
            "counts": {
                "total": 0,
                "passed": 0,
                "drift": 0,
            "no_proof": 0,
            "failures": 0,
            "optional": 0,
            "skipped": 0,
        },
    }

        lines = format_verify_tools_output(result)

        output = "\n".join(lines)
        assert "Tool Verification Report" in output
        assert "Total: 0 tools" in output


class TestBackwardCompatibilityAliases:
    """Test backward compatibility aliases."""

    def test_underscore_prefixed_aliases_exist(self) -> None:
        """Test that underscore-prefixed aliases are available."""
        from cihub.commands.triage.verification import (
            _format_verify_tools_output,
            _verify_tools_from_report,
        )

        assert _verify_tools_from_report is verify_tools_from_report
        assert _format_verify_tools_output is format_verify_tools_output
