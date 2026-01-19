"""Comprehensive tests for ai_loop command (autonomous CI fix loop).

Tests cover:
- LoopState dataclass initialization and mutation
- Circuit breaker logic (duration, error patterns, consecutive failures)
- Main loop iteration (success, failure, max iterations)
- Environment variable handling for CIHUB_EMIT_TRIAGE
- Integration with cmd_ci and cmd_fix (mocked)
"""

# TEST-METRICS:
#   Coverage: 78.7%

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from cihub.commands.ai_loop import (
    AI_LOOP_CONFIG,
    LoopState,
    _break_reason,
    _build_ci_args,
    _resolve_settings,
    _run_ci_with_triage,
    _save_iteration_state,
    _should_break,
    cmd_ai_loop,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.types import CommandResult

# =============================================================================
# LoopState Tests
# =============================================================================


class TestLoopState:
    """Tests for LoopState dataclass."""

    def test_default_initialization(self) -> None:
        """LoopState initializes with correct defaults."""
        state = LoopState()

        assert state.iteration == 0
        assert state.max_iterations == 10
        assert state.fixes_applied == []
        assert state.failures_seen == []
        assert state.last_failure_signature == frozenset()
        assert state.consecutive_same_failures == 0
        assert state.suggestions == []
        assert state.stop_reason is None
        assert isinstance(state.start_time, float)

    def test_custom_max_iterations(self) -> None:
        """LoopState accepts custom max_iterations."""
        state = LoopState(max_iterations=5)

        assert state.max_iterations == 5

    def test_mutable_lists_are_independent(self) -> None:
        """Each LoopState instance has independent lists."""
        state1 = LoopState()
        state2 = LoopState()

        state1.fixes_applied.append("fix1")
        state1.failures_seen.append("failure1")

        assert state2.fixes_applied == []
        assert state2.failures_seen == []

    def test_iteration_tracking(self) -> None:
        """LoopState correctly tracks iteration count."""
        state = LoopState()

        for i in range(5):
            state.iteration = i + 1
            assert state.iteration == i + 1


# =============================================================================
# Circuit Breaker Tests (_should_break)
# =============================================================================


class TestCircuitBreaker:
    """Tests for _should_break circuit breaker logic."""

    def test_no_break_on_empty_problems(self) -> None:
        """Circuit breaker does not trigger on empty problems."""
        state = LoopState()
        result = CommandResult(exit_code=EXIT_FAILURE, problems=[])

        should_stop = _should_break(state, result)

        assert should_stop is False
        assert state.consecutive_same_failures == 0

    def test_no_break_on_first_failure(self) -> None:
        """Circuit breaker does not trigger on first failure."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "pytest", "message": "test failed"}],
        )

        should_stop = _should_break(state, result)

        assert should_stop is False
        assert state.consecutive_same_failures == 1

    def test_breaks_on_consecutive_same_failures(self) -> None:
        """Circuit breaker triggers after N consecutive identical failures."""
        state = LoopState()
        threshold = AI_LOOP_CONFIG["circuit_breaker"]["same_error_threshold"]
        problems = [{"tool": "pytest", "message": "test failed"}]
        result = CommandResult(exit_code=EXIT_FAILURE, problems=problems)

        # Simulate consecutive failures up to threshold
        for _ in range(threshold):
            should_stop = _should_break(state, result)

        assert should_stop is True
        assert state.consecutive_same_failures == threshold

    def test_resets_counter_on_different_failures(self) -> None:
        """Consecutive failure counter resets when failure signature changes."""
        state = LoopState()

        # First failure
        result1 = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "pytest", "message": "test failed"}],
        )
        _should_break(state, result1)
        assert state.consecutive_same_failures == 1

        # Different failure
        result2 = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "ruff", "message": "lint error"}],
        )
        _should_break(state, result2)
        assert state.consecutive_same_failures == 1  # Reset to 1, not 2

    def test_breaks_on_error_pattern_permission_denied(self) -> None:
        """Circuit breaker triggers on 'permission denied' error pattern."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "unknown", "message": "Permission Denied accessing file"}],
        )

        should_stop = _should_break(state, result)

        assert should_stop is True

    def test_breaks_on_error_pattern_rate_limit(self) -> None:
        """Circuit breaker triggers on 'rate limit' error pattern."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "gh", "message": "API rate limit exceeded"}],
        )

        should_stop = _should_break(state, result)

        assert should_stop is True

    def test_breaks_on_error_pattern_out_of_memory(self) -> None:
        """Circuit breaker triggers on 'out of memory' error pattern."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "jest", "message": "Out of memory error during tests"}],
        )

        should_stop = _should_break(state, result)

        assert should_stop is True

    def test_breaks_on_error_pattern_authentication_failed(self) -> None:
        """Circuit breaker triggers on 'authentication failed' error pattern."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "gh", "message": "Authentication failed"}],
        )

        should_stop = _should_break(state, result)

        assert should_stop is True

    def test_breaks_on_duration_limit_exceeded(self) -> None:
        """Circuit breaker triggers when max duration is exceeded."""
        state = LoopState()
        # Set start time in the past (beyond max duration)
        state.start_time = time.time() - 700  # 700s > 600s default

        result = CommandResult(exit_code=EXIT_FAILURE, problems=[])

        should_stop = _should_break(state, result)

        assert should_stop is True

    def test_no_break_within_duration_limit(self) -> None:
        """Circuit breaker does not trigger when within duration limit."""
        state = LoopState()
        # Start time is now (within limit)

        result = CommandResult(exit_code=EXIT_FAILURE, problems=[])

        should_stop = _should_break(state, result)

        assert should_stop is False

    def test_error_pattern_case_insensitive(self) -> None:
        """Error pattern matching is case insensitive."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "unknown", "message": "PERMISSION DENIED"}],
        )

        should_stop = _should_break(state, result)

        assert should_stop is True

    def test_break_reason_duration_timeout(self) -> None:
        """_break_reason returns duration_timeout when elapsed exceeds limit."""
        state = LoopState()
        state.start_time = time.time() - 700
        result = CommandResult(exit_code=EXIT_FAILURE, problems=[])

        reason = _break_reason(state, result)

        assert reason == "duration_timeout"

    def test_break_reason_error_pattern(self) -> None:
        """_break_reason returns error_pattern when message matches."""
        state = LoopState()
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "unknown", "message": "Permission denied"}],
        )

        reason = _break_reason(state, result)

        assert reason == "error_pattern"

    def test_break_reason_repeat_failures(self) -> None:
        """_break_reason returns repeat_failures after threshold repeats."""
        state = LoopState()
        threshold = AI_LOOP_CONFIG["circuit_breaker"]["same_error_threshold"]
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "pytest", "message": "same error every time"}],
        )

        reason = None
        for _ in range(threshold):
            reason = _break_reason(state, result)

        assert reason == "repeat_failures"


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestBuildCiArgs:
    """Tests for _build_ci_args helper."""

    def test_builds_basic_args(self, tmp_path: Path) -> None:
        """_build_ci_args creates args with required fields."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(tmp_path / ".cihub" / "ai-loop"),
            max_iterations=10,
            fix_mode="safe",
            emit_report=False,
        )
        settings = _resolve_settings(args)
        output_dir = tmp_path / ".cihub"

        ci_args = _build_ci_args(settings=settings, output_dir=output_dir, iteration=1, max_iterations=10)

        assert ci_args.repo == str(tmp_path)
        assert ci_args.output_dir == str(output_dir)
        assert ci_args.ai_loop_iteration == 1
        assert ci_args.ai_loop_max_iterations == 10
        assert ci_args.install_deps is False

    def test_passes_through_correlation_id(self, tmp_path: Path) -> None:
        """_build_ci_args passes through correlation_id."""
        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(tmp_path / ".cihub" / "ai-loop"),
            max_iterations=10,
            fix_mode="safe",
            emit_report=False,
            correlation_id="test-correlation-123",
            config_from_hub=None,
        )
        settings = _resolve_settings(args)
        output_dir = tmp_path / ".cihub"

        ci_args = _build_ci_args(settings=settings, output_dir=output_dir, iteration=1, max_iterations=10)

        assert ci_args.correlation_id == "test-correlation-123"


class TestRunCiWithTriage:
    """Tests for _run_ci_with_triage helper."""

    def test_sets_triage_env_var(self) -> None:
        """_run_ci_with_triage sets CIHUB_EMIT_TRIAGE=true."""
        captured_env: dict[str, str] = {}

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            captured_env["CIHUB_EMIT_TRIAGE"] = os.environ.get("CIHUB_EMIT_TRIAGE", "")
            return CommandResult(exit_code=EXIT_SUCCESS, summary="OK")

        args = argparse.Namespace()
        _run_ci_with_triage(mock_cmd_ci, args)

        assert captured_env["CIHUB_EMIT_TRIAGE"] == "true"

    def test_restores_original_env_var(self) -> None:
        """_run_ci_with_triage restores original CIHUB_EMIT_TRIAGE value."""
        os.environ["CIHUB_EMIT_TRIAGE"] = "original_value"

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="OK")

        try:
            args = argparse.Namespace()
            _run_ci_with_triage(mock_cmd_ci, args)

            assert os.environ.get("CIHUB_EMIT_TRIAGE") == "original_value"
        finally:
            os.environ.pop("CIHUB_EMIT_TRIAGE", None)

    def test_removes_env_var_if_not_set_originally(self) -> None:
        """_run_ci_with_triage removes CIHUB_EMIT_TRIAGE if it wasn't set."""
        os.environ.pop("CIHUB_EMIT_TRIAGE", None)

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="OK")

        args = argparse.Namespace()
        _run_ci_with_triage(mock_cmd_ci, args)

        assert "CIHUB_EMIT_TRIAGE" not in os.environ


