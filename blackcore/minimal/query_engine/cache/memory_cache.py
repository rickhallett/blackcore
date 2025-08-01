"""High-performance memory cache implementation with LRU/LFU eviction policies."""

import time
import sys
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from typing import Any, Callable, Dict, Optional, Tuple
from dataclasses import dataclass, field
import heapq


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    
    key: str
    value: Any
    size_bytes: int
    created_at: float
    accessed_at: float
    access_count: int = 1
    ttl: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> None:
        """Update access metadata."""
        self.accessed_at = time.time()
        self.access_count += 1
    
    def get_age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


class BaseMemoryCache(ABC):
    """Base class for memory cache implementations."""
    
    __slots__ = ['_capacity_bytes', '_current_size_bytes', '_entries', '_lock', '_stats']
    
    def __init__(self, capacity_mb: int = 1024):
        """Initialize cache with capacity in MB."""
        self._capacity_bytes = capacity_mb * 1024 * 1024
        self._current_size_bytes = 0
        self._entries: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_evictions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self._entries.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                self._evict_entry(key)
                self._stats['expired_evictions'] += 1
                self._stats['misses'] += 1
                return None
            
            entry.access()
            self._on_access(key, entry)
            self._stats['hits'] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        size_bytes = self._estimate_size(value)
        
        with self._lock:
            # Remove existing entry if present
            if key in self._entries:
                self._evict_entry(key)
            
            # Check if new entry fits
            if size_bytes > self._capacity_bytes:
                return  # Entry too large for cache
            
            # Make room if needed
            while self._current_size_bytes + size_bytes > self._capacity_bytes:
                evict_key = self._select_eviction_candidate()
                if evict_key is None:
                    break
                self._evict_entry(evict_key)
                self._stats['evictions'] += 1
            
            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=size_bytes,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl
            )
            
            self._entries[key] = entry
            self._current_size_bytes += size_bytes
            self._on_insert(key, entry)
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._entries:
                self._evict_entry(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._entries.clear()
            self._current_size_bytes = 0
            self._on_clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
            
            return {
                'capacity_mb': self._capacity_bytes / (1024 * 1024),
                'used_mb': self._current_size_bytes / (1024 * 1024),
                'utilization': self._current_size_bytes / self._capacity_bytes,
                'entry_count': len(self._entries),
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'expired_evictions': self._stats['expired_evictions']
            }
    
    def resize(self, new_capacity_mb: int) -> None:
        """Resize cache capacity."""
        with self._lock:
            self._capacity_bytes = new_capacity_mb * 1024 * 1024
            
            # Evict entries if over new capacity
            while self._current_size_bytes > self._capacity_bytes:
                evict_key = self._select_eviction_candidate()
                if evict_key is None:
                    break
                self._evict_entry(evict_key)
                self._stats['evictions'] += 1
    
    def _evict_entry(self, key: str) -> None:
        """Remove entry from cache."""
        if key in self._entries:
            entry = self._entries[key]
            self._current_size_bytes -= entry.size_bytes
            del self._entries[key]
            self._on_evict(key)
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value in bytes."""
        return sys.getsizeof(value)
    
    @abstractmethod
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select entry to evict."""
        pass
    
    @abstractmethod
    def _on_access(self, key: str, entry: CacheEntry) -> None:
        """Handle entry access for eviction policy."""
        pass
    
    @abstractmethod
    def _on_insert(self, key: str, entry: CacheEntry) -> None:
        """Handle new entry insertion."""
        pass
    
    @abstractmethod
    def _on_evict(self, key: str) -> None:
        """Handle entry eviction."""
        pass
    
    @abstractmethod
    def _on_clear(self) -> None:
        """Handle cache clear."""
        pass


class LRUCache(BaseMemoryCache):
    """Least Recently Used cache implementation."""
    
    def __init__(self, capacity_mb: int = 1024):
        super().__init__(capacity_mb)
        self._access_order: OrderedDict[str, None] = OrderedDict()
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select least recently used entry."""
        if not self._access_order:
            return None
        # First item is least recently used
        return next(iter(self._access_order))
    
    def _on_access(self, key: str, entry: CacheEntry) -> None:
        """Move accessed entry to end."""
        self._access_order.move_to_end(key)
    
    def _on_insert(self, key: str, entry: CacheEntry) -> None:
        """Add new entry to end."""
        self._access_order[key] = None
    
    def _on_evict(self, key: str) -> None:
        """Remove from access order."""
        self._access_order.pop(key, None)
    
    def _on_clear(self) -> None:
        """Clear access order."""
        self._access_order.clear()


class LFUCache(BaseMemoryCache):
    """Least Frequently Used cache implementation."""
    
    def __init__(self, capacity_mb: int = 1024):
        super().__init__(capacity_mb)
        self._frequency_lists: Dict[int, OrderedDict[str, None]] = defaultdict(OrderedDict)
        self._key_frequencies: Dict[str, int] = {}
        self._min_frequency = 0
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select least frequently used entry."""
        if not self._key_frequencies:
            return None
        
        # Find non-empty frequency list starting from minimum
        while self._min_frequency in self._frequency_lists:
            freq_list = self._frequency_lists[self._min_frequency]
            if freq_list:
                # Return least recently used item from this frequency
                return next(iter(freq_list))
            else:
                # Clean up empty list and increment
                del self._frequency_lists[self._min_frequency]
                self._min_frequency += 1
        
        return None
    
    def _on_access(self, key: str, entry: CacheEntry) -> None:
        """Increment frequency and move to appropriate list."""
        old_freq = self._key_frequencies.get(key, 0)
        new_freq = entry.access_count
        
        # Remove from old frequency list
        if old_freq > 0 and old_freq in self._frequency_lists:
            self._frequency_lists[old_freq].pop(key, None)
            if not self._frequency_lists[old_freq]:
                del self._frequency_lists[old_freq]
                if old_freq == self._min_frequency:
                    self._min_frequency += 1
        
        # Add to new frequency list
        self._frequency_lists[new_freq][key] = None
        self._key_frequencies[key] = new_freq
    
    def _on_insert(self, key: str, entry: CacheEntry) -> None:
        """Add new entry with frequency 1."""
        self._frequency_lists[1][key] = None
        self._key_frequencies[key] = 1
        self._min_frequency = 1
    
    def _on_evict(self, key: str) -> None:
        """Remove from frequency tracking."""
        freq = self._key_frequencies.pop(key, 0)
        if freq in self._frequency_lists:
            self._frequency_lists[freq].pop(key, None)
            if not self._frequency_lists[freq]:
                del self._frequency_lists[freq]
    
    def _on_clear(self) -> None:
        """Clear frequency tracking."""
        self._frequency_lists.clear()
        self._key_frequencies.clear()
        self._min_frequency = 0


class MemoryCache(LRUCache):
    """Default memory cache using LRU eviction."""
    
    def __init__(self, capacity_mb: int = 1024):
        super().__init__(capacity_mb)
    
    async def get_or_compute(self, key: str, compute_fn: Callable, ttl: int = 3600) -> Any:
        """Get from cache or compute with timing."""
        # Try to get from cache
        result = self.get(key)
        if result is not None:
            return result
        
        # Compute value
        if hasattr(compute_fn, '__aiter__'):
            result = await compute_fn()
        else:
            result = compute_fn()
        
        # Cache result
        self.set(key, result, ttl)
        return result