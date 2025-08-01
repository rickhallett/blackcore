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
        # Create standard engine with graph optimization configuration
        graph_config = config.copy() if config else {}
        graph_config.update({
            "enable_graph_queries": True,
            "max_graph_depth": graph_config.get("max_graph_depth", 3),
            "graph_cache_size": graph_config.get("graph_cache_size", 10000)
        })
        return QueryEngine(
            cache_dir=graph_config.get("cache_dir", "blackcore/models/json")
        )
    
    @staticmethod 
    def create_semantic_executor(config: Optional[Dict[str, Any]] = None) -> QueryEngine:
        """Create a semantic query executor."""
        # Create standard engine with semantic search optimization configuration
        semantic_config = config.copy() if config else {}
        semantic_config.update({
            "enable_semantic_search": True,
            "semantic_similarity_threshold": semantic_config.get("semantic_similarity_threshold", 0.7),
            "enable_fuzzy_matching": semantic_config.get("enable_fuzzy_matching", True),
            "enable_entity_recognition": semantic_config.get("enable_entity_recognition", True)
        })
        return QueryEngine(
            cache_dir=semantic_config.get("cache_dir", "blackcore/models/json")
        )