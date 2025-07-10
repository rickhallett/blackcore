#!/usr/bin/env python3
"""
Script to ingest a structured intelligence package (JSON) into Notion.
This script will create or update pages in the Project Nassau databases.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Union

# Add parent directory to path to import blackcore modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.notion.client import NotionClient
from blackcore.notion.database_creator import DatabaseCreator
from dotenv import load_dotenv

# This map is the "brain" of the relational linker.
# It defines which fields are relations and which database they point to.
# Key: Source Database Name, Value: {Notion Property Name: Target Database Name}
RELATION_FIELD_MAP = {
    "Actionable Tasks": {
        "Assignee": "People & Contacts",
        "Related Agenda": "Agendas & Epics",
        "Blocked By": "Actionable Tasks",  # Self-referential
    },
    "People & Contacts": {
        "Organization": "Organizations & Bodies",
        "Linked Transgressions": "Identified Transgressions",
    },
    "Organizations & Bodies": {
        "Key People": "People & Contacts",
        "Linked Documents": "Documents & Evidence",
    },
    "Agendas & Epics": {
        "Owner": "People & Contacts",  # Person property is treated as a relation
        "Actionable Tasks": "Actionable Tasks",
        "Key Documents": "Documents & Evidence",
    },
    "Identified Transgressions": {
        "Perpetrator (Person)": "People & Contacts",
        "Perpetrator (Org)": "Organizations & Bodies",
        "Evidence": "Intelligence & Transcripts",  # Can be multi-relation
    },
    "Intelligence & Transcripts": {
        "Tagged Entities": "People & Contacts",  # Can be multi-relation to others too
    },
    "Key Places & Events": {
        "People Involved": "People & Contacts",
        "Related Transgressions": "Identified Transgressions",
    },
}


class IntelligenceIngestor:
    """Handles the ingestion of a structured intelligence package into Notion."""

    def __init__(self, client: NotionClient, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run
        self.id_cache: Dict[str, Dict[str, str]] = {}
        self.data: Dict[str, Any] = {}
        print(f"Ingestor initialized. Dry run: {self.dry_run}")

    def _get_db_id(self, db_name: str) -> str:
        """Helper to get a database ID from the client's cache, raising an error if not found."""
        db_id = self.client.get_cached_database_id(db_name)
        if not db_id:
            raise ValueError(
                f"FATAL: Could not find database ID for '{db_name}'. Ensure it was created."
            )
        return db_id

    def ingest_package(self, package_path: Path):
        """Loads and processes an entire intelligence package."""
        print(f"Loading intelligence package from: {package_path}")
        with open(package_path, "r") as f:
            self.data = json.load(f)

        db_names_from_schema = [schema.name for schema in get_all_database_schemas()]
        for db_name in db_names_from_schema:
            self.id_cache[db_name] = {}

        # --- PASS 1: Create all core objects without linking relations ---
        print("\n--- PASS 1: Creating/Finding core database pages ---")
        self._process_all_items_for_creation()

        # --- PASS 2: Update objects with relations ---
        print("\n--- PASS 2: Linking relations for all objects ---")
        self._link_all_relations()

        print("\n✅ Ingestion complete!")

    def _find_or_create_page(self, db_name: str, title: str, properties: Dict[str, Any]) -> str:
        """Finds a page by title in a DB, or creates it if it doesn't exist."""
        if title in self.id_cache.get(db_name, {}):
            return self.id_cache[db_name][title]

        db_id = self._get_db_id(db_name)

        search_results = self.client.client.databases.query(
            database_id=db_id, filter={"property": "title", "title": {"equals": title}}
        )

        if search_results.get("results"):
            page_id = search_results["results"][0]["id"]
            print(f"  [FOUND] Found '{title}' in {db_name} (ID: {page_id}).")
            self.id_cache[db_name][title] = page_id
            return page_id
        else:
            print(f"  [CREATE] Creating '{title}' in {db_name}...")
            if self.dry_run:
                print("    DRY RUN: Skipping creation.")
                return f"dry-run-id-for-{title}"

            new_page = self.client.client.pages.create(
                parent={"database_id": db_id}, properties=properties
            )
            page_id = new_page["id"]
            self.id_cache[db_name][title] = page_id
            return page_id

    def _build_properties(self, item: Dict[str, Any], db_name: str) -> Dict[str, Any]:
        """Builds a Notion properties object from a JSON item, excluding relations."""
        properties = {}
        relation_fields_for_db = list(RELATION_FIELD_MAP.get(db_name, {}).keys())

        # Map JSON keys to Notion property names and types
        prop_map = {
            # Selects
            "status": ("Status", "select"),
            "role": ("Role", "select"),
            "priority": ("Priority", "select"),
            "phase": ("Phase", "select"),
            "category": ("Category", "select"),
            "severity": ("Severity", "select"),
            "source": ("Source", "select"),
            # Rich Text
            "notes": ("Notes", "rich_text"),
            "description": ("Description", "rich_text"),
            "objective": ("Objective Summary", "rich_text"),
            "rawNote": ("Raw Transcript/Note", "rich_text"),
            # Others
            "email": ("Email", "email"),
            "website": ("Website", "url"),
            "dueDate": ("Due Date", "date"),
            "recordedDate": ("Date Recorded", "date"),
            "date": ("Date of Transgression", "date"),
        }

        for json_key, (notion_name, prop_type) in prop_map.items():
            if json_key in item and notion_name not in relation_fields_for_db:
                value = item[json_key]
                if prop_type == "select":
                    properties[notion_name] = {"select": {"name": value}}
                elif prop_type == "rich_text":
                    properties[notion_name] = {"rich_text": [{"text": {"content": value}}]}
                elif prop_type == "email":
                    properties[notion_name] = {"email": value}
                elif prop_type == "url":
                    properties[notion_name] = {"url": value}
                elif prop_type == "date":
                    properties[notion_name] = {"date": {"start": value}}
        return properties

    def _process_all_items_for_creation(self):
        """Processes all items from the JSON data for creation."""
        # Maps JSON list key to (Database Name, Title Key in JSON)
        db_map = {
            "organizations": ("Organizations & Bodies", "name"),
            "people": ("People & Contacts", "fullName"),
            "agendas": ("Agendas & Epics", "title"),
            "tasks": ("Actionable Tasks", "name"),
            "transgressions": ("Identified Transgressions", "summary"),
            "intelligence": ("Intelligence & Transcripts", "title"),
        }

        for json_key, (db_name, title_key) in db_map.items():
            print(f"\nProcessing creation for '{db_name}'...")
            for item in self.data.get(json_key, []):
                title = item.get(title_key)
                if not title:
                    print(f"  [WARN] Skipping item in '{db_name}' with no '{title_key}'.")
                    continue

                properties = self._build_properties(item, db_name)
                # The title property is always required
                properties["title"] = {"title": [{"text": {"content": title}}]}
                self._find_or_create_page(db_name, title, properties)

    def _link_all_relations(self):
        """Iterates through the entire dataset and links all defined relations."""
        db_map = {
            "tasks": ("Actionable Tasks", "name"),
            "people": ("People & Contacts", "fullName"),
            "agendas": ("Agendas & Epics", "title"),
            "transgressions": ("Identified Transgressions", "summary"),
        }

        # Map JSON keys back to Notion Field names for lookup in RELATION_FIELD_MAP
        json_to_notion_field_map = {
            "assignee": "Assignee",
            "relatedAgenda": "Related Agenda",
            "blockedBy": "Blocked By",
            "organization": "Organization",
            "owner": "Owner",
            "perpetratorOrg": "Perpetrator (Org)",
            "perpetratorPerson": "Perpetrator (Person)",
            "evidence": "Evidence",
        }

        for json_key, (db_name, title_key) in db_map.items():
            if db_name not in RELATION_FIELD_MAP:
                continue

            print(f"\nLinking relations for '{db_name}'...")
            for item in self.data.get(json_key, []):
                source_title = item.get(title_key)
                if not source_title or source_title not in self.id_cache.get(db_name, {}):
                    continue

                source_page_id = self.id_cache[db_name][source_title]
                properties_to_update = {}

                for json_field, notion_field in json_to_notion_field_map.items():
                    if json_field in item and notion_field in RELATION_FIELD_MAP.get(db_name, {}):
                        target_db_name = RELATION_FIELD_MAP[db_name][notion_field]
                        target_titles = item[json_field]

                        if not isinstance(target_titles, list):
                            target_titles = [target_titles]  # Handle single and multi-relations

                        relation_ids = []
                        for target_title in target_titles:
                            if target_title in self.id_cache.get(target_db_name, {}):
                                relation_ids.append(
                                    {"id": self.id_cache[target_db_name][target_title]}
                                )
                            else:
                                print(
                                    f"  [WARN] Could not find target '{target_title}' in '{target_db_name}' to link from '{source_title}'."
                                )

                        if relation_ids:
                            # The property type for linking is "relation" for Relation fields
                            # and "people" for Person fields.
                            prop_type = "people" if notion_field == "Owner" else "relation"
                            properties_to_update[notion_field] = {prop_type: relation_ids}

                if properties_to_update:
                    print(f"  [LINK] Updating relations for '{source_title}' in '{db_name}'.")
                    if self.dry_run:
                        print(f"    DRY RUN: Skipping update for page {source_page_id}.")
                        continue

                    self.client.client.pages.update(
                        page_id=source_page_id, properties=properties_to_update
                    )
                    time.sleep(0.5)


def main():
    """Main function to run the ingestion."""
    load_dotenv()

    package_file = Path("intelligence_package_20250618.json")
    if not package_file.exists():
        print(f"Error: Intelligence package file not found at '{package_file}'")
        return 1

    try:
        print("Verifying database structure first...")
        client = NotionClient()
        # This step is crucial as it populates the client's internal DB ID cache
        creator = DatabaseCreator(client, os.getenv("NOTION_PARENT_PAGE_ID"))
        creator.create_all_databases(check_existing=True)

        ingestor = IntelligenceIngestor(
            client, dry_run=False
        )  # Set to True to test without writing
        ingestor.ingest_package(package_file)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        # Re-raise to see the full traceback for easier debugging
        raise e

    return 0


if __name__ == "__main__":
    sys.exit(main())
