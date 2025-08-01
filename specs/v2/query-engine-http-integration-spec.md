# Query Engine HTTP Integration Specification

## Overview

This specification defines how the Query Engine integrates with the existing FastAPI HTTP layer to provide RESTful endpoints for querying, searching, and exporting data from the Blackcore system.

## Goals

1. Expose query engine functionality through RESTful HTTP endpoints
2. Leverage existing authentication and authorization infrastructure
3. Provide async export capabilities for large datasets
4. Maintain performance with caching and streaming
5. Ensure security with rate limiting and query validation

## API Endpoints

### 1. Structured Query Endpoint

```http
POST /api/v1/query/structured
Authorization: Bearer {token}
Content-Type: application/json

{
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
  "includes": ["Organization", "Related Tasks"],
  "pagination": {
    "page": 1,
    "size": 50
  }
}

Response:
{
  "data": [...],
  "total_count": 150,
  "page": 1,
  "page_size": 50,
  "execution_time_ms": 23.5,
  "from_cache": false,
  "links": {
    "self": "/api/v1/query/structured?page=1",
    "next": "/api/v1/query/structured?page=2",
    "last": "/api/v1/query/structured?page=3"
  }
}
```

### 2. Text Search Endpoint

```http
POST /api/v1/query/search
Authorization: Bearer {token}
Content-Type: application/json

{
  "query_text": "beach huts council meeting",
  "databases": ["Intelligence & Transcripts", "Actionable Tasks"],
  "max_results": 100,
  "similarity_threshold": 0.7
}

Response:
{
  "matches": [
    {
      "entity_id": "abc123",
      "database": "Intelligence & Transcripts",
      "similarity_score": 0.92,
      "matched_content": "Discussion about beach huts in council meeting...",
      "entity_data": {...}
    }
  ],
  "query_text": "beach huts council meeting",
  "execution_time_ms": 156.3
}
```

### 3. Export Endpoints

#### Create Export Job
```http
POST /api/v1/query/export
Authorization: Bearer {token}
Content-Type: application/json

{
  "query": {
    "database": "Actionable Tasks",
    "filters": [
      {"field": "Status", "operator": "in", "value": ["Pending", "In Progress"]}
    ]
  },
  "format": "excel",
  "options": {
    "include_headers": true,
    "sheet_name": "Active Tasks"
  }
}

Response:
{
  "job_id": "exp_789xyz",
  "status": "pending",
  "created_at": "2024-01-15T10:00:00Z",
  "format": "excel",
  "links": {
    "status": "/api/v1/query/export/exp_789xyz",
    "download": "/api/v1/query/export/exp_789xyz/download"
  }
}
```

#### Check Export Status
```http
GET /api/v1/query/export/{job_id}
Authorization: Bearer {token}

Response:
{
  "job_id": "exp_789xyz",
  "status": "completed",
  "created_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:00:45Z",
  "format": "excel",
  "rows_exported": 1543,
  "file_size_bytes": 245632,
  "download_url": "/api/v1/query/export/exp_789xyz/download",
  "expires_at": "2024-01-16T10:00:45Z"
}
```

#### Download Export
```http
GET /api/v1/query/export/{job_id}/download
Authorization: Bearer {token}

Response:
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="active_tasks_20240115.xlsx"
[Binary file data]
```

### 4. Query Statistics Endpoint

```http
GET /api/v1/query/stats
Authorization: Bearer {token}

Response:
{
  "total_queries": 15234,
  "cache_hit_rate": 0.82,
  "average_execution_time_ms": 34.2,
  "popular_databases": {
    "People & Contacts": 4521,
    "Actionable Tasks": 3876,
    "Intelligence & Transcripts": 2934
  },
  "popular_filters": {
    "Status": 8234,
    "Organization": 5123,
    "Date Created": 3421
  },
  "cache_statistics": {
    "memory_hit_rate": 0.75,
    "redis_hit_rate": 0.15,
    "disk_hit_rate": 0.05
  }
}
```

### 5. Query Cost Estimation

```http
POST /api/v1/query/estimate
Authorization: Bearer {token}
Content-Type: application/json

{
  "database": "Intelligence & Transcripts",
  "filters": [...],
  "includes": [...]
}

Response:
{
  "estimated_rows": 5000,
  "estimated_cost": 2500.5,
  "estimated_time_ms": 450,
  "optimization_hints": [
    "Consider adding index on 'Date Created' field",
    "Large dataset - consider using pagination"
  ],
  "suggested_indexes": [
    "CREATE INDEX idx_intelligence_date ON intelligence_transcripts(date_created)"
  ]
}
```

## Request/Response Models

### Query Models

```python
class QueryRequest(BaseModel):
    """Structured query request."""
    database: str
    filters: List[QueryFilter] = []
    sort_fields: List[SortField] = []
    includes: List[str] = []
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    distinct: bool = False

class QueryFilter(BaseModel):
    """Filter specification."""
    field: str
    operator: QueryOperator
    value: Any
    case_sensitive: bool = True

class SortField(BaseModel):
    """Sort specification."""
    field: str
    order: Literal["asc", "desc"] = "asc"

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1)
    size: int = Field(100, ge=1, le=1000)
```

### Export Models

