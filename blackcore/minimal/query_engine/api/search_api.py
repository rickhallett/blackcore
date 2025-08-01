"""Enhanced Search API endpoints with semantic capabilities."""

from fastapi import APIRouter, HTTPException, Depends, Query as QueryParam
from typing import List, Optional, Dict, Any
import time
import asyncio
import logging
from pydantic import BaseModel, Field

from .auth import get_current_api_key, check_rate_limit
from .models import EntityResponse, ErrorResponse
from ..search.semantic_search import SemanticSearchEngine, SemanticSearchResult
from ..interfaces import QueryEngine
from ..models import SearchConfig

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/search", tags=["Search"])

# Initialize search engine
semantic_engine = SemanticSearchEngine()


class UniversalSearchRequest(BaseModel):
    """Request for universal entity search."""
    query: str = Field(..., description="Natural language search query", min_length=1, max_length=500)
    databases: Optional[List[str]] = Field(None, description="Databases to search (None = all)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters to apply")
    max_results: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    min_score: float = Field(0.1, ge=0.0, le=1.0, description="Minimum relevance score")
    enable_fuzzy: bool = Field(True, description="Enable fuzzy matching")
    enable_semantic: bool = Field(True, description="Enable semantic search features")
    include_explanations: bool = Field(False, description="Include explanations for results")


class SearchSuggestion(BaseModel):
    """Search suggestion response."""
    suggestion: str
    type: str  # 'query', 'entity', 'field'
    confidence: float


class SemanticSearchResponse(BaseModel):
    """Response for semantic search results."""
    results: List[Dict[str, Any]]
    total_count: int
    query: str
    intent: Optional[str] = None
    suggestions: List[SearchSuggestion] = []
    facets: Optional[Dict[str, Dict[str, int]]] = None
    execution_time_ms: float


class EntitySearchResponse(BaseModel):
    """Response for entity-specific search."""
    entity_type: str
    results: List[EntityResponse]
    total_count: int
    execution_time_ms: float


