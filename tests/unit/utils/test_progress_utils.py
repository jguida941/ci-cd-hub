"""Tests for cihub.utils.progress module."""

from __future__ import annotations

from cihub.utils.progress import _bar


class TestBar:
    """Tests for _bar progress bar function."""

    def test_zero_percent(self) -> None:
        """0% shows all empty blocks."""
        result = _bar(0)
        assert result == "░" * 20

    def test_hundred_percent(self) -> None:
        """100% shows all filled blocks."""
        result = _bar(100)
        assert result == "█" * 20

    def test_fifty_percent(self) -> None:
        """50% shows half filled, half empty."""
        result = _bar(50)
        assert result == "█" * 10 + "░" * 10

    def test_twenty_percent(self) -> None:
        """20% shows 4 filled blocks."""
        result = _bar(20)
        assert result == "████░░░░░░░░░░░░░░░░"

    def test_negative_clamped_to_zero(self) -> None:
        """Negative values are clamped to 0%."""
        result = _bar(-10)
        assert result == "░" * 20

    def test_over_hundred_clamped(self) -> None:
        """Values over 100 are clamped to 100%."""
        result = _bar(150)
        assert result == "█" * 20

    def test_partial_percentage(self) -> None:
        """Partial percentages round down to nearest 5%."""
        result = _bar(23)  # Should be 4 blocks (20%)
        assert result == "████░░░░░░░░░░░░░░░░"
