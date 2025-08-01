"""Query and table statistics for optimization."""

from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import math


@dataclass
class Histogram:
    """Histogram for column value distribution."""
    
    field: str
    buckets: List[Tuple[Any, Any, int]]  # (min, max, count) for each bucket
    total_count: int
    null_count: int = 0
    
    def estimate_frequency(self, value: Any) -> float:
        """Estimate frequency of a specific value."""
        if self.total_count == 0:
            return 0.0
        
        for min_val, max_val, count in self.buckets:
            if min_val <= value <= max_val:
                # Assume uniform distribution within bucket
                bucket_selectivity = count / self.total_count
                return bucket_selectivity / max(1, count)
        
        return 0.0
    
    def estimate_range_frequency(self, min_value: Optional[Any], max_value: Optional[Any]) -> float:
        """Estimate frequency of values in a range."""
        if self.total_count == 0:
            return 0.0
        
        matching_count = 0
        
        for bucket_min, bucket_max, count in self.buckets:
            # Check if bucket overlaps with range
            if min_value is None or bucket_max >= min_value:
                if max_value is None or bucket_min <= max_value:
                    # Bucket overlaps - estimate fraction
                    if min_value is None and max_value is None:
                        matching_count += count
                    elif min_value is None:
                        if bucket_max <= max_value:
                            matching_count += count
                        else:
                            # Partial overlap
                            overlap_fraction = 0.5  # Simplified
                            matching_count += count * overlap_fraction
                    elif max_value is None:
                        if bucket_min >= min_value:
                            matching_count += count
                        else:
                            # Partial overlap
                            overlap_fraction = 0.5  # Simplified
                            matching_count += count * overlap_fraction
                    else:
                        # Both bounds specified
                        if bucket_min >= min_value and bucket_max <= max_value:
                            matching_count += count
                        else:
                            # Partial overlap
                            overlap_fraction = 0.5  # Simplified
                            matching_count += count * overlap_fraction
        
        return matching_count / self.total_count


@dataclass
class TableStatistics:
    """Statistics for a database table."""
    
    database_name: str
    row_count: int
    distinct_values: Dict[str, int] = field(default_factory=dict)  # field -> distinct count
    indexed_fields: List[str] = field(default_factory=list)
    histograms: Dict[str, Histogram] = field(default_factory=dict)  # field -> histogram
    avg_row_size_bytes: int = 1000
    last_updated: Optional[float] = None
    
    def get_histogram(self, field: str) -> Optional[Histogram]:
        """Get histogram for a field."""
        return self.histograms.get(field)
    
    def estimate_table_size_mb(self) -> float:
        """Estimate table size in MB."""
        return (self.row_count * self.avg_row_size_bytes) / (1024 * 1024)


@dataclass
class QueryStatistics:
    """Statistics for query execution."""
    
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_execution_time_ms: float = 0.0
    query_patterns: Dict[str, int] = field(default_factory=dict)  # pattern -> count
    slow_queries: List[Dict[str, Any]] = field(default_factory=list)
    popular_databases: Dict[str, int] = field(default_factory=dict)
    popular_filters: Dict[str, int] = field(default_factory=dict)
    
    @property
    def average_execution_time_ms(self) -> float:
        """Calculate average execution time."""
        if self.total_queries == 0:
            return 0.0
        return self.total_execution_time_ms / self.total_queries
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    def record_query(self, database: str, filters: List[str], execution_time_ms: float, from_cache: bool):
        """Record a query execution."""
        self.total_queries += 1
        self.total_execution_time_ms += execution_time_ms
        
        if from_cache:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Track popular databases
        self.popular_databases[database] = self.popular_databases.get(database, 0) + 1
        
        # Track popular filters
        for filter_field in filters:
            self.popular_filters[filter_field] = self.popular_filters.get(filter_field, 0) + 1
        
        # Track slow queries
        if execution_time_ms > 1000:  # Queries slower than 1 second
            self.slow_queries.append({
                'database': database,
                'filters': filters,
                'execution_time_ms': execution_time_ms,
                'from_cache': from_cache
            })
            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]


class StatisticsCollector:
    """Collect and maintain query and table statistics."""
    
    def __init__(self):
        """Initialize statistics collector."""
        self._table_stats: Dict[str, TableStatistics] = {}
        self._query_stats = QueryStatistics()
    
    def update_table_statistics(self, database: str, stats: TableStatistics):
        """Update statistics for a table."""
        self._table_stats[database] = stats
    
    def get_table_statistics(self, database: str) -> Optional[TableStatistics]:
        """Get statistics for a table."""
        return self._table_stats.get(database)
    
    def record_query_execution(self, database: str, filters: List[str], 
                             execution_time_ms: float, from_cache: bool):
        """Record a query execution."""
        self._query_stats.record_query(database, filters, execution_time_ms, from_cache)
    
    def get_query_statistics(self) -> QueryStatistics:
        """Get query execution statistics."""
        return self._query_stats
    
    def compute_table_statistics(self, database: str, data: List[Dict[str, Any]]) -> TableStatistics:
        """Compute statistics from actual data."""
        stats = TableStatistics(
            database_name=database,
            row_count=len(data)
        )
        
        if not data:
            return stats
        
        # Compute distinct values for each field
        field_values = {}
        for row in data:
            for field, value in row.items():
                if field not in field_values:
                    field_values[field] = set()
                if value is not None:
                    field_values[field].add(value)
        
        for field, values in field_values.items():
            stats.distinct_values[field] = len(values)
        
        # Estimate average row size
        sample_size = min(100, len(data))
        total_size = sum(len(str(data[i])) for i in range(sample_size))
        stats.avg_row_size_bytes = total_size // sample_size if sample_size > 0 else 1000
        
        # Create simple histograms for numeric fields
        for field in field_values:
            values = [row.get(field) for row in data if row.get(field) is not None]
            if values and all(isinstance(v, (int, float)) for v in values):
                stats.histograms[field] = self._create_histogram(field, values)
        
        self._table_stats[database] = stats
        return stats
    
    def _create_histogram(self, field: str, values: List[Union[int, float]], num_buckets: int = 10) -> Histogram:
        """Create a histogram from numeric values."""
        if not values:
            return Histogram(field=field, buckets=[], total_count=0)
        
        sorted_values = sorted(values)
        total_count = len(values)
        bucket_size = max(1, total_count // num_buckets)
        
        buckets = []
        for i in range(0, total_count, bucket_size):
            bucket_values = sorted_values[i:i + bucket_size]
            if bucket_values:
                min_val = bucket_values[0]
                max_val = bucket_values[-1]
                count = len(bucket_values)
                buckets.append((min_val, max_val, count))
        
        return Histogram(
            field=field,
            buckets=buckets,
            total_count=total_count,
            null_count=0
        )