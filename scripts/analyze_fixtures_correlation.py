#!/usr/bin/env python3
"""Analyze correlation between YAML fixtures, LangChain logs, and raw API logs.

This script:
1. Loads YAML fixtures (Layer 2)
2. Loads LangChain logs (Layer 1)
3. Loads raw API logs (Layer 3)
4. Correlates all 3 layers using correlation_id
5. Generates cost analysis and performance metrics

Usage:
    python scripts/analyze_fixtures_correlation.py

Output:
    - Console report with correlations
    - tests/fixtures/mock_adapters/correlation_report.md
    - tests/fixtures/mock_adapters/cost_analysis.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import yaml


def load_yaml_fixtures(fixture_path: Path) -> Dict:
    """Load YAML fixture file."""
    if not fixture_path.exists():
        return {}

    with open(fixture_path) as f:
        return yaml.safe_load(f) or {}


def load_json_log(log_path: Path) -> Optional[Dict]:
    """Load JSON log file."""
    if not log_path.exists():
        return None

    with open(log_path) as f:
        return json.load(f)


def find_log_by_correlation_id(log_dir: Path, correlation_id: str) -> Optional[Dict]:
    """Find log file by correlation ID."""
    log_file = log_dir / f"{correlation_id}.json"
    return load_json_log(log_file)


def analyze_embeddings_correlation(base_dir: Path) -> Dict:
    """Analyze embeddings fixtures and logs."""
    embeddings_yaml = load_yaml_fixtures(base_dir / "embeddings.yaml")
    embeddings_list = embeddings_yaml.get("embeddings", [])

    langchain_dir = base_dir / "langchain_calls" / "embeddings"
    raw_api_dir = base_dir / "raw_api" / "embeddings"

    results = []
    total_cost = 0.0
    total_tokens = 0
    total_duration = 0.0

    for emb in embeddings_list:
        correlation_id = emb.get("correlation_id")
        if not correlation_id:
            results.append({
                "yaml_key": emb.get("key"),
                "correlation_id": None,
                "status": "missing_correlation_id",
                "langchain_log": None,
                "raw_api_log": None
            })
            continue

        # Load Layer 1 (LangChain)
        langchain_log = find_log_by_correlation_id(langchain_dir, correlation_id)

        # Load Layer 3 (Raw API)
        raw_api_log = find_log_by_correlation_id(raw_api_dir, correlation_id)

        # Extract metrics
        cost = 0.0
        tokens = 0
        duration = 0.0

        if raw_api_log:
            metadata = raw_api_log.get("metadata", {})
            cost = metadata.get("cost_usd", 0.0)
            tokens = metadata.get("tokens", {}).get("total", 0)
            duration = metadata.get("duration_ms", 0.0)

            total_cost += cost
            total_tokens += tokens
            total_duration += duration

        results.append({
            "yaml_key": emb.get("key"),
            "correlation_id": correlation_id,
            "text_preview": emb.get("text", "")[:60] + "...",
            "status": "✅" if (langchain_log and raw_api_log) else "⚠️ partial",
            "langchain_log": "found" if langchain_log else "missing",
            "raw_api_log": "found" if raw_api_log else "missing",
            "tokens": tokens,
            "cost_usd": cost,
            "duration_ms": duration
        })

    return {
        "type": "embeddings",
        "total_fixtures": len(embeddings_list),
        "results": results,
        "totals": {
            "cost_usd": round(total_cost, 8),
            "tokens": total_tokens,
            "avg_duration_ms": round(total_duration / len(embeddings_list), 2) if embeddings_list else 0
        }
    }


def analyze_chat_correlation(base_dir: Path) -> Dict:
    """Analyze chat fixtures and logs."""
    chat_yaml = load_yaml_fixtures(base_dir / "chat.yaml")
    completions_list = chat_yaml.get("completions", [])

    langchain_dir = base_dir / "langchain_calls" / "chat"
    raw_api_dir = base_dir / "raw_api" / "chat"

    results = []
    total_cost = 0.0
    total_tokens = 0
    total_duration = 0.0

    for comp in completions_list:
        correlation_id = comp.get("correlation_id")
        if not correlation_id:
            results.append({
                "yaml_key": comp.get("key"),
                "correlation_id": None,
                "status": "missing_correlation_id",
                "langchain_log": None,
                "raw_api_log": None
            })
            continue

        # Load Layer 1 (LangChain)
        langchain_log = find_log_by_correlation_id(langchain_dir, correlation_id)

        # Load Layer 3 (Raw API)
        raw_api_log = find_log_by_correlation_id(raw_api_dir, correlation_id)

        # Extract metrics
        cost = 0.0
        tokens = 0
        duration = 0.0

        if raw_api_log:
            metadata = raw_api_log.get("metadata", {})
            cost = metadata.get("cost_usd", 0.0)
            tokens = metadata.get("tokens", {}).get("total", 0)
            duration = metadata.get("duration_ms", 0.0)

            total_cost += cost
            total_tokens += tokens
            total_duration += duration

        results.append({
            "yaml_key": comp.get("key"),
            "correlation_id": correlation_id,
            "prompt_preview": comp.get("prompt", "")[:60] + "...",
            "status": "✅" if (langchain_log and raw_api_log) else "⚠️ partial",
            "langchain_log": "found" if langchain_log else "missing",
            "raw_api_log": "found" if raw_api_log else "missing",
            "tokens": tokens,
            "cost_usd": cost,
            "duration_ms": duration
        })

    return {
        "type": "chat",
        "total_fixtures": len(completions_list),
        "results": results,
        "totals": {
            "cost_usd": round(total_cost, 8),
            "tokens": total_tokens,
            "avg_duration_ms": round(total_duration / len(completions_list), 2) if completions_list else 0
        }
    }


def generate_markdown_report(emb_analysis: Dict, chat_analysis: Dict, output_path: Path):
    """Generate markdown correlation report."""
    report = f"""# Fixture Correlation Analysis Report

