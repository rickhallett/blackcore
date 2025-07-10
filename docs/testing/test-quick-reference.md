# Testing Quick Reference

## Essential Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=blackcore.minimal

# Run specific test file
pytest tests/unit/test_config.py

# Run tests matching pattern
pytest -k "test_process"

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run with debugging
pytest -s  # show print statements
pytest --pdb  # drop to debugger on failure
```

## Test Organization

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Performance tests
pytest tests/integration/test_performance.py

# Edge case tests
pytest tests/unit/test_edge_cases.py
```

## Make Commands

```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-coverage     # With coverage report
make test-performance  # Performance tests
make lint             # Run linting
make format           # Format code
make clean            # Clean test artifacts
```

## Common Test Patterns

### Basic Test
```python
def test_function_success():
    result = function_under_test(valid_input)
    assert result.success is True
    assert result.value == expected_value
```

### Test with Mock
```python
@patch('module.ExternalClient')
def test_with_mock(mock_client):
    mock_client.return_value.method.return_value = "mocked"
    result = function_under_test()
    assert result == "mocked"
    mock_client.return_value.method.assert_called_once()
```

### Test Exception
```python
def test_error_handling():
    with pytest.raises(ValueError) as exc_info:
        function_with_invalid_input()
    assert "Expected error" in str(exc_info.value)
```

### Test with Fixture
```python
def test_with_config(test_config):
    processor = TranscriptProcessor(config=test_config)
    result = processor.process(sample_data)
    assert result.success
```

### Parametrized Test
```python
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_cases(input, expected):
    assert process(input) == expected
```

## Debugging Tips

### Show all print statements
```bash
pytest -s
```

### Run specific test method
```bash
pytest tests/unit/test_config.py::TestConfig::test_load_from_file
```

### Run last failed tests
```bash
pytest --lf
```

### Run tests that match expression
```bash
pytest -k "config and not error"
```

### Generate HTML report
```bash
pytest --html=report.html --self-contained-html
```

## Coverage Commands

### Generate coverage report
```bash
pytest --cov=blackcore.minimal --cov-report=html
open htmlcov/index.html
```

### Show missing lines
```bash
pytest --cov=blackcore.minimal --cov-report=term-missing
```

### Coverage for specific module
```bash
pytest --cov=blackcore.minimal.config tests/unit/test_config.py
```

## Performance Testing

### Run with timing
```bash
pytest --durations=10  # Show 10 slowest tests
```

### Profile test execution
```bash
pytest --profile
```

### Run in parallel
```bash
pytest -n auto  # Requires pytest-xdist
```

## CI/CD Integration

### GitHub Actions
- Tests run automatically on push/PR
- Python 3.9, 3.10, 3.11 support
- Coverage uploaded to Codecov
- Performance tests on PRs

### Local CI simulation
```bash
# Run as CI would
act -j unit-tests  # Requires 'act' tool
```

## Common Fixtures

| Fixture | Purpose |
|---------|---------|
| `test_config` | Standard test configuration |
| `mock_notion_client` | Mocked Notion API client |
| `mock_ai_client` | Mocked AI client |
| `sample_transcripts` | Test transcript data |
| `temp_cache_dir` | Temporary cache directory |

## Test Markers

```python
@pytest.mark.slow  # Slow tests
@pytest.mark.integration  # Integration tests
@pytest.mark.unit  # Unit tests
@pytest.mark.skip("Reason")  # Skip test
@pytest.mark.xfail  # Expected to fail
```

## Environment Variables

```bash
# Set for integration tests
export NOTION_API_KEY="test-key"
export ANTHROPIC_API_KEY="test-key"

# Run with env vars
BLACKCORE_DRY_RUN=true pytest
```

## Troubleshooting

### Import errors
```bash
# Add project to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Clear test cache
```bash
rm -rf .pytest_cache
rm -rf .test_cache
```

### Reset test database
```bash
# Remove test artifacts
make clean
```

## Best Practices

1. **Keep tests fast** - Mock external services
2. **Test one thing** - Each test should verify one behavior
3. **Use fixtures** - Don't repeat setup code
4. **Clear names** - `test_<what>_<condition>_<expected>`
5. **Test edges** - Empty, None, large values
6. **Clean up** - Reset state between tests