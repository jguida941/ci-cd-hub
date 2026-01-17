"""Tests for ci_runner core types and utility functions.

Split from test_ci_runner.py for better organization.
Tests: ToolResult, _parse_junit, _parse_coverage, _parse_json, _find_files
"""

from __future__ import annotations

import json
from pathlib import Path

from cihub.ci_runner import (
    ToolResult,
    _find_files,
    _parse_coverage,
    _parse_json,
    _parse_junit,
)


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_to_payload(self) -> None:
        result = ToolResult(
            tool="pytest",
            ran=True,
            success=True,
            metrics={"coverage": 85},
            artifacts={"report": "/path/to/report.xml"},
        )
        payload = result.to_payload()

        assert payload["tool"] == "pytest"
        assert payload["ran"] is True
        assert payload["success"] is True
        assert payload["metrics"]["coverage"] == 85
        assert payload["artifacts"]["report"] == "/path/to/report.xml"

    def test_from_payload(self) -> None:
        data = {
            "tool": "ruff",
            "ran": True,
            "success": False,
            "metrics": {"errors": 5},
            "artifacts": {},
        }
        result = ToolResult.from_payload(data)

        assert result.tool == "ruff"
        assert result.ran is True
        assert result.success is False
        assert result.metrics["errors"] == 5

    def test_from_payload_handles_missing_fields(self) -> None:
        result = ToolResult.from_payload({})

        assert result.tool == ""
        assert result.ran is False
        assert result.success is False
        assert result.metrics == {}
        assert result.artifacts == {}

    def test_write_json(self, tmp_path: Path) -> None:
        result = ToolResult(tool="test", ran=True, success=True)
        output_path = tmp_path / "subdir" / "result.json"

        result.write_json(output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["tool"] == "test"


class TestParseJunit:
    """Tests for _parse_junit function."""

    def test_parses_single_testsuite(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <testsuite tests="10" failures="2" errors="1" skipped="1" time="1.5">
        </testsuite>"""
        path = tmp_path / "junit.xml"
        path.write_text(xml)

        result = _parse_junit(path)

        assert result["tests_passed"] == 6
        assert result["tests_failed"] == 3
        assert result["tests_skipped"] == 1
        assert result["tests_runtime_seconds"] == 1.5

    def test_parses_testsuites_container(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <testsuites>
            <testsuite tests="5" failures="1" errors="0" skipped="0" time="0.5"/>
            <testsuite tests="5" failures="0" errors="1" skipped="1" time="0.5"/>
        </testsuites>"""
        path = tmp_path / "junit.xml"
        path.write_text(xml)

        result = _parse_junit(path)

        assert result["tests_passed"] == 7
        assert result["tests_failed"] == 2
        assert result["tests_skipped"] == 1
        assert result["tests_runtime_seconds"] == 1.0

    def test_returns_zeros_for_missing_file(self, tmp_path: Path) -> None:
        result = _parse_junit(tmp_path / "missing.xml")

        assert result["tests_passed"] == 0
        assert result["tests_failed"] == 0
        assert result["tests_skipped"] == 0


class TestParseCoverage:
    """Tests for _parse_coverage function."""

    def test_parses_cobertura_format(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <coverage line-rate="0.85" lines-covered="850" lines-valid="1000">
        </coverage>"""
        path = tmp_path / "coverage.xml"
        path.write_text(xml)

        result = _parse_coverage(path)

        assert result["coverage"] == 85
        assert result["coverage_lines_covered"] == 850
        assert result["coverage_lines_total"] == 1000

    def test_handles_lines_total_alias(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <coverage line-rate="0.75" lines-covered="75" lines-total="100">
        </coverage>"""
        path = tmp_path / "coverage.xml"
        path.write_text(xml)

        result = _parse_coverage(path)
        assert result["coverage_lines_total"] == 100

    def test_returns_zeros_for_missing_file(self, tmp_path: Path) -> None:
        result = _parse_coverage(tmp_path / "missing.xml")

        assert result["coverage"] == 0
        assert result["coverage_lines_covered"] == 0


class TestParseJson:
    """Tests for _parse_json function."""

    def test_parses_dict(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text('{"key": "value"}')

        result = _parse_json(path)
        assert result == {"key": "value"}

    def test_parses_list(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text("[1, 2, 3]")

        result = _parse_json(path)
        assert result == [1, 2, 3]

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        result = _parse_json(tmp_path / "missing.json")
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not valid json")

        result = _parse_json(path)
        assert result is None

    def test_returns_none_for_primitive(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text('"just a string"')

        result = _parse_json(path)
        assert result is None


class TestFindFiles:
    """Tests for _find_files function."""

    def test_finds_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "dir").mkdir()
        (tmp_path / "file1.xml").write_text("")
        (tmp_path / "dir" / "file2.xml").write_text("")

        result = _find_files(tmp_path, ["*.xml", "**/*.xml"])

        assert len(result) == 2

    def test_deduplicates_results(self, tmp_path: Path) -> None:
        (tmp_path / "test.xml").write_text("")

        result = _find_files(tmp_path, ["*.xml", "test.xml"])

        assert len(result) == 1

    def test_returns_sorted_paths(self, tmp_path: Path) -> None:
        (tmp_path / "z.xml").write_text("")
        (tmp_path / "a.xml").write_text("")

        result = _find_files(tmp_path, ["*.xml"])

        assert str(result[0]).endswith("a.xml")
