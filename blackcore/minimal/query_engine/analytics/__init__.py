"""Analytics module for BlackCore intelligence analysis."""

from .analytics_engine import AnalyticsEngine
from .metrics_calculator import MetricsCalculator
from .network_analyzer import NetworkAnalyzer
from .trend_analyzer import TrendAnalyzer
from .cache_manager import CacheManager
from .models import (
    # Enums
    NetworkAlgorithm,
    TimeGranularity,
    MetricType,
    TrendDirection,
    HealthStatus,
    
    # Request Models
    AnalyticsRequest,
    NetworkAnalysisRequest,
    TimelineRequest,
    TaskAnalyticsRequest,
    InsightsRequest,
    
    # Response Models
    OverviewResponse,
    NetworkAnalysisResponse,
    TimelineResponse,
    TaskAnalyticsResponse,
    IntelligenceInsightsResponse,
    SystemHealthResponse,
    
    # Data Models
    NetworkNode,
    NetworkEdge,
    Community,
    NetworkMetrics,
    TimeSeriesPoint,
    ForecastPoint,
    Pattern,
    Anomaly,
    Correlation,
    TrendIndicator,
    ActivitySummary,
    HealthIndicators,
    
    # Configuration
    AnalyticsConfig,
    CacheKey,
    CacheEntry
)

__all__ = [
    # Core Classes
    'AnalyticsEngine',
    'MetricsCalculator',
    'NetworkAnalyzer', 
    'TrendAnalyzer',
    'CacheManager',
    
    # Enums
    'NetworkAlgorithm',
    'TimeGranularity',
    'MetricType',
    'TrendDirection',
    'HealthStatus',
    
    # Request Models
    'AnalyticsRequest',
    'NetworkAnalysisRequest',
    'TimelineRequest',
    'TaskAnalyticsRequest',
    'InsightsRequest',
    
    # Response Models
    'OverviewResponse',
    'NetworkAnalysisResponse',
    'TimelineResponse',
    'TaskAnalyticsResponse',
    'IntelligenceInsightsResponse',
    'SystemHealthResponse',
    
    # Data Models
    'NetworkNode',
    'NetworkEdge',
    'Community',
    'NetworkMetrics',
    'TimeSeriesPoint',
    'ForecastPoint',
    'Pattern',
    'Anomaly',
    'Correlation',
    'TrendIndicator',
    'ActivitySummary',
    'HealthIndicators',
    
    # Configuration
    'AnalyticsConfig',
    'CacheKey',
    'CacheEntry'
]

# Version info
__version__ = '1.0.0'
__author__ = 'BlackCore Intelligence Team'
__description__ = 'Advanced analytics engine for intelligence data analysis'