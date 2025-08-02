"""
LLM-Specific Performance Profiler

Provides detailed performance profiling and optimization recommendations
for LLM operations including latency analysis, token usage, and bottleneck detection.
"""

import time
import json
import psutil
import threading
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
from contextlib import contextmanager

from .models import ExtractedEntities


@dataclass
class LLMOperationMetrics:
    """Metrics for a single LLM operation."""
    operation_id: str
    operation_type: str  # extraction, scoring, validation
    model: str
    start_time: float
    end_time: float
    
    # Latency breakdown
    total_latency_ms: float
    api_latency_ms: float
    preprocessing_ms: float
    postprocessing_ms: float
    
    # Token metrics
    input_tokens: int
    output_tokens: int
    
    # Resource usage
    cpu_percent: float
    memory_mb: float
    
    # Quality metrics
    success: bool
    error: Optional[str] = None
    output_quality_score: Optional[float] = None
    
    # Context
    input_size_bytes: int = 0
    output_size_bytes: int = 0
    batch_size: int = 1


@dataclass
class PerformanceProfile:
    """Aggregated performance profile."""
    model: str
    operation_type: str
    sample_count: int
    
    # Latency statistics
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    
    # Throughput
    avg_tokens_per_second: float
    requests_per_minute: float
    
    # Cost efficiency
    avg_cost_per_operation: float
    tokens_per_dollar: float
    
    # Reliability
    success_rate: float
    error_types: Dict[str, int]
    
    # Resource usage
    avg_cpu_percent: float
    avg_memory_mb: float
    
    # Recommendations
    bottlenecks: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)


