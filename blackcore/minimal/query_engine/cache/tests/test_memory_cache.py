"""Comprehensive tests for memory cache performance."""

import pytest
import time
import asyncio
import threading
from unittest.mock import Mock, patch
import sys

from ..memory_cache import MemoryCache, LRUCache, LFUCache, CacheEntry


class TestCacheEntry:
    """Test cache entry functionality."""
    
    def test_cache_entry_creation(self):
        """Test creating cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            size_bytes=100,
            created_at=time.time(),
            accessed_at=time.time(),
            ttl=3600
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.size_bytes == 100
        assert entry.access_count == 1
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        past_time = time.time() - 7200  # 2 hours ago
        
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            size_bytes=100,
            created_at=past_time,
            accessed_at=past_time,
            ttl=3600  # 1 hour TTL
        )
        
        assert entry.is_expired()
        assert entry.get_age_seconds() > 7200
    
    def test_cache_entry_access(self):
        """Test accessing cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            size_bytes=100,
            created_at=time.time(),
            accessed_at=time.time()
        )
        
        initial_count = entry.access_count
        initial_time = entry.accessed_at
        
        time.sleep(0.01)
        entry.access()
        
        assert entry.access_count == initial_count + 1
        assert entry.accessed_at > initial_time


class TestLRUCache:
    """Test LRU cache implementation."""
    
    def test_lru_basic_operations(self):
        """Test basic LRU cache operations."""
        cache = LRUCache(capacity_mb=1)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test miss
        assert cache.get("key2") is None
        
        # Test overwrite
        cache.set("key1", "new_value1")
        assert cache.get("key1") == "new_value1"
    
    def test_lru_eviction_policy(self):
        """Test LRU eviction policy."""
        # Small cache that can hold ~3 small items
        cache = LRUCache(capacity_mb=0.001)
        
        # Add items
        cache.set("key1", "a" * 100)
        cache.set("key2", "b" * 100)
        cache.set("key3", "c" * 100)
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add new item - should evict key2 (least recently used)
        cache.set("key4", "d" * 100)
        
        assert cache.get("key1") is not None  # Recently accessed
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") is not None  # Still present
        assert cache.get("key4") is not None  # Newly added
    
    def test_lru_ttl_expiration(self):
        """Test TTL expiration in LRU cache."""
        cache = LRUCache(capacity_mb=1)
        
        # Set with short TTL
        cache.set("key1", "value1", ttl=0.1)  # 100ms TTL
        
        # Should be present immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired
        assert cache.get("key1") is None
        
        # Check stats
        stats = cache.get_stats()
        assert stats['expired_evictions'] > 0
    
    def test_lru_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = LRUCache(capacity_mb=1)
        
        # Generate some activity
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        cache.get("key1")  # Hit
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 2/3
        assert stats['entry_count'] == 1
    
    def test_lru_thread_safety(self):
        """Test thread safety of LRU cache."""
        cache = LRUCache(capacity_mb=10)
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_key_{i}"
                    cache.set(key, f"value_{i}")
                    result = cache.get(key)
                    if result != f"value_{i}":
                        errors.append(f"Thread {thread_id}: Expected value_{i}, got {result}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Run multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestLFUCache:
    """Test LFU cache implementation."""
    
    def test_lfu_basic_operations(self):
        """Test basic LFU cache operations."""
        cache = LFUCache(capacity_mb=1)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test miss
        assert cache.get("key2") is None
    
    def test_lfu_eviction_policy(self):
        """Test LFU eviction policy."""
        # Small cache
        cache = LFUCache(capacity_mb=0.001)
        
        # Add items with different access patterns
        cache.set("key1", "a" * 100)
        cache.set("key2", "b" * 100)
        cache.set("key3", "c" * 100)
        
        # Access key1 and key3 multiple times
        for _ in range(5):
            cache.get("key1")
            cache.get("key3")
        
        # Access key2 only once
        cache.get("key2")
        
        # Add new item - should evict key2 (least frequently used)
        cache.set("key4", "d" * 100)
        
        assert cache.get("key1") is not None  # Frequently accessed
        assert cache.get("key2") is None      # Evicted (least frequent)
        assert cache.get("key3") is not None  # Frequently accessed
        assert cache.get("key4") is not None  # Newly added
    
    def test_lfu_frequency_tracking(self):
        """Test frequency tracking in LFU cache."""
        cache = LFUCache(capacity_mb=1)
        
        cache.set("key1", "value1")
        
        # Access multiple times
        for _ in range(10):
            cache.get("key1")
        
        # Check internal frequency tracking
        assert "key1" in cache._key_frequencies
        assert cache._key_frequencies["key1"] == 11  # 1 initial + 10 accesses


class TestMemoryCache:
    """Test default memory cache with async support."""
    
    @pytest.mark.asyncio
    async def test_get_or_compute_async(self):
        """Test async get_or_compute functionality."""
        cache = MemoryCache(capacity_mb=1)
        compute_count = 0
        
        async def compute_fn():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.01)
            return f"computed_value_{compute_count}"
        
        # First call should compute
        result1 = await cache.get_or_compute("key1", compute_fn)
        assert result1 == "computed_value_1"
        assert compute_count == 1
        
        # Second call should use cache
        result2 = await cache.get_or_compute("key1", compute_fn)
        assert result2 == "computed_value_1"
        assert compute_count == 1  # Not incremented
    
    def test_get_or_compute_sync(self):
        """Test sync get_or_compute functionality."""
        cache = MemoryCache(capacity_mb=1)
        compute_count = 0
        
        def compute_fn():
            nonlocal compute_count
            compute_count += 1
            return f"computed_value_{compute_count}"
        
        # Run in async context
        async def test():
            result1 = await cache.get_or_compute("key1", compute_fn)
            assert result1 == "computed_value_1"
            assert compute_count == 1
            
            result2 = await cache.get_or_compute("key1", compute_fn)
            assert result2 == "computed_value_1"
            assert compute_count == 1
        
        asyncio.run(test())


