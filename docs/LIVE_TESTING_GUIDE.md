# Live AI Testing Guide

This guide provides comprehensive documentation for the live AI testing infrastructure implemented in the Blackcore minimal module.

## Overview

The live AI testing system validates semantic accuracy of entity extraction from real transcripts using actual API calls to AI providers. It includes structured test scenarios, comprehensive validation metrics, cost controls, and safety mechanisms.

## Architecture

### Core Components

```
blackcore/minimal/tests/live/
├── transcript_library.py          # Structured test scenarios with expected outcomes
├── config.py                     # Configuration and cost tracking
├── conftest.py                   # Test fixtures and safety mechanisms  
├── test_live_ai_extraction.py    # Live API validation tests
├── run_transcript_library_tests.py # Dedicated test runner
├── run_live_tests.py             # General live test runner
├── .env.example                  # Configuration template
└── README.md                     # Documentation
```

### Test Scenarios

The system includes 4 comprehensive test scenarios:

1. **Simple Meeting** (`simple_meeting`)
   - **Category**: Meeting
   - **Content**: Q4 strategy session with attendees, discussion points, action items
   - **Expected Entities**: 6+ entities (people, organization, tasks, place)
   - **Validation Focus**: Basic entity extraction accuracy

2. **Security Incident** (`security_incident`)
   - **Category**: Security Incident  
   - **Content**: Database breach report with timeline, response team, actions
   - **Expected Entities**: 6+ entities including transgressions, people, tasks, places
   - **Validation Focus**: Transgression detection and security response mapping

3. **Multi-Organization Partnership** (`multi_org_partnership`)
   - **Category**: Partnership
   - **Content**: Three-way partnership agreement with complex relationships
   - **Expected Entities**: 8+ entities across organizations, people, places, tasks
   - **Validation Focus**: Complex relationship extraction and multi-org handling

4. **Board Meeting** (`board_meeting`)
   - **Category**: Board Meeting
   - **Content**: Board decisions on hiring, budget, acquisitions
   - **Expected Entities**: 6+ entities including people, organizations, tasks
   - **Validation Focus**: Decision extraction and governance actions

## Validation Framework

### Metrics

Each test scenario is validated using comprehensive metrics:

- **Entity Coverage**: Percentage of required entities found (threshold: 80%)
- **Type Accuracy**: Percentage of entities with correct types (threshold: 90%)
- **Name Accuracy**: Percentage of entities with acceptable names (threshold: 70%)
- **Overall Score**: Composite score across all metrics

### Expected Entity Structure

```python
@dataclass
class ExpectedEntity:
    name: str                           # Primary entity name
    type: EntityType                    # Required entity type
    required_properties: Dict[str, Any] # Must-have properties
    optional_properties: Dict[str, Any] # Nice-to-have properties  
    name_variations: List[str]          # Alternative acceptable names
```

### Validation Logic

```python
def validate_extraction(actual: ExtractedEntities, expected: ExpectedExtractionOutcome) -> Dict[str, Any]:
    """
    Returns:
    - overall_score: Composite validation score (0.0-1.0)
    - entity_coverage: Required entities found / total required
    - type_accuracy: Entities with correct types / total entities
    - name_accuracy: Entities with acceptable names / total entities
    - passed: Boolean pass/fail based on thresholds
    """
```

## Configuration

### Environment Variables

```bash
# Feature flags
ENABLE_LIVE_AI_TESTS=true              # Enable live AI tests
ENABLE_LIVE_NOTION_TESTS=false         # Enable live Notion tests (future)

# API keys (use separate test keys, NOT production)
LIVE_TEST_AI_API_KEY=your-test-key     # Anthropic API key for testing
LIVE_TEST_NOTION_API_KEY=your-notion-key # Notion API key for testing

# Cost controls
LIVE_TEST_SPEND_LIMIT=10.00            # USD spending limit per session
LIVE_TEST_MAX_AI_CALLS=50              # Maximum AI calls per session

# Test environment
LIVE_TEST_NOTION_WORKSPACE=workspace-id # Dedicated test workspace
LIVE_TEST_DATA_PREFIX=LIVETEST_         # Prefix for test data isolation
LIVE_TEST_API_TIMEOUT=30.0             # API timeout in seconds
LIVE_TEST_MAX_RETRIES=3                # Maximum retries for failed calls
```

### Configuration Setup

1. **Copy configuration template:**
   ```bash
   cp blackcore/minimal/tests/live/.env.example blackcore/minimal/tests/live/.env
   ```

2. **Edit configuration:**
   ```bash
   # Enable tests
   ENABLE_LIVE_AI_TESTS=true
   
   # Add test API key (NOT production key)
   LIVE_TEST_AI_API_KEY=sk-ant-api03-your-test-key-here
   
   # Set conservative cost limits
   LIVE_TEST_SPEND_LIMIT=5.00
   LIVE_TEST_MAX_AI_CALLS=20
   ```

## Safety Mechanisms

### API Key Separation
- **Required**: Use `LIVE_TEST_AI_API_KEY`, never `ANTHROPIC_API_KEY`
- **Protection**: Tests automatically hide production keys during execution
- **Validation**: Tests fail if production keys are accidentally used

