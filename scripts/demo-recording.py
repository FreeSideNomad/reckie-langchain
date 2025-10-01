#!/usr/bin/env python3
"""Demo script to show recording wrapper in action.

This demonstrates how recording mode works - it makes real API calls
and automatically saves responses to YAML fixtures.

Usage:
    # Enable recording
    export RECORD_FIXTURES=true
    export OPENAI_API_KEY=your-key

    # Run demo
    python scripts/demo-recording.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.dependencies import get_embeddings_provider, get_chat_provider


def demo_embeddings():
    """Demo embeddings recording."""
    print("=" * 60)
    print("🎬 Demo: Embeddings Recording")
    print("=" * 60)

    # Get provider (will be RecordingEmbeddings if RECORD_FIXTURES=true)
    embeddings = get_embeddings_provider()
    print(f"Provider: {type(embeddings).__name__}")
    print()

    # Test scenarios
    test_texts = [
        "This is a test document",
        "Our vision is to build an AI-powered document management system",
        "PostgreSQL database schema with pgvector extension"
    ]

    print(f"Embedding {len(test_texts)} texts...")
    vectors = embeddings.embed_documents(test_texts)

    print(f"✓ Got {len(vectors)} vectors, each with {len(vectors[0])} dimensions")
    print()

    # Single query
    print("Embedding single query...")
    query_vector = embeddings.embed_query("What is vector search?")
    print(f"✓ Got query vector with {len(query_vector)} dimensions")
    print()

    if os.getenv("RECORD_FIXTURES") == "true":
        print("✅ Responses recorded to tests/fixtures/mock_adapters/embeddings.yaml")
    else:
        print("ℹ️  Recording disabled (set RECORD_FIXTURES=true to enable)")


def demo_chat():
    """Demo chat recording."""
    print("=" * 60)
    print("💬 Demo: Chat Recording")
    print("=" * 60)

    # Get provider (will be RecordingChatModel if RECORD_FIXTURES=true)
    chat = get_chat_provider()
    print(f"Provider: {type(chat).__name__}")
    print()

    # Test scenarios
    test_prompts = [
        "Say hello in a friendly way",
        "Explain what a mock adapter is in one sentence",
        "What are the benefits of testing without API costs?"
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"[{i}/{len(test_prompts)}] Sending: {prompt}")
        response = chat.invoke(prompt)
        print(f"    Response: {response.content[:100]}...")
        print()

    if os.getenv("RECORD_FIXTURES") == "true":
        print("✅ Responses recorded to tests/fixtures/mock_adapters/chat.yaml")
    else:
        print("ℹ️  Recording disabled (set RECORD_FIXTURES=true to enable)")


def main():
    """Run demo."""
    # Check environment
    print("🔧 Environment Configuration")
    print(f"  RECORD_FIXTURES: {os.getenv('RECORD_FIXTURES', 'not set')}")
    print(f"  USE_MOCK_ADAPTERS: {os.getenv('USE_MOCK_ADAPTERS', 'not set')}")
    print(f"  OPENAI_API_KEY: {'✓ set' if os.getenv('OPENAI_API_KEY') else '✗ not set'}")
    print()

    if os.getenv("USE_MOCK_ADAPTERS") == "true":
        print("⚠️  USE_MOCK_ADAPTERS=true - will use mocks, not recording!")
        print("   To record real data, unset USE_MOCK_ADAPTERS")
        return

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set - cannot record real data")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Run demos
    demo_embeddings()
    print()
    demo_chat()

    print()
    print("=" * 60)
    print("✅ Demo Complete")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Check fixture files in tests/fixtures/mock_adapters/")
    print("  2. Run tests with USE_MOCK_ADAPTERS=true to use fixtures")
    print("  3. Record more scenarios as needed")


if __name__ == "__main__":
    main()
