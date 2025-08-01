"""Statistics collection for query optimization."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import time


class StatisticsCollector:
    """Collects and manages query execution statistics."""
    
    def __init__(self):
        """Initialize statistics collector."""
        self.query_stats: List[Dict[str, Any]] = []
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "disk_hits": 0
        }
        self.database_access_counts: Dict[str, int] = {}
        self.filter_usage_counts: Dict[str, int] = {}
        self.total_execution_time_ms = 0.0
        self.query_count = 0
    
    def record_query(self, database: str, filters: List[str], execution_time_ms: float, from_cache: bool):
        """Record query execution statistics."""
        self.query_count += 1
        self.total_execution_time_ms += execution_time_ms
        
        # Update database access counts
        self.database_access_counts[database] = self.database_access_counts.get(database, 0) + 1
        
        # Update filter usage counts
        for filter_field in filters:
            self.filter_usage_counts[filter_field] = self.filter_usage_counts.get(filter_field, 0) + 1
        
        # Update cache stats
        if from_cache:
            self.cache_stats["hits"] += 1
        else:
            self.cache_stats["misses"] += 1
        
        # Store detailed query stats
        self.query_stats.append({
            "timestamp": datetime.now(),
            "database": database,
            "filters": filters,
            "execution_time_ms": execution_time_ms,
            "from_cache": from_cache
        })
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get aggregated query statistics."""
        cache_total = self.cache_stats["hits"] + self.cache_stats["misses"]
        cache_hit_rate = self.cache_stats["hits"] / cache_total if cache_total > 0 else 0.0
        
        avg_execution_time = self.total_execution_time_ms / self.query_count if self.query_count > 0 else 0.0
        
        return {
            "total_queries": self.query_count,
            "cache_hit_rate": cache_hit_rate,
            "average_execution_time_ms": avg_execution_time,
            "popular_databases": dict(sorted(
                self.database_access_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "popular_filters": dict(sorted(
                self.filter_usage_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "cache_statistics": {
                "memory_hit_rate": self.cache_stats["memory_hits"] / cache_total if cache_total > 0 else 0.0,
                "redis_hit_rate": self.cache_stats["redis_hits"] / cache_total if cache_total > 0 else 0.0,
                "disk_hit_rate": self.cache_stats["disk_hits"] / cache_total if cache_total > 0 else 0.0
            }
        }
    
    def update_cache_tier_hit(self, tier: str):
        """Update cache tier hit statistics."""
        if tier == "memory":
            self.cache_stats["memory_hits"] += 1
        elif tier == "redis":
            self.cache_stats["redis_hits"] += 1
        elif tier == "disk":
            self.cache_stats["disk_hits"] += 1