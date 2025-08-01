"""Multi-tier cache management with Redis and disk backends."""

import asyncio
import json
import hashlib
import pickle
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Protocol
from dataclasses import dataclass
import aiofiles

from .memory_cache import MemoryCache, LRUCache
from .cache_statistics import CacheStatistics, CacheMetrics
from ..models import QueryResult


@dataclass
class CachedResult:
    """Wrapper for cached query results."""
    
    query_hash: str
    result: QueryResult
    cached_at: float
    ttl: int
    tags: List[str] = None
    
    def is_expired(self) -> bool:
        """Check if cached result has expired."""
        return time.time() - self.cached_at > self.ttl
    
    def age_seconds(self) -> float:
        """Get age of cached result in seconds."""
        return time.time() - self.cached_at


class RedisCache:
    """Redis cache implementation."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis cache."""
        self._redis_url = redis_url or "redis://localhost:6379"
        self._client = None
        self._connected = False
        
    async def connect(self):
        """Connect to Redis."""
        try:
            import aioredis
            self._client = await aioredis.create_redis_pool(self._redis_url)
            self._connected = True
        except Exception:
            # Redis not available, operate without it
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self._connected or not self._client:
            return None
            
        try:
            data = await self._client.get(key)
            if data:
                return pickle.loads(data)
        except Exception:
            pass
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis."""
        if not self._connected or not self._client:
            return False
            
        try:
            data = pickle.dumps(value)
            await self._client.setex(key, ttl, data)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis."""
        if not self._connected or not self._client:
            return False
            
        try:
            await self._client.delete(key)
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            await self._client.wait_closed()


