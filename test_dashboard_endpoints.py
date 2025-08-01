"""Simplified dashboard endpoints for GUI testing without authentication."""

import json
from typing import Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
import structlog

from blackcore.minimal.api.models import DashboardStats, TimelineEvent, ProcessingMetrics

logger = structlog.get_logger()
router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get comprehensive dashboard statistics."""
    try:
        base_path = Path("blackcore/models/json")
        
        # Initialize stats structure
        stats = {
            "transcripts": {"total": 0, "today": 0, "this_week": 0},
            "entities": {},
            "processing": {"success_rate": 0.0, "avg_processing_time": 0.0},
            "recent_activity": [],
            "last_updated": datetime.now()
        }
        
        # Count entities from JSON files
        entity_files = {
            "people": "people_places.json",
            "organizations": "organizations_bodies.json", 
            "tasks": "actionable_tasks.json",
            "documents": "documents_evidence.json",
            "transgressions": "identified_transgressions.json",
            "transcripts": "intelligence_transcripts.json"
        }
        
        for entity_type, filename in entity_files.items():
            file_path = base_path / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle different JSON structures
                    if isinstance(data, dict):
                        # Find the main data array
                        main_key = next((k for k in data.keys() if isinstance(data[k], list)), None)
                        if main_key:
                            count = len(data[main_key])
                        else:
                            count = len(data)
                    elif isinstance(data, list):
                        count = len(data)
                    else:
                        count = 1
                    
                    stats["entities"][entity_type] = count
                    
                    # Special handling for transcripts
                    if entity_type == "transcripts":
                        stats["transcripts"]["total"] = count
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse {filename}")
                    stats["entities"][entity_type] = 0
            else:
                stats["entities"][entity_type] = 0
        
        # Mock recent activity
        stats["recent_activity"] = [
            {
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "type": "transcript_processed",
                "description": "Processed council meeting transcript",
                "entity_count": 5
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "type": "entities_extracted", 
                "description": "Extracted 3 new organizations",
                "entity_count": 3
            }
        ]
        
        # Mock processing stats
        stats["processing"]["success_rate"] = 95.0
        stats["processing"]["avg_processing_time"] = 45.2
        
        return DashboardStats(**stats)
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard stats")

@router.get("/timeline", response_model=List[TimelineEvent])
async def get_timeline_events(days: int = 7):
    """Get timeline of recent activities."""
    try:
        # Mock timeline events
        events = []
        base_time = datetime.now()
        
        for i in range(5):
            event_time = base_time - timedelta(hours=i*6)
            events.append(TimelineEvent(
                timestamp=event_time,
                event_type="processing" if i % 2 == 0 else "extraction",
                title=f"Intelligence Report #{10-i}",
                description=f"Processed meeting transcript with {3+i} entities extracted",
                entities_affected=3+i,
                severity="info"
            ))
        
        return events
        
    except Exception as e:
        logger.error(f"Timeline error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load timeline")

@router.get("/metrics", response_model=ProcessingMetrics)
async def get_processing_metrics():
    """Get processing performance metrics."""
    try:
        return ProcessingMetrics(
            total_processed=156,
            success_rate=95.5,
            avg_processing_time=42.3,
            entities_extracted=847,
            error_rate=4.5,
            last_24h_processed=23,
            performance_trend="stable"
        )
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load metrics")