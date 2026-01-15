"""Tests for cihub.utils.debug module."""

from __future__ import annotations

import io

from cihub.utils.debug import debug_context_enabled, emit_debug_context


class TestDebugContextEnabled:
    """Tests for debug_context_enabled function."""

    def test_returns_false_when_not_set(self) -> None:
        """Returns False when env var not set."""
        env: dict[str, str] = {}
        assert debug_context_enabled(env=env) is False

    def test_returns_true_when_enabled(self) -> None:
        """Returns True when env var is truthy."""
        env = {"CIHUB_DEBUG_CONTEXT": "true"}
        assert debug_context_enabled(env=env) is True


class TestEmitDebugContext:
    """Tests for emit_debug_context function."""

    def test_does_nothing_when_disabled(self) -> None:
        """Does not emit when debug context is disabled."""
        output = io.StringIO()
        env: dict[str, str] = {}
        emit_debug_context("Test", [("key", "value")], env=env, file=output)
        assert output.getvalue() == ""

    def test_emits_when_enabled(self) -> None:
        """Emits debug context when enabled."""
        output = io.StringIO()
        env = {"CIHUB_DEBUG_CONTEXT": "true"}
        emit_debug_context("Test Title", [("key1", "val1"), ("key2", "val2")], env=env, file=output)
        result = output.getvalue()
        assert "[cihub debug] Test Title" in result
        assert "key1: val1" in result
        assert "key2: val2" in result

    def test_skips_none_values(self) -> None:
        """Skips entries with None values."""
        output = io.StringIO()
        env = {"CIHUB_DEBUG_CONTEXT": "true"}
        emit_debug_context("Test", [("key1", "val1"), ("key2", None), ("key3", "val3")], env=env, file=output)
        result = output.getvalue()
        assert "key1: val1" in result
        assert "key2" not in result
        assert "key3: val3" in result

    def test_skips_empty_string_values(self) -> None:
        """Skips entries with empty string values."""
        output = io.StringIO()
        env = {"CIHUB_DEBUG_CONTEXT": "true"}
        emit_debug_context("Test", [("key1", "val1"), ("key2", ""), ("key3", "val3")], env=env, file=output)
        result = output.getvalue()
        assert "key1: val1" in result
        assert "key2" not in result
        assert "key3: val3" in result
