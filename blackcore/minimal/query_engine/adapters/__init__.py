"""Adapter modules for integrating with different agent implementations."""

from .agent_a import (
    BlackcoreDataLoader,
    BlackcoreFilterEngine,
    create_blackcore_data_loader,
    create_blackcore_filter_engine,
    integrate_agent_a
)

from .agent_c import (
    SimpleCacheManager,
    SimpleQueryOptimizer,
    SimpleExportEngine,
    create_simple_cache_manager,
    create_simple_query_optimizer,
    create_simple_export_engine,
    integrate_agent_c
)

# Convenience function to integrate all available agents
def integrate_all_agents(**kwargs):
    """Integrate all available agent adapters."""
    config = {}
    
    # Agent A integration
    json_data_path = kwargs.get('json_data_path')
    config.update(integrate_agent_a(json_data_path))
    
    # Agent C integration
    config.update(integrate_agent_c(
        enable_disk_cache=kwargs.get('enable_disk_cache', False),
        cache_file=kwargs.get('cache_file'),
        max_cache_items=kwargs.get('max_cache_items', 1000),
        default_ttl=kwargs.get('default_ttl', 3600)
    ))
    
    return config


__all__ = [
    # Agent A
    'BlackcoreDataLoader',
    'BlackcoreFilterEngine',
    'create_blackcore_data_loader',
    'create_blackcore_filter_engine',
    'integrate_agent_a',
    
    # Agent C
    'SimpleCacheManager',
    'SimpleQueryOptimizer',
    'SimpleExportEngine',
    'create_simple_cache_manager',
    'create_simple_query_optimizer',
    'create_simple_export_engine',
    'integrate_agent_c',
    
    # Integration
    'integrate_all_agents'
]