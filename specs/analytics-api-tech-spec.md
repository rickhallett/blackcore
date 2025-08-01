# BlackCore Analytics API Technical Specification

## 1. Overview

The Analytics API provides comprehensive real-time intelligence metrics, entity relationship analysis, and operational insights for the BlackCore intelligence processing system. It transforms raw intelligence data into actionable insights through advanced analytics and visualization.

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics API Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Overview │ Network │ Timeline │ Tasks │ Intelligence │ System  │
│  Endpoint │ Analysis│ Analysis │ Perf  │  Insights    │ Health  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 Analytics Engine Core                           │
├─────────────────────────────────────────────────────────────────┤
│  Metrics        │ Network       │ Trend         │ Cache         │
│  Calculator     │ Analyzer      │ Analyzer      │ Manager       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Data Layer                                   │
├─────────────────────────────────────────────────────────────────┤
│  People &    │ Tasks │ Organizations │ Documents │ Intelligence │
│  Contacts    │       │ & Bodies      │ Evidence  │ Transcripts  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

- **Analytics Engine**: Core computation orchestrator
- **Metrics Calculator**: Statistical computations and KPI calculations
- **Network Analyzer**: Entity relationship mapping and graph analysis
- **Trend Analyzer**: Time-series analysis and pattern detection
- **Cache Manager**: Performance optimization and result caching

## 3. Data Models

### 3.1 Request Models

```python
class AnalyticsRequest(BaseModel):
    """Base analytics request with common filters."""
    start_date: Optional[datetime] = Field(None, description="Start date for analysis")
    end_date: Optional[datetime] = Field(None, description="End date for analysis") 
    databases: Optional[List[str]] = Field(None, description="Specific databases to analyze")
    entity_types: Optional[List[str]] = Field(None, description="Entity types to include")
    refresh_cache: bool = Field(False, description="Force cache refresh")

class NetworkAnalysisRequest(AnalyticsRequest):
    """Network analysis specific parameters."""
    max_depth: int = Field(3, ge=1, le=5, description="Maximum relationship depth")
    min_connections: int = Field(2, ge=1, description="Minimum connections to include")
    algorithm: NetworkAlgorithm = Field(NetworkAlgorithm.CENTRALITY, description="Analysis algorithm")

class TimelineRequest(AnalyticsRequest):
    """Timeline analysis parameters."""
    granularity: TimeGranularity = Field(TimeGranularity.DAILY, description="Time granularity")
    metrics: List[str] = Field(..., description="Metrics to track over time")
    include_forecasting: bool = Field(False, description="Include trend forecasting")
```

### 3.2 Response Models

```python
class OverviewResponse(BaseModel):
    """Dashboard overview response."""
    total_entities: Dict[str, int]
    recent_activity: ActivitySummary
    top_metrics: Dict[str, float]
    health_indicators: HealthStatus
    trends: Dict[str, TrendIndicator]
    execution_time_ms: float

class NetworkNode(BaseModel):
    """Network graph node."""
    id: str
    label: str
    type: str
    properties: Dict[str, Any]
    centrality_score: float
    connections: int

class NetworkEdge(BaseModel):
    """Network graph edge."""
    source: str
    target: str
    relationship: str
    weight: float
    properties: Dict[str, Any]

class NetworkAnalysisResponse(BaseModel):
    """Network analysis results."""
    nodes: List[NetworkNode]
    edges: List[NetworkEdge] 
    communities: List[Community]
    metrics: NetworkMetrics
    execution_time_ms: float
```

### 3.3 Enumeration Types

```python
class NetworkAlgorithm(str, Enum):
    CENTRALITY = "centrality"
    COMMUNITY = "community"
    INFLUENCE = "influence"
    CLUSTERING = "clustering"

class TimeGranularity(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily" 
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class MetricType(str, Enum):
    COUNT = "count"
    RATE = "rate"
    PERCENTAGE = "percentage"
    DISTRIBUTION = "distribution"
```

## 4. Analytics Engine Specifications

### 4.1 Core Metrics Categories

