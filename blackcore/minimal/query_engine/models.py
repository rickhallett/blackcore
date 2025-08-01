"""Core models for the query engine."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class QueryOperator(str, Enum):
    """Supported query operators."""
    
    EQUALS = "eq"
    NOT_EQUALS = "ne" 
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    REGEX = "regex"
    FUZZY = "fuzzy"


class SortOrder(str, Enum):
    """Sort order options."""
    
    ASC = "asc"
    DESC = "desc"


class ExportFormat(str, Enum):
    """Supported export formats."""
    
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    EXCEL = "excel"
    PARQUET = "parquet"
    TSV = "tsv"


class QueryFilter(BaseModel):
    """Represents a filter condition in a query."""
    
    field: str = Field(description="Field to filter on")
    operator: QueryOperator = Field(description="Filter operator")
    value: Any = Field(description="Filter value")
    case_sensitive: bool = Field(default=True, description="Case sensitive comparison")
    
    model_config = ConfigDict(use_enum_values=True)


class SortField(BaseModel):
    """Represents a field to sort by."""
    
    field: str = Field(description="Field to sort by")
    order: SortOrder = Field(default=SortOrder.ASC, description="Sort order")
    
    model_config = ConfigDict(use_enum_values=True)


class QueryPagination(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(ge=1, default=1, description="Page number (1-based)")
    size: int = Field(ge=1, le=1000, default=100, description="Items per page") 
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


class RelationshipInclude(BaseModel):
    """Specification for including related entities."""
    
    relation_field: str = Field(description="Field containing the relationship")
    target_database: Optional[str] = Field(default=None, description="Target database name")
    filters: List[QueryFilter] = Field(default_factory=list, description="Filters for related entities")
    max_depth: int = Field(ge=1, le=5, default=1, description="Maximum relationship depth")


class StructuredQuery(BaseModel):
    """Structured query representation."""
    
    database: str = Field(description="Target database name")
    filters: List[QueryFilter] = Field(default_factory=list, description="Query filters")
    sort_fields: List[SortField] = Field(default_factory=list, description="Sort fields")
    includes: List[RelationshipInclude] = Field(default_factory=list, description="Related entities to include")
    pagination: QueryPagination = Field(default_factory=QueryPagination, description="Pagination settings")
    distinct: bool = Field(default=False, description="Return only distinct results")
    
    model_config = ConfigDict(use_enum_values=True)


class GraphQuery(BaseModel):
    """Graph traversal query."""
    
    start_entities: List[str] = Field(description="Starting entity IDs")
    relationship_types: Optional[List[str]] = Field(default=None, description="Relationship types to follow")
    max_depth: int = Field(ge=1, le=10, default=3, description="Maximum traversal depth")
    node_filters: List[QueryFilter] = Field(default_factory=list, description="Node filters")
    edge_filters: List[QueryFilter] = Field(default_factory=list, description="Edge filters")
    return_paths: bool = Field(default=False, description="Return traversal paths")
    
    model_config = ConfigDict(use_enum_values=True)


class TemporalQuery(BaseModel):
    """Time-based query parameters."""
    
    start_date: Optional[datetime] = Field(default=None, description="Start date")
    end_date: Optional[datetime] = Field(default=None, description="End date")
    time_field: str = Field(default="date", description="Field to use for time filtering")
    group_by_period: Optional[str] = Field(default=None, description="Time period for grouping (day/week/month/year)")
    
    model_config = ConfigDict(use_enum_values=True)


class SemanticQuery(BaseModel):
    """Semantic search query."""
    
    query_text: str = Field(description="Natural language query")
    similarity_threshold: float = Field(ge=0.0, le=1.0, default=0.7, description="Minimum similarity score")
    max_results: int = Field(ge=1, le=1000, default=50, description="Maximum results to return")
    databases: Optional[List[str]] = Field(default=None, description="Databases to search")
    
    model_config = ConfigDict(use_enum_values=True)


class QueryResult(BaseModel):
    """Query execution result."""
    
    data: List[Dict[str, Any]] = Field(description="Result data")
    total_count: int = Field(description="Total number of matching items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    from_cache: bool = Field(default=False, description="Whether result came from cache")
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size
    
    @property
    def has_next_page(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.total_pages
    
    @property
    def has_previous_page(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1


class GraphResult(BaseModel):
    """Graph query result."""
    
    nodes: List[Dict[str, Any]] = Field(description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(description="Graph edges")
    paths: Optional[List[List[str]]] = Field(default=None, description="Traversal paths")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Graph metrics")
    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    
    @property
    def node_count(self) -> int:
        """Number of nodes in result."""
        return len(self.nodes)
    
    @property 
    def edge_count(self) -> int:
        """Number of edges in result."""
        return len(self.edges)


class SemanticMatch(BaseModel):
    """Semantic search match."""
    
    entity_id: str = Field(description="Matched entity ID")
    database: str = Field(description="Source database")
    similarity_score: float = Field(description="Similarity score")
    matched_content: str = Field(description="Content that matched")
    entity_data: Dict[str, Any] = Field(description="Full entity data")
    
    model_config = ConfigDict(use_enum_values=True)


class SemanticResult(BaseModel):
    """Semantic search result."""
    
    matches: List[SemanticMatch] = Field(description="Semantic matches")
    query_text: str = Field(description="Original query text")
    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    
    @property
    def match_count(self) -> int:
        """Number of matches."""
        return len(self.matches)


class QueryStatistics(BaseModel):
    """Query execution statistics."""
    
    total_queries: int = Field(description="Total queries executed")
    cache_hits: int = Field(description="Number of cache hits")
    cache_misses: int = Field(description="Number of cache misses")
    average_execution_time_ms: float = Field(description="Average execution time")
    popular_databases: Dict[str, int] = Field(description="Most queried databases")
    popular_filters: Dict[str, int] = Field(description="Most used filters")
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


class QueryError(Exception):
    """Base class for query engine errors."""
    
    def __init__(self, message: str, query: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.query = query


class QueryValidationError(QueryError):
    """Raised when query validation fails."""
    pass


class QueryExecutionError(QueryError):
    """Raised when query execution fails."""
    pass


class QuerySecurityError(QueryError):
    """Raised when query violates security policies."""
    pass


class OptimizedQuery(BaseModel):
    """Optimized query plan."""
    
    original_query: StructuredQuery = Field(description="Original query")
    optimized_filters: List[QueryFilter] = Field(default_factory=list, description="Optimized filters")
    suggested_indexes: List[str] = Field(default_factory=list, description="Suggested database indexes")
    estimated_cost: float = Field(description="Estimated query cost")
    optimization_notes: List[str] = Field(default_factory=list, description="Optimization explanations")
    
    model_config = ConfigDict(use_enum_values=True)