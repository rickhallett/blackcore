"""High-level Query Engine API.

This module provides the main user-facing API for the query engine,
integrating all three agents through the orchestrator.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
import logging

from .core.orchestrator import QueryEngineOrchestrator, QueryEngineBuilder
from .models.shared import StructuredQuery, QueryResult, ExecutionContext
from .adapters import integrate_all_agents
from .search import SimpleTextSearchEngine
from .relationships import GraphRelationshipResolver
from .nlp import SimpleQueryParser

logger = logging.getLogger(__name__)


class QueryEngineAPI:
    """Main Query Engine interface for Blackcore intelligence data."""
    
    def __init__(self, 
                 json_data_path: Optional[str] = None,
                 enable_cache: bool = True,
                 enable_optimization: bool = True,
                 enable_profiling: bool = False,
                 **kwargs):
        """Initialize the query engine with default configuration."""
        
        # Set up logging if profiling is enabled
        if enable_profiling:
            logging.basicConfig(level=logging.INFO)
        
        # Integrate all available agents
        agent_config = integrate_all_agents(
            json_data_path=json_data_path,
            enable_disk_cache=kwargs.get('enable_disk_cache', False),
            cache_file=kwargs.get('cache_file'),
            max_cache_items=kwargs.get('max_cache_items', 1000),
            default_ttl=kwargs.get('default_ttl', 3600)
        )
        
        # Add Agent B components
        agent_config.update({
            'nlp_parser': SimpleQueryParser(),
            'search_engine': SimpleTextSearchEngine(),
            'relationship_resolver': GraphRelationshipResolver()
        })
        
        # Build orchestrator
        builder = (QueryEngineBuilder()
                   .with_cache_enabled(enable_cache)
                   .with_optimization_enabled(enable_optimization)
                   .with_profiling_enabled(enable_profiling))
        
        # Add all components
        for component_name, component in agent_config.items():
            if hasattr(builder, f'with_{component_name}'):
                getattr(builder, f'with_{component_name}')(component)
        
        self._orchestrator = builder.build()
        self._enable_profiling = enable_profiling
    
    async def search(self, query: str, **kwargs) -> QueryResult:
        """Perform a natural language search query."""
        user_context = {
            'user_id': kwargs.get('user_id'),
            'session_id': kwargs.get('session_id')
        }
        
        try:
            result = await self._orchestrator.execute_natural_language_query(
                query, user_context
            )
            
            if self._enable_profiling:
                logger.info(f"Search completed: {len(result.data)} results in {result.execution_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise
    
    def search_sync(self, query: str, **kwargs) -> QueryResult:
        """Synchronous version of search."""
        return asyncio.run(self.search(query, **kwargs))
    
    async def query(self, structured_query: Union[StructuredQuery, Dict[str, Any]], **kwargs) -> QueryResult:
        """Execute a structured query."""
        if isinstance(structured_query, dict):
            structured_query = StructuredQuery(**structured_query)
        
        context = ExecutionContext(
            query=structured_query,
            user_id=kwargs.get('user_id'),
            session_id=kwargs.get('session_id'),
            timeout_ms=kwargs.get('timeout_ms', 30000),
            enable_cache=kwargs.get('enable_cache', True),
            enable_optimization=kwargs.get('enable_optimization', True),
            enable_profiling=kwargs.get('enable_profiling', self._enable_profiling)
        )
        
        try:
            result = await self._orchestrator.execute_structured_query(
                structured_query, context
            )
            
            if self._enable_profiling:
                logger.info(f"Query completed: {len(result.data)} results in {result.execution_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def query_sync(self, structured_query: Union[StructuredQuery, Dict[str, Any]], **kwargs) -> QueryResult:
        """Synchronous version of query."""
        return asyncio.run(self.query(structured_query, **kwargs))
    
    async def export(self, result: QueryResult, format: str = 'json', **kwargs) -> Union[bytes, str]:
        """Export query results in the specified format."""
        try:
            return await self._orchestrator.export_results(result, format, kwargs)
        except Exception as e:
            logger.error(f"Export failed for format '{format}': {e}")
            raise
    
    def export_sync(self, result: QueryResult, format: str = 'json', **kwargs) -> Union[bytes, str]:
        """Synchronous version of export."""
        return asyncio.run(self.export(result, format, **kwargs))
    
    def get_available_databases(self) -> List[str]:
        """Get list of available databases."""
        if hasattr(self._orchestrator.data_loader, 'get_available_databases'):
            return self._orchestrator.data_loader.get_available_databases()
        return []
    
    def get_supported_export_formats(self) -> List[str]:
        """Get list of supported export formats."""
        if hasattr(self._orchestrator.export_engine, 'get_supported_formats'):
            return self._orchestrator.export_engine.get_supported_formats()
        return ['json', 'csv', 'txt', 'tsv']
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine performance statistics."""
        return self._orchestrator.get_statistics()
    
    def clear_cache(self, tags: Optional[List[str]] = None):
        """Clear cache entries."""
        if hasattr(self._orchestrator.cache_manager, 'clear_cache'):
            self._orchestrator.cache_manager.clear_cache(tags)


