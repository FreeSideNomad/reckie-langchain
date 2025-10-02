"""Enhanced conversation chain service with token tracking and error handling.

Provides LangChain ConversationChain with:
- Token usage tracking (records model + tokens for analytics)
- Retry logic with exponential backoff
- Circuit breaker pattern
- Error handling with correlation IDs
- Rate limit and timeout handling
"""

import logging
import os
import time
import uuid
from typing import AsyncIterator, Optional
from uuid import UUID

from httpx import TimeoutException
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage
from langchain_community.callbacks.manager import get_openai_callback
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_openai import ChatOpenAI
from openai import APIError, RateLimitError
from pybreaker import CircuitBreaker
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.database.models.conversation_metric import ConversationMetric

logger = logging.getLogger(__name__)

# Circuit breaker for OpenAI API (fails after 5 consecutive errors, recovers after 60s)
openai_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)


class ConversationChainServiceWithTracking:
    """Service for managing conversation chains with tracking and resilience.

    Features:
    - Token usage tracking per conversation turn
    - Retry logic with exponential backoff (3 attempts)
    - Circuit breaker (after 5 consecutive failures)
    - Error logging with correlation IDs
    - Rate limit handling (429 errors)
    - API timeout configuration (30s default)
    """

    def __init__(
        self,
        db_session: Session,
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        max_context_messages: int = 10,
        timeout: int = 30,
    ):
        """Initialize conversation chain service with tracking.

        Args:
            db_session: SQLAlchemy session for metric storage
            model: OpenAI model name (default: gpt-4-turbo)
            temperature: Sampling temperature 0-1 (default: 0.7)
            max_context_messages: Max messages in context window (default: 10)
            timeout: API request timeout in seconds (default: 30)
        """
        self.db_session = db_session
        self.model = model
        self.temperature = temperature
        self.max_context_messages = max_context_messages
        self.timeout = timeout

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
        if connection_string is None:
            connection_string = os.getenv("DATABASE_URL", "")

        chat_history = PostgresChatMessageHistory(
            connection_string=connection_string, session_id=str(conversation_id)
        )

        memory = ConversationBufferMemory(
            chat_memory=chat_history,
            return_messages=True,
            memory_key="history",
            ai_prefix="AI",
            human_prefix="Human",
        )

        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            streaming=True,
            timeout=self.timeout,
            api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore[arg-type]
        )

        chain = ConversationChain(llm=llm, memory=memory, verbose=False)

        return chain

    def _record_metric(
        self,
        conversation_id: UUID,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        duration_ms: int,
        correlation_id: UUID,
        error_occurred: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Record token usage metric to database.

        Records facts (model + tokens) without cost calculation.
        Cost analytics performed separately using pricing configuration.

        Args:
            conversation_id: Conversation UUID
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            total_tokens: Total tokens
            duration_ms: API call duration in milliseconds
            correlation_id: Correlation ID for tracing
            error_occurred: Whether an error occurred
            error_message: Error message if applicable
        """
        metric = ConversationMetric(
            conversation_id=conversation_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=self.model,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            error_occurred=error_occurred,
            error_message=error_message,
        )

        self.db_session.add(metric)
        self.db_session.commit()

        logger.info(
            f"Token metric recorded: {total_tokens} tokens, "
            f"model={self.model}, correlation_id={correlation_id}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError, TimeoutException)),
    )
    @openai_breaker
    async def _invoke_with_retry(
        self, chain: ConversationChain, message: str, correlation_id: UUID
    ) -> dict:
        """Invoke chain with retry logic and circuit breaker.

        Args:
            chain: ConversationChain instance
            message: User message
            correlation_id: Correlation ID for tracing

        Returns:
            Response dict from chain

        Raises:
            RateLimitError: After 3 retry attempts on rate limit
            APIError: After 3 retry attempts on API error
            TimeoutException: After 3 retry attempts on timeout
        """
        try:
            response: dict = await chain.ainvoke({"input": message})
            return response
        except RateLimitError:
            logger.warning(f"Rate limit hit (correlation_id={correlation_id}), retrying...")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error (correlation_id={correlation_id}): {e}")
            raise
        except TimeoutException:
            logger.error(f"OpenAI request timed out (correlation_id={correlation_id})")
            raise

    async def stream_response(
        self,
        conversation_id: UUID,
        user_message: str,
        connection_string: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream conversation response with token tracking.

        Args:
            conversation_id: Conversation UUID
            user_message: User's input message
            connection_string: Database URL (optional)

        Yields:
            Individual tokens from the LLM response

        Tracks token usage and records metrics to database.
        """
        correlation_id = uuid.uuid4()
        chain = self.create_chain(conversation_id, connection_string)

        start_time = time.time()

        try:
            # Use callback to track token usage
            with get_openai_callback() as cb:
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

                # Record metrics after streaming completes
                duration_ms = int((time.time() - start_time) * 1000)
                self._record_metric(
                    conversation_id=conversation_id,
                    prompt_tokens=cb.prompt_tokens,
                    completion_tokens=cb.completion_tokens,
                    total_tokens=cb.total_tokens,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id,
                    error_occurred=False,
                )

        except (RateLimitError, APIError, TimeoutException) as e:
            error_message = str(e)
            duration_ms = int((time.time() - start_time) * 1000)

            # Record error metric
            self._record_metric(
                conversation_id=conversation_id,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                error_occurred=True,
                error_message=error_message,
            )

            logger.error(f"Error in stream_response (correlation_id={correlation_id}): {e}")
            raise

    def invoke_with_tracking(
        self,
        conversation_id: UUID,
        user_message: str,
        connection_string: Optional[str] = None,
    ) -> str:
        """Invoke conversation chain with token tracking (non-streaming).

        Args:
            conversation_id: Conversation UUID
            user_message: User's input message
            connection_string: Database URL (optional)

        Returns:
            Complete response string

        Tracks token usage and records metrics to database.
        """
        correlation_id = uuid.uuid4()
        chain = self.create_chain(conversation_id, connection_string)

        start_time = time.time()

        try:
            with get_openai_callback() as cb:
                response = chain.invoke({"input": user_message})

                duration_ms = int((time.time() - start_time) * 1000)
                self._record_metric(
                    conversation_id=conversation_id,
                    prompt_tokens=cb.prompt_tokens,
                    completion_tokens=cb.completion_tokens,
                    total_tokens=cb.total_tokens,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id,
                    error_occurred=False,
                )

                result: str = response.get("response", "")
                return result

        except (RateLimitError, APIError, TimeoutException) as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self._record_metric(
                conversation_id=conversation_id,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                error_occurred=True,
                error_message=str(e),
            )

            logger.error(f"Error in invoke_with_tracking (correlation_id={correlation_id}): {e}")
            raise

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

        history: list[dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                if isinstance(msg.content, str):
                    history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                if isinstance(msg.content, str):
                    history.append({"role": "assistant", "content": msg.content})

        return history