class TestSaveIterationState:
    """Tests for _save_iteration_state helper."""

    def test_saves_state_file(self, tmp_path: Path) -> None:
        """_save_iteration_state creates JSON state file."""
        state_path = tmp_path / "state.json"
        state = LoopState(iteration=3, max_iterations=10)
        state.fixes_applied = ["fix1", "fix2"]
        state.failures_seen = ["failure1"]
        state.consecutive_same_failures = 2
        result = CommandResult(
            exit_code=EXIT_FAILURE,
            problems=[{"tool": "pytest", "message": "failed"}],
        )

        _save_iteration_state(state_path, state, result)

        assert state_path.exists()

        data = json.loads(state_path.read_text())
        assert data["iteration"] == 3
        assert data["exit_code"] == EXIT_FAILURE
        assert data["problems_count"] == 1
        assert data["fixes_applied_total"] == 2
        assert data["failures_seen_total"] == 1
        assert data["consecutive_same_failures"] == 2
        assert "timestamp" in data

    def test_handles_empty_problems(self, tmp_path: Path) -> None:
        """_save_iteration_state handles None problems."""
        state = LoopState(iteration=1)
        result = CommandResult(exit_code=EXIT_SUCCESS, problems=None)

        state_path = tmp_path / "state.json"
        _save_iteration_state(state_path, state, result)

        data = json.loads(state_path.read_text())
        assert data["problems_count"] == 0


