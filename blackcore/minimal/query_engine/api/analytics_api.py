"""Analytics API endpoints for the Query Engine."""

from fastapi import APIRouter, HTTPException, Depends, Query as QueryParam
from typing import List, Optional, Dict, Any
import logging
import time
from datetime import datetime, timedelta

from ..analytics import (
    AnalyticsEngine, AnalyticsRequest, NetworkAnalysisRequest, TimelineRequest,
    TaskAnalyticsRequest, InsightsRequest, OverviewResponse, NetworkAnalysisResponse,
    TimelineResponse, TaskAnalyticsResponse, IntelligenceInsightsResponse,
    SystemHealthResponse, TimeGranularity, NetworkAlgorithm
)
from .auth import get_current_api_key

logger = logging.getLogger(__name__)

# Create analytics router
router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Global analytics engine instance
_analytics_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine(
            data_dir="blackcore/models/json",
            enable_caching=True
        )
    return _analytics_engine


async def verify_api_access(api_key: str = Depends(get_current_api_key)):
    """Verify API access for analytics endpoints."""
    # Additional analytics-specific access checks can be added here
    return api_key


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="Dashboard Overview",
    description="Get comprehensive dashboard overview with key metrics and trends"
)
async def get_overview(
    period: str = QueryParam("30d", description="Time period (7d, 30d, 90d, 1y)"),
    refresh: bool = QueryParam(False, description="Force cache refresh"),
    databases: Optional[List[str]] = QueryParam(None, description="Specific databases to analyze"),
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Get dashboard overview analytics including entity counts, recent activity, 
    top metrics, health indicators, and trends."""
    try:
        # Parse period parameter
        period_mapping = {
            "7d": 7, "30d": 30, "90d": 90, "1y": 365
        }
        days = period_mapping.get(period, 30)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build analytics request
        request = AnalyticsRequest(
            start_date=start_date,
            end_date=end_date,
            databases=databases,
            refresh_cache=refresh
        )
        
        # Execute analytics
        result = await analytics_engine.generate_overview(request)
        
        logger.info(f"Overview analytics completed in {result.execution_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error generating overview analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/entities/network",
    response_model=NetworkAnalysisResponse,
    summary="Network Analysis",
    description="Analyze entity relationship networks with various algorithms"
)
async def get_network_analysis(
    entity_type: Optional[str] = QueryParam(None, description="Focus on specific entity type"),
    max_depth: int = QueryParam(3, ge=1, le=5, description="Maximum relationship depth"),
    algorithm: NetworkAlgorithm = QueryParam(NetworkAlgorithm.CENTRALITY, description="Analysis algorithm"),
    min_connections: int = QueryParam(2, ge=1, description="Minimum connections threshold"),
    focus_entity: Optional[str] = QueryParam(None, description="Focus analysis on specific entity"),
    databases: Optional[List[str]] = QueryParam(None, description="Specific databases to analyze"),
    refresh: bool = QueryParam(False, description="Force cache refresh"),
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Analyze entity relationship networks using graph algorithms including centrality 
    analysis, community detection, influence mapping, and clustering."""
    try:
        # Build network analysis request
        request = NetworkAnalysisRequest(
            databases=databases,
            entity_types=[entity_type] if entity_type else None,
            refresh_cache=refresh,
            max_depth=max_depth,
            min_connections=min_connections,
            algorithm=algorithm,
            focus_entity=focus_entity
        )
        
        # Execute network analysis
        result = await analytics_engine.analyze_network(request)
        
        logger.info(f"Network analysis completed in {result.execution_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error performing network analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/activities/timeline",
    response_model=TimelineResponse,
    summary="Activity Timeline",
    description="Generate activity timeline with trends and forecasting"
)
async def get_activity_timeline(
    start_date: Optional[datetime] = QueryParam(None, description="Analysis start date"),
    end_date: Optional[datetime] = QueryParam(None, description="Analysis end date"),
    granularity: TimeGranularity = QueryParam(TimeGranularity.DAILY, description="Time granularity"),
    metrics: List[str] = QueryParam(["entity_count", "task_completion"], description="Metrics to track"),
    include_forecasting: bool = QueryParam(False, description="Include trend forecasting"),
    forecast_periods: int = QueryParam(30, ge=7, le=90, description="Forecast periods"),
    databases: Optional[List[str]] = QueryParam(None, description="Specific databases to analyze"),
    refresh: bool = QueryParam(False, description="Force cache refresh"),
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Generate activity timeline showing trends over time with optional forecasting.
    Supports multiple time granularities and customizable metrics."""
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Build timeline request
        request = TimelineRequest(
            start_date=start_date,
            end_date=end_date,
            databases=databases,
            refresh_cache=refresh,
            granularity=granularity,
            metrics=metrics,
            include_forecasting=include_forecasting,
            forecast_periods=forecast_periods
        )
        
        # Execute timeline analysis
        result = await analytics_engine.generate_timeline(request)
        
        logger.info(f"Timeline analysis completed in {result.execution_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error generating timeline analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tasks/performance",
    response_model=TaskAnalyticsResponse,
    summary="Task Performance",
    description="Analyze task performance metrics and trends"
)
async def get_task_performance(
    assignee: Optional[str] = QueryParam(None, description="Filter by assignee"),
    priority: Optional[str] = QueryParam(None, description="Filter by priority level"),
    status: Optional[str] = QueryParam(None, description="Filter by task status"),
    start_date: Optional[datetime] = QueryParam(None, description="Analysis start date"),
    end_date: Optional[datetime] = QueryParam(None, description="Analysis end date"),
    include_performance: bool = QueryParam(True, description="Include performance metrics"),
    databases: Optional[List[str]] = QueryParam(None, description="Specific databases to analyze"),
    refresh: bool = QueryParam(False, description="Force cache refresh"),
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Analyze task performance including completion metrics, assignee performance,
    priority analysis, and performance trends."""
    try:
        # Build task analytics request
        request = TaskAnalyticsRequest(
            start_date=start_date,
            end_date=end_date,
            databases=databases,
            refresh_cache=refresh,
            assignee=assignee,
            priority=priority,
            status=status,
            include_performance=include_performance
        )
        
        # Execute task analysis
        result = await analytics_engine.analyze_tasks(request)
        
        logger.info(f"Task analysis completed in {result.execution_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing task performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/intelligence/insights",
    response_model=IntelligenceInsightsResponse,
    summary="Intelligence Insights",
    description="Generate intelligence insights including patterns, anomalies, and correlations"
)
async def get_intelligence_insights(
    insight_types: List[str] = QueryParam(["patterns", "anomalies"], description="Types of insights"),
    confidence_threshold: float = QueryParam(0.7, ge=0.0, le=1.0, description="Minimum confidence level"),
    max_insights: int = QueryParam(10, ge=1, le=50, description="Maximum insights to return"),
    databases: Optional[List[str]] = QueryParam(None, description="Specific databases to analyze"),
    refresh: bool = QueryParam(False, description="Force cache refresh"),
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Generate intelligence insights including pattern detection, anomaly identification,
    and correlation analysis across the knowledge graph."""
    try:
        # Build insights request
        request = InsightsRequest(
            databases=databases,
            refresh_cache=refresh,
            insight_types=insight_types,
            confidence_threshold=confidence_threshold,
            max_insights=max_insights
        )
        
        # Execute insights analysis
        result = await analytics_engine.generate_insights(request)
        
        logger.info(f"Insights analysis completed in {result.execution_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error generating intelligence insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/system/health",
    response_model=SystemHealthResponse,
    summary="System Health",
    description="Get comprehensive system health metrics and status"
)
async def get_system_health(
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Get comprehensive system health metrics including API performance,
    data quality, resource usage, and overall system status."""
    try:
        # Execute system health check
        result = await analytics_engine.get_system_health()
        
        logger.info(f"System health check completed in {result.execution_time_ms:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/databases",
    response_model=List[str],
    summary="Available Databases",
    description="List all databases available for analytics"
)
async def list_analytics_databases(
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """List all databases available for analytics processing."""
    try:
        databases = analytics_engine.get_available_databases()
        return databases
        
    except Exception as e:
        logger.error(f"Error listing analytics databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cache/invalidate",
    summary="Invalidate Cache",
    description="Invalidate analytics cache entries"
)
async def invalidate_analytics_cache(
    pattern: Optional[str] = None,
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Invalidate analytics cache entries. If pattern is provided, only matching 
    entries are invalidated. Otherwise, all cache is cleared."""
    try:
        if analytics_engine.cache_manager:
            await analytics_engine.cache_manager.invalidate_cache(pattern)
            message = f"Cache invalidated" + (f" (pattern: {pattern})" if pattern else " (all entries)")
        else:
            message = "Caching is disabled"
        
        return {"message": message, "timestamp": datetime.utcnow()}
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cache/stats",
    summary="Cache Statistics",
    description="Get analytics cache performance statistics"
)
async def get_cache_stats(
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Get detailed analytics cache performance statistics including hit rates,
    cache size, and performance metrics."""
    try:
        if analytics_engine.cache_manager:
            stats = analytics_engine.cache_manager.get_cache_stats()
            health = analytics_engine.cache_manager.get_cache_health()
            
            return {
                "cache_enabled": True,
                "statistics": stats,
                "health": health,
                "timestamp": datetime.utcnow()
            }
        else:
            return {
                "cache_enabled": False,
                "message": "Caching is disabled",
                "timestamp": datetime.utcnow()
            }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional utility endpoints

@router.get(
    "/metrics/available",
    summary="Available Metrics",
    description="List all available analytics metrics"
)
async def list_available_metrics(
    api_key: str = Depends(verify_api_access)
):
    """List all available analytics metrics that can be tracked in timeline analysis."""
    return {
        "timeline_metrics": [
            "entity_count",
            "task_completion", 
            "activity_level",
            "document_processing",
            "relationship_creation"
        ],
        "insight_types": [
            "patterns",
            "anomalies", 
            "correlations",
            "trends"
        ],
        "network_algorithms": [
            "centrality",
            "community",
            "influence", 
            "clustering"
        ],
        "time_granularities": [
            "hourly",
            "daily",
            "weekly",
            "monthly"
        ]
    }


@router.get(
    "/export/csv",
    summary="Export Analytics Data",
    description="Export analytics data in CSV format"
)
async def export_analytics_csv(
    metric: str = QueryParam(..., description="Metric to export"),
    start_date: Optional[datetime] = QueryParam(None, description="Start date"),
    end_date: Optional[datetime] = QueryParam(None, description="End date"),
    granularity: TimeGranularity = QueryParam(TimeGranularity.DAILY, description="Time granularity"),
    api_key: str = Depends(verify_api_access),
    analytics_engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    """Export analytics data in CSV format for external analysis."""
    try:
        # Set default date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Generate timeline data
        request = TimelineRequest(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            metrics=[metric],
            include_forecasting=False
        )
        
        result = await analytics_engine.generate_timeline(request)
        
        # Convert to CSV format
        csv_lines = ["timestamp," + metric]
        for point in result.timeline:
            timestamp = point.timestamp.isoformat()
            value = point.values.get(metric, 0)
            csv_lines.append(f"{timestamp},{value}")
        
        csv_content = "\n".join(csv_lines)
        
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=analytics_{metric}_{start_date.date()}_to_{end_date.date()}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting analytics CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))