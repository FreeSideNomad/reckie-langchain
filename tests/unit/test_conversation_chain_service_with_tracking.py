"""Unit tests for ConversationChainServiceWithTracking."""

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import TimeoutException
from openai import RateLimitError

from src.database.models.conversation_metric import ConversationMetric
from src.services.conversation_chain_service_with_tracking import (
    ConversationChainServiceWithTracking,
)


class TestConversationChainServiceWithTracking:
    """Test suite for ConversationChainServiceWithTracking."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        return session

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_init(self, mock_db_session):
        """Test service initialization."""
        service = ConversationChainServiceWithTracking(
            db_session=mock_db_session,
            model="gpt-4-turbo",
            temperature=0.7,
            timeout=30,
        )

        assert service.model == "gpt-4-turbo"
        assert service.temperature == 0.7
        assert service.timeout == 30

    @patch("src.services.conversation_chain_service_with_tracking.ConversationChain")
    @patch("src.services.conversation_chain_service_with_tracking.PostgresChatMessageHistory")
    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "OPENAI_API_KEY": "test-key",
        },
    )
    def test_create_chain(self, mock_history, mock_conversation_chain, mock_db_session):
        """Test create_chain creates chain with memory."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()

        chain = service.create_chain(conversation_id)

        assert chain is not None
        mock_history.assert_called_once()
        mock_conversation_chain.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "OPENAI_API_KEY": "test-key",
        },
    )
    def test_record_metric(self, mock_db_session):
        """Test _record_metric saves metric to database."""
        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()
        correlation_id = uuid.uuid4()

        service._record_metric(
            conversation_id=conversation_id,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            duration_ms=1500,
            correlation_id=correlation_id,
            error_occurred=False,
        )

        # Verify metric was added to session
        mock_db_session.add.assert_called_once()
        metric = mock_db_session.add.call_args[0][0]

        assert isinstance(metric, ConversationMetric)
        assert metric.conversation_id == conversation_id
        assert metric.prompt_tokens == 100
        assert metric.completion_tokens == 50
        assert metric.total_tokens == 150
        assert metric.model == "gpt-4-turbo"
        assert metric.correlation_id == correlation_id
        assert metric.duration_ms == 1500
        assert metric.error_occurred is False

        mock_db_session.commit.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "OPENAI_API_KEY": "test-key",
        },
    )
    def test_record_metric_with_error(self, mock_db_session):
        """Test _record_metric records error details."""
        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()
        correlation_id = uuid.uuid4()

        service._record_metric(
            conversation_id=conversation_id,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=500,
            correlation_id=correlation_id,
            error_occurred=True,
            error_message="Rate limit exceeded",
        )

        metric = mock_db_session.add.call_args[0][0]

        assert metric.error_occurred is True
        assert metric.error_message == "Rate limit exceeded"
        assert metric.total_tokens == 0

    @pytest.mark.asyncio
    @patch("src.services.conversation_chain_service_with_tracking.get_openai_callback")
    @patch("src.services.conversation_chain_service_with_tracking.ConversationChain")
    @patch("src.services.conversation_chain_service_with_tracking.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_stream_response_tracks_tokens(
        self, mock_history, mock_conversation_chain, mock_callback, mock_db_session
    ):
        """Test stream_response tracks token usage."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        # Mock callback context manager
        mock_cb = MagicMock()
        mock_cb.prompt_tokens = 100
        mock_cb.completion_tokens = 50
        mock_cb.total_tokens = 150
        mock_callback.return_value.__enter__.return_value = mock_cb
        mock_callback.return_value.__exit__.return_value = None

        # Mock chain astream
        async def mock_astream(inputs):
            for chunk in [{"response": "Hello"}, {"response": " world"}]:
                yield chunk

        mock_chain_instance = MagicMock()
        mock_chain_instance.astream = mock_astream
        mock_conversation_chain.return_value = mock_chain_instance

        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()

        # Collect streamed tokens
        tokens = []
        async for token in service.stream_response(conversation_id, "Hi there"):
            tokens.append(token)

        assert tokens == ["Hello", " world"]

        # Verify metric was recorded
        mock_db_session.add.assert_called_once()
        metric = mock_db_session.add.call_args[0][0]

        assert metric.prompt_tokens == 100
        assert metric.completion_tokens == 50
        assert metric.total_tokens == 150
        assert metric.error_occurred is False

    @pytest.mark.asyncio
    @patch("src.services.conversation_chain_service_with_tracking.ConversationChain")
    @patch("src.services.conversation_chain_service_with_tracking.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_stream_response_handles_rate_limit(
        self, mock_history, mock_conversation_chain, mock_db_session
    ):
        """Test stream_response handles rate limit errors."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        # Mock chain astream to raise RateLimitError
        class MockAsyncIterator:
            def __init__(self):
                pass

            def __aiter__(self):
                return self

            async def __anext__(self):
                raise RateLimitError(
                    "Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body=None,
                )

        mock_chain_instance = MagicMock()
        mock_chain_instance.astream = MagicMock(return_value=MockAsyncIterator())
        mock_conversation_chain.return_value = mock_chain_instance

        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()

        # Should raise RateLimitError
        with pytest.raises(RateLimitError):
            async for _ in service.stream_response(conversation_id, "Hi there"):
                pass

        # Verify error metric was recorded
        mock_db_session.add.assert_called_once()
        metric = mock_db_session.add.call_args[0][0]

        assert metric.error_occurred is True
        assert "Rate limit exceeded" in metric.error_message
        assert metric.total_tokens == 0

    @patch("src.services.conversation_chain_service_with_tracking.get_openai_callback")
    @patch("src.services.conversation_chain_service_with_tracking.ConversationChain")
    @patch("src.services.conversation_chain_service_with_tracking.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_invoke_with_tracking(
        self, mock_history, mock_conversation_chain, mock_callback, mock_db_session
    ):
        """Test invoke_with_tracking (non-streaming)."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        # Mock callback
        mock_cb = MagicMock()
        mock_cb.prompt_tokens = 100
        mock_cb.completion_tokens = 50
        mock_cb.total_tokens = 150
        mock_callback.return_value.__enter__.return_value = mock_cb
        mock_callback.return_value.__exit__.return_value = None

        # Mock chain invoke
        mock_chain_instance = MagicMock()
        mock_chain_instance.invoke.return_value = {"response": "Hello world"}
        mock_conversation_chain.return_value = mock_chain_instance

        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()

        response = service.invoke_with_tracking(conversation_id, "Hi there")

        assert response == "Hello world"

        # Verify metric was recorded
        mock_db_session.add.assert_called_once()
        metric = mock_db_session.add.call_args[0][0]

        assert metric.total_tokens == 150
        assert metric.error_occurred is False

    @patch("src.services.conversation_chain_service_with_tracking.get_openai_callback")
    @patch("src.services.conversation_chain_service_with_tracking.ConversationChain")
    @patch("src.services.conversation_chain_service_with_tracking.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_invoke_with_tracking_handles_timeout(
        self, mock_history, mock_conversation_chain, mock_callback, mock_db_session
    ):
        """Test invoke_with_tracking handles timeout errors."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        # Mock chain to raise httpx TimeoutException
        mock_chain_instance = MagicMock()
        mock_chain_instance.invoke.side_effect = TimeoutException("Request timed out")
        mock_conversation_chain.return_value = mock_chain_instance

        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()

        # Should raise TimeoutException
        with pytest.raises(TimeoutException):
            service.invoke_with_tracking(conversation_id, "Hi there")

        # Verify error metric was recorded
        mock_db_session.add.assert_called_once()
        metric = mock_db_session.add.call_args[0][0]

        assert metric.error_occurred is True
        assert "Request timed out" in metric.error_message

    @patch("src.services.conversation_chain_service_with_tracking.PostgresChatMessageHistory")
    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "OPENAI_API_KEY": "test-key",
        },
    )
    def test_get_conversation_history(self, mock_history, mock_db_session):
        """Test get_conversation_history retrieves messages."""
        from langchain.schema import AIMessage, HumanMessage

        # Mock message history
        mock_history_instance = MagicMock()
        mock_history_instance.messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
            AIMessage(content="I'm doing well!"),
        ]
        mock_history.return_value = mock_history_instance

        service = ConversationChainServiceWithTracking(db_session=mock_db_session)
        conversation_id = uuid.uuid4()

        history = service.get_conversation_history(conversation_id)

        assert len(history) == 4
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}
        assert history[2] == {"role": "user", "content": "How are you?"}
        assert history[3] == {"role": "assistant", "content": "I'm doing well!"}
