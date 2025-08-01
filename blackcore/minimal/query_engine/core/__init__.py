"""Core query engine components."""

from .orchestrator import (
    QueryEngineOrchestrator,
    QueryEngineBuilder,
    DataLoader,
    FilterEngine,
    CacheManager,
    QueryOptimizer,
    ExportEngine
)

# Convenience exports
QueryEngine = QueryEngineOrchestrator
QueryBuilder = QueryEngineBuilder

# Factory functions
def create_query_engine(**kwargs) -> QueryEngineOrchestrator:
    """Create a query engine with the given configuration."""
    builder = QueryEngineBuilder()
    
    # Add components if provided
    if 'data_loader' in kwargs:
        builder.with_data_loader(kwargs['data_loader'])
    if 'filter_engine' in kwargs:
        builder.with_filter_engine(kwargs['filter_engine'])
    if 'nlp_parser' in kwargs:
        builder.with_nlp_parser(kwargs['nlp_parser'])
    if 'search_engine' in kwargs:
        builder.with_search_engine(kwargs['search_engine'])
    if 'relationship_resolver' in kwargs:
        builder.with_relationship_resolver(kwargs['relationship_resolver'])
    if 'cache_manager' in kwargs:
        builder.with_cache_manager(kwargs['cache_manager'])
    if 'query_optimizer' in kwargs:
        builder.with_query_optimizer(kwargs['query_optimizer'])
    if 'export_engine' in kwargs:
        builder.with_export_engine(kwargs['export_engine'])
    
    # Configuration flags
    if 'enable_cache' in kwargs:
        builder.with_cache_enabled(kwargs['enable_cache'])
    if 'enable_optimization' in kwargs:
        builder.with_optimization_enabled(kwargs['enable_optimization'])
    if 'enable_profiling' in kwargs:
        builder.with_profiling_enabled(kwargs['enable_profiling'])
    
    return builder.build()


# Quick access functions
async def quick_search(query: str, **kwargs) -> 'QueryResult':
    """Perform a quick search with minimal configuration."""
    engine = create_query_engine(**kwargs)
    return await engine.execute_natural_language_query(query)


def create_query(intent: str, **kwargs) -> 'StructuredQuery':
    """Create a structured query."""
    from ..models.shared import StructuredQuery
    return StructuredQuery(intent=intent, **kwargs)


__all__ = [
    # Main classes
    'QueryEngine',
    'QueryEngineOrchestrator',
    'QueryBuilder',
    'QueryEngineBuilder',
    
    # Factory functions
    'create_query_engine',
    'quick_search',
    'create_query',
    
    # Protocol exports
    'DataLoader',
    'FilterEngine',
    'CacheManager',
    'QueryOptimizer',
    'ExportEngine'
]