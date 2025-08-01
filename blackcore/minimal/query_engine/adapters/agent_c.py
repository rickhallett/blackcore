"""Protocol adapters for Agent C (Performance & Export) integration.

This module provides adapters that implement caching, optimization, and export
functionality as required by the orchestrator interfaces.
"""

import json
import csv
import hashlib
import time
import io
import sqlite3
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging
import asyncio

from ..core.orchestrator import CacheManager, QueryOptimizer, ExportEngine
from ..models.shared import (
    StructuredQuery,
    QueryResult,
    QueryStatistics,
    OptimizedQuery,
    CachedResult,
    ExportRequest
)
from ..models import QueryFilter, QueryOperator

logger = logging.getLogger(__name__)


class SimpleCacheManager:
    """Simple in-memory cache manager with optional SQLite persistence."""
    
    def __init__(self, 
                 max_memory_items: int = 1000,
                 default_ttl: int = 3600,
                 persist_to_disk: bool = False,
                 cache_file: Optional[str] = None):
        """Initialize cache manager."""
        self.max_memory_items = max_memory_items
        self.default_ttl = default_ttl
        self.persist_to_disk = persist_to_disk
        
        # In-memory cache
        self._cache: Dict[str, CachedResult] = {}
        self._access_times: Dict[str, float] = {}
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Disk persistence
        if persist_to_disk:
            self.cache_file = cache_file or "query_cache.db"
            self._init_disk_cache()
    
    def _init_disk_cache(self):
        """Initialize SQLite cache database."""
        try:
            self._conn = sqlite3.connect(self.cache_file)
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    query_hash TEXT PRIMARY KEY,
                    result_data TEXT,
                    created_at TEXT,
                    ttl INTEGER,
                    hit_count INTEGER,
                    tags TEXT
                )
            ''')
            self._conn.commit()
            logger.info(f"Initialized disk cache: {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to initialize disk cache: {e}")
            self.persist_to_disk = False
    
    def get_cached_result(self, query_hash: str, max_age: Optional[int] = None) -> Optional[CachedResult]:
        """Get cached result if available and not expired."""
        # Check memory cache first
        if query_hash in self._cache:
            cached = self._cache[query_hash]
            
            # Check expiration
            age_limit = max_age or cached.ttl
            if not cached.is_expired() and age_limit:
                # Update access time and hit count
                self._access_times[query_hash] = time.time()
                cached.hit_count += 1
                self._hits += 1
                
                logger.debug(f"Cache HIT for {query_hash[:8]}... (age: {(datetime.now() - cached.created_at).total_seconds():.1f}s)")
                return cached
            else:
                # Expired - remove from cache
                del self._cache[query_hash]
                del self._access_times[query_hash]
        
        # Check disk cache if enabled
        if self.persist_to_disk:
            cached = self._load_from_disk(query_hash, max_age)
            if cached:
                # Load back into memory cache
                self._cache[query_hash] = cached
                self._access_times[query_hash] = time.time()
                self._hits += 1
                return cached
        
        self._misses += 1
        logger.debug(f"Cache MISS for {query_hash[:8]}...")
        return None
    
    def cache_result(self, query_hash: str, result: Any, ttl: int = None, tags: List[str] = None) -> None:
        """Cache a query result."""
        ttl = ttl or self.default_ttl
        tags = tags or []
        
        # Create cached result
        cached = CachedResult(
            result=result,
            query_hash=query_hash,
            created_at=datetime.now(),
            ttl=ttl,
            hit_count=0,
            tags=tags
        )
        
        # Add to memory cache
        self._cache[query_hash] = cached
        self._access_times[query_hash] = time.time()
        
        # LRU eviction if over limit
        if len(self._cache) > self.max_memory_items:
            self._evict_lru()
        
        # Persist to disk if enabled
        if self.persist_to_disk:
            self._save_to_disk(cached)
        
        logger.debug(f"Cached result for {query_hash[:8]}... (TTL: {ttl}s)")
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        # Find least recently used
        lru_hash = min(self._access_times.items(), key=lambda x: x[1])[0]
        
        # Remove from cache
        del self._cache[lru_hash]
        del self._access_times[lru_hash]
        self._evictions += 1
        
        logger.debug(f"Evicted LRU item: {lru_hash[:8]}...")
    
    def _load_from_disk(self, query_hash: str, max_age: Optional[int] = None) -> Optional[CachedResult]:
        """Load cached result from disk."""
        if not self.persist_to_disk:
            return None
        
        try:
            cursor = self._conn.execute('''
                SELECT result_data, created_at, ttl, hit_count, tags 
                FROM cache_entries 
                WHERE query_hash = ?
            ''', (query_hash,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            result_json, created_at_str, ttl, hit_count, tags_str = row
            
            # Parse data
            result_data = json.loads(result_json)
            created_at = datetime.fromisoformat(created_at_str)
            tags = json.loads(tags_str) if tags_str else []
            
            # Check expiration
            cached = CachedResult(
                result=result_data,
                query_hash=query_hash,
                created_at=created_at,
                ttl=ttl,
                hit_count=hit_count,
                tags=tags
            )
            
            if cached.is_expired():
                # Remove expired entry
                self._conn.execute('DELETE FROM cache_entries WHERE query_hash = ?', (query_hash,))
                self._conn.commit()
                return None
            
            return cached
            
        except Exception as e:
            logger.error(f"Error loading from disk cache: {e}")
            return None
    
    def _save_to_disk(self, cached: CachedResult):
        """Save cached result to disk."""
        if not self.persist_to_disk:
            return
        
        try:
            # Convert result to JSON
            if hasattr(cached.result, 'to_dict'):
                result_json = json.dumps(cached.result.to_dict())
            else:
                result_json = json.dumps(cached.result, default=str)
            
            # Insert or replace
            self._conn.execute('''
                INSERT OR REPLACE INTO cache_entries 
                (query_hash, result_data, created_at, ttl, hit_count, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                cached.query_hash,
                result_json,
                cached.created_at.isoformat(),
                cached.ttl,
                cached.hit_count,
                json.dumps(cached.tags)
            ))
            self._conn.commit()
            
        except Exception as e:
            logger.error(f"Error saving to disk cache: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'evictions': self._evictions,
            'memory_items': len(self._cache),
            'max_memory_items': self.max_memory_items
        }
    
    def clear_cache(self, tags: Optional[List[str]] = None):
        """Clear cache entries, optionally filtered by tags."""
        if tags:
            # Clear specific tags
            to_remove = []
            for query_hash, cached in self._cache.items():
                if any(tag in cached.tags for tag in tags):
                    to_remove.append(query_hash)
            
            for query_hash in to_remove:
                del self._cache[query_hash]
                if query_hash in self._access_times:
                    del self._access_times[query_hash]
            
            if self.persist_to_disk:
                tags_condition = ' OR '.join(['tags LIKE ?' for _ in tags])
                tag_patterns = [f'%"{tag}"%' for tag in tags]
                self._conn.execute(f'DELETE FROM cache_entries WHERE {tags_condition}', tag_patterns)
                self._conn.commit()
        else:
            # Clear all
            self._cache.clear()
            self._access_times.clear()
            
            if self.persist_to_disk:
                self._conn.execute('DELETE FROM cache_entries')
                self._conn.commit()


