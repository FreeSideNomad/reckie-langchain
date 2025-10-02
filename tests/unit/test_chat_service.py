"""Unit tests for ChatService."""

import os
import uuid
from unittest.mock import MagicMock, patch

from src.services.chat_service import ChatService


class TestChatService:
    """Test suite for ChatService."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_chat_service_initialization_default(self):
        """Test ChatService initializes with default parameters."""
        service = ChatService()

        assert service.chat_model.model_name == "gpt-4-turbo"
        assert service.chat_model.temperature == 0.7
        assert service.chat_model.streaming is True

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_chat_service_initialization_custom(self):
        """Test ChatService initializes with custom parameters."""
        service = ChatService(model="gpt-3.5-turbo", temperature=0.5, streaming=False)

        assert service.chat_model.model_name == "gpt-3.5-turbo"
        assert service.chat_model.temperature == 0.5
        assert service.chat_model.streaming is False

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_chat_service_uses_env_api_key(self):
        """Test ChatService uses OPENAI_API_KEY from environment."""
        service = ChatService()

        # API key is stored as SecretStr, need to get_secret_value()
        assert service.chat_model.openai_api_key.get_secret_value() == "test-key"

    @patch("src.services.chat_service.PostgresChatMessageHistory")
    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "OPENAI_API_KEY": "test-key",
        },
    )
    def test_get_conversation_memory_default_connection(self, mock_history):
        """Test get_conversation_memory uses DATABASE_URL from environment."""
        service = ChatService()
        conversation_id = uuid.uuid4()

        service.get_conversation_memory(conversation_id)

        mock_history.assert_called_once_with(
            connection_string="postgresql://test:test@localhost/test",
            session_id=str(conversation_id),
        )

    @patch("src.services.chat_service.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_conversation_memory_custom_connection(self, mock_history):
        """Test get_conversation_memory with custom connection string."""
        service = ChatService()
        conversation_id = uuid.uuid4()
        custom_conn = "postgresql://custom:custom@localhost/custom"

        service.get_conversation_memory(conversation_id, custom_conn)

        mock_history.assert_called_once_with(
            connection_string=custom_conn, session_id=str(conversation_id)
        )

    @patch("src.services.chat_service.PostgresChatMessageHistory")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_conversation_memory_returns_history_instance(self, mock_history):
        """Test get_conversation_memory returns PostgresChatMessageHistory."""
        service = ChatService()
        conversation_id = uuid.uuid4()
        mock_instance = MagicMock()
        mock_history.return_value = mock_instance

        result = service.get_conversation_memory(conversation_id)

        assert result == mock_instance
