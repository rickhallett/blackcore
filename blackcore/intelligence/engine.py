"""Analysis engine orchestration implementation."""

import asyncio
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict

from .interfaces import (
    IAnalysisStrategy,
    ILLMProvider,
    IGraphBackend,
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    ICache
)
from .cache import InMemoryCache

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """Orchestrates analysis strategies for intelligence processing."""
    
    def __init__(
        self,
        llm_provider: ILLMProvider,
        graph_backend: IGraphBackend,
        strategies: Optional[List[IAnalysisStrategy]] = None,
        enable_caching: bool = False,
        cache: Optional[ICache] = None,
        timeout_seconds: Optional[int] = None,
        collect_metrics: bool = False,
        pre_process_hook: Optional[Callable[[AnalysisRequest], AnalysisRequest]] = None,
        post_process_hook: Optional[Callable[[AnalysisResult], AnalysisResult]] = None
    ):
        """Initialize analysis engine.
        
        Args:
            llm_provider: LLM provider for analysis
            graph_backend: Graph backend for data storage
            strategies: List of analysis strategies
            enable_caching: Whether to cache analysis results
            cache: Cache implementation (uses InMemoryCache if not provided)
            timeout_seconds: Timeout for individual analyses
            collect_metrics: Whether to collect metrics
            pre_process_hook: Function to pre-process requests
            post_process_hook: Function to post-process results
        """
        self.llm_provider = llm_provider
        self.graph_backend = graph_backend
        self.strategies = strategies or []
        self.enable_caching = enable_caching
        self.cache = cache or InMemoryCache() if enable_caching else None
        self.timeout_seconds = timeout_seconds
        self.collect_metrics = collect_metrics
        self.pre_process_hook = pre_process_hook
        self.post_process_hook = post_process_hook
        
        # Metrics
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0,
            "requests_by_type": defaultdict(int),
            "errors": []
        }
    
    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Execute a single analysis request.
        
        Args:
            request: Analysis request to execute
            
        Returns:
            Analysis result
        """
        start_time = datetime.now()
        
        try:
            # Update metrics
            if self.collect_metrics:
                self._metrics["total_requests"] += 1
                self._metrics["requests_by_type"][request.type] += 1
            
            # Pre-process request
            if self.pre_process_hook:
                request = self.pre_process_hook(request)
            
            # Check cache
            if self.enable_caching and self.cache:
                cache_key = self._get_cache_key(request)
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for request: {request.type}")
                    result = AnalysisResult.from_dict(cached_result)
                    if self.post_process_hook:
                        result = self.post_process_hook(result)
                    return result
            
            # Find appropriate strategy
            strategy = self._find_strategy(request.type)
            if not strategy:
                error_msg = f"No strategy found for analysis type: {request.type}"
                logger.error(error_msg)
                return self._create_error_result(request, [error_msg], start_time)
            
            # Execute analysis with timeout if configured
            if self.timeout_seconds:
                try:
                    result = await asyncio.wait_for(
                        strategy.analyze(request, self.llm_provider, self.graph_backend),
                        timeout=self.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    error_msg = f"Analysis timed out after {self.timeout_seconds} seconds"
                    logger.error(error_msg)
                    return self._create_error_result(request, [error_msg], start_time)
            else:
                result = await strategy.analyze(request, self.llm_provider, self.graph_backend)
            
            # Update metrics
            if self.collect_metrics:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._metrics["total_duration_ms"] += duration_ms
                if result.success:
                    self._metrics["successful_requests"] += 1
                else:
                    self._metrics["failed_requests"] += 1
                    self._metrics["errors"].extend(result.errors)
            
            # Cache successful results
            if self.enable_caching and self.cache and result.success:
                cache_key = self._get_cache_key(request)
                await self.cache.set(cache_key, result.to_dict(), ttl=3600)
            
            # Post-process result
            if self.post_process_hook:
                result = self.post_process_hook(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            error_msg = f"Analysis failed: {str(e)}"
            
            if self.collect_metrics:
                self._metrics["failed_requests"] += 1
                self._metrics["errors"].append(error_msg)
            
            return self._create_error_result(request, [error_msg], start_time)
    
    async def analyze_batch(self, requests: List[AnalysisRequest]) -> List[AnalysisResult]:
        """Execute multiple analysis requests in parallel.
        
        Args:
            requests: List of analysis requests
            
        Returns:
            List of analysis results
        """
        # Create tasks for parallel execution
        tasks = [self.analyze(request) for request in requests]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = self._create_error_result(
                    requests[i],
                    [f"Batch execution failed: {str(result)}"],
                    datetime.now()
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results
    
    def add_strategy(self, strategy: IAnalysisStrategy) -> None:
        """Add a new analysis strategy.
        
        Args:
            strategy: Strategy to add
        """
        self.strategies.append(strategy)
        logger.info(f"Added strategy: {strategy.__class__.__name__}")
    
    def remove_strategy(self, strategy: IAnalysisStrategy) -> None:
        """Remove an analysis strategy.
        
        Args:
            strategy: Strategy to remove
        """
        if strategy in self.strategies:
            self.strategies.remove(strategy)
            logger.info(f"Removed strategy: {strategy.__class__.__name__}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics.
        
        Returns:
            Dictionary of metrics
        """
        if not self.collect_metrics:
            return {}
        
        metrics = self._metrics.copy()
        
        # Calculate average duration
        if metrics["total_requests"] > 0:
            metrics["average_duration_ms"] = (
                metrics["total_duration_ms"] / metrics["total_requests"]
            )
        else:
            metrics["average_duration_ms"] = 0
        
        # Convert defaultdict to regular dict
        metrics["requests_by_type"] = dict(metrics["requests_by_type"])
        
        return metrics
    
    def reset_metrics(self) -> None:
        """Reset engine metrics."""
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0,
            "requests_by_type": defaultdict(int),
            "errors": []
        }
    
    def _find_strategy(self, analysis_type: AnalysisType) -> Optional[IAnalysisStrategy]:
        """Find strategy that can handle the analysis type.
        
        Args:
            analysis_type: Type of analysis
            
        Returns:
            Strategy that can handle the type, or None
        """
        for strategy in self.strategies:
            if strategy.can_handle(analysis_type):
                return strategy
        return None
    
    def _get_cache_key(self, request: AnalysisRequest) -> str:
        """Generate cache key for request.
        
        Args:
            request: Analysis request
            
        Returns:
            Cache key
        """
        # Create deterministic key from request
        key_data = {
            "type": str(request.type),
            "parameters": request.parameters,
            "context": request.context,
            "constraints": request.constraints
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _create_error_result(
        self,
        request: AnalysisRequest,
        errors: List[str],
        start_time: datetime
    ) -> AnalysisResult:
        """Create error result.
        
        Args:
            request: Original request
            errors: List of error messages
            start_time: When analysis started
            
        Returns:
            Error analysis result
        """
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return AnalysisResult(
            request=request,
            success=False,
            data=None,
            errors=errors,
            duration_ms=duration_ms
        )