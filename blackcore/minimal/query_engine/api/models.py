"""API models for the Query Engine HTTP interface."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models import QueryOperator, SortOrder


class FilterRequest(BaseModel):
    """API model for filter conditions."""
    
    field: str = Field(
        ..., 
        description="Field to filter on (supports dot notation for nested fields)",
        example="metadata.priority"
    )
    operator: QueryOperator = Field(
        ...,
        description="Filter operator to apply",
        example="gt"
    )
    value: Any = Field(
        ...,
        description="Value to compare against",
        example=5
    )
    case_sensitive: bool = Field(
        default=True,
        description="Whether string comparisons are case-sensitive"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "field": "age",
                "operator": "gte",
                "value": 30,
                "case_sensitive": True
            }
        }


class SortRequest(BaseModel):
    """API model for sort configuration."""
    
    field: str = Field(
        ...,
        description="Field to sort by",
        example="created_at"
    )
    order: SortOrder = Field(
        default=SortOrder.ASC,
        description="Sort order (asc or desc)",
        example="desc"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "field": "score",
                "order": "desc"
            }
        }


class PaginationRequest(BaseModel):
    """API model for pagination parameters."""
    
    page: int = Field(
        ge=1,
        default=1,
        description="Page number (1-based)",
        example=1
    )
    size: int = Field(
        ge=1,
        le=1000,
        default=100,
        description="Items per page (max 1000)",
        example=50
    )
    
    class Config:
        schema_extra = {
            "example": {
                "page": 1,
                "size": 100
            }
        }


class IncludeRequest(BaseModel):
    """API model for relationship includes."""
    
    relation_field: str = Field(
        ...,
        description="Field containing the relationship",
        example="assignee"
    )
    target_database: Optional[str] = Field(
        default=None,
        description="Target database name (if different from default)",
        example="People & Contacts"
    )
    filters: List[FilterRequest] = Field(
        default_factory=list,
        description="Filters to apply on related entities"
    )
    max_depth: int = Field(
        ge=1,
        le=5,
        default=1,
        description="Maximum relationship traversal depth"
    )


class QueryRequest(BaseModel):
    """Main query request model for structured queries."""
    
    database: str = Field(
        ...,
        description="Target database name",
        example="Intelligence & Transcripts"
    )
    filters: List[FilterRequest] = Field(
        default_factory=list,
        description="Filter conditions to apply"
    )
    sort: List[SortRequest] = Field(
        default_factory=list,
        description="Sort configuration"
    )
    includes: List[IncludeRequest] = Field(
        default_factory=list,
        description="Related entities to include"
    )
    pagination: PaginationRequest = Field(
        default_factory=PaginationRequest,
        description="Pagination settings"
    )
    distinct: bool = Field(
        default=False,
        description="Return only distinct results"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "database": "People & Contacts",
                "filters": [
                    {
                        "field": "properties.Department",
                        "operator": "eq",
                        "value": "Engineering"
                    },
                    {
                        "field": "created_time",
                        "operator": "gte",
                        "value": "2024-01-01T00:00:00Z"
                    }
                ],
                "sort": [
                    {
                        "field": "properties.Name",
                        "order": "asc"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "size": 50
                }
            }
        }


class GraphQueryRequest(BaseModel):
    """API model for graph traversal queries."""
    
    start_entities: List[str] = Field(
        ...,
        description="Starting entity IDs for traversal",
        example=["entity-123", "entity-456"]
    )
    relationship_types: Optional[List[str]] = Field(
        default=None,
        description="Relationship types to follow (null for all)",
        example=["manages", "works_with"]
    )
    max_depth: int = Field(
        ge=1,
        le=10,
        default=3,
        description="Maximum traversal depth"
    )
    node_filters: List[FilterRequest] = Field(
        default_factory=list,
        description="Filters to apply on nodes"
    )
    return_paths: bool = Field(
        default=False,
        description="Include traversal paths in response"
    )


class SemanticQueryRequest(BaseModel):
    """API model for semantic/natural language queries."""
    
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language query",
        example="Find all people who work on AI projects"
    )
    databases: Optional[List[str]] = Field(
        default=None,
        description="Databases to search (null for all)",
        example=["People & Contacts", "Projects"]
    )
    similarity_threshold: float = Field(
        ge=0.0,
        le=1.0,
        default=0.7,
        description="Minimum similarity score"
    )
    max_results: int = Field(
        ge=1,
        le=1000,
        default=50,
        description="Maximum results to return"
    )


class TextSearchRequest(BaseModel):
    """API model for text search across databases."""
    
    query: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Search query text",
        example="quarterly planning"
    )
    databases: Optional[List[str]] = Field(
        default=None,
        description="Databases to search (null for all)"
    )
    fields: Optional[List[str]] = Field(
        default=None,
        description="Fields to search in (null for all text fields)",
        example=["properties.Name", "properties.Description"]
    )
    fuzzy: bool = Field(
        default=False,
        description="Enable fuzzy matching"
    )
    max_results: int = Field(
        ge=1,
        le=500,
        default=100,
        description="Maximum results to return"
    )


class QueryStatisticsRequest(BaseModel):
    """API model for query statistics request."""
    
    database: Optional[str] = Field(
        default=None,
        description="Database to get statistics for (null for all)"
    )
    entity_type: Optional[str] = Field(
        default=None,
        description="Entity type to filter by"
    )
    date_range: Optional[Dict[str, datetime]] = Field(
        default=None,
        description="Date range for statistics",
        example={"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}
    )


# Response Models

class EntityResponse(BaseModel):
    """Response model for a single entity."""
    
    id: str
    database: str
    properties: Dict[str, Any]
    created_time: datetime
    last_edited_time: datetime
    url: Optional[str] = None
    _score: Optional[float] = Field(
        default=None,
        description="Relevance score for search results"
    )


class QueryResponse(BaseModel):
    """Response model for structured query results."""
    
    data: List[EntityResponse] = Field(
        description="Query results"
    )
    total_count: int = Field(
        description="Total number of matching items"
    )
    page: int = Field(
        description="Current page number"
    )
    page_size: int = Field(
        description="Items per page"
    )
    total_pages: int = Field(
        description="Total number of pages"
    )
    execution_time_ms: float = Field(
        description="Query execution time in milliseconds"
    )
    from_cache: bool = Field(
        default=False,
        description="Whether result came from cache"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "data": [
                    {
                        "id": "abc123",
                        "database": "People & Contacts",
                        "properties": {
                            "Name": "John Doe",
                            "Department": "Engineering"
                        },
                        "created_time": "2024-01-15T10:00:00Z",
                        "last_edited_time": "2024-01-20T15:30:00Z"
                    }
                ],
                "total_count": 150,
                "page": 1,
                "page_size": 50,
                "total_pages": 3,
                "execution_time_ms": 45.2,
                "from_cache": False
            }
        }


class GraphNode(BaseModel):
    """Response model for a graph node."""
    
    id: str
    type: str
    properties: Dict[str, Any]
    database: str


class GraphEdge(BaseModel):
    """Response model for a graph edge."""
    
    source: str
    target: str
    relationship_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    """Response model for graph query results."""
    
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    paths: Optional[List[List[str]]] = None
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph metrics (node count, edge count, etc.)"
    )
    execution_time_ms: float


class TextSearchResult(BaseModel):
    """Response model for text search result."""
    
    entity: EntityResponse
    matched_fields: List[str] = Field(
        description="Fields that matched the query"
    )
    highlight: Optional[Dict[str, str]] = Field(
        default=None,
        description="Highlighted snippets from matched fields"
    )
    score: float = Field(
        description="Relevance score"
    )


class TextSearchResponse(BaseModel):
    """Response model for text search results."""
    
    results: List[TextSearchResult]
    total_count: int
    query: str
    execution_time_ms: float
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "entity": {
                            "id": "xyz789",
                            "database": "Intelligence & Transcripts",
                            "properties": {
                                "Title": "Q4 Planning Meeting"
                            },
                            "created_time": "2024-01-10T09:00:00Z",
                            "last_edited_time": "2024-01-10T10:30:00Z"
                        },
                        "matched_fields": ["properties.Title", "properties.Content"],
                        "highlight": {
                            "properties.Title": "Q4 <em>Planning</em> Meeting"
                        },
                        "score": 0.95
                    }
                ],
                "total_count": 5,
                "query": "planning",
                "execution_time_ms": 23.5
            }
        }


class DatabaseInfo(BaseModel):
    """Information about a queryable database."""
    
    name: str
    record_count: int
    last_updated: Optional[datetime]
    available_fields: List[str]
    indexed_fields: List[str]


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    
    status: str = Field(description="System status (healthy/degraded/unhealthy)")
    version: str
    databases: List[DatabaseInfo]
    cache_status: Dict[str, Any]
    performance_metrics: Dict[str, float]


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Invalid filter operator 'foo' for field 'age'",
                "details": {
                    "field": "filters[0].operator",
                    "allowed_values": ["eq", "ne", "gt", "gte", "lt", "lte"]
                },
                "request_id": "req_123abc"
            }
        }