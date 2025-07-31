# Analytics Dashboard Specification

## Overview

A FastAPI-based analytics dashboard that provides real-time insights into the Blackcore knowledge graph through RESTful endpoints and a simple web interface.

## Goals

1. Provide quick access to key metrics and insights
2. Enable entity search and relationship exploration
3. Visualize activity trends and patterns
4. Support data export for reporting
5. Maintain sub-second response times

## Architecture

### FastAPI Application Structure

```python
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

app = FastAPI(title="Blackcore Analytics", version="1.0.0")

# Enable CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for simple UI
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### Core Data Models

```python
class EntitySummary(BaseModel):
    id: str
    type: str
    name: str
    created: datetime
    last_modified: datetime
    relationship_count: int

class RelationshipStats(BaseModel):
    entity_id: str
    entity_name: str
    total_connections: int
    connections_by_type: Dict[str, int]
    most_connected_to: List[EntitySummary]

class ActivityMetrics(BaseModel):
    period: str  # "day", "week", "month"
    entities_created: int
    entities_modified: int
    relationships_created: int
    transcripts_processed: int
    timeline: List[Dict[str, Any]]

class SearchResult(BaseModel):
    entity: EntitySummary
    score: float
    context: Optional[str]
    database: str
```

### Analytics Service

```python
class AnalyticsService:
    def __init__(self, json_cache_path: str):
        self.cache_path = json_cache_path
        self.data = self._load_all_data()
        self._build_indexes()
    
    def _build_indexes(self):
        """Build in-memory indexes for fast queries"""
        self.entity_index = {}
        self.relationship_index = {}
        self.timeline_index = defaultdict(list)
        
        for db_name, db_data in self.data.items():
            for entity in db_data.get("items", []):
                entity_id = entity.get("id")
                self.entity_index[entity_id] = {
                    "database": db_name,
                    "data": entity
                }
                
                # Index by creation date
                created = entity.get("created_time")
                if created:
                    date = datetime.fromisoformat(created).date()
                    self.timeline_index[date].append({
                        "type": "created",
                        "entity_id": entity_id,
                        "database": db_name
                    })
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        stats = {
            "total_entities": 0,
            "by_database": {},
            "total_relationships": 0,
            "recent_activity": {
                "last_24h": 0,
                "last_week": 0,
                "last_month": 0
            }
        }
        
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        for db_name, db_data in self.data.items():
            count = len(db_data.get("items", []))
            stats["total_entities"] += count
            stats["by_database"][db_name] = count
            
            # Count recent activity
            for entity in db_data.get("items", []):
                created = entity.get("created_time")
                if created:
                    created_dt = datetime.fromisoformat(created)
                    if created_dt > day_ago:
                        stats["recent_activity"]["last_24h"] += 1
                    if created_dt > week_ago:
                        stats["recent_activity"]["last_week"] += 1
                    if created_dt > month_ago:
                        stats["recent_activity"]["last_month"] += 1
        
        return stats
    
    def get_relationship_stats(self, entity_id: str) -> RelationshipStats:
        """Get relationship statistics for an entity"""
        entity_data = self.entity_index.get(entity_id)
        if not entity_data:
            raise ValueError(f"Entity {entity_id} not found")
        
        connections = defaultdict(list)
        
        # Find all relationships
        for prop_name, prop_value in entity_data["data"].items():
            if isinstance(prop_value, list) and prop_value:
                # Check if it's a relation property
                first_item = prop_value[0]
                if isinstance(first_item, dict) and "id" in first_item:
                    for related in prop_value:
                        connections[prop_name].append(related["id"])
        
        # Count connections by type
        connections_by_type = {k: len(v) for k, v in connections.items()}
        total = sum(connections_by_type.values())
        
        # Find most connected entities
        all_connected = []
        for connected_ids in connections.values():
            all_connected.extend(connected_ids)
        
        # Get top 5 most frequent connections
        from collections import Counter
        most_common = Counter(all_connected).most_common(5)
        
        most_connected_to = []
        for conn_id, count in most_common:
            if conn_id in self.entity_index:
                conn_data = self.entity_index[conn_id]
                most_connected_to.append(EntitySummary(
                    id=conn_id,
                    type=conn_data["database"],
                    name=self._get_entity_name(conn_data["data"]),
                    created=conn_data["data"].get("created_time"),
                    last_modified=conn_data["data"].get("last_edited_time"),
                    relationship_count=count
                ))
        
        return RelationshipStats(
            entity_id=entity_id,
            entity_name=self._get_entity_name(entity_data["data"]),
            total_connections=total,
            connections_by_type=connections_by_type,
            most_connected_to=most_connected_to
        )
```

### API Endpoints

```python
# 1. Summary Statistics
@app.get("/api/stats/summary")
async def get_summary_stats():
    """Get overall system statistics"""
    return analytics.get_summary_stats()

# 2. Database Statistics
@app.get("/api/stats/database/{database_name}")
async def get_database_stats(database_name: str):
    """Get statistics for a specific database"""
    data = analytics.get_database_stats(database_name)
    if not data:
        raise HTTPException(status_code=404, detail="Database not found")
    return data

# 3. Relationship Statistics
@app.get("/api/stats/relationships")
async def get_top_relationships(limit: int = 20):
    """Get most connected entities"""
    return analytics.get_most_connected_entities(limit)

