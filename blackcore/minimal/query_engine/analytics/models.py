"""Data models for the Analytics API."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class NetworkAlgorithm(str, Enum):
    """Network analysis algorithms."""
    CENTRALITY = "centrality"
    COMMUNITY = "community"
    INFLUENCE = "influence"
    CLUSTERING = "clustering"


class TimeGranularity(str, Enum):
    """Time analysis granularity."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MetricType(str, Enum):
    """Types of metrics."""
    COUNT = "count"
    RATE = "rate"
    PERCENTAGE = "percentage"
    DISTRIBUTION = "distribution"


class TrendDirection(str, Enum):
    """Trend directions."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class HealthStatus(str, Enum):
    """System health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# Request Models
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
    focus_entity: Optional[str] = Field(None, description="Focus analysis on specific entity")


class TimelineRequest(AnalyticsRequest):
    """Timeline analysis parameters."""
    
    granularity: TimeGranularity = Field(TimeGranularity.DAILY, description="Time granularity")
    metrics: List[str] = Field(..., description="Metrics to track over time")
    include_forecasting: bool = Field(False, description="Include trend forecasting")
    forecast_periods: int = Field(30, ge=1, le=90, description="Number of periods to forecast")


class TaskAnalyticsRequest(AnalyticsRequest):
    """Task analytics parameters."""
    
    assignee: Optional[str] = Field(None, description="Filter by assignee")
    priority: Optional[str] = Field(None, description="Filter by priority level")
    status: Optional[str] = Field(None, description="Filter by task status")
    include_performance: bool = Field(True, description="Include performance metrics")


class InsightsRequest(AnalyticsRequest):
    """Intelligence insights parameters."""
    
    insight_types: List[str] = Field(["patterns", "anomalies"], description="Types of insights")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence level")
    max_insights: int = Field(10, ge=1, le=50, description="Maximum insights to return")


# Response Models
class TrendIndicator(BaseModel):
    """Trend analysis indicator."""
    
    direction: TrendDirection
    rate: float = Field(..., description="Rate of change")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in trend")
    significance: bool = Field(..., description="Statistical significance")


class ActivitySummary(BaseModel):
    """Recent activity summary."""
    
    last_24h: int = Field(..., description="Activity in last 24 hours")
    last_7d: int = Field(..., description="Activity in last 7 days")
    last_30d: int = Field(..., description="Activity in last 30 days")
    trend: TrendDirection = Field(..., description="Overall trend direction")


class HealthIndicators(BaseModel):
    """System health indicators."""
    
    system_health: HealthStatus
    data_quality: float = Field(..., ge=0.0, le=1.0, description="Data quality score")
    api_performance: HealthStatus
    uptime: float = Field(..., description="System uptime in hours")


class OverviewResponse(BaseModel):
    """Dashboard overview response."""
    
    total_entities: Dict[str, int] = Field(..., description="Entity counts by type")
    recent_activity: ActivitySummary
    top_metrics: Dict[str, float] = Field(..., description="Key performance indicators")
    health_indicators: HealthIndicators
    trends: Dict[str, TrendIndicator] = Field(..., description="Trend analysis")
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NetworkNode(BaseModel):
    """Network graph node."""
    
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    centrality_score: float = Field(..., ge=0.0, le=1.0, description="Centrality score")
    connections: int = Field(..., ge=0, description="Number of connections")
    community: Optional[str] = Field(None, description="Community assignment")


class NetworkEdge(BaseModel):
    """Network graph edge."""
    
    source: str
    target: str
    relationship: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Relationship weight")
    properties: Dict[str, Any] = Field(default_factory=dict)


class Community(BaseModel):
    """Network community."""
    
    id: str
    label: str
    members: List[str] = Field(..., description="Community member IDs")
    size: int = Field(..., ge=0, description="Community size")
    modularity: float = Field(..., description="Community modularity score")
    center_node: Optional[str] = Field(None, description="Community center node")


class NetworkMetrics(BaseModel):
    """Network analysis metrics."""
    
    total_nodes: int = Field(..., ge=0)
    total_edges: int = Field(..., ge=0)
    density: float = Field(..., ge=0.0, le=1.0, description="Network density")
    avg_clustering: float = Field(..., ge=0.0, le=1.0, description="Average clustering coefficient")
    diameter: Optional[int] = Field(None, description="Network diameter")
    communities_count: int = Field(..., ge=0, description="Number of communities")


class NetworkAnalysisResponse(BaseModel):
    """Network analysis results."""
    
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    communities: List[Community]
    metrics: NetworkMetrics
    algorithm_used: NetworkAlgorithm
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    
    timestamp: datetime
    values: Dict[str, float] = Field(..., description="Metric values at this timestamp")


class ForecastPoint(BaseModel):
    """Forecast data point."""
    
    timestamp: datetime
    predicted_value: float
    confidence_interval: Optional[Dict[str, float]] = Field(None, description="Lower/upper bounds")


class TimelineResponse(BaseModel):
    """Activity timeline response."""
    
    timeline: List[TimeSeriesPoint]
    trends: Dict[str, TrendIndicator]
    forecasts: Optional[Dict[str, List[ForecastPoint]]] = Field(None, description="Forecast data")
    granularity: TimeGranularity
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskMetrics(BaseModel):
    """Task performance metrics."""
    
    total_tasks: int = Field(..., ge=0)
    completed: int = Field(..., ge=0)
    in_progress: int = Field(..., ge=0)
    overdue: int = Field(..., ge=0)
    completion_rate: float = Field(..., ge=0.0, le=1.0, description="Task completion rate")
    avg_completion_time: Optional[float] = Field(None, description="Average completion time in days")


