"""Cache statistics and metrics tracking."""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import threading


@dataclass
class CacheMetrics:
    """Performance metrics for cache operations."""
    
    operation: str
    duration_ms: float
    timestamp: float
    cache_tier: str
    hit: bool
    key: Optional[str] = None
    size_bytes: Optional[int] = None


@dataclass 
class PerformanceMetrics:
    """Track performance metrics."""
    
    execution_time_ms: float
    memory_used_mb: float
    cache_hit_rate: float
    rows_processed: int
    
    def bottleneck(self) -> str:
        """Identify performance bottleneck."""
        if self.cache_hit_rate < 0.7:
            return "cache_misses"
        elif self.memory_used_mb > 1000:
            return "memory_pressure"
        elif self.execution_time_ms > 1000:
            return "slow_execution"
        return "none"


class CacheStatistics:
    """Comprehensive cache statistics tracking."""
    
    def __init__(self, window_size: int = 10000):
        """Initialize statistics tracker."""
        self._window_size = window_size
        self._metrics_window: deque[CacheMetrics] = deque(maxlen=window_size)
        self._counters = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'cache_misses': 0,
            'total_requests': 0,
            'evictions': 0,
            'expirations': 0
        }
        self._lock = threading.RLock()
        self._start_time = time.time()
        
        # Track latency percentiles
        self._latency_buckets = {
            'l1': deque(maxlen=1000),
            'l2': deque(maxlen=1000),
            'l3': deque(maxlen=1000)
        }
    
    def record_metric(self, metric: CacheMetrics) -> None:
        """Record a cache operation metric."""
        with self._lock:
            self._metrics_window.append(metric)
            self._counters['total_requests'] += 1
            
            if metric.hit:
                if metric.cache_tier == 'l1':
                    self._counters['l1_hits'] += 1
                    self._latency_buckets['l1'].append(metric.duration_ms)
                elif metric.cache_tier == 'l2':
                    self._counters['l2_hits'] += 1
                    self._latency_buckets['l2'].append(metric.duration_ms)
                elif metric.cache_tier == 'l3':
                    self._counters['l3_hits'] += 1
                    self._latency_buckets['l3'].append(metric.duration_ms)
            else:
                self._counters['cache_misses'] += 1
    
    def increment(self, counter: str, value: int = 1) -> None:
        """Increment a counter."""
        with self._lock:
            if counter in self._counters:
                self._counters[counter] += value
    
    def timer(self, operation: str) -> 'TimerContext':
        """Context manager for timing operations."""
        return TimerContext(self, operation)
    
    def get_hit_rates(self) -> Dict[str, float]:
        """Get cache hit rates by tier."""
        with self._lock:
            total = self._counters['total_requests']
            if total == 0:
                return {'l1': 0.0, 'l2': 0.0, 'l3': 0.0, 'overall': 0.0}
            
            l1_rate = self._counters['l1_hits'] / total
            l2_rate = self._counters['l2_hits'] / total
            l3_rate = self._counters['l3_hits'] / total
            overall_rate = (self._counters['l1_hits'] + self._counters['l2_hits'] + 
                          self._counters['l3_hits']) / total
            
            return {
                'l1': l1_rate,
                'l2': l2_rate,
                'l3': l3_rate,
                'overall': overall_rate
            }
    
    def get_latency_percentiles(self, percentiles: List[float] = [0.5, 0.9, 0.95, 0.99]) -> Dict[str, Dict[float, float]]:
        """Get latency percentiles by cache tier."""
        with self._lock:
            results = {}
            
            for tier, latencies in self._latency_buckets.items():
                if not latencies:
                    results[tier] = {p: 0.0 for p in percentiles}
                    continue
                
                sorted_latencies = sorted(latencies)
                tier_percentiles = {}
                
                for p in percentiles:
                    index = int(len(sorted_latencies) * p)
                    if index >= len(sorted_latencies):
                        index = len(sorted_latencies) - 1
                    tier_percentiles[p] = sorted_latencies[index]
                
                results[tier] = tier_percentiles
            
            return results
    
    def get_summary(self) -> Dict[str, any]:
        """Get comprehensive statistics summary."""
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            requests_per_second = self._counters['total_requests'] / uptime_seconds if uptime_seconds > 0 else 0
            
            hit_rates = self.get_hit_rates()
            latency_percentiles = self.get_latency_percentiles()
            
            # Calculate recent metrics from window
            recent_hits = sum(1 for m in self._metrics_window if m.hit)
            recent_hit_rate = recent_hits / len(self._metrics_window) if self._metrics_window else 0
            
            # Average latencies
            avg_latencies = {}
            for tier, latencies in self._latency_buckets.items():
                if latencies:
                    avg_latencies[tier] = sum(latencies) / len(latencies)
                else:
                    avg_latencies[tier] = 0.0
            
            return {
                'uptime_seconds': uptime_seconds,
                'total_requests': self._counters['total_requests'],
                'requests_per_second': requests_per_second,
                'hit_rates': hit_rates,
                'counters': dict(self._counters),
                'latency_percentiles': latency_percentiles,
                'average_latencies_ms': avg_latencies,
                'recent_hit_rate': recent_hit_rate,
                'eviction_rate': self._counters['evictions'] / self._counters['total_requests'] if self._counters['total_requests'] > 0 else 0
            }
    
    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._metrics_window.clear()
            for key in self._counters:
                self._counters[key] = 0
            for tier in self._latency_buckets:
                self._latency_buckets[tier].clear()
            self._start_time = time.time()


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, stats: CacheStatistics, operation: str):
        self.stats = stats
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        # Record metric - actual recording logic would depend on operation type
        # This is simplified for the example
        metric = CacheMetrics(
            operation=self.operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
            cache_tier='unknown',
            hit=False
        )
        self.stats.record_metric(metric)