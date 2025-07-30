"""Redis cache implementation."""

import pickle
import asyncio
from typing import Any, Optional
import logging

try:
    import aioredis
except ImportError:
    aioredis = None

from ..interfaces import ICache

logger = logging.getLogger(__name__)


class RedisCache(ICache):
    """Redis-based cache implementation."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "blackcore:",
        **redis_kwargs
    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis_kwargs = redis_kwargs
        self.redis = None
        self._lock = asyncio.Lock()
    
    async def _ensure_connection(self):
        """Ensure Redis connection is established."""
        if self.redis is None:
            if aioredis is None:
                raise ImportError("aioredis is required for RedisCache")
            
            self.redis = await aioredis.create_redis_pool(
                self.redis_url,
                **self.redis_kwargs
            )
    
    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        await self._ensure_connection()
        
        redis_key = self._make_key(key)
        
        try:
            data = await self.redis.get(redis_key)
            if data is None:
                return None
            
            # Deserialize
            return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Failed to get cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        await self._ensure_connection()
        
        redis_key = self._make_key(key)
        
        try:
            # Serialize value
            data = pickle.dumps(value)
            
            # Set with optional expiry
            if ttl:
                await self.redis.set(redis_key, data, expire=ttl)
            else:
                await self.redis.set(redis_key, data)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        await self._ensure_connection()
        
        redis_key = self._make_key(key)
        
        try:
            result = await self.redis.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        await self._ensure_connection()
        
        try:
            await self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            self.redis = None