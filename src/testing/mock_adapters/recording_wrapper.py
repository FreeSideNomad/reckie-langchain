"""Recording wrapper for LangChain adapters with fixture capture.

This module provides a transparent recording layer that wraps real LangChain
adapters and automatically saves API responses to YAML fixtures. It's useful for:
- Initial fixture generation
- Production logging and debugging
- Fixture updates when API changes
- Cost monitoring

Enhanced with dual-layer logging:
- Layer 1: LangChain abstraction (via callback)
- Layer 2: YAML fixtures (this module)
- Layer 3: Raw OpenAI API (via httpx transport)

All three layers share a correlation_id for complete traceability.

Usage:
    # Enable recording mode
    export RECORD_FIXTURES=true
    export RECORD_FIXTURES_PATH=tests/fixtures/mock_adapters

    # Use recording wrapper in your code
    embeddings = RecordingEmbeddings(OpenAIEmbeddings())
    vectors = embeddings.embed_documents(["text1", "text2"])
    # → Makes real API call AND saves response to embeddings.yaml
    # → Logs LangChain call to langchain_calls/embeddings/<id>.json
    # → Logs raw HTTP to raw_api/embeddings/<id>.json
"""

import hashlib
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from src.testing.mock_adapters.httpx_logging_transport import get_logging_transport
from src.testing.mock_adapters.langchain_logging_callback import get_langchain_logger


