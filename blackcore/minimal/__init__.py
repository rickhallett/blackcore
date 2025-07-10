"""Minimal transcript processing module for Notion updates.

This module provides a streamlined implementation focused on:
- Processing transcripts (JSON/text)
- Extracting entities using AI
- Updating Notion databases
- High test coverage without enterprise complexity
"""

from .transcript_processor import TranscriptProcessor
from .ai_extractor import AIExtractor
from .notion_updater import NotionUpdater
from .models import TranscriptInput, ProcessingResult, ExtractedEntities, Entity, Relationship

__all__ = [
    "TranscriptProcessor",
    "AIExtractor",
    "NotionUpdater",
    "TranscriptInput",
    "ProcessingResult",
    "ExtractedEntities",
    "Entity",
    "Relationship",
]

__version__ = "0.1.0"
