"""Core interfaces and abstractions for the query engine."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pathlib import Path

from .models import (
    QueryFilter, StructuredQuery, GraphQuery, SemanticQuery,
    QueryResult, GraphResult, SemanticResult
)


@runtime_checkable
class DataLoader(Protocol):
    """Interface for loading data from various sources."""
    
    def load_database(self, database_name: str) -> List[Dict[str, Any]]:
        """Load a database by name."""
        ...
    
    def get_available_databases(self) -> List[str]:
        """Get list of available databases."""
        ...
    
    def refresh_cache(self, database_name: Optional[str] = None) -> None:
        """Refresh cached data."""
        ...


@runtime_checkable
class FilterEngine(Protocol):
    """Interface for applying filters to data."""
    
    def apply_filters(self, data: List[Dict[str, Any]], filters: List[QueryFilter]) -> List[Dict[str, Any]]:
        """Apply filters to data."""
        ...
    
    def validate_filter(self, filter_condition: QueryFilter, database_schema: Dict[str, Any]) -> bool:
        """Validate that a filter is applicable to the schema."""
        ...


@runtime_checkable
class SortingEngine(Protocol):
    """Interface for sorting and pagination."""
    
    def apply_sorting(self, data: List[Dict[str, Any]], sort_fields: List[Any]) -> List[Dict[str, Any]]:
        """Apply sorting to data."""
        ...
    
    def apply_pagination(self, data: List[Dict[str, Any]], page: int, size: int) -> tuple[List[Dict[str, Any]], int]:
        """Apply pagination and return data with total count."""
        ...


@runtime_checkable
class TextSearchEngine(Protocol):
    """Interface for text search functionality."""
    
    def search(self, query_text: str, data: List[Dict[str, Any]], database_name: str) -> List[Dict[str, Any]]:
        """Perform text search on data."""
        ...
    
    def calculate_relevance_score(self, item: Dict[str, Any], query_text: str) -> float:
        """Calculate relevance score for an item."""
        ...


@runtime_checkable
class RelationshipResolver(Protocol):
    """Interface for resolving relationships between entities."""
    
    def resolve_relationships(
        self, 
        data: List[Dict[str, Any]], 
        includes: List[Any],
        data_loader: DataLoader
    ) -> List[Dict[str, Any]]:
        """Resolve and embed relationships."""
        ...
    
    def get_related_entities(
        self, 
        entity_id: str, 
        relation_field: str,
        target_database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get entities related to a specific entity."""
        ...


@runtime_checkable
class CacheManager(Protocol):
    """Interface for query result caching."""
    
    def get_cached_result(self, query_hash: str) -> Optional[QueryResult]:
        """Get cached query result."""
        ...
    
    def cache_result(self, query_hash: str, result: QueryResult, ttl: int = 3600) -> None:
        """Cache query result."""
        ...
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """Invalidate cached results."""
        ...


@runtime_checkable
class QueryOptimizer(Protocol):
    """Interface for query optimization."""
    
    def optimize_query(self, query: StructuredQuery) -> StructuredQuery:
        """Optimize query for better performance."""
        ...
    
    def estimate_cost(self, query: StructuredQuery) -> float:
        """Estimate query execution cost."""
        ...
    
    def suggest_indexes(self, queries: List[StructuredQuery]) -> List[str]:
        """Suggest indexes based on query patterns."""
        ...