# =============================================================================
# Main Command Tests (cmd_ai_loop)
# =============================================================================


class TestCmdAiLoop:
    """Tests for cmd_ai_loop main command."""

    def test_success_on_first_iteration(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop returns success when CI passes on first try."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="All checks passed")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=5,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_SUCCESS
        assert "1 iteration" in result.summary
        assert result.data["iterations"] == 1

    def test_success_after_multiple_iterations(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop returns success when CI passes after fixes."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        iteration_count = 0

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count < 3:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary="Tests failed",
                    problems=[{"tool": f"pytest-{iteration_count}", "message": "failure"}],
                )
            return CommandResult(exit_code=EXIT_SUCCESS, summary="All checks passed")

        def mock_cmd_fix(args: argparse.Namespace) -> CommandResult:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Fixed",
                data={"fixes": ["auto-fix-1"]},
            )

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setattr("cihub.commands.fix.cmd_fix", mock_cmd_fix)
        monkeypatch.setattr(
            "cihub.commands.ai_loop_local.get_worktree_changes",
            lambda _path: ["fixed.txt"],
        )

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=5,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data["iterations"] == 3
        assert "auto-fix-1" in result.data["fixes_applied"]

    def test_failure_after_max_iterations(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop fails after max iterations reached."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        iteration_count = 0

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            nonlocal iteration_count
            iteration_count += 1
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Tests failed",
                problems=[{"tool": f"pytest-{iteration_count}", "message": "failure"}],
            )

        def mock_cmd_fix(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Fixed", data={"fixes": []})

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setattr("cihub.commands.fix.cmd_fix", mock_cmd_fix)
        monkeypatch.setattr(
            "cihub.commands.ai_loop_local.get_worktree_changes",
            lambda _path: ["fixed.txt"],
        )

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=3,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["iterations"] == 3
        assert "Could not fix" in result.summary
        assert result.data["stop_reason"] == "max_iterations"

    def test_circuit_breaker_stops_loop(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop stops when circuit breaker triggers."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        # Same failure every time triggers circuit breaker
        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Tests failed",
                problems=[{"tool": "pytest", "message": "same error every time"}],
            )

        def mock_cmd_fix(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Fixed", data={"fixes": []})

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setattr("cihub.commands.fix.cmd_fix", mock_cmd_fix)
        monkeypatch.setattr(
            "cihub.commands.ai_loop_local.get_worktree_changes",
            lambda _path: ["fixed.txt"],
        )

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=10,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        result = cmd_ai_loop(args)

        # Should stop before max_iterations due to circuit breaker
        assert result.exit_code == EXIT_FAILURE
        threshold = AI_LOOP_CONFIG["circuit_breaker"]["same_error_threshold"]
        assert result.data["iterations"] <= threshold
        assert result.data["stop_reason"] == "repeat_failures"

    def test_flaky_detection_stops_on_test_failures(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop stops early when flaky tests are detected."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)
        ci_output_dir = output_dir / "ci"
        ci_output_dir.mkdir(parents=True)

        history_path = ci_output_dir / "history.jsonl"
        history_entries = [
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "failed", "failure_count": 1},
            {"overall_status": "success", "failure_count": 0},
            {"overall_status": "failed", "failure_count": 1},
            {"overall_status": "success", "failure_count": 0},
        ]
        history_path.write_text(
            "\n".join(json.dumps(entry) for entry in history_entries),
            encoding="utf-8",
        )

        triage_path = ci_output_dir / "triage.json"
        triage_path.write_text(
            json.dumps(
                {
                    "failures": [
                        {
                            "tool": "pytest",
                            "category": "test",
                            "status": "failed",
                            "reason": "tool_failed",
                            "message": "pytest failed",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Tests failed",
                problems=[{"tool": "pytest", "message": "failure"}],
            )

        def mock_cmd_fix(args: argparse.Namespace) -> CommandResult:
            raise AssertionError("fix should not run on flaky stop")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setattr("cihub.commands.fix.cmd_fix", mock_cmd_fix)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=5,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["iterations"] == 1
        assert result.data["stop_reason"] == "flaky"
        assert any(item["code"] == "CIHUB-AI-FLAKY-DETECTED" for item in result.suggestions)

    def test_report_only_mode_calls_fix_with_report_flag(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop in report-only mode calls fix with report=True."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        fix_calls: list[argparse.Namespace] = []

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary="Tests failed",
                problems=[{"tool": "pytest", "message": "failure"}],
            )

        def mock_cmd_fix(args: argparse.Namespace) -> CommandResult:
            fix_calls.append(args)
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Report generated", data={})

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setattr("cihub.commands.fix.cmd_fix", mock_cmd_fix)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=1,
            fix_mode="report-only",
            emit_report=True,
            resume=True,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_FAILURE
        assert len(fix_calls) == 1
        assert fix_calls[0].report is True
        assert fix_calls[0].ai is True

    def test_handles_cmd_fix_exception(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop continues when cmd_fix raises exception."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        iteration_count = 0

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count < 2:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary="Tests failed",
                    problems=[{"tool": "pytest", "message": "failure"}],
                )
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Passed")

        def mock_cmd_fix(args: argparse.Namespace) -> CommandResult:
            raise RuntimeError("Fix command failed")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setattr("cihub.commands.fix.cmd_fix", mock_cmd_fix)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=5,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        # Should not raise, should continue loop
        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_SUCCESS

    def test_creates_output_directory(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_dir" / "ai-loop"

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Passed")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=1,
            fix_mode="safe",
            emit_report=False,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_SUCCESS
        assert output_dir.exists()
        assert any(output_dir.iterdir())

    def test_uses_default_output_dir(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop uses .cihub/ai-loop as default output directory."""

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Passed")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=None,
            max_iterations=1,
            fix_mode="safe",
            emit_report=False,
        )

        result = cmd_ai_loop(args)

        assert result.exit_code == EXIT_SUCCESS
        assert (tmp_path / ".cihub" / "ai-loop").exists()

    def test_result_includes_duration(self, tmp_path: Path, monkeypatch) -> None:
        """cmd_ai_loop result includes duration_seconds."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Passed")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=1,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        result = cmd_ai_loop(args)

        assert "duration_seconds" in result.data
        assert result.data["duration_seconds"] >= 0

    def test_env_var_restoration_on_success(self, tmp_path: Path, monkeypatch) -> None:
        """Verify CIHUB_EMIT_TRIAGE is restored after successful run."""
        output_dir = tmp_path / ".cihub" / "ai-loop"
        output_dir.mkdir(parents=True)

        original_value = "original_val"
        captured_during_run = []

        def mock_cmd_ci(args: argparse.Namespace) -> CommandResult:
            captured_during_run.append(os.environ.get("CIHUB_EMIT_TRIAGE"))
            return CommandResult(exit_code=EXIT_SUCCESS, summary="Passed")

        monkeypatch.setattr("cihub.commands.ci.cmd_ci", mock_cmd_ci)
        monkeypatch.setenv("CIHUB_EMIT_TRIAGE", original_value)

        args = argparse.Namespace(
            repo=str(tmp_path),
            output_dir=str(output_dir),
            max_iterations=1,
            fix_mode="safe",
            emit_report=False,
            resume=True,
        )

        cmd_ai_loop(args)

        # During run it should be "true"
        assert captured_during_run[0] == "true"
        # After run it should be restored
        assert os.environ.get("CIHUB_EMIT_TRIAGE") == original_value


# =============================================================================
# Configuration Tests
# =============================================================================


class TestAiLoopConfig:
    """Tests for AI_LOOP_CONFIG structure."""

    def test_config_has_required_keys(self) -> None:
        """AI_LOOP_CONFIG has all required configuration keys."""
        assert "max_iterations" in AI_LOOP_CONFIG
        assert "max_duration_seconds" in AI_LOOP_CONFIG
        assert "circuit_breaker" in AI_LOOP_CONFIG
        assert "forbidden_paths" in AI_LOOP_CONFIG

    def test_circuit_breaker_has_required_keys(self) -> None:
        """Circuit breaker config has required keys."""
        cb = AI_LOOP_CONFIG["circuit_breaker"]
        assert "consecutive_failures" in cb
        assert "same_error_threshold" in cb
        assert "error_patterns" in cb

    def test_forbidden_paths_includes_workflows(self) -> None:
        """Forbidden paths include workflow files for safety."""
        paths = AI_LOOP_CONFIG["forbidden_paths"]
        assert any(".github/workflows" in p for p in paths)

    def test_forbidden_paths_includes_env_files(self) -> None:
        """Forbidden paths include env files for secrets protection."""
        paths = AI_LOOP_CONFIG["forbidden_paths"]
        assert any(".env" in p for p in paths)

    def test_default_max_iterations_is_reasonable(self) -> None:
        """Default max_iterations is a reasonable value."""
        assert 1 <= AI_LOOP_CONFIG["max_iterations"] <= 20

    def test_default_max_duration_is_reasonable(self) -> None:
        """Default max_duration_seconds is reasonable (not too long)."""
        assert AI_LOOP_CONFIG["max_duration_seconds"] <= 1800  # 30 minutes max

    def test_error_patterns_is_list(self) -> None:
        """Error patterns is a list of strings."""
        patterns = AI_LOOP_CONFIG["circuit_breaker"]["error_patterns"]
        assert isinstance(patterns, list)
        assert all(isinstance(p, str) for p in patterns)

    def test_max_files_per_iteration_exists(self) -> None:
        """max_files_per_iteration configuration exists."""
        assert "max_files_per_iteration" in AI_LOOP_CONFIG
        assert AI_LOOP_CONFIG["max_files_per_iteration"] > 0
