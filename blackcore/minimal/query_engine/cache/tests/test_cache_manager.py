"""Tests for multi-tier cache manager."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import shutil
from pathlib import Path

from ..cache_manager import CacheManager, MultiTierCache, RedisCache, DiskCache, CachedResult
from ..cache_statistics import CacheStatistics, CacheMetrics
from ...models import QueryResult


class TestCachedResult:
    """Test cached result wrapper."""
    
    def test_cached_result_creation(self):
        """Test creating cached result."""
        result = QueryResult(
            data=[{"id": 1, "name": "test"}],
            total_count=1,
            page=1,
            page_size=10,
            execution_time_ms=5.0
        )
        
        cached = CachedResult(
            query_hash="test_hash",
            result=result,
            cached_at=time.time(),
            ttl=3600,
            tags=["test", "query"]
        )
        
        assert cached.query_hash == "test_hash"
        assert cached.result == result
        assert not cached.is_expired()
        assert cached.age_seconds() < 1
    
    def test_cached_result_expiration(self):
        """Test cached result expiration."""
        result = QueryResult(
            data=[],
            total_count=0,
            page=1,
            page_size=10,
            execution_time_ms=1.0
        )
        
        past_time = time.time() - 7200
        cached = CachedResult(
            query_hash="test_hash",
            result=result,
            cached_at=past_time,
            ttl=3600
        )
        
        assert cached.is_expired()
        assert cached.age_seconds() > 7200


class TestDiskCache:
    """Test disk cache implementation."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_disk_cache_operations(self, temp_cache_dir):
        """Test basic disk cache operations."""
        cache = DiskCache(cache_dir=temp_cache_dir)
        
        # Test set and get
        test_data = {"key": "value", "number": 42}
        await cache.set("test_key", test_data, ttl=3600)
        
        result = await cache.get("test_key")
        assert result == test_data
        
        # Test miss
        assert await cache.get("missing_key") is None
        
        # Test delete
        assert await cache.delete("test_key")
        assert await cache.get("test_key") is None
    
    @pytest.mark.asyncio
    async def test_disk_cache_expiration(self, temp_cache_dir):
        """Test disk cache expiration."""
        cache = DiskCache(cache_dir=temp_cache_dir)
        
        # Set with short TTL
        await cache.set("test_key", "test_value", ttl=0)
        
        # Should be expired immediately
        assert await cache.get("test_key") is None
    
    @pytest.mark.asyncio
    async def test_disk_cache_sharding(self, temp_cache_dir):
        """Test disk cache directory sharding."""
        cache = DiskCache(cache_dir=temp_cache_dir)
        
        # Add multiple items
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")
        
        # Check that shard directories were created
        cache_path = Path(temp_cache_dir)
        shard_dirs = list(cache_path.iterdir())
        assert len(shard_dirs) > 1  # Should have multiple shard directories
    
    def test_disk_cache_cleanup(self, temp_cache_dir):
        """Test expired entry cleanup."""
        cache = DiskCache(cache_dir=temp_cache_dir)
        
        # Add expired entries to index
        past_time = time.time() - 7200
        cache._index = {
            "expired_key": {
                "cached_at": past_time,
                "ttl": 3600,
                "size": 100
            },
            "valid_key": {
                "cached_at": time.time(),
                "ttl": 3600,
                "size": 100
            }
        }
        
        # Run cleanup
        cache.cleanup_expired()
        
        # Only valid key should remain
        assert "expired_key" not in cache._index
        assert "valid_key" in cache._index


class TestMultiTierCache:
    """Test multi-tier cache implementation."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis cache."""
        redis = AsyncMock(spec=RedisCache)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=True)
        return redis
    
    @pytest.fixture
    def mock_disk(self):
        """Mock disk cache."""
        disk = AsyncMock(spec=DiskCache)
        disk.get = AsyncMock(return_value=None)
        disk.set = AsyncMock(return_value=True)
        disk.delete = AsyncMock(return_value=True)
        return disk
    
    @pytest.mark.asyncio
    async def test_multi_tier_l1_hit(self):
        """Test L1 (memory) cache hit."""
        cache = MultiTierCache(memory_limit_mb=10, enable_redis=False, enable_disk=False)
        await cache.initialize()
        
        # Populate L1
        test_value = "test_value"
        cache._memory_cache.set("test_key", test_value)
        
        # Get should hit L1
        result = await cache.get_or_compute("test_key", AsyncMock())
        assert result == test_value
        
        # Check statistics
        stats = cache.get_statistics()
        summary = stats.get_summary()
        assert summary['counters']['l1_hits'] == 1
        assert summary['counters']['cache_misses'] == 0
    
    @pytest.mark.asyncio
    async def test_multi_tier_l2_hit(self, mock_redis):
        """Test L2 (Redis) cache hit."""
        cache = MultiTierCache(memory_limit_mb=10, enable_redis=True, enable_disk=False)
        cache._redis_cache = mock_redis
        await cache.initialize()
        
        # Mock Redis hit
        test_value = "redis_value"
        mock_redis.get.return_value = test_value
        
        # Get should hit L2
        result = await cache.get_or_compute("test_key", AsyncMock())
        assert result == test_value
        
        # Verify Redis was called
        mock_redis.get.assert_called_once_with("test_key")
        
        # Check that value was promoted to L1
        assert cache._memory_cache.get("test_key") == test_value
    
    @pytest.mark.asyncio
    async def test_multi_tier_l3_hit(self, mock_redis, mock_disk):
        """Test L3 (disk) cache hit."""
        cache = MultiTierCache(memory_limit_mb=10, enable_redis=True, enable_disk=True)
        cache._redis_cache = mock_redis
        cache._disk_cache = mock_disk
        await cache.initialize()
        
        # Mock disk hit
        test_value = "disk_value"
        mock_disk.get.return_value = test_value
        
        # Get should hit L3
        result = await cache.get_or_compute("test_key", AsyncMock())
        assert result == test_value
        
        # Verify disk was called
        mock_disk.get.assert_called_once_with("test_key")
        
        # Check that value was promoted to L1 and L2
        assert cache._memory_cache.get("test_key") == test_value
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_tier_cache_miss(self):
        """Test cache miss and computation."""
        cache = MultiTierCache(memory_limit_mb=10, enable_redis=False, enable_disk=False)
        await cache.initialize()
        
        compute_called = False
        
        async def compute_fn():
            nonlocal compute_called
            compute_called = True
            return "computed_value"
        
        # Should miss and compute
        result = await cache.get_or_compute("test_key", compute_fn)
        assert result == "computed_value"
        assert compute_called
        
        # Check statistics
        stats = cache.get_statistics()
        summary = stats.get_summary()
        assert summary['counters']['cache_misses'] == 1
        
        # Should now be in L1
        assert cache._memory_cache.get("test_key") == "computed_value"


