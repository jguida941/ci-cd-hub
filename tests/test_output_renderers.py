"""Tests for cihub.output.renderers module.

Tests the OutputRenderer abstraction and concrete implementations:
- HumanRenderer: Human-readable output
- JsonRenderer: JSON output
- get_renderer: Factory function

Includes parameterized tests and Hypothesis property-based tests.
"""

from __future__ import annotations

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cihub.output import HumanRenderer, JsonRenderer, get_renderer
from cihub.types import CommandResult


# ============================================================================
# get_renderer Tests
# ============================================================================


class TestGetRenderer:
    """Tests for get_renderer factory function."""

    @pytest.mark.parametrize(
        "json_mode,expected_type",
        [
            (False, HumanRenderer),
            (True, JsonRenderer),
        ],
        ids=["human", "json"],
    )
    def test_returns_correct_renderer(
        self, json_mode: bool, expected_type: type
    ) -> None:
        """Factory returns correct renderer type."""
        renderer = get_renderer(json_mode=json_mode)
        assert isinstance(renderer, expected_type)

    def test_default_is_human(self) -> None:
        """Default (no args) returns HumanRenderer."""
        renderer = get_renderer()
        assert isinstance(renderer, HumanRenderer)


# ============================================================================
# HumanRenderer Tests
# ============================================================================


