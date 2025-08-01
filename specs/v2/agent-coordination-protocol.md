# Agent Coordination Protocol

## Overview

This document defines how the three development agents (A: Data Foundation, B: Intelligence Search, C: Performance Export) coordinate their parallel development efforts on the Blackcore Query Engine.

## Communication Channels

### 1. Daily Standup Format (Async)
Each agent posts a daily update in the shared channel by 9 AM:

```markdown
**Agent [A/B/C] Daily Update - [Date]**
✅ Completed:
- [List completed items]

🚧 In Progress:
- [Current work items]

🔜 Next:
- [Planned for today]

⚠️ Blockers:
- [Any blockers needing attention]

📊 Metrics:
- [Relevant performance/quality metrics]
```

### 2. Interface Change Protocol

When changing a public interface:

```markdown
**INTERFACE CHANGE NOTICE**
Agent: [A/B/C]
Interface: [InterfaceName]
Change Type: [Addition/Modification/Deprecation]
Version: [New version number]

Changes:
```diff
- old_method(param: str) -> str
+ new_method(param: str, options: Dict) -> Result
```

Impact:
- Affects: [Which agents/modules]
- Migration: [How to update]
- Deadline: [When change takes effect]
```

### 3. Integration Points

## Week 1: Foundation Sprint

### Agent A Focus:
```python
# Priority 1: Basic data loading
class JSONDataLoader:
    def load_database(self, name: str) -> List[Dict[str, Any]]
    def get_available_databases(self) -> List[str]

# Priority 2: Basic filtering  
class BasicFilterEngine:
    def apply_filters(self, data: List[Dict], filters: List[QueryFilter]) -> List[Dict]
```

### Agent B Focus:
```python
# Design interfaces and prepare test data
class TextSearchEngine(Protocol):
    # Define interface
    pass

# Create mock data loader for testing
class MockDataLoader:
    # Implements Agent A's interface
    pass
```

### Agent C Focus:
```python
# Design cache interface
class CacheManager(Protocol):
    # Define interface
    pass

# Implement basic memory cache
class MemoryCache:
    # Simple LRU implementation
    pass
```

### Week 1 Integration Test:
```python
# Friday: All agents run this test
def test_basic_integration():
    loader = JSONDataLoader()  # From Agent A
    data = loader.load_database("test_db")
    
    filter_engine = BasicFilterEngine()  # From Agent A
    filtered = filter_engine.apply_filters(data, test_filters)
    
    cache = MemoryCache()  # From Agent C
    cache.set("test_query", filtered)
    assert cache.get("test_query") == filtered
```

## Week 2: Feature Development

### Dependency Handoffs

#### Agent A → Agent B:
```python
# Agent A provides by Monday:
class DataLoader:
    """Stable v1.0 - Agent B can rely on this."""
    def load_database(self, name: str) -> List[Dict[str, Any]]:
        """Returns list of entities with properties."""
        pass
```

#### Agent B Development:
```python
# Agent B can now implement:
class RelationshipResolver:
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader  # Uses Agent A's interface
    
    def resolve_relationships(self, entity: Dict, includes: List[str]) -> Dict:
        # Implementation using real data loader
        pass
```

#### Agent C Optimization:
```python
# Agent C profiles Agent A's code:
class QueryProfiler:
    def profile_query_execution(self, query: StructuredQuery) -> PerformanceProfile:
        # Identify bottlenecks in Agent A's implementation
        # Suggest optimizations
        pass
```

## Week 3: Integration & Optimization

### Cross-Team Code Reviews

Each agent reviews specific aspects:

- **Agent A reviews Agent B**: Data access patterns, efficiency
- **Agent B reviews Agent C**: Cache key generation, search integration  
- **Agent C reviews Agent A**: Performance bottlenecks, memory usage

### Performance Testing Protocol

