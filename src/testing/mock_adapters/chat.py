"""Mock chat model adapter implementing LangChain BaseChatModel interface."""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class MockChatModel(BaseChatModel):
    """Mock LangChain chat model using YAML fixtures.

    This adapter implements the LangChain BaseChatModel interface and returns
    deterministic responses from YAML fixture files. It's designed for:
    - Fast testing without API calls (<1ms per call)
    - Deterministic, reproducible test results
    - Learning how to build real provider adapters

    Example:
        >>> chat = MockChatModel()
        >>> response = chat.invoke("Hello")
        >>> print(response.content)
    """

    fixture_path: str = ""
    fixtures: Dict[str, str] = {}
    model_name: str = "mock-chat-model"

    def __init__(
        self, fixture_path: Optional[str] = None, model_name: str = "mock-chat-model", **kwargs: Any
    ):
        """Initialize mock chat model.

        Args:
            fixture_path: Path to YAML fixture file. If None, uses default.
            model_name: Model identifier
            **kwargs: Additional arguments passed to BaseChatModel
        """
        # Call parent __init__ first (BaseChatModel expects no custom kwargs)
        super().__init__(**kwargs)

        # Set instance attributes after parent initialization
        if fixture_path is None:
            # Default to tests/fixtures/mock_adapters/chat.yaml
            fixture_path = os.path.join(
                Path(__file__).parent.parent.parent.parent,
                "tests",
                "fixtures",
                "mock_adapters",
                "chat.yaml",
            )

        self.fixture_path = fixture_path
        self.model_name = model_name
        self.fixtures = self._load_fixtures()

    def _load_fixtures(self) -> Dict[str, str]:
        """Load chat completion fixtures from YAML file.

        Returns:
            Dictionary mapping prompt keys/hashes to responses
        """
        if not os.path.exists(self.fixture_path):
            # Return empty dict if fixture file doesn't exist yet
            return {}

        with open(self.fixture_path, "r") as f:
            data = yaml.safe_load(f)

        if not data or "completions" not in data:
            return {}

        # Build lookup dict: key -> response, prompt -> response
        fixtures = {}
        for item in data["completions"]:
            key = item.get("key")
            prompt = item.get("prompt")
            response = item.get("response")

            if key:
                fixtures[key] = response
            if prompt:
                # Also allow lookup by exact prompt match
                fixtures[prompt] = response

        return fixtures

    def _get_response(self, messages: List[BaseMessage]) -> str:
        """Get response for messages.

        Args:
            messages: List of messages in conversation

        Returns:
            Response text

        Raises:
            ValueError: If no fixture found for prompt
        """
        # Convert messages to a single prompt string
        prompt = self._messages_to_prompt(messages)

        # Try exact prompt match first
        if prompt in self.fixtures:
            return self.fixtures[prompt]

        # Try hashed lookup (first 8 chars of hash as key)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        if prompt_hash in self.fixtures:
            return self.fixtures[prompt_hash]

        # Fallback: generate deterministic response from hash
        # This allows tests to work even without fixtures
        response_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"Mock response for prompt (hash: {response_hash[:8]})"

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert message list to single prompt string.

        Args:
            messages: List of messages

        Returns:
            Combined prompt string
        """
        if not messages:
            return ""

        # Simple concatenation for now
        # Real adapters would format this properly (system/user/assistant roles)
        parts: List[str] = []
        for msg in messages:
            if hasattr(msg, "content"):
                # content can be str or list, convert to str
                content = msg.content
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    # For multimodal content, just join text parts
                    parts.append(str(content))
        return " ".join(parts)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat completion.

        Args:
            messages: List of messages in conversation
            stop: Stop sequences (ignored for mock)
            run_manager: Callback manager (ignored for mock)
            **kwargs: Additional arguments (ignored for mock)

        Returns:
            ChatResult with generated response
        """
        response_text = self._get_response(messages)
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        """Return type of language model."""
        return "mock-chat-model"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters."""
        return {
            "model_name": self.model_name,
            "fixture_path": self.fixture_path,
        }

    # Optional: Implement streaming (return single chunk)
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        """Stream chat completion (mock: returns single chunk).

        Args:
            messages: List of messages
            stop: Stop sequences (ignored)
            run_manager: Callback manager (ignored)
            **kwargs: Additional arguments (ignored)

        Yields:
            ChatGenerationChunk with complete response
        """
        # For mock, just return the complete response as a single chunk
        result = self._generate(messages, stop, run_manager, **kwargs)
        for generation in result.generations:
            yield generation
