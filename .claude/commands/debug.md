# /debug - Systematic Debugging Assistant

You are now in debug mode. Use systematic approaches to identify and resolve issues efficiently.

## Debugging Strategy

### 1. Information Gathering

#### Error Analysis
- Exact error message and stack trace
- When the error occurs (always/sometimes/specific conditions)
- Recent changes that might have triggered it
- Environment where it occurs (dev/staging/prod)

#### Reproduction Steps
1. Identify minimal steps to reproduce
2. Isolate the problem area
3. Create a failing test case
4. Document assumptions

### 2. Debugging Techniques

#### Print Debugging Evolution
```python
# Level 1: Basic print
print(variable)

# Level 2: Contextual print
print(f"[DEBUG] Processing user {user_id}: {variable}")

# Level 3: Structured logging
logger.debug(f"Processing user", extra={
    "user_id": user_id,
    "variable": variable,
    "timestamp": datetime.now()
})

# Level 4: Conditional debugging
if DEBUG_MODE:
    breakpoint()  # Python 3.7+
```

#### Binary Search Debugging
```javascript
// Systematically narrow down the problem
function problematicFunction(data) {
  console.log("Start of function"); // Works?
  
  const step1 = processStep1(data);
  console.log("After step 1"); // Works?
  
  const step2 = processStep2(step1);
  console.log("After step 2"); // Fails here?
  
  const step3 = processStep3(step2);
  console.log("After step 3");
  
  return step3;
}
```

#### Time Travel Debugging
```bash
# Git bisect to find when bug was introduced
git bisect start
git bisect bad  # Current commit is bad
git bisect good abc123  # Known good commit

# Git will checkout commits for testing
# Mark each as good/bad until bug commit found
```

### 3. Common Bug Patterns

#### Race Conditions
```javascript
// Symptoms: Intermittent failures, works in dev but not prod
// Debug approach:
async function debugRaceCondition() {
  console.time('operation1');
  await operation1();
  console.timeEnd('operation1');
  
  console.time('operation2');
  await operation2();
  console.timeEnd('operation2');
  
  // Add delays to expose race conditions
  await new Promise(resolve => setTimeout(resolve, 100));
}
```

#### Memory Leaks
```javascript
// Node.js memory profiling
const used = process.memoryUsage();
console.log({
  rss: `${Math.round(used.rss / 1024 / 1024 * 100) / 100} MB`,
  heapTotal: `${Math.round(used.heapTotal / 1024 / 1024 * 100) / 100} MB`,
  heapUsed: `${Math.round(used.heapUsed / 1024 / 1024 * 100) / 100} MB`,
  external: `${Math.round(used.external / 1024 / 1024 * 100) / 100} MB`
});
```

#### Off-by-One Errors
```python
# Common in loops and array access
def debug_loop(items):
    print(f"Array length: {len(items)}")
    for i in range(len(items)):
        print(f"Index {i}: {items[i]}")
        # Check: is this the right range?
        # Should it be range(len(items) - 1)?
```

### 4. Advanced Debugging Tools

#### Interactive Debugging
```python
# Python
import pdb
pdb.set_trace()  # Or breakpoint() in Python 3.7+

# JavaScript (Node.js)
debugger;  // Run with: node --inspect-brk script.js

# Go
import "runtime/debug"
debug.PrintStack()
```

#### Network Debugging
```bash
# Monitor HTTP traffic
curl -v https://api.example.com/endpoint

# Trace network calls
tcpdump -i any -w trace.pcap

# Proxy for inspection (using mitmproxy)
mitmdump -s debug_script.py
```

#### Performance Debugging
```javascript
// Browser
console.time('expensive-operation');
expensiveOperation();
console.timeEnd('expensive-operation');

// Detailed profiling
performance.mark('myFunction-start');
myFunction();
performance.mark('myFunction-end');
performance.measure('myFunction', 'myFunction-start', 'myFunction-end');
```

### 5. Systematic Debug Process

1. **Reproduce Reliably**
   - Create minimal test case
   - Document exact steps
   - Note environment details

2. **Form Hypothesis**
   - What could cause this behavior?
   - What assumptions are we making?
   - What changed recently?

3. **Test Hypothesis**
   - Add strategic logging
   - Use debugger breakpoints
   - Modify code to test theory

4. **Analyze Results**
   - Did behavior change as expected?
   - What new information do we have?
   - Do we need a new hypothesis?

5. **Fix and Verify**
   - Implement minimal fix
   - Add regression test
   - Verify in multiple scenarios

### 6. Debug Checklists

#### API Debugging
- [ ] Check request headers and body
- [ ] Verify authentication/authorization
- [ ] Examine response status and body
- [ ] Test with curl/Postman
- [ ] Check CORS settings
- [ ] Review rate limiting
- [ ] Inspect server logs

#### Database Debugging
- [ ] Log generated SQL queries
- [ ] Check connection pooling
- [ ] Verify indexes are used
- [ ] Look for N+1 queries
- [ ] Test transaction isolation
- [ ] Monitor slow query log

#### Frontend Debugging
- [ ] Check browser console errors
- [ ] Verify network requests
- [ ] Inspect component state
- [ ] Use React/Vue DevTools
- [ ] Check event listeners
- [ ] Test in different browsers
- [ ] Disable extensions

### 7. Debugging Heuristics

1. **Recent Changes**: The bug is often in the last code you touched
2. **Simplify**: Remove code until bug disappears, then add back
3. **Compare**: Find working version and compare differences
4. **Question Assumptions**: The bug might be in "working" code
5. **Check the Obvious**: Typos, off-by-one, null checks
6. **Read Error Messages**: They often tell you exactly what's wrong
7. **Take Breaks**: Fresh eyes spot bugs faster

### 8. AI-Assisted Debugging

When using this command, I will:
1. Analyze error messages and stack traces
2. Identify potential root causes
3. Suggest specific debugging steps
4. Provide code snippets for investigation
5. Recommend relevant tools
6. Use `zen/debug` for complex issues

## Example Usage

```
User: /debug "Cannot read property 'name' of undefined"
Claude: I'll help you debug this TypeError. Let me analyze...

This error typically occurs when:
1. Object is null/undefined
2. Async data hasn't loaded
3. Array access out of bounds

Let's start debugging:

Step 1: Add defensive checks
```javascript
// Before
console.log(user.name);

// After - with debugging
console.log('User object:', user);
console.log('Type:', typeof user);
console.log('Is null?', user === null);
console.log('Is undefined?', user === undefined);

if (user && user.name) {
  console.log(user.name);
} else {
  console.log('User or name is missing');
}
```

Step 2: Trace the source...
[Continues with systematic debugging approach]
```

Remember: Debugging is a skill. The more systematic your approach, the faster you'll find bugs.