class APIQueryBuilder:
    """Builder for constructing structured queries."""
    
    def __init__(self):
        self._query_data = {
            'intent': 'search',
            'entities': [],
            'filters': [],
            'sort_criteria': [],
            'include_relationships': [],
            'aggregations': [],
            'group_by': []
        }
    
    def intent(self, intent: str) -> 'APIQueryBuilder':
        """Set query intent."""
        self._query_data['intent'] = intent
        return self
    
    def entities(self, *entities: str) -> 'APIQueryBuilder':
        """Add entities to search."""
        self._query_data['entities'].extend(entities)
        return self
    
    def filter(self, field: str, operator: str, value: Any) -> 'APIQueryBuilder':
        """Add a filter condition."""
        from .models import QueryFilter, QueryOperator
        
        # Convert string operator to enum
        if isinstance(operator, str):
            operator = QueryOperator(operator.upper())
        
        filter_obj = QueryFilter(field=field, operator=operator, value=value)
        self._query_data['filters'].append(filter_obj)
        return self
    
    def equals(self, field: str, value: Any) -> 'APIQueryBuilder':
        """Add equals filter."""
        return self.filter(field, 'EQUALS', value)
    
    def contains(self, field: str, value: str) -> 'APIQueryBuilder':
        """Add contains filter."""
        return self.filter(field, 'CONTAINS', value)
    
    def greater_than(self, field: str, value: Any) -> 'APIQueryBuilder':
        """Add greater than filter."""
        return self.filter(field, 'GT', value)
    
    def less_than(self, field: str, value: Any) -> 'APIQueryBuilder':
        """Add less than filter."""
        return self.filter(field, 'LT', value)
    
    def in_list(self, field: str, values: List[Any]) -> 'APIQueryBuilder':
        """Add in list filter."""
        return self.filter(field, 'IN', values)
    
    def sort(self, field: str, direction: str = 'asc') -> 'APIQueryBuilder':
        """Add sort criteria."""
        self._query_data['sort_criteria'].append((field, direction))
        return self
    
    def sort_asc(self, field: str) -> 'APIQueryBuilder':
        """Add ascending sort."""
        return self.sort(field, 'asc')
    
    def sort_desc(self, field: str) -> 'APIQueryBuilder':
        """Add descending sort."""
        return self.sort(field, 'desc')
    
    def limit(self, limit: int) -> 'APIQueryBuilder':
        """Set result limit."""
        self._query_data['limit'] = limit
        return self
    
    def offset(self, offset: int) -> 'APIQueryBuilder':
        """Set result offset."""
        self._query_data['offset'] = offset
        return self
    
    def include_relationships(self, *relationships: str) -> 'APIQueryBuilder':
        """Include specific relationships."""
        self._query_data['include_relationships'].extend(relationships)
        return self
    
    def relationship_depth(self, depth: int) -> 'APIQueryBuilder':
        """Set relationship traversal depth."""
        self._query_data['relationship_depth'] = depth
        return self
    
    def aggregate(self, field: str, function: str, alias: Optional[str] = None) -> 'APIQueryBuilder':
        """Add aggregation."""
        agg = {'field': field, 'function': function}
        if alias:
            agg['alias'] = alias
        self._query_data['aggregations'].append(agg)
        return self
    
    def count(self, field: str = '*', alias: Optional[str] = None) -> 'APIQueryBuilder':
        """Add count aggregation."""
        return self.aggregate(field, 'count', alias)
    
    def sum(self, field: str, alias: Optional[str] = None) -> 'APIQueryBuilder':
        """Add sum aggregation."""
        return self.aggregate(field, 'sum', alias)
    
    def avg(self, field: str, alias: Optional[str] = None) -> 'APIQueryBuilder':
        """Add average aggregation."""
        return self.aggregate(field, 'avg', alias)
    
    def group_by(self, *fields: str) -> 'APIQueryBuilder':
        """Add group by fields."""
        self._query_data['group_by'].extend(fields)
        return self
    
    def build(self) -> StructuredQuery:
        """Build the structured query."""
        return StructuredQuery(**self._query_data)


# Convenience functions
def create_query_engine_api(**kwargs) -> QueryEngineAPI:
    """Create a query engine with the given configuration."""
    return QueryEngineAPI(**kwargs)


async def quick_search_api(query: str, **kwargs) -> QueryResult:
    """Perform a quick search without creating a persistent engine."""
    engine = create_query_engine_api(**kwargs)
    return await engine.search(query)


def create_query_api(intent: str = 'search') -> APIQueryBuilder:
    """Create a query builder."""
    return APIQueryBuilder().intent(intent)


# Synchronous convenience functions
def quick_search_sync_api(query: str, **kwargs) -> QueryResult:
    """Synchronous version of quick_search."""
    return asyncio.run(quick_search_api(query, **kwargs))


__all__ = [
    'QueryEngineAPI',
    'APIQueryBuilder',
    'create_query_engine_api',
    'quick_search_api',
    'quick_search_sync_api',
    'create_query_api'
]