**Generated**: {datetime.now().isoformat()}

## Summary

### Embeddings
- **Total Fixtures**: {emb_analysis['total_fixtures']}
- **Total Cost**: ${emb_analysis['totals']['cost_usd']:.8f}
- **Total Tokens**: {emb_analysis['totals']['tokens']:,}
- **Avg Duration**: {emb_analysis['totals']['avg_duration_ms']:.2f}ms

### Chat Completions
- **Total Fixtures**: {chat_analysis['total_fixtures']}
- **Total Cost**: ${chat_analysis['totals']['cost_usd']:.8f}
- **Total Tokens**: {chat_analysis['totals']['tokens']:,}
- **Avg Duration**: {chat_analysis['totals']['avg_duration_ms']:.2f}ms

### Grand Total
- **Total Fixtures**: {emb_analysis['total_fixtures'] + chat_analysis['total_fixtures']}
- **Total Cost**: ${emb_analysis['totals']['cost_usd'] + chat_analysis['totals']['cost_usd']:.6f}
- **Total Tokens**: {emb_analysis['totals']['tokens'] + chat_analysis['totals']['tokens']:,}

---

## Embeddings Correlation

| YAML Key | Correlation ID | Text Preview | Layer 1 | Layer 3 | Tokens | Cost | Duration |
|----------|----------------|--------------|---------|---------|--------|------|----------|
"""

    for result in emb_analysis['results'][:20]:  # Show first 20
        report += f"| {result['yaml_key']} | {result['correlation_id'] or 'N/A'} | {result.get('text_preview', 'N/A')[:40]} | {result['langchain_log']} | {result['raw_api_log']} | {result.get('tokens', 0)} | ${result.get('cost_usd', 0):.8f} | {result.get('duration_ms', 0):.1f}ms |\n"

    if len(emb_analysis['results']) > 20:
        report += f"\n*... and {len(emb_analysis['results']) - 20} more embeddings*\n"

    report += """
---

## Chat Completions Correlation

| YAML Key | Correlation ID | Prompt Preview | Layer 1 | Layer 3 | Tokens | Cost | Duration |
|----------|----------------|----------------|---------|---------|--------|------|----------|
"""

    for result in chat_analysis['results'][:20]:  # Show first 20
        report += f"| {result['yaml_key']} | {result['correlation_id'] or 'N/A'} | {result.get('prompt_preview', 'N/A')[:40]} | {result['langchain_log']} | {result['raw_api_log']} | {result.get('tokens', 0)} | ${result.get('cost_usd', 0):.8f} | {result.get('duration_ms', 0):.1f}ms |\n"

    if len(chat_analysis['results']) > 20:
        report += f"\n*... and {len(chat_analysis['results']) - 20} more chat completions*\n"

    report += """
---

## Layer Verification