```python
class ExportRequest(BaseModel):
    """Export request specification."""
    query: QueryRequest
    format: ExportFormat
    options: Dict[str, Any] = {}
    template_name: Optional[str] = None

class ExportJob(BaseModel):
    """Export job information."""
    job_id: str
    status: ExportStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    format: ExportFormat
    rows_exported: Optional[int]
    file_size_bytes: Optional[int]
    error_message: Optional[str]
    download_url: Optional[str]
    expires_at: Optional[datetime]
```

## Integration Architecture

### 1. Query Service Layer

```python
class QueryService:
    """Bridge between HTTP endpoints and query engine."""
    
    def __init__(self, query_engine: QueryEngine, cache_manager: CacheManager):
        self.engine = query_engine
        self.cache = cache_manager
        self.stats_collector = StatisticsCollector()
    
    async def execute_query(
        self, 
        request: QueryRequest, 
        user: User
    ) -> QueryResult:
        # Validate query permissions
        self._validate_access(request.database, user)
        
        # Check query complexity
        if self._is_expensive_query(request):
            raise HTTPException(400, "Query too complex")
        
        # Convert to internal query format
        query = self._build_query(request)
        
        # Execute with caching
        result = await self.engine.execute_structured_query(query)
        
        # Track statistics
        self.stats_collector.record_query(request, result)
        
        return result
```

### 2. Export Service

```python
class ExportService:
    """Handle async export jobs."""
    
    def __init__(self, export_manager: ExportManager, job_queue: JobQueue):
        self.export_manager = export_manager
        self.job_queue = job_queue
    
    async def create_export(
        self, 
        request: ExportRequest, 
        user: User
    ) -> str:
        # Validate export size
        estimated_size = self._estimate_export_size(request)
        if estimated_size > user.export_quota:
            raise HTTPException(400, "Export exceeds quota")
        
        # Create async job
        job_id = await self.export_manager.create_export_job(
            data_iterator=self._create_iterator(request.query),
            format=request.format,
            **request.options
        )
        
        return job_id
```

## Security Considerations

### 1. Query Validation

- Maximum filter count: 20
- Maximum include depth: 3
- Maximum result size: 10,000 rows (without export)
- Query timeout: 30 seconds

### 2. Rate Limiting

```python
# Per-user rate limits
rate_limits = {
    "query": "100/minute",
    "search": "50/minute", 
    "export": "10/hour"
}
```

### 3. Access Control

- Users can only query databases they have access to
- Field-level permissions for sensitive data
- Export audit logging

### 4. Input Sanitization

- Validate all field names against schema
- Escape special characters in search queries
- Sanitize export filenames

## Performance Optimization

### 1. Query Optimization

- Automatic filter reordering
- Index usage hints
- Query plan caching

### 2. Result Streaming

```python
@app.get("/api/v1/query/stream")
async def stream_query_results(request: QueryRequest):
    async def generate():
        async for row in query_service.stream_results(request):
            yield json.dumps(row) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

### 3. Cache Strategy

- L1: In-memory cache for frequent queries (1-minute TTL)
- L2: Redis cache for recent queries (1-hour TTL) 
- L3: Disk cache for expensive queries (24-hour TTL)

## Monitoring & Metrics

### 1. Prometheus Metrics

```python
query_duration_histogram = Histogram(
    'query_duration_seconds',
    'Query execution duration',
    ['database', 'operation']
)

cache_hit_counter = Counter(
    'cache_hits_total',
    'Cache hit count',
    ['cache_tier']
)
```

### 2. Logging

```python
logger.info("Query executed", extra={
    "database": request.database,
    "filter_count": len(request.filters),
    "execution_time_ms": result.execution_time_ms,
    "cache_hit": result.from_cache,
    "user_id": user.id
})
```

## Error Handling

### Standard Error Responses

```json
{
  "error_code": "QUERY_TIMEOUT",
  "message": "Query execution exceeded 30 second timeout",
  "details": {
    "database": "Intelligence & Transcripts",
    "estimated_rows": 50000
  },
  "request_id": "req_abc123",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### Error Codes

- `QUERY_VALIDATION_ERROR`: Invalid query syntax
- `QUERY_TIMEOUT`: Query execution timeout
- `QUERY_TOO_COMPLEX`: Query complexity exceeds limits
- `DATABASE_NOT_FOUND`: Unknown database name
- `FIELD_NOT_FOUND`: Unknown field name
- `ACCESS_DENIED`: Insufficient permissions
- `EXPORT_QUOTA_EXCEEDED`: Export size exceeds user quota

## Testing Strategy

### 1. Unit Tests
- Query parsing and validation
- Filter operator implementations
- Export format handlers

### 2. Integration Tests
- End-to-end query execution
- Cache behavior verification
- Export job lifecycle

### 3. Performance Tests
- Query latency under load
- Concurrent query handling
- Large export streaming

### 4. Security Tests
- SQL injection attempts
- Query complexity attacks
- Rate limit enforcement

## Migration Plan

1. **Phase 1**: Deploy query endpoints (read-only)
2. **Phase 2**: Enable caching and optimization
3. **Phase 3**: Add export functionality
4. **Phase 4**: Implement streaming and advanced features

## Future Enhancements

1. **GraphQL Interface**: Alternative query language
2. **Saved Queries**: Store and share common queries
3. **Query Builder UI**: Visual query construction
4. **Aggregations**: SUM, COUNT, AVG operations
5. **Webhooks**: Subscribe to query results changes
6. **Query Scheduling**: Periodic query execution