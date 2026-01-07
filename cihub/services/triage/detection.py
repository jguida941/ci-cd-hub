"""Flaky test and regression detection functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import TEST_COUNT_DROP_THRESHOLD


def detect_test_count_regression(history_path: Path, current_count: int) -> list[dict[str, Any]]:
    """Detect test count regression by comparing to previous runs (Issue 16).

    Args:
        history_path: Path to history.jsonl file.
        current_count: Current test count from this run.

    Returns:
        List of warning dicts to add to triage bundle.
    """
    warnings: list[dict[str, Any]] = []

    if not history_path.exists() or current_count == 0:
        return warnings

    # Read last entry from history
    try:
        lines = history_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return warnings

        # Get the most recent entry
        last_entry = json.loads(lines[-1])
        previous_count = last_entry.get("tests_total", 0)

        if previous_count == 0:
            return warnings

        # Calculate drop percentage
        drop_pct = (previous_count - current_count) / previous_count

        if drop_pct > TEST_COUNT_DROP_THRESHOLD:
            warnings.append(
                {
                    "type": "test_count_regression",
                    "severity": "warning",
                    "message": (
                        f"Test count dropped {drop_pct:.1%}: "
                        f"{previous_count} → {current_count} (-{previous_count - current_count} tests)"
                    ),
                    "previous_count": previous_count,
                    "current_count": current_count,
                    "drop_percentage": round(drop_pct * 100, 1),
                    "hint": (
                        "Check if tests were deleted or excluded. "
                        "Use 'cihub triage --history' to view test count trends."
                    ),
                }
            )

        # Coverage regression detection could be added in the future once current coverage
        # is passed into this helper (Issue 16 follow-up).

    except (json.JSONDecodeError, KeyError, TypeError):
        # Ignore malformed history entries
        pass

    return warnings


def detect_flaky_patterns(history_path: Path, min_runs: int = 5) -> dict[str, Any]:
    """Detect flaky test patterns from triage history.

    A "flaky" pattern is detected when:
    - The same repo/branch alternates between pass and fail
    - Failure counts fluctuate without code changes
    - State changes more than expected for the run count

    Args:
        history_path: Path to history.jsonl file (same as write_triage_bundle uses).
        min_runs: Minimum runs required for flaky analysis.

    Returns:
        Dict with flakiness analysis: score, state_changes, runs_analyzed, details.
    """
    result: dict[str, Any] = {
        "flakiness_score": 0.0,
        "state_changes": 0,
        "runs_analyzed": 0,
        "suspected_flaky": False,
        "details": [],
        "recommendation": "",
    }

    if not history_path.exists():
        result["recommendation"] = "No history available. Run CI multiple times to enable flaky detection."
        return result

    try:
        lines = history_path.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < min_runs:
            result["runs_analyzed"] = len(lines)
            result["recommendation"] = f"Need at least {min_runs} runs for flaky analysis (have {len(lines)})."
            return result

        entries = [json.loads(line) for line in lines]
        result["runs_analyzed"] = len(entries)

        # Analyze state transitions (pass → fail → pass indicates flakiness)
        state_changes = 0
        prev_status = None
        failure_counts: list[int] = []

        for entry in entries:
            status = entry.get("overall_status", "")
            is_passing = status in ("success", "passed")
            failure_count = entry.get("failure_count", 0)
            failure_counts.append(failure_count)

            if prev_status is not None and is_passing != prev_status:
                state_changes += 1

            prev_status = is_passing

        result["state_changes"] = state_changes

        # Calculate flakiness score:
        # - 0% = perfectly stable (all pass or all fail)
        # - 100% = maximally flaky (alternates every run)
        max_possible_changes = len(entries) - 1
        if max_possible_changes > 0:
            flakiness_score = (state_changes / max_possible_changes) * 100
            result["flakiness_score"] = round(flakiness_score, 1)

        # Detect suspected flakiness (score > 30% suggests instability)
        if result["flakiness_score"] > 30:
            result["suspected_flaky"] = True
            result["details"].append(f"High state change rate: {state_changes} changes in {len(entries)} runs")

        # Analyze failure count variance
        if failure_counts:
            avg_failures = sum(failure_counts) / len(failure_counts)
            variance = sum((f - avg_failures) ** 2 for f in failure_counts) / len(failure_counts)

            if variance > 1 and avg_failures > 0:
                result["details"].append(f"Failure count variance: {variance:.1f} (avg failures: {avg_failures:.1f})")
                result["suspected_flaky"] = True

        # Generate recommendation
        if result["suspected_flaky"]:
            result["recommendation"] = (
                "Flaky behavior detected. Consider:\n"
                "  1. Check for timing-dependent tests\n"
                "  2. Look for external service dependencies\n"
                "  3. Review pytest output for specific failing tests\n"
                "  4. Run 'pytest --last-failed' locally to reproduce"
            )
        else:
            result["recommendation"] = "CI appears stable. No obvious flaky patterns detected."

        # Add recent history summary
        recent_statuses = [
            "pass" if e.get("overall_status") in ("success", "passed") else "fail" for e in entries[-10:]
        ]
        result["recent_history"] = "".join(recent_statuses)

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        result["recommendation"] = f"Error analyzing history: {exc}"

    return result


def detect_gate_changes(history_path: Path, min_runs: int = 2) -> dict[str, Any]:
    """Detect gate status changes over time from triage history.

    Tracks which gates have changed status (passed→failed or failed→passed)
    across runs to identify unstable or recently fixed gates.

    Args:
        history_path: Path to history.jsonl file.
        min_runs: Minimum runs required for analysis.

    Returns:
        Dict with gate change analysis: new_failures, fixed_gates, recurring_failures.
    """
    result: dict[str, Any] = {
        "runs_analyzed": 0,
        "new_failures": [],  # Gates that started failing recently
        "fixed_gates": [],  # Gates that were fixed recently
        "recurring_failures": [],  # Gates that fail repeatedly
        "gate_history": {},  # Per-gate status over time
        "summary": "",
    }

    if not history_path.exists():
        result["summary"] = "No history available."
        return result

    try:
        lines = history_path.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < min_runs:
            result["runs_analyzed"] = len(lines)
            result["summary"] = f"Need at least {min_runs} runs for gate analysis (have {len(lines)})."
            return result

        entries = [json.loads(line) for line in lines]
        result["runs_analyzed"] = len(entries)

        # Build per-gate history
        gate_history: dict[str, list[bool]] = {}  # gate -> [failed, failed, passed, ...]

        for entry in entries:
            gate_failures = entry.get("gate_failures", [])
            all_gates_seen: set[str] = set()

            # Mark failures
            for gate in gate_failures:
                if gate not in gate_history:
                    gate_history[gate] = []
                gate_history[gate].append(True)  # True = failed
                all_gates_seen.add(gate)

            # Mark passes for gates we've seen before but aren't failing now
            for gate in gate_history:
                if gate not in all_gates_seen:
                    gate_history[gate].append(False)  # False = passed

        # Analyze gate patterns
        for gate, history in gate_history.items():
            if len(history) < min_runs:
                continue

            recent = history[-3:] if len(history) >= 3 else history
            older = history[:-3] if len(history) > 3 else []

            # New failure: wasn't failing before, now failing
            if recent[-1] and (not older or not any(older)):
                result["new_failures"].append(gate)

            # Fixed: was failing, now passing
            if not recent[-1] and any(older):
                result["fixed_gates"].append(gate)

            # Recurring: fails more than 50% of the time
            fail_rate = sum(history) / len(history)
            if fail_rate > 0.5 and len(history) >= 3:
                result["recurring_failures"].append(
                    {
                        "gate": gate,
                        "fail_rate": round(fail_rate * 100, 1),
                        "history": ["fail" if f else "pass" for f in history[-10:]],
                    }
                )

        result["gate_history"] = {k: ["fail" if f else "pass" for f in v[-10:]] for k, v in gate_history.items()}

        # Generate summary
        parts = []
        if result["new_failures"]:
            parts.append(f"New failures: {', '.join(result['new_failures'])}")
        if result["fixed_gates"]:
            parts.append(f"Fixed gates: {', '.join(result['fixed_gates'])}")
        if result["recurring_failures"]:
            recurring_names = [r["gate"] for r in result["recurring_failures"]]
            parts.append(f"Recurring issues: {', '.join(recurring_names)}")

        result["summary"] = "; ".join(parts) if parts else "No significant gate changes detected."

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        result["summary"] = f"Error analyzing history: {exc}"

    return result
