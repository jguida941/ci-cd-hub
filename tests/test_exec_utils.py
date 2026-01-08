"""Tests for exec_utils subprocess wrapper.

This module includes Hypothesis property-based tests to ensure
the safe_run() wrapper handles various edge cases correctly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cihub.utils.exec_utils import (
    TIMEOUT_BUILD,
    TIMEOUT_EXTENDED,
    TIMEOUT_NETWORK,
    TIMEOUT_QUICK,
    CommandNotFoundError,
    CommandTimeoutError,
    resolve_executable,
    safe_run,
)


class TestTimeoutConstants:
    """Verify timeout constants are properly ordered."""

    def test_timeout_ordering(self) -> None:
        """Timeouts should be in ascending order."""
        assert TIMEOUT_QUICK < TIMEOUT_NETWORK < TIMEOUT_BUILD < TIMEOUT_EXTENDED

    def test_timeout_values(self) -> None:
        """Verify expected timeout values per ADR-0045."""
        assert TIMEOUT_QUICK == 30
        assert TIMEOUT_NETWORK == 120
        assert TIMEOUT_BUILD == 600
        assert TIMEOUT_EXTENDED == 900


class TestResolveExecutable:
    """Tests for resolve_executable()."""

    def test_finds_system_command(self) -> None:
        """Common commands should be found."""
        # These should exist on any Unix-like system
        result = resolve_executable("echo")
        assert result.endswith("echo") or result == "echo"

    def test_returns_name_if_not_found(self) -> None:
        """Unknown commands return the original name."""
        result = resolve_executable("nonexistent_command_xyz_123")
        assert result == "nonexistent_command_xyz_123"

    @pytest.mark.parametrize(
        "name",
        [
            "a",  # single char
            "test",  # normal word
            "some-command",  # with hyphen
            "path/to/cmd",  # with slashes
            "  spaces  ",  # whitespace
            "émoji🎉",  # unicode
            "a" * 50,  # long string
            "../../../etc/passwd",  # path traversal attempt
            "cmd; rm -rf /",  # injection attempt
            "$(whoami)",  # command substitution
        ],
    )
    def test_never_raises_on_arbitrary_input(self, name: str) -> None:
        """resolve_executable should never raise, regardless of input.

        Note: Converted from hypothesis test due to mutmut subprocess issues.
        Tests various edge cases that hypothesis would generate.
        """
        result = resolve_executable(name)
        assert isinstance(result, str)


class TestSafeRun:
    """Tests for safe_run() wrapper."""

    def test_runs_simple_command(self) -> None:
        """Basic command execution works."""
        result = safe_run(["echo", "hello"])
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_captures_stdout(self) -> None:
        """stdout is captured by default."""
        result = safe_run(["echo", "test output"])
        assert result.stdout.strip() == "test output"

    def test_captures_stderr(self) -> None:
        """stderr is captured by default."""
        # Using Python to write to stderr reliably
        result = safe_run(["python3", "-c", "import sys; sys.stderr.write('error\\n')"])
        assert "error" in result.stderr

    def test_returns_exit_code(self) -> None:
        """Non-zero exit codes are returned."""
        result = safe_run(["python3", "-c", "import sys; sys.exit(42)"])
        assert result.returncode == 42

    def test_check_raises_on_failure(self) -> None:
        """check=True raises CalledProcessError on non-zero exit."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            safe_run(["python3", "-c", "import sys; sys.exit(1)"], check=True)
        assert exc_info.value.returncode == 1

    def test_command_not_found_error(self) -> None:
        """Missing command raises CommandNotFoundError."""
        with pytest.raises(CommandNotFoundError) as exc_info:
            safe_run(["nonexistent_command_xyz_456"])
        assert exc_info.value.cmd == "nonexistent_command_xyz_456"

    def test_timeout_error(self) -> None:
        """Timeout raises CommandTimeoutError."""
        with pytest.raises(CommandTimeoutError) as exc_info:
            safe_run(["sleep", "10"], timeout=1)
        assert exc_info.value.timeout == 1

    def test_cwd_parameter(self, tmp_path: Path) -> None:
        """Working directory is respected."""
        result = safe_run(["pwd"], cwd=tmp_path)
        assert str(tmp_path) in result.stdout

    def test_env_parameter(self) -> None:
        """Custom environment variables are used."""
        import os

        env = os.environ.copy()
        env["TEST_VAR_XYZ"] = "test_value_123"
        result = safe_run(["python3", "-c", "import os; print(os.environ.get('TEST_VAR_XYZ', ''))"], env=env)
        assert "test_value_123" in result.stdout

    def test_input_parameter(self) -> None:
        """Input is sent to stdin."""
        result = safe_run(["cat"], input="hello from stdin")
        assert "hello from stdin" in result.stdout

    def test_default_timeout(self) -> None:
        """Default timeout is TIMEOUT_QUICK."""
        # This test verifies the default by checking the function signature
        import inspect

        sig = inspect.signature(safe_run)
        timeout_param = sig.parameters["timeout"]
        assert timeout_param.default == TIMEOUT_QUICK

    def test_utf8_output(self) -> None:
        """UTF-8 output is handled correctly."""
        result = safe_run(["python3", "-c", "print('héllo wörld 日本語')"])
        assert "héllo" in result.stdout
        assert "wörld" in result.stdout
        assert "日本語" in result.stdout


class TestSafeRunHypothesis:
    """Property-based tests for safe_run()."""

    @given(
        st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=10)
    def test_handles_arbitrary_args(self, args: list[str]) -> None:
        """safe_run handles arbitrary arguments without crashing.

        It may raise CommandNotFoundError (expected), but should never
        raise unexpected exceptions.
        """
        # Filter out problematic characters
        clean_args = [a.replace("\x00", "").strip() for a in args if a.strip() and "\x00" not in a]
        assume(len(clean_args) > 0)
        assume(all(a for a in clean_args))

        try:
            safe_run(clean_args, timeout=1)
        except CommandNotFoundError:
            pass  # Expected for random command names
        except CommandTimeoutError:
            pass  # Expected for commands that hang

    @given(st.integers(min_value=1, max_value=30))
    @settings(max_examples=5)
    def test_timeout_values_respected(self, timeout: int) -> None:
        """Various timeout values work correctly."""
        # Quick command should complete within any reasonable timeout
        result = safe_run(["echo", "test"], timeout=timeout)
        assert result.returncode == 0


class TestExceptionAttributes:
    """Test custom exception classes."""

    def test_command_not_found_error_attributes(self) -> None:
        """CommandNotFoundError has expected attributes."""
        exc = CommandNotFoundError("missing_cmd")
        assert exc.cmd == "missing_cmd"
        assert "missing_cmd" in str(exc)

    def test_command_timeout_error_attributes(self) -> None:
        """CommandTimeoutError has expected attributes."""
        exc = CommandTimeoutError("slow_cmd", 30)
        assert exc.cmd == "slow_cmd"
        assert exc.timeout == 30
        assert "30" in str(exc)
        assert "slow_cmd" in str(exc)

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=10)
    def test_exception_messages_are_strings(self, cmd: str) -> None:
        """Exception messages are always valid strings."""
        exc1 = CommandNotFoundError(cmd)
        exc2 = CommandTimeoutError(cmd, 60)
        assert isinstance(str(exc1), str)
        assert isinstance(str(exc2), str)
