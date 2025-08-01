"""Search endpoints for Streamlit GUI integration."""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException, Security
import structlog

from .models import GlobalSearchResults, EntityResult
from .auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/search", tags=["Search"])


def search_in_json_data(data: List[Dict], query: str, entity_type: str) -> List[Dict[str, Any]]:
    """Search within JSON data for query terms."""
    results = []
    query_lower = query.lower()
    
    for item in data:
        relevance_score = 0.0
        matching_fields = []
        
        # Search in all string fields
        for key, value in item.items():
            if isinstance(value, str) and query_lower in value.lower():
                # Higher score for title/name matches
                if key.lower() in ['name', 'title', 'event / place name', 'transgression summary']:
                    relevance_score += 0.6
                    matching_fields.append(f"{key}: {value}")
                else:
                    relevance_score += 0.3
                    matching_fields.append(f"{key}: {value[:100]}...")
        
        if relevance_score > 0:
            # Create snippet from matching fields
            snippet = " | ".join(matching_fields[:2])
            
            results.append({
                "id": item.get("id", f"{entity_type}_{hash(str(item))}"),
                "type": entity_type,
                "title": item.get("Name") or item.get("Event / Place Name") or 
                        item.get("Transgression Summary") or item.get("Task Name") or
                        item.get("Document Title") or str(item.get("Request Name", "Unknown")),
                "properties": item,
                "relevance_score": min(relevance_score, 1.0),
                "snippet": snippet
            })
    
    return sorted(results, key=lambda x: x["relevance_score"], reverse=True)


@router.get("/global", response_model=GlobalSearchResults)
async def global_search(
    query: str = Query(..., min_length=2, max_length=200),
    entity_types: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    include_relationships: bool = Query(default=True),
    current_user: Dict[str, Any] = Security(get_current_user)
):
    """Global search across all databases."""
    try:
        start_time = time.time()
        all_results = []
        
        # Define searchable databases
        searchable_databases = {
            "people": {
                "file": "blackcore/models/json/people_places.json",
                "key": "People & Contacts"
            },
            "organizations": {
                "file": "blackcore/models/json/organizations_bodies.json", 
                "key": "Organizations & Bodies"
            },
            "tasks": {
                "file": "blackcore/models/json/actionable_tasks.json",
                "key": "Actionable Tasks"
            },
            "events": {
                "file": "blackcore/models/json/places_events.json",
                "key": "Key Places & Events"
            },
            "documents": {
                "file": "blackcore/models/json/documents_evidence.json",
                "key": "Documents & Evidence"
            },
            "transgressions": {
                "file": "blackcore/models/json/identified_transgressions.json",
                "key": "Identified Transgressions"
            }
        }
        
        # Filter by entity types if specified
        if entity_types:
            searchable_databases = {
                k: v for k, v in searchable_databases.items() 
                if k in entity_types
            }
        
        # Search each database
        for entity_type, db_info in searchable_databases.items():
            try:
                json_file = Path(db_info["file"])
                if json_file.exists():
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                    # Get the data array
                    entity_data = data.get(db_info["key"], [])
                    if isinstance(entity_data, list):
                        # Search in this entity type
                        results = search_in_json_data(entity_data, query, entity_type)
                        all_results.extend(results)
                        
            except Exception as e:
                logger.error(f"Error searching {entity_type}: {e}")
                continue
        
        # Sort by relevance and limit results
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        limited_results = all_results[:limit]
        
        # Generate search suggestions
        suggestions = await get_search_suggestions(query)
        
        search_time = time.time() - start_time
        
        return GlobalSearchResults(
            query=query,
            total_results=len(limited_results),
            results=limited_results,
            search_time=search_time,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/entities/{entity_type}", response_model=List[EntityResult])
async def search_entities(
    entity_type: str,
    query: str = Query(...),
    limit: int = Query(default=20),
    current_user: Dict[str, Any] = Security(get_current_user)
):
    """Search within specific entity type."""
    valid_types = ["people", "organizations", "tasks", "events", "documents", "transgressions"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")
    
    try:
        # Map entity type to file and key
        type_mapping = {
            "people": ("blackcore/models/json/people_places.json", "People & Contacts"),
            "organizations": ("blackcore/models/json/organizations_bodies.json", "Organizations & Bodies"),
            "tasks": ("blackcore/models/json/actionable_tasks.json", "Actionable Tasks"),
            "events": ("blackcore/models/json/places_events.json", "Key Places & Events"),
            "documents": ("blackcore/models/json/documents_evidence.json", "Documents & Evidence"),
            "transgressions": ("blackcore/models/json/identified_transgressions.json", "Identified Transgressions")
        }
        
        file_path, data_key = type_mapping[entity_type]
        json_file = Path(file_path)
        
        if not json_file.exists():
            return []
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        entity_data = data.get(data_key, [])
        if not isinstance(entity_data, list):
            return []
        
        # Search within this entity type
        results = search_in_json_data(entity_data, query, entity_type)
        
        # Convert to EntityResult objects
        entity_results = [
            EntityResult(
                id=result["id"],
                type=result["type"],
                title=result["title"],
                properties=result["properties"],
                relevance_score=result["relevance_score"],
                snippet=result.get("snippet")
            )
            for result in results
        ]
        
        return entity_results
        
    except Exception as e:
        logger.error(f"Entity search error: {e}")
        raise HTTPException(status_code=500, detail="Entity search failed")


@router.get("/suggestions", response_model=List[str])
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    current_user: Dict[str, Any] = Security(get_current_user)
):
    """Get search query suggestions."""
    try:
        # Generate suggestions based on common terms and entity names
        suggestions = []
        query_lower = query.lower()
        
        # Common campaign-related search terms
        common_terms = [
            "shore road", "swanage", "council", "mayor", "planning", "development",
            "dorset coast forum", "consultation", "traffic", "parking", "residents",
            "meeting", "decision", "vote", "proposal", "objection", "support"
        ]
        
        # Add matching common terms
        for term in common_terms:
            if query_lower in term.lower() and term not in suggestions:
                suggestions.append(term)
        
        # Add partial matches from entity names (simplified)
        if len(query) >= 2:
            entity_suggestions = [
                "Mayor Sutton", "Councillor Nocturne", "Town Clerk Martin",
                "Swanage Town Council", "Dorset Coast Forum", "West Coast Developments",
                "Shore Road Closure", "Car Park Development", "Public Consultation"
            ]
            
            for suggestion in entity_suggestions:
                if query_lower in suggestion.lower() and suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        return suggestions[:5]  # Limit to 5 suggestions
        
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return []