class DiskCache:
    """Disk-based cache implementation."""
    
    def __init__(self, cache_dir: str = ".query_cache"):
        """Initialize disk cache."""
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(exist_ok=True)
        self._index_file = self._cache_dir / "index.json"
        self._index = self._load_index()
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from disk."""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_index(self):
        """Save cache index to disk."""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f)
        except Exception:
            pass
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use first 2 chars of hash for directory sharding
        key_hash = hashlib.md5(key.encode()).hexdigest()
        shard = key_hash[:2]
        shard_dir = self._cache_dir / shard
        shard_dir.mkdir(exist_ok=True)
        return shard_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        if key not in self._index:
            return None
        
        entry = self._index[key]
        if time.time() - entry['cached_at'] > entry['ttl']:
            # Expired
            await self.delete(key)
            return None
        
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        try:
            async with aiofiles.open(cache_path, 'rb') as f:
                data = await f.read()
                return pickle.loads(data)
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in disk cache."""
        cache_path = self._get_cache_path(key)
        
        try:
            data = pickle.dumps(value)
            async with aiofiles.open(cache_path, 'wb') as f:
                await f.write(data)
            
            self._index[key] = {
                'cached_at': time.time(),
                'ttl': ttl,
                'size': len(data)
            }
            self._save_index()
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from disk cache."""
        if key in self._index:
            del self._index[key]
            self._save_index()
        
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                cache_path.unlink()
                return True
            except Exception:
                pass
        
        return False
    
    def cleanup_expired(self):
        """Clean up expired entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._index.items():
            if current_time - entry['cached_at'] > entry['ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            asyncio.create_task(self.delete(key))


class MultiTierCache:
    """Multi-tier cache with L1 (memory), L2 (Redis), L3 (disk)."""
    
    def __init__(self, memory_limit_mb: int = 1024, enable_redis: bool = True, enable_disk: bool = True):
        """Initialize multi-tier cache."""
        self._memory_cache = MemoryCache(memory_limit_mb)
        self._redis_cache = RedisCache() if enable_redis else None
        self._disk_cache = DiskCache() if enable_disk else None
        self._stats = CacheStatistics()
        self._initialized = False
    
    async def initialize(self):
        """Initialize cache connections."""
        if self._redis_cache:
            await self._redis_cache.connect()
        self._initialized = True
    
    async def get_or_compute(self, key: str, compute_fn: Callable, ttl: int = 3600, tags: List[str] = None) -> Any:
        """Get from cache or compute with timing."""
        start_time = time.time()
        
        # L1: Memory cache (microseconds)
        result = self._memory_cache.get(key)
        if result is not None:
            duration_ms = (time.time() - start_time) * 1000
            self._stats.record_metric(CacheMetrics(
                operation='get',
                duration_ms=duration_ms,
                timestamp=time.time(),
                cache_tier='l1',
                hit=True,
                key=key
            ))
            self._stats.increment('l1_hits')
            return result
        
        # L2: Redis cache (milliseconds)
        if self._redis_cache:
            result = await self._redis_cache.get(key)
            if result is not None:
                duration_ms = (time.time() - start_time) * 1000
                self._stats.record_metric(CacheMetrics(
                    operation='get',
                    duration_ms=duration_ms,
                    timestamp=time.time(),
                    cache_tier='l2',
                    hit=True,
                    key=key
                ))
                self._stats.increment('l2_hits')
                # Promote to L1
                self._memory_cache.set(key, result, ttl)
                return result
        
        # L3: Disk cache (milliseconds to seconds)
        if self._disk_cache:
            result = await self._disk_cache.get(key)
            if result is not None:
                duration_ms = (time.time() - start_time) * 1000
                self._stats.record_metric(CacheMetrics(
                    operation='get',
                    duration_ms=duration_ms,
                    timestamp=time.time(),
                    cache_tier='l3',
                    hit=True,
                    key=key
                ))
                self._stats.increment('l3_hits')
                # Promote to L1 and L2
                self._memory_cache.set(key, result, ttl)
                if self._redis_cache:
                    await self._redis_cache.set(key, result, ttl)
                return result
        
        # Cache miss - compute result
        self._stats.increment('cache_misses')
        compute_start = time.time()
        
        if asyncio.iscoroutinefunction(compute_fn):
            result = await compute_fn()
        else:
            result = compute_fn()
        
        compute_duration_ms = (time.time() - compute_start) * 1000
        self._stats.record_metric(CacheMetrics(
            operation='compute',
            duration_ms=compute_duration_ms,
            timestamp=time.time(),
            cache_tier='none',
            hit=False,
            key=key
        ))
        
        # Cache result in all tiers
        await self._cache_result(key, result, ttl, tags)
        
        return result
    
    async def _cache_result(self, key: str, result: Any, ttl: int, tags: List[str] = None):
        """Cache result in all available tiers."""
        # L1: Memory
        self._memory_cache.set(key, result, ttl)
        
        # L2: Redis
        if self._redis_cache:
            await self._redis_cache.set(key, result, ttl)
        
        # L3: Disk
        if self._disk_cache:
            await self._disk_cache.set(key, result, ttl)
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache statistics."""
        return self._stats
    
    async def invalidate(self, pattern: Optional[str] = None, tags: Optional[List[str]] = None):
        """Invalidate cached entries."""
        # Simple implementation - could be enhanced with pattern matching
        if pattern is None:
            self._memory_cache.clear()
            # Would need to implement clear for Redis and disk caches
    
    async def close(self):
        """Close cache connections."""
        if self._redis_cache:
            await self._redis_cache.close()


class CacheManager:
    """High-level cache manager implementing the Protocol interface."""
    
    def __init__(self, enable_multi_tier: bool = True):
        """Initialize cache manager."""
        if enable_multi_tier:
            self._cache = MultiTierCache()
        else:
            self._cache = MemoryCache()
        self._query_cache: Dict[str, CachedResult] = {}
    
    async def initialize(self):
        """Initialize cache system."""
        if isinstance(self._cache, MultiTierCache):
            await self._cache.initialize()
    
    def get_cached_result(self, query_hash: str, max_age: Optional[int] = None) -> Optional[CachedResult]:
        """Get cached query result."""
        if query_hash in self._query_cache:
            cached = self._query_cache[query_hash]
            
            # Check expiration
            if cached.is_expired():
                del self._query_cache[query_hash]
                return None
            
            # Check max age if specified
            if max_age and cached.age_seconds() > max_age:
                return None
            
            return cached
        
        return None
    
    def cache_result(self, query_hash: str, result: Any, ttl: int = 3600, tags: List[str] = None) -> None:
        """Cache query result."""
        cached_result = CachedResult(
            query_hash=query_hash,
            result=result,
            cached_at=time.time(),
            ttl=ttl,
            tags=tags or []
        )
        
        self._query_cache[query_hash] = cached_result
        
        # Also cache in multi-tier if available
        if hasattr(self._cache, 'set'):
            self._cache.set(query_hash, result, ttl)
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache statistics."""
        if hasattr(self._cache, 'get_statistics'):
            return self._cache.get_statistics()
        
        # Return basic stats for simple cache
        stats = CacheStatistics()
        return stats
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """Invalidate cached results."""
        if pattern:
            # Pattern-based invalidation
            keys_to_remove = [k for k in self._query_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._query_cache[key]
        else:
            # Clear all
            self._query_cache.clear()
            
        if hasattr(self._cache, 'clear'):
            self._cache.clear()