class AssigneePerformance(BaseModel):
    """Individual assignee performance."""
    
    assignee: str
    assigned: int = Field(..., ge=0)
    completed: int = Field(..., ge=0)
    completion_rate: float = Field(..., ge=0.0, le=1.0)
    avg_completion_time: Optional[float] = Field(None, description="Average time in days")
    current_workload: int = Field(..., ge=0, description="Current active tasks")


class TaskAnalyticsResponse(BaseModel):
    """Task analytics response."""
    
    overall_metrics: TaskMetrics
    by_priority: Dict[str, TaskMetrics] = Field(..., description="Metrics by priority level")
    by_status: Dict[str, int] = Field(..., description="Task counts by status")
    assignee_performance: List[AssigneePerformance] = Field(..., description="Performance by assignee")
    trends: Dict[str, TrendIndicator] = Field(..., description="Task performance trends")
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Pattern(BaseModel):
    """Detected pattern."""
    
    type: str = Field(..., description="Pattern type")
    description: str = Field(..., description="Human-readable description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    supporting_data: Dict[str, Any] = Field(..., description="Supporting statistical data")
    entities: List[str] = Field(default_factory=list, description="Related entities")


class Anomaly(BaseModel):
    """Detected anomaly."""
    
    type: str = Field(..., description="Anomaly type")
    description: str = Field(..., description="Human-readable description")
    timestamp: datetime = Field(..., description="When anomaly occurred")
    severity: str = Field(..., description="Severity level")
    details: Dict[str, Any] = Field(..., description="Anomaly details")
    affected_entities: List[str] = Field(default_factory=list, description="Affected entities")


class Correlation(BaseModel):
    """Statistical correlation."""
    
    entities: List[str] = Field(..., description="Correlated entities/metrics")
    correlation: float = Field(..., ge=-1.0, le=1.0, description="Correlation coefficient")
    p_value: float = Field(..., ge=0.0, le=1.0, description="Statistical significance")
    relationship: str = Field(..., description="Relationship type")
    strength: str = Field(..., description="Correlation strength description")


class IntelligenceInsightsResponse(BaseModel):
    """Intelligence insights response."""
    
    patterns: List[Pattern] = Field(..., description="Detected patterns")
    anomalies: List[Anomaly] = Field(..., description="Detected anomalies")
    correlations: List[Correlation] = Field(..., description="Statistical correlations")
    summary: str = Field(..., description="Executive summary of insights")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIMetrics(BaseModel):
    """API performance metrics."""
    
    requests_per_minute: float = Field(..., ge=0.0)
    avg_response_time: float = Field(..., ge=0.0, description="Average response time in ms")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Error rate percentage")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    active_connections: int = Field(..., ge=0)


class DataMetrics(BaseModel):
    """Data quality metrics."""
    
    freshness_score: float = Field(..., ge=0.0, le=1.0, description="Data freshness score")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Data completeness score")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Data consistency score")
    total_records: int = Field(..., ge=0)
    last_updated: datetime


class ResourceUsage(BaseModel):
    """System resource usage."""
    
    cpu_usage: float = Field(..., ge=0.0, le=1.0, description="CPU usage percentage")
    memory_usage: float = Field(..., ge=0.0, le=1.0, description="Memory usage percentage")
    disk_usage: float = Field(..., ge=0.0, le=1.0, description="Disk usage percentage")
    network_io: Optional[Dict[str, float]] = Field(None, description="Network I/O statistics")


class SystemHealthResponse(BaseModel):
    """System health response."""
    
    overall_health: HealthStatus
    api_metrics: APIMetrics
    data_metrics: DataMetrics
    resource_usage: ResourceUsage
    uptime_seconds: float = Field(..., ge=0.0)
    last_error: Optional[str] = Field(None, description="Last error message")
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Analytics Configuration
class AnalyticsConfig(BaseModel):
    """Analytics engine configuration."""
    
    cache_ttl_seconds: int = Field(300, ge=60, description="Default cache TTL")
    max_network_nodes: int = Field(1000, ge=100, description="Maximum nodes in network analysis")
    max_timeline_points: int = Field(365, ge=30, description="Maximum timeline data points")
    default_forecast_periods: int = Field(30, ge=7, description="Default forecast periods")
    anomaly_threshold: float = Field(2.0, ge=1.0, description="Anomaly detection threshold")
    confidence_threshold: float = Field(0.7, ge=0.5, le=1.0, description="Default confidence threshold")


# Cache Models
class CacheKey(BaseModel):
    """Analytics cache key."""
    
    endpoint: str
    parameters: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def generate_key(self) -> str:
        """Generate cache key string."""
        import hashlib
        import json
        
        data = {
            "endpoint": self.endpoint,
            "parameters": self.parameters
        }
        
        key_string = json.dumps(data, sort_keys=True)
        hash_object = hashlib.md5(key_string.encode())
        return f"analytics:{self.endpoint}:{hash_object.hexdigest()}"


class CacheEntry(BaseModel):
    """Analytics cache entry."""
    
    key: str
    data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = Field(300, ge=60)
    access_count: int = Field(0, ge=0)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        from datetime import timedelta
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time