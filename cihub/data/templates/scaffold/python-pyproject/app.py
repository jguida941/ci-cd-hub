"""CI/CD Hub Scaffold - Sample Application.

This module provides simple functions that demonstrate:
- Type annotations (for mypy)
- Testable logic (for pytest + mutmut)
- Clean code style (for ruff/black/isort)

Replace this with your actual application code.
"""


def add(left: int, right: int) -> int:
    """Add two integers."""
    return left + right


def is_even(value: int) -> bool:
    """Check if a value is even."""
    return value % 2 == 0
