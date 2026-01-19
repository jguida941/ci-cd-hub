"""Tests for hub_ci helper functions.

Split from test_hub_ci.py for better organization.
Tests: _write_outputs, _append_summary, _resolve_output_path, _resolve_summary_path,
       _extract_count, _compare_badges, _count_pip_audit_vulns
"""

# TEST-METRICS:

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest


class TestWriteOutputs:
    """Tests for _write_outputs helper."""

    def test_returns_text_when_no_path(self) -> None:
        from cihub.commands.hub_ci import _write_outputs

        output = _write_outputs({"key1": "value1", "key2": "value2"}, None)
        assert "key1=value1" in (output or "")
        assert "key2=value2" in (output or "")

    def test_writes_to_file_when_path_provided(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _write_outputs

        output_path = tmp_path / "output.txt"
        _write_outputs({"issues": "5"}, output_path)
        content = output_path.read_text()
        assert "issues=5\n" in content

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _write_outputs

        output_path = tmp_path / "output.txt"
        output_path.write_text("existing=value\n")
        _write_outputs({"new": "data"}, output_path)
        content = output_path.read_text()
        assert "existing=value" in content
        assert "new=data" in content


class TestAppendSummary:
    """Tests for _append_summary helper."""

    def test_returns_text_when_no_path(self) -> None:
        from cihub.commands.hub_ci import _append_summary

        output = _append_summary("Summary text", None)
        assert "Summary text" in (output or "")

    def test_writes_to_file_when_path_provided(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _append_summary

        summary_path = tmp_path / "summary.md"
        _append_summary("## Test Summary", summary_path)
        content = summary_path.read_text()
        assert "## Test Summary" in content

    def test_adds_newline_if_missing(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _append_summary

        summary_path = tmp_path / "summary.md"
        _append_summary("No newline", summary_path)
        content = summary_path.read_text()
        assert content.endswith("\n")


class TestResolveOutputPath:
    """Tests for _resolve_output_path helper."""

    @pytest.mark.parametrize(
        "value,github_flag,env_value,expected",
        [
            ("/some/path.txt", False, None, "/some/path.txt"),
            (None, True, "/env/path.txt", "/env/path.txt"),
            (None, False, None, None),
            (None, True, None, None),
        ],
        ids=["explicit_path", "github_env", "no_path_no_flag", "flag_but_no_env"],
    )
    def test_resolve_output_path(
        self, value: str | None, github_flag: bool, env_value: str | None, expected: str | None
    ) -> None:
        """Property: _resolve_output_path resolves paths correctly."""
        from cihub.commands.hub_ci import _resolve_output_path

        env = {"GITHUB_OUTPUT": env_value} if env_value else {}
        with mock.patch.dict(os.environ, env, clear=True):
            result = _resolve_output_path(value, github_flag)
            if expected is None:
                assert result is None
            else:
                assert result == Path(expected)


class TestResolveSummaryPath:
    """Tests for _resolve_summary_path helper."""

    def test_returns_path_from_value(self) -> None:
        from cihub.commands.hub_ci import _resolve_summary_path

        result = _resolve_summary_path("/some/summary.md", False)
        assert result == Path("/some/summary.md")

    def test_returns_env_path_when_github_summary_true(self) -> None:
        from cihub.commands.hub_ci import _resolve_summary_path

        with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/env/summary.md"}):
            result = _resolve_summary_path(None, True)
            assert result == Path("/env/summary.md")


class TestExtractCount:
    """Tests for _extract_count helper."""

    @pytest.mark.parametrize(
        "line,emoji,expected",
        [
            ("🎉 42 🙁 5", "🎉", 42),
            ("🎉 42 🙁 5", "🙁", 5),
            ("🎉 42", "⏰", 0),  # emoji not found
            ("", "🎉", 0),  # empty line
            ("no emoji here", "🎉", 0),  # no match
        ],
        ids=["party_emoji", "sad_emoji", "not_found", "empty_line", "no_emoji"],
    )
    def test_extract_count(self, line: str, emoji: str, expected: int) -> None:
        """Property: _extract_count extracts numeric value after emoji."""
        from cihub.commands.hub_ci import _extract_count

        assert _extract_count(line, emoji) == expected


class TestCompareBadges:
    """Tests for _compare_badges helper."""

    def test_reports_missing_badges_dir(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _compare_badges

        issues = _compare_badges(tmp_path / "missing", tmp_path)
        assert "missing badges directory" in issues[0]

    def test_detects_missing_extra_and_diff(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _compare_badges

        expected = tmp_path / "expected"
        actual = tmp_path / "actual"
        expected.mkdir()
        actual.mkdir()

        (expected / "same.json").write_text('{"value": 1}')
        (actual / "same.json").write_text('{"value": 2}')
        (expected / "missing.json").write_text('{"value": 3}')
        (actual / "extra.json").write_text('{"value": 4}')

        issues = _compare_badges(expected, actual)
        assert "diff: same.json" in issues
        assert "missing: missing.json" in issues
        assert "extra: extra.json" in issues


class TestCountPipAuditVulns:
    """Tests for _count_pip_audit_vulns helper."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            # Multiple packages with vulns
            (
                [
                    {"name": "package1", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]},
                    {"name": "package2", "vulns": [{"id": "CVE-3"}]},
                ],
                3,
            ),
            # Alternative key: vulnerabilities
            ([{"name": "pkg", "vulnerabilities": [{"id": "CVE-1"}]}], 1),
            # Non-list input returns 0
            ({}, 0),
            (None, 0),
            # Empty vulns list
            ([{"name": "pkg", "vulns": []}], 0),
            # Package without vulns key
            ([{"name": "pkg"}], 0),
        ],
        ids=[
            "multiple_packages",
            "vulnerabilities_key",
            "dict_input",
            "none_input",
            "empty_vulns",
            "no_vulns_key",
        ],
    )
    def test_count_pip_audit_vulns(self, data, expected: int) -> None:
        """Property: _count_pip_audit_vulns counts all vulnerabilities."""
        from cihub.commands.hub_ci import _count_pip_audit_vulns

        assert _count_pip_audit_vulns(data) == expected
