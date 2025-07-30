# Live API Integration Tests

This directory contains live integration tests that make actual API calls to external services (AI providers, Notion, etc.). These tests validate semantic accuracy and real-world behavior that cannot be captured by mocked tests.

## ⚠️ Important Notes

- **Cost Impact**: These tests use real API calls and will incur actual costs
- **Separate API Keys**: Use dedicated test API keys, not production keys
- **Rate Limiting**: Tests are designed to be respectful of API rate limits
- **Selective Running**: Only run when you need to validate core functionality

## Quick Start

1. **Set up test API keys** (separate from production):
   ```bash
   export LIVE_TEST_AI_API_KEY="your-test-anthropic-key"
   export LIVE_TEST_NOTION_API_KEY="your-test-notion-key"  # Optional
   ```

2. **Enable live AI tests**:
   ```bash  
   export ENABLE_LIVE_AI_TESTS=true
   ```

3. **Set spending limits** (optional):
   ```bash
   export LIVE_TEST_SPEND_LIMIT=5.00  # USD limit per test run
   export LIVE_TEST_MAX_AI_CALLS=20   # Maximum AI calls per run
   ```

4. **Run the tests**:
   ```bash
   pytest tests/live/ -v
   ```

## Configuration

All configuration is done via environment variables:

### Feature Flags
- `ENABLE_LIVE_AI_TESTS=true` - Enable live AI entity extraction tests
- `ENABLE_LIVE_NOTION_TESTS=true` - Enable live Notion API tests (future)

### API Keys (Separate from Production)
- `LIVE_TEST_AI_API_KEY` - Anthropic/Claude API key for testing
- `LIVE_TEST_NOTION_API_KEY` - Notion API key for testing workspace

### Cost Controls
- `LIVE_TEST_SPEND_LIMIT=10.00` - USD spending limit per test run (default: $10)
- `LIVE_TEST_MAX_AI_CALLS=50` - Maximum AI API calls per run (default: 50)

### Test Environment  
- `LIVE_TEST_NOTION_WORKSPACE` - Dedicated Notion workspace ID for testing
- `LIVE_TEST_DATA_PREFIX=LIVETEST_` - Prefix for test data (default: LIVETEST_)
- `LIVE_TEST_API_TIMEOUT=30.0` - API timeout in seconds (default: 30)

## Test Categories

### AI Entity Extraction Tests (`test_live_ai_extraction.py`)
- **Purpose**: Validate semantic accuracy of entity extraction from real transcripts
- **Cost**: ~$0.01-0.05 per test (using Claude Haiku)
- **What's Tested**:
  - Correct entity identification (people, organizations, tasks, etc.)
  - Property extraction accuracy
  - Relationship detection
  - Consistency across multiple runs

### Structured Transcript Library (`transcript_library.py`)
- **Purpose**: Systematic validation using predefined test cases with expected outcomes
- **Features**:
  - Structured test transcripts with expected entity extraction results
  - Comprehensive validation metrics (coverage, accuracy, scoring)
  - Category-specific test scenarios (meetings, security incidents, partnerships, etc.)
  - Automated quality thresholds and pass/fail criteria

### Test Scenarios
1. **Simple Meeting** (`simple_meeting`) - Basic meeting with clear entities and action items
2. **Security Incident** (`security_incident`) - Security breach with transgressions and response actions
3. **Multi-Organization Partnership** (`multi_org_partnership`) - Complex partnership with relationships
4. **Board Meeting** (`board_meeting`) - Decision-making meeting with approvals and tasks

### Validation Metrics
- **Entity Coverage**: Percentage of required entities found (threshold: 80%)
- **Type Accuracy**: Percentage of entities with correct types (threshold: 90%)
- **Name Accuracy**: Percentage of entities with acceptable names (threshold: 70%)
- **Overall Score**: Composite score across all metrics

## Cost Management

The system includes built-in cost tracking and limits:

- **Pre-flight checks**: Tests estimate costs before making calls
- **Budget enforcement**: Tests stop if spending limit would be exceeded  
- **Session reporting**: Detailed cost summary after each test run
- **Token estimation**: Rough cost calculations based on input/output size

### Sample Cost Report
```
LIVE TEST SESSION SUMMARY
=====================================
Total estimated cost: $0.847
Budget limit: $10.00
Budget used: 8.5%
AI calls made: 12
Remaining budget: $9.153
=====================================
```

## Safety Features

1. **Separate API Keys**: Never uses production `ANTHROPIC_API_KEY` or `NOTION_API_KEY`
2. **Auto-Skip**: Tests automatically skip if not explicitly enabled
3. **Budget Limits**: Hard stops prevent runaway spending
4. **Test Data Isolation**: Uses prefixed test data to avoid production contamination
5. **Conservative Models**: Uses cost-effective models (Claude Haiku) for testing

## Running Specific Tests

### Basic Test Execution
```bash
# Run only AI extraction tests
pytest tests/live/test_live_ai_extraction.py -v

# Run a specific test method
pytest tests/live/test_live_ai_extraction.py::TestLiveAIEntityExtraction::test_simple_meeting_transcript_ai_extraction -v

# Run with increased verbosity and cost reporting
pytest tests/live/ -v -s

# Skip slow tests
pytest tests/live/ -v -m "not slow"
```

### Transcript Library Testing (Recommended)
```bash
# Use the dedicated transcript library test runner
python run_transcript_library_tests.py

# Or run specific transcript library test modes:
python run_transcript_library_tests.py systematic  # Test all transcripts individually
python run_transcript_library_tests.py report     # Generate comprehensive validation report
python run_transcript_library_tests.py specific   # Run original format tests
python run_transcript_library_tests.py consistency # Test AI consistency
python run_transcript_library_tests.py all        # Run all transcript tests

# Run systematic validation for all transcript types
pytest tests/live/ -k "test_transcript_library_systematic_validation" -v

# Generate comprehensive validation report
pytest tests/live/ -k "test_transcript_library_comprehensive_report" -v -s
```

## CI/CD Integration

For automated testing environments:

```yaml
# Example GitHub Actions integration
- name: Run Live AI Tests (Nightly)
  env:
    ENABLE_LIVE_AI_TESTS: true
    LIVE_TEST_AI_API_KEY: ${{ secrets.LIVE_TEST_AI_API_KEY }}
    LIVE_TEST_SPEND_LIMIT: 2.00
    LIVE_TEST_MAX_AI_CALLS: 10
  run: pytest tests/live/ -v
  if: github.event_name == 'schedule'  # Only on scheduled runs
```

## Troubleshooting

### Tests are skipped
- Check that `ENABLE_LIVE_AI_TESTS=true` is set
- Verify API keys are provided and valid

### "Would exceed cost limit" errors
- Increase `LIVE_TEST_SPEND_LIMIT` 
- Reduce test scope or use fewer test cases

### API timeout errors
- Increase `LIVE_TEST_API_TIMEOUT`
- Check network connectivity to API endpoints

### Inconsistent results
- AI models have some inherent variability
- Consider running consistency tests to validate acceptable variation

## Best Practices

1. **Run sparingly**: Live tests are for validation, not regular development
2. **Monitor costs**: Check session summaries and set appropriate limits
3. **Use dedicated keys**: Never test with production API credentials
4. **Test incrementally**: Start with single tests before running full suite
5. **Review results**: Examine AI extraction quality, not just pass/fail status

## Future Enhancements

- Live Notion API testing (currently deferred)
- Automated quality scoring for entity extraction  
- Historical performance tracking
- Integration with monitoring systems
- Support for additional AI providers