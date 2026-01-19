"""Analysis helpers for the AI loop."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from cihub.commands.ai_loop_types import AI_LOOP_CONFIG, LoopState
from cihub.types import CommandResult


def break_reason(state: LoopState, result: CommandResult) -> str | None:
    """Circuit breaker logic to prevent infinite loops."""
    circuit_config = AI_LOOP_CONFIG.get("circuit_breaker", {})
    same_error_threshold = circuit_config.get("same_error_threshold")
    if same_error_threshold is None:
        same_error_threshold = circuit_config.get("consecutive_failures", 3)

    elapsed = time_elapsed_seconds(state)
    if elapsed > state.max_duration_seconds:
        return "duration_timeout"

    error_patterns = circuit_config.get("error_patterns", [])
    for problem in result.problems or []:
        msg = str(problem.get("message", "")).lower()
        for pattern in error_patterns:
            if pattern.lower() in msg:
                return "error_pattern"

    current_failures = failure_signature(result)

    if not current_failures:
        state.last_failure_signature = frozenset()
        state.consecutive_same_failures = 0
        return None

    if current_failures == state.last_failure_signature:
        state.consecutive_same_failures += 1
    else:
        state.last_failure_signature = current_failures
        state.consecutive_same_failures = 1

    if state.consecutive_same_failures >= same_error_threshold:
        return "repeat_failures"

    return None


def should_break(state: LoopState, result: CommandResult) -> bool:
    return break_reason(state, result) is not None


def failure_signature(result: CommandResult) -> frozenset[str]:
    return frozenset(
        f"{problem.get('tool', 'unknown')}:{problem.get('message', '')[:50]}" for problem in (result.problems or [])
    )


def hash_failure_signature(signature: frozenset[str]) -> str:
    if not signature:
        return ""
    payload = "\n".join(sorted(signature))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_triage_failures(output_dir: Path) -> list[dict[str, Any]]:
    triage_path = output_dir / "triage.json"
    if not triage_path.exists():
        return []
    try:
        payload = json.loads(triage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    failures = payload.get("failures")
    if isinstance(failures, list):
        return [item for item in failures if isinstance(item, dict)]
    return []


def extract_failures(triage_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not triage_data:
        return []
    failures = triage_data.get("failures", [])
    if isinstance(failures, list):
        return [item for item in failures if isinstance(item, dict)]
    return []


def problems_from_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    problems = []
    for failure in failures:
        problems.append(
            {
                "tool": failure.get("tool", "unknown"),
                "message": failure.get("message", ""),
            }
        )
    return problems


def is_test_only_failures(failures: list[dict[str, Any]]) -> bool:
    if not failures:
        return False
    categories = {str(item.get("category", "")).lower() for item in failures if item.get("category")}
    return bool(categories) and categories.issubset({"test"})


def dedupe_suggestions(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in suggestions:
        message = str(item.get("message", ""))
        code = str(item.get("code", ""))
        key = (code, message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def time_elapsed_seconds(state: LoopState) -> float:
    return max(0.0, (time.time() - state.start_time))
