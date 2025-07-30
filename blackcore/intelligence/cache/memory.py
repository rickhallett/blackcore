"""In-memory cache implementation."""

import time
import asyncio
from collections import OrderedDict
from typing import Any, Optional
import logging

from ..interfaces import ICache

logger = logging.getLogger(__name__)


class InMemoryCache(ICache):
    """In-memory LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self.cache:
                return None
            
            value, expiry = self.cache[key]
            
            # Check if expired
            if expiry and time.time() > expiry:
                del self.cache[key]
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        async with self._lock:
            # Calculate expiry time
            expiry = time.time() + ttl if ttl else None
            
            # If key exists, update it
            if key in self.cache:
                self.cache[key] = (value, expiry)
                self.cache.move_to_end(key)
            else:
                # Add new key
                self.cache[key] = (value, expiry)
                
                # Evict LRU if needed
                if len(self.cache) > self.max_size:
                    # Remove least recently used (first item)
                    self.cache.popitem(last=False)
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
            return True
    
    async def close(self):
        """Close cache (no-op for in-memory)."""
        pass