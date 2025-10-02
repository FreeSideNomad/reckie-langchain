"""Integration tests for chat WebSocket endpoint."""

import json
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestChatWebSocket:
    """Test suite for chat WebSocket endpoint."""

    @patch("src.api.v1.routes.chat.ConversationChainService")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_websocket_connection_accepted(self, mock_service_class, client):
        """Test WebSocket connection is accepted."""
        conversation_id = str(uuid.uuid4())

        with client.websocket_connect(f"/api/v1/chat/ws/{conversation_id}") as websocket:
            # Connection should be established
            assert websocket is not None

    @patch("src.api.v1.routes.chat.ConversationChainService")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_websocket_invalid_conversation_id(self, mock_service_class, client):
        """Test WebSocket rejects invalid conversation ID."""
        # Mock service to avoid actual LLM calls
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        with client.websocket_connect("/api/v1/chat/ws/invalid-uuid") as websocket:
            # Should receive error message
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid conversation ID" in data["message"]

    @patch("src.api.v1.routes.chat.ConversationChainService")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_websocket_streaming_response(self, mock_service_class, client):
        """Test WebSocket streams response tokens."""
        # Mock streaming service
        mock_service = MagicMock()

        async def mock_stream_response(conv_id, message):
            """Mock streaming response."""
            for token in ["Hello", " world", "!"]:
                yield token

        mock_service.stream_response = mock_stream_response
        mock_service_class.return_value = mock_service

        conversation_id = str(uuid.uuid4())

        with client.websocket_connect(f"/api/v1/chat/ws/{conversation_id}") as websocket:
            # Send message
            websocket.send_text(json.dumps({"message": "Hi there"}))

            # Collect all responses
            responses = []
            while True:
                data = websocket.receive_json()
                responses.append(data)
                if data.get("type") == "done":
                    break

            # Verify streaming protocol
            assert responses[0]["type"] == "start"
            assert responses[1]["type"] == "token"
            assert responses[1]["content"] == "Hello"
            assert responses[2]["type"] == "token"
            assert responses[2]["content"] == " world"
            assert responses[3]["type"] == "token"
            assert responses[3]["content"] == "!"
            assert responses[4]["type"] == "done"

    @patch("src.api.v1.routes.chat.ConversationChainService")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_websocket_missing_message_field(self, mock_service_class, client):
        """Test WebSocket handles missing message field."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        conversation_id = str(uuid.uuid4())

        with client.websocket_connect(f"/api/v1/chat/ws/{conversation_id}") as websocket:
            # Send message without message field
            websocket.send_text(json.dumps({"wrong_field": "value"}))

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Message field is required" in data["message"]

    @patch("src.api.v1.routes.chat.ConversationChainService")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_websocket_invalid_json(self, mock_service_class, client):
        """Test WebSocket handles invalid JSON."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        conversation_id = str(uuid.uuid4())

        with client.websocket_connect(f"/api/v1/chat/ws/{conversation_id}") as websocket:
            # Send invalid JSON
            websocket.send_text("not valid json")

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["message"]

    @patch("src.api.v1.routes.chat.ConversationChainService")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_chat_history_endpoint(self, mock_service_class, client):
        """Test GET /history/{conversation_id} endpoint."""
        # Mock service
        mock_service = MagicMock()
        mock_service.get_conversation_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_service_class.return_value = mock_service

        conversation_id = str(uuid.uuid4())

        # Get history
        response = client.get(f"/api/v1/chat/history/{conversation_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    def test_get_chat_history_invalid_uuid(self, client):
        """Test GET /history with invalid UUID."""
        response = client.get("/api/v1/chat/history/invalid-uuid")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Invalid conversation ID" in data["error"]
