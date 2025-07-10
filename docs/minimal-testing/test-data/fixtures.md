# Test Fixtures Documentation

## Overview

This document describes the test fixtures available for testing the minimal module. These fixtures provide consistent, reusable test data for various scenarios.

## Transcript Fixtures

Located in: `blackcore/minimal/tests/fixtures/transcript_fixtures.py`

### Available Fixtures:

1. **SIMPLE_TRANSCRIPT**
   - Basic transcript with a few entities
   - Contains: 1 person, 1 organization, 1 project
   - Use for: Basic flow testing

2. **COMPLEX_TRANSCRIPT**
   - Board meeting transcript with multiple entities
   - Contains: 3 people, 1 organization, multiple tasks, 1 event, 1 transgression
   - Use for: Relationship testing, complex extraction

3. **EMPTY_TRANSCRIPT**
   - Transcript with empty content
   - Use for: Edge case testing, error handling

4. **LARGE_TRANSCRIPT**
   - Very long transcript (~30KB)
   - Use for: Performance testing, pagination

5. **SPECIAL_CHARS_TRANSCRIPT**
   - Contains unicode, special characters, injection attempts
   - Use for: Security testing, encoding issues

6. **ERROR_TRANSCRIPT**
   - Designed to trigger validation errors
   - Use for: Error handling tests

7. **BATCH_TRANSCRIPTS**
   - List of 10 simple transcripts
   - Use for: Batch processing tests

## Notion Response Fixtures

Located in: `blackcore/minimal/tests/fixtures/notion_fixtures.py`

### Page Responses:
- `NOTION_PAGE_RESPONSE` - Standard page creation response
- `DATABASE_SCHEMA_RESPONSE` - Database schema with various property types
- `SEARCH_RESULTS_RESPONSE` - Paginated search results

### Error Responses:
- `RATE_LIMIT_ERROR` - 429 rate limit error
- `VALIDATION_ERROR` - 400 validation error
- `NOT_FOUND_ERROR` - 404 not found error

### Property Examples:
- `PROPERTY_VALUES` - Examples of all Notion property types

### Helper Functions:
- `create_mock_page()` - Create custom page responses
- `create_error_response()` - Create custom error responses

## AI Response Fixtures

Located in: `blackcore/minimal/tests/fixtures/ai_response_fixtures.py`

### Successful Responses:
- `CLAUDE_RESPONSE_SUCCESS` - Claude API successful extraction
- `OPENAI_RESPONSE_SUCCESS` - OpenAI API successful extraction
- `COMPLEX_EXTRACTION_RESPONSE` - All entity types extracted

### Error Scenarios:
- `MALFORMED_JSON_RESPONSE` - Invalid JSON in response
- `MARKDOWN_RESPONSE` - Response with markdown formatting
- `EMPTY_EXTRACTION_RESPONSE` - No entities found
- `AI_RATE_LIMIT_ERROR` - AI provider rate limit
- `TOKEN_LIMIT_ERROR` - Context length exceeded

### Helper Functions:
- `create_mock_ai_response()` - Create custom AI responses
- `create_mock_error_response()` - Create AI error responses

## Test Helpers

Located in: `blackcore/minimal/tests/utils/test_helpers.py`

### Configuration:
- `create_test_config()` - Create test configuration with defaults

### Mocking:
- `create_mock_notion_client()` - Pre-configured Notion client mock
- `create_mock_ai_client()` - Pre-configured AI client mock

### Assertions:
- `assert_notion_page_equal()` - Compare NotionPage objects
- `assert_properties_formatted()` - Verify property formatting

### Utilities:
- `create_temp_cache_dir()` - Create temporary cache directory
- `cleanup_temp_dir()` - Clean up temporary directories
- `MockResponse` - Mock HTTP response class

## Mock Builders

Located in: `blackcore/minimal/tests/utils/mock_builders.py`

### Builders:

1. **MockNotionClientBuilder**
   - Fluent API for building complex Notion client mocks
   - Configure query results, create/update responses, errors
   - Example:
   ```python
   mock = MockNotionClientBuilder()
       .with_query_results("db-123", [page1, page2])
       .with_create_response("db-123", new_page)
       .build()
   ```

2. **MockAIProviderBuilder**
   - Build AI provider mocks with predefined responses
   - Support for both Claude and OpenAI
   - Example:
   ```python
   mock = MockAIProviderBuilder("claude")
       .with_extraction([entity1, entity2])
       .build()
   ```

3. **ProcessingScenarioBuilder**
   - Create complete test scenarios
   - Combine transcripts, expected entities, and pages
   - Example:
   ```python
   scenario = ProcessingScenarioBuilder()
       .add_transcript(transcript, [entity], [page])
       .build_mocks()
   ```

### Special Scenarios:
- `create_rate_limit_scenario()` - Mock that rate limits after N requests
- `create_flaky_api_mock()` - Mock that randomly fails

## Usage Examples

### Basic Test Setup:
```python
from blackcore.minimal.tests.fixtures import (
    SIMPLE_TRANSCRIPT,
    NOTION_PAGE_RESPONSE,
    CLAUDE_RESPONSE_SUCCESS
)
from blackcore.minimal.tests.utils import (
    create_test_config,
    create_mock_notion_client,
    create_mock_ai_client
)

def test_simple_flow():
    # Setup
    config = create_test_config()
    notion_mock = create_mock_notion_client()
    ai_mock = create_mock_ai_client("claude")
    
    # Configure mocks
    ai_mock.messages.create.return_value = CLAUDE_RESPONSE_SUCCESS
    notion_mock.pages.create.return_value = NOTION_PAGE_RESPONSE
    
    # Run test
    processor = TranscriptProcessor(config)
    result = processor.process_transcript(SIMPLE_TRANSCRIPT)
    
    # Assert
    assert result.status == "success"
```

### Complex Scenario:
```python
from blackcore.minimal.tests.utils import ProcessingScenarioBuilder

def test_batch_with_errors():
    # Build scenario
    builder = ProcessingScenarioBuilder()
    builder.add_transcript(transcript1, entities1, pages1)
    builder.add_error_case(transcript2, "API Error")
    
    ai_mock, notion_mock = builder.build_mocks()
    
    # Run test with mocks
    # ...
```

## Best Practices

1. **Use fixtures for consistency** - Don't create test data inline
2. **Use builders for complex scenarios** - Easier to read and maintain
3. **Clean up resources** - Always clean temporary directories
4. **Mock external calls** - Never make real API calls in tests
5. **Test edge cases** - Use special character and error fixtures
6. **Document custom fixtures** - Add comments explaining purpose