#### 4.1.1 Entity Metrics
- **Total Counts**: People, Organizations, Tasks, Documents, Events
- **Growth Rates**: New entities per time period
- **Status Distributions**: Active/Inactive, Priority levels, Completion rates
- **Relationship Density**: Average connections per entity

#### 4.1.2 Task Analytics
- **Completion Metrics**: Tasks completed, overdue, in progress
- **Performance by Assignee**: Individual productivity statistics
- **Priority Analysis**: High/Medium/Low priority distributions
- **Timeline Tracking**: Average completion time, velocity trends

#### 4.1.3 Intelligence Metrics
- **Processing Volume**: Documents processed, transcripts analyzed
- **Quality Indicators**: Data completeness, validation scores
- **Pattern Detection**: Anomalies, emerging trends, correlation analysis
- **Evidence Tracking**: Evidence collection rates, verification status

#### 4.1.4 Network Analytics
- **Centrality Analysis**: Most connected/influential entities
- **Community Detection**: Entity clusters and groups
- **Relationship Strength**: Connection weights and frequencies
- **Influence Mapping**: Information flow and authority metrics

### 4.2 Performance Requirements

- **Response Time**: <500ms for cached results, <2s for complex computations
- **Concurrency**: Support 50+ concurrent analytics requests
- **Data Volume**: Efficiently process 100K+ entities
- **Cache Hit Rate**: >80% for frequently accessed metrics
- **Memory Usage**: <1GB for analytics computations

### 4.3 Computation Algorithms

#### 4.3.1 Network Analysis Algorithms

```python
def calculate_centrality_scores(graph: NetworkGraph) -> Dict[str, float]:
    """Calculate betweenness centrality scores for all nodes."""
    # Implementation using NetworkX algorithms
    # Returns normalized centrality scores (0-1)

def detect_communities(graph: NetworkGraph) -> List[Community]:
    """Identify communities using Louvain algorithm."""
    # Community detection for entity clustering
    # Returns community assignments with modularity scores

def calculate_influence_scores(graph: NetworkGraph) -> Dict[str, float]:
    """Calculate PageRank-based influence scores."""
    # Authority and hub analysis for influence mapping
    # Returns influence scores normalized (0-1)
```

#### 4.3.2 Time Series Analysis

```python
def calculate_trends(data: TimeSeries, window: int = 7) -> TrendAnalysis:
    """Calculate trend indicators using moving averages."""
    # Trend direction, velocity, acceleration analysis
    # Returns trend classification (up/down/stable)

def detect_anomalies(data: TimeSeries, threshold: float = 2.0) -> List[Anomaly]:
    """Detect statistical anomalies using z-score analysis.""" 
    # Anomaly detection for unusual patterns
    # Returns anomaly points with confidence scores

def forecast_metrics(data: TimeSeries, periods: int = 30) -> Forecast:
    """Generate simple forecasts using linear regression."""
    # Basic forecasting for trend projection
    # Returns forecast values with confidence intervals
```

## 5. API Endpoint Specifications

### 5.1 Overview Dashboard
```
GET /analytics/overview
```

**Parameters:**
- `period`: Time period (7d, 30d, 90d, 1y)
- `refresh`: Force cache refresh (default: false)

**Response:**
```json
{
  "total_entities": {
    "people": 1234,
    "organizations": 567, 
    "tasks": 890,
    "documents": 2345
  },
  "recent_activity": {
    "last_24h": 45,
    "last_7d": 312,
    "trend": "increasing"
  },
  "top_metrics": {
    "task_completion_rate": 0.85,
    "avg_response_time": 245.6,
    "data_freshness": 0.92
  },
  "health_indicators": {
    "system_health": "healthy",
    "data_quality": 0.94,
    "api_performance": "good"
  }
}
```

### 5.2 Network Analysis
```
GET /analytics/entities/network
```

**Parameters:**
- `entity_type`: Focus on specific entity type
- `max_depth`: Maximum relationship traversal depth
- `algorithm`: Analysis algorithm (centrality, community, influence)
- `min_connections`: Minimum connections threshold

