from app import add, is_even


def test_add() -> None:
    assert add(2, 3) == 5


def test_is_even() -> None:
    assert is_even(4)
    assert not is_even(5)