class LLMPerformanceProfiler:
    """Profile and optimize LLM operation performance."""
    
    def __init__(
        self,
        window_size: int = 1000,
        profile_interval: int = 60,
        enable_resource_monitoring: bool = True
    ):
        """Initialize performance profiler.
        
        Args:
            window_size: Size of metrics window for analysis
            profile_interval: Seconds between profile snapshots
            enable_resource_monitoring: Track CPU/memory usage
        """
        self.window_size = window_size
        self.profile_interval = profile_interval
        self.enable_resource_monitoring = enable_resource_monitoring
        
        # Metrics storage
        self.metrics_window = deque(maxlen=window_size)
        self.profiles_by_model = defaultdict(list)
        self.operation_timers = {}
        
        # Real-time monitoring
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        self.current_operations = {}
        
        # Cost tracking
        self.cost_per_1k_tokens = {
            'claude-3-5-haiku': 0.001,
            'claude-3-5-sonnet': 0.003,
            'gpt-3.5-turbo': 0.0005,
            'gpt-4': 0.01
        }
    
    @contextmanager
    def profile_operation(
        self,
        operation_id: str,
        operation_type: str,
        model: str,
        input_data: Any
    ):
        """Context manager to profile an LLM operation.
        
        Usage:
            with profiler.profile_operation("op1", "extraction", "claude-3-5-haiku", transcript) as timer:
                # Perform LLM operation
                timer.record_api_start()
                result = llm.extract(transcript)
                timer.record_api_end()
        """
        timer = OperationTimer(
            operation_id=operation_id,
            operation_type=operation_type,
            model=model,
            input_size=len(str(input_data).encode('utf-8'))
        )
        
        self.operation_timers[operation_id] = timer
        
        # Start resource monitoring if enabled
        if self.enable_resource_monitoring:
            timer.start_resource_monitoring()
        
        timer.start()
        
        try:
            yield timer
        finally:
            timer.stop()
            
            # Record metrics
            metrics = timer.get_metrics()
            self.metrics_window.append(metrics)
            
            # Clean up
            del self.operation_timers[operation_id]
    
    def analyze_performance(
        self,
        model: Optional[str] = None,
        operation_type: Optional[str] = None,
        last_n: Optional[int] = None
    ) -> Dict[str, PerformanceProfile]:
        """Analyze performance metrics and generate profiles.
        
        Args:
            model: Filter by specific model
            operation_type: Filter by operation type
            last_n: Analyze only last N operations
            
        Returns:
            Performance profiles by model/operation
        """
        # Filter metrics
        metrics_to_analyze = list(self.metrics_window)
        
        if last_n:
            metrics_to_analyze = metrics_to_analyze[-last_n:]
        
        if model:
            metrics_to_analyze = [m for m in metrics_to_analyze if m.model == model]
        
        if operation_type:
            metrics_to_analyze = [m for m in metrics_to_analyze if m.operation_type == operation_type]
        
        # Group by model and operation type
        grouped_metrics = defaultdict(list)
        for metric in metrics_to_analyze:
            key = f"{metric.model}:{metric.operation_type}"
            grouped_metrics[key].append(metric)
        
        # Generate profiles
        profiles = {}
        
        for key, metrics in grouped_metrics.items():
            model, op_type = key.split(':')
            profile = self._create_performance_profile(model, op_type, metrics)
            profiles[key] = profile
        
        return profiles
    
    def get_optimization_recommendations(
        self,
        profiles: Dict[str, PerformanceProfile]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on profiles.
        
        Args:
            profiles: Performance profiles to analyze
            
        Returns:
            List of prioritized recommendations
        """
        recommendations = []
        
        for key, profile in profiles.items():
            # High latency detection
            if profile.p95_latency_ms > 5000:
                recommendations.append({
                    'priority': 'high',
                    'type': 'latency',
                    'model': profile.model,
                    'issue': f"High P95 latency: {profile.p95_latency_ms:.0f}ms",
                    'suggestion': "Consider using a faster model or implementing caching",
                    'potential_improvement': f"{(profile.p95_latency_ms - profile.p50_latency_ms) / profile.p95_latency_ms * 100:.0f}% reduction possible"
                })
            
            # Low success rate
            if profile.success_rate < 0.95:
                recommendations.append({
                    'priority': 'high',
                    'type': 'reliability',
                    'model': profile.model,
                    'issue': f"Low success rate: {profile.success_rate:.1%}",
                    'suggestion': "Implement retry logic and error handling",
                    'error_breakdown': profile.error_types
                })
            
            # Cost optimization
            if profile.avg_cost_per_operation > 0.10:
                recommendations.append({
                    'priority': 'medium',
                    'type': 'cost',
                    'model': profile.model,
                    'issue': f"High cost per operation: ${profile.avg_cost_per_operation:.3f}",
                    'suggestion': "Consider cheaper models for simple tasks or batch operations",
                    'alternative_models': self._suggest_cheaper_alternatives(profile.model)
                })
            
            # Resource usage
            if profile.avg_cpu_percent > 50:
                recommendations.append({
                    'priority': 'medium',
                    'type': 'resource',
                    'model': profile.model,
                    'issue': f"High CPU usage: {profile.avg_cpu_percent:.0f}%",
                    'suggestion': "Optimize preprocessing/postprocessing or use async operations"
                })
            
            # Token efficiency
            tokens_per_op = sum(m.input_tokens + m.output_tokens for m in grouped_metrics[key]) / len(grouped_metrics[key])
            if tokens_per_op > 2000:
                recommendations.append({
                    'priority': 'low',
                    'type': 'efficiency',
                    'model': profile.model,
                    'issue': f"High token usage: {tokens_per_op:.0f} tokens/operation",
                    'suggestion': "Optimize prompts or implement prompt compression"
                })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return recommendations
    
    def start_real_time_monitoring(self):
        """Start real-time performance monitoring."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitor_loop)
        self.monitoring_thread.start()
    
    def stop_real_time_monitoring(self):
        """Stop real-time performance monitoring."""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join()
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get current real-time performance statistics."""
        recent_metrics = list(self.metrics_window)[-100:]  # Last 100 operations
        
        if not recent_metrics:
            return {}
        
        # Calculate real-time stats
        current_time = time.time()
        time_window = 300  # 5 minutes
        
        recent_ops = [
            m for m in recent_metrics
            if current_time - m.end_time < time_window
        ]
        
        if not recent_ops:
            return {}
        
        # Group by model
        model_stats = defaultdict(lambda: {
            'operations': 0,
            'avg_latency_ms': 0,
            'success_rate': 0,
            'tokens_per_second': 0
        })
        
        for metric in recent_ops:
            stats = model_stats[metric.model]
            stats['operations'] += 1
            stats['avg_latency_ms'] += metric.total_latency_ms
            stats['success_rate'] += 1 if metric.success else 0
            
            if metric.api_latency_ms > 0:
                tokens = metric.input_tokens + metric.output_tokens
                stats['tokens_per_second'] += tokens / (metric.api_latency_ms / 1000)
        
        # Normalize
        for model, stats in model_stats.items():
            count = stats['operations']
            if count > 0:
                stats['avg_latency_ms'] /= count
                stats['success_rate'] /= count
                stats['tokens_per_second'] /= count
                stats['throughput_rpm'] = count / (time_window / 60)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'time_window_seconds': time_window,
            'total_operations': len(recent_ops),
            'model_stats': dict(model_stats),
            'active_operations': len(self.operation_timers)
        }
    
    def export_performance_data(
        self,
        output_path: str,
        format: str = 'json'
    ):
        """Export performance data for external analysis.
        
        Args:
            output_path: Path to save data
            format: Export format (json, csv)
        """
        if format == 'json':
            data = {
                'export_date': datetime.now().isoformat(),
                'metrics': [self._metric_to_dict(m) for m in self.metrics_window],
                'profiles': {
                    key: self._profile_to_dict(profile)
                    for key, profile in self.analyze_performance().items()
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif format == 'csv':
            import csv
            
            with open(output_path, 'w', newline='') as f:
                if self.metrics_window:
                    fieldnames = self._metric_to_dict(self.metrics_window[0]).keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for metric in self.metrics_window:
                        writer.writerow(self._metric_to_dict(metric))
    
    def _create_performance_profile(
        self,
        model: str,
        operation_type: str,
        metrics: List[LLMOperationMetrics]
    ) -> PerformanceProfile:
        """Create performance profile from metrics."""
        if not metrics:
            return PerformanceProfile(
                model=model,
                operation_type=operation_type,
                sample_count=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                avg_tokens_per_second=0,
                requests_per_minute=0,
                avg_cost_per_operation=0,
                tokens_per_dollar=0,
                success_rate=0,
                error_types={},
                avg_cpu_percent=0,
                avg_memory_mb=0
            )
        
        # Latency statistics
        latencies = [m.total_latency_ms for m in metrics]
        
        # Throughput
        total_time = max(m.end_time for m in metrics) - min(m.start_time for m in metrics)
        rpm = len(metrics) / (total_time / 60) if total_time > 0 else 0
        
        # Token throughput
        token_rates = []
        for m in metrics:
            if m.api_latency_ms > 0:
                tokens = m.input_tokens + m.output_tokens
                rate = tokens / (m.api_latency_ms / 1000)
                token_rates.append(rate)
        
        avg_tokens_per_second = np.mean(token_rates) if token_rates else 0
        
        # Cost calculation
        costs = []
        tokens_per_dollar_list = []
        
        for m in metrics:
            tokens = (m.input_tokens + m.output_tokens) / 1000
            base_rate = self.cost_per_1k_tokens.get(model.split('-')[0], 0.001)
            cost = tokens * base_rate
            costs.append(cost)
            
            if cost > 0:
                tokens_per_dollar_list.append((m.input_tokens + m.output_tokens) / cost)
        
        # Success rate and errors
        successful = [m for m in metrics if m.success]
        success_rate = len(successful) / len(metrics)
        
        error_types = defaultdict(int)
        for m in metrics:
            if not m.success and m.error:
                error_type = m.error.split(':')[0] if ':' in m.error else 'Unknown'
                error_types[error_type] += 1
        
        # Resource usage
        cpu_percents = [m.cpu_percent for m in metrics if m.cpu_percent > 0]
        memory_mbs = [m.memory_mb for m in metrics if m.memory_mb > 0]
        
        # Identify bottlenecks
        bottlenecks = []
        
        # API latency bottleneck
        api_latencies = [m.api_latency_ms for m in metrics]
        preprocessing_latencies = [m.preprocessing_ms for m in metrics]
        
        if api_latencies and preprocessing_latencies:
            avg_api = np.mean(api_latencies)
            avg_preprocessing = np.mean(preprocessing_latencies)
            
            if avg_api > avg_preprocessing * 10:
                bottlenecks.append("API latency dominates - consider batching or caching")
            elif avg_preprocessing > avg_api:
                bottlenecks.append("Preprocessing is slow - optimize data preparation")
        
        # High variance detection
        if latencies:
            cv = np.std(latencies) / np.mean(latencies) if np.mean(latencies) > 0 else 0
            if cv > 0.5:
                bottlenecks.append("High latency variance - investigate intermittent issues")
        
        # Generate optimization suggestions
        suggestions = []
        
        if success_rate < 0.99:
            suggestions.append("Implement robust retry logic with exponential backoff")
        
        if avg_tokens_per_second < 100:
            suggestions.append("Consider streaming responses for better perceived performance")
        
        if np.percentile(latencies, 95) > 2 * np.median(latencies):
            suggestions.append("Implement request timeout and fallback mechanisms")
        
        return PerformanceProfile(
            model=model,
            operation_type=operation_type,
            sample_count=len(metrics),
            avg_latency_ms=np.mean(latencies),
            p50_latency_ms=np.percentile(latencies, 50),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            avg_tokens_per_second=avg_tokens_per_second,
            requests_per_minute=rpm,
            avg_cost_per_operation=np.mean(costs) if costs else 0,
            tokens_per_dollar=np.mean(tokens_per_dollar_list) if tokens_per_dollar_list else 0,
            success_rate=success_rate,
            error_types=dict(error_types),
            avg_cpu_percent=np.mean(cpu_percents) if cpu_percents else 0,
            avg_memory_mb=np.mean(memory_mbs) if memory_mbs else 0,
            bottlenecks=bottlenecks,
            optimization_suggestions=suggestions
        )
    
    def _suggest_cheaper_alternatives(self, current_model: str) -> List[str]:
        """Suggest cheaper model alternatives."""
        model_tiers = {
            'ultra_cheap': ['claude-3-5-haiku', 'gpt-3.5-turbo'],
            'cheap': ['claude-3-5-sonnet', 'gpt-4-turbo'],
            'expensive': ['gpt-4', 'claude-3-opus']
        }
        
        # Find current tier
        current_tier = None
        for tier, models in model_tiers.items():
            if any(m in current_model for m in models):
                current_tier = tier
                break
        
        # Suggest cheaper options
        suggestions = []
        if current_tier == 'expensive':
            suggestions.extend(model_tiers['cheap'])
            suggestions.extend(model_tiers['ultra_cheap'])
        elif current_tier == 'cheap':
            suggestions.extend(model_tiers['ultra_cheap'])
        
        return suggestions
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self.stop_monitoring.is_set():
            # Snapshot current operations
            snapshot_time = time.time()
            
            # Generate periodic profile
            if len(self.metrics_window) > 10:
                profiles = self.analyze_performance()
                
                for key, profile in profiles.items():
                    self.profiles_by_model[key].append({
                        'timestamp': snapshot_time,
                        'profile': profile
                    })
            
            # Sleep until next interval
            self.stop_monitoring.wait(self.profile_interval)
    
    def _metric_to_dict(self, metric: LLMOperationMetrics) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            'operation_id': metric.operation_id,
            'operation_type': metric.operation_type,
            'model': metric.model,
            'start_time': metric.start_time,
            'end_time': metric.end_time,
            'total_latency_ms': metric.total_latency_ms,
            'api_latency_ms': metric.api_latency_ms,
            'preprocessing_ms': metric.preprocessing_ms,
            'postprocessing_ms': metric.postprocessing_ms,
            'input_tokens': metric.input_tokens,
            'output_tokens': metric.output_tokens,
            'cpu_percent': metric.cpu_percent,
            'memory_mb': metric.memory_mb,
            'success': metric.success,
            'error': metric.error,
            'output_quality_score': metric.output_quality_score,
            'input_size_bytes': metric.input_size_bytes,
            'output_size_bytes': metric.output_size_bytes,
            'batch_size': metric.batch_size
        }
    
    def _profile_to_dict(self, profile: PerformanceProfile) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            'model': profile.model,
            'operation_type': profile.operation_type,
            'sample_count': profile.sample_count,
            'avg_latency_ms': profile.avg_latency_ms,
            'p50_latency_ms': profile.p50_latency_ms,
            'p95_latency_ms': profile.p95_latency_ms,
            'p99_latency_ms': profile.p99_latency_ms,
            'min_latency_ms': profile.min_latency_ms,
            'max_latency_ms': profile.max_latency_ms,
            'avg_tokens_per_second': profile.avg_tokens_per_second,
            'requests_per_minute': profile.requests_per_minute,
            'avg_cost_per_operation': profile.avg_cost_per_operation,
            'tokens_per_dollar': profile.tokens_per_dollar,
            'success_rate': profile.success_rate,
            'error_types': profile.error_types,
            'avg_cpu_percent': profile.avg_cpu_percent,
            'avg_memory_mb': profile.avg_memory_mb,
            'bottlenecks': profile.bottlenecks,
            'optimization_suggestions': profile.optimization_suggestions
        }


class OperationTimer:
    """Timer for tracking operation phases."""
    
    def __init__(
        self,
        operation_id: str,
        operation_type: str,
        model: str,
        input_size: int
    ):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.model = model
        self.input_size = input_size
        
        # Timing
        self.start_time = None
        self.end_time = None
        self.api_start_time = None
        self.api_end_time = None
        self.preprocessing_time = 0
        self.postprocessing_start = None
        
        # Resource monitoring
        self.process = psutil.Process()
        self.initial_cpu = None
        self.initial_memory = None
        self.peak_cpu = 0
        self.peak_memory = 0
        
        # Results
        self.input_tokens = 0
        self.output_tokens = 0
        self.output_size = 0
        self.success = True
        self.error = None
        self.quality_score = None
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
        
    def start_resource_monitoring(self):
        """Start resource monitoring."""
        self.initial_cpu = self.process.cpu_percent()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def record_api_start(self):
        """Record API call start."""
        self.api_start_time = time.time()
        if self.start_time:
            self.preprocessing_time = self.api_start_time - self.start_time
    
    def record_api_end(self, input_tokens: int = 0, output_tokens: int = 0):
        """Record API call end."""
        self.api_end_time = time.time()
        self.postprocessing_start = self.api_end_time
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
    
    def set_output(self, output: Any, quality_score: Optional[float] = None):
        """Set operation output."""
        self.output_size = len(str(output).encode('utf-8'))
        self.quality_score = quality_score
    
    def set_error(self, error: str):
        """Set operation error."""
        self.success = False
        self.error = error
    
    def stop(self):
        """Stop timing."""
        self.end_time = time.time()
        
        # Update resource usage
        if self.initial_cpu is not None:
            current_cpu = self.process.cpu_percent()
            current_memory = self.process.memory_info().rss / 1024 / 1024
            
            self.peak_cpu = max(self.peak_cpu, current_cpu)
            self.peak_memory = max(self.peak_memory, current_memory)
    
    def get_metrics(self) -> LLMOperationMetrics:
        """Get operation metrics."""
        total_latency = (self.end_time - self.start_time) * 1000 if self.start_time and self.end_time else 0
        
        api_latency = 0
        if self.api_start_time and self.api_end_time:
            api_latency = (self.api_end_time - self.api_start_time) * 1000
        
        postprocessing = 0
        if self.postprocessing_start and self.end_time:
            postprocessing = (self.end_time - self.postprocessing_start) * 1000
        
        return LLMOperationMetrics(
            operation_id=self.operation_id,
            operation_type=self.operation_type,
            model=self.model,
            start_time=self.start_time or time.time(),
            end_time=self.end_time or time.time(),
            total_latency_ms=total_latency,
            api_latency_ms=api_latency,
            preprocessing_ms=self.preprocessing_time * 1000 if self.preprocessing_time else 0,
            postprocessing_ms=postprocessing,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cpu_percent=self.peak_cpu,
            memory_mb=self.peak_memory,
            success=self.success,
            error=self.error,
            output_quality_score=self.quality_score,
            input_size_bytes=self.input_size,
            output_size_bytes=self.output_size
        )