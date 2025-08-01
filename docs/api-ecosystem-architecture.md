# BlackCore API & Ecosystem Architecture

## Executive Summary

BlackCore's architecture positions it as a central intelligence processing hub within a larger ecosystem of tools and services focused on Project Nassau. The system is designed with clear API boundaries to enable integration with multiple client applications while maintaining security and performance.

## Current API Architecture

### 1. **Existing HTTP API** (`blackcore/minimal/api/`)

BlackCore already includes a production-ready REST API with the following characteristics:

- **FastAPI Framework**: Modern async Python web framework with automatic OpenAPI/Swagger documentation
- **JWT Authentication**: Secure token-based authentication with API key management
- **Async Job Queue**: Redis-backed job processing for long-running operations
- **Auto-generated Documentation**: Swagger UI at `/docs`, ReDoc at `/redoc`

#### Core Endpoints:

```yaml
Authentication:
  - POST /auth/token         # Generate JWT from API key

Transcript Processing:
  - POST /transcripts/process # Process single transcript
  - POST /transcripts/batch   # Batch processing

Job Management:
  - GET  /jobs/{job_id}       # Check job status
  - GET  /jobs/{job_id}/result # Get completed results
  - POST /jobs/{job_id}/cancel # Cancel pending job

System:
  - GET  /health              # Health check
  - GET  /status              # Detailed system status

Configuration:
  - GET  /config/databases    # Available databases
  - PUT  /config/validation   # Update settings (admin)
```

### 2. **Planned API Extensions**

Based on the specs, additional API surfaces are planned:

#### Analytics Dashboard API (`/analytics/*`)
```yaml
Metrics & Insights:
  - GET  /analytics/overview         # System-wide metrics
  - GET  /analytics/activity/{period} # Activity timeline
  - GET  /analytics/entities/top     # Most connected entities
  - GET  /analytics/growth           # Growth trends

Search & Discovery:
  - POST /search/entities            # Full-text entity search
  - GET  /search/relationships       # Relationship exploration
  - POST /search/semantic            # AI-powered search

Data Export:
  - GET  /export/entities/{type}     # Export by entity type
  - POST /export/custom              # Custom export queries
  - GET  /export/formats             # Available formats
```

#### Query Engine API (`/query/*`)
```yaml
Structured Queries:
  - POST /query/structured           # SQL-like queries
  - POST /query/graph               # Graph traversal queries
  - POST /query/semantic            # Natural language queries

Query Management:
  - GET  /query/history             # Query history
  - POST /query/save                # Save query template
  - GET  /query/templates           # Saved templates
```

#### Webhook Receiver (`/webhooks/*`)
```yaml
Event Handling:
  - POST /webhooks/notion           # Notion webhook receiver
  - POST /webhooks/custom           # Custom integrations
  - GET  /webhooks/status          # Webhook health
```

## Ecosystem Positioning

### 1. **BlackCore as Central Hub**

BlackCore serves as the intelligence processing engine in a broader ecosystem:

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
├─────────────────┬──────────────────┬───────────────────────────┤
│  Google Drive   │   Notion API     │   Email/Calendar/Chat      │
│  (Transcripts)  │   (Database)     │   (Future Integration)     │
└────────┬────────┴────────┬─────────┴──────────┬────────────────┘
         │                 │                     │
         ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BlackCore Core                              │
├─────────────────────────────────────────────────────────────────┤
│  Intelligence    │  Deduplication   │  Query Engine  │  API     │
│  Processing      │  Engine          │  (New)         │  Gateway │
└─────────────────┴──────────────────┴────────────────┴──────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   Client Apps     │ │  Analytics Tools  │ │  Automation       │
├───────────────────┤ ├───────────────────┤ ├───────────────────┤
│ • Web Dashboard   │ │ • Grafana         │ │ • Zapier/n8n      │
│ • Mobile App      │ │ • Metabase        │ │ • GitHub Actions  │
│ • CLI Tools       │ │ • Custom Reports  │ │ • Slack Bots      │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

### 2. **Integration Points**

#### Upstream Integrations (Data Sources):
- **Google Drive**: Source transcripts and documents
- **Notion API**: Primary database and UI
- **Email Systems**: Future - meeting invites, correspondence
- **Chat Platforms**: Future - Slack, Teams transcripts
- **Audio/Video**: Future - direct recording processing

#### Downstream Integrations (Consumers):
- **Analytics Platforms**: Business intelligence dashboards
- **Automation Tools**: Workflow automation
- **Communication**: Notifications and alerts
- **Reporting**: Scheduled reports and summaries
- **AI Assistants**: Knowledge retrieval for chat interfaces

### 3. **API Gateway Considerations**

For production deployment, consider an API Gateway layer:

```yaml
Benefits:
  - Centralized authentication/authorization
  - Rate limiting and quotas
  - Request/response transformation
  - API versioning
  - Analytics and monitoring
  - Caching layer

Options:
  - Kong
  - AWS API Gateway
  - Traefik
  - nginx with modules
```