### ✅ Complete Correlations
Fixtures with all 3 layers (YAML + LangChain + Raw API):
"""

    complete_emb = [r for r in emb_analysis['results'] if r['status'] == '✅']
    complete_chat = [r for r in chat_analysis['results'] if r['status'] == '✅']

    report += f"- Embeddings: {len(complete_emb)}/{emb_analysis['total_fixtures']}\n"
    report += f"- Chat: {len(complete_chat)}/{chat_analysis['total_fixtures']}\n"

    report += """
### ⚠️ Partial Correlations
Fixtures missing one or more layers:
"""

    partial_emb = [r for r in emb_analysis['results'] if r['status'] != '✅']
    partial_chat = [r for r in chat_analysis['results'] if r['status'] != '✅']

    report += f"- Embeddings: {len(partial_emb)}/{emb_analysis['total_fixtures']}\n"
    report += f"- Chat: {len(partial_chat)}/{chat_analysis['total_fixtures']}\n"

    if partial_emb:
        report += "\n**Embedding Issues:**\n"
        for r in partial_emb[:5]:
            report += f"- {r['correlation_id'] or 'No ID'}: LangChain={r['langchain_log']}, Raw API={r['raw_api_log']}\n"

    if partial_chat:
        report += "\n**Chat Issues:**\n"
        for r in partial_chat[:5]:
            report += f"- {r['correlation_id'] or 'No ID'}: LangChain={r['langchain_log']}, Raw API={r['raw_api_log']}\n"

    report += """
---

## Usage Instructions

### View Individual Logs

```bash
# View Layer 1 (LangChain log)
cat tests/fixtures/mock_adapters/langchain_calls/embeddings/<correlation_id>.json

# View Layer 2 (YAML fixture)
grep -A 10 "correlation_id: <correlation_id>" tests/fixtures/mock_adapters/embeddings.yaml

# View Layer 3 (Raw API log)
cat tests/fixtures/mock_adapters/raw_api/embeddings/<correlation_id>.json
```

### Trace a Specific Fixture

1. Find correlation_id in YAML fixture
2. Use correlation_id to find matching logs in Layer 1 and Layer 3
3. Compare all 3 layers to understand the complete flow

---

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open(output_path, 'w') as f:
        f.write(report)


def main():
    """Run correlation analysis."""
    print("=" * 80)
    print("FIXTURE CORRELATION ANALYSIS")
    print("=" * 80)
    print()

    base_dir = Path("tests/fixtures/mock_adapters")

    if not base_dir.exists():
        print(f"❌ Error: {base_dir} not found")
        sys.exit(1)

    # Analyze embeddings
    print("📊 Analyzing embeddings correlation...")
    emb_analysis = analyze_embeddings_correlation(base_dir)
    print(f"   Found {emb_analysis['total_fixtures']} embeddings")
    print(f"   Total cost: ${emb_analysis['totals']['cost_usd']:.8f}")
    print(f"   Total tokens: {emb_analysis['totals']['tokens']:,}")
    print()

    # Analyze chat
    print("📊 Analyzing chat correlation...")
    chat_analysis = analyze_chat_correlation(base_dir)
    print(f"   Found {chat_analysis['total_fixtures']} chat completions")
    print(f"   Total cost: ${chat_analysis['totals']['cost_usd']:.8f}")
    print(f"   Total tokens: {chat_analysis['totals']['tokens']:,}")
    print()

    # Generate reports
    print("📝 Generating reports...")

    # Markdown report
    report_path = base_dir / "correlation_report.md"
    generate_markdown_report(emb_analysis, chat_analysis, report_path)
    print(f"   ✅ Markdown report: {report_path}")

    # JSON cost analysis
    cost_analysis = {
        "generated_at": datetime.now().isoformat(),
        "embeddings": emb_analysis['totals'],
        "chat": chat_analysis['totals'],
        "grand_total": {
            "cost_usd": round(
                emb_analysis['totals']['cost_usd'] + chat_analysis['totals']['cost_usd'],
                6
            ),
            "tokens": emb_analysis['totals']['tokens'] + chat_analysis['totals']['tokens'],
            "total_fixtures": emb_analysis['total_fixtures'] + chat_analysis['total_fixtures']
        }
    }

    cost_path = base_dir / "cost_analysis.json"
    with open(cost_path, 'w') as f:
        json.dump(cost_analysis, f, indent=2)
    print(f"   ✅ Cost analysis: {cost_path}")

    print()
    print("=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print()
    print(f"📄 View report: {report_path}")
    print(f"💰 View costs: {cost_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
