"""Dashboard endpoints for Streamlit GUI integration."""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException, Depends, Security
import structlog

from .models import (
    DashboardStats, TimelineEvent, ProcessingMetrics, 
    GlobalSearchResults, EntityResult, NetworkGraph,
    EntityRelationships, RelationshipPath, QueueStatus, JobSummary
)
from .auth import get_current_user
from ..config import ConfigManager

logger = structlog.get_logger()

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Helper functions for data collection
async def get_transcript_count() -> Dict[str, int]:
    """Get transcript count statistics."""
    try:
        config = ConfigManager().load()
        
        # Read from intelligence transcripts JSON file
        transcripts_file = Path("blackcore/models/json/intelligence_transcripts.json")
        if transcripts_file.exists():
            with open(transcripts_file, 'r') as f:
                data = json.load(f)
                total = len(data.get("Intelligence & Transcripts", []))
                
                # Count today's transcripts (simplified - would use actual timestamps)
                today_count = min(3, total)  # Mock data for now
                
                return {
                    "total": total,
                    "today": today_count,
                    "this_week": min(10, total),
                    "this_month": total
                }
        else:
            return {"total": 0, "today": 0, "this_week": 0, "this_month": 0}
            
    except Exception as e:
        logger.error(f"Error getting transcript count: {e}")
        return {"total": 0, "today": 0, "this_week": 0, "this_month": 0}


async def get_entity_counts() -> Dict[str, int]:
    """Get entity count statistics."""
    try:
        entity_counts = {}
        
        # Map of JSON files to entity types
        entity_files = {
            "people": "blackcore/models/json/people_places.json",
            "organizations": "blackcore/models/json/organizations_bodies.json", 
            "tasks": "blackcore/models/json/actionable_tasks.json",
            "events": "blackcore/models/json/places_events.json",
            "documents": "blackcore/models/json/documents_evidence.json",
            "transgressions": "blackcore/models/json/identified_transgressions.json"
        }
        
        for entity_type, file_path in entity_files.items():
            try:
                json_file = Path(file_path)
                if json_file.exists():
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        # Get the main data key (varies by file)
                        main_key = list(data.keys())[0] if data else None
                        if main_key and isinstance(data[main_key], list):
                            entity_counts[entity_type] = len(data[main_key])
                            entity_counts[f"{entity_type}_new"] = min(2, len(data[main_key]))  # Mock new count
                        else:
                            entity_counts[entity_type] = 0
                            entity_counts[f"{entity_type}_new"] = 0
                else:
                    entity_counts[entity_type] = 0
                    entity_counts[f"{entity_type}_new"] = 0
            except Exception as e:
                logger.error(f"Error reading {entity_type} file: {e}")
                entity_counts[entity_type] = 0
                entity_counts[f"{entity_type}_new"] = 0
                
        return entity_counts
        
    except Exception as e:
        logger.error(f"Error getting entity counts: {e}")
        return {}


async def get_processing_stats() -> Dict[str, Any]:
    """Get processing performance statistics."""
    # Mock data for now - would integrate with actual job tracking
    return {
        "avg_processing_time": 25.3,
        "success_rate": 0.94,
        "entities_per_transcript": 4.2,
        "relationships_per_transcript": 2.8,
        "cache_hit_rate": 0.73,
        "total_processed": 47,
        "failed_jobs": 3
    }


async def get_recent_activity() -> List[Dict[str, Any]]:
    """Get recent activity timeline."""
    # Mock recent activity data - would integrate with actual event tracking
    base_time = datetime.utcnow()
    
    activities = [
        {
            "id": "act_001",
            "timestamp": (base_time - timedelta(minutes=15)).isoformat(),
            "event_type": "transcript_processed",
            "title": "Council Meeting Transcript Processed",
            "description": "Extracted 6 entities, 4 relationships",
            "entity_type": "transcript",
            "entity_id": "trans_001"
        },
        {
            "id": "act_002", 
            "timestamp": (base_time - timedelta(hours=2)).isoformat(),
            "event_type": "transgression_identified",
            "title": "New Procedural Violation Identified",
            "description": "Potential conflict of interest in planning decision",
            "entity_type": "transgression",
            "entity_id": "trans_002"
        },
        {
            "id": "act_003",
            "timestamp": (base_time - timedelta(hours=4)).isoformat(), 
            "event_type": "entity_linked",
            "title": "New Relationship Mapped",
            "description": "Mayor linked to construction project",
            "entity_type": "relationship",
            "entity_id": "rel_001"
        },
        {
            "id": "act_004",
            "timestamp": (base_time - timedelta(hours=6)).isoformat(),
            "event_type": "batch_completed",
            "title": "Batch Processing Completed", 
            "description": "5 transcripts processed successfully",
            "entity_type": "batch",
            "entity_id": "batch_001"
        }
    ]
    
    return activities


# Dashboard endpoints
@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: Dict[str, Any] = Security(get_current_user)):
    """Get real-time dashboard statistics."""
    try:
        # Parallel data collection for performance
        stats_tasks = [
            get_transcript_count(),
            get_entity_counts(),
            get_processing_stats(),
            get_recent_activity()
        ]
        
        transcript_count, entity_counts, processing_stats, recent_activity = \
            await asyncio.gather(*stats_tasks)
        
        return DashboardStats(
            transcripts=transcript_count,
            entities=entity_counts,
            processing=processing_stats,
            recent_activity=recent_activity,
            last_updated=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard stats")


@router.get("/timeline", response_model=List[TimelineEvent])
async def get_timeline_events(
    days: int = Query(default=7, ge=1, le=30),
    entity_type: Optional[str] = Query(default=None),
    current_user: Dict[str, Any] = Security(get_current_user)
):
    """Get timeline of intelligence events."""
    try:
        # Get recent activity and filter by timeframe
        recent_activity = await get_recent_activity()
        
        # Filter by entity type if specified
        if entity_type:
            recent_activity = [
                activity for activity in recent_activity 
                if activity.get("entity_type") == entity_type
            ]
        
        # Convert to TimelineEvent objects
        events = [
            TimelineEvent(
                id=activity["id"],
                timestamp=datetime.fromisoformat(activity["timestamp"].replace("Z", "+00:00")),
                event_type=activity["event_type"],
                title=activity["title"], 
                description=activity["description"],
                entity_type=activity.get("entity_type"),
                entity_id=activity.get("entity_id")
            )
            for activity in recent_activity
        ]
        
        return events
        
    except Exception as e:
        logger.error(f"Timeline events error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch timeline events")


@router.get("/metrics", response_model=ProcessingMetrics)
async def get_processing_metrics(current_user: Dict[str, Any] = Security(get_current_user)):
    """Get processing performance metrics."""
    try:
        stats = await get_processing_stats()
        
        return ProcessingMetrics(
            avg_processing_time=stats.get("avg_processing_time", 0.0),
            success_rate=stats.get("success_rate", 0.0),
            entities_per_transcript=stats.get("entities_per_transcript", 0.0),
            relationships_per_transcript=stats.get("relationships_per_transcript", 0.0),
            cache_hit_rate=stats.get("cache_hit_rate", 0.0)
        )
        
    except Exception as e:
        logger.error(f"Processing metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch processing metrics")