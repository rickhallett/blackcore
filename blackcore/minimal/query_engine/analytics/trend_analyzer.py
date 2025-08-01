"""Time series analysis and trend detection for analytics."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics
import math

from .models import (
    TrendDirection, TrendIndicator, TimeGranularity, TimeSeriesPoint, 
    ForecastPoint, Pattern, Anomaly
)

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends, patterns, and forecasts in time series data."""
    
    def __init__(self):
        """Initialize the trend analyzer."""
        logger.debug("TrendAnalyzer initialized")
    
    def calculate_trends(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, TrendIndicator]:
        """Calculate trend indicators for various metrics.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary mapping metric names to trend indicators
        """
        try:
            trends = {}
            
            # Entity creation trends
            entity_trend = self._calculate_entity_creation_trend(all_data, start_date, end_date)
            if entity_trend:
                trends['entity_creation'] = entity_trend
            
            # Task completion trends
            task_trend = self._calculate_task_completion_trend(all_data, start_date, end_date)
            if task_trend:
                trends['task_completion'] = task_trend
            
            # Activity trends
            activity_trend = self._calculate_activity_trend(all_data, start_date, end_date)
            if activity_trend:
                trends['activity_level'] = activity_trend
            
            return trends
            
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return {}
    
    def generate_timeline(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.DAILY,
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Generate timeline data for specified metrics.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            start_date: Start date for timeline
            end_date: End date for timeline
            granularity: Time granularity
            metrics: Specific metrics to track
            
        Returns:
            Dictionary with timeline data
        """
        try:
            # Set default date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Default metrics
            if not metrics:
                metrics = ['entity_count', 'task_completion', 'activity_level']
            
            # Generate time buckets
            time_buckets = self._generate_time_buckets(start_date, end_date, granularity)
            
            # Initialize timeline data
            timeline = []
            
            for bucket_start, bucket_end in time_buckets:
                bucket_data = {
                    'timestamp': bucket_start,
                    'values': {}
                }
                
                # Calculate metrics for this time bucket
                for metric in metrics:
                    value = self._calculate_metric_for_period(
                        all_data, metric, bucket_start, bucket_end
                    )
                    bucket_data['values'][metric] = value
                
                timeline.append(TimeSeriesPoint(**bucket_data))
            
            return {'timeline': timeline}
            
        except Exception as e:
            logger.error(f"Error generating timeline: {e}")
            return {'timeline': []}
    
    def analyze_timeline_trends(self, timeline: List[TimeSeriesPoint]) -> Dict[str, TrendIndicator]:
        """Analyze trends in timeline data.
        
        Args:
            timeline: List of time series points
            
        Returns:
            Dictionary mapping metrics to trend indicators
        """
        try:
            trends = {}
            
            if not timeline:
                return trends
            
            # Get all metrics from timeline
            all_metrics = set()
            for point in timeline:
                all_metrics.update(point.values.keys())
            
            # Analyze trend for each metric
            for metric in all_metrics:
                values = []
                for point in timeline:
                    if metric in point.values:
                        values.append(point.values[metric])
                
                if len(values) >= 3:  # Need at least 3 points for trend
                    trend = self._analyze_metric_trend(values)
                    trends[metric] = trend
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing timeline trends: {e}")
            return {}
    
    def generate_forecasts(
        self,
        timeline: List[TimeSeriesPoint],
        forecast_periods: int = 30
    ) -> Dict[str, List[ForecastPoint]]:
        """Generate simple forecasts based on timeline data.
        
        Args:
            timeline: Historical timeline data
            forecast_periods: Number of periods to forecast
            
        Returns:
            Dictionary mapping metrics to forecast points
        """
        try:
            forecasts = {}
            
            if not timeline or len(timeline) < 2:
                return forecasts
            
            # Get time interval
            time_interval = timeline[1].timestamp - timeline[0].timestamp
            
            # Get all metrics
            all_metrics = set()
            for point in timeline:
                all_metrics.update(point.values.keys())
            
            # Generate forecasts for each metric
            for metric in all_metrics:
                values = []
                for point in timeline:
                    if metric in point.values:
                        values.append(point.values[metric])
                
                if len(values) >= 2:
                    forecast_points = self._generate_metric_forecast(
                        values, timeline[-1].timestamp, time_interval, forecast_periods
                    )
                    forecasts[metric] = forecast_points
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Error generating forecasts: {e}")
            return {}
    
    def detect_patterns(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        confidence_threshold: float = 0.7
    ) -> List[Pattern]:
        """Detect patterns in the data.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            confidence_threshold: Minimum confidence level
            
        Returns:
            List of detected patterns
        """
        try:
            patterns = []
            
            # Temporal patterns
            temporal_patterns = self._detect_temporal_patterns(all_data)
            patterns.extend(temporal_patterns)
            
            # Status patterns
            status_patterns = self._detect_status_patterns(all_data)
            patterns.extend(status_patterns)
            
            # Relationship patterns
            relationship_patterns = self._detect_relationship_patterns(all_data)
            patterns.extend(relationship_patterns)
            
            # Filter by confidence threshold
            filtered_patterns = [p for p in patterns if p.confidence >= confidence_threshold]
            
            return filtered_patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return []
    
    def detect_anomalies(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        confidence_threshold: float = 0.7
    ) -> List[Anomaly]:
        """Detect anomalies in the data.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            confidence_threshold: Minimum confidence level
            
        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            
            # Volume anomalies
            volume_anomalies = self._detect_volume_anomalies(all_data)
            anomalies.extend(volume_anomalies)
            
            # Status anomalies
            status_anomalies = self._detect_status_anomalies(all_data)
            anomalies.extend(status_anomalies)
            
            # Temporal anomalies
            temporal_anomalies = self._detect_temporal_anomalies(all_data)
            anomalies.extend(temporal_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def _calculate_entity_creation_trend(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[TrendIndicator]:
        """Calculate trend in entity creation."""
        try:
            # Get creation timestamps
            creation_dates = []
            
            for db_name, entities in all_data.items():
                for entity in entities:
                    for field in ['created_time', 'Created', 'Date']:
                        if field in entity:
                            try:
                                if isinstance(entity[field], str):
                                    date = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                    creation_dates.append(date)
                                    break
                            except (ValueError, TypeError):
                                continue
            
            if len(creation_dates) < 5:
                return None
            
            # Sort dates
            creation_dates.sort()
            
            # Calculate weekly creation rates
            now = datetime.utcnow()
            weeks = []
            for i in range(4):  # Last 4 weeks
                week_start = now - timedelta(weeks=i+1)
                week_end = now - timedelta(weeks=i)
                week_count = sum(1 for date in creation_dates if week_start <= date < week_end)
                weeks.append(week_count)
            
            weeks.reverse()  # Oldest to newest
            
            if len(weeks) >= 2:
                # Calculate trend
                direction, rate, confidence = self._calculate_linear_trend(weeks)
                return TrendIndicator(
                    direction=direction,
                    rate=rate,
                    confidence=confidence,
                    significance=confidence > 0.5
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating entity creation trend: {e}")
            return None
    
    def _calculate_task_completion_trend(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[TrendIndicator]:
        """Calculate trend in task completion."""
        try:
            tasks = all_data.get('Actionable Tasks', [])
            if not tasks:
                return None
            
            # Calculate completion rates for recent periods
            now = datetime.utcnow()
            completion_rates = []
            
            for i in range(4):  # Last 4 weeks
                week_start = now - timedelta(weeks=i+1)
                week_end = now - timedelta(weeks=i)
                
                week_tasks = []
                for task in tasks:
                    # Try to find task creation/update date
                    task_date = None
                    for field in ['created_time', 'last_edited_time', 'Due Date']:
                        if field in task:
                            try:
                                if isinstance(task[field], str):
                                    task_date = datetime.fromisoformat(task[field].replace('Z', '+00:00'))
                                    break
                            except (ValueError, TypeError):
                                continue
                    
                    if task_date and week_start <= task_date < week_end:
                        week_tasks.append(task)
                
                if week_tasks:
                    completed = sum(1 for task in week_tasks 
                                  if task.get('Status', '').lower() in ['done', 'completed'])
                    rate = completed / len(week_tasks)
                    completion_rates.append(rate)
                else:
                    completion_rates.append(0.0)
            
            completion_rates.reverse()  # Oldest to newest
            
            if len(completion_rates) >= 2:
                direction, rate, confidence = self._calculate_linear_trend(completion_rates)
                return TrendIndicator(
                    direction=direction,
                    rate=rate,
                    confidence=confidence,
                    significance=confidence > 0.5
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating task completion trend: {e}")
            return None
    
    def _calculate_activity_trend(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[TrendIndicator]:
        """Calculate overall activity trend."""
        try:
            # Count activities by week
            now = datetime.utcnow()
            weekly_activities = []
            
            for i in range(4):  # Last 4 weeks
                week_start = now - timedelta(weeks=i+1)
                week_end = now - timedelta(weeks=i)
                
                week_activity = 0
                for db_name, entities in all_data.items():
                    for entity in entities:
                        # Check for any activity in this period
                        for field in ['last_edited_time', 'created_time', 'Last Modified']:
                            if field in entity:
                                try:
                                    if isinstance(entity[field], str):
                                        date = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                        if week_start <= date < week_end:
                                            week_activity += 1
                                            break
                                except (ValueError, TypeError):
                                    continue
                
                weekly_activities.append(week_activity)
            
            weekly_activities.reverse()  # Oldest to newest
            
            if len(weekly_activities) >= 2:
                direction, rate, confidence = self._calculate_linear_trend(weekly_activities)
                return TrendIndicator(
                    direction=direction,
                    rate=rate,
                    confidence=confidence,
                    significance=confidence > 0.5
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating activity trend: {e}")
            return None
    
    def _generate_time_buckets(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity
    ) -> List[Tuple[datetime, datetime]]:
        """Generate time buckets for timeline analysis."""
        buckets = []
        current = start_date
        
        if granularity == TimeGranularity.HOURLY:
            delta = timedelta(hours=1)
        elif granularity == TimeGranularity.DAILY:
            delta = timedelta(days=1)
        elif granularity == TimeGranularity.WEEKLY:
            delta = timedelta(weeks=1)
        elif granularity == TimeGranularity.MONTHLY:
            delta = timedelta(days=30)  # Approximate
        else:
            delta = timedelta(days=1)  # Default
        
        while current < end_date:
            bucket_end = min(current + delta, end_date)
            buckets.append((current, bucket_end))
            current = bucket_end
        
        return buckets
    
    def _calculate_metric_for_period(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        metric: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate a specific metric for a time period."""
        try:
            if metric == 'entity_count':
                # Count entities created in period
                count = 0
                for db_name, entities in all_data.items():
                    for entity in entities:
                        for field in ['created_time', 'Created', 'Date']:
                            if field in entity:
                                try:
                                    if isinstance(entity[field], str):
                                        date = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                        if start_date <= date < end_date:
                                            count += 1
                                            break
                                except (ValueError, TypeError):
                                    continue
                return float(count)
            
            elif metric == 'task_completion':
                # Count completed tasks in period
                tasks = all_data.get('Actionable Tasks', [])
                completed = 0
                for task in tasks:
                    if task.get('Status', '').lower() in ['done', 'completed']:
                        # Check if completed in this period (simplified)
                        completed += 1
                return float(completed)
            
            elif metric == 'activity_level':
                # Count any activity in period
                activity = 0
                for db_name, entities in all_data.items():
                    for entity in entities:
                        for field in ['last_edited_time', 'created_time']:
                            if field in entity:
                                try:
                                    if isinstance(entity[field], str):
                                        date = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                        if start_date <= date < end_date:
                                            activity += 1
                                            break
                                except (ValueError, TypeError):
                                    continue
                return float(activity)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating metric {metric}: {e}")
            return 0.0
    
    def _analyze_metric_trend(self, values: List[float]) -> TrendIndicator:
        """Analyze trend in a series of values."""
        try:
            direction, rate, confidence = self._calculate_linear_trend(values)
            return TrendIndicator(
                direction=direction,
                rate=rate,
                confidence=confidence,
                significance=confidence > 0.5
            )
        except Exception as e:
            logger.error(f"Error analyzing metric trend: {e}")
            return TrendIndicator(
                direction=TrendDirection.STABLE,
                rate=0.0,
                confidence=0.0,
                significance=False
            )
    
    def _generate_metric_forecast(
        self,
        values: List[float],
        last_timestamp: datetime,
        time_interval: timedelta,
        forecast_periods: int
    ) -> List[ForecastPoint]:
        """Generate forecast for a metric using linear regression."""
        try:
            if len(values) < 2:
                return []
            
            # Simple linear regression
            n = len(values)
            x_values = list(range(n))
            
            # Calculate slope and intercept
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(values)
            
            numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator
            
            intercept = y_mean - slope * x_mean
            
            # Generate forecasts
            forecasts = []
            for i in range(1, forecast_periods + 1):
                forecast_timestamp = last_timestamp + i * time_interval
                predicted_value = intercept + slope * (n + i - 1)
                
                # Simple confidence interval (±20%)
                confidence_interval = {
                    'lower': predicted_value * 0.8,
                    'upper': predicted_value * 1.2
                }
                
                forecast = ForecastPoint(
                    timestamp=forecast_timestamp,
                    predicted_value=max(0, predicted_value),  # Ensure non-negative
                    confidence_interval=confidence_interval
                )
                forecasts.append(forecast)
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Error generating metric forecast: {e}")
            return []
    
    def _calculate_linear_trend(self, values: List[float]) -> Tuple[TrendDirection, float, float]:
        """Calculate linear trend direction, rate, and confidence."""
        try:
            if len(values) < 2:
                return TrendDirection.STABLE, 0.0, 0.0
            
            n = len(values)
            x_values = list(range(n))
            
            # Calculate correlation coefficient as confidence measure
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(values)
            
            numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            x_variance = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            y_variance = sum((values[i] - y_mean) ** 2 for i in range(n))
            
            if x_variance == 0 or y_variance == 0:
                return TrendDirection.STABLE, 0.0, 0.0
            
            correlation = numerator / math.sqrt(x_variance * y_variance)
            confidence = abs(correlation)
            
            # Calculate slope
            slope = numerator / x_variance
            rate = abs(slope / y_mean) if y_mean != 0 else 0.0
            
            # Determine direction
            if slope > 0.01:  # Threshold for significant increase
                direction = TrendDirection.INCREASING
            elif slope < -0.01:  # Threshold for significant decrease
                direction = TrendDirection.DECREASING
            else:
                # Check volatility
                if statistics.stdev(values) > y_mean * 0.5:  # High volatility
                    direction = TrendDirection.VOLATILE
                else:
                    direction = TrendDirection.STABLE
            
            return direction, rate, confidence
            
        except Exception as e:
            logger.error(f"Error calculating linear trend: {e}")
            return TrendDirection.STABLE, 0.0, 0.0
    
    def _detect_temporal_patterns(self, all_data: Dict[str, List[Dict[str, Any]]]) -> List[Pattern]:
        """Detect temporal patterns in the data."""
        patterns = []
        
        try:
            # Collect timestamps
            timestamps = []
            for db_name, entities in all_data.items():
                for entity in entities:
                    for field in ['created_time', 'last_edited_time', 'Date']:
                        if field in entity:
                            try:
                                if isinstance(entity[field], str):
                                    date = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                    timestamps.append(date)
                                    break
                            except (ValueError, TypeError):
                                continue
            
            if len(timestamps) < 10:
                return patterns
            
            # Analyze day-of-week patterns
            dow_counts = [0] * 7  # Monday = 0, Sunday = 6
            for ts in timestamps:
                dow_counts[ts.weekday()] += 1
            
            # Find peak day
            max_count = max(dow_counts)
            max_day = dow_counts.index(max_count)
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            if max_count > len(timestamps) * 0.2:  # More than 20% on one day
                pattern = Pattern(
                    type='temporal',
                    description=f'Increased activity on {day_names[max_day]}s',
                    confidence=min(0.9, max_count / len(timestamps) * 3),
                    supporting_data={
                        'day_of_week': max_day,
                        'count': max_count,
                        'total': len(timestamps),
                        'percentage': max_count / len(timestamps)
                    },
                    entities=[]
                )
                patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"Error detecting temporal patterns: {e}")
        
        return patterns
    
    def _detect_status_patterns(self, all_data: Dict[str, List[Dict[str, Any]]]) -> List[Pattern]:
        """Detect patterns in status distributions."""
        patterns = []
        
        try:
            # Analyze task status patterns
            tasks = all_data.get('Actionable Tasks', [])
            if tasks:
                status_counts = defaultdict(int)
                for task in tasks:
                    status = task.get('Status', 'Unknown')
                    status_counts[status] += 1
                
                total_tasks = len(tasks)
                
                # Check for concerning patterns
                not_started = status_counts.get('Not started', 0) + status_counts.get('To-Do', 0)
                if not_started > total_tasks * 0.7:  # More than 70% not started
                    pattern = Pattern(
                        type='status',
                        description='High proportion of tasks not yet started',
                        confidence=0.8,
                        supporting_data={
                            'not_started': not_started,
                            'total': total_tasks,
                            'percentage': not_started / total_tasks
                        },
                        entities=['Actionable Tasks']
                    )
                    patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"Error detecting status patterns: {e}")
        
        return patterns
    
    def _detect_relationship_patterns(self, all_data: Dict[str, List[Dict[str, Any]]]) -> List[Pattern]:
        """Detect patterns in entity relationships."""
        patterns = []
        
        try:
            # Analyze people-organization relationships
            people = all_data.get('People & Contacts', [])
            if people:
                org_counts = defaultdict(int)
                for person in people:
                    orgs = person.get('Organization', [])
                    if isinstance(orgs, list):
                        for org in orgs:
                            if isinstance(org, str):
                                org_counts[org] += 1
                
                if org_counts:
                    max_org = max(org_counts, key=org_counts.get)
                    max_count = org_counts[max_org]
                    
                    if max_count > len(people) * 0.3:  # More than 30% from one org
                        pattern = Pattern(
                            type='relationship',
                            description=f'High concentration of people from {max_org}',
                            confidence=0.7,
                            supporting_data={
                                'organization': max_org,
                                'count': max_count,
                                'total_people': len(people),
                                'percentage': max_count / len(people)
                            },
                            entities=['People & Contacts', 'Organizations & Bodies']
                        )
                        patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"Error detecting relationship patterns: {e}")
        
        return patterns
    
    def _detect_volume_anomalies(self, all_data: Dict[str, List[Dict[str, Any]]]) -> List[Anomaly]:
        """Detect volume anomalies in the data."""
        anomalies = []
        
        try:
            # Check for unusually large databases
            db_sizes = {db_name: len(entities) for db_name, entities in all_data.items()}
            
            if len(db_sizes) > 1:
                mean_size = statistics.mean(db_sizes.values())
                stdev_size = statistics.stdev(db_sizes.values()) if len(db_sizes) > 1 else 0
                
                for db_name, size in db_sizes.items():
                    if stdev_size > 0:
                        z_score = (size - mean_size) / stdev_size
                        
                        if abs(z_score) > 2.0:  # More than 2 standard deviations
                            severity = 'high' if abs(z_score) > 3.0 else 'medium'
                            
                            anomaly = Anomaly(
                                type='volume',
                                description=f'Unusual entity count in {db_name}',
                                timestamp=datetime.utcnow(),
                                severity=severity,
                                details={
                                    'database': db_name,
                                    'size': size,
                                    'mean_size': mean_size,
                                    'z_score': z_score
                                },
                                affected_entities=[db_name]
                            )
                            anomalies.append(anomaly)
            
        except Exception as e:
            logger.error(f"Error detecting volume anomalies: {e}")
        
        return anomalies
    
    def _detect_status_anomalies(self, all_data: Dict[str, List[Dict[str, Any]]]) -> List[Anomaly]:
        """Detect status-related anomalies."""
        anomalies = []
        
        try:
            # Check for unusual task status distributions
            tasks = all_data.get('Actionable Tasks', [])
            if tasks:
                overdue_tasks = []
                for task in tasks:
                    due_date_str = task.get('Due Date', '')
                    if due_date_str:
                        try:
                            if isinstance(due_date_str, str):
                                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                                if due_date < datetime.utcnow() and task.get('Status', '').lower() not in ['done', 'completed']:
                                    overdue_tasks.append(task)
                        except (ValueError, TypeError):
                            continue
                
                if len(overdue_tasks) > len(tasks) * 0.3:  # More than 30% overdue
                    anomaly = Anomaly(
                        type='status',
                        description='High number of overdue tasks',
                        timestamp=datetime.utcnow(),
                        severity='high',
                        details={
                            'overdue_count': len(overdue_tasks),
                            'total_tasks': len(tasks),
                            'percentage': len(overdue_tasks) / len(tasks)
                        },
                        affected_entities=['Actionable Tasks']
                    )
                    anomalies.append(anomaly)
            
        except Exception as e:
            logger.error(f"Error detecting status anomalies: {e}")
        
        return anomalies
    
    def _detect_temporal_anomalies(self, all_data: Dict[str, List[Dict[str, Any]]]) -> List[Anomaly]:
        """Detect temporal anomalies in the data."""
        anomalies = []
        
        try:
            # Check for unusual activity spikes
            now = datetime.utcnow()
            recent_activity = []
            
            # Count activity by day for last 7 days
            for i in range(7):
                day_start = now - timedelta(days=i+1)
                day_end = now - timedelta(days=i)
                
                day_activity = 0
                for db_name, entities in all_data.items():
                    for entity in entities:
                        for field in ['created_time', 'last_edited_time']:
                            if field in entity:
                                try:
                                    if isinstance(entity[field], str):
                                        date = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                        if day_start <= date < day_end:
                                            day_activity += 1
                                            break
                                except (ValueError, TypeError):
                                    continue
                
                recent_activity.append(day_activity)
            
            if len(recent_activity) > 1:
                mean_activity = statistics.mean(recent_activity)
                stdev_activity = statistics.stdev(recent_activity) if len(recent_activity) > 1 else 0
                
                # Check for spikes
                max_activity = max(recent_activity)
                if stdev_activity > 0:
                    z_score = (max_activity - mean_activity) / stdev_activity
                    
                    if z_score > 2.0:  # Unusual spike
                        anomaly = Anomaly(
                            type='temporal',
                            description='Unusual spike in activity',
                            timestamp=now - timedelta(days=recent_activity.index(max_activity)),
                            severity='medium',
                            details={
                                'spike_value': max_activity,
                                'mean_activity': mean_activity,
                                'z_score': z_score
                            },
                            affected_entities=list(all_data.keys())
                        )
                        anomalies.append(anomaly)
            
        except Exception as e:
            logger.error(f"Error detecting temporal anomalies: {e}")
        
        return anomalies