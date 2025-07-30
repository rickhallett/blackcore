"""Utility functions for minimal transcript processor."""

import json
from pathlib import Path
from typing import Dict, List, Any, Union
from datetime import datetime

from .models import TranscriptInput, TranscriptSource


def load_transcript_from_file(file_path: Union[str, Path]) -> TranscriptInput:
    """Load a transcript from a JSON or text file.

    Args:
        file_path: Path to the file

    Returns:
        TranscriptInput object

    Raises:
        ValueError: If file format is not supported
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix == ".json":
        # Load JSON transcript
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert to TranscriptInput
        return TranscriptInput(**data)

    elif path.suffix in [".txt", ".md"]:
        # Load plain text transcript
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Use filename as title
        title = path.stem.replace("_", " ").title()

        # Try to extract date from filename (common patterns)
        date = None
        import re

        date_patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
            r"(\d{2}-\d{2}-\d{4})",  # MM-DD-YYYY
            r"(\d{8})",  # YYYYMMDD
        ]

        for pattern in date_patterns:
            match = re.search(pattern, path.stem)
            if match:
                date_str = match.group(1)
                try:
                    if len(date_str) == 8 and "-" not in date_str:
                        # YYYYMMDD format
                        date = datetime.strptime(date_str, "%Y%m%d")
                    elif "-" in date_str:
                        if date_str.count("-") == 2:
                            if len(date_str.split("-")[0]) == 4:
                                date = datetime.strptime(date_str, "%Y-%m-%d")
                            else:
                                date = datetime.strptime(date_str, "%m-%d-%Y")
                except ValueError:
                    pass
                break

        return TranscriptInput(
            title=title,
            content=content,
            date=date,
            source=TranscriptSource.PERSONAL_NOTE,
        )

    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def load_transcripts_from_directory(
    dir_path: Union[str, Path],
) -> List[TranscriptInput]:
    """Load all transcripts from a directory.

    Args:
        dir_path: Path to directory containing transcript files

    Returns:
        List of TranscriptInput objects
    """
    path = Path(dir_path)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    transcripts = []

    # Look for JSON and text files
    for file_path in path.iterdir():
        if file_path.suffix in [".json", ".txt", ".md"]:
            try:
                transcript = load_transcript_from_file(file_path)
                transcripts.append(transcript)
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")

    # Sort by date if available
    transcripts.sort(key=lambda t: t.date or datetime.min)

    return transcripts


def save_processing_result(
    result: Dict[str, Any], output_path: Union[str, Path]
) -> None:
    """Save processing result to a JSON file.

    Args:
        result: Processing result dictionary
        output_path: Path to save the result
    """
    path = Path(output_path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)


def format_entity_summary(entities: List[Dict[str, Any]]) -> str:
    """Format a human-readable summary of extracted entities.

    Args:
        entities: List of entity dictionaries

    Returns:
        Formatted string summary
    """
    if not entities:
        return "No entities extracted."

    summary = []

    # Group by type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for entity in entities:
        entity_type = entity.get("type", "unknown")
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(entity)

    # Format each type
    for entity_type, type_entities in by_type.items():
        summary.append(f"\n{entity_type.upper()} ({len(type_entities)}):")
        for entity in type_entities[:5]:  # Show first 5
            name = entity.get("name", "Unnamed")
            confidence = entity.get("confidence", 1.0)

            line = f"  • {name}"
            if confidence < 1.0:
                line += f" (confidence: {confidence:.0%})"

            # Add key properties
            props = entity.get("properties", {})
            if props:
                prop_strs = []
                for key, value in list(props.items())[:3]:  # First 3 properties
                    prop_strs.append(f"{key}: {value}")
                if prop_strs:
                    line += f" - {', '.join(prop_strs)}"

            summary.append(line)

        if len(type_entities) > 5:
            summary.append(f"  ... and {len(type_entities) - 5} more")

    return "\n".join(summary)


def validate_config_databases(config: Dict[str, Any]) -> List[str]:
    """Validate that all required database IDs are configured.

    Args:
        config: Configuration dictionary

    Returns:
        List of warning messages for missing configurations
    """
    warnings = []

    databases = config.get("notion", {}).get("databases", {})

    required_databases = [
        "people",
        "organizations",
        "tasks",
        "transcripts",
        "transgressions",
    ]

    for db_name in required_databases:
        db_config = databases.get(db_name, {})
        if not db_config.get("id"):
            warnings.append(f"Database ID not configured for '{db_name}'")

    return warnings


def create_sample_transcript() -> Dict[str, Any]:
    """Create a sample transcript for testing.

    Returns:
        Sample transcript dictionary
    """
    return {
        "title": "Meeting with Mayor - Beach Hut Survey Discussion",
        "content": """Meeting held on January 9, 2025 with Mayor John Smith of Swanage Town Council.

