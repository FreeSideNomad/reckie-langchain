"""Pilot tests demonstrating mock adapter pattern.

These tests show how to use mock adapters in real scenarios.
They demonstrate the three modes:
1. Mock mode (USE_MOCK_ADAPTERS=true) - No API calls
2. Recording mode (RECORD_FIXTURES=true) - Real API + save responses
3. Real mode (default) - Real API calls

Run with:
    # Mock mode (fast, no API costs)
    USE_MOCK_ADAPTERS=true pytest tests/pilot/

    # Recording mode (captures real API data)
    RECORD_FIXTURES=true pytest tests/pilot/

    # Real mode (uses real API)
    pytest tests/pilot/
"""

import os

import pytest

from src.api.dependencies import get_chat_provider, get_embeddings_provider


def test_embedding_simple_text():
    """Pilot: Simple embedding test."""
    embeddings = get_embeddings_provider()

    text = "This is a pilot test for embeddings"
    vector = embeddings.embed_query(text)

    assert len(vector) == 1536
    assert all(isinstance(v, float) for v in vector)
    print(f"✓ Embedded text: '{text[:30]}...'")
    print(f"  Vector dimension: {len(vector)}")
    print(f"  First 5 values: {vector[:5]}")


def test_embedding_batch():
    """Pilot: Batch embedding test."""
    embeddings = get_embeddings_provider()

    texts = ["Product vision document", "Feature specification", "Technical architecture"]
    vectors = embeddings.embed_documents(texts)

    assert len(vectors) == 3
    assert all(len(v) == 1536 for v in vectors)
    print(f"✓ Embedded {len(texts)} texts")
    for i, text in enumerate(texts):
        print(f"  [{i+1}] {text}: {len(vectors[i])} dims")


def test_embedding_edge_case_empty():
    """Pilot: Edge case - empty text."""
    embeddings = get_embeddings_provider()

    vector = embeddings.embed_query("")

    assert len(vector) == 1536
    print("✓ Handled empty string")


def test_chat_simple_prompt():
    """Pilot: Simple chat test."""
    chat = get_chat_provider()

    response = chat.invoke("Say hello")

    assert response.content
    assert len(response.content) > 0
    print(f"✓ Chat response: '{response.content[:50]}...'")


def test_chat_multi_turn():
    """Pilot: Multi-turn conversation test."""
    from langchain_core.messages import HumanMessage

    chat = get_chat_provider()

    messages = [HumanMessage(content="I'm testing mock adapters")]
    response = chat.invoke(messages)

    assert response.content
    print(f"✓ Multi-turn response: '{response.content[:50]}...'")


def test_chat_streaming():
    """Pilot: Streaming chat test (mock returns full response)."""
    chat = get_chat_provider()

    chunks = list(chat.stream("Count to three"))

    assert len(chunks) >= 1  # Mock returns at least 1 chunk
    print(f"✓ Streaming: Got {len(chunks)} chunk(s)")


@pytest.mark.skipif(
    os.getenv("USE_MOCK_ADAPTERS") != "true", reason="Only test mock behavior in mock mode"
)
def test_mock_mode_no_api_key_required():
    """Pilot: Verify mock mode works without API key."""
    # This test only runs in mock mode
    # It verifies that tests can run without OPENAI_API_KEY

    embeddings = get_embeddings_provider()
    vector = embeddings.embed_query("no API key needed")

    assert len(vector) == 1536
    print("✓ Mock mode works without API key")


def test_deterministic_responses():
    """Pilot: Verify responses are deterministic."""
    embeddings = get_embeddings_provider()

    text = "deterministic test"
    vector1 = embeddings.embed_query(text)
    vector2 = embeddings.embed_query(text)

    assert vector1 == vector2
    print("✓ Responses are deterministic")


def test_provider_type():
    """Pilot: Show which provider is being used."""
    embeddings = get_embeddings_provider()
    chat = get_chat_provider()

    print(f"\n📊 Provider Information:")
    print(f"  Embeddings: {type(embeddings).__name__}")
    print(f"  Chat: {type(chat).__name__}")

    if os.getenv("USE_MOCK_ADAPTERS") == "true":
        print(f"  Mode: 🎭 MOCK (no API calls)")
    elif os.getenv("RECORD_FIXTURES") == "true":
        print(f"  Mode: 🎬 RECORDING (real API + save fixtures)")
    else:
        print(f"  Mode: 🌐 REAL (real API calls)")


# Performance baseline test
def test_performance_baseline():
    """Pilot: Measure test execution time."""
    import time

    embeddings = get_embeddings_provider()

    start = time.time()
    embeddings.embed_query("performance test")
    duration = time.time() - start

    print(f"\n⏱️  Performance:")
    print(f"  Embedding time: {duration*1000:.2f}ms")

    if os.getenv("USE_MOCK_ADAPTERS") == "true":
        assert duration < 0.1, "Mock should be <100ms"
        print(f"  ✓ Mock mode is fast (<100ms)")
