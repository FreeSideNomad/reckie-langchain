# Dual-Layer API Logging Implementation

**Status**: ✅ Core implementation complete, integration in progress
**Created**: 2025-10-01
**Purpose**: Capture both LangChain abstraction AND raw OpenAI API calls with correlation

---

## Architecture Overview

### Three-Layer Capture System

```
┌────────────────────────────────────────────────────────────────┐
│  Application Layer (your code)                                 │
│  embeddings.embed_query("text") / chat.invoke(messages)       │
└─────────────────────┬──────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────┐
│  📊 LAYER 1: LangChain Abstraction                             │
│  Module: langchain_logging_callback.py                         │
│  Output: langchain_calls/embeddings/<id>.json                  │
│          langchain_calls/chat/<id>.json                        │
│  Purpose: How LangChain sees and processes API calls           │
└─────────────────────┬──────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────┐
│  📝 LAYER 2: YAML Fixtures (for mocking)                       │
│  Module: recording_wrapper.py                                  │
│  Output: embeddings.yaml / chat.yaml                           │
│  Purpose: Simplified fixtures for test mocking                 │
└─────────────────────┬──────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────┐
│  OpenAI SDK (langchain_openai)                                 │
└─────────────────────┬──────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────┐
│  📡 LAYER 3: Raw OpenAI HTTP                                   │
│  Module: httpx_logging_transport.py                            │
│  Output: raw_api/embeddings/<id>.json                          │
│          raw_api/chat/<id>.json                                │
│  Purpose: Actual HTTP request/response from OpenAI API         │
└─────────────────────┬──────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────┐
│  OpenAI API (https://api.openai.com/v1/...)                    │
└────────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### ✅ Completed

1. **httpx_logging_transport.py** - Layer 3 (Raw HTTP capture)
   - Location: `src/testing/mock_adapters/httpx_logging_transport.py`
   - Functionality: Intercepts httpx requests/responses
   - Output: JSON files with complete HTTP request/response
   - Cost calculation: Automatic per-request pricing

2. **langchain_logging_callback.py** - Layer 1 (LangChain abstraction)
   - Location: `src/testing/mock_adapters/langchain_logging_callback.py`
   - Functionality: LangChain callback handler
   - Output: JSON files with LangChain's view of API calls
   - Captures: Messages, prompts, generations, token usage

3. **recording_wrapper.py** - Layer 2 (YAML fixtures) - PARTIAL
   - Location: `src/testing/mock_adapters/recording_wrapper.py`
   - Status: RecordingEmbeddings.embed_query() ✅, embed_documents() ✅
   - Remaining: async methods, RecordingChatModel updates
   - Output: YAML with correlation_id field

### 🔄 In Progress

4. **recording_wrapper.py** - Complete remaining methods
   - `aembed_documents()` - Add dual logging
   - `aembed_query()` - Add dual logging
   - `RecordingChatModel._generate()` - Add dual logging
   - `RecordingChatModel._save_fixture()` - Add correlation_id

5. **dependencies.py** - Integration
   - Update `get_embeddings_provider()` to use httpx transport
   - Update `get_chat_provider()` to use httpx transport + callback
   - Configure OpenAI SDK with custom http_client

### ⏳ Pending

6. **Fixture Generation Scripts**
   - `scripts/generate_vision_fixtures.py` - Chunk and embed vision.md
   - `scripts/generate_chat_fixtures.py` - Generate 30 conversation scenarios

7. **Test Suites**
   - `tests/integration/test_rag_vector_search.py` - 55 embedding tests
   - `tests/integration/test_chat_workflows.py` - 30 chat workflow tests

8. **Analysis Tools**
   - `scripts/analyze_fixtures_correlation.py` - Correlate all 3 layers
   - `scripts/analyze_api_costs.py` - Cost breakdown per fixture

---

## Correlation ID System

Every API call gets a unique correlation_id that links all 3 layers:

### Example Correlation Flow

```
correlation_id: emb_a3f8c9d2_12ab34cd

Layer 1: langchain_calls/embeddings/emb_a3f8c9d2_12ab34cd.json
{
  "correlation_id": "emb_a3f8c9d2_12ab34cd",
  "layer": "langchain_abstraction",
  "langchain_input": {
    "text": "This is a test",
    "model": "text-embedding-3-small"
  },
  "langchain_output": {
    "vector": [0.1, 0.2, ...],
    "dimension": 1536
  }
}

Layer 2: embeddings.yaml
embeddings:
  - key: a3f8c9d2
    correlation_id: emb_a3f8c9d2_12ab34cd  ← Links to layers 1 & 3
    text: "This is a test"
    vector: [0.1, 0.2, ...]

Layer 3: raw_api/embeddings/emb_a3f8c9d2_12ab34cd.json
{
  "correlation_id": "emb_a3f8c9d2_12ab34cd",
  "layer": "raw_openai_api",
  "request": {
    "method": "POST",
    "url": "https://api.openai.com/v1/embeddings",
    "body": {"input": "This is a test", "model": "text-embedding-3-small"}
  },
  "response": {
    "status_code": 200,
    "body": {
      "data": [{"embedding": [0.1, 0.2, ...]}],
      "usage": {"prompt_tokens": 5, "total_tokens": 5}
    }
  },
  "metadata": {
    "cost_usd": 0.0000001,
    "duration_ms": 145.3
  }
}
```

---

## File Structure

```
tests/fixtures/mock_adapters/
├── embeddings.yaml                       # Layer 2 (simplified fixtures)
│   └── embeddings:
│       ├── correlation_id: emb_xxx       # Links to layers 1 & 3
│       ├── text: "..."
│       └── vector: [...]
│
├── chat.yaml                             # Layer 2 (simplified fixtures)
│   └── completions:
│       ├── correlation_id: chat_xxx      # Links to layers 1 & 3
│       ├── prompt: "..."
│       └── response: "..."
│
├── langchain_calls/                      # Layer 1 (LangChain abstraction)
│   ├── embeddings/
│   │   ├── emb_xxx_yyy.json
│   │   └── emb_zzz_www.json
│   └── chat/
│       ├── chat_xxx_yyy.json
│       └── chat_zzz_www.json
│
├── raw_api/                              # Layer 3 (Raw OpenAI HTTP)
│   ├── embeddings/
│   │   ├── emb_xxx_yyy.json
│   │   └── emb_zzz_www.json
│   └── chat/
│       ├── chat_xxx_yyy.json
│       └── chat_zzz_www.json
│
└── documents/
    └── vision.md                         # Test document source