## What Should Be Exposed via HTTP API

### Essential APIs (Already Implemented):
1. **Transcript Processing**: Core functionality
2. **Authentication**: Security layer
3. **Job Management**: Async operation tracking
4. **Health/Status**: Operational monitoring

### High-Value APIs (Should Implement):

1. **Query Engine API**
   - Enables external tools to query the knowledge graph
   - Supports custom reporting and analysis
   - Foundation for AI assistant integrations

2. **Search API**
   - Universal search across all entities
   - Semantic search capabilities
   - Relationship exploration

3. **Analytics API**
   - Real-time metrics and KPIs
   - Activity tracking
   - Trend analysis

4. **Webhook Receivers**
   - Real-time synchronization
   - Event-driven workflows
   - Third-party integrations

5. **Export API**
   - Bulk data export
   - Multiple format support
   - Scheduled exports

### APIs to Consider for Future:

1. **GraphQL Endpoint**
   - More flexible queries
   - Reduced over-fetching
   - Better for complex relationships

2. **WebSocket/SSE**
   - Real-time updates
   - Live collaboration features
   - Progress streaming

3. **Batch Operations**
   - Bulk entity updates
   - Mass relationship creation
   - Import/export workflows

## Security & Access Control

### API Key Management
```python
class APIKeyManager:
    """Manage API keys with scopes and rate limits."""
    
    scopes = {
        "read": ["GET /api/*"],
        "write": ["POST /api/*", "PUT /api/*"],
        "admin": ["*"],
        "analytics": ["GET /analytics/*"],
        "webhooks": ["POST /webhooks/*"]
    }
    
    rate_limits = {
        "default": "60/minute",
        "analytics": "600/minute",
        "batch": "10/minute",
        "export": "5/minute"
    }
```

### Authentication Layers
1. **API Keys**: For service-to-service
2. **JWT Tokens**: For user sessions
3. **OAuth2**: For third-party integrations
4. **Webhook Signatures**: For webhook validation

## Swagger/OpenAPI Integration

BlackCore's FastAPI implementation automatically generates OpenAPI schemas:

### Accessing API Documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Enhancing API Documentation:
```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="BlackCore Intelligence API",
    description="Central intelligence processing for Project Nassau",
    version="2.0.0",
    terms_of_service="https://example.com/terms",
    contact={
        "name": "BlackCore Team",
        "email": "support@example.com"
    },
    license_info={
        "name": "Proprietary",
    }
)

class TranscriptInput(BaseModel):
    """Input model for transcript processing."""
    
    title: str = Field(
        ..., 
        description="Title of the transcript",
        example="Q4 Planning Meeting"
    )
    content: str = Field(
        ..., 
        description="Full transcript content",
        example="John: Let's discuss Q4 objectives..."
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata",
        example={"source": "zoom", "duration": 3600}
    )
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Team Standup - 2024-01-15",
                "content": "Sarah: Yesterday I completed...",
                "metadata": {
                    "participants": ["Sarah", "John", "Mike"],
                    "duration": 900
                }
            }
        }
```

## Deployment Recommendations

### 1. **API Versioning Strategy**
```
/api/v1/  - Current stable API
/api/v2/  - New query engine features
/api/beta/ - Experimental endpoints
```

### 2. **Load Balancing**
```nginx
upstream blackcore_api {
    server api1.internal:8000;
    server api2.internal:8000;
    server api3.internal:8000;
}
```

### 3. **Caching Strategy**
- **Redis**: API response caching
- **CDN**: Static asset delivery
- **Database**: Query result caching

### 4. **Monitoring & Observability**
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Jaeger**: Distributed tracing
- **ELK Stack**: Log aggregation

## Ecosystem Integration Examples

### 1. **Slack Bot Integration**
```python
@app.post("/integrations/slack/commands")
async def handle_slack_command(
    command: str,
    text: str,
    user_id: str
):
    if command == "/search":
        results = await search_entities(text)
        return format_slack_response(results)
```

### 2. **Zapier Webhook**
```python
@app.post("/integrations/zapier/trigger")
async def zapier_trigger(
    event_type: str,
    entity_id: str
):
    # Trigger Zapier workflows on entity changes
    pass
```

### 3. **GitHub Actions**
```yaml
- name: Process Meeting Notes
  uses: http://api.blackcore.com/actions/process
  with:
    transcript: ${{ steps.notes.outputs.content }}
    dry_run: false
```

## Next Steps

1. **Implement Query Engine API** - Enable external querying
2. **Add Analytics Endpoints** - Provide insights API
3. **Setup API Gateway** - Centralize API management
4. **Create SDK/Client Libraries** - Ease integration
5. **Implement Webhook System** - Enable real-time sync
6. **Add GraphQL Layer** - Optional, for complex queries
7. **Enhance Documentation** - API cookbook and examples

The architecture is well-positioned to serve as a central intelligence hub, with clear extension points for ecosystem growth while maintaining security and performance standards.