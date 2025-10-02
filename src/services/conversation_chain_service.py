"""Conversation chain service for streaming chat with memory.

Provides LangChain ConversationChain with PostgreSQL memory and streaming support.
"""

import os
from typing import AsyncIterator, Optional
from uuid import UUID

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_openai import ChatOpenAI


class ConversationChainService:
    """Service for managing conversation chains with streaming and memory.

    Integrates ChatOpenAI with PostgresChatMessageHistory for persistent,
    streaming conversations.
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

    def create_chain(
        self, conversation_id: UUID, connection_string: Optional[str] = None
    ) -> ConversationChain:
        """Create conversation chain with memory for given conversation.

        Args:
            conversation_id: Conversation UUID for session tracking
            connection_string: Database URL (defaults to DATABASE_URL env var)

        Returns:
            ConversationChain instance with memory and streaming enabled
        """
        # Get database connection string
        if connection_string is None:
            connection_string = os.getenv("DATABASE_URL", "")

        # Create PostgreSQL message history
        chat_history = PostgresChatMessageHistory(
            connection_string=connection_string, session_id=str(conversation_id)
        )

        # Wrap in LangChain memory with message limit
        memory = ConversationBufferMemory(
            chat_memory=chat_history,
            return_messages=True,
            memory_key="history",
            ai_prefix="AI",
            human_prefix="Human",
        )

        # Create streaming-enabled LLM
        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            streaming=True,
            api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore[arg-type]
        )

        # Create conversation chain
        chain = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=False,  # Set to True for debugging
        )

        return chain

    async def stream_response(
        self,
        conversation_id: UUID,
        user_message: str,
        connection_string: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream conversation response token by token.

        Args:
            conversation_id: Conversation UUID
            user_message: User's input message
            connection_string: Database URL (optional)

        Yields:
            Individual tokens from the LLM response
        """
        chain = self.create_chain(conversation_id, connection_string)

        # Stream response using LangChain's astream
        async for chunk in chain.astream({"input": user_message}):
            # Extract text from response
            if isinstance(chunk, dict):
                if "response" in chunk:
                    content = chunk["response"]
                    if isinstance(content, str):
                        yield content
                elif "output" in chunk:
                    content = chunk["output"]
                    if isinstance(content, str):
                        yield content
            elif isinstance(chunk, (AIMessage, HumanMessage)):
                if isinstance(chunk.content, str):
                    yield chunk.content
            elif isinstance(chunk, str):
                yield chunk

    def get_conversation_history(
        self, conversation_id: UUID, connection_string: Optional[str] = None
    ) -> list[dict[str, str]]:
        """Get conversation history for given conversation.

        Args:
            conversation_id: Conversation UUID
            connection_string: Database URL (optional)

        Returns:
            List of messages as dicts with 'role' and 'content'
        """
        if connection_string is None:
            connection_string = os.getenv("DATABASE_URL", "")

        chat_history = PostgresChatMessageHistory(
            connection_string=connection_string, session_id=str(conversation_id)
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