class RecordingEmbeddings(Embeddings):
    """Wrapper that records embeddings API responses to YAML fixtures.

    This wrapper delegates to a real embeddings provider and captures responses
    for later replay. It's transparent - code using it doesn't need to change.

    Example:
        >>> from langchain_openai import OpenAIEmbeddings
        >>> real_embeddings = OpenAIEmbeddings()
        >>> recording_embeddings = RecordingEmbeddings(real_embeddings)
        >>> vectors = recording_embeddings.embed_documents(["test"])
        >>> # Response saved to YAML automatically
    """

    def __init__(
        self,
        wrapped_embeddings: Embeddings,
        fixture_path: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        """Initialize recording wrapper.

        Args:
            wrapped_embeddings: Real embeddings provider to wrap
            fixture_path: Path to YAML file for saving. If None, uses env var or default.
            enabled: Whether recording is enabled. If None, checks RECORD_FIXTURES env var.
        """
        self.wrapped_embeddings = wrapped_embeddings

        # Determine if recording is enabled
        if enabled is None:
            enabled = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
        self.enabled = enabled

        # Determine fixture path
        if fixture_path is None:
            fixture_dir = os.getenv("RECORD_FIXTURES_PATH", "tests/fixtures/mock_adapters")
            fixture_path = os.path.join(fixture_dir, "embeddings.yaml")
        self.fixture_path = fixture_path

        # Load existing fixtures
        self.fixtures = self._load_existing_fixtures()

    def _load_existing_fixtures(self) -> Dict[str, Any]:
        """Load existing fixtures from file.

        Returns:
            Dictionary with existing fixture data
        """
        if not os.path.exists(self.fixture_path):
            return {"embeddings": [], "metadata": {"recorded_at": None, "total_count": 0}}

        with open(self.fixture_path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return {"embeddings": [], "metadata": {"recorded_at": None, "total_count": 0}}

        return data

    def _save_fixture(
        self,
        text: str,
        vector: List[float],
        correlation_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save a new fixture to the YAML file with correlation ID.

        Args:
            text: Input text
            vector: Embedding vector
            correlation_id: Unique ID linking to LangChain and raw API logs
            metadata: Optional metadata (model, tokens, etc.)
        """
        if not self.enabled:
            return

        # Generate key from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]

        # Check if already recorded
        for item in self.fixtures.get("embeddings", []):
            if item.get("text") == text or item.get("key") == text_hash:
                # Already recorded, skip
                return

        # Add new fixture with correlation ID
        fixture_item = {
            "key": text_hash,
            "correlation_id": correlation_id,  # Links to Layer 1 and Layer 3
            "text": text,
            "vector": vector,
            "dimension": len(vector),
            "recorded_at": datetime.now().isoformat(),
        }

        if metadata:
            fixture_item.update(metadata)

        self.fixtures.setdefault("embeddings", []).append(fixture_item)
        self.fixtures.setdefault("metadata", {})
        self.fixtures["metadata"]["total_count"] = len(self.fixtures["embeddings"])
        self.fixtures["metadata"]["last_updated"] = datetime.now().isoformat()

        # Save to file
        os.makedirs(os.path.dirname(self.fixture_path), exist_ok=True)
        with open(self.fixture_path, "w") as f:
            yaml.dump(self.fixtures, f, default_flow_style=False, sort_keys=False)

        print(f"📝 [Layer 2] YAML fixture: {text[:50]}... → {self.fixture_path}")
        print(f"   🔗 Correlation: {correlation_id}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents and record responses with dual logging.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        vectors = []
        for text in texts:
            # Generate correlation ID for this embedding
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            correlation_id = f"emb_{text_hash}_{uuid4().hex[:8]}"

            # Set correlation ID in both loggers
            get_logging_transport().set_correlation_id(correlation_id)
            get_langchain_logger().set_correlation_id(correlation_id)

            # Time the call
            start_time = time.time()

            # Call real API (triggers Layer 3: raw HTTP log)
            vector = self.wrapped_embeddings.embed_query(text)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log to Layer 1 (LangChain abstraction)
            get_langchain_logger().log_embedding_call(
                correlation_id=correlation_id, text=text, vector=vector, duration_ms=duration_ms
            )

            # Record to Layer 2 (YAML fixture)
            self._save_fixture(text, vector, correlation_id)

            vectors.append(vector)

        return vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed query and record response with dual logging.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        # Generate correlation ID
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        correlation_id = f"emb_{text_hash}_{uuid4().hex[:8]}"

        # Set correlation ID in both loggers
        get_logging_transport().set_correlation_id(correlation_id)
        get_langchain_logger().set_correlation_id(correlation_id)

        # Time the call
        start_time = time.time()

        # Call real API (triggers Layer 3: raw HTTP log)
        vector = self.wrapped_embeddings.embed_query(text)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log to Layer 1 (LangChain abstraction)
        get_langchain_logger().log_embedding_call(
            correlation_id=correlation_id, text=text, vector=vector, duration_ms=duration_ms
        )

        # Record to Layer 2 (YAML fixture)
        self._save_fixture(text, vector, correlation_id)

        return vector

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async embed documents with dual logging."""
        vectors = []
        for text in texts:
            # Generate correlation ID
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            correlation_id = f"emb_{text_hash}_{uuid4().hex[:8]}"

            # Set correlation ID in both loggers
            get_logging_transport().set_correlation_id(correlation_id)
            get_langchain_logger().set_correlation_id(correlation_id)

            # Time the call
            start_time = time.time()

            # Call real API
            vector = await self.wrapped_embeddings.aembed_query(text)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log to Layer 1 (LangChain)
            get_langchain_logger().log_embedding_call(
                correlation_id=correlation_id, text=text, vector=vector, duration_ms=duration_ms
            )

            # Record to Layer 2 (YAML)
            self._save_fixture(text, vector, correlation_id)

            vectors.append(vector)

        return vectors

    async def aembed_query(self, text: str) -> List[float]:
        """Async embed query with dual logging."""
        # Generate correlation ID
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        correlation_id = f"emb_{text_hash}_{uuid4().hex[:8]}"

        # Set correlation ID in both loggers
        get_logging_transport().set_correlation_id(correlation_id)
        get_langchain_logger().set_correlation_id(correlation_id)

        # Time the call
        start_time = time.time()

        # Call real API
        vector = await self.wrapped_embeddings.aembed_query(text)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log to Layer 1 (LangChain)
        get_langchain_logger().log_embedding_call(
            correlation_id=correlation_id, text=text, vector=vector, duration_ms=duration_ms
        )

        # Record to Layer 2 (YAML)
        self._save_fixture(text, vector, correlation_id)

        return vector


class RecordingChatModel(BaseChatModel):
    """Wrapper that records chat model responses to YAML fixtures.

    This wrapper delegates to a real chat model and captures responses
    for later replay. It's transparent - code using it doesn't need to change.

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> real_chat = ChatOpenAI()
        >>> recording_chat = RecordingChatModel(wrapped_chat=real_chat)
        >>> response = recording_chat.invoke("Hello")
        >>> # Response saved to YAML automatically
    """

    wrapped_chat: BaseChatModel
    fixture_path: str = ""
    enabled: bool = False
    fixtures: Dict[str, Any] = {}

    def __init__(
        self,
        wrapped_chat: BaseChatModel,
        fixture_path: Optional[str] = None,
        enabled: Optional[bool] = None,
        **kwargs: Any,
    ):
        """Initialize recording wrapper.

        Args:
            wrapped_chat: Real chat model to wrap
            fixture_path: Path to YAML file for saving. If None, uses env var or default.
            enabled: Whether recording is enabled. If None, checks RECORD_FIXTURES env var.
            **kwargs: Additional arguments
        """
        # Initialize parent with wrapped_chat
        super().__init__(wrapped_chat=wrapped_chat, **kwargs)  # type: ignore[call-arg]

        # Determine if recording is enabled
        if enabled is None:
            enabled = os.getenv("RECORD_FIXTURES", "false").lower() == "true"
        self.enabled = enabled

        # Determine fixture path
        if fixture_path is None:
            fixture_dir = os.getenv("RECORD_FIXTURES_PATH", "tests/fixtures/mock_adapters")
            fixture_path = os.path.join(fixture_dir, "chat.yaml")
        self.fixture_path = fixture_path

        # Load existing fixtures
        self.fixtures = self._load_existing_fixtures()

    def _load_existing_fixtures(self) -> Dict[str, Any]:
        """Load existing fixtures from file."""
        if not os.path.exists(self.fixture_path):
            return {"completions": [], "metadata": {"recorded_at": None, "total_count": 0}}

        with open(self.fixture_path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return {"completions": [], "metadata": {"recorded_at": None, "total_count": 0}}

        return data

    def _save_fixture(
        self,
        prompt: str,
        response: str,
        correlation_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save a new fixture to the YAML file with correlation ID."""
        if not self.enabled:
            return

        # Generate key from prompt hash
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

        # Check if already recorded
        for item in self.fixtures.get("completions", []):
            if item.get("prompt") == prompt or item.get("key") == prompt_hash:
                # Already recorded, skip
                return

        # Add new fixture with correlation ID
        fixture_item = {
            "key": prompt_hash,
            "correlation_id": correlation_id,  # Links to Layer 1 and Layer 3
            "prompt": prompt,
            "response": response,
            "recorded_at": datetime.now().isoformat(),
        }

        if metadata:
            fixture_item.update(metadata)

        self.fixtures.setdefault("completions", []).append(fixture_item)
        self.fixtures.setdefault("metadata", {})
        self.fixtures["metadata"]["total_count"] = len(self.fixtures["completions"])
        self.fixtures["metadata"]["last_updated"] = datetime.now().isoformat()

        # Save to file
        os.makedirs(os.path.dirname(self.fixture_path), exist_ok=True)
        with open(self.fixture_path, "w") as f:
            yaml.dump(self.fixtures, f, default_flow_style=False, sort_keys=False)

        print(f"💬 [Layer 2] YAML fixture: {prompt[:50]}... → {self.fixture_path}")
        print(f"   🔗 Correlation: {correlation_id}")

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert messages to prompt string."""
        parts: List[str] = []
        for msg in messages:
            if hasattr(msg, "content"):
                # content can be str or list, convert to str
                content = msg.content
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    # For multimodal content, just convert to string
                    parts.append(str(content))
        return " ".join(parts)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat completion and record response with dual logging."""
        # Generate correlation ID
        prompt = self._messages_to_prompt(messages)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        correlation_id = f"chat_{prompt_hash}_{uuid4().hex[:8]}"

        # Set correlation ID in loggers
        get_logging_transport().set_correlation_id(correlation_id)
        get_langchain_logger().set_correlation_id(correlation_id)

        # Time the call
        start_time = time.time()

        # Call real API (triggers Layer 3: raw HTTP log)
        result = self.wrapped_chat._generate(messages, stop, run_manager, **kwargs)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Extract response
        if result.generations:
            content = result.generations[0].message.content
            # Convert content to string (can be str or list)
            response = content if isinstance(content, str) else str(content)
        else:
            response = ""

        # Log to Layer 1 (LangChain abstraction) - manually like embeddings
        get_langchain_logger().log_chat_call(
            correlation_id=correlation_id,
            prompt=prompt,
            response=response,
            messages=messages,
            result=result,
            duration_ms=duration_ms,
        )

        # Record to Layer 2 (YAML)
        self._save_fixture(prompt, response, correlation_id)

        return result

    @property
    def _llm_type(self) -> str:
        """Return type of language model."""
        return f"recording-{self.wrapped_chat._llm_type}"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters."""
        return {
            "wrapped_model": self.wrapped_chat._identifying_params,
            "fixture_path": self.fixture_path,
            "recording_enabled": self.enabled,
        }
