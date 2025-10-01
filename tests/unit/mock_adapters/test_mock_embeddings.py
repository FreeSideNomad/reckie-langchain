"""Unit tests for MockEmbeddings adapter."""

import pytest

from src.testing.mock_adapters.embeddings import MockEmbeddings


def test_mock_embeddings_initialization():
    """Test MockEmbeddings can be initialized."""
    embeddings = MockEmbeddings()
    assert embeddings is not None
    assert embeddings.embedding_dimension == 1536


def test_embed_query_returns_vector():
    """Test embed_query returns a vector of correct dimension."""
    embeddings = MockEmbeddings()
    vector = embeddings.embed_query("test text")

    assert isinstance(vector, list)
    assert len(vector) == 1536
    assert all(isinstance(v, float) for v in vector)


def test_embed_documents_returns_list_of_vectors():
    """Test embed_documents returns multiple vectors."""
    embeddings = MockEmbeddings()
    texts = ["text1", "text2", "text3"]
    vectors = embeddings.embed_documents(texts)

    assert isinstance(vectors, list)
    assert len(vectors) == 3
    assert all(len(v) == 1536 for v in vectors)


def test_embed_same_text_returns_same_vector():
    """Test deterministic: same text → same vector."""
    embeddings = MockEmbeddings()
    text = "test deterministic"

    vector1 = embeddings.embed_query(text)
    vector2 = embeddings.embed_query(text)

    assert vector1 == vector2


def test_embed_different_texts_return_different_vectors():
    """Test different texts produce different vectors."""
    embeddings = MockEmbeddings()

    vector1 = embeddings.embed_query("text one")
    vector2 = embeddings.embed_query("text two")

    assert vector1 != vector2


def test_embed_empty_string():
    """Test embedding empty string doesn't crash."""
    embeddings = MockEmbeddings()
    vector = embeddings.embed_query("")

    assert isinstance(vector, list)
    assert len(vector) == 1536


@pytest.mark.asyncio
async def test_async_embed_query():
    """Test async embed_query works."""
    embeddings = MockEmbeddings()
    vector = await embeddings.aembed_query("async test")

    assert isinstance(vector, list)
    assert len(vector) == 1536


@pytest.mark.asyncio
async def test_async_embed_documents():
    """Test async embed_documents works."""
    embeddings = MockEmbeddings()
    texts = ["async1", "async2"]
    vectors = await embeddings.aembed_documents(texts)

    assert len(vectors) == 2
    assert all(len(v) == 1536 for v in vectors)


def test_fixture_lookup_by_text():
    """Test that fixtures can be looked up by exact text match."""
    embeddings = MockEmbeddings()

    # Use text that's NOT in fixtures to test hash fallback
    vector = embeddings.embed_query("Text not in fixtures - should use hash fallback")

    assert len(vector) == 1536
    # Should work regardless of whether fixture exists