class SimpleQueryOptimizer:
    """Simple query optimizer with basic filter reordering."""
    
    def __init__(self):
        """Initialize optimizer."""
        # Operator selectivity estimates (lower = more selective)
        self._operator_selectivity = {
            QueryOperator.EQUALS: 0.1,
            QueryOperator.IN: 0.2,
            QueryOperator.BETWEEN: 0.3,
            QueryOperator.GT: 0.4,
            QueryOperator.LT: 0.4,  
            QueryOperator.GTE: 0.5,
            QueryOperator.LTE: 0.5,
            QueryOperator.CONTAINS: 0.6,
            QueryOperator.STARTS_WITH: 0.7,
            QueryOperator.ENDS_WITH: 0.7,
            QueryOperator.NOT_EQUALS: 0.9,
            QueryOperator.NOT_CONTAINS: 0.9,
            QueryOperator.NOT_IN: 0.9,
            QueryOperator.IS_NULL: 0.3,
            QueryOperator.IS_NOT_NULL: 0.8
        }
        
        # Field cost estimates (lower = cheaper to evaluate)
        self._field_costs = {
            'id': 1,
            'name': 2,
            'title': 2,
            'type': 2,
            'status': 2,
            'description': 5,
            'content': 10,
            'notes': 10
        }
    
    def optimize_query(self, query: StructuredQuery, statistics: QueryStatistics) -> OptimizedQuery:
        """Optimize query for better performance."""
        # Reorder filters by selectivity and cost
        reordered_filters = self._optimize_filter_order(query.filters)
        
        # Generate execution plan
        execution_plan = self.generate_execution_plan(query)
        
        # Estimate cost
        estimated_cost = self._estimate_query_cost(query, reordered_filters)
        
        # Generate optimization suggestions
        suggested_indexes = self._suggest_indexes(query)
        cache_keys = self._generate_cache_keys(query)
        
        return OptimizedQuery(
            original_query=query,
            reordered_filters=reordered_filters,
            execution_plan=execution_plan,
            estimated_cost=estimated_cost,
            suggested_indexes=suggested_indexes,
            cache_keys=cache_keys,
            use_parallel_execution=len(query.filters) > 5,
            use_streaming=query.limit and query.limit > 10000
        )
    
    def generate_execution_plan(self, query: StructuredQuery) -> Dict[str, Any]:
        """Generate query execution plan."""
        plan = {
            'steps': [],
            'estimated_rows': 1000,  # Default estimate
            'strategy': 'sequential'
        }
        
        # Data loading step
        plan['steps'].append({
            'step': 'load_data',
            'operation': 'scan',
            'entities': query.entities,
            'estimated_cost': len(query.entities) * 100
        })
        
        # Filter steps
        for i, filter_obj in enumerate(query.filters):
            selectivity = self._operator_selectivity.get(filter_obj.operator, 0.5)
            plan['steps'].append({
                'step': f'filter_{i}',
                'operation': 'filter',
                'field': filter_obj.field,
                'operator': filter_obj.operator.value,
                'selectivity': selectivity,
                'estimated_cost': self._field_costs.get(filter_obj.field, 5)
            })
            plan['estimated_rows'] *= selectivity
        
        # Search step
        if query.source_query:
            plan['steps'].append({
                'step': 'text_search',
                'operation': 'search',
                'query': query.source_query,
                'estimated_cost': plan['estimated_rows'] * 2
            })
        
        # Relationship resolution
        if query.include_relationships:
            plan['steps'].append({
                'step': 'resolve_relationships',
                'operation': 'graph_traversal',
                'relationships': query.include_relationships,
                'depth': query.relationship_depth,
                'estimated_cost': plan['estimated_rows'] * query.relationship_depth * 10
            })
        
        # Sorting
        if query.sort_criteria:
            plan['steps'].append({
                'step': 'sort',
                'operation': 'sort',
                'fields': [field for field, _ in query.sort_criteria],
                'estimated_cost': plan['estimated_rows'] * 10
            })
        
        return plan
    
    def _optimize_filter_order(self, filters: List[QueryFilter]) -> List[QueryFilter]:
        """Reorder filters for optimal performance."""
        if not filters:
            return filters
        
        # Calculate priority for each filter (lower = execute first)
        filter_priorities = []
        
        for filter_obj in filters:
            selectivity = self._operator_selectivity.get(filter_obj.operator, 0.5)
            cost = self._field_costs.get(filter_obj.field, 5)
            
            # Priority = selectivity * cost (prefer selective, cheap filters first)
            priority = selectivity * cost
            filter_priorities.append((priority, filter_obj))
        
        # Sort by priority and return filters
        filter_priorities.sort(key=lambda x: x[0])
        return [f for _, f in filter_priorities]
    
    def _estimate_query_cost(self, query: StructuredQuery, filters: List[QueryFilter]) -> float:
        """Estimate total query execution cost."""
        cost = 0.0
        
        # Base data loading cost
        cost += len(query.entities) * 100
        
        # Filter costs
        estimated_rows = 10000  # Starting estimate
        for filter_obj in filters:
            selectivity = self._operator_selectivity.get(filter_obj.operator, 0.5)
            field_cost = self._field_costs.get(filter_obj.field, 5)
            
            cost += estimated_rows * field_cost * 0.001
            estimated_rows *= selectivity
        
        # Search cost
        if query.source_query:
            cost += estimated_rows * 2
        
        # Relationship cost
        if query.include_relationships:
            cost += estimated_rows * query.relationship_depth * 10
        
        # Sort cost
        if query.sort_criteria:
            cost += estimated_rows * len(query.sort_criteria) * 0.1
        
        return cost
    
    def _suggest_indexes(self, query: StructuredQuery) -> List[str]:
        """Suggest indexes that could improve performance."""
        indexes = []
        
        # Index on frequently filtered fields
        for filter_obj in query.filters:
            if filter_obj.operator in [QueryOperator.EQUALS, QueryOperator.IN]:
                indexes.append(f"idx_{filter_obj.field}")
        
        # Composite index for sort + filter
        if query.sort_criteria and query.filters:
            sort_fields = [field for field, _ in query.sort_criteria]
            filter_fields = [f.field for f in query.filters[:2]]  # Top 2 filters
            combined_fields = filter_fields + sort_fields
            indexes.append(f"idx_composite_{'_'.join(combined_fields)}")
        
        return indexes
    
    def _generate_cache_keys(self, query: StructuredQuery) -> List[str]:
        """Generate cache keys for partial results."""
        keys = []
        
        # Cache key for data loading
        if query.entities:
            entity_key = hashlib.md5('_'.join(sorted(query.entities)).encode()).hexdigest()[:8]
            keys.append(f"data_{entity_key}")
        
        # Cache key for search results
        if query.source_query:
            search_key = hashlib.md5(query.source_query.encode()).hexdigest()[:8]
            keys.append(f"search_{search_key}")
        
        return keys