Present:
- Mayor John Smith (Swanage Town Council)
- Sarah Johnson (Council Planning Department)
- Mark Wilson (Community Representative)

Discussion Points:

1. Beach Hut Survey Concerns
The Mayor expressed concerns about the methodology used in the recent beach hut survey. 
He stated that the survey failed to capture input from long-term residents and focused 
primarily on tourist opinions.

Sarah Johnson from Planning noted that the survey was conducted according to standard 
procedures but acknowledged that the timing (during peak tourist season) may have 
skewed results.

2. Action Items
- Mark Wilson to organize a community meeting for resident feedback (Due: January 20)
- Planning Department to review survey methodology (Due: February 1)
- Mayor to draft letter to county council highlighting concerns

3. Identified Issues
The Mayor's dismissal of resident concerns in favor of tourist revenue appears to be 
a pattern. This represents a potential breach of his duty to represent constituents.

Next meeting scheduled for January 25, 2025.""",
        "date": "2025-01-09T14:00:00",
        "source": "voice_memo",
        "metadata": {"duration_minutes": 45, "location": "Town Hall Conference Room B"},
    }


def create_sample_config() -> Dict[str, Any]:
    """Create a sample configuration for testing.

    Returns:
        Sample configuration dictionary
    """
    return {
        "notion": {
            "api_key": "YOUR_NOTION_API_KEY",
            "databases": {
                "people": {
                    "id": "YOUR_PEOPLE_DB_ID",
                    "mappings": {
                        "name": "Full Name",
                        "role": "Role",
                        "organization": "Organization",
                    },
                },
                "organizations": {
                    "id": "YOUR_ORG_DB_ID",
                    "mappings": {"name": "Organization Name", "category": "Category"},
                },
                "tasks": {
                    "id": "YOUR_TASKS_DB_ID",
                    "mappings": {
                        "name": "Task Name",
                        "assignee": "Assignee",
                        "due_date": "Due Date",
                        "status": "Status",
                    },
                },
                "transcripts": {
                    "id": "YOUR_TRANSCRIPTS_DB_ID",
                    "mappings": {
                        "title": "Entry Title",
                        "date": "Date Recorded",
                        "content": "Raw Transcript/Note",
                        "summary": "AI Summary",
                        "entities": "Tagged Entities",
                        "status": "Processing Status",
                    },
                },
                "transgressions": {
                    "id": "YOUR_TRANSGRESSIONS_DB_ID",
                    "mappings": {
                        "summary": "Transgression Summary",
                        "perpetrator_person": "Perpetrator (Person)",
                        "perpetrator_org": "Perpetrator (Org)",
                        "severity": "Severity",
                    },
                },
            },
            "rate_limit": 3.0,
            "retry_attempts": 3,
        },
        "ai": {
            "provider": "claude",
            "api_key": "YOUR_AI_API_KEY",
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4000,
            "temperature": 0.3,
        },
        "processing": {
            "batch_size": 10,
            "cache_ttl": 3600,
            "dry_run": False,
            "verbose": True,
        },
    }
