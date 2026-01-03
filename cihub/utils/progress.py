"""Progress display utilities."""

from __future__ import annotations


def _bar(value: int) -> str:
    """Render a visual progress bar using Unicode block characters.

    Args:
        value: Percentage value (0-100). Values outside range are clamped.

    Returns:
        A 20-character progress bar string using █ and ░ characters.
    """
    if value < 0:
        value = 0
    filled = min(20, max(0, value // 5))
    return f"{'█' * filled}{'░' * (20 - filled)}"
