# Blackcore Minimal API

HTTP(S) API for the Blackcore Minimal Transcript Processor, providing RESTful endpoints for transcript processing and entity extraction.

## Features

- 🔐 JWT-based authentication with API keys
- 🚀 Async processing with job queue
- 📊 Real-time job status tracking
- 🔄 Batch transcript processing
- 🛡️ Rate limiting and security
- 📖 Auto-generated API documentation
- 🐳 Docker support

## Quick Start

### Local Development

1. Install dependencies:
```bash
uv sync
# or
pip install -e .
```

2. Set environment variables:
```bash
export NOTION_API_KEY="your-notion-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export API_SECRET_KEY="your-secret-key-change-in-production"
```

3. Run the API server:
```bash
python -m blackcore.minimal.api.server
```

4. Visit API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. Build and run with Docker Compose:
```bash
cd blackcore/minimal/api
docker-compose up -d
```

2. Check health:
```bash
curl http://localhost:8000/health
```

## API Usage

### Authentication

1. Generate access token:
```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}'
```

2. Use token in requests:
```bash
export TOKEN="your-access-token"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/transcripts/process
```

### Process Transcript

```bash
curl -X POST http://localhost:8000/transcripts/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": {
      "title": "Team Meeting",
      "content": "Discussion about Q4 objectives...",
      "date": "2024-01-15T10:00:00Z",
      "source": "google_meet"
    },
    "options": {
      "dry_run": false,
      "enable_deduplication": true,
      "deduplication_threshold": 90.0
    }
  }'
```

### Check Job Status

```bash
# Get job status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/jobs/{job_id}

# Get job result (when completed)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/jobs/{job_id}/result
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/transcripts/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transcripts": [
      {
        "title": "Meeting 1",
        "content": "First meeting content...",
        "date": "2024-01-15T09:00:00Z"
      },
      {
        "title": "Meeting 2",
        "content": "Second meeting content...",
        "date": "2024-01-15T10:00:00Z"
      }
    ],
    "options": {
      "dry_run": false
    },
    "batch_size": 10
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `API_SECRET_KEY` | JWT signing key | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `NOTION_API_KEY` | Notion API key | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `RUN_WORKER` | Run worker in same process | `true` |

### Rate Limiting

Default: 60 requests per minute per API key

Configure in `auth.py`:
```python
rate_limiter = RateLimiter(requests_per_minute=60)
```

## API Endpoints

### System
- `GET /health` - Health check
- `GET /status` - Detailed system status

### Authentication
- `POST /auth/token` - Generate access token

### Transcript Processing
- `POST /transcripts/process` - Process single transcript
- `POST /transcripts/batch` - Process multiple transcripts

### Job Management
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs/{job_id}/result` - Get job result
- `POST /jobs/{job_id}/cancel` - Cancel pending job

### Configuration
- `GET /config/databases` - Get database configuration
- `PUT /config/validation` - Update validation settings (admin)

## Development

### Running Tests

```bash
# Run all API tests
pytest blackcore/minimal/tests/test_api.py -v

# Run specific test class
pytest blackcore/minimal/tests/test_api.py::TestAuthentication -v

# Run with coverage
pytest blackcore/minimal/tests/test_api.py --cov=blackcore.minimal.api
```

### Adding New Endpoints

1. Define models in `models.py`
2. Add endpoint in `app.py`
3. Add authentication/authorization as needed
4. Write tests in `test_api.py`

### Custom Authentication

To implement custom authentication:

1. Extend `auth.py`:
```python
async def verify_api_key_from_db(api_key: str) -> Optional[Dict]:
    # Implement database lookup
    pass
```

2. Update token generation:
```python
@app.post("/auth/token")
async def generate_token(request: TokenRequest):
    user = await verify_api_key_from_db(request.api_key)
    if not user:
        raise HTTPException(401, "Invalid API key")
    
    return auth_handler.generate_token_response(
        api_key=request.api_key,
        expires_in=request.expires_in
    )
```

## Production Deployment

### Security Checklist

- [ ] Change `API_SECRET_KEY` from default
- [ ] Use HTTPS with valid certificates
- [ ] Configure CORS origins properly
- [ ] Set up API key management
- [ ] Enable request logging
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting

### Scaling

1. **Separate Workers**: Run API and workers separately
2. **Load Balancing**: Use nginx/HAProxy for multiple API instances
3. **Redis Cluster**: For high-availability job queue
4. **Database**: Store job results in PostgreSQL for persistence

### Monitoring

- Prometheus metrics: `/metrics` (add prometheus-fastapi-instrumentator)
- Health checks: `/health`
- Structured logging with request IDs
- OpenTelemetry tracing support

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis is running: `redis-cli ping`
   - Verify `REDIS_URL` is correct
   - Falls back to in-memory queue

2. **Authentication Errors**
   - Verify token not expired
   - Check `API_SECRET_KEY` matches
   - Ensure Bearer format: `Bearer <token>`

3. **Job Not Processing**
   - Check worker is running
   - Verify Redis connectivity
   - Check logs for errors

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m blackcore.minimal.api.server
```

## API Client Examples

### Python Client

```python
import requests

class BlackcoreClient:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.token = None
        
    def authenticate(self):
        response = requests.post(
            f"{self.api_url}/auth/token",
            json={"api_key": self.api_key}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        
    def process_transcript(self, transcript):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.api_url}/transcripts/process",
            headers=headers,
            json={"transcript": transcript}
        )
        response.raise_for_status()
        return response.json()
```

### JavaScript/TypeScript Client

```typescript
class BlackcoreClient {
  private token: string | null = null;
  
  constructor(
    private apiUrl: string,
    private apiKey: string
  ) {}
  
  async authenticate(): Promise<void> {
    const response = await fetch(`${this.apiUrl}/auth/token`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: this.apiKey})
    });
    
    const data = await response.json();
    this.token = data.access_token;
  }
  
  async processTranscript(transcript: any): Promise<any> {
    const response = await fetch(`${this.apiUrl}/transcripts/process`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({transcript})
    });
    
    return response.json();
  }
}
```

## License

See main project LICENSE file.