### Cost Controls
- **Pre-flight Checks**: Tests estimate costs before making API calls
- **Budget Enforcement**: Tests stop if spending limit would be exceeded
- **Session Reporting**: Detailed cost summary after each test run
- **Token Estimation**: Rough cost calculations based on input/output size

### Auto-Skip Behavior
- **Default State**: Tests are disabled by default (`ENABLE_LIVE_AI_TESTS=false`)
- **Explicit Enablement**: Must explicitly set `ENABLE_LIVE_AI_TESTS=true`
- **Missing Keys**: Tests skip gracefully if API keys not provided
- **Safety First**: Prevents accidental API usage during development

## Running Tests

### Quick Start

```bash
# 1. Enable tests and set API key
export ENABLE_LIVE_AI_TESTS=true
export LIVE_TEST_AI_API_KEY=your-test-key

# 2. Run all transcript library tests
python blackcore/minimal/tests/live/run_transcript_library_tests.py
```

### Test Execution Modes

#### 1. Systematic Validation (Recommended)
Tests all transcript scenarios individually with detailed validation:
```bash
python run_transcript_library_tests.py systematic
```

#### 2. Comprehensive Report
Generates batch analysis with category summaries:
```bash
python run_transcript_library_tests.py report
```

#### 3. Consistency Testing
Tests AI reliability across multiple runs:
```bash
python run_transcript_library_tests.py consistency
```

#### 4. Specific Transcript Tests
Runs original format tests for specific scenarios:
```bash
python run_transcript_library_tests.py specific
```

#### 5. All Tests
Runs complete transcript library validation:
```bash
python run_transcript_library_tests.py all
```

### Direct pytest Usage

```bash
# Run all live tests
pytest blackcore/minimal/tests/live/ -v -s

# Run specific test type
pytest blackcore/minimal/tests/live/ -k "systematic_validation" -v

# Run with custom markers
pytest blackcore/minimal/tests/live/ -v -m "not slow"

# Run single test scenario
pytest blackcore/minimal/tests/live/ -k "simple_meeting" -v
```

## Expected Output

### Successful Test Run

```
✅ Q4 Strategy Session - Live AI Extraction Results:
   - Overall Score: 0.92
   - Entity Coverage: 1.00 (6/6)
   - Type Accuracy: 1.00
   - Name Accuracy: 0.83
   - Entity Count Valid: True
   - Required Types Found: {person, organization, task, place}
   ✅ Found required entity: John Smith (person)
   ✅ Found required entity: Sarah Johnson (person)
   ✅ Found required entity: Mike Chen (person)
   ✅ Found required entity: Acme Corporation (organization)
   ✅ Found required entity: sales forecast (task)
   ✅ Found required entity: technical feasibility study (task)

Live AI Test Cost Summary: $0.023 / $10.00 (0.2%) - 1 calls
```

### Session Summary

```
================================================================================
LIVE TEST SESSION SUMMARY
================================================================================
Total estimated cost: $0.847
Budget limit: $10.00
Budget used: 8.5%
AI calls made: 12
Remaining budget: $9.153
================================================================================
```

### Comprehensive Report

```
🔍 Comprehensive Transcript Library Validation
================================================================================
Q4 Strategy Session                 | Score: 0.92 | ✅
Database Breach Incident           | Score: 0.88 | ✅
Three-Way Partnership Agreement    | Score: 0.85 | ✅
Board Meeting with Key Decisions   | Score: 0.90 | ✅
================================================================================
MEETING              | 1/1 passed | Avg Score: 0.92 | Avg Coverage: 1.00
SECURITY_INCIDENT    | 1/1 passed | Avg Score: 0.88 | Avg Coverage: 0.83
PARTNERSHIP          | 1/1 passed | Avg Score: 0.85 | Avg Coverage: 0.88
BOARD_MEETING        | 1/1 passed | Avg Score: 0.90 | Avg Coverage: 0.92
================================================================================
OVERALL SUMMARY      | 4/4 passed | Avg Score: 0.89 | Avg Coverage: 0.91
================================================================================
```

## Cost Management

### Expected Costs

Using Claude Haiku (cost-effective model):
- **Per Test**: ~$0.01-0.05
- **Full Library**: ~$0.20-0.40 (4 scenarios)
- **Consistency Testing**: ~$0.15-0.30 (3 runs × 1 scenario)
- **Comprehensive Report**: ~$0.20-0.40 (all scenarios)

### Cost Optimization

1. **Model Selection**: Uses Claude Haiku by default (most cost-effective)
2. **Token Limits**: Restricts max tokens to control output costs
3. **Conservative Temperature**: Uses low temperature (0.1) for consistent results
4. **Batch Efficiency**: Processes multiple tests in single session

### Budget Monitoring

```python
# Real-time cost tracking
if not cost_tracker.can_make_call(input_tokens, estimated_output_tokens):
    pytest.fail(f"Would exceed cost limit. Current: ${cost_tracker.estimated_cost}")

# Post-test reporting  
cost_tracker.record_ai_call(input_tokens, actual_output_tokens)
summary = cost_tracker.get_summary()
```