class BaseQueryExecutor(ABC):
    """Base class for query executors."""
    
    def __init__(
        self,
        data_loader: DataLoader,
        filter_engine: FilterEngine,
        sorting_engine: SortingEngine,
        text_search_engine: Optional[TextSearchEngine] = None,
        relationship_resolver: Optional[RelationshipResolver] = None,
        cache_manager: Optional[CacheManager] = None,
        query_optimizer: Optional[QueryOptimizer] = None
    ):
        self.data_loader = data_loader
        self.filter_engine = filter_engine
        self.sorting_engine = sorting_engine
        self.text_search_engine = text_search_engine
        self.relationship_resolver = relationship_resolver
        self.cache_manager = cache_manager
        self.query_optimizer = query_optimizer
    
    @abstractmethod
    def execute(self, query: Any) -> Any:
        """Execute a query."""
        pass
    
    def _generate_query_hash(self, query: Any) -> str:
        """Generate hash for query caching."""
        import hashlib
        import json
        
        query_str = json.dumps(query.model_dump() if hasattr(query, 'model_dump') else query, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()


class StructuredQueryExecutor(BaseQueryExecutor):
    """Executor for structured queries."""
    
    def execute(self, query: StructuredQuery) -> QueryResult:
        """Execute a structured query."""
        import time
        start_time = time.time()
        
        # Check cache first
        if self.cache_manager:
            query_hash = self._generate_query_hash(query)
            cached_result = self.cache_manager.get_cached_result(query_hash)
            if cached_result:
                cached_result.from_cache = True
                return cached_result
        
        # Optimize query if optimizer available
        if self.query_optimizer:
            query = self.query_optimizer.optimize_query(query)
        
        # Load data
        data = self.data_loader.load_database(query.database)
        
        # Apply filters
        filtered = self.filter_engine.apply_filters(data, query.filters)
        
        # Apply sorting
        sorted_data = self.sorting_engine.apply_sorting(filtered, query.sort_fields)
        
        # Handle distinct
        if query.distinct:
            sorted_data = self._apply_distinct(sorted_data)
        
        # Apply pagination
        paginated, total_count = self.sorting_engine.apply_pagination(
            sorted_data, query.pagination.page, query.pagination.size
        )
        
        # Resolve relationships
        if query.includes and self.relationship_resolver:
            paginated = self.relationship_resolver.resolve_relationships(
                paginated, query.includes, self.data_loader
            )
        
        execution_time = (time.time() - start_time) * 1000
        
        result = QueryResult(
            data=paginated,
            total_count=total_count,
            page=query.pagination.page,
            page_size=query.pagination.size,
            execution_time_ms=execution_time
        )
        
        # Cache result
        if self.cache_manager:
            self.cache_manager.cache_result(query_hash, result)
        
        return result
    
    def _apply_distinct(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply distinct filtering to data."""
        import json
        seen = set()
        distinct_data = []
        
        for item in data:
            # Create a hash of the item for deduplication
            item_hash = hash(json.dumps(item, sort_keys=True, default=str))
            if item_hash not in seen:
                seen.add(item_hash)
                distinct_data.append(item)
        
        return distinct_data


class GraphQueryExecutor(BaseQueryExecutor):
    """Executor for graph traversal queries."""
    
    def execute(self, query: GraphQuery) -> GraphResult:
        """Execute a graph query."""
        import time
        start_time = time.time()
        
        # TODO: Implement graph traversal logic
        # This would involve:
        # 1. Starting from specified entities
        # 2. Traversing relationships up to max_depth
        # 3. Building graph structure
        
        execution_time = (time.time() - start_time) * 1000
        
        return GraphResult(
            nodes=[],
            edges=[],
            paths=[] if query.return_paths else None,
            execution_time_ms=execution_time
        )


class SemanticQueryExecutor(BaseQueryExecutor):
    """Executor for semantic search queries."""
    
    def execute(self, query: SemanticQuery) -> SemanticResult:
        """Execute a semantic query."""
        import time
        start_time = time.time()
        
        # TODO: Implement semantic search
        # This would involve AI/ML components for embeddings
        
        execution_time = (time.time() - start_time) * 1000
        
        return SemanticResult(
            matches=[],
            query_text=query.query_text,
            execution_time_ms=execution_time
        )


class QueryEngineFactory:
    """Factory for creating query engine components."""
    
    @staticmethod
    def create_structured_executor(
        cache_dir: str = "blackcore/models/json",
        enable_caching: bool = True,
        enable_optimization: bool = False
    ) -> StructuredQueryExecutor:
        """Create a structured query executor with default components."""
        from .loaders import JSONDataLoader
        from .filters import BasicFilterEngine
        from .sorting import BasicSortingEngine
        from .search import BasicTextSearchEngine
        from .relationships import BasicRelationshipResolver
        # Import conditionally based on flags
        if enable_caching:
            from .cache import MemoryCacheManager
        if enable_optimization:
            from .optimization import BasicQueryOptimizer
        
        data_loader = JSONDataLoader(cache_dir)
        filter_engine = BasicFilterEngine()
        sorting_engine = BasicSortingEngine()
        text_search_engine = BasicTextSearchEngine()
        relationship_resolver = BasicRelationshipResolver()
        cache_manager = MemoryCacheManager() if enable_caching else None
        query_optimizer = BasicQueryOptimizer() if enable_optimization else None
        
        return StructuredQueryExecutor(
            data_loader=data_loader,
            filter_engine=filter_engine,
            sorting_engine=sorting_engine,
            text_search_engine=text_search_engine,
            relationship_resolver=relationship_resolver,
            cache_manager=cache_manager,
            query_optimizer=query_optimizer
        )


class QueryEngine:
    """Main query engine orchestrator."""
    
    def __init__(
        self,
        structured_executor: Optional[StructuredQueryExecutor] = None,
        graph_executor: Optional[GraphQueryExecutor] = None,
        semantic_executor: Optional[SemanticQueryExecutor] = None
    ):
        self.structured_executor = structured_executor or QueryEngineFactory.create_structured_executor()
        self.graph_executor = graph_executor
        self.semantic_executor = semantic_executor
    
    def execute_structured_query(self, query: StructuredQuery) -> QueryResult:
        """Execute a structured query."""
        return self.structured_executor.execute(query)
    
    def execute_graph_query(self, query: GraphQuery) -> GraphResult:
        """Execute a graph query."""
        if not self.graph_executor:
            raise NotImplementedError("Graph query executor not configured")
        return self.graph_executor.execute(query)
    
    def execute_semantic_query(self, query: SemanticQuery) -> SemanticResult:
        """Execute a semantic query."""
        if not self.semantic_executor:
            raise NotImplementedError("Semantic query executor not configured")
        return self.semantic_executor.execute(query)
    
    def text_search(self, query_text: str, databases: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Perform text search across databases."""
        if not self.structured_executor.text_search_engine:
            raise NotImplementedError("Text search engine not configured")
        
        results = []
        available_databases = self.structured_executor.data_loader.get_available_databases()
        search_databases = databases or available_databases
        
        for db_name in search_databases:
            try:
                data = self.structured_executor.data_loader.load_database(db_name)
                matches = self.structured_executor.text_search_engine.search(query_text, data, db_name)
                results.extend(matches)
            except Exception:
                # Skip databases that can't be loaded
                continue
        
        # Sort by relevance score
        return sorted(results, key=lambda x: x.get("_score", 0), reverse=True)