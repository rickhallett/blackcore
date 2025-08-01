# Technical Specification: Streamlit GUI Integration with FastAPI Backend

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend (Port 8501)              │
├─────────────────────────────────────────────────────────────────┤
│  Dashboard │  Search │  Network │  Processing │  Transgressions │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP Requests (axios/requests)
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)                  │
├─────────────────────────────────────────────────────────────────┤
│  /dashboard/* │  /search/* │  /network/* │  /jobs/* │  /config/* │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               Existing Blackcore Infrastructure                │
├─────────────────────────────────────────────────────────────────┤
│  TranscriptProcessor │  NotionUpdater │  Cache │  Repositories  │
└─────────────────────────────────────────────────────────────────┘
```

## FastAPI Backend Extensions

### 1. Dashboard Endpoints

```python
# Add to blackcore/minimal/api/app.py

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import Query
import asyncio

@app.get("/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard_stats():
    """Get real-time dashboard statistics."""
    try:
        # Parallel data collection for performance
        stats_tasks = [
            get_transcript_count(),
            get_entity_counts(),
            get_processing_stats(),
            get_recent_activity()
        ]
        
        transcript_count, entity_counts, processing_stats, recent_activity = \
            await asyncio.gather(*stats_tasks)
        
        return DashboardStats(
            transcripts=transcript_count,
            entities=entity_counts,
            processing=processing_stats,
            recent_activity=recent_activity,
            last_updated=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard stats")

@app.get("/dashboard/timeline", response_model=List[TimelineEvent], tags=["Dashboard"])
async def get_timeline_events(
    days: int = Query(default=7, ge=1, le=30),
    entity_type: Optional[str] = Query(default=None)
):
    """Get timeline of intelligence events."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    events = await get_timeline_data(start_date, end_date, entity_type)
    return events

@app.get("/dashboard/metrics", response_model=ProcessingMetrics, tags=["Dashboard"])
async def get_processing_metrics():
    """Get processing performance metrics."""
    return await calculate_processing_metrics()
```

### 2. Search Endpoints

```python
@app.get("/search/global", response_model=GlobalSearchResults, tags=["Search"])
async def global_search(
    query: str = Query(..., min_length=2, max_length=200),
    entity_types: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    include_relationships: bool = Query(default=True)
):
    """Global search across all databases."""
    try:
        search_params = SearchParams(
            query=query,
            entity_types=entity_types or [],
            limit=limit,
            include_relationships=include_relationships
        )
        
        # Use existing search infrastructure
        results = await search_service.search_all_databases(search_params)
        
        return GlobalSearchResults(
            query=query,
            total_results=len(results),
            results=results,
            search_time=results.search_time,
            suggestions=await get_search_suggestions(query)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/search/entities/{entity_type}", response_model=List[EntityResult], tags=["Search"])
async def search_entities(
    entity_type: str,
    query: str = Query(...),
    filters: Optional[Dict[str, Any]] = Query(default=None)
):
    """Search within specific entity type."""
    valid_types = ["people", "organizations", "tasks", "events", "documents", "transgressions"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")
    
    results = await search_service.search_by_type(entity_type, query, filters)
    return results

@app.get("/search/suggestions", response_model=List[str], tags=["Search"])
async def get_search_suggestions(query: str = Query(..., min_length=1)):
    """Get search query suggestions."""
    return await search_service.get_suggestions(query)
```

### 3. Network/Relationship Endpoints

```python
@app.get("/network/graph", response_model=NetworkGraph, tags=["Network"])
async def get_network_graph(
    entity_id: Optional[str] = Query(default=None),
    depth: int = Query(default=2, ge=1, le=4),
    entity_types: Optional[List[str]] = Query(default=None),
    min_relationship_strength: float = Query(default=0.3, ge=0.0, le=1.0)
):
    """Get network graph data for visualization."""
    try:
        graph_params = NetworkParams(
            center_entity=entity_id,
            depth=depth,
            entity_types=entity_types,
            min_strength=min_relationship_strength
        )
        
        graph_data = await network_service.build_graph(graph_params)
        
        return NetworkGraph(
            nodes=graph_data.nodes,
            edges=graph_data.edges,
            metadata=graph_data.metadata,
            center_node=entity_id
        )
    except Exception as e:
        logger.error(f"Network graph error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate network graph")

@app.get("/network/relationships/{entity_id}", response_model=EntityRelationships, tags=["Network"])
async def get_entity_relationships(entity_id: str):
    """Get all relationships for a specific entity."""
    relationships = await relationship_service.get_entity_relationships(entity_id)
    return EntityRelationships(
        entity_id=entity_id,
        relationships=relationships,
        relationship_count=len(relationships)
    )

@app.get("/network/path", response_model=RelationshipPath, tags=["Network"])
async def find_relationship_path(
    from_entity: str = Query(...),
    to_entity: str = Query(...),
    max_depth: int = Query(default=4, ge=1, le=6)
):
    """Find shortest relationship path between two entities."""
    path = await network_service.find_path(from_entity, to_entity, max_depth)
    return RelationshipPath(
        from_entity=from_entity,
        to_entity=to_entity,
        path=path,
        path_length=len(path) - 1 if path else 0
    )
```

### 4. Processing Queue Endpoints

```python
@app.get("/queue/status", response_model=QueueStatus, tags=["Processing"])
async def get_queue_status():
    """Get current processing queue status."""
    if not job_queue:
        raise HTTPException(status_code=503, detail="Job queue not available")
    
    status = await job_queue.get_status()
    return QueueStatus(
        pending_jobs=status.pending,
        running_jobs=status.running,
        completed_jobs=status.completed,
        failed_jobs=status.failed,
        total_jobs=status.total,
        worker_status=await job_worker.get_status() if job_worker else "unavailable"
    )

@app.get("/queue/jobs", response_model=List[JobSummary], tags=["Processing"])
async def get_recent_jobs(limit: int = Query(default=20, ge=1, le=100)):
    """Get recent job history."""
    jobs = await job_queue.get_recent_jobs(limit)
    return [JobSummary.from_job(job) for job in jobs]

@app.post("/queue/clear", tags=["Processing"])
async def clear_completed_jobs(current_user: Dict[str, Any] = Security(require_admin)):
    """Clear completed and failed jobs from queue."""
    cleared = await job_queue.clear_completed()
    return {"message": f"Cleared {cleared} jobs from queue"}
```

### 5. Data Models for API Responses

```python
# Add to blackcore/minimal/api/models.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class DashboardStats(BaseModel):
    transcripts: Dict[str, int]
    entities: Dict[str, int] 
    processing: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    last_updated: datetime

class TimelineEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

class ProcessingMetrics(BaseModel):
    avg_processing_time: float
    success_rate: float
    entities_per_transcript: float
    relationships_per_transcript: float
    cache_hit_rate: float

class GlobalSearchResults(BaseModel):
    query: str
    total_results: int
    results: List[Dict[str, Any]]
    search_time: float
    suggestions: List[str]

class EntityResult(BaseModel):
    id: str
    type: str
    title: str
    properties: Dict[str, Any]
    relevance_score: float
    snippet: Optional[str] = None

class NetworkGraph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    center_node: Optional[str] = None

class EntityRelationships(BaseModel):
    entity_id: str
    relationships: List[Dict[str, Any]]
    relationship_count: int

class RelationshipPath(BaseModel):
    from_entity: str
    to_entity: str
    path: List[str]
    path_length: int

class QueueStatus(BaseModel):
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_jobs: int
    worker_status: str

class JobSummary(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    transcript_title: str
    entities_extracted: int
    processing_time: Optional[float]
    
    @classmethod
    def from_job(cls, job):
        return cls(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
            transcript_title=job.metadata.get("title", "Unknown"),
            entities_extracted=job.result.get("entities_count", 0) if job.result else 0,
            processing_time=job.processing_time
        )
```

## Streamlit Frontend Implementation

### 1. Main Application Structure

```python
# streamlit_app.py
import streamlit as st
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
st.set_page_config(
    page_title="Nassau Campaign Intelligence",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Client Class
class BlackcoreAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        # Add authentication headers if needed
        # self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/stats")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch dashboard stats: {e}")
            return None
    
    def search_global(self, query: str, entity_types=None, limit=50):
        """Perform global search."""
        params = {"query": query, "limit": limit}
        if entity_types:
            params["entity_types"] = entity_types
        
        try:
            response = self.session.get(f"{self.base_url}/search/global", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Search failed: {e}")
            return None
    
    def get_network_graph(self, entity_id=None, depth=2):
        """Get network graph data."""
        params = {"depth": depth}
        if entity_id:
            params["entity_id"] = entity_id
        
        try:
            response = self.session.get(f"{self.base_url}/network/graph", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch network data: {e}")
            return None
    
    def get_queue_status(self):
        """Get processing queue status."""
        try:
            response = self.session.get(f"{self.base_url}/queue/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch queue status: {e}")
            return None
    
    def get_recent_jobs(self, limit=20):
        """Get recent processing jobs."""
        try:
            response = self.session.get(f"{self.base_url}/queue/jobs", params={"limit": limit})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch recent jobs: {e}")
            return None

# Initialize API client
@st.cache_resource
def get_api_client():
    return BlackcoreAPI(API_BASE_URL)

api = get_api_client()
```

## Deployment Configuration

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  blackcore-api:
    build: 
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - BLACKCORE_MASTER_KEY=${BLACKCORE_MASTER_KEY}
      - NOTION_API_KEY=${NOTION_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./blackcore:/app/blackcore
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  streamlit-gui:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://blackcore-api:8000
    depends_on:
      - blackcore-api
    volumes:
      - ./streamlit_app.py:/app/streamlit_app.py
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  default:
    name: nassau-intelligence
```

### Implementation Timeline

**Week 1:** Core Infrastructure
- Day 1-2: FastAPI endpoint extensions
- Day 3-4: Basic Streamlit dashboard 
- Day 5-7: Search functionality

**Week 2:** Advanced Features
- Day 1-3: Network visualization
- Day 4-5: Processing queue management
- Day 6-7: Campaign-specific features

**Week 3:** Deployment & Refinement
- Day 1-2: Docker deployment
- Day 3-7: Campaign testing and iteration

This specification provides the foundation for rapid development of a campaign-focused intelligence GUI that leverages the existing Blackcore infrastructure.