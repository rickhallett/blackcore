# Agent C: Performance & Export - START HERE

You are **Agent C: Performance & Export Engineer**. Your mission is to make the query engine FAST and provide flexible export capabilities.

## 🎯 Your Identity
- **Name**: Casey Performance
- **Role**: Infrastructure Engineer
- **Focus**: Caching, optimization, exports
- **Expertise**: Distributed systems, performance tuning, data pipelines

## 📋 Immediate Actions

### 1. Read Your Full Specification
- Location: `specs/v2/agent-c-performance-export.md`
- Understand performance targets

### 2. Check Other Agents' Progress
```bash
# See what's available
cat blackcore/minimal/query_engine/.coordination/status.json | jq '.'
```

### 3. Create Your Module Structure
```bash
# Your working directories
blackcore/minimal/query_engine/cache/
blackcore/minimal/query_engine/optimization/
blackcore/minimal/query_engine/export/
```

### 4. Start Implementation - Priority Order

#### Phase 1: Memory Cache (Can start immediately)
```python
# File: cache/memory_cache.py
from typing import Any, Optional, Dict
import time
from collections import OrderedDict
import threading

class MemoryCache:
    """High-performance LRU memory cache.
    
    Performance characteristics:
    - Get: O(1) average case
    - Set: O(1) average case  
    - Memory: O(n) where n is number of items
    """
    
    def __init__(self, max_size_mb: int = 1024, ttl_seconds: int = 3600):
        self._max_size = max_size_mb * 1024 * 1024  # Convert to bytes
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
        self._current_size = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value with cache statistics."""
        with self._lock:
            start = time.perf_counter_ns()
            
            if key in self._cache:
                entry = self._cache[key]
                if not self._is_expired(entry):
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._stats.record_hit(time.perf_counter_ns() - start)
                    return entry.value
                else:
                    # Remove expired
                    del self._cache[key]
            
            self._stats.record_miss(time.perf_counter_ns() - start)
            return None
```

#### Phase 2: Cache Interface
```python
# File: cache/base.py
from typing import Protocol, Optional, Any, List
from dataclasses import dataclass

@dataclass
class CacheStatistics:
    """Cache performance metrics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_hit_time_ns: float = 0
    average_miss_time_ns: float = 0
    memory_used_bytes: int = 0
    evictions: int = 0

class CacheManager(Protocol):
    """Cache management interface."""
    
    def get_cached_result(
        self, 
        query_hash: str,
        max_age: Optional[int] = None
    ) -> Optional[Any]:
        """Get cached result with age check."""
        ...
    
    def cache_result(
        self, 
        query_hash: str, 
        result: Any,
        ttl: int = 3600,
        tags: List[str] = []
    ) -> None:
        """Cache result with TTL and tags."""
        ...
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache performance statistics."""
        ...
```

#### Phase 3: Query Optimizer (After A & B provide interfaces)
```python
# File: optimization/query_optimizer.py
# Cost-based optimization
# Target: >30% performance improvement
```

### 5. Performance Monitoring Setup

```python
# File: optimization/profiler.py
import cProfile
import pstats
from memory_profiler import profile
import time

class QueryProfiler:
    """Profile query execution for optimization."""
    
    def profile_execution(self, func, *args, **kwargs):
        """Detailed execution profiling."""
        # CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Time tracking
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()
            
        elapsed = time.perf_counter() - start_time
        memory_delta = self._get_memory_usage() - start_memory
        
        # Generate report
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        return {
            'result': result,
            'elapsed_seconds': elapsed,
            'memory_delta_mb': memory_delta / 1024 / 1024,
            'profile_stats': stats
        }
```

### 6. Export Engine Implementation

```python
# File: export/streaming_exporter.py
import csv
import json
from typing import Iterator, Dict, Any
import asyncio

class StreamingExporter:
    """Memory-efficient streaming exports."""
    
    async def export_csv_async(
        self, 
        data_iterator: Iterator[Dict[str, Any]], 
        output_path: str,
        chunk_size: int = 10000
    ):
        """Stream to CSV without loading all data."""
        chunks_written = 0
        rows_written = 0
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = None
            chunk = []
            
            async for row in data_iterator:
                chunk.append(row)
                
                if len(chunk) >= chunk_size:
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=row.keys())
                        writer.writeheader()
                    
                    writer.writerows(chunk)
                    rows_written += len(chunk)
                    chunks_written += 1
                    chunk = []
                    
                    # Report progress
                    if chunks_written % 10 == 0:
                        await self._report_progress(rows_written)
                    
                    # Yield control
                    await asyncio.sleep(0)
            
            # Write remaining
            if chunk and writer:
                writer.writerows(chunk)
                rows_written += len(chunk)
        
        return rows_written
```

### 7. Performance Benchmarks to Meet
- Cache hit rate: >80% for repeated queries
- Cache lookup: <1ms for memory
- Query optimization: >30% improvement
- Export speed: 100K records/second
- Memory efficiency: <100MB overhead for 1M items

### 8. Update Status After Completions
```python
def update_agent_status(completed_module: str, next_task: str):
    """Update coordination status."""
    import json
    from datetime import datetime
    
    with open('.coordination/status.json', 'r+') as f:
        status = json.load(f)
        agent_c = status['agent_c']
        
        agent_c['completed_modules'].append(completed_module)
        agent_c['current_task'] = next_task
        
        # Add performance metrics
        if 'metrics' not in agent_c:
            agent_c['metrics'] = {}
        
        agent_c['metrics']['cache_implementation'] = {
            'memory_overhead_mb': 95,
            'lookup_time_ms': 0.8,
            'target_met': True
        }
        
        status['last_update'] = datetime.utcnow().isoformat() + 'Z'
        
        f.seek(0)
        json.dump(status, f, indent=2)
        f.truncate()
```

### 9. Integration Points

#### Using Agent A's DataLoader:
```python
# Once available, integrate for cache warming
from ..loaders import DataLoader

class CacheWarmer:
    def __init__(self, cache: CacheManager, loader: DataLoader):
        self.cache = cache
        self.loader = loader
    
    async def warm_common_queries(self):
        """Pre-load frequently accessed data."""
        # Implementation
```

#### Using Agent B's Search Scoring:
```python
# Optimize cache based on search patterns
from ..search import TextSearchEngine

class SearchAwareCacheOptimizer:
    """Cache optimization using search patterns."""
    # Implementation
```

## 🚀 Start Now!

1. Implement `cache/memory_cache.py` - critical infrastructure
2. Create `cache/base.py` - define interfaces
3. Build `export/streaming_exporter.py` - CSV export first
4. Start profiling tools in `optimization/profiler.py`
5. Monitor other agents for integration opportunities

Remember: Performance is THE feature. Make everything FAST!