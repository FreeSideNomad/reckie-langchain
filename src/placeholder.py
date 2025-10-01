"""Placeholder module for CI/CD testing."""

from typing import Optional


def hello_world(name: Optional[str] = None) -> str:
    """
    Return a greeting message.

    Args:
        name: Optional name to greet

    Returns:
        Greeting message
    """
    if name:
        return f"Hello, {name}!"
    return "Hello, World!"


def add_numbers(a: int, b: int) -> int:
    """
    Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def is_even(number: int) -> bool:
    """
    Check if a number is even.

    Args:
        number: Number to check

    Returns:
        True if even, False otherwise
    """
    return number % 2 == 0
