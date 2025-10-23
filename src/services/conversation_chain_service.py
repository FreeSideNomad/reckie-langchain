"""Conversation chain service for streaming chat with memory.

Provides modern LangChain RunnableWithMessageHistory with PostgreSQL memory and streaming support.
Uses custom ConversationsChatMessageHistory to integrate with conversations table.
"""

import os
from typing import Any, AsyncIterator, Optional, cast
from uuid import UUID

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.schema import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.services.custom_chat_history import ConversationsChatMessageHistory


class ConversationChainService:
    """Service for managing conversation chains with streaming and memory.

    Integrates ChatOpenAI with custom ConversationsChatMessageHistory for persistent,
    streaming conversations using modern RunnableWithMessageHistory.
    """

    def __init__(
        self,
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        max_context_messages: int = 10,
    ):
        """Initialize conversation chain service.

        Args:
            model: OpenAI model name (default: gpt-4-turbo)
            temperature: Sampling temperature 0-1 (default: 0.7)
            max_context_messages: Max messages in context window (default: 10)
        """
        self.model = model
        self.temperature = temperature
        self.max_context_messages = max_context_messages
        self._connection_string: Optional[str] = None
        self._session_configs: dict[str, tuple[UUID, UUID, UUID]] = {}

    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Get chat message history for a session.

        Args:
            session_id: Session identifier (conversation_id as string)

        Returns:
            BaseChatMessageHistory instance for this session
        """
        # Retrieve stored configuration for this session
        if session_id not in self._session_configs:
            raise ValueError(f"No configuration found for session {session_id}")

        conversation_id, user_id, document_id = self._session_configs[session_id]
        connection_string: str = self._connection_string or os.getenv("DATABASE_URL") or ""

        return ConversationsChatMessageHistory(
            conversation_id=conversation_id,
            user_id=user_id,
            document_id=document_id,
            connection_string=connection_string
        )

    def get_chat_history(self, conversation_id: UUID) -> BaseChatMessageHistory:
        """Get the chat message history for a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            BaseChatMessageHistory instance for direct message manipulation
        """
        session_id = str(conversation_id)
        return self._get_session_history(session_id)

    def create_chain(
        self,
        conversation_id: UUID,
        user_id: UUID,
        document_id: UUID,
        connection_string: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> RunnableWithMessageHistory:
        """Create conversation chain with memory for given conversation.

        Args:
            conversation_id: Conversation UUID for session tracking
            user_id: User UUID
            document_id: Document UUID being edited
            connection_string: Database URL (defaults to DATABASE_URL env var)
            system_prompt: Optional system prompt to use instead of default

        Returns:
            RunnableWithMessageHistory instance with memory and streaming enabled
        """
        # Store connection string and session configuration
        self._connection_string = connection_string
        session_id = str(conversation_id)
        self._session_configs[session_id] = (conversation_id, user_id, document_id)

        # Create streaming-enabled LLM
        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            streaming=True,
            api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore[arg-type]
        )

        # Use provided system prompt or default
        sys_prompt = system_prompt or "You are a helpful AI assistant."

        # Escape curly braces in system prompt to avoid template variable conflicts
        # LangChain requires {{ and }} for literal braces in prompt templates
        escaped_prompt = sys_prompt.replace("{", "{{").replace("}", "}}")

        # Create prompt template with message history placeholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", escaped_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])

        # Create base runnable (prompt | llm)
        runnable = prompt | llm

        # Wrap with message history
        chain = RunnableWithMessageHistory(
            runnable=runnable,
            get_session_history=self._get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        return chain

    async def stream_response(
        self,
        conversation_id: UUID,
        user_id: UUID,
        document_id: UUID,
        user_message: str,
        connection_string: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream conversation response token by token.

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            document_id: Document UUID
            user_message: User's input message
            connection_string: Database URL (optional)

        Yields:
            Individual tokens from the LLM response
        """
        chain = self.create_chain(conversation_id, user_id, document_id, connection_string)
        session_id = str(conversation_id)

        # Stream response using RunnableWithMessageHistory's astream
        # Pass session_id in config for history tracking
        config: dict[str, Any] = {"configurable": {"session_id": session_id}}

        async for chunk in chain.astream({"input": user_message}, config=config):  # type: ignore[arg-type]
            # Extract text from response chunks
            # RunnableWithMessageHistory returns AIMessage chunks
            if isinstance(chunk, (AIMessage, HumanMessage)):
                if isinstance(chunk.content, str):
                    yield chunk.content
            elif isinstance(chunk, str):
                yield chunk
            # Handle dict responses (shouldn't happen with new approach, but keep for safety)
            elif isinstance(chunk, dict):
                if "content" in chunk and isinstance(chunk["content"], str):
                    yield chunk["content"]

    def get_conversation_history(
        self,
        conversation_id: UUID,
        user_id: UUID,
        document_id: UUID,
        connection_string: Optional[str] = None
    ) -> list[dict[str, str]]:
        """Get conversation history for given conversation.

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            document_id: Document UUID
            connection_string: Database URL (optional)

        Returns:
            List of messages as dicts with 'role' and 'content'
        """
        if connection_string is None:
            connection_string = os.getenv("DATABASE_URL", "")

        chat_history = ConversationsChatMessageHistory(
            conversation_id=conversation_id,
            user_id=user_id,
            document_id=document_id,
            connection_string=connection_string
        )

        messages = chat_history.messages

        # Convert to simple dict format
        history: list[dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                if isinstance(msg.content, str):
                    history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                if isinstance(msg.content, str):
                    history.append({"role": "assistant", "content": msg.content})

        return history
