"""CI/CD Hub Scaffold - Sample Tests.

These tests demonstrate:
- pytest test discovery (test_ prefix)
- Basic assertions (for coverage metrics)
- Mutation-killable logic (for mutmut)

Run with: pytest tests/
Coverage: pytest --cov=cihub_setup_sample tests/
"""

from cihub_setup_sample import add


def test_add() -> None:
    """Test addition function."""
    assert add(2, 3) == 5
