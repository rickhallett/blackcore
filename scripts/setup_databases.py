#!/usr/bin/env python3
"""Setup script to create all Project Nassau databases in Notion."""

import os
import sys
from pathlib import Path

# Add parent directory to path to import blackcore modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.notion.client import NotionClient
from blackcore.notion.database_creator import DatabaseCreator
from dotenv import load_dotenv


def main():
    """Main function to set up all databases."""
    print("=== Project Nassau Database Setup ===\n")

    # Load environment variables
    load_dotenv()

    # Get parent page ID
    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
    if not parent_page_id:
        print("Please provide the parent page ID where databases should be created.")
        print("You can find this in the URL when viewing the page in Notion.")
        print("Example: https://www.notion.so/Page-Name-XXXXXXXXXXXXX")
        print("The ID is the part after the last dash (XXXXXXXXXXXXX)\n")

        parent_page_id = input("Enter parent page ID: ").strip()

        if not parent_page_id:
            print("Error: Parent page ID is required.")
            return 1

        # Save for future use
        with open(".env", "a") as f:
            f.write(f"\nNOTION_PARENT_PAGE_ID={parent_page_id}\n")
        print("Saved parent page ID to .env file.\n")

    try:
        # Initialize Notion client
        print("Connecting to Notion API...")
        client = NotionClient()
        print("✓ Connected successfully\n")

        # Initialize database creator
        creator = DatabaseCreator(client, parent_page_id)

        # Create all databases
        database_ids = creator.create_all_databases(check_existing=True)

        if not database_ids:
            print("\nNo databases were created.")
            return 1

        # Verify databases
        print("\nVerifying databases...")
        successful, missing = creator.verify_databases()

        if missing:
            print(f"\nWarning: {len(missing)} databases could not be verified:")
            for db in missing:
                print(f"  - {db}")

        # Generate and save report
        report = creator.get_database_report()
        print("\n" + report)

        # Save report to file
        report_path = Path("database_report.txt")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Report saved to: {report_path}")

        # Save database IDs for future use
        db_ids_path = Path(".database_ids")
        with open(db_ids_path, "w") as f:
            for name, db_id in database_ids.items():
                f.write(f"{name}={db_id}\n")
        print(f"Database IDs saved to: {db_ids_path}")

        print("\n✅ Database setup complete!")
        return 0

    except ValueError as e:
        print(f"\nError: {e}")
        print("Please ensure NOTION_API_KEY is set in your .env file.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