```python
# Shared performance test suite
class PerformanceIntegrationTest:
    @pytest.mark.benchmark
    def test_full_query_performance(self):
        # Agent A: Load 100K records
        loader = JSONDataLoader()
        data = loader.load_database("large_test_db")
        
        # Agent B: Complex search
        search_engine = TextSearchEngine()
        results = search_engine.search("complex query", data)
        
        # Agent C: Cache and measure
        cache = CacheManager()
        metrics = cache.get_statistics()
        
        assert metrics.total_time_ms < 200
        assert metrics.memory_used_mb < 500
```

## Conflict Resolution

### Interface Conflicts
If two agents need incompatible interface changes:

1. **Document the conflict** in shared channel
2. **Propose alternatives** with pros/cons
3. **Vote or escalate** if no consensus in 24h
4. **Version the interface** to support both temporarily

### Performance Conflicts
If optimizations conflict:

1. **Measure impact** with benchmarks
2. **Find compromise** that helps both
3. **Document tradeoffs** in code
4. **Plan future resolution** in backlog

## Mock Services

Each agent provides mocks for others:

### Agent A Mocks (for B & C):
```python
class MockDataLoader:
    """Mock for testing without file I/O."""
    def load_database(self, name: str) -> List[Dict[str, Any]]:
        return generate_test_data(1000)  # Consistent test data
```

### Agent B Mocks (for C):
```python  
class MockSearchEngine:
    """Mock for testing without NLP."""
    def search(self, query: str, data: List[Dict]) -> List[SearchResult]:
        # Simple substring matching for tests
        return [SearchResult(d, 0.5) for d in data if query in str(d)]
```

### Agent C Mocks (for A & B):
```python
class MockCache:
    """Mock for testing without Redis."""
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
```

## Success Metrics Dashboard

### Shared Metrics (Updated Daily)

```markdown
## Query Engine Progress Dashboard

### Agent A - Data Foundation
- ✅ Data Loading: 100ms (Target: <100ms) ✅
- 🔄 Filter Performance: 75ms (Target: <50ms) 
- ✅ Test Coverage: 96% (Target: >95%)

### Agent B - Intelligence Search  
- ✅ Search Accuracy: 92% (Target: >90%)
- 🔄 NLP Parsing: 78% (Target: >85%)
- ✅ Relationship Depth: 5 levels (Target: 5+)

### Agent C - Performance Export
- ✅ Cache Hit Rate: 84% (Target: >80%)
- 🔄 Export Speed: 85K/s (Target: 100K/s)
- ✅ Memory Efficiency: 95MB/1M items (Target: <100MB)

### Integration Tests
- ✅ Cross-module Tests: 42/42 passing
- ✅ Performance Tests: 8/8 passing
- 🔄 Load Tests: 6/8 passing
```

## Emergency Protocols

### Blocking Issue Process
1. **Immediate notification** in channel with @mention
2. **Provide workaround** if possible
3. **Pair debugging** if needed
4. **Update interfaces** only as last resort

### Performance Regression
1. **Automatic alerts** when benchmarks fail
2. **Rollback to last good version**
3. **Root cause analysis** within 4 hours
4. **Fix or feature flag** within 24 hours

## Code Handoff Protocol

### Documentation Requirements
Each module must include:
- README.md with quick start
- API documentation with examples
- Performance characteristics
- Known limitations
- Future optimization opportunities

### Example Module Handoff

```markdown
## Filter Engine v1.0 - Ready for Integration

### Quick Start
```python
from blackcore.minimal.query_engine.filters import BasicFilterEngine

engine = BasicFilterEngine()
filtered = engine.apply_filters(data, [
    QueryFilter("status", QueryOperator.EQUALS, "active"),
    QueryFilter("score", QueryOperator.GT, 0.8)
])
```

### Performance
- 10K records: 12ms
- 100K records: 125ms  
- Memory: O(1) - streaming implementation

### Limitations
- No regex support yet (coming in v1.1)
- Case-sensitive by default

### API Stability
- Stable for v1.x
- Breaking changes only in v2.0
```

This coordination protocol ensures smooth parallel development while maintaining system integrity and performance targets.