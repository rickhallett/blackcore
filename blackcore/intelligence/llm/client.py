"""LLM client implementation with caching and rate limiting."""

import asyncio
import hashlib
import json
import time
import logging
from collections import defaultdict
from typing import Dict, List, Any, Optional

from ..interfaces import ILLMProvider, ICache
from ..config import LLMConfig

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        requests_per_minute: int = 50,
        tokens_per_minute: int = 40000
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        
        # Initialize buckets at full capacity
        self.request_bucket = float(requests_per_minute)
        self.token_bucket = float(tokens_per_minute)
        
        # Track last update time
        self.last_update = time.time()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self, tokens: int):
        """Wait if rate limit would be exceeded."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Refill buckets based on elapsed time
            if elapsed > 0:
                # Calculate refill amounts
                minutes_elapsed = elapsed / 60.0
                request_refill = minutes_elapsed * self.requests_per_minute
                token_refill = minutes_elapsed * self.tokens_per_minute
                
                # Refill buckets (cap at max capacity)
                self.request_bucket = min(
                    self.request_bucket + request_refill,
                    self.requests_per_minute
                )
                self.token_bucket = min(
                    self.token_bucket + token_refill,
                    self.tokens_per_minute
                )
                
                self.last_update = now
            
            # Check if we need to wait
            wait_time = 0.0
            
            # Check request limit
            if self.request_bucket < 1:
                request_wait = (1 - self.request_bucket) / self.requests_per_minute * 60
                wait_time = max(wait_time, request_wait)
            
            # Check token limit
            if self.token_bucket < tokens:
                token_wait = (tokens - self.token_bucket) / self.tokens_per_minute * 60
                wait_time = max(wait_time, token_wait)
            
            # Wait if needed
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                
                # Update time and refill after waiting
                now = time.time()
                elapsed = wait_time
                minutes_elapsed = elapsed / 60.0
                
                self.request_bucket = min(
                    self.request_bucket + minutes_elapsed * self.requests_per_minute,
                    self.requests_per_minute
                )
                self.token_bucket = min(
                    self.token_bucket + minutes_elapsed * self.tokens_per_minute,
                    self.tokens_per_minute
                )
                self.last_update = now
            
            # Consume from buckets
            self.request_bucket -= 1
            self.token_bucket -= tokens


class LLMClient:
    """Unified LLM client with caching and rate limiting."""
    
    def __init__(
        self,
        provider: ILLMProvider,
        cache: Optional[ICache] = None,
        config: Optional[LLMConfig] = None
    ):
        self.provider = provider
        self.cache = cache
        self.config = config or LLMConfig()
        
        # Rate limiters per model
        self.rate_limiters = defaultdict(lambda: RateLimiter(
            requests_per_minute=self.config.requests_per_minute,
            tokens_per_minute=self.config.tokens_per_minute
        ))
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens": 0,
            "total_duration_ms": 0,
            "errors": 0
        }
    
    def _cache_key(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """Generate cache key for a request."""
        key_data = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "model": model or "default"
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        cache_ttl: Optional[int] = 3600,
        model: Optional[str] = None
    ) -> str:
        """Get completion with caching and rate limiting."""
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        # Check cache
        if self.cache and cache_ttl:
            cache_key = self._cache_key(prompt, system_prompt, temperature, model)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                self.metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cached
            self.metrics["cache_misses"] += 1
        
        # Estimate tokens and rate limit
        tokens = self.provider.estimate_tokens(prompt)
        if system_prompt:
            tokens += self.provider.estimate_tokens(system_prompt)
        
        rate_limiter = self.rate_limiters[model or "default"]
        await rate_limiter.wait_if_needed(tokens)
        
        try:
            # Make the actual request
            response = await self.provider.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            
            # Update metrics
            self.metrics["total_tokens"] += tokens
            
            # Cache the response
            if self.cache and cache_ttl:
                await self.cache.set(cache_key, response, ttl=cache_ttl)
            
            return response
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"LLM completion error: {e}")
            raise
        finally:
            # Update timing metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics["total_duration_ms"] += duration_ms
    
    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete with function calling (no caching for functions)."""
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        # Estimate tokens and rate limit
        tokens = self.provider.estimate_tokens(prompt)
        if system_prompt:
            tokens += self.provider.estimate_tokens(system_prompt)
        # Add tokens for function definitions
        tokens += len(json.dumps(functions)) // 4
        
        rate_limiter = self.rate_limiters[model or "default"]
        await rate_limiter.wait_if_needed(tokens)
        
        try:
            # Make the actual request
            response = await self.provider.complete_with_functions(
                prompt=prompt,
                functions=functions,
                system_prompt=system_prompt,
                temperature=temperature
            )
            
            # Update metrics
            self.metrics["total_tokens"] += tokens
            
            return response
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"LLM function completion error: {e}")
            raise
        finally:
            # Update timing metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics["total_duration_ms"] += duration_ms
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics."""
        metrics = self.metrics.copy()
        
        # Calculate derived metrics
        if metrics["total_requests"] > 0:
            metrics["cache_hit_rate"] = metrics["cache_hits"] / metrics["total_requests"]
            metrics["avg_duration_ms"] = metrics["total_duration_ms"] / metrics["total_requests"]
            metrics["avg_tokens_per_request"] = metrics["total_tokens"] / metrics["total_requests"]
        
        return metrics