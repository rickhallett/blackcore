"""Tests for cache implementations."""

import pytest
import asyncio
import time
import pickle
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict
import pytest_asyncio

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

class TestInMemoryCache:
    """Tests for in-memory cache implementation."""
    
    def test_cache_initialization(self):
        """Test cache initialization with default and custom size."""
        from blackcore.intelligence.cache import InMemoryCache
        
        # Default size
        cache = InMemoryCache()
        assert cache.max_size == 1000
        assert len(cache.cache) == 0
        
        # Custom size
        cache = InMemoryCache(max_size=500)
        assert cache.max_size == 500
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        # Set value
        result = await cache.set("key1", "value1")
        assert result is True
        
        # Get value
        value = await cache.get("key1")
        assert value == "value1"
        
        # Get non-existent key
        value = await cache.get("non_existent")
        assert value is None
    
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        # Set with TTL
        await cache.set("key1", "value1", ttl=1)  # 1 second TTL
        
        # Should exist immediately
        assert await cache.get("key1") == "value1"
        
        # Mock time to simulate expiration
        with patch('time.time', return_value=time.time() + 2):
            # Should be expired
            assert await cache.get("key1") is None
    
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache(max_size=3)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it most recently used
        await cache.get("key1")
        
        # Add new item - should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        # Check what's in cache
        assert await cache.get("key1") == "value1"  # Still there (recently used)
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New item
    
    async def test_delete_operation(self):
        """Test delete operation."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        # Set and delete
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None
        
        # Delete non-existent key
        result = await cache.delete("non_existent")
        assert result is False
    
    async def test_clear_operation(self):
        """Test clear operation."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        # Add multiple items
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Clear all
        result = await cache.clear()
        assert result is True
        
        # All should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None
        assert len(cache.cache) == 0
    
    async def test_concurrent_access(self):
        """Test thread safety with concurrent access."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        async def set_values(start: int, count: int):
            for i in range(start, start + count):
                await cache.set(f"key{i}", f"value{i}")
        
        # Concurrent sets
        await asyncio.gather(
            set_values(0, 50),
            set_values(50, 50),
            set_values(100, 50)
        )
        
        # Verify all values
        for i in range(150):
            assert await cache.get(f"key{i}") == f"value{i}"
    
    async def test_complex_data_types(self):
        """Test storing complex data types."""
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        # Test various data types
        test_data = {
            "dict": {"a": 1, "b": [2, 3, 4]},
            "list": [1, 2, {"nested": True}],
            "tuple": (1, 2, 3),
            "set": {1, 2, 3},
            "none": None,
            "bool": True,
            "float": 3.14
        }
        
        for key, value in test_data.items():
            await cache.set(key, value)
            retrieved = await cache.get(key)
            assert retrieved == value


class TestRedisCache:
    """Tests for Redis cache implementation."""
    
    @pytest.fixture
    def mock_redis_pool(self):
        """Mock Redis connection pool."""
        pool = AsyncMock()
        pool.get = AsyncMock()
        pool.set = AsyncMock(return_value=True)
        pool.delete = AsyncMock(return_value=1)
        pool.flushdb = AsyncMock()
        pool.close = AsyncMock()
        pool.wait_closed = AsyncMock()
        return pool
    
    @pytest_asyncio.fixture
    async def redis_cache(self, mock_redis_pool):
        """Create Redis cache with mocked connection."""
        from blackcore.intelligence.cache import RedisCache
        
        # Mock aioredis module
        with patch('blackcore.intelligence.cache.redis.aioredis') as mock_aioredis:
            mock_aioredis.create_redis_pool = AsyncMock(return_value=mock_redis_pool)
            cache = RedisCache()
            await cache._ensure_connection()
            return cache
    
    async def test_redis_initialization(self):
        """Test Redis cache initialization."""
        from blackcore.intelligence.cache import RedisCache
        
        # Default initialization
        cache = RedisCache()
        assert cache.redis_url == "redis://localhost:6379"
        assert cache.key_prefix == "blackcore:"
        assert cache.redis is None
        
        # Custom initialization
        cache = RedisCache(
            redis_url="redis://custom:6380",
            key_prefix="custom:"
        )
        assert cache.redis_url == "redis://custom:6380"
        assert cache.key_prefix == "custom:"
    
    async def test_redis_set_and_get(self, redis_cache, mock_redis_pool):
        """Test Redis set and get operations."""
        # Test set
        result = await redis_cache.set("test_key", {"data": "value"})
        assert result is True
        
        # Verify set was called with serialized data
        mock_redis_pool.set.assert_called_once()
        call_args = mock_redis_pool.set.call_args
        assert call_args[0][0] == "blackcore:test_key"
        assert pickle.loads(call_args[0][1]) == {"data": "value"}
        
        # Test get
        mock_redis_pool.get.return_value = pickle.dumps({"data": "value"})
        value = await redis_cache.get("test_key")
        assert value == {"data": "value"}
        
        # Test get non-existent
        mock_redis_pool.get.return_value = None
        value = await redis_cache.get("non_existent")
        assert value is None
    
    async def test_redis_ttl(self, redis_cache, mock_redis_pool):
        """Test Redis TTL setting."""
        await redis_cache.set("test_key", "value", ttl=300)
        
        # Verify expire was set
        call_args = mock_redis_pool.set.call_args
        assert call_args[1]['expire'] == 300
    
    async def test_redis_delete(self, redis_cache, mock_redis_pool):
        """Test Redis delete operation."""
        # Successful delete
        result = await redis_cache.delete("test_key")
        assert result is True
        mock_redis_pool.delete.assert_called_with("blackcore:test_key")
        
        # Failed delete
        mock_redis_pool.delete.return_value = 0
        result = await redis_cache.delete("non_existent")
        assert result is False
    
    async def test_redis_clear(self, redis_cache, mock_redis_pool):
        """Test Redis clear operation."""
        result = await redis_cache.clear()
        assert result is True
        mock_redis_pool.flushdb.assert_called_once()
    
    async def test_redis_connection_failure(self):
        """Test handling of Redis connection failures."""
        from blackcore.intelligence.cache import RedisCache
        
        with patch('blackcore.intelligence.cache.redis.aioredis') as mock_aioredis:
            mock_aioredis.create_redis_pool = AsyncMock(side_effect=Exception("Connection failed"))
            cache = RedisCache()
            
            # Operations should handle connection failure gracefully
            with pytest.raises(Exception) as exc_info:
                await cache.get("test_key")
            assert "Connection failed" in str(exc_info.value)
    
    async def test_redis_serialization_error(self, redis_cache, mock_redis_pool):
        """Test handling of serialization errors."""
        # Return invalid pickle data
        mock_redis_pool.get.return_value = b"invalid pickle data"
        
        # Should handle gracefully
        value = await redis_cache.get("test_key")
        assert value is None
    
    async def test_redis_key_prefix(self, redis_cache):
        """Test key prefix handling."""
        assert redis_cache._make_key("test") == "blackcore:test"
        assert redis_cache._make_key("") == "blackcore:"
        assert redis_cache._make_key("a:b:c") == "blackcore:a:b:c"


class TestCacheFactory:
    """Tests for cache factory."""
    
    async def test_create_memory_cache(self):
        """Test creating memory cache through factory."""
        from blackcore.intelligence.cache import create_cache
        from blackcore.intelligence.config import CacheConfig
        
        config = CacheConfig(backend="memory", max_size=500)
        cache = create_cache(config)
        
        assert cache.__class__.__name__ == "InMemoryCache"
        assert cache.max_size == 500
    
    async def test_create_redis_cache(self):
        """Test creating Redis cache through factory."""
        from blackcore.intelligence.cache import create_cache
        from blackcore.intelligence.config import CacheConfig
        
        config = CacheConfig(
            backend="redis",
            connection_params={"redis_url": "redis://test:6379"}
        )
        cache = create_cache(config)
        
        assert cache.__class__.__name__ == "RedisCache"
        assert cache.redis_url == "redis://test:6379"
    
    def test_invalid_cache_backend(self):
        """Test error handling for invalid cache backend."""
        from blackcore.intelligence.cache import create_cache
        from blackcore.intelligence.config import CacheConfig
        
        config = CacheConfig(backend="invalid")
        
        with pytest.raises(ValueError) as exc_info:
            create_cache(config)
        assert "Unknown cache backend" in str(exc_info.value)


class TestCacheIntegration:
    """Integration tests for cache with other components."""
    
    async def test_cache_with_llm_client(self):
        """Test cache integration with LLM client."""
        from blackcore.intelligence.llm.client import LLMClient
        from blackcore.intelligence.cache import InMemoryCache
        
        # Setup
        cache = InMemoryCache()
        mock_provider = Mock()
        mock_provider.estimate_tokens = Mock(return_value=10)
        mock_provider.complete = AsyncMock(return_value="Response")
        
        client = LLMClient(provider=mock_provider, cache=cache)
        
        # First call - cache miss
        result1 = await client.complete("Test prompt", cache_ttl=3600)
        assert result1 == "Response"
        assert client.metrics["cache_misses"] == 1
        assert mock_provider.complete.call_count == 1
        
        # Second call - cache hit
        result2 = await client.complete("Test prompt", cache_ttl=3600)
        assert result2 == "Response"
        assert client.metrics["cache_hits"] == 1
        assert mock_provider.complete.call_count == 1  # Not called again
    
    async def test_cache_key_generation(self):
        """Test cache key generation for different parameters."""
        from blackcore.intelligence.llm.client import LLMClient
        from blackcore.intelligence.cache import InMemoryCache
        
        cache = InMemoryCache()
        mock_provider = Mock()
        mock_provider.estimate_tokens = Mock(return_value=10)
        
        client = LLMClient(provider=mock_provider, cache=cache)
        
        # Different keys for different parameters
        key1 = client._cache_key("prompt1", "system1", 0.7, "gpt-4")
        key2 = client._cache_key("prompt1", "system1", 0.7, "gpt-4")
        key3 = client._cache_key("prompt2", "system1", 0.7, "gpt-4")
        key4 = client._cache_key("prompt1", "system2", 0.7, "gpt-4")
        key5 = client._cache_key("prompt1", "system1", 0.8, "gpt-4")
        key6 = client._cache_key("prompt1", "system1", 0.7, "gpt-3.5")
        
        # Same parameters = same key
        assert key1 == key2
        
        # Different parameters = different keys
        assert key1 != key3
        assert key1 != key4
        assert key1 != key5
        assert key1 != key6