**Response:**
```json
{
  "nodes": [
    {
      "id": "person_123",
      "label": "Alice Johnson", 
      "type": "person",
      "centrality_score": 0.87,
      "connections": 15,
      "properties": {"department": "Engineering"}
    }
  ],
  "edges": [
    {
      "source": "person_123",
      "target": "org_456", 
      "relationship": "works_for",
      "weight": 0.9
    }
  ],
  "communities": [
    {
      "id": "community_1",
      "members": ["person_123", "person_124"],
      "label": "Engineering Team",
      "modularity": 0.45
    }
  ],
  "metrics": {
    "total_nodes": 234,
    "total_edges": 567,
    "density": 0.12,
    "avg_clustering": 0.34
  }
}
```

### 5.3 Activity Timeline
```
GET /analytics/activities/timeline
```

**Parameters:**
- `start_date`: Analysis start date
- `end_date`: Analysis end date
- `granularity`: Time granularity (daily, weekly, monthly)
- `metrics`: Specific metrics to track

**Response:**
```json
{
  "timeline": [
    {
      "date": "2024-01-15",
      "metrics": {
        "new_entities": 12,
        "completed_tasks": 8,
        "documents_processed": 23
      }
    }
  ],
  "trends": {
    "new_entities": {
      "direction": "increasing",
      "rate": 0.15,
      "confidence": 0.78
    }
  },
  "forecast": {
    "next_30_days": [
      {"date": "2024-02-01", "predicted_value": 15.2}
    ]
  }
}
```

### 5.4 Task Performance
```
GET /analytics/tasks/performance
```

**Parameters:**
- `assignee`: Filter by assignee
- `priority`: Filter by priority level
- `status`: Filter by task status
- `timeframe`: Analysis timeframe

**Response:**
```json
{
  "completion_metrics": {
    "total_tasks": 345,
    "completed": 278,
    "completion_rate": 0.806,
    "avg_completion_time": 4.2
  },
  "by_priority": {
    "high": {"total": 45, "completed": 40, "rate": 0.89},
    "medium": {"total": 150, "completed": 125, "rate": 0.83},
    "low": {"total": 150, "completed": 113, "rate": 0.75}
  },
  "by_assignee": [
    {
      "assignee": "Alice Johnson",
      "assigned": 25,
      "completed": 23,
      "rate": 0.92,
      "avg_time": 3.1
    }
  ]
}
```

### 5.5 Intelligence Insights
```
GET /analytics/intelligence/insights
```

**Parameters:**
- `insight_type`: Type of insights (patterns, anomalies, correlations)
- `confidence_threshold`: Minimum confidence level
- `limit`: Maximum number of insights

**Response:**
```json
{
  "patterns": [
    {
      "type": "temporal",
      "description": "Increased activity on Mondays",
      "confidence": 0.87,
      "supporting_data": {
        "samples": 156,
        "correlation": 0.73
      }
    }
  ],
  "anomalies": [
    {
      "type": "volume",
      "description": "Unusual spike in document processing",
      "date": "2024-01-15",
      "severity": "medium",
      "details": {
        "expected": 25,
        "actual": 67,
        "z_score": 2.8
      }
    }
  ],
  "correlations": [
    {
      "entities": ["task_completion", "document_volume"],
      "correlation": 0.64,
      "p_value": 0.003,
      "relationship": "positive"
    }
  ]
}
```

### 5.6 System Health
```
GET /analytics/system/health
```

**Response:**
```json
{
  "overall_health": "healthy",
  "api_metrics": {
    "requests_per_minute": 45.2,
    "avg_response_time": 234.5,
    "error_rate": 0.002,
    "cache_hit_rate": 0.84
  },
  "data_metrics": {
    "freshness_score": 0.92,
    "completeness_score": 0.88,
    "consistency_score": 0.95
  },
  "resource_usage": {
    "cpu_usage": 0.34,
    "memory_usage": 0.67,
    "disk_usage": 0.45
  }
}
```

## 6. Caching Strategy

### 6.1 Cache Layers

