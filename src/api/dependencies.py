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
        from src.testing.mock_adapters.embeddings import MockEmbeddings

        return MockEmbeddings()

    elif record_fixtures:
        # Recording mode: Wrap real provider with recording + httpx logging
        import httpx
        from langchain_openai import OpenAIEmbeddings

        from src.testing.mock_adapters.httpx_logging_transport import get_logging_transport
        from src.testing.mock_adapters.recording_wrapper import RecordingEmbeddings

        # Create OpenAI client with logging transport (Layer 3: raw HTTP)
        real_embeddings = OpenAIEmbeddings(
            http_client=httpx.Client(transport=get_logging_transport())
        )
        return RecordingEmbeddings(real_embeddings)

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
        from src.testing.mock_adapters.chat import MockChatModel

        return MockChatModel()

    elif record_fixtures:
        # Recording mode: Wrap real provider with recording + httpx logging + callback
        import httpx
        from langchain_openai import ChatOpenAI

        from src.testing.mock_adapters.httpx_logging_transport import get_logging_transport
        from src.testing.mock_adapters.langchain_logging_callback import get_langchain_logger
        from src.testing.mock_adapters.recording_wrapper import RecordingChatModel

        # Create OpenAI client with logging transport (Layer 3) + callback (Layer 1)
        real_chat = ChatOpenAI(
            temperature=0,  # deterministic
            http_client=httpx.Client(transport=get_logging_transport()),
            callbacks=[get_langchain_logger()],
        )
        return RecordingChatModel(real_chat)

    else:
        # Real mode: Return real provider
        from langchain_openai import ChatOpenAI

        return ChatOpenAI()
