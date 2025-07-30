# /review - Comprehensive Code Review

You are now in code review mode. Perform a thorough analysis of the code using the following systematic approach:

## Review Checklist

### 1. Code Quality & Standards
- [ ] Code follows project conventions and style guide
- [ ] Variable and function names are clear and descriptive
- [ ] No code duplication (DRY principle)
- [ ] Functions are focused and single-purpose
- [ ] Appropriate abstraction levels

### 2. Architecture & Design
- [ ] Design patterns used appropriately
- [ ] SOLID principles followed
- [ ] Clear separation of concerns
- [ ] Scalability considerations
- [ ] No over-engineering

### 3. Performance
- [ ] No obvious performance bottlenecks
- [ ] Efficient algorithms used (check time/space complexity)
- [ ] Database queries optimized
- [ ] Caching used where appropriate
- [ ] Resource cleanup handled properly

### 4. Security
- [ ] Input validation present
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities  
- [ ] Authentication/authorization checks
- [ ] Sensitive data properly handled
- [ ] No hardcoded secrets

### 5. Error Handling
- [ ] All errors caught and handled appropriately
- [ ] Meaningful error messages
- [ ] No silent failures
- [ ] Proper logging in place
- [ ] Graceful degradation

### 6. Testing
- [ ] Unit tests present and comprehensive
- [ ] Edge cases covered
- [ ] Integration tests where needed
- [ ] Test coverage adequate (aim for 80%+)
- [ ] Tests are maintainable

### 7. Documentation
- [ ] Code is self-documenting where possible
- [ ] Complex logic has comments
- [ ] API documentation complete
- [ ] README updated if needed
- [ ] Change log updated

### 8. Maintainability
- [ ] Code is easy to understand
- [ ] Dependencies are justified
- [ ] No unnecessary complexity
- [ ] Future changes considered
- [ ] Technical debt documented

## Review Process

1. **Initial Scan**: Use Grep to find files changed recently or in the current branch
2. **Deep Analysis**: For each file:
   - Read the complete file to understand context
   - Use the zen code review tool: `zen/codereview` for AI-powered analysis
   - Check against the checklist above
3. **Pattern Detection**: Look for:
   - Common anti-patterns
   - Code smells
   - Security vulnerabilities
   - Performance issues
4. **Improvement Suggestions**: For each issue found:
   - Explain why it's a problem
   - Provide specific fix with code example
   - Suggest preventive measures
5. **Summary**: Provide:
   - Overall assessment (1-10 score)
   - Top 3 critical issues
   - Top 3 positive aspects
   - Specific, actionable recommendations

## Additional Considerations

- **Context**: Consider the project phase (MVP vs. production)
- **Team Standards**: Respect existing patterns even if not ideal
- **Pragmatism**: Balance perfect code with delivery timelines
- **Learning**: Explain the "why" behind suggestions

## Example Usage

```
User: /review src/api/
Claude: I'll perform a comprehensive code review of the src/api/ directory...
[Detailed analysis follows]
```

Remember: The goal is to improve code quality while being constructive and educational. Focus on high-impact improvements first.