## Troubleshooting

### Common Issues

1. **Tests Skipped**
   ```
   Error: "Live AI tests disabled"
   Solution: Set ENABLE_LIVE_AI_TESTS=true
   ```

2. **Cost Limit Exceeded**
   ```
   Error: "Would exceed cost limit"
   Solution: Increase LIVE_TEST_SPEND_LIMIT or reduce test scope
   ```

3. **API Timeout**
   ```
   Error: "API timeout"
   Solution: Increase LIVE_TEST_API_TIMEOUT or check network connectivity
   ```

4. **Inconsistent Results**
   ```
   Issue: AI models have inherent variability
   Solution: Run consistency tests to validate acceptable variation
   ```

### Debug Mode

```bash
# Run with maximum verbosity
pytest blackcore/minimal/tests/live/ -v -s --tb=long

# Enable debug logging
LIVE_TEST_DEBUG=true python run_transcript_library_tests.py
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Live AI Tests
on:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  live-ai-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Only on scheduled runs
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest
        
    - name: Run Live AI Tests
      env:
        ENABLE_LIVE_AI_TESTS: true
        LIVE_TEST_AI_API_KEY: ${{ secrets.LIVE_TEST_AI_API_KEY }}
        LIVE_TEST_SPEND_LIMIT: 2.00
        LIVE_TEST_MAX_AI_CALLS: 10
      run: |
        python blackcore/minimal/tests/live/run_transcript_library_tests.py report
```

### Monitoring Integration

```bash
# OpenTelemetry tracing
OTEL_EXPORTER_OTLP_ENDPOINT=your-endpoint python run_transcript_library_tests.py

# Custom metrics collection
LIVE_TEST_METRICS_ENDPOINT=your-metrics-url python run_transcript_library_tests.py
```

## Best Practices

### Development Workflow

1. **Start Small**: Test individual scenarios before running full suite
2. **Monitor Costs**: Check session summaries and set appropriate limits
3. **Use Dedicated Keys**: Never test with production API credentials
4. **Version Control**: Track validation scores over time for regression detection
5. **Review Results**: Examine AI extraction quality, not just pass/fail status

### Quality Assurance

1. **Baseline Establishment**: Run tests multiple times to establish expected score ranges
2. **Regression Testing**: Compare current scores against historical baselines
3. **Threshold Tuning**: Adjust quality thresholds based on model capabilities
4. **Scenario Expansion**: Add new test scenarios as system capabilities grow

### Production Readiness

1. **Validation Pipeline**: Integrate live tests into CI/CD for model validation
2. **Performance Monitoring**: Track extraction accuracy trends over time
3. **Cost Optimization**: Monitor spending patterns and optimize test frequency
4. **Alert Configuration**: Set up alerts for validation score degradation

## Implementation Details

### Test Library Architecture

```python
class TestTranscriptLibrary:
    """Library of test transcripts for entity extraction validation."""
    
    def get_transcript(self, transcript_id: str) -> Optional[TestTranscript]
    def get_transcripts_by_category(self, category: TranscriptCategory) -> List[TestTranscript]
    def get_all_transcripts(self) -> List[TestTranscript]
    def get_transcripts_by_tags(self, tags: List[str]) -> List[TestTranscript]
```

### Validation Framework

```python
class ExtractionResultValidator:
    """Validates entity extraction results against expected outcomes."""
    
    @staticmethod
    def validate_extraction(
        actual: ExtractedEntities,
        expected: ExpectedExtractionOutcome
    ) -> Dict[str, Any]
```

### Cost Tracking

```python
class CostTracker:
    """Tracks and limits API call costs during testing."""
    
    def estimate_ai_call_cost(self, input_tokens: int, output_tokens: int) -> Decimal
    def can_make_call(self, input_tokens: int, output_tokens: int) -> bool
    def record_ai_call(self, input_tokens: int, output_tokens: int) -> bool
    def get_summary(self) -> Dict[str, Any]
```

## Future Enhancements

### Planned Features

1. **Historical Tracking**: Store validation results over time for trend analysis
2. **Advanced Scoring**: More sophisticated validation metrics beyond coverage/accuracy
3. **Notion Integration**: Live testing with real Notion workspace operations
4. **Model Comparison**: Test multiple AI providers/models simultaneously
5. **Custom Scenarios**: User-defined test scenarios with expected outcomes

### Extensibility

```python
# Add new test scenarios
def add_custom_scenario(library: TestTranscriptLibrary, scenario: TestTranscript):
    library._transcripts[scenario.id] = scenario

# Custom validation metrics
def add_custom_validator(validator: ExtractionResultValidator, metric_fn):
    validator.custom_metrics.append(metric_fn)

# Extended cost tracking
def add_cost_provider(tracker: CostTracker, provider: str, pricing: Dict):
    tracker.provider_pricing[provider] = pricing
```

This comprehensive testing infrastructure provides robust validation of AI entity extraction semantic accuracy with full cost controls and safety mechanisms.