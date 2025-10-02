"""Chat service for OpenAI integration with conversation memory.

Provides LangChain-based chat functionality with PostgreSQL conversation history.
Model-agnostic design allows switching between OpenAI, Anthropic, Google, etc.
"""

import os
from typing import Optional
from uuid import UUID

from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_openai import ChatOpenAI


class ChatService:
    """Service for managing AI chat with conversation memory.

    Uses LangChain abstractions for model-agnostic implementation.
    Currently configured for OpenAI, but can switch to Anthropic, Google, etc.
    """

    def __init__(
        self, model: str = "gpt-4-turbo", temperature: float = 0.7, streaming: bool = True
    ):
        """Initialize chat service with OpenAI model.

        Args:
            model: Model name (default: gpt-4-turbo)
            temperature: Sampling temperature 0-1 (default: 0.7)
            streaming: Enable streaming responses (default: True)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        self.chat_model = ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=streaming,
            api_key=api_key,  # type: ignore[arg-type]
        )

    def get_conversation_memory(
        self, conversation_id: UUID, connection_string: Optional[str] = None
    ) -> PostgresChatMessageHistory:
        """Get conversation memory from PostgreSQL.

        Args:
            conversation_id: Conversation UUID (used as session_id)
            connection_string: Database URL (defaults to DATABASE_URL env var)

        Returns:
            PostgresChatMessageHistory instance for this conversation
        """
        if connection_string is None:
            connection_string = os.getenv("DATABASE_URL", "")

        return PostgresChatMessageHistory(
            connection_string=connection_string, session_id=str(conversation_id)
        )