@router.post("/universal", response_model=SemanticSearchResponse)
async def universal_search(
    request: UniversalSearchRequest,
    query_engine: QueryEngine = Depends(lambda: QueryEngine()),
    api_key: str = Depends(get_current_api_key)
):
    """Perform universal search across all entities with semantic understanding.
    
    Features:
    - Natural language query understanding
    - Fuzzy matching for typos
    - Synonym expansion
    - Entity recognition
    - Intent detection
    - Cross-database search
    """
    try:
        start_time = time.time()
        
        # Load data from specified databases
        all_data = []
        databases = request.databases or query_engine.structured_executor.data_loader.get_available_databases()
        
        for db_name in databases:
            try:
                data = query_engine.structured_executor.data_loader.load_database(db_name)
                # Add database info to each item
                for item in data:
                    item['_database'] = db_name
                all_data.extend(data)
            except Exception as e:
                logger.warning(f"Failed to load database {db_name}: {e}")
        
        # Apply pre-filters if provided
        if request.filters:
            all_data = _apply_filters(all_data, request.filters)
        
        # Configure search
        config = SearchConfig(
            max_results=request.max_results,
            min_score=request.min_score,
            enable_fuzzy=request.enable_fuzzy,
            enable_stemming=request.enable_semantic,
            field_weights=None  # Use default weights
        )
        
        # Perform semantic search
        results = await asyncio.to_thread(
            semantic_engine.search,
            request.query,
            all_data,
            config
        )
        
        # Parse query for intent
        query_info = semantic_engine._parse_query(request.query)
        
        # Generate suggestions
        suggestions = []
        if len(results) < 5:  # Few results, suggest alternatives
            alt_queries = await _generate_query_suggestions(request.query, all_data)
            suggestions = [
                SearchSuggestion(suggestion=q, type="query", confidence=0.8)
                for q in alt_queries[:5]
            ]
        
        # Calculate facets
        facets = _calculate_facets(results) if results else None
        
        # Format results
        formatted_results = []
        for result in results:
            formatted = {
                "entity": _format_entity(result.entity),
                "score": result.score,
                "database": result.database
            }
            
            if request.include_explanations and hasattr(result, 'explanation'):
                formatted["explanation"] = result.explanation
                formatted["highlights"] = getattr(result, 'highlights', {})
            
            formatted_results.append(formatted)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SemanticSearchResponse(
            results=formatted_results,
            total_count=len(results),
            query=request.query,
            intent=query_info.get('intent'),
            suggestions=suggestions,
            facets=facets,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Universal search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = QueryParam(..., description="Partial query for suggestions"),
    databases: Optional[List[str]] = QueryParam(None, description="Databases to consider"),
    limit: int = QueryParam(10, ge=1, le=50, description="Maximum suggestions"),
    query_engine: QueryEngine = Depends(lambda: QueryEngine())
):
    """Get search suggestions based on partial query.
    
    Returns suggestions for:
    - Query completions
    - Related entities
    - Common searches
    """
    try:
        # Load sample data for suggestions
        sample_data = []
        dbs = databases or query_engine.structured_executor.data_loader.get_available_databases()
        
        for db_name in dbs[:3]:  # Limit databases for performance
            try:
                data = query_engine.structured_executor.data_loader.load_database(db_name)
                sample_data.extend(data[:100])  # Sample per database
            except:
                pass
        
        # Get suggestions
        suggestions = semantic_engine.get_search_suggestions(q, sample_data, limit)
        
        # Format as suggestion objects
        formatted = [
            SearchSuggestion(
                suggestion=s,
                type="query",
                confidence=0.9 - (i * 0.05)  # Decreasing confidence
            )
            for i, s in enumerate(suggestions)
        ]
        
        return formatted
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/{entity_type}", response_model=EntitySearchResponse)
async def search_entities(
    entity_type: str,
    query: str = QueryParam(..., description="Search query"),
    limit: int = QueryParam(50, ge=1, le=500),
    query_engine: QueryEngine = Depends(lambda: QueryEngine()),
    api_key: str = Depends(get_current_api_key)
):
    """Search for specific entity types with optimized queries.
    
    Entity types:
    - people: Search in People & Contacts
    - tasks: Search in Actionable Tasks
    - documents: Search in Documents & Evidence
    - organizations: Search in Organizations & Bodies
    - events: Search in Key Places & Events
    """
    try:
        start_time = time.time()
        
        # Map entity types to databases
        entity_db_map = {
            'people': 'People & Contacts',
            'tasks': 'Actionable Tasks',
            'documents': 'Documents & Evidence',
            'organizations': 'Organizations & Bodies',
            'events': 'Key Places & Events',
            'transcripts': 'Intelligence & Transcripts'
        }
        
        if entity_type not in entity_db_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity type. Choose from: {list(entity_db_map.keys())}"
            )
        
        db_name = entity_db_map[entity_type]
        
        # Load specific database
        try:
            data = query_engine.structured_executor.data_loader.load_database(db_name)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Database '{db_name}' not found"
            )
        
        # Add database info
        for item in data:
            item['_database'] = db_name
        
        # Perform search with entity-specific config
        config = SearchConfig(
            max_results=limit,
            min_score=0.1,
            enable_fuzzy=True,
            field_weights=_get_entity_field_weights(entity_type)
        )
        
        results = await asyncio.to_thread(
            semantic_engine.search,
            query,
            data,
            config
        )
        
        # Format results
        entities = [
            EntityResponse(
                id=r.entity.get('id', ''),
                database=db_name,
                properties=r.entity.get('properties', {}),
                created_time=r.entity.get('created_time', ''),
                last_edited_time=r.entity.get('last_edited_time', ''),
                url=r.entity.get('url'),
                _score=r.score
            )
            for r in results
        ]
        
        execution_time = (time.time() - start_time) * 1000
        
        return EntitySearchResponse(
            entity_type=entity_type,
            results=entities,
            total_count=len(entities),
            execution_time_ms=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    query: str = QueryParam(..., description="Natural language query"),
    context: Optional[str] = QueryParam(None, description="Additional context for search"),
    databases: Optional[List[str]] = QueryParam(None),
    enable_learning: bool = QueryParam(False, description="Learn from this search"),
    query_engine: QueryEngine = Depends(lambda: QueryEngine()),
    api_key: str = Depends(get_current_api_key)
):
    """Advanced semantic search with context understanding.
    
    Features:
    - Context-aware search
    - Query learning
    - Relationship exploration
    - Concept matching
    """
    try:
        start_time = time.time()
        
        # Enhance query with context
        enhanced_query = query
        if context:
            enhanced_query = f"{context} {query}"
        
        # Load data
        all_data = []
        dbs = databases or query_engine.structured_executor.data_loader.get_available_databases()
        
        for db_name in dbs:
            try:
                data = query_engine.structured_executor.data_loader.load_database(db_name)
                for item in data:
                    item['_database'] = db_name
                all_data.extend(data)
            except:
                pass
        
        # Advanced semantic config
        config = SearchConfig(
            max_results=100,
            min_score=0.05,  # Lower threshold for semantic
            enable_fuzzy=True,
            enable_stemming=True
        )
        
        # Perform search
        results = await asyncio.to_thread(
            semantic_engine.search,
            enhanced_query,
            all_data,
            config
        )
        
        # Learn from search if enabled
        if enable_learning and results:
            # TODO: Implement search learning
            pass
        
        # Analyze relationships in results
        relationships = _analyze_relationships(results[:20]) if results else {}
        
        # Format response
        formatted_results = []
        for result in results:
            formatted = {
                "entity": _format_entity(result.entity),
                "score": result.score,
                "database": result.database,
                "semantic_score": getattr(result, 'semantic_score', result.score)
            }
            
            if hasattr(result, 'explanation'):
                formatted["explanation"] = result.explanation
                formatted["matched_concepts"] = getattr(result, 'matched_tokens', [])
            
            formatted_results.append(formatted)
        
        # Generate insights
        facets = _calculate_facets(results)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SemanticSearchResponse(
            results=formatted_results,
            total_count=len(results),
            query=query,
            intent="semantic_analysis",
            suggestions=[],
            facets=facets,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
def _apply_filters(data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply additional filters to data."""
    filtered = []
    
    for item in data:
        match = True
        for field, value in filters.items():
            item_value = item
            for part in field.split('.'):
                item_value = item_value.get(part, {}) if isinstance(item_value, dict) else None
            
            if item_value != value:
                match = False
                break
        
        if match:
            filtered.append(item)
    
    return filtered


def _format_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Format entity for response."""
    return {
        "id": entity.get("id", ""),
        "properties": entity.get("properties", {}),
        "created_time": entity.get("created_time", ""),
        "last_edited_time": entity.get("last_edited_time", ""),
        "url": entity.get("url")
    }


def _calculate_facets(results: List[Any]) -> Dict[str, Dict[str, int]]:
    """Calculate facets from search results."""
    facets = {
        "databases": {},
        "types": {},
        "statuses": {}
    }
    
    for result in results:
        entity = result.entity
        
        # Database facet
        db = entity.get('_database', 'Unknown')
        facets['databases'][db] = facets['databases'].get(db, 0) + 1
        
        # Type facet
        entity_type = entity.get('properties', {}).get('Type', 'Unknown')
        if entity_type:
            facets['types'][str(entity_type)] = facets['types'].get(str(entity_type), 0) + 1
        
        # Status facet
        status = entity.get('properties', {}).get('Status', 'Unknown')
        if status:
            facets['statuses'][str(status)] = facets['statuses'].get(str(status), 0) + 1
    
    # Remove empty facets
    return {k: v for k, v in facets.items() if v}


async def _generate_query_suggestions(query: str, data: List[Dict[str, Any]]) -> List[str]:
    """Generate alternative query suggestions."""
    suggestions = []
    
    # Simple suggestions based on query modification
    words = query.lower().split()
    
    # Try removing words
    if len(words) > 2:
        for i in range(len(words)):
            alt = ' '.join(words[:i] + words[i+1:])
            suggestions.append(alt)
    
    # Try partial matches
    if len(query) > 5:
        suggestions.append(query[:len(query)//2] + "*")
    
    return suggestions[:5]


def _get_entity_field_weights(entity_type: str) -> Dict[str, float]:
    """Get field weights optimized for entity type."""
    weights = {
        'people': {
            'properties.Name': 3.0,
            'properties.Email': 2.5,
            'properties.Department': 2.0,
            'properties.Role': 2.0,
            'properties.Title': 1.5
        },
        'tasks': {
            'properties.Title': 3.0,
            'properties.Description': 2.0,
            'properties.Status': 1.5,
            'properties.Priority': 1.5,
            'properties.Assignee': 2.0
        },
        'documents': {
            'properties.Title': 3.0,
            'properties.Content': 2.0,
            'properties.Summary': 2.5,
            'properties.Tags': 2.0,
            'properties.Type': 1.5
        },
        'organizations': {
            'properties.Name': 3.0,
            'properties.Description': 2.0,
            'properties.Type': 1.5,
            'properties.Industry': 1.5
        },
        'events': {
            'properties.Title': 3.0,
            'properties.Location': 2.0,
            'properties.Date': 2.0,
            'properties.Description': 1.5
        }
    }
    
    return weights.get(entity_type, {})


def _analyze_relationships(results: List[Any]) -> Dict[str, Any]:
    """Analyze relationships between search results."""
    relationships = {
        "common_properties": {},
        "linked_entities": [],
        "clusters": []
    }
    
    # Find common property values
    property_values = {}
    for result in results:
        for key, value in result.entity.get('properties', {}).items():
            if value and isinstance(value, (str, int, float)):
                if key not in property_values:
                    property_values[key] = {}
                str_value = str(value)
                property_values[key][str_value] = property_values[key].get(str_value, 0) + 1
    
    # Find properties that appear multiple times
    for prop, values in property_values.items():
        common = {v: count for v, count in values.items() if count > 1}
        if common:
            relationships['common_properties'][prop] = common
    
    return relationships