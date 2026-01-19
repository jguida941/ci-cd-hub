"""Event sink for streaming CLI output without direct prints in commands."""

from __future__ import annotations

from typing import Any, Callable

EventSink = Callable[[str, dict[str, Any]], None]

_EVENT_SINK: EventSink | None = None


def set_event_sink(sink: EventSink | None) -> None:
    """Register a sink for streaming output events."""
    global _EVENT_SINK
    _EVENT_SINK = sink


def get_event_sink() -> EventSink | None:
    """Return the active event sink (if any)."""
    return _EVENT_SINK


def emit_event(event: str, payload: dict[str, Any] | None = None) -> None:
    """Emit an output event if a sink is registered."""
    if _EVENT_SINK is None:
        return
    _EVENT_SINK(event, payload or {})
