"""Unit tests for EmbeddingService."""

import os
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError, RateLimitError

from src.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        service = EmbeddingService()

        assert service.model == "text-embedding-3-small"
        assert service._chunk_size == 500
        assert service._chunk_overlap == 50
        assert service.embeddings is not None
        assert service._splitter is not None

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        service = EmbeddingService(
            model="text-embedding-ada-002", chunk_size=1000, chunk_overlap=100
        )

        assert service.model == "text-embedding-ada-002"
        assert service._chunk_size == 1000
        assert service._chunk_overlap == 100

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_chunk_text_small_document(self):
        """Test chunking of small document (no chunking needed)."""
        service = EmbeddingService(chunk_size=500)

        text = "This is a short document."
        chunks = service._chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_chunk_text_large_document(self):
        """Test chunking of large document."""
        service = EmbeddingService(chunk_size=100, chunk_overlap=20)

        # Create text > 100 characters
        text = " ".join(["word"] * 50)  # ~200 characters
        chunks = service._chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 1

        # Check overlap exists (first chunk should share words with second)
        assert any(word in chunks[1] for word in chunks[0].split()[-5:])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_text_success(self, mock_embeddings_class):
        """Test embed_text returns vector."""
        # Mock embedding response
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService()
        text = "Test query"

        result = service.embed_text(text)

        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_embeddings.embed_query.assert_called_once_with(text)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_text_rate_limit_error(self, mock_embeddings_class):
        """Test embed_text handles rate limit errors."""
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.side_effect = RateLimitError(
            "Rate limit exceeded", response=MagicMock(status_code=429), body=None
        )
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService()

        with pytest.raises(RateLimitError):
            service.embed_text("Test")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_text_api_error(self, mock_embeddings_class):
        """Test embed_text handles API errors."""
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.side_effect = APIError(
            "API error", request=MagicMock(), body=None
        )
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService()

        with pytest.raises(APIError):
            service.embed_text("Test")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_document_single_chunk(self, mock_embeddings_class):
        """Test embed_document with small text (single chunk)."""
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536]
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService()
        text = "Short document"

        result = service.embed_document(text)

        assert len(result) == 1
        chunk_text, embedding = result[0]
        assert chunk_text == text
        assert len(embedding) == 1536

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_document_multiple_chunks(self, mock_embeddings_class):
        """Test embed_document with large text (multiple chunks)."""
        mock_embeddings = MagicMock()
        # Return 3 embeddings for 3 chunks
        mock_embeddings.embed_documents.return_value = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.3] * 1536,
        ]
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService(chunk_size=100, chunk_overlap=20)

        # Large text that will be chunked
        text = " ".join(["word"] * 100)  # ~400 characters

        result = service.embed_document(text)

        # Should have multiple chunks
        assert len(result) > 1

        # Each result is (chunk_text, embedding) tuple
        for chunk_text, embedding in result:
            assert isinstance(chunk_text, str)
            assert len(embedding) == 1536

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_document_with_retry_on_rate_limit(self, mock_embeddings_class):
        """Test embed_document retries on rate limit."""
        mock_embeddings = MagicMock()

        # Fail twice, then succeed
        mock_embeddings.embed_documents.side_effect = [
            RateLimitError("Rate limit", response=MagicMock(status_code=429), body=None),
            RateLimitError("Rate limit", response=MagicMock(status_code=429), body=None),
            [[0.1] * 1536],  # Success on 3rd attempt
        ]
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService()
        text = "Test document"

        result = service.embed_document(text)

        # Should succeed after retries
        assert len(result) == 1
        assert mock_embeddings.embed_documents.call_count == 3

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_document_exhausts_retries(self, mock_embeddings_class):
        """Test embed_document raises after max retries."""
        from tenacity import RetryError

        mock_embeddings = MagicMock()

        # Always fail
        mock_embeddings.embed_documents.side_effect = RateLimitError(
            "Rate limit", response=MagicMock(status_code=429), body=None
        )
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService()
        text = "Test document"

        # Tenacity wraps the exception in RetryError
        with pytest.raises(RetryError):
            service.embed_document(text)

        # Should have tried 3 times
        assert mock_embeddings.embed_documents.call_count == 3

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_chunk_config(self):
        """Test get_chunk_config returns configuration."""
        service = EmbeddingService(chunk_size=1000, chunk_overlap=100)

        config = service.get_chunk_config()

        assert config["chunk_size"] == 1000
        assert config["chunk_overlap"] == 100

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_model_info(self):
        """Test get_model_info returns model details."""
        service = EmbeddingService(model="text-embedding-3-small")

        info = service.get_model_info()

        assert info["model"] == "text-embedding-3-small"
        assert info["dimension"] == 1536

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.services.embedding_service.OpenAIEmbeddings")
    def test_embed_document_returns_chunk_embedding_pairs(self, mock_embeddings_class):
        """Test embed_document returns correct (chunk, embedding) structure."""
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_embeddings_class.return_value = mock_embeddings

        service = EmbeddingService(chunk_size=50)
        text = "First chunk. " * 10 + "Second chunk. " * 10  # Force 2 chunks

        result = service.embed_document(text)

        # Should return list of tuples
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) for item in result)
        assert all(len(item) == 2 for item in result)

        # Each tuple: (chunk_text: str, embedding: List[float])
        for chunk_text, embedding in result:
            assert isinstance(chunk_text, str)
            assert isinstance(embedding, list)
            assert len(embedding) == 1536
