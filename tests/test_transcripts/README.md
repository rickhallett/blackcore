# Blackcore Entity Extraction Test Suite

This directory contains mock transcripts designed to comprehensively test the Blackcore framework's ability to identify, extract, and store entities from intelligence transcripts.

## Test Transcripts

### 1. **test_transcript_council_meeting.json**
- **Focus**: Council meeting dynamics, existing entities, transgressions
- **Key Tests**: 
  - Entity variation handling (STC → Swanage Town Council)
  - Purdah violation detection
  - Relationship extraction between council members

### 2. **test_transcript_strategy_call.json**
- **Focus**: Task creation, assignment tracking, campaign planning
- **Key Tests**:
  - Task extraction with assignees and deadlines
  - New organization creation
  - Complex organizational relationships (subsidiaries)

### 3. **test_transcript_field_report.json**
- **Focus**: Canvassing data, location mapping, sentiment analysis
- **Key Tests**:
  - Address-to-person mapping
  - Sentiment classification (supporter/opposition)
  - Informal speech parsing with multiple speakers

### 4. **test_transcript_email_investigation.json**
- **Focus**: Evidence documentation, temporal sequencing, deception detection
- **Key Tests**:
  - Email metadata extraction
  - Timeline construction from communications
  - Transgression evidence linking

### 5. **test_transcript_complex_scenario.json**
- **Focus**: Stress test with abbreviations, pronouns, complex relationships
- **Key Tests**:
  - Abbreviation resolution (DCC, STC, NS1/NS2)
  - Speaker disambiguation
  - Financial data extraction
  - Entity role evolution

## Running Tests

### Run all tests:
```bash
python test_transcript_runner.py
```

### Test specific transcript:
```bash
python test_transcript_runner.py --transcript test_council_001
```

### Verbose output:
```bash
python test_transcript_runner.py --verbose
```

## Expected Output

The test runner will:
1. Load each test transcript
2. Extract entities using the Blackcore framework
3. Compare against expected entities
4. Report accuracy metrics and missing/unexpected entities

### Success Criteria:
- ✅ 80%+ accuracy: Excellent extraction
- ⚠️  60-79% accuracy: Needs improvement
- ❌ <60% accuracy: Significant issues

## Test Data Structure

Each test transcript contains:
- **metadata**: Recording details and participants
- **content**: The actual transcript text
- **expected_entities**: What should be extracted
- **test_scenarios**: Specific edge cases being tested

## Adding New Tests

To add a new test transcript:
1. Create a new JSON file: `test_transcript_[scenario].json`
2. Follow the existing structure
3. Include diverse entity types and relationships
4. Document specific test scenarios
5. Run the test to establish baseline

## Integration with CI/CD

These tests can be integrated into the CI/CD pipeline:
```bash
# In your CI configuration
pytest tests/test_transcripts/test_transcript_runner.py
```

## Known Limitations

- The test runner currently operates in dry_run mode
- Some complex relationship extractions may require AI model configuration
- Financial data extraction requires specific patterns in the transcript text

## Future Enhancements

1. Add performance benchmarking
2. Test entity deduplication
3. Validate relationship directionality
4. Test incremental entity updates
5. Add multi-language transcript tests