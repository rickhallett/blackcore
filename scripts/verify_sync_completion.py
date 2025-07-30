#!/usr/bin/env python3
"""
Verify Sync Completion - Check how many pages were created in each database.
"""

import os
import json
import sys
from pathlib import Path
from notion_client import Client

# Set environment
os.environ["NOTION_API_KEY"] = "***REMOVED***"
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Check sync completion status."""
    client = Client(auth=os.environ["NOTION_API_KEY"])

    # Load config
    config_path = Path(__file__).parent.parent / "blackcore/config/notion_config.json"
    with open(config_path) as f:
        config = json.load(f)

    total_created = 0
    print("🔍 SYNC COMPLETION VERIFICATION")
    print("=" * 50)

    for db_name, db_config in config.items():
        database_id = db_config["id"]

        try:
            # Query database to get page count
            response = client.databases.query(database_id=database_id)
            page_count = len(response["results"])

            # Check if there are more pages
            while response.get("has_more"):
                response = client.databases.query(
                    database_id=database_id, start_cursor=response["next_cursor"]
                )
                page_count += len(response["results"])

            print(f"{db_name}: {page_count} pages")
            total_created += page_count

        except Exception as e:
            print(f"{db_name}: ❌ Error - {e}")

    print("=" * 50)
    print(f"📊 TOTAL PAGES IN NOTION: {total_created}")

    # Expected totals from our data
    expected_totals = {
        "People & Contacts": 43,
        "Organizations & Bodies": 8,
        "Agendas & Epics": 12,
        "Documents & Evidence": 8,
        "Intelligence & Transcripts": 14,
        "Identified Transgressions": 6,
        "Actionable Tasks": 6,
        "Key Places & Events": 9,
    }

    expected_total = sum(expected_totals.values())
    print(f"📈 EXPECTED TOTAL: {expected_total}")
    print(f"✅ SUCCESS RATE: {(total_created/expected_total*100):.1f}%")

    if total_created >= expected_total * 0.9:  # 90% success rate
        print("\n🎉 SYNC COMPLETED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  Sync appears incomplete")
        return 1


if __name__ == "__main__":
    sys.exit(main())
