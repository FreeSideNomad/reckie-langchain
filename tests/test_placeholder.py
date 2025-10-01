"""Tests for placeholder module."""

import pytest

from src.placeholder import add_numbers, hello_world, is_even


class TestHelloWorld:
    """Tests for hello_world function."""

    def test_hello_world_no_name(self) -> None:
        """Test hello_world with no name."""
        result = hello_world()
        assert result == "Hello, World!"

    def test_hello_world_with_name(self) -> None:
        """Test hello_world with a name."""
        result = hello_world("Alice")
        assert result == "Hello, Alice!"

    def test_hello_world_empty_string(self) -> None:
        """Test hello_world with empty string."""
        result = hello_world("")
        assert result == "Hello, World!"

    def test_hello_world_none(self) -> None:
        """Test hello_world with None explicitly."""
        result = hello_world(None)
        assert result == "Hello, World!"


class TestAddNumbers:
    """Tests for add_numbers function."""

    def test_add_positive_numbers(self) -> None:
        """Test adding two positive numbers."""
        result = add_numbers(2, 3)
        assert result == 5

    def test_add_negative_numbers(self) -> None:
        """Test adding two negative numbers."""
        result = add_numbers(-2, -3)
        assert result == -5

    def test_add_mixed_numbers(self) -> None:
        """Test adding positive and negative numbers."""
        result = add_numbers(5, -3)
        assert result == 2

    def test_add_zero(self) -> None:
        """Test adding with zero."""
        result = add_numbers(0, 5)
        assert result == 5

    def test_add_large_numbers(self) -> None:
        """Test adding large numbers."""
        result = add_numbers(1000000, 2000000)
        assert result == 3000000


class TestIsEven:
    """Tests for is_even function."""

    def test_even_positive(self) -> None:
        """Test with positive even number."""
        assert is_even(4) is True

    def test_odd_positive(self) -> None:
        """Test with positive odd number."""
        assert is_even(5) is False

    def test_even_negative(self) -> None:
        """Test with negative even number."""
        assert is_even(-4) is True

    def test_odd_negative(self) -> None:
        """Test with negative odd number."""
        assert is_even(-5) is False

    def test_zero(self) -> None:
        """Test with zero."""
        assert is_even(0) is True

    def test_large_even(self) -> None:
        """Test with large even number."""
        assert is_even(1000000) is True

    def test_large_odd(self) -> None:
        """Test with large odd number."""
        assert is_even(1000001) is False


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (1, 1, 2),
        (0, 0, 0),
        (-1, 1, 0),
        (10, 20, 30),
    ],
)
def test_add_numbers_parametrized(a: int, b: int, expected: int) -> None:
    """Parametrized test for add_numbers."""
    assert add_numbers(a, b) == expected


@pytest.mark.parametrize(
    "number,expected",
    [
        (0, True),
        (1, False),
        (2, True),
        (3, False),
        (100, True),
        (101, False),
    ],
)
def test_is_even_parametrized(number: int, expected: bool) -> None:
    """Parametrized test for is_even."""
    assert is_even(number) is expected