class SimpleExportEngine:
    """Simple export engine supporting multiple formats."""
    
    def __init__(self):
        """Initialize export engine."""
        self._formatters = {
            'json': self._export_json,
            'csv': self._export_csv,
            'txt': self._export_txt,
            'tsv': self._export_tsv
        }
    
    def export(self, result: QueryResult, format: str, options: Dict[str, Any] = None) -> Union[bytes, str]:
        """Export query result in specified format."""
        options = options or {}
        
        if format not in self._formatters:
            raise ValueError(f"Unsupported export format: {format}. Supported: {list(self._formatters.keys())}")
        
        formatter = self._formatters[format]
        return formatter(result, options)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return list(self._formatters.keys())
    
    def _export_json(self, result: QueryResult, options: Dict[str, Any]) -> str:
        """Export as JSON."""
        include_metadata = options.get('include_metadata', True)
        pretty = options.get('pretty', False)
        
        export_data = {
            'data': result.data
        }
        
        if include_metadata:
            export_data.update({
                'metadata': {
                    'total_count': result.total_count,
                    'query_id': result.query_id,
                    'execution_time_ms': result.execution_time_ms,
                    'cache_hit': result.cache_hit,
                    'exported_at': datetime.now().isoformat()
                }
            })
        
        if result.aggregations:
            export_data['aggregations'] = result.aggregations
        
        indent = 2 if pretty else None
        return json.dumps(export_data, indent=indent, default=str)
    
    def _export_csv(self, result: QueryResult, options: Dict[str, Any]) -> str:
        """Export as CSV."""
        if not result.data:
            return ""
        
        delimiter = options.get('delimiter', ',')
        include_headers = options.get('include_headers', True)
        flatten_nested = options.get('flatten_nested', True)
        
        # Flatten nested objects if requested
        if flatten_nested:
            flattened_data = []
            for row in result.data:
                flattened_row = self._flatten_dict(row)
                flattened_data.append(flattened_row)
            data = flattened_data
        else:
            data = result.data
        
        # Get all field names
        all_fields = set()
        for row in data:
            all_fields.update(row.keys())
        
        fieldnames = sorted(all_fields)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        
        if include_headers:
            writer.writeheader()
        
        for row in data:
            # Ensure all fields are present
            complete_row = {field: row.get(field, '') for field in fieldnames}
            writer.writerow(complete_row)
        
        return output.getvalue()
    
    def _export_txt(self, result: QueryResult, options: Dict[str, Any]) -> str:
        """Export as plain text."""
        lines = []
        
        # Add header
        lines.append(f"Query Results ({result.total_count} records)")
        lines.append("=" * 50)
        lines.append("")
        
        # Add records
        for i, record in enumerate(result.data):
            lines.append(f"Record {i + 1}:")
            for key, value in record.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        # Add metadata
        if result.query_id:
            lines.append(f"Query ID: {result.query_id}")
        lines.append(f"Execution Time: {result.execution_time_ms:.2f} ms")
        lines.append(f"Cache Hit: {result.cache_hit}")
        
        return "\n".join(lines)
    
    def _export_tsv(self, result: QueryResult, options: Dict[str, Any]) -> str:
        """Export as TSV (Tab-Separated Values)."""
        options = dict(options)  # Copy to avoid modifying original
        options['delimiter'] = '\t'
        return self._export_csv(result, options)
    
    def _flatten_dict(self, obj: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep).items())
            elif isinstance(value, list):
                # Convert list to string representation
                items.append((new_key, str(value)))
            else:
                items.append((new_key, value))
        
        return dict(items)


# Factory functions for easy instantiation
def create_simple_cache_manager(
    max_memory_items: int = 1000,
    default_ttl: int = 3600,
    persist_to_disk: bool = False,
    cache_file: Optional[str] = None
) -> SimpleCacheManager:
    """Create a simple cache manager."""
    return SimpleCacheManager(max_memory_items, default_ttl, persist_to_disk, cache_file)


def create_simple_query_optimizer() -> SimpleQueryOptimizer:
    """Create a simple query optimizer."""
    return SimpleQueryOptimizer()


def create_simple_export_engine() -> SimpleExportEngine:
    """Create a simple export engine."""
    return SimpleExportEngine()


# Integration helper
def integrate_agent_c(
    enable_disk_cache: bool = False,
    cache_file: Optional[str] = None,
    max_cache_items: int = 1000,
    default_ttl: int = 3600
) -> Dict[str, Any]:
    """Create all Agent C components for integration."""
    return {
        'cache_manager': create_simple_cache_manager(
            max_memory_items=max_cache_items,
            default_ttl=default_ttl,
            persist_to_disk=enable_disk_cache,
            cache_file=cache_file
        ),
        'query_optimizer': create_simple_query_optimizer(),
        'export_engine': create_simple_export_engine()
    }