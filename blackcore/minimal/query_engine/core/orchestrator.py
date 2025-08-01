"""Query Engine Orchestrator - Main coordinator for all agents.

This module implements the central orchestrator that coordinates between:
- Agent A: Data loading and filtering
- Agent B: Search and relationship resolution  
- Agent C: Performance optimization and caching
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Union, Protocol
from dataclasses import dataclass, field
import logging

from ..models.shared import (
    StructuredQuery,
    QueryResult,
    QueryStatistics,
    ExecutionContext,
    QueryStatus,
    OptimizedQuery,
    CachedResult
)
from ..search.interfaces import TextSearchEngine, SearchResult
from ..relationships.interfaces import RelationshipResolver
from ..nlp.interfaces import QueryParser


logger = logging.getLogger(__name__)


class DataLoader(Protocol):
    """Protocol for Agent A's data loader."""
    def load_database(self, database_name: str) -> List[Dict[str, Any]]: ...
    def get_available_databases(self) -> List[str]: ...
    def refresh_cache(self, database_name: Optional[str] = None) -> None: ...


class FilterEngine(Protocol):
    """Protocol for Agent A's filter engine."""
    def apply_filters(self, data: List[Dict[str, Any]], filters: List['QueryFilter']) -> List[Dict[str, Any]]: ...


class CacheManager(Protocol):
    """Protocol for Agent C's cache manager."""
    def get_cached_result(self, query_hash: str, max_age: Optional[int] = None) -> Optional[CachedResult]: ...
    def cache_result(self, query_hash: str, result: Any, ttl: int = 3600, tags: List[str] = None) -> None: ...
    def get_statistics(self) -> Dict[str, Any]: ...


class QueryOptimizer(Protocol):
    """Protocol for Agent C's query optimizer."""
    def optimize_query(self, query: StructuredQuery, statistics: QueryStatistics) -> OptimizedQuery: ...
    def generate_execution_plan(self, query: StructuredQuery) -> Dict[str, Any]: ...


class ExportEngine(Protocol):
    """Protocol for Agent C's export engine."""
    def export(self, result: QueryResult, format: str, options: Dict[str, Any] = None) -> Union[bytes, str]: ...
    def get_supported_formats(self) -> List[str]: ...


