"""Caching implementation for relationship data.

This module provides caching mechanisms to improve performance
of relationship resolution operations.
"""

import time
import hashlib
import json
from typing import Any, Optional, Dict, List
from collections import OrderedDict
from threading import Lock

from .interfaces import RelationshipCache


class LRURelationshipCache:
    """Least Recently Used cache for relationship data."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = Lock()
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        with self.lock:
            self.stats.requests += 1
            
            if key not in self.cache:
                self.stats.misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self.cache[key]
                self.stats.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.stats.hits += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        with self.lock:
            # Remove oldest items if at capacity
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats.evictions += 1
            
            # Create cache entry
            entry = CacheEntry(
                value=value,
                ttl=ttl or self.default_ttl
            )
            
            self.cache[key] = entry
            self.stats.sets += 1
    
    def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        with self.lock:
            keys_to_remove = []
            
            # Simple pattern matching (supports * wildcard)
            if '*' in pattern:
                prefix = pattern.split('*')[0]
                for key in self.cache:
                    if key.startswith(prefix):
                        keys_to_remove.append(key)
            else:
                # Exact match
                if pattern in self.cache:
                    keys_to_remove.append(pattern)
            
            # Remove matched keys
            for key in keys_to_remove:
                del self.cache[key]
                self.stats.invalidations += 1
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self.lock:
            self.cache.clear()
            self.stats.clears += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "requests": self.stats.requests,
                "hit_rate": self.stats.hit_rate,
                "sets": self.stats.sets,
                "evictions": self.stats.evictions,
                "invalidations": self.stats.invalidations,
                "clears": self.stats.clears
            }


class TwoLevelCache:
    """Two-level cache with fast L1 and larger L2."""
    
    def __init__(
        self,
        l1_size: int = 100,
        l2_size: int = 1000,
        l1_ttl: int = 300,
        l2_ttl: int = 3600
    ):
        """Initialize two-level cache.
        
        Args:
            l1_size: Size of L1 cache (fast, small)
            l2_size: Size of L2 cache (slower, larger)
            l1_ttl: TTL for L1 cache
            l2_ttl: TTL for L2 cache
        """
        self.l1 = LRURelationshipCache(l1_size, l1_ttl)
        self.l2 = LRURelationshipCache(l2_size, l2_ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks L1 then L2)."""
        # Check L1
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # Check L2
        value = self.l2.get(key)
        if value is not None:
            # Promote to L1
            self.l1.set(key, value)
            return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in both cache levels."""
        self.l1.set(key, value, ttl)
        self.l2.set(key, value, ttl)
    
    def invalidate(self, pattern: str) -> None:
        """Invalidate in both levels."""
        self.l1.invalidate(pattern)
        self.l2.invalidate(pattern)
    
    def clear(self) -> None:
        """Clear both levels."""
        self.l1.clear()
        self.l2.clear()


class CacheKeyBuilder:
    """Builds cache keys for relationship queries."""
    
    @staticmethod
    def build_relationship_key(
        entity_id: str,
        relationship_type: str,
        depth: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build cache key for relationship query."""
        key_parts = [
            "rel",
            entity_id,
            relationship_type,
            str(depth)
        ]
        
        if filters:
            # Sort filters for consistent keys
            filter_str = json.dumps(filters, sort_keys=True)
            filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]
            key_parts.append(filter_hash)
        
        return ":".join(key_parts)
    
    @staticmethod
    def build_path_key(
        from_id: str,
        to_id: str,
        max_length: int
    ) -> str:
        """Build cache key for path query."""
        return f"path:{from_id}:{to_id}:{max_length}"
    
    @staticmethod
    def build_graph_key(
        root_ids: List[str],
        max_depth: int
    ) -> str:
        """Build cache key for graph query."""
        # Sort IDs for consistent keys
        sorted_ids = sorted(root_ids)
        ids_hash = hashlib.md5(":".join(sorted_ids).encode()).hexdigest()[:8]
        return f"graph:{ids_hash}:{max_depth}"


class CacheEntry:
    """Single cache entry with TTL support."""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


class CacheStats:
    """Cache statistics tracker."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.requests = 0
        self.sets = 0
        self.evictions = 0
        self.invalidations = 0
        self.clears = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.requests == 0:
            return 0.0
        return self.hits / self.requests