class TestCachePerformance:
    """Performance benchmarks for cache implementations."""
    
    def test_cache_throughput(self):
        """Test cache operation throughput."""
        cache = LRUCache(capacity_mb=100)
        
        # Measure set operations
        start_time = time.time()
        for i in range(10000):
            cache.set(f"key_{i}", f"value_{i}")
        set_duration = time.time() - start_time
        set_ops_per_sec = 10000 / set_duration
        
        # Measure get operations (hits)
        start_time = time.time()
        for i in range(10000):
            cache.get(f"key_{i}")
        get_hit_duration = time.time() - start_time
        get_hit_ops_per_sec = 10000 / get_hit_duration
        
        # Measure get operations (misses)
        start_time = time.time()
        for i in range(10000):
            cache.get(f"missing_key_{i}")
        get_miss_duration = time.time() - start_time
        get_miss_ops_per_sec = 10000 / get_miss_duration
        
        # Performance assertions (should handle >100k ops/sec)
        assert set_ops_per_sec > 100000, f"Set throughput too low: {set_ops_per_sec:.0f} ops/sec"
        assert get_hit_ops_per_sec > 100000, f"Get hit throughput too low: {get_hit_ops_per_sec:.0f} ops/sec"
        assert get_miss_ops_per_sec > 100000, f"Get miss throughput too low: {get_miss_ops_per_sec:.0f} ops/sec"
    
    def test_cache_memory_efficiency(self):
        """Test memory efficiency of cache."""
        cache = LRUCache(capacity_mb=10)
        
        # Fill cache with data
        value_size = 1000  # 1KB values
        test_value = "x" * value_size
        
        items_added = 0
        for i in range(10000):
            cache.set(f"key_{i}", test_value)
            items_added += 1
            
            stats = cache.get_stats()
            if stats['used_mb'] >= 9:  # Stop at 90% capacity
                break
        
        stats = cache.get_stats()
        
        # Check memory utilization
        assert stats['utilization'] > 0.8, "Cache not utilizing available memory efficiently"
        assert stats['utilization'] < 1.0, "Cache exceeding capacity"
        
        # Check overhead (should be reasonable)
        expected_size_mb = (items_added * value_size) / (1024 * 1024)
        actual_size_mb = stats['used_mb']
        overhead_ratio = actual_size_mb / expected_size_mb
        
        assert overhead_ratio < 2.0, f"Memory overhead too high: {overhead_ratio:.2f}x"
    
    def test_concurrent_performance(self):
        """Test performance under concurrent access."""
        cache = LRUCache(capacity_mb=100)
        
        # Pre-populate cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        
        operations_per_thread = 10000
        thread_count = 10
        
        def worker():
            for i in range(operations_per_thread):
                if i % 2 == 0:
                    cache.get(f"key_{i % 1000}")
                else:
                    cache.set(f"new_key_{i}", f"value_{i}")
        
        # Measure concurrent performance
        start_time = time.time()
        
        threads = []
        for _ in range(thread_count):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        duration = time.time() - start_time
        total_operations = operations_per_thread * thread_count
        ops_per_sec = total_operations / duration
        
        # Should handle >100k ops/sec even with contention
        assert ops_per_sec > 100000, f"Concurrent throughput too low: {ops_per_sec:.0f} ops/sec"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])