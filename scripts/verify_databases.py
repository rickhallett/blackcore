#!/usr/bin/env python3
"""Verification script to check Project Nassau databases in Notion."""

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path to import blackcore modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.notion.client import NotionClient
from blackcore.notion.schemas.all_databases import get_all_database_schemas
from dotenv import load_dotenv


def load_database_ids() -> Dict[str, str]:
    """Load saved database IDs from file.

    Returns:
        Dictionary mapping database names to IDs
    """
    db_ids = {}
    db_ids_path = Path(".database_ids")

    if db_ids_path.exists():
        with open(db_ids_path, "r") as f:
            for line in f:
                if "=" in line:
                    name, db_id = line.strip().split("=", 1)
                    db_ids[name] = db_id

    return db_ids


def verify_database_properties(client: NotionClient, db_name: str, db_id: str) -> List[str]:
    """Verify that a database has all expected properties.

    Args:
        client: Notion client
        db_name: Database name
        db_id: Database ID

    Returns:
        List of missing properties
    """
    schemas = get_all_database_schemas()
    expected_schema = None

    for schema in schemas:
        if schema.name == db_name:
            expected_schema = schema
            break

    if not expected_schema:
        return [f"Schema not found for {db_name}"]

    try:
        database = client.get_database(db_id)
        actual_properties = set(database.get("properties", {}).keys())
        expected_properties = set(prop.name for prop in expected_schema.properties)

        missing = expected_properties - actual_properties
        return list(missing)

    except Exception as e:
        return [f"Error accessing database: {e}"]


def main():
    """Main verification function."""
    print("=== Project Nassau Database Verification ===\n")

    # Load environment variables
    load_dotenv()

    try:
        # Initialize Notion client
        client = NotionClient()

        # Get expected databases
        schemas = get_all_database_schemas()
        expected_names = [schema.name for schema in schemas]

        print(f"Expected databases: {len(expected_names)}")

        # Search for existing databases
        print("\nSearching for databases...")
        found_databases = {}

        for name in expected_names:
            results = client.search_databases(name)
            if results:
                found_databases[name] = results[0]["id"]
                print(f"✓ Found: {name}")
            else:
                print(f"✗ Missing: {name}")

        # Load saved database IDs
        saved_ids = load_database_ids()

        # Compare found vs saved
        if saved_ids:
            print(f"\nSaved database IDs: {len(saved_ids)}")
            for name, saved_id in saved_ids.items():
                if name in found_databases:
                    if found_databases[name] != saved_id:
                        print(f"⚠ ID mismatch for {name}")
                else:
                    print(f"⚠ Saved but not found: {name}")

        # Verify properties for found databases
        print("\nVerifying database properties...")
        all_valid = True

        for name, db_id in found_databases.items():
            missing_props = verify_database_properties(client, name, db_id)
            if missing_props:
                all_valid = False
                print(f"\n✗ {name} is missing properties:")
                for prop in missing_props:
                    print(f"  - {prop}")
            else:
                print(f"✓ {name} has all expected properties")

        # Summary
        print("\n=== Summary ===")
        print(f"Total expected: {len(expected_names)}")
        print(f"Total found: {len(found_databases)}")
        print(f"Missing: {len(expected_names) - len(found_databases)}")

        if len(found_databases) == len(expected_names) and all_valid:
            print("\n✅ All databases verified successfully!")
            return 0
        else:
            print("\n⚠ Some databases are missing or incomplete.")
            print("Run 'python scripts/setup_databases.py' to create missing databases.")
            return 1

    except ValueError as e:
        print(f"\nError: {e}")
        print("Please ensure NOTION_API_KEY is set in your .env file.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
