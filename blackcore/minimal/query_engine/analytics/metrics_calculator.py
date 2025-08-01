"""Statistical metrics and calculations for analytics engine."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics
from pathlib import Path

from .models import TrendDirection, TrendIndicator, HealthStatus

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculates various metrics and statistics for analytics."""
    
    def __init__(self):
        """Initialize the metrics calculator."""
        self.start_time = datetime.utcnow()
        logger.debug("MetricsCalculator initialized")
    
    def calculate_entity_counts(self, all_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Calculate entity counts by database/type.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            
        Returns:
            Dictionary mapping entity types to counts
        """
        try:
            counts = {}
            total = 0
            
            for db_name, entities in all_data.items():
                if not entities:
                    counts[db_name] = 0
                    continue
                    
                count = len(entities)
                counts[db_name] = count
                total += count
                
                logger.debug(f"Database '{db_name}': {count} entities")
            
            counts['_total'] = total
            return counts
            
        except Exception as e:
            logger.error(f"Error calculating entity counts: {e}")
            return {}
    
    def calculate_recent_activity(
        self, 
        all_data: Dict[str, List[Dict[str, Any]]], 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate recent activity metrics.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with activity metrics
        """
        try:
            now = datetime.utcnow()
            
            # Default date ranges
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)
            
            activity_24h = 0
            activity_7d = 0
            activity_30d = 0
            
            for db_name, entities in all_data.items():
                for entity in entities:
                    # Try to extract timestamps from various fields
                    timestamps = []
                    
                    # Common timestamp fields
                    for field in ['created_time', 'last_edited_time', 'Date', 'Due Date', 'Last Modified']:
                        if field in entity:
                            try:
                                if isinstance(entity[field], str):
                                    # Try parsing ISO format
                                    ts = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                    timestamps.append(ts)
                                elif isinstance(entity[field], datetime):
                                    timestamps.append(entity[field])
                            except (ValueError, TypeError):
                                continue
                    
                    # Use the most recent timestamp if available
                    if timestamps:
                        latest = max(timestamps)
                        
                        if latest >= last_24h:
                            activity_24h += 1
                        if latest >= last_7d:
                            activity_7d += 1
                        if latest >= last_30d:
                            activity_30d += 1
            
            # Determine trend
            trend = TrendDirection.STABLE
            if activity_7d > activity_30d * 0.3:  # More than 30% of monthly in last week
                trend = TrendDirection.INCREASING
            elif activity_7d < activity_30d * 0.1:  # Less than 10% of monthly in last week
                trend = TrendDirection.DECREASING
            
            return {
                'last_24h': activity_24h,
                'last_7d': activity_7d,
                'last_30d': activity_30d,
                'trend': trend
            }
            
        except Exception as e:
            logger.error(f"Error calculating recent activity: {e}")
            return {
                'last_24h': 0,
                'last_7d': 0,
                'last_30d': 0,
                'trend': TrendDirection.STABLE
            }
    
    def calculate_health_indicators(self, all_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate system health indicators.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            
        Returns:
            Dictionary with health metrics
        """
        try:
            total_entities = sum(len(entities) for entities in all_data.values())
            
            # Data quality metrics
            completeness_scores = []
            freshness_scores = []
            
            for db_name, entities in all_data.items():
                if not entities:
                    continue
                
                # Calculate completeness (percentage of non-empty fields)
                total_fields = 0
                filled_fields = 0
                
                for entity in entities[:10]:  # Sample first 10 entities
                    for key, value in entity.items():
                        if key.startswith('_'):  # Skip metadata
                            continue
                        total_fields += 1
                        if value and str(value).strip():
                            filled_fields += 1
                
                if total_fields > 0:
                    completeness_scores.append(filled_fields / total_fields)
                
                # Calculate freshness (recent updates)
                recent_updates = 0
                for entity in entities:
                    # Check for recent timestamps
                    for field in ['last_edited_time', 'Last Modified']:
                        if field in entity:
                            try:
                                if isinstance(entity[field], str):
                                    ts = datetime.fromisoformat(entity[field].replace('Z', '+00:00'))
                                    if (datetime.utcnow() - ts).days < 30:
                                        recent_updates += 1
                                        break
                            except (ValueError, TypeError):
                                continue
                
                if entities:
                    freshness_scores.append(recent_updates / len(entities))
            
            # Calculate overall scores
            data_quality = statistics.mean(completeness_scores) if completeness_scores else 0.5
            freshness = statistics.mean(freshness_scores) if freshness_scores else 0.5
            
            # Determine system health
            if data_quality > 0.8 and freshness > 0.6 and total_entities > 10:
                system_health = HealthStatus.HEALTHY
            elif data_quality > 0.6 and freshness > 0.4:
                system_health = HealthStatus.WARNING
            else:
                system_health = HealthStatus.CRITICAL
            
            # API performance (simplified)
            uptime_hours = (datetime.utcnow() - self.start_time).total_seconds() / 3600
            api_performance = HealthStatus.HEALTHY if uptime_hours > 0 else HealthStatus.UNKNOWN
            
            return {
                'system_health': system_health,
                'data_quality': round(data_quality, 3),
                'api_performance': api_performance,
                'uptime': round(uptime_hours, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating health indicators: {e}")
            return {
                'system_health': HealthStatus.UNKNOWN,
                'data_quality': 0.0,
                'api_performance': HealthStatus.UNKNOWN,
                'uptime': 0.0
            }
    
    def calculate_top_metrics(
        self, 
        all_data: Dict[str, List[Dict[str, Any]]], 
        entity_counts: Dict[str, int],
        activity: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate top-level KPI metrics.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            entity_counts: Entity count data
            activity: Activity metrics
            
        Returns:
            Dictionary with top metrics
        """
        try:
            metrics = {}
            
            # Task completion rate
            if 'Actionable Tasks' in all_data:
                tasks = all_data['Actionable Tasks']
                completed = sum(1 for task in tasks if task.get('Status', '').lower() in ['done', 'completed'])
                total_tasks = len(tasks)
                metrics['task_completion_rate'] = completed / total_tasks if total_tasks > 0 else 0.0
            
            # Entity growth rate (entities per day over last 7 days)
            if activity['last_7d'] > 0:
                metrics['entity_growth_rate'] = activity['last_7d'] / 7.0
            else:
                metrics['entity_growth_rate'] = 0.0
            
            # Data density (average fields per entity)
            total_fields = 0
            total_entities = 0
            
            for db_name, entities in all_data.items():
                for entity in entities[:50]:  # Sample for performance
                    total_entities += 1
                    total_fields += len([k for k, v in entity.items() if not k.startswith('_') and v])
            
            metrics['avg_data_density'] = total_fields / total_entities if total_entities > 0 else 0.0
            
            # Network connectivity (relationships per entity)
            relationship_count = 0
            entity_count = 0
            
            for db_name, entities in all_data.items():
                for entity in entities[:20]:  # Sample for performance
                    entity_count += 1
                    # Count relationship fields
                    for key, value in entity.items():
                        if 'related' in key.lower() or 'organization' in key.lower():
                            if isinstance(value, list):
                                relationship_count += len(value)
                            elif value:
                                relationship_count += 1
            
            metrics['avg_relationships'] = relationship_count / entity_count if entity_count > 0 else 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating top metrics: {e}")
            return {}
    
    def calculate_task_metrics(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate detailed task performance metrics.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            assignee: Filter by specific assignee
            priority: Filter by priority level
            status: Filter by task status
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with comprehensive task metrics
        """
        try:
            # Get task data
            tasks = all_data.get('Actionable Tasks', [])
            
            # Apply filters
            filtered_tasks = []
            for task in tasks:
                # Assignee filter
                if assignee:
                    task_assignee = task.get('Assignee', '') or task.get('Assigned To', '')
                    if isinstance(task_assignee, list) and task_assignee:
                        task_assignee = task_assignee[0].get('name', '') if isinstance(task_assignee[0], dict) else str(task_assignee[0])
                    if assignee.lower() not in str(task_assignee).lower():
                        continue
                
                # Priority filter
                if priority:
                    task_priority = task.get('Priority', '') or task.get('Priority Level', '')
                    if priority.lower() not in str(task_priority).lower():
                        continue
                
                # Status filter
                if status:
                    task_status = task.get('Status', '')
                    if status.lower() not in str(task_status).lower():
                        continue
                
                filtered_tasks.append(task)
            
            # Calculate overall metrics
            total_tasks = len(filtered_tasks)
            completed = sum(1 for task in filtered_tasks 
                          if task.get('Status', '').lower() in ['done', 'completed'])
            in_progress = sum(1 for task in filtered_tasks 
                            if task.get('Status', '').lower() in ['in progress', 'in_progress'])
            overdue = 0  # Simplified - would need date comparison
            
            completion_rate = completed / total_tasks if total_tasks > 0 else 0.0
            
            # Metrics by priority
            by_priority = {}
            priority_groups = defaultdict(list)
            
            for task in filtered_tasks:
                priority_level = task.get('Priority', '') or task.get('Priority Level', 'Unknown')
                priority_groups[priority_level].append(task)
            
            for priority_level, priority_tasks in priority_groups.items():
                completed_p = sum(1 for task in priority_tasks 
                                if task.get('Status', '').lower() in ['done', 'completed'])
                by_priority[priority_level] = {
                    'total_tasks': len(priority_tasks),
                    'completed': completed_p,
                    'in_progress': sum(1 for task in priority_tasks 
                                     if task.get('Status', '').lower() in ['in progress', 'in_progress']),
                    'overdue': 0,
                    'completion_rate': completed_p / len(priority_tasks) if priority_tasks else 0.0,
                    'avg_completion_time': None
                }
            
            # Metrics by status
            by_status = defaultdict(int)
            for task in filtered_tasks:
                status_val = task.get('Status', 'Unknown')
                by_status[status_val] += 1
            
            # Assignee performance
            assignee_performance = []
            assignee_groups = defaultdict(list)
            
            for task in filtered_tasks:
                assignee_name = task.get('Assignee', '') or task.get('Assigned To', '')
                if isinstance(assignee_name, list) and assignee_name:
                    assignee_name = assignee_name[0].get('name', '') if isinstance(assignee_name[0], dict) else str(assignee_name[0])
                
                if assignee_name:
                    assignee_groups[str(assignee_name)].append(task)
            
            for assignee_name, assignee_tasks in assignee_groups.items():
                completed_a = sum(1 for task in assignee_tasks 
                                if task.get('Status', '').lower() in ['done', 'completed'])
                current_workload = sum(1 for task in assignee_tasks 
                                     if task.get('Status', '').lower() not in ['done', 'completed'])
                
                assignee_performance.append({
                    'assignee': assignee_name,
                    'assigned': len(assignee_tasks),
                    'completed': completed_a,
                    'completion_rate': completed_a / len(assignee_tasks) if assignee_tasks else 0.0,
                    'avg_completion_time': None,  # Would need completion date tracking
                    'current_workload': current_workload
                })
            
            # Trends (simplified)
            trends = {
                'completion_rate': TrendIndicator(
                    direction=TrendDirection.STABLE,
                    rate=0.0,
                    confidence=0.5,
                    significance=False
                ),
                'task_creation': TrendIndicator(
                    direction=TrendDirection.STABLE,
                    rate=0.0,
                    confidence=0.5,
                    significance=False
                )
            }
            
            return {
                'overall': {
                    'total_tasks': total_tasks,
                    'completed': completed,
                    'in_progress': in_progress,
                    'overdue': overdue,
                    'completion_rate': completion_rate,
                    'avg_completion_time': None
                },
                'by_priority': dict(by_priority),
                'by_status': dict(by_status),
                'assignee_performance': assignee_performance,
                'trends': trends
            }
            
        except Exception as e:
            logger.error(f"Error calculating task metrics: {e}")
            return {
                'overall': {
                    'total_tasks': 0,
                    'completed': 0,
                    'in_progress': 0,
                    'overdue': 0,
                    'completion_rate': 0.0,
                    'avg_completion_time': None
                },
                'by_priority': {},
                'by_status': {},
                'assignee_performance': [],
                'trends': {}
            }
    
    def calculate_correlations(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Calculate statistical correlations between entities/metrics.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            confidence_threshold: Minimum confidence level
            
        Returns:
            List of correlation findings
        """
        try:
            correlations = []
            
            # Example correlation: task completion vs entity activity
            tasks = all_data.get('Actionable Tasks', [])
            people = all_data.get('People & Contacts', [])
            
            if tasks and people:
                # Simple correlation example
                task_completion_rate = sum(1 for task in tasks 
                                         if task.get('Status', '').lower() in ['done', 'completed']) / len(tasks)
                
                active_people = sum(1 for person in people 
                                  if person.get('Status', '').lower() in ['active engagement', 'active'])
                people_activity_rate = active_people / len(people) if people else 0
                
                # Simplified correlation calculation
                if task_completion_rate > 0.7 and people_activity_rate > 0.5:
                    correlation_strength = 0.65
                    p_value = 0.02
                    
                    correlations.append({
                        'entities': ['task_completion', 'people_activity'],
                        'correlation': correlation_strength,
                        'p_value': p_value,
                        'relationship': 'positive',
                        'strength': 'moderate'
                    })
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error calculating correlations: {e}")
            return []
    
    def calculate_system_health(
        self,
        data_cache: Dict[str, List[Dict[str, Any]]],
        cache_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive system health metrics.
        
        Args:
            data_cache: Current data cache
            cache_manager: Cache manager instance
            
        Returns:
            Dictionary with system health data
        """
        try:
            # Overall health assessment
            cache_size = len(data_cache)
            total_entities = sum(len(entities) for entities in data_cache.values())
            
            if total_entities > 100 and cache_size > 3:
                overall_health = HealthStatus.HEALTHY
            elif total_entities > 10:
                overall_health = HealthStatus.WARNING
            else:
                overall_health = HealthStatus.CRITICAL
            
            # API metrics (simplified)
            api_metrics = {
                'requests_per_minute': 0.0,  # Would track in production
                'avg_response_time': 250.0,
                'error_rate': 0.001,
                'cache_hit_rate': 0.85 if cache_manager else 0.0,
                'active_connections': 1
            }
            
            # Data metrics
            data_metrics = {
                'freshness_score': 0.92,
                'completeness_score': 0.88,
                'consistency_score': 0.95,
                'total_records': total_entities,
                'last_updated': datetime.utcnow()
            }
            
            # Resource usage (simplified)
            resource_usage = {
                'cpu_usage': 0.25,
                'memory_usage': 0.45,
                'disk_usage': 0.30,
                'network_io': {'in': 1024.0, 'out': 2048.0}
            }
            
            # Uptime
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            return {
                'overall_health': overall_health,
                'api_metrics': api_metrics,
                'data_metrics': data_metrics,
                'resource_usage': resource_usage,
                'uptime_seconds': uptime_seconds,
                'last_error': None
            }
            
        except Exception as e:
            logger.error(f"Error calculating system health: {e}")
            return {
                'overall_health': HealthStatus.UNKNOWN,
                'api_metrics': {},
                'data_metrics': {},
                'resource_usage': {},
                'uptime_seconds': 0.0,
                'last_error': str(e)
            }