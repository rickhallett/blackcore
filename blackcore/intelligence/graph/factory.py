"""Factory for creating graph backend instances."""

from typing import Optional
from ..config import GraphConfig
from ..interfaces import IGraphBackend
from .networkx_backend import NetworkXBackend
from .sqlite_backend import SQLiteBackend


async def create_graph_backend(config: GraphConfig) -> IGraphBackend:
    """Create graph backend based on configuration.
    
    Args:
        config: Graph backend configuration
        
    Returns:
        Graph backend instance
        
    Raises:
        ValueError: If unknown backend type is specified
    """
    if config.backend == "networkx":
        return NetworkXBackend()
    
    elif config.backend == "sqlite":
        # Get database path from config
        db_path = ":memory:"  # Default to in-memory
        if config.connection_params:
            db_path = config.connection_params.get("db_path", ":memory:")
        
        backend = SQLiteBackend(db_path)
        await backend.initialize()
        return backend
    
    else:
        raise ValueError(f"Unknown graph backend: {config.backend}")