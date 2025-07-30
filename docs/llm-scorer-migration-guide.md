# LLM Scorer Migration Guide

This guide walks through migrating from the simple rule-based deduplication to the LLM-based intelligent deduplication system.

## Overview

The LLM-based scorer replaces hardcoded nickname mappings and string normalization with Claude 3.5 Haiku's intelligent entity matching. This provides more accurate deduplication with less maintenance.

## Migration Steps

### 1. Update Dependencies

First, ensure you have the anthropic package installed:

```bash
# Using uv
uv sync

# Or using pip
pip install anthropic>=0.25.0
```

### 2. Configure LLM Scorer

Update your configuration to enable the LLM scorer:

#### Option A: Using config.json

```json
{
  "processing": {
    "deduplication_scorer": "llm",
    "llm_scorer_config": {
      "model": "claude-3-5-haiku-20241022",
      "temperature": 0.1,
      "cache_ttl": 3600,
      "batch_size": 5
    }
  }
}
```

#### Option B: Using environment variables

```bash
# In your .env file
ANTHROPIC_API_KEY=your-api-key-here
```

#### Option C: Programmatic configuration

```python
from blackcore.minimal.models import Config, ProcessingConfig

config = Config(
    processing=ProcessingConfig(
        deduplication_scorer="llm",
        llm_scorer_config={
            "model": "claude-3-5-haiku-20241022",
            "temperature": 0.1,
            "cache_ttl": 3600,
            "batch_size": 5
        }
    )
)
```

### 3. Test the Migration

Run a test to ensure the LLM scorer is working:

```python
from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput

# Create processor with LLM scorer
processor = TranscriptProcessor()

# Process a test transcript
transcript = TranscriptInput(
    title="Test Meeting",
    content="Tony Smith and Anthony Smith discussed the project..."
)

result = processor.process_transcript(transcript)
```

You should see output indicating the LLM scorer is being used:
```
Using LLM scorer (Claude 3.5 Haiku) with simple scorer fallback
```

### 4. Gradual Rollout

For production environments, we recommend a gradual rollout:

1. **A/B Testing**: Run both scorers in parallel and compare results
2. **Monitoring**: Track deduplication accuracy and API costs
3. **Incremental adoption**: Start with less critical entity types

Example A/B testing setup:

```python
# Run both scorers and compare
simple_scorer = SimpleScorer()
llm_scorer = LLMScorer(api_key=config.ai.api_key)

# Compare results
simple_score, simple_reason = simple_scorer.score_entities(entity1, entity2)
llm_score, llm_reason, llm_details = llm_scorer.score_entities(entity1, entity2)

# Log differences for analysis
if abs(simple_score - llm_score) > 20:
    log.info(f"Score difference: Simple={simple_score}, LLM={llm_score}")
```

## Cost Considerations

### Pricing

Claude 3.5 Haiku pricing (as of 2024):
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens

### Estimated Costs

- Average entity comparison: ~500 tokens
- Cost per comparison: ~$0.0003
- 1000 entities/day: ~$0.30/day

### Cost Optimization

1. **Caching**: Results are cached for 1 hour by default
2. **Batching**: Process up to 5 comparisons per API call
3. **Selective use**: Only use for high-value deduplication

## Monitoring and Debugging

### Enable Verbose Logging

```python
config.processing.verbose = True
```

### Check Cache Statistics

```python
scorer = processor.scorer
if hasattr(scorer, 'get_cache_stats'):
    stats = scorer.get_cache_stats()
    print(f"Cache entries: {stats['entries']}")
```

### Monitor API Errors

The LLM scorer automatically falls back to simple scoring on errors:

```python
# Check if fallback was used
if details.get("fallback"):
    print(f"Fallback used: {details.get('error')}")
```

## Rollback Plan

If you need to rollback to simple scoring:

1. Update configuration:
   ```json
   {
     "processing": {
       "deduplication_scorer": "simple"
     }
   }
   ```

2. Or set programmatically:
   ```python
   config.processing.deduplication_scorer = "simple"
   ```

The system will immediately switch back to rule-based scoring.

## Advanced Configuration

### Custom Models

Use different Claude models:

```json
{
  "llm_scorer_config": {
    "model": "claude-3-5-sonnet-20241022"  // More capable but costlier
  }
}
```

### Adjust Temperature

Lower temperature for more consistent results:

```json
{
  "llm_scorer_config": {
    "temperature": 0.0  // Most deterministic
  }
}
```

### Custom Cache TTL

Longer cache for stable data:

```json
{
  "llm_scorer_config": {
    "cache_ttl": 7200  // 2 hours
  }
}
```

## Troubleshooting

### Issue: LLM scorer not being used

Check:
1. API key is set correctly
2. Configuration specifies `"deduplication_scorer": "llm"`
3. No import errors for anthropic package

### Issue: High API costs

Solutions:
1. Increase cache TTL
2. Increase batch size
3. Use simple scorer for low-value entities

### Issue: Slower performance

Solutions:
1. Enable batching
2. Use async processing (future enhancement)
3. Pre-warm cache with common entities

## Best Practices

1. **Start with high-value entities**: People and Organizations benefit most
2. **Monitor costs daily**: Set up billing alerts
3. **Review edge cases**: Collect examples where LLM excels
4. **Maintain fallback**: Always have simple scorer as backup
5. **Cache warming**: Pre-process known duplicates

## Future Enhancements

Planned improvements:
- Multi-model support (GPT-4o-mini)
- Async processing
- Confidence calibration
- User feedback integration
- Bulk processing mode