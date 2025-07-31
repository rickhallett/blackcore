"""Test thread safety of RateLimiter."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from blackcore.minimal.notion_updater import RateLimiter


class TestRateLimiterThreadSafety:
    """Test suite for RateLimiter thread safety."""

    def test_single_threaded_rate_limiting(self):
        """Test that rate limiting works correctly in single-threaded use."""
        rate_limiter = RateLimiter(requests_per_second=10.0)  # 100ms between requests
        
        start_time = time.time()
        
        # Make 3 requests
        for i in range(3):
            rate_limiter.wait_if_needed()
        
        elapsed = time.time() - start_time
        
        # Should take at least 200ms for 3 requests at 10 req/s
        assert elapsed >= 0.2
        assert elapsed < 0.3  # Some tolerance

    def test_concurrent_requests_respect_rate_limit(self):
        """Test that concurrent requests properly respect rate limits."""
        rate_limiter = RateLimiter(requests_per_second=5.0)  # 200ms between requests
        request_times = []
        lock = threading.Lock()
        
        def make_request(request_id):
            rate_limiter.wait_if_needed()
            with lock:
                request_times.append(time.time())
            return request_id
        
        # Make 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]
        
        # Sort request times
        request_times.sort()
        
        # Check that requests are properly spaced
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i-1]
            # Each request should be at least 190ms apart (allowing 10ms tolerance)
            assert time_diff >= 0.19, f"Requests {i-1} and {i} too close: {time_diff}s"

    def test_no_race_condition_on_last_request_time(self):
        """Test that there's no race condition when updating last_request_time."""
        rate_limiter = RateLimiter(requests_per_second=100.0)  # Fast rate
        successful_requests = []
        lock = threading.Lock()
        
        def make_request(request_id):
            try:
                rate_limiter.wait_if_needed()
                with lock:
                    successful_requests.append(request_id)
                return True
            except Exception as e:
                print(f"Request {request_id} failed: {e}")
                return False
        
        # Make many concurrent requests
        num_requests = 50
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in futures]
        
        # All requests should succeed
        assert all(results)
        assert len(successful_requests) == num_requests

    def test_thread_safety_stress_test(self):
        """Stress test with many threads making rapid requests."""
        rate_limiter = RateLimiter(requests_per_second=50.0)  # 20ms between requests
        errors = []
        completed = []
        lock = threading.Lock()
        
        def worker(worker_id, num_requests):
            try:
                for i in range(num_requests):
                    rate_limiter.wait_if_needed()
                    with lock:
                        completed.append((worker_id, i))
            except Exception as e:
                with lock:
                    errors.append((worker_id, str(e)))
        
        # Start multiple workers
        workers = []
        num_workers = 10
        requests_per_worker = 5
        
        start_time = time.time()
        
        for i in range(num_workers):
            thread = threading.Thread(target=worker, args=(i, requests_per_worker))
            thread.start()
            workers.append(thread)
        
        # Wait for all workers
        for thread in workers:
            thread.join()
        
        elapsed = time.time() - start_time
        
        # Check no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Check all requests completed
        assert len(completed) == num_workers * requests_per_worker
        
        # Check timing - 50 requests at 50 req/s should take ~1 second
        assert elapsed >= 0.98  # Allow small tolerance
        assert elapsed < 1.5  # But not too slow

    def test_rate_limiter_initialization_thread_safe(self):
        """Test that RateLimiter can be safely initialized from multiple threads."""
        rate_limiters = []
        lock = threading.Lock()
        
        def create_rate_limiter():
            limiter = RateLimiter(requests_per_second=10.0)
            with lock:
                rate_limiters.append(limiter)
        
        # Create rate limiters concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_rate_limiter)
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        # All should be created successfully
        assert len(rate_limiters) == 10
        
        # Each should have correct configuration
        for limiter in rate_limiters:
            assert limiter.min_interval == 0.1  # 1.0 / 10.0

    def test_concurrent_different_rate_limiters(self):
        """Test that multiple rate limiter instances don't interfere with each other."""
        fast_limiter = RateLimiter(requests_per_second=100.0)
        slow_limiter = RateLimiter(requests_per_second=2.0)
        
        fast_times = []
        slow_times = []
        lock = threading.Lock()
        
        def fast_worker():
            for _ in range(5):
                fast_limiter.wait_if_needed()
                with lock:
                    fast_times.append(time.time())
        
        def slow_worker():
            for _ in range(3):
                slow_limiter.wait_if_needed()
                with lock:
                    slow_times.append(time.time())
        
        # Run both concurrently
        fast_thread = threading.Thread(target=fast_worker)
        slow_thread = threading.Thread(target=slow_worker)
        
        start_time = time.time()
        fast_thread.start()
        slow_thread.start()
        
        fast_thread.join()
        slow_thread.join()
        
        # Fast requests should complete quickly
        fast_duration = max(fast_times) - min(fast_times)
        assert fast_duration < 0.1  # 5 requests at 100 req/s
        
        # Slow requests should take longer
        slow_duration = max(slow_times) - min(slow_times)
        assert slow_duration >= 1.0  # 3 requests at 2 req/s = at least 1 second