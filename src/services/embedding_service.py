"""Embedding service for generating OpenAI text embeddings.

Handles document chunking internally as a private implementation detail.
Callers use simple public API: embed_text() or embed_document().
"""

import logging
from typing import List, Tuple

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from openai import APIError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating OpenAI text embeddings.

    Encapsulates chunking strategy - callers don't need to know about it.
    Provides simple API for embedding single texts or full documents.

    Note: Synchronous implementation for simplicity.
    Future enhancement: Use Celery for async task queue.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """Initialize embedding service.

        Args:
            model: OpenAI embedding model name
            chunk_size: Maximum tokens per chunk (default: 500)
            chunk_overlap: Overlapping tokens between chunks (default: 50)
        """
        self.model = model
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

        # Initialize OpenAI embeddings
        # Note: OpenAIEmbeddings reads OPENAI_API_KEY from environment automatically
        self.embeddings = OpenAIEmbeddings(model=self.model)

        # Private: text splitter for chunking
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks.

        Private implementation detail. Callers use embed_document() instead.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks with overlap
        """
        return self._splitter.split_text(text)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single small text (no chunking).

        Use for: short queries, single sentences, metadata, etc.

        Args:
            text: Short text to embed (< 500 tokens recommended)

        Returns:
            1536-dimensional embedding vector (text-embedding-3-small)

        Raises:
            RateLimitError: OpenAI rate limit exceeded
            APIError: OpenAI API error
        """
        try:
            embedding = self.embeddings.embed_query(text)
            logger.debug(f"Generated embedding for text (length={len(text)})")
            return embedding
        except RateLimitError:
            logger.warning("Embedding rate limit hit for embed_text()")
            raise
        except APIError as e:
            logger.error(f"Embedding API error in embed_text(): {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    def embed_document(self, text: str) -> List[Tuple[str, List[float]]]:
        """Generate embeddings for document (handles chunking internally).

        Use for: full documents that may exceed token limits.
        Automatically chunks large text and returns chunk-embedding pairs.

        Includes retry logic with exponential backoff for API resilience.

        Args:
            text: Document text (any length)

        Returns:
            List of (chunk_text, embedding_vector) tuples
            Each embedding is 1536-dimensional

        Raises:
            RateLimitError: After 3 retry attempts on rate limit
            APIError: After 3 retry attempts on API error
        """
        try:
            # Internal chunking - caller doesn't need to know about this
            chunks = self._chunk_text(text)
            logger.info(
                f"Chunked document into {len(chunks)} chunks "
                f"(size={self._chunk_size}, overlap={self._chunk_overlap})"
            )

            # Batch embed all chunks
            embeddings = self.embeddings.embed_documents(chunks)
            logger.info(f"Generated {len(embeddings)} embeddings successfully")

            # Return chunk-embedding pairs
            return list(zip(chunks, embeddings))

        except RateLimitError:
            logger.warning("Embedding rate limit hit for embed_document(), retrying...")
            raise
        except APIError as e:
            logger.error(f"Embedding API error in embed_document(): {e}")
            raise

    def get_chunk_config(self) -> dict:
        """Get current chunking configuration.

        Useful for debugging and logging.

        Returns:
            Dict with chunk_size and chunk_overlap
        """
        return {"chunk_size": self._chunk_size, "chunk_overlap": self._chunk_overlap}

    def get_model_info(self) -> dict:
        """Get embedding model information.

        Returns:
            Dict with model name and vector dimension
        """
        return {
            "model": self.model,
            "dimension": 1536,  # text-embedding-3-small dimension
        }
