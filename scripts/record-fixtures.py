#!/usr/bin/env python3
"""Record real API responses to YAML fixtures for mock adapters.

This script makes real API calls to OpenAI and saves the responses as YAML fixtures.
It's designed to be run once to capture realistic test data.

Usage:
    python scripts/record-fixtures.py --embeddings --chat
    python scripts/record-fixtures.py --embeddings-only
    python scripts/record-fixtures.py --chat-only

Environment Variables:
    OPENAI_API_KEY: Required for API access

Cost Estimation:
    - Embeddings: ~$0.10 for 10 texts (text-embedding-3-small)
    - Chat: ~$0.50 for 10 completions (gpt-3.5-turbo)
    - Total: ~$2.89 for full fixture set
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import yaml
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage


# Test scenarios to record
EMBEDDING_SCENARIOS = [
    {
        "key": "simple_text",
        "text": "This is a test document"
    },
    {
        "key": "product_vision",
        "text": "Our vision is to build an AI-powered document management system"
    },
    {
        "key": "technical_docs",
        "text": "PostgreSQL database schema with pgvector extension for embeddings"
    },
    {
        "key": "feature_description",
        "text": "LangChain provider adapter mock pattern for testing without API costs"
    },
    {
        "key": "user_story",
        "text": "As a developer I want mock adapters so that I can run tests without API calls"
    },
    {
        "key": "acceptance_criteria",
        "text": "Given a test scenario When I run tests Then embeddings are returned from fixtures"
    },
    {
        "key": "code_snippet",
        "text": "def get_embeddings_provider(): return MockEmbeddings() if USE_MOCK_ADAPTERS else OpenAIEmbeddings()"
    },
    {
        "key": "empty_text",
        "text": ""
    },
    {
        "key": "very_long_text",
        "text": "This is a very long document with many words and sentences that goes on and on. " * 50  # Repeat for length
    },
    {
        "key": "technical_jargon",
        "text": "Kubernetes pods orchestration with Helm charts deployment via ArgoCD GitOps pipeline"
    },
]

CHAT_SCENARIOS = [
    {
        "key": "simple_greeting",
        "prompt": "Say hello"
    },
    {
        "key": "vision_summary",
        "prompt": "Summarize this vision: We want to build an AI-powered hierarchical document management system"
    },
    {
        "key": "technical_explanation",
        "prompt": "Explain what pgvector is in one sentence"
    },
    {
        "key": "code_generation",
        "prompt": "Write a Python function that returns 'Hello World'"
    },
    {
        "key": "question_answering",
        "prompt": "What is the capital of France?"
    },
    {
        "key": "multi_turn_context",
        "prompt": "I'm building a testing framework. What should I mock?"
    },
    {
        "key": "error_explanation",
        "prompt": "Why would a test fail with 'NotImplementedError'?"
    },
    {
        "key": "empty_prompt",
        "prompt": ""
    },
    {
        "key": "very_long_prompt",
        "prompt": "Explain in detail: " + "This is important context. " * 100
    },
    {
        "key": "code_review",
        "prompt": "Review this code: class MockEmbeddings(Embeddings): pass"
    },
]


def record_embeddings(output_path: str, model: str = "text-embedding-3-small"):
    """Record embedding responses from OpenAI API.

    Args:
        output_path: Path to output YAML file
        model: OpenAI embedding model to use

    Returns:
        Number of embeddings recorded
    """
    print(f"🎬 Recording embeddings using {model}...")
    print(f"📊 Scenarios to record: {len(EMBEDDING_SCENARIOS)}")

    # Initialize OpenAI embeddings
    embeddings_provider = OpenAIEmbeddings(model=model)

    # Record each scenario
    recorded_data = {"embeddings": []}
    total_tokens = 0

    for i, scenario in enumerate(EMBEDDING_SCENARIOS, 1):
        key = scenario["key"]
        text = scenario["text"]

        print(f"  [{i}/{len(EMBEDDING_SCENARIOS)}] Recording '{key}'... ", end="", flush=True)

        try:
            # Make API call
            vector = embeddings_provider.embed_query(text)

            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            est_tokens = len(text) // 4
            total_tokens += est_tokens

            # Add to dataset
            recorded_data["embeddings"].append({
                "key": key,
                "text": text,
                "vector": vector,
                "dimension": len(vector),
                "model": model,
                "tokens_estimate": est_tokens
            })

            print(f"✓ (vector dim: {len(vector)})")

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    # Save to YAML
    print(f"\n💾 Saving to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        yaml.dump(recorded_data, f, default_flow_style=False, sort_keys=False)

    # Cost estimation (text-embedding-3-small: $0.00002 per 1K tokens)
    cost = (total_tokens / 1000) * 0.00002
    print(f"✅ Recorded {len(recorded_data['embeddings'])} embeddings")
    print(f"📈 Total tokens: ~{total_tokens}")
    print(f"💰 Estimated cost: ${cost:.4f}")

    return len(recorded_data['embeddings'])


def record_chat(output_path: str, model: str = "gpt-3.5-turbo"):
    """Record chat completion responses from OpenAI API.

    Args:
        output_path: Path to output YAML file
        model: OpenAI chat model to use

    Returns:
        Number of completions recorded
    """
    print(f"🎬 Recording chat completions using {model}...")
    print(f"📊 Scenarios to record: {len(CHAT_SCENARIOS)}")

    # Initialize OpenAI chat
    chat_model = ChatOpenAI(model=model, temperature=0)  # temperature=0 for deterministic

    # Record each scenario
    recorded_data = {"completions": []}
    total_tokens = 0

    for i, scenario in enumerate(CHAT_SCENARIOS, 1):
        key = scenario["key"]
        prompt = scenario["prompt"]

        print(f"  [{i}/{len(CHAT_SCENARIOS)}] Recording '{key}'... ", end="", flush=True)

        try:
            # Make API call
            messages = [HumanMessage(content=prompt)]
            response = chat_model.invoke(messages)

            # Estimate tokens (rough: input + output)
            est_tokens = (len(prompt) + len(response.content)) // 4
            total_tokens += est_tokens

            # Add to dataset
            recorded_data["completions"].append({
                "key": key,
                "prompt": prompt,
                "response": response.content,
                "model": model,
                "tokens_estimate": est_tokens
            })

            print(f"✓ (response length: {len(response.content)} chars)")

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    # Save to YAML
    print(f"\n💾 Saving to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        yaml.dump(recorded_data, f, default_flow_style=False, sort_keys=False)

    # Cost estimation (gpt-3.5-turbo: $0.0005 per 1K input, $0.0015 per 1K output)
    # Simplified: assume 50/50 input/output
    cost = (total_tokens / 1000) * 0.001
    print(f"✅ Recorded {len(recorded_data['completions'])} completions")
    print(f"📈 Total tokens: ~{total_tokens}")
    print(f"💰 Estimated cost: ${cost:.4f}")

    return len(recorded_data['completions'])


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Record real API responses to YAML fixtures"
    )
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Record embedding fixtures"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Record chat completion fixtures"
    )
    parser.add_argument(
        "--embeddings-only",
        action="store_true",
        help="Record only embeddings (skip chat)"
    )
    parser.add_argument(
        "--chat-only",
        action="store_true",
        help="Record only chat (skip embeddings)"
    )
    parser.add_argument(
        "--output-dir",
        default="tests/fixtures/mock_adapters",
        help="Output directory for fixtures (default: tests/fixtures/mock_adapters)"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Determine what to record
    record_embeddings_flag = args.embeddings or args.embeddings_only or (not args.chat_only and not args.embeddings_only)
    record_chat_flag = args.chat or args.chat_only or (not args.embeddings_only and not args.chat_only)

    # Calculate paths
    project_root = Path(__file__).parent.parent
    embeddings_path = project_root / args.output_dir / "embeddings.yaml"
    chat_path = project_root / args.output_dir / "chat.yaml"

    print("=" * 60)
    print("🎬 OpenAI API Fixture Recording")
    print("=" * 60)
    print(f"📁 Output directory: {args.output_dir}")
    print(f"🔑 API Key: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
    print()

    total_embeddings = 0
    total_completions = 0

    # Record embeddings
    if record_embeddings_flag:
        try:
            total_embeddings = record_embeddings(str(embeddings_path))
            print()
        except Exception as e:
            print(f"❌ Embedding recording failed: {e}")

    # Record chat
    if record_chat_flag:
        try:
            total_completions = record_chat(str(chat_path))
            print()
        except Exception as e:
            print(f"❌ Chat recording failed: {e}")

    # Summary
    print("=" * 60)
    print("✅ Recording Complete")
    print("=" * 60)
    if total_embeddings > 0:
        print(f"📊 Embeddings: {total_embeddings} recorded → {embeddings_path}")
    if total_completions > 0:
        print(f"💬 Chat: {total_completions} recorded → {chat_path}")
    print()
    print("Next steps:")
    print("  1. Review the fixture files for quality")
    print("  2. Commit fixtures to git")
    print("  3. Run tests with USE_MOCK_ADAPTERS=true")
    print()


if __name__ == "__main__":
    main()
