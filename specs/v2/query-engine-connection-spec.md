# Query Engine HTTP Connection Technical Specification

## Overview

This specification details the connection between the HTTP API layer and the core query engine for Blackcore's intelligence processing system. The implementation bridges REST endpoints with the existing query engine to provide real-time data access.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HTTP Client   │───▶│   FastAPI Layer  │───▶│  Query Engine   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Query Service   │───▶│  JSON Cache     │
                       └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Export Manager  │
                       └──────────────────┘
```

## Component Specifications

### 1. Model Conversion Layer

**Purpose**: Convert between HTTP API models and internal query engine models.

**Key Conversions**:

| HTTP Model | Engine Model | Conversion Logic |
|------------|-------------|------------------|
| `QueryRequest` | `StructuredQuery` | Field-by-field mapping with validation |
| `QueryFilter` | `QueryFilter` | Direct mapping with operator enum conversion |
| `SortField` | `SortField` | Direct mapping with order enum conversion |
| `PaginationParams` | `QueryPagination` | Direct mapping with offset calculation |
| `QueryResponse` | `QueryResult` | Add HTTP-specific metadata (links, etc.) |

**Implementation Location**: `api/query_service.py` - `_build_internal_query()` method

### 2. Query Execution Bridge

**Async Wrapper Strategy**:
- Query engine is synchronous for performance
- HTTP layer requires async for concurrency
- Use `asyncio.to_thread()` for CPU-bound query operations

**Performance Considerations**:
- Cache query results at HTTP layer
- Implement query timeout protection
- Add request deduplication for identical queries

**Error Handling**:
```python
try:
    result = await asyncio.to_thread(self.engine.execute_structured_query, query)
except QueryValidationError as e:
    raise HTTPException(400, f"Invalid query: {e}")
except QueryExecutionError as e:
    raise HTTPException(500, f"Query failed: {e}")
except QuerySecurityError as e:
    raise HTTPException(403, f"Access denied: {e}")
```

### 3. Export System Architecture

**Job Management**:
```python
@dataclass
class ExportJobState:
    job_id: str
    status: str  # pending, running, completed, failed
    created_at: datetime
    query: StructuredQuery
    format: ExportFormat
    file_path: Optional[Path] = None
    error_message: Optional[str] = None
    progress: int = 0
    rows_exported: int = 0
```

**Export Processing Pipeline**:
1. **Job Creation**: Generate unique ID, validate query, estimate size
2. **Background Processing**: Execute query, stream to file, update progress
3. **File Management**: Store in temp directory, set expiration, cleanup

**Supported Formats**:
- CSV: Standard comma-separated values
- JSON: Pretty-printed array format
- JSONL: Newline-delimited JSON (streaming friendly)
- TSV: Tab-separated values
- Excel: Basic XLSX format (if openpyxl available)

### 4. Statistics Integration

**Metrics Collection Points**:
- Query execution time (start to finish)
- Cache hit/miss rates per tier (Memory, Redis, Disk)
- Database access patterns
- Filter usage frequency
- Export job statistics

**Statistics Storage**:
```python
class QueryMetrics:
    execution_time_ms: float
    cache_tier_hit: Optional[str]  # 'memory', 'redis', 'disk', None
    database_accessed: str
    filter_fields: List[str]
    result_count: int
    user_id: str
    timestamp: datetime
```

### 5. Database Schema Discovery

**Dynamic Schema Generation**:
1. Scan `blackcore/models/json/*.json` for available databases
2. Analyze first 100 records to infer field types
3. Generate field metadata with filter/sort capabilities

**Field Type Detection**:
```python
def detect_field_type(sample_values: List[Any]) -> FieldType:
    """Detect field type from sample values."""
    if all(isinstance(v, bool) for v in sample_values):
        return FieldType.BOOLEAN
    elif all(isinstance(v, (int, float)) for v in sample_values):
        return FieldType.NUMBER
    elif all(isinstance(v, str) and is_iso_date(v) for v in sample_values):
        return FieldType.DATE
    elif all(isinstance(v, list) for v in sample_values):
        return FieldType.MULTI_SELECT
    else:
        return FieldType.TEXT
```

## API Endpoint Implementations

### POST /api/v1/query/structured

**Request Processing Flow**:
1. Validate request model
2. Check user permissions for database
3. Apply rate limiting
4. Convert to internal query format
5. Execute query with caching
6. Convert results back to HTTP format
7. Generate HATEOAS links
8. Return response

**Response Enhancement**:
```json
{
  "data": [...],
  "total_count": 1500,
  "page": 1,
  "page_size": 100,
  "execution_time_ms": 45.2,
  "from_cache": true,
  "cache_tier": "memory",
  "links": {
    "self": "/api/v1/query/structured?page=1",
    "next": "/api/v1/query/structured?page=2",
    "export": "/api/v1/query/export"
  }
}
```

### POST /api/v1/query/search

**Text Search Implementation**:
1. Validate search parameters
2. Apply similarity threshold filtering
3. Search across specified databases
4. Rank results by relevance score
5. Apply pagination to results
6. Return formatted matches

**Search Result Format**:
```json
{
  "matches": [
    {
      "entity_id": "notion_page_id",
      "database": "Intelligence & Transcripts",
      "similarity_score": 0.92,
      "matched_content": "highlighted text snippet",
      "entity_data": { /* full record */ }
    }
  ],
  "query_text": "search terms",
  "execution_time_ms": 156.3,
  "total_matches": 25
}
```

### POST /api/v1/query/export

**Export Job Creation**:
1. Validate export request
2. Estimate result size and check quotas
3. Create background job
4. Return job tracking information
5. Process export asynchronously

**Export Job Processing**:
```python
async def process_export_job(job_id: str):
    """Background export job processor."""
    job = export_jobs[job_id]
    try:
        job.status = "running"
        
        # Execute query
        result = await asyncio.to_thread(
            engine.execute_structured_query,
            job.query
        )
        
        # Stream to file
        exporter = StreamingExporter()
        export_result = await exporter.export_data(
            result.data,
            job.file_path,
            job.format
        )
        
        job.status = "completed"
        job.rows_exported = export_result['rows_exported']
        job.file_size_bytes = export_result['file_size_bytes']
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
```

## Configuration

### Environment Variables
```bash
# Query Engine Configuration
QUERY_CACHE_DIR=blackcore/models/json
QUERY_TIMEOUT_SECONDS=30
EXPORT_TEMP_DIR=/tmp/blackcore_exports
EXPORT_RETENTION_HOURS=24

