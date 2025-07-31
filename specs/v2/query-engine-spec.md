# Query Engine Specification

## Overview

The Query Engine provides a unified interface for querying data across all Blackcore databases, supporting filters, relationships, pagination, and text search.

## Goals

1. Enable complex queries across multiple databases
2. Support relationship traversal
3. Provide efficient pagination for large result sets
4. Enable full-text search within properties
5. Maintain compatibility with existing JSON cache

## Architecture

### Query Interface

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class QueryOperator(Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    IN = "in"
    GT = "gt"
    LT = "lt"
    BETWEEN = "between"

class QueryFilter:
    def __init__(self, field: str, operator: QueryOperator, value: Any):
        self.field = field
        self.operator = operator
        self.value = value

class QueryBuilder:
    def __init__(self, database: str):
        self.database = database
        self.filters: List[QueryFilter] = []
        self.includes: List[str] = []  # Related entities to include
        self.order_by: Optional[str] = None
        self.limit: int = 100
        self.offset: int = 0
    
    def filter(self, field: str, operator: QueryOperator, value: Any) -> 'QueryBuilder':
        self.filters.append(QueryFilter(field, operator, value))
        return self
    
    def include(self, relation: str) -> 'QueryBuilder':
        self.includes.append(relation)
        return self
    
    def order(self, field: str, desc: bool = False) -> 'QueryBuilder':
        self.order_by = f"{'-' if desc else ''}{field}"
        return self
    
    def paginate(self, page: int, per_page: int = 100) -> 'QueryBuilder':
        self.limit = per_page
        self.offset = (page - 1) * per_page
        return self
```

### Query Engine Implementation

```python
class QueryEngine:
    def __init__(self, json_cache_path: str):
        self.cache_path = json_cache_path
        self.databases = self._load_database_configs()
    
    def execute(self, query: QueryBuilder) -> QueryResult:
        # Load database from JSON cache
        data = self._load_database(query.database)
        
        # Apply filters
        filtered = self._apply_filters(data, query.filters)
        
        # Load related entities
        if query.includes:
            filtered = self._load_relations(filtered, query.includes)
        
        # Apply ordering
        if query.order_by:
            filtered = self._apply_ordering(filtered, query.order_by)
        
        # Apply pagination
        total = len(filtered)
        paginated = filtered[query.offset:query.offset + query.limit]
        
        return QueryResult(
            data=paginated,
            total=total,
            page=query.offset // query.limit + 1,
            per_page=query.limit
        )
    
    def search(self, query: str, databases: List[str] = None) -> List[SearchResult]:
        """Full-text search across specified databases"""
        results = []
        search_dbs = databases or self.databases.keys()
        
        for db in search_dbs:
            data = self._load_database(db)
            matches = self._text_search(data, query)
            results.extend([
                SearchResult(database=db, entity=match, score=score)
                for match, score in matches
            ])
        
        return sorted(results, key=lambda x: x.score, reverse=True)
```

## Usage Examples

### Basic Filtering

```python
# Find all people in a specific organization
query = QueryBuilder("People & Contacts") \
    .filter("Organization", QueryOperator.EQUALS, "Dorset Council") \
    .order("Full Name")

results = engine.execute(query)
```

### Relationship Loading

```python
# Find all tasks with their assignees
query = QueryBuilder("Actionable Tasks") \
    .filter("Status", QueryOperator.IN, ["In Progress", "Pending"]) \
    .include("Assignee") \
    .include("Related Agenda")

results = engine.execute(query)
# Each task will have 'Assignee' and 'Related Agenda' entities loaded
```

### Date Range Queries

```python
# Find all intelligence from last week
from datetime import datetime, timedelta

last_week = datetime.now() - timedelta(days=7)
query = QueryBuilder("Intelligence & Transcripts") \
    .filter("Date Created", QueryOperator.GT, last_week) \
    .order("Date Created", desc=True)

results = engine.execute(query)
```

### Cross-Database Search

```python
# Search for "beach huts" across all databases
results = engine.search("beach huts", databases=[
    "Intelligence & Transcripts",
    "Documents & Evidence", 
    "Actionable Tasks"
])

for result in results[:10]:
    print(f"{result.database}: {result.entity['title']} (score: {result.score})")
```

### Complex Relationship Queries

```python
# Find all people connected to a specific transgression
transgression_id = "123"

# First, get the transgression with all relationships
transgression_query = QueryBuilder("Identified Transgressions") \
    .filter("id", QueryOperator.EQUALS, transgression_id) \
    .include("Perpetrator (Person)") \
    .include("Perpetrator (Org)")

transgression = engine.execute(transgression_query).data[0]

# Then get all people in the perpetrator organization
if transgression.get("Perpetrator (Org)"):
    org_id = transgression["Perpetrator (Org)"][0]["id"]
    people_query = QueryBuilder("People & Contacts") \
        .filter("Organization", QueryOperator.CONTAINS, org_id)
    
    related_people = engine.execute(people_query)
```

## Performance Considerations

1. **Indexing**: Create indexes on commonly queried fields
2. **Caching**: Cache parsed JSON data in memory
3. **Lazy Loading**: Load relationships only when requested
4. **Query Optimization**: Combine filters efficiently
5. **Pagination**: Always paginate large result sets

## Testing Strategy

1. **Unit Tests**:
   - Filter operators (equals, contains, between, etc.)
   - Pagination logic
   - Ordering logic
   - Text search algorithm

2. **Integration Tests**:
   - Cross-database queries
   - Relationship loading
   - Complex filter combinations
   - Performance with large datasets

3. **Performance Tests**:
   - Query 10,000+ entities
   - Load deep relationship chains
   - Concurrent query execution

## Future Enhancements

1. **Query Caching**: Cache frequent queries
2. **Query Plans**: Optimize execution order
3. **Aggregations**: COUNT, SUM, AVG operations
4. **GraphQL Interface**: Alternative query language
5. **Query Builder UI**: Visual query construction

## Dependencies

- Python 3.11+
- No external database required (uses JSON cache)
- Optional: Redis for query result caching

## Timeline

- Days 1-2: Core filter implementation
- Days 3-4: Relationship loading
- Day 5: Text search
- Days 6-7: Testing and optimization