"""Recording wrapper for LangChain adapters with fixture capture.

This module provides a transparent recording layer that wraps real LangChain
adapters and automatically saves API responses to YAML fixtures. It's useful for:
- Initial fixture generation
- Production logging and debugging
- Fixture updates when API changes
- Cost monitoring

Usage:
    # Enable recording mode
    export RECORD_FIXTURES=true
    export RECORD_FIXTURES_PATH=tests/fixtures/mock_adapters

    # Use recording wrapper in your code
    embeddings = RecordingEmbeddings(OpenAIEmbeddings())
    vectors = embeddings.embed_documents(["text1", "text2"])
    # → Makes real API call AND saves response to embeddings.yaml
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


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
        enabled: bool = None,
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

    def _save_fixture(self, text: str, vector: List[float], metadata: Dict[str, Any] = None):
        """Save a new fixture to the YAML file.

        Args:
            text: Input text
            vector: Embedding vector
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

        # Add new fixture
        fixture_item = {
            "key": text_hash,
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

        print(f"📝 Recorded embedding: {text[:50]}... → {self.fixture_path}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents and record responses.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Call real API
        vectors = self.wrapped_embeddings.embed_documents(texts)

        # Record each response
        for text, vector in zip(texts, vectors):
            self._save_fixture(text, vector)

        return vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed query and record response.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        # Call real API
        vector = self.wrapped_embeddings.embed_query(text)

        # Record response
        self._save_fixture(text, vector)

        return vector

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async embed documents."""
        vectors = await self.wrapped_embeddings.aembed_documents(texts)
        for text, vector in zip(texts, vectors):
            self._save_fixture(text, vector)
        return vectors

    async def aembed_query(self, text: str) -> List[float]:
        """Async embed query."""
        vector = await self.wrapped_embeddings.aembed_query(text)
        self._save_fixture(text, vector)
        return vector


class RecordingChatModel(BaseChatModel):
    """Wrapper that records chat model responses to YAML fixtures.

    This wrapper delegates to a real chat model and captures responses
    for later replay. It's transparent - code using it doesn't need to change.

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> real_chat = ChatOpenAI()
        >>> recording_chat = RecordingChatModel(real_chat)
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
        enabled: bool = None,
        **kwargs: Any,
    ):
        """Initialize recording wrapper.

        Args:
            wrapped_chat: Real chat model to wrap
            fixture_path: Path to YAML file for saving. If None, uses env var or default.
            enabled: Whether recording is enabled. If None, checks RECORD_FIXTURES env var.
            **kwargs: Additional arguments
        """
        # Determine if recording is enabled
        if enabled is None:
            enabled = os.getenv("RECORD_FIXTURES", "false").lower() == "true"

        # Determine fixture path
        if fixture_path is None:
            fixture_dir = os.getenv("RECORD_FIXTURES_PATH", "tests/fixtures/mock_adapters")
            fixture_path = os.path.join(fixture_dir, "chat.yaml")

        # Initialize parent
        super().__init__(
            wrapped_chat=wrapped_chat,
            fixture_path=fixture_path,
            enabled=enabled,
            fixtures={},
            **kwargs,
        )

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

    def _save_fixture(self, prompt: str, response: str, metadata: Dict[str, Any] = None):
        """Save a new fixture to the YAML file."""
        if not self.enabled:
            return

        # Generate key from prompt hash
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

        # Check if already recorded
        for item in self.fixtures.get("completions", []):
            if item.get("prompt") == prompt or item.get("key") == prompt_hash:
                # Already recorded, skip
                return

        # Add new fixture
        fixture_item = {
            "key": prompt_hash,
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

        print(f"💬 Recorded chat: {prompt[:50]}... → {self.fixture_path}")

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert messages to prompt string."""
        return " ".join([msg.content for msg in messages if hasattr(msg, "content")])

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat completion and record response."""
        # Call real API
        result = self.wrapped_chat._generate(messages, stop, run_manager, **kwargs)

        # Record response
        prompt = self._messages_to_prompt(messages)
        response = result.generations[0].message.content if result.generations else ""
        self._save_fixture(prompt, response)

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
