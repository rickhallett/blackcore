"""
Blackcore Query Engine - Advanced intelligence data querying and analysis.

This module provides a comprehensive query engine for intelligence data,
supporting natural language queries, graph traversal, relationship analysis,
and advanced analytics.
"""

from .engine import QueryEngine, QueryBuilder, QueryResult, create_query, quick_search
from .models import (
    QueryFilter, QueryOperator, SortOrder, ExportFormat,
    GraphQuery, SemanticQuery, TemporalQuery, StructuredQuery
)
# from .nlp import NaturalLanguageProcessor  # TODO: Implement
# from .graph import GraphAnalysisEngine  # TODO: Implement
# from .cache import QueryCacheManager  # TODO: Implement
# from .security import QuerySecurityFilter  # TODO: Implement
# from .export import ExportEngine  # TODO: Implement

__version__ = "1.0.0"

__all__ = [
    # Core classes
    "QueryEngine",
    "QueryBuilder",
    "QueryResult",
    "create_query",
    "quick_search",
    
    # Models
    "QueryFilter",
    "QueryOperator", 
    "SortOrder",
    "ExportFormat",
    "StructuredQuery",
    "GraphQuery",
    "SemanticQuery",
    "TemporalQuery",
    
    # Processing engines
    # "NaturalLanguageProcessor",  # TODO: Implement
    # "GraphAnalysisEngine",  # TODO: Implement
    # "QueryCacheManager",  # TODO: Implement
    # "QuerySecurityFilter",  # TODO: Implement
    # "ExportEngine",  # TODO: Implement
]