# Performance Tuning
MAX_CONCURRENT_QUERIES=10
MAX_EXPORT_SIZE_MB=100
DEFAULT_PAGE_SIZE=100
MAX_PAGE_SIZE=1000
```

### JSON Configuration Updates
```json
{
  "query_engine": {
    "cache_enabled": true,
    "statistics_enabled": true,
    "export_formats": ["csv", "json", "jsonl", "tsv"],
    "max_query_complexity": 20,
    "default_timeout_ms": 30000
  }
}
```

## Performance Specifications

### Query Performance Targets
- **Simple queries** (1-3 filters): < 50ms
- **Complex queries** (4+ filters): < 200ms  
- **Text search**: < 500ms
- **Cache hits**: < 5ms

### Export Performance Targets
- **Small exports** (< 1K rows): < 2 seconds
- **Medium exports** (1K-10K rows): < 30 seconds
- **Large exports** (10K+ rows): Background processing

### Memory Usage Targets
- **Query processing**: < 100MB per concurrent query
- **Export buffering**: < 50MB per export job
- **Cache overhead**: < 20% of cached data size

## Error Handling Strategy

### Error Categories
1. **Validation Errors** (400): Invalid request format, missing fields
2. **Authentication Errors** (401): Invalid or missing tokens
3. **Authorization Errors** (403): Insufficient permissions
4. **Not Found Errors** (404): Database or entity not found
5. **Rate Limit Errors** (429): Too many requests
6. **Server Errors** (500): Query execution failures, system errors

### Error Response Format
```json
{
  "error_code": "QUERY_VALIDATION_FAILED",
  "message": "Invalid filter operator 'invalid_op' for field 'Status'",
  "details": {
    "field": "filters[0].operator",
    "allowed_values": ["eq", "ne", "in", "not_in", "contains"]
  },
  "request_id": "req_12345",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Security Considerations

### Access Control
- **Database-level permissions**: Users can only query allowed databases
- **Field-level filtering**: Sensitive fields excluded from responses
- **Query complexity limits**: Prevent resource exhaustion attacks
- **Rate limiting**: Per-user and global request limits

### Data Protection
- **Input sanitization**: All query parameters validated and sanitized
- **SQL injection prevention**: Parameterized queries and input validation
- **Export security**: Temporary files with restricted permissions
- **Audit logging**: All query and export activities logged

## Testing Strategy

### Unit Tests
- Model conversion functions
- Query validation logic
- Export format generation
- Error handling scenarios

### Integration Tests
- Full HTTP → Engine → HTTP flow
- Cache integration and statistics
- Export job lifecycle
- Database schema discovery

### Performance Tests
- Query execution benchmarks
- Cache hit rate validation
- Concurrent request handling
- Export processing scalability

### Security Tests
- Access control validation
- Input sanitization verification
- Rate limiting enforcement
- Error information disclosure

## Migration Strategy

### Phase 1: Core Connection (This Implementation)
- Connect structured queries and text search
- Basic export functionality
- Essential error handling

### Phase 2: Enhanced Features
- Advanced export options (filtering, custom templates)
- Query optimization suggestions
- Real-time query progress updates

### Phase 3: Advanced Analytics
- Query performance analytics dashboard
- Usage pattern analysis
- Predictive caching
- Query recommendation engine

## Monitoring and Observability

### Metrics to Track
- Query response times (p50, p95, p99)
- Cache hit rates by tier
- Error rates by type
- Export job success rates
- Database usage patterns

### Logging Strategy
- **Debug**: Internal query conversion and processing
- **Info**: Successful query executions with timing
- **Warn**: Performance degradation or unusual patterns
- **Error**: Query failures and system errors

### Health Checks
- Database connectivity
- Cache system availability
- Export directory accessibility
- Background job processor status