"""Cache management for analytics performance optimization."""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import hashlib
import pickle

from .models import (
    AnalyticsRequest, NetworkAnalysisRequest, TimelineRequest, CacheKey, CacheEntry,
    OverviewResponse, NetworkAnalysisResponse, TimelineResponse
)

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for analytics results to improve performance."""
    
    def __init__(
        self, 
        cache_dir: str = ".cache/analytics",
        default_ttl: int = 300,
        max_cache_size: int = 100
    ):
        """Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default TTL in seconds
            max_cache_size: Maximum number of cache entries
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        
        # In-memory cache for frequently accessed items
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
        logger.debug(f"CacheManager initialized with cache_dir: {cache_dir}")
    
    async def get_overview_metrics(self, request: AnalyticsRequest) -> Optional[OverviewResponse]:
        """Get cached overview metrics.
        
        Args:
            request: Analytics request
            
        Returns:
            Cached overview response if available
        """
        try:
            cache_key = self._generate_cache_key('overview', request.dict())
            cached_entry = await self._get_cached_entry(cache_key)
            
            if cached_entry:
                self._cache_stats['hits'] += 1
                return OverviewResponse(**cached_entry.data)
            
            self._cache_stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached overview metrics: {e}")
            return None
    
    async def cache_overview_metrics(self, request: AnalyticsRequest, response: OverviewResponse):
        """Cache overview metrics.
        
        Args:
            request: Analytics request
            response: Overview response to cache
        """
        try:
            cache_key = self._generate_cache_key('overview', request.dict())
            await self._store_cached_entry(cache_key, response.dict(), self.default_ttl)
        except Exception as e:
            logger.error(f"Error caching overview metrics: {e}")
    
    async def get_network_analysis(self, request: NetworkAnalysisRequest) -> Optional[NetworkAnalysisResponse]:
        """Get cached network analysis.
        
        Args:
            request: Network analysis request
            
        Returns:
            Cached network analysis response if available
        """
        try:
            cache_key = self._generate_cache_key('network', request.dict())
            cached_entry = await self._get_cached_entry(cache_key)
            
            if cached_entry:
                self._cache_stats['hits'] += 1
                return NetworkAnalysisResponse(**cached_entry.data)
            
            self._cache_stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached network analysis: {e}")
            return None
    
    async def cache_network_analysis(self, request: NetworkAnalysisRequest, response: NetworkAnalysisResponse):
        """Cache network analysis.
        
        Args:
            request: Network analysis request
            response: Network analysis response to cache
        """
        try:
            cache_key = self._generate_cache_key('network', request.dict())
            # Network analysis can be cached longer as it changes less frequently
            await self._store_cached_entry(cache_key, response.dict(), self.default_ttl * 6)
        except Exception as e:
            logger.error(f"Error caching network analysis: {e}")
    
    async def get_timeline_analysis(self, request: TimelineRequest) -> Optional[TimelineResponse]:
        """Get cached timeline analysis.
        
        Args:
            request: Timeline request
            
        Returns:
            Cached timeline response if available
        """
        try:
            cache_key = self._generate_cache_key('timeline', request.dict())
            cached_entry = await self._get_cached_entry(cache_key)
            
            if cached_entry:
                self._cache_stats['hits'] += 1
                return TimelineResponse(**cached_entry.data)
            
            self._cache_stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached timeline analysis: {e}")
            return None
    
    async def cache_timeline_analysis(self, request: TimelineRequest, response: TimelineResponse):
        """Cache timeline analysis.
        
        Args:
            request: Timeline request
            response: Timeline response to cache
        """
        try:
            cache_key = self._generate_cache_key('timeline', request.dict())
            await self._store_cached_entry(cache_key, response.dict(), self.default_ttl * 2)
        except Exception as e:
            logger.error(f"Error caching timeline analysis: {e}")
    
    async def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match cache keys (None = all)
        """
        try:
            if pattern is None:
                # Clear all cache
                self._memory_cache.clear()
                
                # Clear file cache
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                
                logger.info("All cache entries invalidated")
            else:
                # Clear matching entries
                keys_to_remove = []
                for key in self._memory_cache:
                    if pattern in key:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._memory_cache[key]
                
                # Clear matching file cache
                for cache_file in self.cache_dir.glob(f"*{pattern}*.cache"):
                    cache_file.unlink()
                
                logger.info(f"Cache entries matching '{pattern}' invalidated")
                
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = self._cache_stats['hits'] / total_requests if total_requests > 0 else 0.0
        
        return {
            'hits': self._cache_stats['hits'],
            'misses': self._cache_stats['misses'],
            'evictions': self._cache_stats['evictions'],
            'hit_rate': hit_rate,
            'memory_cache_size': len(self._memory_cache),
            'file_cache_size': len(list(self.cache_dir.glob("*.cache")))
        }
    
    async def cleanup(self):
        """Cleanup expired cache entries and perform maintenance."""
        try:
            # Clean memory cache
            expired_keys = []
            for key, entry in self._memory_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._memory_cache[key]
            
            # Clean file cache
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry_data = pickle.load(f)
                        entry = CacheEntry(**entry_data)
                        
                        if entry.is_expired():
                            cache_file.unlink()
                            
                except Exception as e:
                    logger.warning(f"Error checking cache file {cache_file}: {e}")
                    # Remove corrupted cache file
                    cache_file.unlink()
            
            logger.debug(f"Cache cleanup completed. Removed {len(expired_keys)} expired entries")
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def _generate_cache_key(self, endpoint: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for request.
        
        Args:
            endpoint: API endpoint name
            parameters: Request parameters
            
        Returns:
            Cache key string
        """
        # Remove timestamps and other volatile parameters for better cache efficiency
        stable_params = parameters.copy()
        
        # Remove volatile fields
        volatile_fields = ['refresh_cache', 'timestamp']
        for field in volatile_fields:
            stable_params.pop(field, None)
        
        # Convert datetime objects to strings for hashing
        for key, value in stable_params.items():
            if isinstance(value, datetime):
                stable_params[key] = value.isoformat()
        
        # Generate hash
        param_string = json.dumps(stable_params, sort_keys=True, default=str)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        
        return f"analytics:{endpoint}:{param_hash}"
    
    async def _get_cached_entry(self, cache_key: str) -> Optional[CacheEntry]:
        """Get cached entry by key.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached entry if available and not expired
        """
        try:
            # Check memory cache first
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                if not entry.is_expired():
                    entry.access_count += 1
                    return entry
                else:
                    # Remove expired entry
                    del self._memory_cache[cache_key]
            
            # Check file cache
            cache_file = self.cache_dir / f"{cache_key}.cache"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    entry_data = pickle.load(f)
                    entry = CacheEntry(**entry_data)
                    
                    if not entry.is_expired():
                        # Promote to memory cache if frequently accessed
                        entry.access_count += 1
                        if entry.access_count > 2:  # Promote after 3 accesses
                            self._memory_cache[cache_key] = entry
                            self._ensure_memory_cache_size()
                        
                        return entry
                    else:
                        # Remove expired file
                        cache_file.unlink()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached entry {cache_key}: {e}")
            return None
    
    async def _store_cached_entry(self, cache_key: str, data: Dict[str, Any], ttl: int):
        """Store entry in cache.
        
        Args:
            cache_key: Cache key
            data: Data to cache
            ttl: Time to live in seconds
        """
        try:
            entry = CacheEntry(
                key=cache_key,
                data=data,
                ttl_seconds=ttl,
                access_count=1
            )
            
            # Store in memory cache
            self._memory_cache[cache_key] = entry
            self._ensure_memory_cache_size()
            
            # Store in file cache for persistence
            cache_file = self.cache_dir / f"{cache_key}.cache"
            with open(cache_file, 'wb') as f:
                pickle.dump(entry.dict(), f)
            
        except Exception as e:
            logger.error(f"Error storing cached entry {cache_key}: {e}")
    
    def _ensure_memory_cache_size(self):
        """Ensure memory cache doesn't exceed maximum size."""
        while len(self._memory_cache) > self.max_cache_size:
            # Remove least recently used entry (simplified LRU)
            oldest_key = min(self._memory_cache.keys(), 
                           key=lambda k: self._memory_cache[k].created_at)
            del self._memory_cache[oldest_key]
            self._cache_stats['evictions'] += 1
    
    async def preload_cache(self, requests: List[Dict[str, Any]]):
        """Preload cache with common requests.
        
        Args:
            requests: List of request dictionaries to preload
        """
        try:
            logger.info(f"Preloading cache with {len(requests)} requests")
            
            # This would typically trigger analytics calculations
            # For now, just log the intent
            for request in requests:
                logger.debug(f"Would preload cache for: {request}")
            
        except Exception as e:
            logger.error(f"Error preloading cache: {e}")
    
    def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health metrics.
        
        Returns:
            Dictionary with cache health information
        """
        try:
            stats = self.get_cache_stats()
            
            # Calculate health score based on hit rate and cache utilization
            hit_rate = stats['hit_rate']
            memory_utilization = stats['memory_cache_size'] / self.max_cache_size
            
            health_score = (hit_rate * 0.7) + (min(memory_utilization, 1.0) * 0.3)
            
            if health_score > 0.8:
                health_status = 'excellent'
            elif health_score > 0.6:
                health_status = 'good'
            elif health_score > 0.4:
                health_status = 'fair'
            else:
                health_status = 'poor'
            
            return {
                'health_status': health_status,
                'health_score': health_score,
                'hit_rate': hit_rate,
                'memory_utilization': memory_utilization,
                'total_entries': stats['memory_cache_size'] + stats['file_cache_size'],
                'recommendations': self._get_cache_recommendations(stats)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache health: {e}")
            return {
                'health_status': 'unknown',
                'health_score': 0.0,
                'error': str(e)
            }
    
    def _get_cache_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Get cache optimization recommendations.
        
        Args:
            stats: Cache statistics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if stats['hit_rate'] < 0.5:
            recommendations.append("Consider increasing cache TTL to improve hit rate")
        
        if stats['memory_cache_size'] < self.max_cache_size * 0.5:
            recommendations.append("Memory cache underutilized - consider preloading common queries")
        
        if stats['evictions'] > stats['hits'] * 0.1:
            recommendations.append("High eviction rate - consider increasing max cache size")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal")
        
        return recommendations