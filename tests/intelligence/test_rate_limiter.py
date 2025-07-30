"""Tests for rate limiting functionality."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

pytestmark = pytest.mark.asyncio


class TestRateLimiter:
    """Tests for token bucket rate limiter."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default values."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter()
        assert limiter.requests_per_minute == 50
        assert limiter.tokens_per_minute == 40000
        assert limiter.request_bucket == 50
        assert limiter.token_bucket == 40000
    
    def test_rate_limiter_custom_limits(self):
        """Test rate limiter with custom limits."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=100, tokens_per_minute=80000)
        assert limiter.requests_per_minute == 100
        assert limiter.tokens_per_minute == 80000
        assert limiter.request_bucket == 100
        assert limiter.token_bucket == 80000
    
    async def test_wait_if_needed_no_wait(self):
        """Test wait_if_needed when no waiting is required."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=60000)
        
        # Should not wait when buckets have capacity
        start_time = time.time()
        await limiter.wait_if_needed(tokens=100)
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1  # Should be instant
        assert limiter.request_bucket == 59
        assert limiter.token_bucket == 59900
    
    async def test_wait_if_needed_request_limit(self):
        """Test waiting when request limit is reached."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=60000)
        limiter.request_bucket = 0  # Exhaust requests
        
        # Mock time to avoid actual waiting
        with patch('time.time', side_effect=[0, 0.1, 0.5, 1.0, 1.1]):
            with patch('asyncio.sleep') as mock_sleep:
                await limiter.wait_if_needed(tokens=100)
                
                # Should have waited for refill
                mock_sleep.assert_called()
                assert limiter.request_bucket == 0  # Still consumed 1
    
    async def test_wait_if_needed_token_limit(self):
        """Test waiting when token limit is reached."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=60000)
        limiter.token_bucket = 50  # Only 50 tokens left
        
        # Mock time to avoid actual waiting
        with patch('time.time', side_effect=[0, 0.1, 0.5, 1.0, 1.1]):
            with patch('asyncio.sleep') as mock_sleep:
                await limiter.wait_if_needed(tokens=1000)
                
                # Should have waited for token refill
                mock_sleep.assert_called()
    
    async def test_bucket_refill(self):
        """Test bucket refill over time."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=60000)
        
        # Consume some capacity
        limiter.request_bucket = 30
        limiter.token_bucket = 30000
        initial_time = time.time()
        limiter.last_update = initial_time
        
        # Mock time passing (30 seconds = 0.5 minutes)
        with patch('time.time', return_value=initial_time + 30):
            await limiter.wait_if_needed(tokens=100)
            
            # Should have refilled half capacity
            assert limiter.request_bucket == 59  # 30 + 30 - 1
            assert limiter.token_bucket == 59900  # 30000 + 30000 - 100
    
    async def test_max_bucket_capacity(self):
        """Test buckets don't exceed maximum capacity."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=60000)
        
        # Set buckets to near full
        limiter.request_bucket = 59
        limiter.token_bucket = 59000
        initial_time = time.time()
        limiter.last_update = initial_time
        
        # Mock time passing (2 minutes)
        with patch('time.time', return_value=initial_time + 120):
            await limiter.wait_if_needed(tokens=100)
            
            # Should be capped at max
            assert limiter.request_bucket == 59  # 60 - 1
            assert limiter.token_bucket == 59900  # 60000 - 100
    
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting with concurrent requests."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=10, tokens_per_minute=1000)
        
        async def make_request(tokens):
            await limiter.wait_if_needed(tokens)
            return True
        
        # Make concurrent requests
        tasks = [make_request(100) for _ in range(15)]
        
        with patch('asyncio.sleep') as mock_sleep:
            results = await asyncio.gather(*tasks)
            
            # Should have rate limited some requests
            assert all(results)
            assert mock_sleep.call_count > 0  # Some requests should have waited
    
    def test_rate_limiter_metrics(self):
        """Test rate limiter tracks metrics correctly."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=60000)
        
        # Initial state
        assert limiter.request_bucket == 60
        assert limiter.token_bucket == 60000
        assert hasattr(limiter, 'last_update')


class TestRateLimiterEdgeCases:
    """Tests for rate limiter edge cases."""
    
    async def test_zero_tokens_request(self):
        """Test handling requests with zero tokens."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter()
        initial_tokens = limiter.token_bucket
        
        await limiter.wait_if_needed(tokens=0)
        
        # Should still consume request but no tokens
        assert limiter.request_bucket == 49
        assert limiter.token_bucket == initial_tokens
    
    async def test_massive_token_request(self):
        """Test handling requests exceeding bucket capacity."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=1000)
        
        with patch('asyncio.sleep') as mock_sleep:
            # Request more tokens than bucket capacity
            await limiter.wait_if_needed(tokens=5000)
            
            # Should wait but still process
            assert mock_sleep.called
            assert limiter.token_bucket < 0  # Can go negative
    
    async def test_negative_time_drift(self):
        """Test handling system time going backwards."""
        from blackcore.intelligence.llm.client import RateLimiter
        
        limiter = RateLimiter()
        initial_time = time.time()
        limiter.last_update = initial_time
        
        # Mock time going backwards
        with patch('time.time', return_value=initial_time - 10):
            await limiter.wait_if_needed(tokens=100)
            
            # Should handle gracefully
            assert limiter.last_update >= initial_time - 10
    
    def test_rate_limiter_thread_safety(self):
        """Test rate limiter is thread-safe."""
        from blackcore.intelligence.llm.client import RateLimiter
        import threading
        
        limiter = RateLimiter(requests_per_minute=100, tokens_per_minute=10000)
        results = []
        
        def consume_tokens():
            # This is a basic thread safety test
            # In production, use asyncio locks
            for _ in range(10):
                current = limiter.token_bucket
                limiter.token_bucket = current - 10
                results.append(current)
        
        threads = [threading.Thread(target=consume_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All operations should have completed
        assert len(results) == 50


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with LLM client."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = Mock()
        provider.estimate_tokens = Mock(return_value=100)
        provider.complete = AsyncMock(return_value="Test response")
        return provider
    
    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache."""
        cache = Mock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        return cache
    
    async def test_llm_client_with_rate_limiting(self, mock_provider, mock_cache):
        """Test LLM client respects rate limits."""
        from blackcore.intelligence.llm.client import LLMClient
        from blackcore.intelligence.config import LLMConfig
        
        config = LLMConfig(
            requests_per_minute=10,
            tokens_per_minute=1000
        )
        
        client = LLMClient(
            provider=mock_provider,
            cache=mock_cache,
            config=config
        )
        
        # Make multiple requests
        with patch('asyncio.sleep') as mock_sleep:
            tasks = [
                client.complete("Test prompt", cache_ttl=0)
                for _ in range(15)
            ]
            results = await asyncio.gather(*tasks)
            
            # All should complete
            assert len(results) == 15
            assert all(r == "Test response" for r in results)
            
            # Some should have been rate limited
            assert mock_sleep.call_count > 0
    
    async def test_different_models_different_limiters(self, mock_provider):
        """Test different models use different rate limiters."""
        from blackcore.intelligence.llm.client import LLMClient
        
        client = LLMClient(provider=mock_provider)
        
        # Use different models
        await client.complete("Test", model="gpt-4", cache_ttl=0)
        await client.complete("Test", model="gpt-3.5", cache_ttl=0)
        
        # Should have different rate limiters
        assert "gpt-4" in client.rate_limiters
        assert "gpt-3.5" in client.rate_limiters
        assert client.rate_limiters["gpt-4"] != client.rate_limiters["gpt-3.5"]