```

---

## Usage

### Recording Mode (Capture All 3 Layers)

```bash
# Enable recording
export RECORD_FIXTURES=true
export RECORD_FIXTURES_PATH=tests/fixtures/mock_adapters

# Run code that calls OpenAI API
python scripts/generate_vision_fixtures.py

# Result: 3 files created per API call
# - langchain_calls/<type>/<id>.json  (Layer 1)
# - <type>.yaml (Layer 2, with correlation_id)
# - raw_api/<type>/<id>.json (Layer 3)
```

### Mock Mode (Use YAML Fixtures Only)

```bash
# Use mocks (no API calls, no logging)
export USE_MOCK_ADAPTERS=true

# Run tests
pytest tests/integration/test_rag_vector_search.py -v

# Result: Fast tests using embeddings.yaml, no API costs
```

### Analysis Mode (Correlate Layers)

```bash
# Analyze correlation between all layers
python scripts/analyze_fixtures_correlation.py

# Output: Shows how each YAML fixture maps to LangChain + raw API logs
# Includes cost analysis, token usage, duration metrics
```

---

## Benefits

### Complete Traceability
- See how LangChain transforms your inputs (Layer 1)
- Get simplified fixtures for fast testing (Layer 2)
- Inspect actual HTTP calls to OpenAI (Layer 3)
- correlation_id links all 3 layers

### Production Debugging
- Compare production logs with test fixtures
- Understand differences between test and production
- Verify fixtures match real API behavior

### Cost Analysis
- Track exact cost per fixture
- Identify expensive operations
- Optimize prompt strategies

### Compliance
- Complete audit trail of all API calls
- Track data sent to third-party APIs
- Support data retention policies

---

## Next Steps

### Immediate Tasks

1. **Complete RecordingChatModel updates**
   - Add dual logging to `_generate()` method
   - Add correlation_id to `_save_fixture()`
   - Add LangChain callback support

2. **Update dependencies.py**
   - Configure httpx transport: `httpx.Client(transport=get_logging_transport())`
   - Add LangChain callback: `callbacks=[get_langchain_logger()]`

3. **Test integration**
   - Create simple test script
   - Verify all 3 layers capture correctly
   - Verify correlation IDs match

### Follow-on Tasks

4. **Create fixture generation scripts**
   - Generate 45 vision.md chunks + embeddings
   - Generate 30 chat workflow scenarios

5. **Create analysis tools**
   - Correlation analyzer
   - Cost calculator
   - Performance analyzer

6. **Generate test suites**
   - 55 embedding tests (RAG scenarios)
   - 30 chat tests (workflow scenarios)

7. **Execute 200 API calls**
   - Record all fixtures
   - Analyze results
   - Generate report

---

## Cost Estimate

### One-Time Recording
- **100 embedding calls**: ~$0.0002
- **100 chat calls**: ~$0.03-0.04
- **Total**: ~$0.03-0.04 USD

### Ongoing Mock Testing
- **Cost**: $0.00 (uses YAML fixtures)
- **Speed**: <1ms per test
- **Benefit**: Unlimited test runs

### ROI
- **Break-even**: After ~3-4 test runs in CI/CD
- **Annual savings**: $100s-$1000s (depending on test frequency)

---

## Configuration

### Environment Variables

```bash
# Recording mode (captures all 3 layers)
RECORD_FIXTURES=true
RECORD_FIXTURES_PATH=tests/fixtures/mock_adapters

# Mock mode (uses YAML only, no API calls)
USE_MOCK_ADAPTERS=true

# Optional: Custom log directories
API_LOG_DIR=tests/fixtures/api_logs              # Layer 3 directory
LANGCHAIN_LOG_DIR=tests/fixtures/langchain_calls # Layer 1 directory
```

---

## Testing Checklist

- [x] Layer 3 (httpx transport) captures raw HTTP
- [x] Layer 1 (callback) captures LangChain abstraction
- [x] Layer 2 (YAML) includes correlation_id
- [ ] RecordingEmbeddings.embed_query() - Complete ✅
- [ ] RecordingEmbeddings.embed_documents() - Complete ✅
- [ ] RecordingEmbeddings.aembed_query() - TODO
- [ ] RecordingEmbeddings.aembed_documents() - TODO
- [ ] RecordingChatModel._generate() - TODO
- [ ] RecordingChatModel._save_fixture() - TODO
- [ ] dependencies.py integration - TODO
- [ ] End-to-end test with all 3 layers - TODO
- [ ] Correlation verification - TODO

---

## Known Issues

None yet - implementation in progress.

---

## References

- **OpenAI Pricing**: https://openai.com/pricing
- **LangChain Callbacks**: https://python.langchain.com/docs/concepts/callbacks/
- **HTTPX Transports**: https://www.python-httpx.org/advanced/#custom-transports

---

**Last Updated**: 2025-10-01
**Status**: Core implementation complete, integration pending
