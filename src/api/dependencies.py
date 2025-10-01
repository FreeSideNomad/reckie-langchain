"""FastAPI dependency injection functions."""

import os
from typing import Generator

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_embeddings_provider() -> Embeddings:
    """
    Get embeddings provider based on environment configuration.

    Returns mock or real embeddings based on USE_MOCK_ADAPTERS env var.
    Supports recording mode with RECORD_FIXTURES env var.

    Environment Variables:
        USE_MOCK_ADAPTERS: If "true", returns mock embeddings (no API calls)
        RECORD_FIXTURES: If "true", wraps real provider with recording
        RECORD_FIXTURES_PATH: Path to save fixtures (default: tests/fixtures/mock_adapters)

    Returns:
        Embeddings: Mock, recording, or real embeddings provider

    Example:
        # Mock mode (CI/CD, local testing)
        export USE_MOCK_ADAPTERS=true
        embeddings = get_embeddings_provider()  # → MockEmbeddings

        # Recording mode (capture real API data)
        export RECORD_FIXTURES=true
        embeddings = get_embeddings_provider()  # → RecordingEmbeddings(OpenAIEmbeddings())

        # Real mode (production)
        embeddings = get_embeddings_provider()  # → OpenAIEmbeddings()
    """
    use_mock = os.getenv("USE_MOCK_ADAPTERS", "false").lower() == "true"
    record_fixtures = os.getenv("RECORD_FIXTURES", "false").lower() == "true"

    if use_mock:
        # Mock mode: Return mock embeddings (no API calls)
        from src.testing.mock_adapters.embeddings import MockEmbeddings  # type: ignore

        return MockEmbeddings()  # type: ignore

    elif record_fixtures:
        # Recording mode: Wrap real provider with recording
        from langchain_openai import OpenAIEmbeddings

        from src.testing.mock_adapters.recording_wrapper import RecordingEmbeddings  # type: ignore

        real_embeddings = OpenAIEmbeddings()
        return RecordingEmbeddings(real_embeddings)  # type: ignore

    else:
        # Real mode: Return real provider
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings()


def get_chat_provider() -> BaseChatModel:
    """
    Get chat model provider based on environment configuration.

    Returns mock or real chat model based on USE_MOCK_ADAPTERS env var.
    Supports recording mode with RECORD_FIXTURES env var.

    Environment Variables:
        USE_MOCK_ADAPTERS: If "true", returns mock chat model (no API calls)
        RECORD_FIXTURES: If "true", wraps real provider with recording
        RECORD_FIXTURES_PATH: Path to save fixtures (default: tests/fixtures/mock_adapters)

    Returns:
        BaseChatModel: Mock, recording, or real chat model

    Example:
        # Mock mode (CI/CD, local testing)
        export USE_MOCK_ADAPTERS=true
        chat = get_chat_provider()  # → MockChatModel

        # Recording mode (capture real API data)
        export RECORD_FIXTURES=true
        chat = get_chat_provider()  # → RecordingChatModel(ChatOpenAI())

        # Real mode (production)
        chat = get_chat_provider()  # → ChatOpenAI()
    """
    use_mock = os.getenv("USE_MOCK_ADAPTERS", "false").lower() == "true"
    record_fixtures = os.getenv("RECORD_FIXTURES", "false").lower() == "true"

    if use_mock:
        # Mock mode: Return mock chat model (no API calls)
        from src.testing.mock_adapters.chat import MockChatModel  # type: ignore

        return MockChatModel()  # type: ignore

    elif record_fixtures:
        # Recording mode: Wrap real provider with recording
        from langchain_openai import ChatOpenAI

        from src.testing.mock_adapters.recording_wrapper import RecordingChatModel  # type: ignore

        real_chat = ChatOpenAI(temperature=0)  # temperature=0 for deterministic
        return RecordingChatModel(real_chat)  # type: ignore

    else:
        # Real mode: Return real provider
        from langchain_openai import ChatOpenAI

        return ChatOpenAI()
