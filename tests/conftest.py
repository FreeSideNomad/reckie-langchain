"""Pytest configuration and fixtures for all tests."""

import os
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest


@pytest.fixture
def mock_embeddings():
    """Fixture providing mock embeddings adapter."""
    from src.testing.mock_adapters.embeddings import MockEmbeddings

    return MockEmbeddings()


@pytest.fixture
def mock_chat():
    """Fixture providing mock chat model."""
    from src.testing.mock_adapters.chat import MockChatModel

    return MockChatModel()


@pytest.fixture
def embeddings_provider():
    """Fixture providing embeddings via dependency injection."""
    from src.api.dependencies import get_embeddings_provider

    return get_embeddings_provider()


@pytest.fixture
def chat_provider():
    """Fixture providing chat model via dependency injection."""
    from src.api.dependencies import get_chat_provider

    return get_chat_provider()
