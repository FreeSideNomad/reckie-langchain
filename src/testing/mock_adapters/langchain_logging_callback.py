"""LangChain callback handler for logging API calls at abstraction layer.

This module captures Layer 1: LangChain's view of API interactions.
Logs how LangChain processes and transforms inputs/outputs.

Usage:
    from src.testing.mock_adapters.langchain_logging_callback import get_langchain_logger

    # Add to LangChain model
    chat = ChatOpenAI(callbacks=[get_langchain_logger()])
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class LangChainLoggingCallback(BaseCallbackHandler):
    """Callback handler that logs LangChain API calls.

    Captures LangChain's abstraction layer:
    - How LangChain formats prompts/messages
    - How LangChain processes responses
    - LangChain metadata (model params, invocation settings)
    - Token usage from LangChain's perspective
    """

    def __init__(self, log_dir: Optional[str] = None):
        """Initialize LangChain logging callback.

        Args:
            log_dir: Directory to write log files
        """
        super().__init__()

        if log_dir is None:
            log_dir = "tests/fixtures/mock_adapters/langchain_calls"

        self.log_dir = Path(log_dir)
        self.embeddings_dir = self.log_dir / "embeddings"
        self.chat_dir = self.log_dir / "chat"

        # Create directories
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.chat_dir.mkdir(parents=True, exist_ok=True)

        # Track request timing and correlation IDs
        self.request_start_times: Dict[str, float] = {}
        self._current_correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for next callback.

        Links this LangChain log to YAML fixture and raw API log.

        Args:
            correlation_id: Unique ID shared across all 3 layers
        """
        self._current_correlation_id = correlation_id

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called when LLM (chat) starts.

        Args:
            serialized: Serialized LLM object
            prompts: List of prompt strings
            **kwargs: Additional arguments
        """
        correlation_id = self._current_correlation_id or f"lc_{int(time.time() * 1000)}"
        self.request_start_times[correlation_id] = time.time()

        # Store correlation ID in metadata for on_llm_end
        kwargs.setdefault("metadata", {})["correlation_id"] = correlation_id

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM (chat) ends - log complete interaction.

        Args:
            response: LLM result object
            **kwargs: Additional arguments
        """
        correlation_id = (
            kwargs.get("metadata", {}).get("correlation_id") or self._current_correlation_id
        )
        if not correlation_id:
            correlation_id = f"lc_{int(time.time() * 1000)}"

        start_time = self.request_start_times.pop(correlation_id, time.time())
        duration_ms = (time.time() - start_time) * 1000

        # Extract LLM output details
        llm_output = response.llm_output or {}

        # Build log entry
        log_entry = {
            "correlation_id": correlation_id,
            "layer": "langchain_abstraction",
            "timestamp": time.time(),
            "timestamp_iso": datetime.now().isoformat(),
            "api_type": "chat",
            "langchain_input": {
                "messages": self._extract_messages(kwargs),
                "invocation_params": kwargs.get("invocation_params", {}),
            },
            "langchain_output": {
                "generations": (
                    [
                        {
                            "text": gen.text if hasattr(gen, "text") else None,
                            "message": {
                                "role": "assistant",
                                "content": (
                                    str(gen.message.content) if hasattr(gen, "message") else None
                                ),
                            },
                            "generation_info": (
                                gen.generation_info if hasattr(gen, "generation_info") else {}
                            ),
                        }
                        for gen in response.generations[0]
                    ]
                    if response.generations
                    else []
                ),
                "llm_output": llm_output,
            },
            "metadata": {
                "duration_ms": round(duration_ms, 2),
                "model_name": llm_output.get("model_name", "unknown"),
                "token_usage": llm_output.get("token_usage", {}),
                "system_fingerprint": llm_output.get("system_fingerprint"),
            },
        }

        # Save to file
        log_file = self.chat_dir / f"{correlation_id}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)

        print(f"🔗 [Layer 1] LangChain: {correlation_id} → {log_file}")

        # Reset correlation ID
        self._current_correlation_id = None

    def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any
    ) -> None:
        """Called when chat model starts.

        Args:
            serialized: Serialized model
            messages: List of message lists
            **kwargs: Additional arguments
        """
        correlation_id = self._current_correlation_id or f"lc_{int(time.time() * 1000)}"
        self.request_start_times[correlation_id] = time.time()
        kwargs.setdefault("metadata", {})["correlation_id"] = correlation_id

    def log_embedding_call(
        self,
        correlation_id: str,
        text: str,
        vector: List[float],
        model: str = "text-embedding-3-small",
        duration_ms: float = 0,
    ) -> None:
        """Log embedding API call (called manually from RecordingEmbeddings).

        Args:
            correlation_id: Unique ID linking to other layers
            text: Input text
            vector: Resulting embedding vector
            model: Model name
            duration_ms: Call duration
        """
        log_entry = {
            "correlation_id": correlation_id,
            "layer": "langchain_abstraction",
            "timestamp": time.time(),
            "timestamp_iso": datetime.now().isoformat(),
            "api_type": "embeddings",
            "langchain_input": {"text": text, "model": model},
            "langchain_output": {"vector": vector, "dimension": len(vector)},
            "metadata": {"duration_ms": round(duration_ms, 2), "model_name": model},
        }

        # Save to file
        log_file = self.embeddings_dir / f"{correlation_id}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)

        print(f"🔗 [Layer 1] LangChain: {correlation_id} → {log_file}")

    def log_chat_call(
        self,
        correlation_id: str,
        prompt: str,
        response: str,
        messages: List[BaseMessage],
        result: Any,
        model: str = "gpt-3.5-turbo",
        duration_ms: float = 0,
    ) -> None:
        """Log chat API call (called manually from RecordingChatModel).

        Args:
            correlation_id: Unique ID linking to other layers
            prompt: Input prompt string
            response: Response text
            messages: Original messages
            result: ChatResult object
            model: Model name
            duration_ms: Call duration
        """
        # Extract token usage from result if available
        llm_output = (
            result.llm_output if hasattr(result, "llm_output") and result.llm_output else {}
        )

        log_entry = {
            "correlation_id": correlation_id,
            "layer": "langchain_abstraction",
            "timestamp": time.time(),
            "timestamp_iso": datetime.now().isoformat(),
            "api_type": "chat",
            "langchain_input": {
                "prompt": prompt,
                "messages": [{"role": msg.type, "content": str(msg.content)} for msg in messages],
                "model": model,
            },
            "langchain_output": {
                "response": response,
                "generations": (
                    [
                        {
                            "text": gen.text if hasattr(gen, "text") else None,
                            "message": {
                                "role": "assistant",
                                "content": (
                                    str(gen.message.content) if hasattr(gen, "message") else None
                                ),
                            },
                        }
                        for gen in result.generations[0]
                    ]
                    if hasattr(result, "generations") and result.generations
                    else []
                ),
            },
            "metadata": {
                "duration_ms": round(duration_ms, 2),
                "model_name": llm_output.get("model_name", model),
                "token_usage": llm_output.get("token_usage", {}),
            },
        }

        # Save to file
        log_file = self.chat_dir / f"{correlation_id}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)

        print(f"🔗 [Layer 1] LangChain: {correlation_id} → {log_file}")

    def _extract_messages(self, kwargs: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract messages from kwargs.

        Args:
            kwargs: Callback kwargs

        Returns:
            List of message dicts with role and content
        """
        invocation_params = kwargs.get("invocation_params", {})
        messages = invocation_params.get("messages", [])

        extracted = []
        for msg in messages:
            if isinstance(msg, dict):
                extracted.append(msg)
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                extracted.append(
                    {
                        "role": msg.role if hasattr(msg, "role") else "unknown",
                        "content": str(msg.content),
                    }
                )

        return extracted


# Global singleton
_langchain_logger: Optional[LangChainLoggingCallback] = None


def get_langchain_logger() -> LangChainLoggingCallback:
    """Get or create global LangChain logging callback instance."""
    global _langchain_logger
    if _langchain_logger is None:
        _langchain_logger = LangChainLoggingCallback()
    return _langchain_logger
