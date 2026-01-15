"""Tests for the core module."""

from cihub_src_sample.core import add, greet


def test_greet() -> None:
    """Test the greet function."""
    assert greet("World") == "Hello, World!"


def test_add() -> None:
    """Test the add function."""
    assert add(2, 3) == 5