class TestCacheManager:
    """Test high-level cache manager."""
    
    def test_cache_manager_basic_operations(self):
        """Test basic cache manager operations."""
        manager = CacheManager(enable_multi_tier=False)
        
        # Create test result
        result = QueryResult(
            data=[{"id": 1}],
            total_count=1,
            page=1,
            page_size=10,
            execution_time_ms=5.0
        )
        
        # Cache result
        manager.cache_result("test_hash", result, ttl=3600, tags=["test"])
        
        # Get cached result
        cached = manager.get_cached_result("test_hash")
        assert cached is not None
        assert cached.result == result
        assert cached.tags == ["test"]
    
    def test_cache_manager_expiration(self):
        """Test cache expiration handling."""
        manager = CacheManager(enable_multi_tier=False)
        
        # Create expired result
        result = QueryResult(
            data=[],
            total_count=0,
            page=1,
            page_size=10,
            execution_time_ms=1.0
        )
        
        # Manually create expired entry
        past_time = time.time() - 7200
        cached = CachedResult(
            query_hash="test_hash",
            result=result,
            cached_at=past_time,
            ttl=3600
        )
        manager._query_cache["test_hash"] = cached
        
        # Should return None for expired entry
        assert manager.get_cached_result("test_hash") is None
        assert "test_hash" not in manager._query_cache
    
    def test_cache_manager_max_age(self):
        """Test max age parameter."""
        manager = CacheManager(enable_multi_tier=False)
        
        # Create result
        result = QueryResult(
            data=[],
            total_count=0,
            page=1,
            page_size=10,
            execution_time_ms=1.0
        )
        
        # Cache with long TTL
        manager.cache_result("test_hash", result, ttl=7200)
        
        # Should get with no max age
        assert manager.get_cached_result("test_hash") is not None
        
        # Should not get with very short max age
        assert manager.get_cached_result("test_hash", max_age=0) is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        manager = CacheManager(enable_multi_tier=False)
        
        # Add multiple cached results
        for i in range(10):
            result = QueryResult(
                data=[{"id": i}],
                total_count=1,
                page=1,
                page_size=10,
                execution_time_ms=1.0
            )
            manager.cache_result(f"hash_{i}", result)
        
        # Pattern-based invalidation
        manager.invalidate_cache(pattern="hash_")
        assert len(manager._query_cache) == 0
        
        # Add some back
        for i in range(5):
            result = QueryResult(
                data=[{"id": i}],
                total_count=1,
                page=1,
                page_size=10,
                execution_time_ms=1.0
            )
            manager.cache_result(f"test_{i}", result)
            manager.cache_result(f"other_{i}", result)
        
        # Invalidate only "test_" pattern
        manager.invalidate_cache(pattern="test_")
        assert len(manager._query_cache) == 5  # Only "other_" remain
        
        # Clear all
        manager.invalidate_cache()
        assert len(manager._query_cache) == 0


class TestCachePerformanceMetrics:
    """Test cache performance metrics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_cache_latency_tracking(self):
        """Test latency tracking across tiers."""
        cache = MultiTierCache(memory_limit_mb=10)
        await cache.initialize()
        
        # Generate some cache activity
        for i in range(100):
            cache._memory_cache.set(f"key_{i}", f"value_{i}")
        
        # Get from L1 (should be fast)
        for i in range(50):
            await cache.get_or_compute(f"key_{i}", AsyncMock())
        
        # Check latency percentiles
        stats = cache.get_statistics()
        summary = stats.get_summary()
        
        l1_latencies = summary['latency_percentiles']['l1']
        assert l1_latencies[0.5] < 1.0  # Median < 1ms
        assert l1_latencies[0.99] < 10.0  # 99th percentile < 10ms
    
    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculations."""
        stats = CacheStatistics()
        
        # Simulate cache activity
        for i in range(100):
            if i < 80:  # 80% hits
                stats.increment('l1_hits')
            else:
                stats.increment('cache_misses')
            stats.increment('total_requests')
        
        hit_rates = stats.get_hit_rates()
        assert hit_rates['overall'] == 0.8
        assert hit_rates['l1'] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])