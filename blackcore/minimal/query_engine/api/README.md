# Query Engine API

High-performance HTTP API for querying the BlackCore knowledge graph. Built with FastAPI for automatic OpenAPI/Swagger documentation and async support.

## Features

- 🚀 **High Performance** - Optimized query execution with caching
- 📖 **Auto Documentation** - Swagger UI and ReDoc interfaces
- 🔐 **API Key Authentication** - Secure access with rate limiting
- 🔍 **Advanced Querying** - Complex filters, sorting, and pagination
- 🔗 **Relationship Traversal** - Follow entity relationships
- 📊 **Batch Operations** - Execute multiple queries efficiently
- 🎯 **Text Search** - Full-text search across databases

## Quick Start

### Running the API

```bash
# Install dependencies
pip install fastapi uvicorn

# Run the server
python -m blackcore.minimal.query_engine.api.app

# Or with uvicorn directly
uvicorn blackcore.minimal.query_engine.api.app:app --reload
```

The API will be available at `http://localhost:8001`

### API Documentation

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

## Authentication

The API uses Bearer token authentication with API keys:

```bash
# Include API key in Authorization header
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8001/query
```

Default test API keys:
- `test-api-key` - Standard access (60 requests/minute)
- `admin-api-key` - Admin access (600 requests/minute)

## Core Endpoints

### Query Endpoint

`POST /query` - Execute structured queries

```json
{
  "database": "People & Contacts",
  "filters": [
    {
      "field": "properties.Department",
      "operator": "eq",
      "value": "Engineering"
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
```

### Search Endpoints

The Search API provides advanced semantic search capabilities:

- `POST /search` - Basic text search (deprecated, use /search/universal)
- `POST /search/universal` - Semantic search with NLP
- `POST /search/entities/{type}` - Entity-specific search
- `POST /search/semantic` - Context-aware semantic search
- `GET /search/suggestions` - Search suggestions

See [SEARCH_API.md](SEARCH_API.md) for comprehensive documentation.

Example:
```json
{
  "query": "Alice machine learning quarterly report",
  "databases": ["People & Contacts", "Documents & Evidence"],
  "enable_fuzzy": true,
  "enable_semantic": true
}
```

### System Endpoints

- `GET /health` - Health check
- `GET /status` - System status with database info
- `GET /databases` - List available databases
- `GET /databases/{name}/schema` - Get database schema

## Query Operators

Supported filter operators:

- `eq` - Equals
- `ne` - Not equals
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `contains` - Contains substring/element
- `not_contains` - Does not contain
- `in` - In list
- `not_in` - Not in list
- `between` - Between two values
- `is_null` - Is null
- `is_not_null` - Is not null
- `regex` - Regular expression match
- `fuzzy` - Fuzzy string matching

## Examples

### Complex Query Example

```python
import requests

# Query people in Engineering over 30 years old
query = {
    "database": "People & Contacts",
    "filters": [
        {
            "field": "properties.Department",
            "operator": "eq",
            "value": "Engineering"
        },
        {
            "field": "properties.Age",
            "operator": "gt",
            "value": 30
        }
    ],
    "sort": [
        {
            "field": "properties.Age",
            "order": "desc"
        }
    ],
    "pagination": {
        "page": 1,
        "size": 20
    }
}

response = requests.post(
    "http://localhost:8001/query",
    json=query,
    headers={"Authorization": "Bearer test-api-key"}
)

result = response.json()
print(f"Found {result['total_count']} people")
```

### Batch Query Example

```python
# Execute multiple queries in one request
batch_queries = [
    {
        "database": "People & Contacts",
        "filters": [{"field": "properties.Department", "operator": "eq", "value": "Sales"}]
    },
    {
        "database": "Actionable Tasks",
        "filters": [{"field": "properties.Status", "operator": "eq", "value": "In Progress"}]
    }
]

response = requests.post(
    "http://localhost:8001/query/batch",
    json=batch_queries,
    headers={"Authorization": "Bearer test-api-key"}
)

results = response.json()
```

### Text Search Example

```python
# Search for entities mentioning "AI"
search_request = {
    "query": "artificial intelligence",
    "databases": ["Intelligence & Transcripts", "Documents & Evidence"],
    "max_results": 50
}

response = requests.post(
    "http://localhost:8001/search",
    json=search_request,
    headers={"Authorization": "Bearer test-api-key"}
)

search_results = response.json()
```

## Performance

- Query results are cached for improved performance
- Batch queries execute in parallel
- Optimized filtering and sorting algorithms
- Support for 10K+ records with sub-second response times

## Configuration

Environment variables:

- `QUERY_ENGINE_CACHE_DIR` - Directory for JSON database files (default: `blackcore/models/json`)
- `ENABLE_CACHING` - Enable query result caching (default: `true`)
- `ENABLE_AUTH` - Enable API authentication (default: `true`)
- `API_PORT` - API server port (default: `8001`)

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `400` - Bad request (validation error)
- `401` - Unauthorized (invalid API key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not found
- `429` - Too many requests (rate limited)
- `500` - Internal server error

Error responses include details:

```json
{
  "error": "validation_error",
  "message": "Invalid filter operator 'foo'",
  "details": {
    "field": "filters[0].operator",
    "allowed_values": ["eq", "ne", "gt", "gte", "lt", "lte"]
  }
}
```

## Development

### Running Tests

```bash
# Run all API tests
pytest blackcore/minimal/query_engine/api/tests/ -v

# Run with coverage
pytest blackcore/minimal/query_engine/api/tests/ --cov=blackcore.minimal.query_engine.api
```

### Adding Custom Endpoints

1. Define request/response models in `models.py`
2. Add endpoint in `app.py`
3. Add authentication if needed
4. Write tests in `test_api.py`

### Performance Monitoring

The API includes execution time in all query responses:

```json
{
  "data": [...],
  "execution_time_ms": 45.2,
  "from_cache": false
}
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8001
CMD ["uvicorn", "blackcore.minimal.query_engine.api.app:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Scaling Considerations

1. **Load Balancing** - Run multiple API instances behind nginx/HAProxy
2. **Caching** - Use Redis for distributed caching
3. **Database** - Consider PostgreSQL for persistent storage
4. **Monitoring** - Add Prometheus metrics and tracing

## License

See main BlackCore project license.