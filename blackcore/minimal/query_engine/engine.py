"""Core query engine implementation."""

import json
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from ..models import NotionPage, DatabaseConfig
from .models import (
    QueryFilter, QueryOperator, SortOrder, SortField, QueryPagination,
    StructuredQuery, GraphQuery, SemanticQuery, TemporalQuery,
    QueryResult, GraphResult, SemanticResult, SemanticMatch,
    QueryError, QueryValidationError, QueryExecutionError
)


class QueryEngine:
    """Main query engine for intelligence data analysis."""
    
    def __init__(self, cache_dir: str = "blackcore/models/json"):
        """Initialize query engine with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.databases: Dict[str, List[Dict[str, Any]]] = {}
        self.database_configs: Dict[str, DatabaseConfig] = {}
        self._load_database_configs()
    
    def _load_database_configs(self) -> None:
        """Load database configurations."""
        config_path = Path("blackcore/config/notion_config.json")
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)
                for db_name, db_config in config_data.get("databases", {}).items():
                    self.database_configs[db_name] = DatabaseConfig(
                        id=db_config["id"],
                        name=db_name,
                        mappings=db_config.get("mappings", {}),
                        property_types=db_config.get("property_types", {})
                    )
    
    def _load_database(self, database_name: str) -> List[Dict[str, Any]]:
        """Load database from JSON cache."""
        if database_name in self.databases:
            return self.databases[database_name]
        
        # Find JSON file for database
        json_file = None
        for file_path in self.cache_dir.glob("*.json"):
            if database_name.lower().replace(" ", "_").replace("&", "and") in file_path.stem.lower():
                json_file = file_path
                break
        
        if not json_file or not json_file.exists():
            raise QueryExecutionError(f"Database '{database_name}' not found in cache")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.databases[database_name] = data
                return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise QueryExecutionError(f"Failed to load database '{database_name}': {e}")
    
    def _apply_filters(self, data: List[Dict[str, Any]], filters: List[QueryFilter]) -> List[Dict[str, Any]]:
        """Apply filters to data."""
        if not filters:
            return data
        
        filtered = []
        for item in data:
            if self._item_matches_filters(item, filters):
                filtered.append(item)
        
        return filtered
    
    def _item_matches_filters(self, item: Dict[str, Any], filters: List[QueryFilter]) -> bool:
        """Check if item matches all filters."""
        for filter_condition in filters:
            if not self._item_matches_filter(item, filter_condition):
                return False
        return True
    
    def _item_matches_filter(self, item: Dict[str, Any], filter_condition: QueryFilter) -> bool:
        """Check if item matches a single filter."""
        field_value = self._get_field_value(item, filter_condition.field)
        filter_value = filter_condition.value
        operator = filter_condition.operator
        
        # Handle case sensitivity for string operations
        if isinstance(field_value, str) and isinstance(filter_value, str):
            if not filter_condition.case_sensitive:
                field_value = field_value.lower()
                filter_value = filter_value.lower()
        
        # Apply operator
        if operator == QueryOperator.EQUALS:
            return field_value == filter_value
        elif operator == QueryOperator.NOT_EQUALS:
            return field_value != filter_value
        elif operator == QueryOperator.CONTAINS:
            if isinstance(field_value, str):
                return filter_value in field_value
            elif isinstance(field_value, list):
                return filter_value in field_value
            return False
        elif operator == QueryOperator.NOT_CONTAINS:
            if isinstance(field_value, str):
                return filter_value not in field_value
            elif isinstance(field_value, list):
                return filter_value not in field_value
            return True
        elif operator == QueryOperator.IN:
            return field_value in filter_value if isinstance(filter_value, (list, tuple)) else False
        elif operator == QueryOperator.NOT_IN:
            return field_value not in filter_value if isinstance(filter_value, (list, tuple)) else True
        elif operator == QueryOperator.GT:
            return self._compare_values(field_value, filter_value) > 0
        elif operator == QueryOperator.GTE:
            return self._compare_values(field_value, filter_value) >= 0
        elif operator == QueryOperator.LT:
            return self._compare_values(field_value, filter_value) < 0
        elif operator == QueryOperator.LTE:
            return self._compare_values(field_value, filter_value) <= 0
        elif operator == QueryOperator.BETWEEN:
            if isinstance(filter_value, (list, tuple)) and len(filter_value) == 2:
                return filter_value[0] <= field_value <= filter_value[1]
            return False
        elif operator == QueryOperator.IS_NULL:
            return field_value is None or field_value == ""
        elif operator == QueryOperator.IS_NOT_NULL:
            return field_value is not None and field_value != ""
        elif operator == QueryOperator.REGEX:
            import re
            try:
                return bool(re.search(str(filter_value), str(field_value)))
            except re.error:
                return False
        elif operator == QueryOperator.FUZZY:
            # Simple fuzzy matching - could be enhanced with proper fuzzy libraries
            if isinstance(field_value, str) and isinstance(filter_value, str):
                return self._fuzzy_match(field_value, filter_value)
            return False
        
        return False
    
    def _get_field_value(self, item: Dict[str, Any], field_path: str) -> Any:
        """Get field value from item, supporting nested fields."""
        current = item
        
        # Handle properties nested structure
        if field_path in item.get("properties", {}):
            prop_data = item["properties"][field_path]
            
            # Extract value based on property type
            if isinstance(prop_data, dict):
                if "title" in prop_data and prop_data["title"]:
                    return prop_data["title"][0].get("plain_text", "")
                elif "rich_text" in prop_data and prop_data["rich_text"]:
                    return prop_data["rich_text"][0].get("plain_text", "")
                elif "select" in prop_data and prop_data["select"]:
                    return prop_data["select"].get("name", "")
                elif "multi_select" in prop_data:
                    return [opt.get("name", "") for opt in prop_data["multi_select"]]
                elif "number" in prop_data:
                    return prop_data["number"]
                elif "checkbox" in prop_data:
                    return prop_data["checkbox"]
                elif "date" in prop_data and prop_data["date"]:
                    return prop_data["date"].get("start")
                elif "people" in prop_data:
                    return [person.get("name", "") for person in prop_data["people"]]
                elif "relation" in prop_data:
                    return [rel.get("id", "") for rel in prop_data["relation"]]
            
            return prop_data
        
        # Handle direct field access
        for part in field_path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _compare_values(self, a: Any, b: Any) -> int:
        """Compare two values, handling different types."""
        if type(a) != type(b):
            # Try to convert to comparable types
            try:
                if isinstance(a, str) and isinstance(b, (int, float)):
                    a = float(a)
                elif isinstance(b, str) and isinstance(a, (int, float)):
                    b = float(b)
            except (ValueError, TypeError):
                # Fall back to string comparison
                a, b = str(a), str(b)
        
        if a < b:
            return -1
        elif a > b:
            return 1
        else:
            return 0
    
    def _fuzzy_match(self, text: str, pattern: str, threshold: float = 0.6) -> bool:
        """Simple fuzzy string matching."""
        # Simple implementation - could use more sophisticated algorithms
        text_words = text.lower().split()
        pattern_words = pattern.lower().split()
        
        matches = 0
        for pattern_word in pattern_words:
            for text_word in text_words:
                if pattern_word in text_word or text_word in pattern_word:
                    matches += 1
                    break
        
        return (matches / len(pattern_words)) >= threshold
    
    def _apply_sorting(self, data: List[Dict[str, Any]], sort_fields: List[SortField]) -> List[Dict[str, Any]]:
        """Apply sorting to data."""
        if not sort_fields:
            return data
        
        def sort_key(item):
            key_values = []
            for sort_field in sort_fields:
                value = self._get_field_value(item, sort_field.field)
                # Handle None values
                if value is None:
                    value = "" if sort_field.order == SortOrder.ASC else "~"  # ~ sorts last in ASCII
                key_values.append(value)
            return key_values
        
        reverse = any(sf.order == SortOrder.DESC for sf in sort_fields)
        return sorted(data, key=sort_key, reverse=reverse)
    
    def _apply_pagination(self, data: List[Dict[str, Any]], pagination: QueryPagination) -> List[Dict[str, Any]]:
        """Apply pagination to data."""
        start = pagination.offset
        end = start + pagination.size
        return data[start:end]
    
    def execute_structured_query(self, query: StructuredQuery) -> QueryResult:
        """Execute a structured query."""
        start_time = time.time()
        
        try:
            # Load database
            data = self._load_database(query.database)
            
            # Apply filters
            filtered = self._apply_filters(data, query.filters)
            
            # Apply sorting
            sorted_data = self._apply_sorting(filtered, query.sort_fields)
            
            # Handle distinct
            if query.distinct:
                seen = set()
                distinct_data = []
                for item in sorted_data:
                    # Create a hash of the item for deduplication
                    item_hash = hash(json.dumps(item, sort_keys=True, default=str))
                    if item_hash not in seen:
                        seen.add(item_hash)
                        distinct_data.append(item)
                sorted_data = distinct_data
            
            total_count = len(sorted_data)
            
            # Apply pagination
            paginated = self._apply_pagination(sorted_data, query.pagination)
            
            # Load relationships if requested
            if query.includes:
                paginated = self._load_relationships(paginated, query.includes)
            
            execution_time = (time.time() - start_time) * 1000
            
            return QueryResult(
                data=paginated,
                total_count=total_count,
                page=query.pagination.page,
                page_size=query.pagination.size,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            raise QueryExecutionError(f"Query execution failed: {e}")
    
    async def execute_structured_query_async(self, query: StructuredQuery) -> QueryResult:
        """Execute a structured query asynchronously."""
        # Use asyncio.to_thread to run synchronous query in thread pool
        return await asyncio.to_thread(self.execute_structured_query, query)
    
    async def text_search_async(self, query_text: str, databases: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Perform text search asynchronously."""
        return await asyncio.to_thread(self.text_search, query_text, databases)
    
    def _load_relationships(self, data: List[Dict[str, Any]], includes: List[Any]) -> List[Dict[str, Any]]:
        """Load related entities for the data."""
        # TODO: Implement relationship loading
        # This would involve:
        # 1. Identifying relation fields in the data
        # 2. Loading related entities from other databases
        # 3. Embedding related data in the results
        return data
    
    def execute_graph_query(self, query: GraphQuery) -> GraphResult:
        """Execute a graph traversal query."""
        start_time = time.time()
        
        # TODO: Implement graph query execution
        # This would involve:
        # 1. Starting from specified entities
        # 2. Traversing relationships up to max_depth
        # 3. Applying node and edge filters
        # 4. Building graph structure
        # 5. Optionally returning paths
        
        execution_time = (time.time() - start_time) * 1000
        
        return GraphResult(
            nodes=[],
            edges=[],
            paths=[] if query.return_paths else None,
            execution_time_ms=execution_time
        )
    
    def execute_semantic_query(self, query: SemanticQuery) -> SemanticResult:
        """Execute a semantic search query."""
        start_time = time.time()
        
        # TODO: Implement semantic search
        # This would involve:
        # 1. Converting query text to embeddings
        # 2. Computing similarity with stored embeddings
        # 3. Ranking results by similarity
        # 4. Filtering by threshold
        
        execution_time = (time.time() - start_time) * 1000
        
        return SemanticResult(
            matches=[],
            query_text=query.query_text,
            execution_time_ms=execution_time
        )
    
    def text_search(self, query_text: str, databases: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Perform full-text search across databases."""
        results = []
        search_databases = databases or list(self.database_configs.keys())
        
        for db_name in search_databases:
            try:
                data = self._load_database(db_name)
                matches = self._search_database_content(data, query_text, db_name)
                results.extend(matches)
            except QueryExecutionError:
                # Skip databases that can't be loaded
                continue
        
        # Sort by relevance score (if available)
        return sorted(results, key=lambda x: x.get("_score", 0), reverse=True)
    
    def _search_database_content(self, data: List[Dict[str, Any]], query_text: str, database_name: str) -> List[Dict[str, Any]]:
        """Search content within a database."""
        matches = []
        query_lower = query_text.lower()
        
        for item in data:
            score = self._calculate_text_match_score(item, query_lower)
            if score > 0:
                # Add metadata about the match
                match_item = item.copy()
                match_item["_score"] = score
                match_item["_database"] = database_name
                matches.append(match_item)
        
        return matches
    
    def _calculate_text_match_score(self, item: Dict[str, Any], query_lower: str) -> float:
        """Calculate text match score for an item."""
        score = 0.0
        text_content = self._extract_searchable_text(item)
        
        if query_lower in text_content.lower():
            # Basic scoring - could be enhanced with TF-IDF or other algorithms
            score = text_content.lower().count(query_lower) / len(text_content.split())
            
            # Boost score for title matches
            title_text = self._get_field_value(item, "title") or ""
            if query_lower in str(title_text).lower():
                score *= 2.0
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _extract_searchable_text(self, item: Dict[str, Any]) -> str:
        """Extract searchable text from an item."""
        text_parts = []
        
        # Extract from properties
        properties = item.get("properties", {})
        for prop_name, prop_value in properties.items():
            if isinstance(prop_value, dict):
                # Extract text from various property types
                if "title" in prop_value and prop_value["title"]:
                    text_parts.append(prop_value["title"][0].get("plain_text", ""))
                elif "rich_text" in prop_value and prop_value["rich_text"]:
                    for text_obj in prop_value["rich_text"]:
                        text_parts.append(text_obj.get("plain_text", ""))
                elif "select" in prop_value and prop_value["select"]:
                    text_parts.append(prop_value["select"].get("name", ""))
            elif isinstance(prop_value, str):
                text_parts.append(prop_value)
        
        return " ".join(text_parts)


class QueryBuilder:
    """Fluent interface for building queries."""
    
    def __init__(self, database: str):
        """Initialize query builder for a database."""
        self.query = StructuredQuery(database=database)
    
    def filter(self, field: str, operator: QueryOperator, value: Any, case_sensitive: bool = True) -> 'QueryBuilder':
        """Add a filter condition."""
        self.query.filters.append(QueryFilter(
            field=field,
            operator=operator,
            value=value,
            case_sensitive=case_sensitive
        ))
        return self
    
    def sort(self, field: str, order: SortOrder = SortOrder.ASC) -> 'QueryBuilder':
        """Add sorting."""
        self.query.sort_fields.append(SortField(field=field, order=order))
        return self
    
    def include_relations(self, relation_field: str, target_database: Optional[str] = None, max_depth: int = 1) -> 'QueryBuilder':
        """Include related entities."""
        from .models import RelationshipInclude
        self.query.includes.append(RelationshipInclude(
            relation_field=relation_field,
            target_database=target_database,
            max_depth=max_depth
        ))
        return self
    
    def paginate(self, page: int, size: int = 100) -> 'QueryBuilder':
        """Set pagination."""
        self.query.pagination = QueryPagination(page=page, size=size)
        return self
    
    def distinct(self) -> 'QueryBuilder':
        """Return only distinct results."""
        self.query.distinct = True
        return self
    
    def build(self) -> StructuredQuery:
        """Build the final query."""
        return self.query
    
    def execute(self, engine: QueryEngine) -> QueryResult:
        """Execute the query using the provided engine."""
        return engine.execute_structured_query(self.query)


# Convenience functions
def create_query(database: str) -> QueryBuilder:
    """Create a new query builder."""
    return QueryBuilder(database)


def quick_search(query_text: str, databases: Optional[List[str]] = None, cache_dir: str = "blackcore/models/json") -> List[Dict[str, Any]]:
    """Perform a quick text search across databases."""
    engine = QueryEngine(cache_dir)
    return engine.text_search(query_text, databases)