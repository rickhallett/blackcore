"""Query engine factory for creating specialized query executors."""

from typing import Dict, Any, Optional
from .engine import QueryEngine


class QueryEngineFactory:
    """Factory for creating query engine instances."""
    
    @staticmethod
    def create_structured_executor(config: Optional[Dict[str, Any]] = None) -> QueryEngine:
        """Create a structured query executor."""
        return QueryEngine(
            cache_dir=config.get("cache_dir", "blackcore/models/json") if config else "blackcore/models/json"
        )
    
    @staticmethod
    def create_graph_executor(config: Optional[Dict[str, Any]] = None) -> QueryEngine:
        """Create a graph query executor."""
        # For now, returns standard engine
        # TODO: Create specialized graph executor
        return QueryEngineFactory.create_structured_executor(config)
    
    @staticmethod 
    def create_semantic_executor(config: Optional[Dict[str, Any]] = None) -> QueryEngine:
        """Create a semantic query executor."""
        # For now, returns standard engine
        # TODO: Create specialized semantic executor with embeddings support
        return QueryEngineFactory.create_structured_executor(config)