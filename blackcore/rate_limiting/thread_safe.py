"""Thread-safe rate limiter implementation."""

import threading
import time
import os
from typing import Optional
from datetime import datetime

try:
    import redis
except ImportError:
    redis = None


class ThreadSafeRateLimiter:
    """Thread-safe rate limiter with optional distributed support via Redis."""

    def __init__(
        self,
        requests_per_second: float = 3.0,
        burst_size: int = 5,
        redis_client: Optional["redis.Redis"] = None,
        redis_key_prefix: str = "notion:rate_limit",
    ):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum sustained request rate
            burst_size: Maximum burst size for token bucket
            redis_client: Optional Redis client for distributed rate limiting
            redis_key_prefix: Prefix for Redis keys
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.burst_size = burst_size
        self.redis_client = redis_client
        self.redis_key_prefix = redis_key_prefix

        # Local rate limiting state
        self._local_lock = threading.RLock()
        self._last_request_time = 0.0
        self._tokens = float(burst_size)
        self._last_refill_time = time.time()

        # Instance ID for distributed rate limiting
        self.instance_id = f"{os.getpid()}:{threading.get_ident()}"

    def wait_if_needed(self) -> float:
        """Wait if necessary to maintain rate limit.

        Returns:
            Time waited in seconds
        """
        if self.redis_client and redis is not None:
            return self._distributed_wait()
        else:
            return self._local_wait()

    def _local_wait(self) -> float:
        """Thread-safe local rate limiting using token bucket algorithm."""
        wait_time = 0.0

        with self._local_lock:
            current_time = time.time()

            # Refill tokens based on time elapsed
            time_since_refill = current_time - self._last_refill_time
            tokens_to_add = time_since_refill * self.requests_per_second
            self._tokens = min(self.burst_size, self._tokens + tokens_to_add)
            self._last_refill_time = current_time

            # Check if we have tokens available
            if self._tokens >= 1.0:
                # Consume a token
                self._tokens -= 1.0
                self._last_request_time = current_time
            else:
                # Calculate wait time
                tokens_needed = 1.0 - self._tokens
                wait_time = tokens_needed / self.requests_per_second

                # Wait
                time.sleep(wait_time)

                # Update state after waiting
                current_time = time.time()
                self._tokens = 0.0
                self._last_request_time = current_time
                self._last_refill_time = current_time

        return wait_time

    def _distributed_wait(self) -> float:
        """Distributed rate limiting using Redis sliding window."""
        wait_time = 0.0
        key = f"{self.redis_key_prefix}:sliding_window"
        current_time = time.time()
        window_start = current_time - 1.0  # 1 second window

        # Lua script for atomic rate limit check
        lua_script = """
        local key = KEYS[1]
        local current_time = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        local instance_id = ARGV[4]
        
        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        
        -- Count current requests in window
        local current_count = redis.call('ZCOUNT', key, window_start, current_time)
        
        if current_count < max_requests then
            -- Add this request
            redis.call('ZADD', key, current_time, instance_id .. ':' .. current_time)
            redis.call('EXPIRE', key, 2)
            return 0
        else
            -- Rate limit exceeded
            return 1
        end
        """

        try:
            # Try to acquire slot
            result = self.redis_client.eval(
                lua_script,
                1,
                key,
                str(current_time),
                str(window_start),
                str(self.requests_per_second),
                self.instance_id,
            )

            if result == 1:
                # Rate limit exceeded, calculate wait time
                # Get the oldest request time in the window
                oldest_requests = self.redis_client.zrange(key, 0, 0, withscores=True)

                if oldest_requests:
                    oldest_time = oldest_requests[0][1]
                    # Wait until the oldest request expires from the window
                    wait_time = (oldest_time + 1.0) - current_time
                    if wait_time > 0:
                        time.sleep(wait_time)

                    # Try again after waiting
                    self._distributed_wait()

        except Exception as e:
            # Fall back to local rate limiting on Redis error
            from ..security.audit import AuditLogger

            audit = AuditLogger()
            audit.log_error("rate_limit_redis_error", str(e), context={"fallback": "local"})
            return self._local_wait()

        return wait_time

    def get_current_rate(self) -> dict:
        """Get current rate limiting statistics.

        Returns:
            Dictionary with rate limit stats
        """
        with self._local_lock:
            current_time = time.time()

            # Update tokens
            time_since_refill = current_time - self._last_refill_time
            tokens_to_add = time_since_refill * self.requests_per_second
            current_tokens = min(self.burst_size, self._tokens + tokens_to_add)

            stats = {
                "requests_per_second": self.requests_per_second,
                "burst_size": self.burst_size,
                "available_tokens": current_tokens,
                "distributed": self.redis_client is not None,
                "instance_id": self.instance_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if self.redis_client and redis is not None:
                try:
                    key = f"{self.redis_key_prefix}:sliding_window"
                    current_count = self.redis_client.zcount(key, time.time() - 1.0, time.time())
                    stats["current_window_requests"] = current_count
                except Exception:
                    pass

            return stats

    def reset(self) -> None:
        """Reset rate limiter state."""
        with self._local_lock:
            self._tokens = float(self.burst_size)
            self._last_request_time = 0.0
            self._last_refill_time = time.time()

        if self.redis_client and redis is not None:
            try:
                key = f"{self.redis_key_prefix}:sliding_window"
                self.redis_client.delete(key)
            except Exception:
                pass

    def update_rate(self, requests_per_second: float, burst_size: Optional[int] = None) -> None:
        """Update rate limit parameters dynamically.

        Args:
            requests_per_second: New request rate
            burst_size: New burst size (optional)
        """
        with self._local_lock:
            self.requests_per_second = requests_per_second
            self.min_interval = 1.0 / requests_per_second

            if burst_size is not None:
                # Adjust current tokens proportionally
                token_ratio = self._tokens / self.burst_size
                self.burst_size = burst_size
                self._tokens = token_ratio * burst_size

    def __enter__(self):
        """Context manager entry."""
        self.wait_if_needed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
