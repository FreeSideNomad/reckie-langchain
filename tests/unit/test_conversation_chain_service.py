"""Unit tests for ConversationChainService."""

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.services.conversation_chain_service import ConversationChainService


class TestConversationChainService:
    """Test suite for ConversationChainService."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_service_initialization_default(self):
        """Test service initializes with default parameters."""
        service = ConversationChainService()

        assert service.model == "gpt-4-turbo"
        assert service.temperature == 0.7
        assert service.max_context_messages == 10

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_service_initialization_custom(self):
        """Test service initializes with custom parameters."""
        service = ConversationChainService(
            model="gpt-3.5-turbo", temperature=0.5, max_context_messages=5
        )

        assert service.model == "gpt-3.5-turbo"
        assert service.temperature == 0.5
        assert service.max_context_messages == 5

    @patch("src.services.conversation_chain_service.ConversationChain")
    @patch("src.services.conversation_chain_service.PostgresChatMessageHistory")
    @patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql://test:test@localhost/test", "OPENAI_API_KEY": "test-key"},
    )
    def test_create_chain_with_default_connection(self, mock_history, mock_chain):
        """Test create_chain uses DATABASE_URL from environment."""
        # Mock PostgresChatMessageHistory properly
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        service = ConversationChainService()
        conversation_id = uuid.uuid4()

        service.create_chain(conversation_id)

        # Verify PostgresChatMessageHistory was called with env DATABASE_URL
        mock_history.assert_called_once_with(
            connection_string="postgresql://test:test@localhost/test",
            session_id=str(conversation_id),
        )

        # Verify ConversationChain was called
        assert mock_chain.called

    @patch("src.services.conversation_chain_service.ConversationChain")
    @patch("src.services.conversation_chain_service.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_create_chain_with_custom_connection(self, mock_history, mock_chain):
        """Test create_chain with custom connection string."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        service = ConversationChainService()
        conversation_id = uuid.uuid4()
        custom_conn = "postgresql://custom:custom@localhost/custom"

        service.create_chain(conversation_id, custom_conn)

        # Verify PostgresChatMessageHistory was called with custom connection
        mock_history.assert_called_once_with(
            connection_string=custom_conn, session_id=str(conversation_id)
        )

        # Verify ConversationChain was called
        assert mock_chain.called

    @patch("src.services.conversation_chain_service.ConversationChain")
    @patch("src.services.conversation_chain_service.PostgresChatMessageHistory")
    @patch("src.services.conversation_chain_service.ChatOpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_create_chain_configures_llm(self, mock_chat_openai, mock_history, mock_chain):
        """Test create_chain configures LLM with correct parameters."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        service = ConversationChainService(model="gpt-3.5-turbo", temperature=0.5)
        conversation_id = uuid.uuid4()

        service.create_chain(conversation_id)

        # Verify ChatOpenAI was called with correct parameters
        mock_chat_openai.assert_called_once_with(
            model="gpt-3.5-turbo", temperature=0.5, streaming=True, api_key="test-key"
        )

    @pytest.mark.asyncio
    @patch("src.services.conversation_chain_service.ConversationChain")
    @patch("src.services.conversation_chain_service.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_stream_response(self, mock_history, mock_conversation_chain):
        """Test stream_response yields tokens from chain."""
        from langchain.schema import BaseChatMessageHistory

        mock_history_instance = MagicMock(spec=BaseChatMessageHistory)
        mock_history.return_value = mock_history_instance

        # Mock the chain's astream method
        async def mock_astream(inputs):
            for chunk in [{"response": "Hello"}, {"response": " world"}, {"response": "!"}]:
                yield chunk

        mock_chain_instance = MagicMock()
        mock_chain_instance.astream = mock_astream
        mock_conversation_chain.return_value = mock_chain_instance

        service = ConversationChainService()
        conversation_id = uuid.uuid4()

        # Collect streamed tokens
        tokens = []
        async for token in service.stream_response(conversation_id, "Hi there"):
            tokens.append(token)

        # Verify tokens were yielded
        assert tokens == ["Hello", " world", "!"]

    @patch("src.services.conversation_chain_service.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_conversation_history(self, mock_history):
        """Test get_conversation_history returns formatted messages."""
        from langchain.schema import AIMessage, HumanMessage

        # Mock message history
        mock_history_instance = MagicMock()
        mock_history_instance.messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
            AIMessage(content="I'm doing well, thank you!"),
        ]
        mock_history.return_value = mock_history_instance

        service = ConversationChainService()
        conversation_id = uuid.uuid4()

        history = service.get_conversation_history(conversation_id)

        # Verify history format
        assert len(history) == 4
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}
        assert history[2] == {"role": "user", "content": "How are you?"}
        assert history[3] == {"role": "assistant", "content": "I'm doing well, thank you!"}

    @patch("src.services.conversation_chain_service.PostgresChatMessageHistory")
    @patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql://test:test@localhost/test", "OPENAI_API_KEY": "test-key"},
    )
    def test_get_conversation_history_uses_env_database_url(self, mock_history):
        """Test get_conversation_history uses DATABASE_URL from environment."""
        mock_history_instance = MagicMock()
        mock_history_instance.messages = []
        mock_history.return_value = mock_history_instance

        service = ConversationChainService()
        conversation_id = uuid.uuid4()

        service.get_conversation_history(conversation_id)

        # Verify called with env DATABASE_URL
        mock_history.assert_called_once_with(
            connection_string="postgresql://test:test@localhost/test",
            session_id=str(conversation_id),
        )
