"""Cache factory for creating cache instances."""

from typing import Optional
from ..config import CacheConfig
from ..interfaces import ICache
from .memory import InMemoryCache
from .redis import RedisCache


def create_cache(config: CacheConfig) -> ICache:
    """Create cache instance based on configuration.
    
    Args:
        config: Cache configuration
        
    Returns:
        Cache instance
        
    Raises:
        ValueError: If unknown cache backend is specified
    """
    if config.backend == "memory":
        return InMemoryCache(max_size=config.max_size)
    
    elif config.backend == "redis":
        # Extract Redis-specific parameters
        redis_params = config.connection_params or {}
        return RedisCache(**redis_params)
    
    else:
        raise ValueError(f"Unknown cache backend: {config.backend}")