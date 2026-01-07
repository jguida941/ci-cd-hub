"""Output formatting helpers for triage command.

This module provides human-readable formatting for various
triage analysis outputs (gate history, flaky detection, etc.).
"""

from __future__ import annotations

from typing import Any


def format_gate_history_output(gate_result: dict[str, Any]) -> list[str]:
    """Format gate history analysis for human-readable output.

    Args:
        gate_result: Result from detect_gate_changes()

    Returns:
        List of formatted output lines
    """
    lines = [
        "Gate History Analysis",
        "=" * 50,
        f"Runs analyzed: {gate_result['runs_analyzed']}",
    ]

    if gate_result.get("new_failures"):
        lines.append(f"New failures: {', '.join(gate_result['new_failures'])}")

    if gate_result.get("fixed_gates"):
        lines.append(f"Fixed gates: {', '.join(gate_result['fixed_gates'])}")

    if gate_result.get("recurring_failures"):
        lines.append("Recurring issues:")
        for item in gate_result["recurring_failures"]:
            lines.append(f"  - {item['gate']} (fails {item['fail_rate']}%): {''.join(item['history'])}")

    if gate_result.get("gate_history"):
        lines.append("Gate timeline (last 10 runs):")
        for gate, timeline in gate_result["gate_history"].items():
            lines.append(f"  - {gate}: {''.join(timeline)}")

    lines.append(f"Summary: {gate_result['summary']}")
    return lines


def format_flaky_output(flaky_result: dict[str, Any]) -> list[str]:
    """Format flaky analysis for human-readable output.

    Args:
        flaky_result: Result from detect_flaky_patterns()

    Returns:
        List of formatted output lines
    """
    suspected = "YES" if flaky_result["suspected_flaky"] else "No"
    lines = [
        "Flaky Test Analysis",
        "=" * 50,
        f"Runs analyzed: {flaky_result['runs_analyzed']}",
        f"State changes: {flaky_result['state_changes']}",
        f"Flakiness score: {flaky_result['flakiness_score']}%",
        f"Suspected flaky: {suspected}",
    ]

    if flaky_result.get("recent_history"):
        lines.append(f"Recent runs (newest last): {flaky_result['recent_history']}")

    if flaky_result.get("details"):
        lines.append("Details:")
        for detail in flaky_result["details"]:
            lines.append(f"  - {detail}")

    lines.append(f"Recommendation: {flaky_result['recommendation']}")
    return lines


# Backward compatibility aliases (with underscore prefix)
_format_gate_history_output = format_gate_history_output
_format_flaky_output = format_flaky_output


__all__ = [
    "format_flaky_output",
    "format_gate_history_output",
    # Backward compatibility
    "_format_flaky_output",
    "_format_gate_history_output",
]