1. **L1 Cache (Memory)**: In-process caching for frequently accessed data
2. **L2 Cache (Redis)**: Distributed caching for computed analytics
3. **L3 Cache (Database)**: Pre-computed aggregate tables

### 6.2 Cache Keys and TTL

```python
CACHE_STRATEGIES = {
    "overview_metrics": {"ttl": 300, "key": "analytics:overview:{period}"},
    "network_analysis": {"ttl": 1800, "key": "analytics:network:{params_hash}"},
    "task_performance": {"ttl": 600, "key": "analytics:tasks:{timeframe}"},
    "system_health": {"ttl": 60, "key": "analytics:health"},
    "entity_counts": {"ttl": 900, "key": "analytics:entities:{type}"}
}
```

### 6.3 Cache Invalidation

- **Time-based**: Automatic TTL expiration
- **Event-based**: Invalidation on data updates
- **Manual**: Force refresh via API parameter

## 7. Performance Optimizations

### 7.1 Query Optimization

- **Parallel Processing**: Concurrent data loading from multiple sources
- **Lazy Loading**: Load data only when needed for specific metrics
- **Batch Processing**: Group similar computations together
- **Index Usage**: Leverage database indexes for fast filtering

### 7.2 Memory Management

- **Streaming Processing**: Process large datasets in chunks
- **Memory Pools**: Reuse allocated memory for computations
- **Garbage Collection**: Explicit cleanup of temporary objects
- **Data Compression**: Compress cached results to save memory

### 7.3 Scalability Features

- **Horizontal Scaling**: Support multiple analytics worker instances
- **Load Balancing**: Distribute analytics requests across workers
- **Background Jobs**: Offload expensive computations to background tasks
- **Result Pagination**: Paginate large result sets

## 8. Security and Authentication

### 8.1 Authentication Requirements

- **API Key Authentication**: Required for all analytics endpoints
- **Scope-based Access**: Different analytics scopes (read, admin)
- **Rate Limiting**: Configurable rate limits per API key
- **Audit Logging**: Log all analytics API access

### 8.2 Data Privacy

- **Data Anonymization**: Option to anonymize sensitive data in analytics
- **Access Controls**: Restrict access to sensitive analytics
- **Data Retention**: Configurable retention for analytics results
- **Encryption**: Encrypt sensitive analytics data at rest

## 9. Testing Strategy

### 9.1 Unit Tests

- **Metrics Calculator**: Test all metric calculations with known data
- **Network Analyzer**: Validate graph algorithms with test networks
- **Trend Analyzer**: Test time series analysis with synthetic data
- **Cache Manager**: Test caching behavior and invalidation

### 9.2 Integration Tests

- **API Endpoints**: Test all endpoint responses and error handling
- **Data Pipeline**: Test end-to-end analytics pipeline
- **Performance**: Load testing with realistic data volumes
- **Authentication**: Test security and access controls

### 9.3 Performance Tests

- **Response Time**: Measure response times under load
- **Concurrency**: Test concurrent analytics requests
- **Memory Usage**: Monitor memory consumption during analytics
- **Cache Performance**: Measure cache hit rates and effectiveness

## 10. Monitoring and Observability

### 10.1 Metrics to Track

- **Request Metrics**: Request count, response time, error rate
- **Computation Metrics**: Analytics computation time, cache hit rate
- **Resource Metrics**: CPU usage, memory usage, network I/O
- **Business Metrics**: Most requested analytics, user adoption

### 10.2 Alerting

- **Performance Alerts**: Response time thresholds, error rate spikes
- **Resource Alerts**: High CPU/memory usage, disk space
- **Business Alerts**: Anomalies in key business metrics
- **Health Alerts**: System health degradation

### 10.3 Dashboards

- **Technical Dashboard**: API performance, system health, resource usage
- **Business Dashboard**: Analytics usage, popular metrics, trends
- **Operational Dashboard**: Real-time monitoring, alert status

This technical specification provides the foundation for building a comprehensive, scalable, and secure Analytics API that transforms BlackCore into a powerful intelligence analytics platform.