class QueryEngineOrchestrator:
    """Main orchestrator that coordinates all three agents."""
    
    def __init__(
        self,
        # Agent A components
        data_loader: Optional[DataLoader] = None,
        filter_engine: Optional[FilterEngine] = None,
        
        # Agent B components  
        nlp_parser: Optional[QueryParser] = None,
        search_engine: Optional[TextSearchEngine] = None,
        relationship_resolver: Optional[RelationshipResolver] = None,
        
        # Agent C components
        cache_manager: Optional[CacheManager] = None,
        query_optimizer: Optional[QueryOptimizer] = None,
        export_engine: Optional[ExportEngine] = None,
        
        # Configuration
        enable_cache: bool = True,
        enable_optimization: bool = True,
        enable_profiling: bool = True
    ):
        """Initialize orchestrator with all agent components."""
        # Agent A
        self.data_loader = data_loader
        self.filter_engine = filter_engine
        
        # Agent B
        self.nlp_parser = nlp_parser
        self.search_engine = search_engine
        self.relationship_resolver = relationship_resolver
        
        # Agent C
        self.cache_manager = cache_manager
        self.query_optimizer = query_optimizer
        self.export_engine = export_engine
        
        # Configuration
        self.enable_cache = enable_cache
        self.enable_optimization = enable_optimization
        self.enable_profiling = enable_profiling
        
        # Statistics
        self._query_count = 0
        self._total_execution_time = 0.0
        
    async def execute_natural_language_query(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute a natural language query through the full pipeline."""
        start_time = time.time()
        
        # Create execution context
        context = ExecutionContext(
            query=None,  # Will be set after parsing
            user_id=user_context.get('user_id') if user_context else None,
            session_id=user_context.get('session_id') if user_context else None,
            enable_cache=self.enable_cache,
            enable_optimization=self.enable_optimization,
            enable_profiling=self.enable_profiling
        )
        
        try:
            # Step 1: Parse natural language query (Agent B)
            parsed_query = await self._parse_query(query, context)
            context.query = StructuredQuery.from_parsed_query(parsed_query)
            
            # Step 2: Execute structured query
            result = await self.execute_structured_query(context.query, context)
            
            return result
            
        finally:
            # Track statistics
            execution_time = (time.time() - start_time) * 1000
            self._query_count += 1
            self._total_execution_time += execution_time
            
            if self.enable_profiling:
                logger.info(
                    f"Query executed in {execution_time:.2f}ms "
                    f"(bottleneck: {context.statistics.bottleneck()})"
                )
    
    async def execute_structured_query(
        self,
        query: StructuredQuery,
        context: Optional[ExecutionContext] = None
    ) -> QueryResult:
        """Execute a structured query through the pipeline."""
        if context is None:
            context = ExecutionContext(query=query)
        
        # Update status
        context.query = query
        status = QueryStatus.PENDING
        
        try:
            # Step 1: Check cache (Agent C)
            if self.enable_cache and self.cache_manager:
                cached_result = await self._check_cache(query, context)
                if cached_result:
                    return cached_result
            
            # Step 2: Optimize query (Agent C)
            if self.enable_optimization and self.query_optimizer:
                query = await self._optimize_query(query, context)
            
            # Step 3: Load data (Agent A)
            status = QueryStatus.LOADING
            data = await self._load_data(query, context)
            context.raw_data = data
            
            # Step 4: Apply filters (Agent A)
            status = QueryStatus.EXECUTING
            filtered_data = await self._apply_filters(data, query, context)
            context.filtered_data = filtered_data
            
            # Step 5: Search if needed (Agent B)
            if query.source_query and self.search_engine:
                search_results = await self._apply_search(filtered_data, query, context)
                context.search_results = search_results
                # Update filtered data based on search results
                filtered_data = self._merge_search_results(filtered_data, search_results)
            
            # Step 6: Resolve relationships (Agent B)
            if query.include_relationships and self.relationship_resolver:
                relationship_graph = await self._resolve_relationships(
                    filtered_data, query, context
                )
            else:
                relationship_graph = None
            
            # Step 7: Sort and paginate
            final_data = await self._sort_and_paginate(filtered_data, query, context)
            
            # Step 8: Build result
            result = QueryResult(
                data=final_data,
                total_count=len(filtered_data),
                query_id=query.query_id,
                execution_time_ms=context.statistics.total_time_ms,
                cache_hit=False,
                search_results=context.search_results,
                relationship_graph=relationship_graph
            )
            
            # Step 9: Cache result (Agent C)
            if self.enable_cache and self.cache_manager:
                status = QueryStatus.CACHING
                await self._cache_result(query, result, context)
            
            status = QueryStatus.COMPLETED
            return result
            
        except Exception as e:
            status = QueryStatus.FAILED
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def _parse_query(self, query: str, context: ExecutionContext) -> 'ParsedQuery':
        """Parse natural language query using Agent B's NLP parser."""
        start_time = time.time()
        
        if not self.nlp_parser:
            raise ValueError("NLP parser not configured")
        
        parsed = self.nlp_parser.parse(query)
        
        if self.enable_profiling:
            context.track_time('parse', (time.time() - start_time) * 1000)
        
        return parsed
    
    async def _check_cache(
        self, 
        query: StructuredQuery, 
        context: ExecutionContext
    ) -> Optional[QueryResult]:
        """Check cache for existing results."""
        start_time = time.time()
        
        # Generate cache key from query
        cache_key = self._generate_cache_key(query)
        
        cached = self.cache_manager.get_cached_result(
            cache_key, 
            max_age=context.cache_ttl if context.enable_cache else None
        )
        
        if self.enable_profiling:
            context.track_time('cache_check', (time.time() - start_time) * 1000)
        
        if cached and not cached.is_expired():
            context.statistics.cache_hits += 1
            return cached.result
        
        context.statistics.cache_misses += 1
        return None
    
    async def _optimize_query(
        self,
        query: StructuredQuery,
        context: ExecutionContext
    ) -> StructuredQuery:
        """Optimize query using Agent C's optimizer."""
        start_time = time.time()
        
        optimized = self.query_optimizer.optimize_query(query, context.statistics)
        
        if self.enable_profiling:
            context.track_time('optimize', (time.time() - start_time) * 1000)
        
        # Apply optimized components
        if optimized.reordered_filters:
            query.filters = optimized.reordered_filters
        
        return query
    
    async def _load_data(
        self,
        query: StructuredQuery,
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Load data using Agent A's data loader."""
        start_time = time.time()
        
        if not self.data_loader:
            raise ValueError("Data loader not configured")
        
        # Determine databases to load based on entities
        databases = self._determine_databases(query.entities)
        
        all_data = []
        for database in databases:
            data = self.data_loader.load_database(database)
            all_data.extend(data)
        
        if self.enable_profiling:
            context.track_time('load', (time.time() - start_time) * 1000)
            context.statistics.rows_scanned = len(all_data)
        
        return all_data
    
    async def _apply_filters(
        self,
        data: List[Dict[str, Any]],
        query: StructuredQuery,
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Apply filters using Agent A's filter engine."""
        start_time = time.time()
        
        if not query.filters or not self.filter_engine:
            return data
        
        filtered = self.filter_engine.apply_filters(data, query.filters)
        
        if self.enable_profiling:
            context.track_time('filter', (time.time() - start_time) * 1000)
        
        return filtered
    
    async def _apply_search(
        self,
        data: List[Dict[str, Any]],
        query: StructuredQuery,
        context: ExecutionContext
    ) -> List[SearchResult]:
        """Apply text search using Agent B's search engine."""
        start_time = time.time()
        
        if not self.search_engine:
            return []
        
        # Convert data to searchable documents
        documents = [
            {
                'id': item.get('id', str(i)),
                'content': self._extract_searchable_content(item),
                'metadata': item
            }
            for i, item in enumerate(data)
        ]
        
        # Perform search
        results = self.search_engine.search(
            query.source_query,
            documents,
            limit=query.limit
        )
        
        if self.enable_profiling:
            context.track_time('search', (time.time() - start_time) * 1000)
        
        return results
    
    async def _resolve_relationships(
        self,
        data: List[Dict[str, Any]],
        query: StructuredQuery,
        context: ExecutionContext
    ) -> 'RelationshipGraph':
        """Resolve relationships using Agent B's resolver."""
        start_time = time.time()
        
        if not self.relationship_resolver:
            return None
        
        # Build graph from data
        graph = self.relationship_resolver.build_graph(data)
        
        # Resolve requested relationships
        for relationship_type in query.include_relationships:
            graph = self.relationship_resolver.resolve(
                graph,
                relationship_type,
                max_depth=query.relationship_depth
            )
        
        if self.enable_profiling:
            context.track_time('relationship', (time.time() - start_time) * 1000)
            context.statistics.relationships_resolved = len(graph.edges)
        
        return graph
    
    async def _sort_and_paginate(
        self,
        data: List[Dict[str, Any]],
        query: StructuredQuery,
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Sort and paginate results."""
        start_time = time.time()
        
        # Sort if criteria specified
        if query.sort_criteria:
            for field, direction in reversed(query.sort_criteria):
                reverse = direction.lower() == 'desc'
                data.sort(
                    key=lambda x: x.get(field, ''),
                    reverse=reverse
                )
        
        # Paginate
        if query.offset:
            data = data[query.offset:]
        if query.limit:
            data = data[:query.limit]
        
        if self.enable_profiling:
            context.track_time('sort', (time.time() - start_time) * 1000)
            context.statistics.rows_returned = len(data)
        
        return data
    
    async def _cache_result(
        self,
        query: StructuredQuery,
        result: QueryResult,
        context: ExecutionContext
    ) -> None:
        """Cache result using Agent C's cache manager."""
        if not self.cache_manager:
            return
        
        cache_key = self._generate_cache_key(query)
        tags = query.entities + [query.intent]
        
        self.cache_manager.cache_result(
            cache_key,
            result,
            ttl=context.cache_ttl,
            tags=tags
        )
    
    def _generate_cache_key(self, query: StructuredQuery) -> str:
        """Generate deterministic cache key from query."""
        # Simple implementation - should be more sophisticated
        import hashlib
        import json
        
        key_data = {
            'intent': query.intent,
            'entities': sorted(query.entities),
            'filters': [
                {'field': f.field, 'op': f.operator.value, 'value': str(f.value)}
                for f in query.filters
            ],
            'sort': query.sort_criteria,
            'limit': query.limit,
            'offset': query.offset,
            'relationships': sorted(query.include_relationships),
            'depth': query.relationship_depth
        }
        
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()
    
    def _determine_databases(self, entities: List[str]) -> List[str]:
        """Determine which databases to load based on entities."""
        # Simple mapping - should be more sophisticated
        entity_to_database = {
            'people': 'People & Contacts',
            'person': 'People & Contacts',
            'organizations': 'Organizations & Bodies',
            'organization': 'Organizations & Bodies',
            'tasks': 'Actionable Tasks',
            'task': 'Actionable Tasks',
            'places': 'Key Places & Events',
            'place': 'Key Places & Events',
            'events': 'Key Places & Events',
            'event': 'Key Places & Events'
        }
        
        databases = set()
        for entity in entities:
            entity_lower = entity.lower()
            for key, db in entity_to_database.items():
                if key in entity_lower:
                    databases.add(db)
        
        # Default to all databases if none matched
        if not databases and self.data_loader:
            databases = set(self.data_loader.get_available_databases())
        
        return list(databases)
    
    def _extract_searchable_content(self, item: Dict[str, Any]) -> str:
        """Extract searchable text content from an item."""
        # Combine relevant text fields
        text_fields = ['name', 'title', 'description', 'content', 'notes']
        
        content_parts = []
        for field in text_fields:
            if field in item and item[field]:
                content_parts.append(str(item[field]))
        
        return ' '.join(content_parts)
    
    def _merge_search_results(
        self,
        data: List[Dict[str, Any]],
        search_results: List[SearchResult]
    ) -> List[Dict[str, Any]]:
        """Merge search results with data, preserving search relevance order."""
        if not search_results:
            return data
        
        # Create lookup for quick access
        data_by_id = {item.get('id', str(i)): item for i, item in enumerate(data)}
        
        # Return data in search result order
        result = []
        for search_result in search_results:
            if search_result.document_id in data_by_id:
                result.append(data_by_id[search_result.document_id])
        
        return result
    
    async def export_results(
        self,
        result: QueryResult,
        format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[bytes, str]:
        """Export query results using Agent C's export engine."""
        if not self.export_engine:
            raise ValueError("Export engine not configured")
        
        return self.export_engine.export(result, format, options or {})
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        stats = {
            'total_queries': self._query_count,
            'average_execution_time_ms': (
                self._total_execution_time / self._query_count 
                if self._query_count > 0 else 0
            )
        }
        
        # Add cache statistics if available
        if self.cache_manager:
            stats['cache'] = self.cache_manager.get_statistics()
        
        return stats


class QueryEngineBuilder:
    """Builder for constructing a fully configured query engine."""
    
    def __init__(self):
        self._config = {}
        
    def with_data_loader(self, loader: DataLoader) -> 'QueryEngineBuilder':
        """Add Agent A's data loader."""
        self._config['data_loader'] = loader
        return self
    
    def with_filter_engine(self, engine: FilterEngine) -> 'QueryEngineBuilder':
        """Add Agent A's filter engine."""
        self._config['filter_engine'] = engine
        return self
    
    def with_nlp_parser(self, parser: QueryParser) -> 'QueryEngineBuilder':
        """Add Agent B's NLP parser."""
        self._config['nlp_parser'] = parser
        return self
    
    def with_search_engine(self, engine: TextSearchEngine) -> 'QueryEngineBuilder':
        """Add Agent B's search engine."""
        self._config['search_engine'] = engine
        return self
    
    def with_relationship_resolver(self, resolver: RelationshipResolver) -> 'QueryEngineBuilder':
        """Add Agent B's relationship resolver."""
        self._config['relationship_resolver'] = resolver
        return self
    
    def with_cache_manager(self, manager: CacheManager) -> 'QueryEngineBuilder':
        """Add Agent C's cache manager."""
        self._config['cache_manager'] = manager
        return self
    
    def with_query_optimizer(self, optimizer: QueryOptimizer) -> 'QueryEngineBuilder':
        """Add Agent C's query optimizer."""
        self._config['query_optimizer'] = optimizer
        return self
    
    def with_export_engine(self, engine: ExportEngine) -> 'QueryEngineBuilder':
        """Add Agent C's export engine."""
        self._config['export_engine'] = engine
        return self
    
    def with_cache_enabled(self, enabled: bool = True) -> 'QueryEngineBuilder':
        """Enable or disable caching."""
        self._config['enable_cache'] = enabled
        return self
    
    def with_optimization_enabled(self, enabled: bool = True) -> 'QueryEngineBuilder':
        """Enable or disable query optimization."""
        self._config['enable_optimization'] = enabled
        return self
    
    def with_profiling_enabled(self, enabled: bool = True) -> 'QueryEngineBuilder':
        """Enable or disable profiling."""
        self._config['enable_profiling'] = enabled
        return self
    
    def build(self) -> QueryEngineOrchestrator:
        """Build the configured query engine."""
        return QueryEngineOrchestrator(**self._config)