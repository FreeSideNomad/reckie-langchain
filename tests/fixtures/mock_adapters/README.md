# Mock Adapter Fixtures

This directory contains YAML fixtures for mock LangChain adapters. Fixtures are real API responses recorded from OpenAI that can be replayed without API costs.

## Files

- **`embeddings.yaml`** - Embedding vectors from OpenAI text-embedding-3-small model
- **`chat.yaml`** - Chat completion responses from OpenAI gpt-3.5-turbo model

## Recording New Fixtures

### Method 1: Using Demo Script

```bash
# Enable recording mode
export RECORD_FIXTURES=true
export OPENAI_API_KEY=your-key-here

# Run demo to record common scenarios
python scripts/demo-recording.py
```

### Method 2: During Normal Development/Testing

```bash
# Enable recording mode
export RECORD_FIXTURES=true
export OPENAI_API_KEY=your-key-here

# Run your code - responses are automatically recorded
python your_script.py

# Or run tests (they'll use real API and record responses)
pytest tests/integration/
```

### Method 3: In Production (Logging Mode)

```python
# In your config/settings
RECORD_FIXTURES = os.getenv("RECORD_FIXTURES", "false") == "true"

# Responses are automatically logged when enabled
# Useful for debugging, monitoring, or capturing edge cases
```

## Using Fixtures (Mock Mode)

```bash
# Enable mock mode (no API calls)
export USE_MOCK_ADAPTERS=true

# Run tests - uses fixtures from this directory
pytest tests/

# No OPENAI_API_KEY needed!
```

## Fixture Format

### Embeddings

```yaml
embeddings:
  - key: "4908f158"  # MD5 hash of text (first 8 chars)
    text: "This is a test document"
    vector: [0.1, 0.2, 0.3, ...]  # 1536 dimensions
    dimension: 1536
    recorded_at: "2025-10-01T15:00:00"

metadata:
  total_count: 10
  last_updated: "2025-10-01T15:00:00"
```

### Chat

```yaml
completions:
  - key: "71de34ec"  # MD5 hash of prompt (first 8 chars)
    prompt: "Say hello"
    response: "Hello! How can I help you today?"
    recorded_at: "2025-10-01T15:00:00"

metadata:
  total_count: 10
  last_updated: "2025-10-01T15:00:00"
```

## Configuration Matrix

| USE_MOCK_ADAPTERS | RECORD_FIXTURES | Behavior |
|-------------------|-----------------|----------|
| `false` | `false` | Real OpenAI API (production) |
| `false` | `true` | Real API + record to fixtures |
| `true` | `false` | Mock adapters (CI/CD, local testing) |
| `true` | `true` | Mock adapters (RECORD_FIXTURES ignored) |

## Fixture Maintenance

### When to Update Fixtures

- **API changes**: When OpenAI updates models or response formats
- **New scenarios**: When adding new test cases
- **Quality issues**: If fixture responses are outdated or incorrect
- **Quarterly**: Scheduled refresh to keep responses realistic

### How to Update

```bash
# Delete old fixtures
rm embeddings.yaml chat.yaml

# Record fresh data
export RECORD_FIXTURES=true
python scripts/demo-recording.py
```

### Best Practices

1. **Keep fixtures small**: Only record scenarios you actually test
2. **Commit fixtures to git**: They're small (<1MB) and essential for tests
3. **Review before committing**: Check for sensitive data or API keys
4. **Document scenarios**: Add comments to fixtures explaining each scenario
5. **Use recording mode sparingly**: Only when needed (costs API usage)

## Cost Estimation

Recording fixtures costs real API usage:

- **Embeddings**: $0.00002 per 1K tokens (text-embedding-3-small)
- **Chat**: $0.0005 per 1K input tokens, $0.0015 per 1K output (gpt-3.5-turbo)

Example:
- 10 embeddings (average 50 tokens each) = ~$0.00001
- 10 chat completions (100 tokens each) = ~$0.01
- **Total for demo script**: ~$0.01-$0.10

## Security Notes

⚠️ **Important**: Fixtures are committed to git and visible in the repository.

**Do NOT record**:
- API keys or secrets
- Personally identifiable information (PII)
- Confidential business data
- Production customer data

The recording wrapper automatically redacts some sensitive data, but always review fixtures before committing.

## Troubleshooting

### "Fixture not found" Error

**Problem**: Mock adapter can't find fixture for a test scenario

**Solution**: Either:
1. Add the scenario to fixtures (record it)
2. Use the hash-based fallback (automatic)
3. Use real API for that test (disable mock mode)

### Recording Not Working

**Check**:
```bash
# Is recording enabled?
echo $RECORD_FIXTURES  # Should be "true"

# Is API key set?
echo $OPENAI_API_KEY  # Should be your key

# Is mock mode disabled?
echo $USE_MOCK_ADAPTERS  # Should be "false" or unset
```

### Fixtures Are Stale

If API responses have changed:

```bash
# Delete old fixtures
rm embeddings.yaml chat.yaml

# Record fresh
export RECORD_FIXTURES=true
python scripts/demo-recording.py
```

## See Also

- [Mock Adapters Implementation](../../../src/testing/mock_adapters/)
- [Recording Wrapper](../../../src/testing/mock_adapters/recording_wrapper.py)
- [Dependency Injection](../../../src/api/dependencies.py)
- [Demo Script](../../../scripts/demo-recording.py)

---

**Last Updated**: 2025-10-01
**Fixture Version**: 1.0
