"""Shared models for query engine integration.

This module defines common data structures used across all agent modules
to ensure consistent communication and data flow.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..search.interfaces import SearchResult
from ..relationships.interfaces import RelationshipGraph
from ..nlp.interfaces import ParsedQuery


class QueryStatus(Enum):
    """Status of query execution."""
    PENDING = "pending"
    PARSING = "parsing"
    OPTIMIZING = "optimizing"
    LOADING = "loading"
    EXECUTING = "executing"
    CACHING = "caching"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StructuredQuery:
    """Unified query representation after parsing.
    
    This is the common format that all agents understand.
    """
    # Core query components
    intent: str  # search, aggregate, relate, etc.
    entities: List[str] = field(default_factory=list)
    filters: List['QueryFilter'] = field(default_factory=list)
    sort_criteria: List[tuple[str, str]] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None
    
    # Relationship specifications
    include_relationships: List[str] = field(default_factory=list)
    relationship_depth: int = 1
    
    # Aggregation specifications
    aggregations: List[Dict[str, Any]] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    
    # Metadata
    query_id: Optional[str] = None
    source_query: Optional[str] = None  # Original natural language query
    parsed_at: Optional[datetime] = None
    confidence: float = 1.0
    
    @classmethod
    def from_parsed_query(cls, parsed: ParsedQuery) -> 'StructuredQuery':
        """Create from NLP parsed query."""
        return cls(
            intent=parsed.intent.value,
            entities=[e.text for e in parsed.entities],
            filters=parsed.filters,  # Assuming compatible format
            sort_criteria=parsed.sort_criteria,
            limit=parsed.limit,
            include_relationships=parsed.relationships_to_include,
            aggregations=parsed.aggregations,
            source_query=parsed.original_text,
            confidence=parsed.confidence
        )


@dataclass
class QueryResult:
    """Unified result format with metadata."""
    # Core results
    data: List[Dict[str, Any]]
    total_count: int
    
    # Metadata
    query_id: Optional[str] = None
    execution_time_ms: float = 0.0
    cache_hit: bool = False
    
    # Search-specific results
    search_results: Optional[List[SearchResult]] = None
    
    # Relationship graph if requested
    relationship_graph: Optional[RelationshipGraph] = None
    
    # Aggregation results
    aggregations: Optional[Dict[str, Any]] = None
    
    # Export readiness
    export_ready: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "data": self.data,
            "total_count": self.total_count,
            "metadata": {
                "query_id": self.query_id,
                "execution_time_ms": self.execution_time_ms,
                "cache_hit": self.cache_hit
            },
            "aggregations": self.aggregations
        }


@dataclass
class QueryStatistics:
    """Performance and execution statistics."""
    # Timing breakdown
    parse_time_ms: float = 0.0
    optimize_time_ms: float = 0.0
    load_time_ms: float = 0.0
    filter_time_ms: float = 0.0
    search_time_ms: float = 0.0
    relationship_time_ms: float = 0.0
    sort_time_ms: float = 0.0
    export_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Resource usage
    memory_used_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Data metrics
    rows_scanned: int = 0
    rows_returned: int = 0
    relationships_resolved: int = 0
    
    # Optimization metrics
    filters_reordered: bool = False
    indexes_used: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    
    def bottleneck(self) -> str:
        """Identify the slowest component."""
        times = {
            'parse': self.parse_time_ms,
            'optimize': self.optimize_time_ms,
            'load': self.load_time_ms,
            'filter': self.filter_time_ms,
            'search': self.search_time_ms,
            'relationship': self.relationship_time_ms,
            'sort': self.sort_time_ms,
            'export': self.export_time_ms
        }
        return max(times.items(), key=lambda x: x[1])[0]


@dataclass
class ExecutionContext:
    """Shared context passed between agents during query execution."""
    # Query information
    query: StructuredQuery
    
    # User context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Performance settings
    timeout_ms: int = 30000  # 30 seconds default
    max_memory_mb: int = 1024
    enable_cache: bool = True
    cache_ttl: int = 3600
    
    # Feature flags
    enable_optimization: bool = True
    enable_profiling: bool = True
    enable_export: bool = True
    
    # Statistics collection
    statistics: QueryStatistics = field(default_factory=QueryStatistics)
    
    # Intermediate results (for passing between agents)
    raw_data: Optional[List[Dict[str, Any]]] = None
    filtered_data: Optional[List[Dict[str, Any]]] = None
    search_results: Optional[List[SearchResult]] = None
    
    def track_time(self, component: str, time_ms: float) -> None:
        """Track execution time for a component."""
        setattr(self.statistics, f"{component}_time_ms", time_ms)
        self.statistics.total_time_ms += time_ms


@dataclass
class OptimizedQuery:
    """Query after optimization by Agent C."""
    original_query: StructuredQuery
    
    # Optimized components
    reordered_filters: List['QueryFilter']
    execution_plan: Dict[str, Any]
    estimated_cost: float
    
    # Suggestions
    suggested_indexes: List[str] = field(default_factory=list)
    cache_keys: List[str] = field(default_factory=list)
    
    # Flags
    use_parallel_execution: bool = False
    use_streaming: bool = False


@dataclass
class CachedResult:
    """Cached query result with metadata."""
    result: QueryResult
    query_hash: str
    created_at: datetime
    ttl: int
    hit_count: int = 0
    tags: List[str] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl


@dataclass
class ExportRequest:
    """Request to export query results."""
    result: QueryResult
    format: str  # json, csv, excel, parquet
    options: Dict[str, Any] = field(default_factory=dict)
    
    # Output options
    output_path: Optional[str] = None
    stream: bool = False
    compress: bool = False
    
    # Format-specific options
    include_metadata: bool = True
    include_relationships: bool = False
    flatten_nested: bool = True


@dataclass
class EntityMetadata:
    """Metadata about entities in the system."""
    entity_type: str
    total_count: int
    field_names: List[str]
    field_types: Dict[str, str]
    indexes: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    
    # Statistics for optimization
    field_cardinality: Dict[str, int] = field(default_factory=dict)
    field_selectivity: Dict[str, float] = field(default_factory=dict)


# Re-export commonly used models from other modules
from ..models import QueryFilter, QueryOperator, SortOrder

__all__ = [
    # Enums
    "QueryStatus",
    "QueryOperator",
    "SortOrder",
    
    # Core models
    "StructuredQuery",
    "QueryResult",
    "QueryStatistics",
    "ExecutionContext",
    
    # Optimization models
    "OptimizedQuery",
    "CachedResult",
    
    # Export models
    "ExportRequest",
    
    # Metadata
    "EntityMetadata",
    
    # Re-exports
    "QueryFilter"
]