"""Query API request and response models."""

from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from ..query_engine.models import QueryOperator, SortOrder, ExportFormat


class QueryFilter(BaseModel):
    """Filter specification for queries."""
    
    field: str = Field(..., description="Field to filter on")
    operator: QueryOperator = Field(..., description="Filter operator")
    value: Any = Field(..., description="Filter value")
    case_sensitive: bool = Field(True, description="Case sensitive comparison")
    
    model_config = ConfigDict(use_enum_values=True)


class SortField(BaseModel):
    """Sort specification for queries."""
    
    field: str = Field(..., description="Field to sort by")
    order: Literal["asc", "desc"] = Field("asc", description="Sort order")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(100, ge=1, le=1000, description="Items per page")


class QueryRequest(BaseModel):
    """Structured query request."""
    
    database: str = Field(..., description="Target database name")
    filters: List[QueryFilter] = Field(default_factory=list, description="Query filters")
    sort_fields: List[SortField] = Field(default_factory=list, description="Sort fields")
    includes: List[str] = Field(default_factory=list, description="Related entities to include")
    pagination: PaginationParams = Field(default_factory=PaginationParams, description="Pagination settings")
    distinct: bool = Field(False, description="Return only distinct results")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "database": "People & Contacts",
                "filters": [
                    {
                        "field": "Organization",
                        "operator": "contains",
                        "value": "Council"
                    }
                ],
                "sort_fields": [
                    {
                        "field": "Full Name",
                        "order": "asc"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "size": 50
                }
            }
        }
    )


class QueryResponse(BaseModel):
    """Query execution response."""
    
    data: List[Dict[str, Any]] = Field(..., description="Query results")
    total_count: int = Field(..., description="Total matching records")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    execution_time_ms: float = Field(..., description="Query execution time")
    from_cache: bool = Field(False, description="Whether result came from cache")
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS links")


class TextSearchRequest(BaseModel):
    """Text search request."""
    
    query_text: str = Field(..., description="Search query text")
    databases: Optional[List[str]] = Field(None, description="Databases to search")
    max_results: int = Field(100, ge=1, le=1000, description="Maximum results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_text": "beach huts council meeting",
                "databases": ["Intelligence & Transcripts", "Actionable Tasks"],
                "max_results": 100,
                "similarity_threshold": 0.7
            }
        }
    )


class TextSearchResponse(BaseModel):
    """Text search response."""
    
    matches: List[Dict[str, Any]] = Field(..., description="Search matches")
    query_text: str = Field(..., description="Original query text")
    execution_time_ms: float = Field(..., description="Search execution time")
    total_matches: int = Field(..., description="Total number of matches found")


class ExportRequest(BaseModel):
    """Export request specification."""
    
    query: QueryRequest = Field(..., description="Query to export")
    format: ExportFormat = Field(..., description="Export format")
    options: Dict[str, Any] = Field(default_factory=dict, description="Format-specific options")
    template_name: Optional[str] = Field(None, description="Export template to use")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": {
                    "database": "Actionable Tasks",
                    "filters": [
                        {
                            "field": "Status",
                            "operator": "in",
                            "value": ["Pending", "In Progress"]
                        }
                    ]
                },
                "format": "excel",
                "options": {
                    "include_headers": True,
                    "sheet_name": "Active Tasks"
                }
            }
        }
    )


class ExportJob(BaseModel):
    """Export job information."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    format: ExportFormat = Field(..., description="Export format")
    rows_exported: Optional[int] = Field(None, description="Number of rows exported")
    file_size_bytes: Optional[int] = Field(None, description="Export file size")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    download_url: Optional[str] = Field(None, description="Download URL when complete")
    expires_at: Optional[datetime] = Field(None, description="Download expiration time")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")


class QueryEstimateRequest(BaseModel):
    """Query cost estimation request."""
    
    database: str = Field(..., description="Target database")
    filters: List[QueryFilter] = Field(default_factory=list, description="Query filters")
    includes: List[str] = Field(default_factory=list, description="Related entities")


class QueryEstimateResponse(BaseModel):
    """Query cost estimation response."""
    
    estimated_rows: int = Field(..., description="Estimated result rows")
    estimated_cost: float = Field(..., description="Estimated query cost")
    estimated_time_ms: float = Field(..., description="Estimated execution time")
    optimization_hints: List[str] = Field(default_factory=list, description="Optimization suggestions")
    suggested_indexes: List[str] = Field(default_factory=list, description="Suggested database indexes")


class QueryStatsResponse(BaseModel):
    """Query statistics response."""
    
    total_queries: int = Field(..., description="Total queries executed")
    cache_hit_rate: float = Field(..., description="Overall cache hit rate")
    average_execution_time_ms: float = Field(..., description="Average query execution time")
    popular_databases: Dict[str, int] = Field(default_factory=dict, description="Most queried databases")
    popular_filters: Dict[str, int] = Field(default_factory=dict, description="Most used filter fields")
    cache_statistics: Dict[str, float] = Field(default_factory=dict, description="Cache tier statistics")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_queries": 15234,
                "cache_hit_rate": 0.82,
                "average_execution_time_ms": 34.2,
                "popular_databases": {
                    "People & Contacts": 4521,
                    "Actionable Tasks": 3876
                },
                "popular_filters": {
                    "Status": 8234,
                    "Organization": 5123
                },
                "cache_statistics": {
                    "memory_hit_rate": 0.75,
                    "redis_hit_rate": 0.15,
                    "disk_hit_rate": 0.05
                }
            }
        }
    )