class TestHumanRenderer:
    """Tests for HumanRenderer class."""

    def test_renders_summary(self) -> None:
        """Summary is included in output."""
        result = CommandResult(exit_code=0, summary="Operation successful")
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "Operation successful" in output

    def test_renders_problems(self) -> None:
        """Problems are rendered with severity icons."""
        result = CommandResult(
            exit_code=1,
            problems=[
                {"severity": "error", "message": "Test failed"},
                {"severity": "warning", "message": "Low coverage"},
            ],
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "[error]" in output
        assert "Test failed" in output
        assert "[warning]" in output
        assert "Low coverage" in output

    def test_renders_items_list(self) -> None:
        """Items in data are rendered as bullet list."""
        result = CommandResult(
            exit_code=0,
            data={"items": ["item1", "item2", "item3"]},
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "item1" in output
        assert "item2" in output
        assert "item3" in output

    def test_renders_table(self) -> None:
        """Table in data is rendered as formatted table."""
        result = CommandResult(
            exit_code=0,
            data={
                "table": {
                    "headers": ["name", "status"],
                    "rows": [
                        {"name": "test1", "status": "pass"},
                        {"name": "test2", "status": "fail"},
                    ],
                }
            },
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "name" in output
        assert "status" in output
        assert "test1" in output
        assert "pass" in output

    def test_renders_key_values(self) -> None:
        """Key-values in data are rendered as aligned pairs."""
        result = CommandResult(
            exit_code=0,
            data={"key_values": {"name": "myproject", "version": "1.0.0"}},
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "name" in output
        assert "myproject" in output
        assert "version" in output

    def test_renders_raw_output(self) -> None:
        """Raw output in data is included as-is."""
        result = CommandResult(
            exit_code=0,
            data={"raw_output": "Pre-formatted\ntext\nhere"},
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "Pre-formatted" in output
        assert "text" in output

    def test_renders_files_generated(self) -> None:
        """Generated files are listed."""
        result = CommandResult(
            exit_code=0,
            files_generated=["report.json", "summary.md"],
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "Generated:" in output
        assert "report.json" in output

    def test_renders_files_modified(self) -> None:
        """Modified files are listed."""
        result = CommandResult(
            exit_code=0,
            files_modified=["config.yaml"],
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "Modified:" in output
        assert "config.yaml" in output

    def test_renders_suggestions(self) -> None:
        """Suggestions are rendered."""
        result = CommandResult(
            exit_code=0,
            suggestions=[{"message": "Consider adding tests"}],
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert "Suggestions:" in output
        assert "Consider adding tests" in output

    def test_empty_result_minimal_output(self) -> None:
        """Empty result produces minimal output."""
        result = CommandResult(exit_code=0)
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        # Should be empty or minimal
        assert output == ""

    @pytest.mark.parametrize(
        "severity,icon",
        [
            ("error", "✗"),
            ("warning", "⚠"),
            ("info", "ℹ"),
            ("success", "✓"),
            ("critical", "☠"),
        ],
        ids=["error", "warning", "info", "success", "critical"],
    )
    def test_severity_icons(self, severity: str, icon: str) -> None:
        """Each severity has correct icon."""
        result = CommandResult(
            exit_code=1,
            problems=[{"severity": severity, "message": "Test"}],
        )
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert icon in output


# ============================================================================
# JsonRenderer Tests
# ============================================================================


class TestJsonRenderer:
    """Tests for JsonRenderer class."""

    def test_output_is_valid_json(self) -> None:
        """Output is valid JSON."""
        result = CommandResult(exit_code=0, summary="Success")
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_includes_command_name(self) -> None:
        """Output includes command name."""
        result = CommandResult(exit_code=0)
        renderer = JsonRenderer()
        output = renderer.render(result, "mycommand", 100)
        parsed = json.loads(output)
        assert parsed["command"] == "mycommand"

    def test_includes_duration(self) -> None:
        """Output includes duration."""
        result = CommandResult(exit_code=0)
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 500)
        parsed = json.loads(output)
        assert parsed["duration_ms"] == 500

    def test_includes_exit_code(self) -> None:
        """Output includes exit code."""
        result = CommandResult(exit_code=42)
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        assert parsed["exit_code"] == 42

    @pytest.mark.parametrize(
        "exit_code,expected_status",
        [
            (0, "success"),
            (1, "failure"),
            (2, "failure"),
            (127, "failure"),
        ],
        ids=["success", "failure_1", "failure_2", "failure_127"],
    )
    def test_status_based_on_exit_code(
        self, exit_code: int, expected_status: str
    ) -> None:
        """Status is success for 0, failure otherwise."""
        result = CommandResult(exit_code=exit_code)
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        assert parsed["status"] == expected_status

    def test_includes_problems(self) -> None:
        """Problems are included in output."""
        result = CommandResult(
            exit_code=1,
            problems=[{"severity": "error", "message": "Failed"}],
        )
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        assert len(parsed["problems"]) == 1
        assert parsed["problems"][0]["message"] == "Failed"

    def test_includes_data(self) -> None:
        """Data dict is included in output."""
        result = CommandResult(
            exit_code=0,
            data={"items": [1, 2, 3], "count": 3},
        )
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        assert parsed["data"]["items"] == [1, 2, 3]
        assert parsed["data"]["count"] == 3


# ============================================================================
# Hypothesis Property-Based Tests
# ============================================================================


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        summary=st.text(max_size=100),
        exit_code=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=50)
    def test_json_renderer_always_valid_json(
        self, summary: str, exit_code: int
    ) -> None:
        """Property: JsonRenderer always produces valid JSON."""
        result = CommandResult(exit_code=exit_code, summary=summary)
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    @given(
        num_problems=st.integers(min_value=0, max_value=10),
        exit_code=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=30)
    def test_human_renderer_no_crash(self, num_problems: int, exit_code: int) -> None:
        """Property: HumanRenderer never crashes."""
        problems = [
            {"severity": "error", "message": f"Problem {i}"}
            for i in range(num_problems)
        ]
        result = CommandResult(exit_code=exit_code, problems=problems)
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        assert isinstance(output, str)

    @given(
        items=st.lists(st.text(min_size=1, max_size=30), max_size=20),
    )
    @settings(max_examples=30)
    def test_human_renderer_includes_all_items(self, items: list) -> None:
        """Property: HumanRenderer includes all items in output."""
        if not items:
            return  # Skip empty lists
        result = CommandResult(exit_code=0, data={"items": items})
        renderer = HumanRenderer()
        output = renderer.render(result, "test", 100)
        for item in items:
            assert item in output

    @given(
        keys=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N")),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=30)
    def test_json_renderer_preserves_data_keys(self, keys: list) -> None:
        """Property: JsonRenderer preserves all data keys."""
        data = {k: f"value_{k}" for k in keys}
        result = CommandResult(exit_code=0, data=data)
        renderer = JsonRenderer()
        output = renderer.render(result, "test", 100)
        parsed = json.loads(output)
        for key in keys:
            assert key in parsed["data"]

    @given(
        duration=st.integers(min_value=0, max_value=1000000),
    )
    @settings(max_examples=30)
    def test_json_renderer_includes_exact_duration(self, duration: int) -> None:
        """Property: JsonRenderer includes exact duration value."""
        result = CommandResult(exit_code=0)
        renderer = JsonRenderer()
        output = renderer.render(result, "test", duration)
        parsed = json.loads(output)
        assert parsed["duration_ms"] == duration


# ============================================================================
# Integration Tests
# ============================================================================


class TestRendererIntegration:
    """Integration tests for renderer usage patterns."""

    def test_renderer_factory_json_mode(self) -> None:
        """Full flow with JSON mode."""
        result = CommandResult(
            exit_code=0,
            summary="CI passed",
            data={"coverage": 85},
        )
        renderer = get_renderer(json_mode=True)
        output = renderer.render(result, "ci", 1000)
        parsed = json.loads(output)
        assert parsed["summary"] == "CI passed"
        assert parsed["data"]["coverage"] == 85

    def test_renderer_factory_human_mode(self) -> None:
        """Full flow with human mode."""
        result = CommandResult(
            exit_code=0,
            summary="CI passed",
            data={"items": ["test1: pass", "test2: pass"]},
        )
        renderer = get_renderer(json_mode=False)
        output = renderer.render(result, "ci", 1000)
        assert "CI passed" in output
        assert "test1: pass" in output
