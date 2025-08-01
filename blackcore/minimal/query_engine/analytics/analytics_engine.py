"""Core analytics engine for BlackCore intelligence analysis."""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .models import (
    AnalyticsRequest, OverviewResponse, NetworkAnalysisRequest, NetworkAnalysisResponse,
    TimelineRequest, TimelineResponse, TaskAnalyticsRequest, TaskAnalyticsResponse,
    InsightsRequest, IntelligenceInsightsResponse, SystemHealthResponse,
    AnalyticsConfig, HealthStatus, TrendDirection
)
from .metrics_calculator import MetricsCalculator
from .network_analyzer import NetworkAnalyzer
from .trend_analyzer import TrendAnalyzer
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Core analytics engine for intelligence data analysis."""
    
    def __init__(
        self,
        data_dir: str = "blackcore/models/json",
        config: Optional[AnalyticsConfig] = None,
        enable_caching: bool = True
    ):
        """Initialize the analytics engine.
        
        Args:
            data_dir: Directory containing JSON database files
            config: Analytics configuration
            enable_caching: Enable result caching
        """
        self.data_dir = Path(data_dir)
        self.config = config or AnalyticsConfig()
        self.enable_caching = enable_caching
        
        # Initialize components
        self.metrics_calculator = MetricsCalculator()
        self.network_analyzer = NetworkAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.cache_manager = CacheManager() if enable_caching else None
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache for loaded data
        self._data_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        logger.info(f"Analytics engine initialized with data_dir: {data_dir}")
    
    def get_available_databases(self) -> List[str]:
        """Get list of available databases."""
        try:
            databases = []
            for json_file in self.data_dir.glob("*.json"):
                if not json_file.name.startswith('.') and 'backup' not in json_file.name:
                    # Convert filename to database name
                    db_name = json_file.stem.replace('_', ' & ').title()
                    if db_name not in databases:
                        databases.append(db_name)
            return sorted(databases)
        except Exception as e:
            logger.error(f"Error getting available databases: {e}")
            return []
    
    def _load_database(self, database_name: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Load data from a specific database.
        
        Args:
            database_name: Name of the database to load
            force_refresh: Force refresh of cached data
            
        Returns:
            List of entities from the database
        """
        # Check cache first
        if not force_refresh and database_name in self._data_cache:
            cache_time = self._cache_timestamps.get(database_name)
            if cache_time and (datetime.utcnow() - cache_time).seconds < 300:  # 5 min cache
                return self._data_cache[database_name]
        
        try:
            # Convert database name to filename
            filename = database_name.lower().replace(' & ', '_').replace(' ', '_') + '.json'
            file_path = self.data_dir / filename
            
            if not file_path.exists():
                logger.warning(f"Database file not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract entities from the JSON structure
            entities = []
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            # Add metadata
                            item['_database'] = database_name
                            item['_source_key'] = key
                            entities.append(item)
            
            # Cache the data
            self._data_cache[database_name] = entities
            self._cache_timestamps[database_name] = datetime.utcnow()
            
            logger.debug(f"Loaded {len(entities)} entities from {database_name}")
            return entities
            
        except Exception as e:
            logger.error(f"Error loading database {database_name}: {e}")
            return []
    
    def _load_all_data(self, databases: Optional[List[str]] = None, force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """Load data from all or specified databases.
        
        Args:
            databases: Specific databases to load (None for all)
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary mapping database names to entity lists
        """
        if databases is None:
            databases = self.get_available_databases()
        
        all_data = {}
        for db_name in databases:
            all_data[db_name] = self._load_database(db_name, force_refresh)
        
        return all_data
    
    async def generate_overview(self, request: AnalyticsRequest) -> OverviewResponse:
        """Generate dashboard overview analytics.
        
        Args:
            request: Analytics request parameters
            
        Returns:
            Overview response with key metrics
        """
        start_time = datetime.utcnow()
        
        # Check cache first
        if self.cache_manager and not request.refresh_cache:
            cached = await self.cache_manager.get_overview_metrics(request)
            if cached:
                return cached
        
        try:
            # Load data
            all_data = self._load_all_data(request.databases, request.refresh_cache)
            
            # Calculate metrics concurrently
            tasks = [
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self.metrics_calculator.calculate_entity_counts, all_data
                ),
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self.metrics_calculator.calculate_recent_activity, all_data, request.start_date, request.end_date
                ),
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self.metrics_calculator.calculate_health_indicators, all_data
                ),
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self.trend_analyzer.calculate_trends, all_data, request.start_date, request.end_date
                )
            ]
            
            entity_counts, activity, health, trends = await asyncio.gather(*tasks)
            
            # Calculate top metrics
            top_metrics = self.metrics_calculator.calculate_top_metrics(all_data, entity_counts, activity)
            
            # Build response
            response = OverviewResponse(
                total_entities=entity_counts,
                recent_activity=activity,
                top_metrics=top_metrics,
                health_indicators=health,
                trends=trends,
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Cache result
            if self.cache_manager:
                await self.cache_manager.cache_overview_metrics(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating overview: {e}")
            raise
    
    async def analyze_network(self, request: NetworkAnalysisRequest) -> NetworkAnalysisResponse:
        """Analyze entity relationship networks.
        
        Args:
            request: Network analysis request parameters
            
        Returns:
            Network analysis response
        """
        start_time = datetime.utcnow()
        
        # Check cache first
        if self.cache_manager and not request.refresh_cache:
            cached = await self.cache_manager.get_network_analysis(request)
            if cached:
                return cached
        
        try:
            # Load data
            all_data = self._load_all_data(request.databases, request.refresh_cache)
            
            # Perform network analysis
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.network_analyzer.analyze_network,
                all_data,
                request.algorithm,
                request.max_depth,
                request.min_connections,
                request.focus_entity
            )
            
            response = NetworkAnalysisResponse(
                nodes=result['nodes'],
                edges=result['edges'],
                communities=result['communities'],
                metrics=result['metrics'],
                algorithm_used=request.algorithm,
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Cache result
            if self.cache_manager:
                await self.cache_manager.cache_network_analysis(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing network: {e}")
            raise
    
    async def generate_timeline(self, request: TimelineRequest) -> TimelineResponse:
        """Generate activity timeline analytics.
        
        Args:
            request: Timeline request parameters
            
        Returns:
            Timeline response with trends and forecasts
        """
        start_time = datetime.utcnow()
        
        # Check cache first
        if self.cache_manager and not request.refresh_cache:
            cached = await self.cache_manager.get_timeline_analysis(request)
            if cached:
                return cached
        
        try:
            # Load data
            all_data = self._load_all_data(request.databases, request.refresh_cache)
            
            # Generate timeline data
            timeline_data = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.trend_analyzer.generate_timeline,
                all_data,
                request.start_date,
                request.end_date,
                request.granularity,
                request.metrics
            )
            
            # Calculate trends
            trends = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.trend_analyzer.analyze_timeline_trends,
                timeline_data['timeline']
            )
            
            # Generate forecasts if requested
            forecasts = None
            if request.include_forecasting:
                forecasts = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.trend_analyzer.generate_forecasts,
                    timeline_data['timeline'],
                    request.forecast_periods
                )
            
            response = TimelineResponse(
                timeline=timeline_data['timeline'],
                trends=trends,
                forecasts=forecasts,
                granularity=request.granularity,
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Cache result
            if self.cache_manager:
                await self.cache_manager.cache_timeline_analysis(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating timeline: {e}")
            raise
    
    async def analyze_tasks(self, request: TaskAnalyticsRequest) -> TaskAnalyticsResponse:
        """Analyze task performance and metrics.
        
        Args:
            request: Task analytics request parameters
            
        Returns:
            Task analytics response
        """
        start_time = datetime.utcnow()
        
        try:
            # Load task data specifically
            task_databases = ['Actionable Tasks']
            if request.databases:
                task_databases = [db for db in request.databases if 'task' in db.lower()]
            
            all_data = self._load_all_data(task_databases, request.refresh_cache)
            
            # Calculate task metrics
            task_metrics = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.metrics_calculator.calculate_task_metrics,
                all_data,
                request.assignee,
                request.priority,
                request.status,
                request.start_date,
                request.end_date
            )
            
            response = TaskAnalyticsResponse(
                overall_metrics=task_metrics['overall'],
                by_priority=task_metrics['by_priority'],
                by_status=task_metrics['by_status'],
                assignee_performance=task_metrics['assignee_performance'],
                trends=task_metrics['trends'],
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing tasks: {e}")
            raise
    
    async def generate_insights(self, request: InsightsRequest) -> IntelligenceInsightsResponse:
        """Generate intelligence insights and patterns.
        
        Args:
            request: Insights request parameters
            
        Returns:
            Intelligence insights response
        """
        start_time = datetime.utcnow()
        
        try:
            # Load data
            all_data = self._load_all_data(request.databases, request.refresh_cache)
            
            # Generate insights concurrently
            tasks = []
            
            if 'patterns' in request.insight_types:
                tasks.append(
                    asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self.trend_analyzer.detect_patterns,
                        all_data,
                        request.confidence_threshold
                    )
                )
            
            if 'anomalies' in request.insight_types:
                tasks.append(
                    asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self.trend_analyzer.detect_anomalies,
                        all_data,
                        request.confidence_threshold
                    )
                )
            
            if 'correlations' in request.insight_types:
                tasks.append(
                    asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self.metrics_calculator.calculate_correlations,
                        all_data,
                        request.confidence_threshold
                    )
                )
            
            results = await asyncio.gather(*tasks)
            
            # Parse results based on insight types
            patterns = results[0] if 'patterns' in request.insight_types else []
            anomalies = results[1] if 'anomalies' in request.insight_types and len(results) > 1 else []
            correlations = results[2] if 'correlations' in request.insight_types and len(results) > 2 else []
            
            # Generate executive summary
            summary = self._generate_insights_summary(patterns, anomalies, correlations)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(patterns, anomalies, correlations)
            
            response = IntelligenceInsightsResponse(
                patterns=patterns[:request.max_insights],
                anomalies=anomalies[:request.max_insights],
                correlations=correlations[:request.max_insights],
                summary=summary,
                confidence=overall_confidence,
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            raise
    
    async def get_system_health(self) -> SystemHealthResponse:
        """Get comprehensive system health metrics.
        
        Returns:
            System health response
        """
        start_time = datetime.utcnow()
        
        try:
            # Calculate system health metrics
            health_data = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.metrics_calculator.calculate_system_health,
                self._data_cache,
                self.cache_manager
            )
            
            response = SystemHealthResponse(
                overall_health=health_data['overall_health'],
                api_metrics=health_data['api_metrics'],
                data_metrics=health_data['data_metrics'],
                resource_usage=health_data['resource_usage'],
                uptime_seconds=health_data['uptime_seconds'],
                last_error=health_data.get('last_error'),
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            raise
    
    def _generate_insights_summary(self, patterns: List, anomalies: List, correlations: List) -> str:
        """Generate executive summary of insights."""
        summary_parts = []
        
        if patterns:
            summary_parts.append(f"Detected {len(patterns)} significant patterns")
        
        if anomalies:
            critical_anomalies = len([a for a in anomalies if a.severity == 'critical'])
            if critical_anomalies:
                summary_parts.append(f"{critical_anomalies} critical anomalies require attention")
            else:
                summary_parts.append(f"Found {len(anomalies)} anomalies")
        
        if correlations:
            strong_correlations = len([c for c in correlations if abs(c.correlation) > 0.7])
            summary_parts.append(f"Identified {strong_correlations} strong correlations")
        
        if not summary_parts:
            return "No significant insights detected in the current analysis."
        
        return ". ".join(summary_parts) + "."
    
    def _calculate_overall_confidence(self, patterns: List, anomalies: List, correlations: List) -> float:
        """Calculate overall confidence in insights."""
        confidences = []
        
        for pattern in patterns:
            confidences.append(pattern.confidence)
        
        for anomaly in anomalies:
            # Convert severity to confidence-like score
            severity_scores = {'low': 0.6, 'medium': 0.8, 'high': 0.9, 'critical': 0.95}
            confidences.append(severity_scores.get(anomaly.severity, 0.7))
        
        for correlation in correlations:
            # Use p-value to determine confidence
            confidences.append(1.0 - correlation.p_value)
        
        if not confidences:
            return 0.0
        
        return sum(confidences) / len(confidences)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
        
        if self.cache_manager:
            await self.cache_manager.cleanup()
        
        logger.info("Analytics engine cleaned up")