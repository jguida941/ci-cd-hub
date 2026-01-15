"""CI/CD Hub Scaffold - Sample Tests.

These tests demonstrate:
- pytest test discovery (test_ prefix)
- Basic assertions (for coverage metrics)
- Mutation-killable logic (for mutmut)

Run with: pytest tests/
Coverage: pytest --cov=. tests/
"""

from app import add, is_even


def test_add() -> None:
    """Test addition function."""
    assert add(2, 3) == 5


def test_is_even() -> None:
    """Test even number detection."""
    assert is_even(4)
    assert not is_even(5)
