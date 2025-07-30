#!/usr/bin/env python3
"""
Debug property preparation to see what's being sent to Notion.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.staged_json_sync import StagedJSONSyncProcessor


def debug_property_preparation():
    """Debug what properties are being prepared for a sample record."""

    # Initialize processor
    config_path = Path(__file__).parent.parent / "sync_config_prod.json"
    processor = StagedJSONSyncProcessor(config_path=str(config_path))

    # Sample record from People & Contacts
    sample_record = {
        "Full Name": "Test Person",
        "Role": "Ally",
        "Status": "Active Engagement",
        "Notes": "Test notes",
        "Email": "test@example.com",
    }

    # Get database config
    db_config = processor.notion_config["People & Contacts"]

    print("Database config:")
    print(json.dumps(db_config, indent=2))

    # Transform the record
    mapping_config = processor.property_mappings.get("People & Contacts", {})
    transformed = processor.transformer.transform_record(
        sample_record, mapping_config, "People & Contacts", stage=1
    )

    print("\nTransformed record:")
    print(json.dumps(transformed, indent=2))

    # Prepare properties
    properties = processor._prepare_properties(transformed, db_config)

    print("\nPrepared properties for Notion API:")
    print(json.dumps(properties, indent=2))

    # Check schema
    schema = None
    for db_id, db_schema in processor.notion_schemas.items():
        if db_schema.get("title") == "People & Contacts":
            schema = db_schema
            break

    if schema:
        print("\nDatabase schema properties:")
        for prop_name, prop_info in schema["properties"].items():
            print(f"  {prop_name}: {prop_info['type']}")


if __name__ == "__main__":
    debug_property_preparation()
