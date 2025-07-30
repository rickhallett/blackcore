"""Configuration models for the intelligence system."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    requests_per_minute: int = 50
    tokens_per_minute: int = 40000
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class GraphConfig:
    """Graph backend configuration."""
    backend: str = "networkx"
    connection_params: Dict[str, Any] = field(default_factory=dict)
    cache_enabled: bool = True
    cache_ttl: int = 3600


@dataclass
class CacheConfig:
    """Cache configuration."""
    backend: str = "memory"
    connection_params: Dict[str, Any] = field(default_factory=dict)
    max_size: int = 1000
    default_ttl: int = 3600
    redis_url: Optional[str] = None


@dataclass
class IntelligenceConfig:
    """Main configuration for intelligence system."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    # Analysis settings
    max_concurrent_analyses: int = 5
    default_confidence_threshold: float = 0.7
    
    # Investigation settings
    max_investigation_depth: int = 3
    evidence_retention_days: int = 90
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4