"""Simplified search endpoints for GUI testing without authentication."""

import json
from typing import Dict, List, Any
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
import structlog

from blackcore.minimal.api.models import GlobalSearchResults, EntityResult

logger = structlog.get_logger()
router = APIRouter()

@router.get("/global", response_model=GlobalSearchResults)
async def global_search(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=20)
):
    """Search across all intelligence databases."""
    try:
        # Search in JSON files
        results = []
        base_path = Path("blackcore/models/json")
        
        search_files = {
            "people": ("people_places.json", "People & Contacts"),
            "organizations": ("organizations_bodies.json", "Organizations & Bodies"),
            "tasks": ("actionable_tasks.json", "Actionable Tasks"),
            "documents": ("documents_evidence.json", "Documents & Evidence"),
            "transgressions": ("identified_transgressions.json", "Identified Transgressions")
        }
        
        query_lower = query.lower()
        
        for entity_type, (filename, data_key) in search_files.items():
            file_path = base_path / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Get the main data array
                    items = data.get(data_key, []) if isinstance(data, dict) else data
                    
                    for item in items:
                        if isinstance(item, dict):
                            # Search in all text fields
                            text_content = ' '.join(str(v) for v in item.values() if isinstance(v, (str, int, float)))
                            if query_lower in text_content.lower():
                                
                                # Get title/name field
                                title = (item.get('Full Name') or 
                                        item.get('Name') or 
                                        item.get('Title') or 
                                        item.get('Organization Name') or
                                        str(list(item.values())[0]))
                                
                                # Calculate relevance score (simple)
                                score = text_content.lower().count(query_lower) / len(text_content) * 100
                                
                                results.append(EntityResult(
                                    id=str(hash(str(item))),
                                    type=entity_type,
                                    title=title,
                                    snippet=text_content[:200] + "..." if len(text_content) > 200 else text_content,
                                    relevance_score=min(score, 100.0),
                                    properties={"source": filename, "raw_data": item}
                                ))
                                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse {filename}")
                    continue
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        results = results[:limit]
        
        # Convert EntityResult objects to dictionaries
        results_dict = [result.dict() for result in results]
        
        return GlobalSearchResults(
            query=query,
            total_results=len(results),
            results=results_dict,
            search_time=50.0,  # Mock timing in milliseconds
            suggestions=[]
        )
        
    except Exception as e:
        logger.error(f"Global search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/entities/{entity_type}", response_model=List[EntityResult])
async def search_entities(
    entity_type: str,
    query: str = Query(...),
    limit: int = Query(default=20)
):
    """Search within specific entity type."""
    valid_types = ["people", "organizations", "tasks", "events", "documents", "transgressions"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")
    
    try:
        # Map entity type to file and key
        type_mapping = {
            "people": ("people_places.json", "People & Contacts"),
            "organizations": ("organizations_bodies.json", "Organizations & Bodies"),
            "tasks": ("actionable_tasks.json", "Actionable Tasks"),
            "events": ("places_events.json", "Key Places & Events"),
            "documents": ("documents_evidence.json", "Documents & Evidence"),
            "transgressions": ("identified_transgressions.json", "Identified Transgressions")
        }
        
        if entity_type not in type_mapping:
            return []
        
        filename, data_key = type_mapping[entity_type]
        file_path = Path(f"blackcore/models/json/{filename}")
        
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get(data_key, []) if isinstance(data, dict) else data
        results = []
        query_lower = query.lower()
        
        for item in items:
            if isinstance(item, dict):
                text_content = ' '.join(str(v) for v in item.values() if isinstance(v, (str, int, float)))
                if query_lower in text_content.lower():
                    
                    title = (item.get('Full Name') or 
                            item.get('Name') or 
                            item.get('Title') or 
                            item.get('Organization Name') or
                            str(list(item.values())[0]))
                    
                    score = text_content.lower().count(query_lower) / len(text_content) * 100
                    
                    results.append(EntityResult(
                        id=str(hash(str(item))),
                        type=entity_type,
                        title=title,
                        snippet=text_content[:200] + "..." if len(text_content) > 200 else text_content,
                        relevance_score=min(score, 100.0),
                        properties={"source": filename, "raw_data": item}
                    ))
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Entity search error: {e}")
        raise HTTPException(status_code=500, detail="Entity search failed")

@router.get("/suggestions", response_model=List[str])
async def get_search_suggestions(query: str = Query(..., min_length=1)):
    """Get search query suggestions."""
    try:
        # Generate suggestions based on common terms
        suggestions = []
        query_lower = query.lower()
        
        # Common campaign-related search terms
        common_terms = [
            "shore road", "swanage", "council", "mayor", "planning", "development",
            "dorset coast forum", "consultation", "traffic", "parking", "residents",
            "heritage", "tourism", "local business", "environmental", "petition"
        ]
        
        # Filter suggestions that match the query
        for term in common_terms:
            if query_lower in term.lower() or any(word in term.lower() for word in query_lower.split()):
                suggestions.append(term)
        
        return suggestions[:5]  # Limit to 5 suggestions
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return []