# 4. Activity Timeline
@app.get("/api/stats/activity")
async def get_activity_timeline(
    period: str = Query("week", regex="^(day|week|month)$"),
    database: Optional[str] = None
):
    """Get activity metrics over time"""
    return analytics.get_activity_metrics(period, database)

# 5. Entity Search
@app.get("/api/search/entities")
async def search_entities(
    q: str = Query(..., min_length=2),
    databases: Optional[List[str]] = Query(None),
    limit: int = Query(20, le=100)
):
    """Search for entities across databases"""
    results = analytics.search_entities(q, databases, limit)
    return {"query": q, "count": len(results), "results": results}

# 6. Entity Details
@app.get("/api/entities/{entity_id}")
async def get_entity_details(entity_id: str):
    """Get detailed information about an entity"""
    entity = analytics.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity

# 7. Entity Connections
@app.get("/api/graph/connections/{entity_id}")
async def get_entity_connections(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3)
):
    """Get entity's connection graph"""
    return analytics.get_connection_graph(entity_id, depth)

# 8. Export Data
@app.get("/api/export/{format}")
async def export_data(
    format: str = Path(..., regex="^(json|csv)$"),
    database: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Export data in various formats"""
    data = analytics.export_data(database, start_date, end_date)
    
    if format == "csv":
        output = analytics.to_csv(data)
        return Response(content=output, media_type="text/csv")
    else:
        return JSONResponse(content=data)

# 9. Intelligence Insights
@app.get("/api/insights/trending")
async def get_trending_topics(days: int = Query(7, ge=1, le=30)):
    """Get trending topics from recent intelligence"""
    return analytics.get_trending_topics(days)

# 10. Task Analytics
@app.get("/api/stats/tasks")
async def get_task_analytics():
    """Get task completion rates and bottlenecks"""
    return {
        "completion_rate": analytics.get_task_completion_rate(),
        "overdue_tasks": analytics.get_overdue_tasks(),
        "task_distribution": analytics.get_task_distribution_by_assignee(),
        "average_completion_time": analytics.get_avg_task_completion_time()
    }
```

### Simple Web UI

```html
<!-- static/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Blackcore Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-8">Blackcore Analytics Dashboard</h1>
        
        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold text-gray-600">Total Entities</h3>
                <p class="text-3xl font-bold" id="total-entities">-</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold text-gray-600">Active Today</h3>
                <p class="text-3xl font-bold" id="active-today">-</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold text-gray-600">Relationships</h3>
                <p class="text-3xl font-bold" id="total-relationships">-</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold text-gray-600">Tasks Pending</h3>
                <p class="text-3xl font-bold" id="tasks-pending">-</p>
            </div>
        </div>
        
        <!-- Search Bar -->
        <div class="bg-white p-6 rounded-lg shadow mb-8">
            <input type="text" id="search-input" 
                   class="w-full px-4 py-2 border rounded-lg" 
                   placeholder="Search entities...">
            <div id="search-results" class="mt-4"></div>
        </div>
        
        <!-- Charts -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-xl font-semibold mb-4">Activity Timeline</h3>
                <canvas id="activity-chart"></canvas>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-xl font-semibold mb-4">Entity Distribution</h3>
                <canvas id="distribution-chart"></canvas>
            </div>
        </div>
    </div>
    
    <script src="/static/dashboard.js"></script>
</body>
</html>
```

```javascript
// static/dashboard.js
async function loadDashboard() {
    // Load summary stats
    const stats = await fetch('/api/stats/summary').then(r => r.json());
    document.getElementById('total-entities').textContent = stats.total_entities;
    document.getElementById('active-today').textContent = stats.recent_activity.last_24h;
    document.getElementById('total-relationships').textContent = stats.total_relationships;
    
    // Load task stats
    const tasks = await fetch('/api/stats/tasks').then(r => r.json());
    document.getElementById('tasks-pending').textContent = tasks.overdue_tasks.length;
    
    // Load activity chart
    const activity = await fetch('/api/stats/activity?period=week').then(r => r.json());
    createActivityChart(activity);
    
    // Load distribution chart
    createDistributionChart(stats.by_database);
}

// Search functionality
document.getElementById('search-input').addEventListener('input', async (e) => {
    const query = e.target.value;
    if (query.length < 2) return;
    
    const results = await fetch(`/api/search/entities?q=${query}`).then(r => r.json());
    displaySearchResults(results.results);
});

// Initialize on load
document.addEventListener('DOMContentLoaded', loadDashboard);
```

## Performance Optimizations

1. **In-Memory Caching**: Cache frequently accessed data
2. **Indexed Search**: Pre-build search indexes
3. **Pagination**: Limit result sizes
4. **Async Processing**: Non-blocking I/O operations
5. **Response Caching**: Cache computed results

## Deployment

```bash
# Development
uvicorn app:app --reload --port 8001

# Production with Gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001

# Docker deployment
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

## Testing Strategy

1. **API Tests**: Test all endpoints with various parameters
2. **Load Tests**: Verify performance with 1000+ concurrent requests
3. **Data Tests**: Validate calculations and aggregations
4. **UI Tests**: Basic frontend functionality

## Security

1. **API Keys**: Optional authentication for production
2. **Rate Limiting**: Prevent abuse
3. **Input Validation**: Sanitize all queries
4. **CORS**: Configure for production domains

## Timeline

- Day 1: Core FastAPI setup and data models
- Day 2: Analytics service and calculations
- Day 3: API endpoints implementation
- Day 4: Simple web UI
- Day 5: Testing and optimization