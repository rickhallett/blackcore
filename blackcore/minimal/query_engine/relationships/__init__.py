"""Relationship resolution module for the query engine."""

from .interfaces import (
    RelationshipDirection,
    TraversalStrategy,
    RelationshipInclude,
    RelationshipConfig,
    RelationshipPath,
    RelationshipGraph,
    DataLoader,
    RelationshipResolver,
    RelationshipCache,
    RelationshipAnalyzer
)

from .graph_resolver import GraphRelationshipResolver, VisitedTracker
from .cache import LRURelationshipCache, TwoLevelCache, CacheKeyBuilder

__all__ = [
    # Enums
    "RelationshipDirection",
    "TraversalStrategy",
    
    # Data classes
    "RelationshipInclude",
    "RelationshipConfig",
    "RelationshipPath",
    "RelationshipGraph",
    
    # Protocols
    "DataLoader",
    "RelationshipResolver",
    "RelationshipCache",
    "RelationshipAnalyzer",
    
    # Implementations
    "GraphRelationshipResolver",
    "VisitedTracker",
    "LRURelationshipCache",
    "TwoLevelCache",
    "CacheKeyBuilder"
]