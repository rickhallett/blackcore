# /test - Comprehensive Test Generation

You are now in test generation mode. Create thorough, well-structured tests following these guidelines:

## Test Strategy

### 1. Understand the Code
- Read and analyze the target code thoroughly
- Identify all code paths and branches
- Map out dependencies and side effects
- Note any async operations or state changes

### 2. Test Categories

#### Unit Tests
- Test each function/method in isolation
- Mock all external dependencies
- Focus on input/output validation
- Cover all branches and edge cases

#### Integration Tests
- Test component interactions
- Use real dependencies where appropriate
- Verify data flow between modules
- Test error propagation

#### Edge Cases
- Null/undefined inputs
- Empty collections
- Boundary values (0, -1, MAX_INT)
- Malformed data
- Concurrent access scenarios
- Network failures/timeouts

### 3. Test Structure

```[language]
describe('ComponentName', () => {
  // Setup and teardown
  beforeEach(() => {
    // Initialize test state
  });

  afterEach(() => {
    // Clean up
  });

  // Group related tests
  describe('methodName', () => {
    it('should handle normal case', () => {
      // Arrange
      const input = setupTestData();
      
      // Act
      const result = methodName(input);
      
      // Assert
      expect(result).toEqual(expectedOutput);
    });

    it('should handle edge case: null input', () => {
      // Test null handling
    });

    it('should handle error case: invalid data', () => {
      // Test error handling
    });
  });
});
```

### 4. Testing Patterns

#### AAA Pattern (Arrange, Act, Assert)
- **Arrange**: Set up test data and conditions
- **Act**: Execute the code being tested
- **Assert**: Verify the results

#### Test Data Builders
```[language]
const createTestUser = (overrides = {}) => ({
  id: 1,
  name: 'Test User',
  email: 'test@example.com',
  ...overrides
});
```

#### Mocking Strategies
- Mock external services
- Stub time-dependent functions
- Spy on function calls
- Fake data generators

### 5. Coverage Goals

- **Line Coverage**: 80%+ for critical code
- **Branch Coverage**: All conditional paths
- **Edge Cases**: At least 3 per function
- **Error Paths**: All catch blocks tested
- **Async Operations**: Both success and failure

### 6. Test Quality Checklist

- [ ] Tests are independent (no shared state)
- [ ] Tests are deterministic (no flaky tests)
- [ ] Tests are fast (mock slow operations)
- [ ] Tests are readable (clear descriptions)
- [ ] Tests actually test something (not just run code)
- [ ] Tests cover happy path and sad path
- [ ] Tests include performance considerations

### 7. Framework-Specific Patterns

#### JavaScript/TypeScript (Jest/Vitest)
```typescript
// Async testing
it('should handle async operations', async () => {
  const result = await asyncFunction();
  expect(result).toBeDefined();
});

// Error testing
it('should throw on invalid input', () => {
  expect(() => functionThatThrows()).toThrow('Expected error');
});
```

#### Python (pytest)
```python
# Parameterized tests
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected

# Fixtures
@pytest.fixture
def sample_data():
    return {"key": "value"}
```

#### Go
```go
func TestFunction(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    string
        wantErr bool
    }{
        {"normal case", "input", "output", false},
        {"error case", "", "", true},
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Function(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("error = %v, wantErr %v", err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("got = %v, want %v", got, tt.want)
            }
        })
    }
}
```

### 8. Test Generation Process

1. **Analyze**: Use `zen/testgen` to analyze code and suggest test cases
2. **Generate**: Create comprehensive test suite
3. **Validate**: Run tests and check coverage
4. **Refine**: Add missing edge cases
5. **Document**: Add comments explaining complex test scenarios

## Example Usage

```
User: /test src/utils/validator.js
Claude: I'll generate comprehensive tests for the validator module...
[Generates complete test file with all edge cases]
```

Remember: Good tests serve as documentation and catch bugs before production. Invest time in writing quality tests.