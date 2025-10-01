"""Mock embeddings adapter implementing LangChain BaseEmbeddings interface."""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from langchain_core.embeddings import Embeddings


class MockEmbeddings(Embeddings):
    """Mock LangChain embeddings adapter using YAML fixtures.

    This adapter implements the LangChain BaseEmbeddings interface and returns
    deterministic embedding vectors from YAML fixture files. It's designed for:
    - Fast testing without API calls (<1ms per embedding)
    - Deterministic, reproducible test results
    - Learning how to build real provider adapters

    Example:
        >>> embeddings = MockEmbeddings()
        >>> vector = embeddings.embed_query("test text")
        >>> vectors = embeddings.embed_documents(["text1", "text2"])
    """

    def __init__(self, fixture_path: str = None, embedding_dimension: int = 1536):
        """Initialize mock embeddings adapter.

        Args:
            fixture_path: Path to YAML fixture file. If None, uses default.
            embedding_dimension: Dimension of embedding vectors (default: 1536 for OpenAI)
        """
        if fixture_path is None:
            # Default to tests/fixtures/mock_adapters/embeddings.yaml
            fixture_path = os.path.join(
                Path(__file__).parent.parent.parent.parent,
                "tests",
                "fixtures",
                "mock_adapters",
                "embeddings.yaml",
            )

        self.fixture_path = fixture_path
        self.embedding_dimension = embedding_dimension
        self.fixtures = self._load_fixtures()

    def _load_fixtures(self) -> Dict[str, List[float]]:
        """Load embedding fixtures from YAML file.

        Returns:
            Dictionary mapping text keys to embedding vectors
        """
        if not os.path.exists(self.fixture_path):
            # Return empty dict if fixture file doesn't exist yet
            return {}

        with open(self.fixture_path, "r") as f:
            data = yaml.safe_load(f)

        if not data or "embeddings" not in data:
            return {}

        # Build lookup dict: key -> vector, text -> vector
        fixtures = {}
        for item in data["embeddings"]:
            key = item.get("key")
            text = item.get("text")
            vector = item.get("vector")

            if key:
                fixtures[key] = vector
            if text:
                # Also allow lookup by exact text match
                fixtures[text] = vector

        return fixtures

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (list of floats)

        Raises:
            ValueError: If no fixture found for text
        """
        # Try exact text match first
        if text in self.fixtures:
            return self.fixtures[text]

        # Try hashed lookup (first 8 chars of hash as key)
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        if text_hash in self.fixtures:
            return self.fixtures[text_hash]

        # Fallback: generate deterministic vector from hash
        # This allows tests to work even without fixtures
        full_hash = hashlib.md5(text.encode()).hexdigest()
        vector = []
        for i in range(0, len(full_hash), 2):
            # Convert hex pairs to float values between -1 and 1
            val = int(full_hash[i : i + 2], 16) / 127.5 - 1.0
            vector.append(val)

        # Pad or truncate to correct dimension
        if len(vector) < self.embedding_dimension:
            vector.extend([0.0] * (self.embedding_dimension - len(vector)))
        else:
            vector = vector[: self.embedding_dimension]

        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents.

        Args:
            texts: List of text documents to embed

        Returns:
            List of embedding vectors, one per document
        """
        return [self._get_embedding(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        return self._get_embedding(text)

    # Optional: Implement async methods (LangChain may use these)
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents."""
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query."""
        return self.embed_query(text)
