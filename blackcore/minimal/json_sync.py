"""JSON sync functionality for syncing local JSON files to Notion databases."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .notion_updater import NotionUpdater
from .property_handlers import PropertyHandlerFactory
from .models import NotionPage
from .config import ConfigManager


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool = True
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    errors: List[str] = field(default_factory=list)
    created_pages: List[NotionPage] = field(default_factory=list)
    updated_pages: List[NotionPage] = field(default_factory=list)


class JSONSyncProcessor:
    """Processor for syncing local JSON files to Notion databases."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the JSON sync processor.

        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load()
        self.notion_updater = NotionUpdater(self.config.notion.api_key)
        self.property_factory = PropertyHandlerFactory()

        # Load the main notion config
        self.notion_config = self._load_notion_config()

        # Processing options
        self.dry_run = False
        self.verbose = False

    def _load_notion_config(self) -> Dict[str, Any]:
        """Load the notion configuration from the main project."""
        # Try to find notion_config.json
        config_paths = [
            Path("blackcore/config/notion_config.json"),
            Path("../config/notion_config.json"),
            Path("../../blackcore/config/notion_config.json"),
            Path(__file__).parent.parent / "config" / "notion_config.json",
        ]

        for path in config_paths:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

        raise FileNotFoundError(
            "Could not find notion_config.json. Please ensure you're running from the project root."
        )

    def _load_json_data(self, json_path: str) -> List[Dict[str, Any]]:
        """Load data from a JSON file."""
        full_path = Path(json_path)
        if not full_path.exists():
            # Try relative to project root
            full_path = Path("..") / ".." / json_path
            if not full_path.exists():
                raise FileNotFoundError(f"JSON file not found: {json_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # The JSON files have a structure like {"DatabaseName": [...]}
        # We need to extract the list of records
        if isinstance(data, dict):
            # Get the first (and usually only) key's value
            return list(data.values())[0] if data else []
        return data

    def _find_existing_page(
        self, database_id: str, title_property: str, title_value: str
    ) -> Optional[Dict[str, Any]]:
        """Find an existing page in Notion by title."""
        if self.dry_run:
            # In dry run mode, we can't query Notion
            return None

        try:
            # Query the database for pages with matching title
            results = self.notion_updater.client.databases.query(
                database_id=database_id,
                filter={
                    "property": title_property,
                    "title": {"equals": title_value},
                },
            )

            if results["results"]:
                return results["results"][0]
            return None

        except Exception as e:
            if self.verbose:
                print(f"   Error searching for existing page: {e}")
            return None

    def _prepare_properties(
        self, record: Dict[str, Any], db_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare properties for Notion from a JSON record."""
        properties = {}
        title_property = db_config["title_property"]

        # First, ensure we have the title property
        if title_property in record:
            properties[title_property] = {
                "title": [{"text": {"content": str(record[title_property])}}]
            }

        # Process all other properties
        for key, value in record.items():
            if key == title_property:
                continue  # Already handled

            # Skip None values
            if value is None:
                continue

            # Handle different property types based on value
            if isinstance(value, list):
                # Could be multi-select or relation
                if key in db_config.get("relations", {}):
                    # This is a relation - we'll handle it separately
                    continue
                else:
                    # Assume multi-select
                    properties[key] = {
                        "multi_select": [{"name": str(item)} for item in value if item]
                    }
            elif isinstance(value, bool):
                properties[key] = {"checkbox": value}
            elif isinstance(value, (int, float)):
                properties[key] = {"number": value}
            elif isinstance(value, str):
                # Could be select, text, or other string types
                if value in [
                    "Active",
                    "Completed",
                    "Pending",
                    "Planning",
                    "Monitoring",
                ]:
                    # Likely a select property
                    properties[key] = {"select": {"name": value}}
                else:
                    # Default to rich text
                    properties[key] = {"rich_text": [{"text": {"content": value}}]}
            else:
                # Default to string representation
                properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}

        return properties

    def sync_database(self, database_name: str) -> SyncResult:
        """Sync a specific database from JSON to Notion.

        Args:
            database_name: Name of the database to sync

        Returns:
            SyncResult with details of the sync operation
        """
        result = SyncResult()

        if database_name not in self.notion_config:
            result.success = False
            result.errors.append(
                f"Database '{database_name}' not found in configuration"
            )
            return result

        db_config = self.notion_config[database_name]
        database_id = db_config["id"]
        json_path = db_config["local_json_path"]
        title_property = db_config["title_property"]

        if self.verbose:
            print(f"\n📂 Syncing database: {database_name}")
            print(f"   JSON path: {json_path}")
            print(f"   Database ID: {database_id}")

        try:
            # Load JSON data
            records = self._load_json_data(json_path)
            if self.verbose:
                print(f"   Found {len(records)} records in JSON file")

            # Process each record
            for i, record in enumerate(records):
                title_value = record.get(title_property, f"Untitled {i}")
                if self.verbose:
                    print(f"\n   Processing: {title_value}")

                # Check if page already exists
                existing_page = self._find_existing_page(
                    database_id, title_property, str(title_value)
                )

                if existing_page:
                    # Update existing page
                    if self.verbose:
                        print("   → Found existing page, updating...")

                    if not self.dry_run:
                        try:
                            properties = self._prepare_properties(record, db_config)
                            updated_page = self.notion_updater.client.pages.update(
                                page_id=existing_page["id"], properties=properties
                            )
                            result.updated_pages.append(
                                NotionPage(
                                    id=updated_page["id"],
                                    database_id=database_id,
                                    properties=properties,
                                )
                            )
                            result.updated_count += 1
                        except Exception as e:
                            result.errors.append(
                                f"Failed to update '{title_value}': {str(e)}"
                            )
                            if self.verbose:
                                print(f"   ❌ Error: {e}")
                    else:
                        result.updated_count += 1
                        if self.verbose:
                            print("   → Would update existing page")

                else:
                    # Create new page
                    if self.verbose:
                        print("   → Creating new page...")

                    if not self.dry_run:
                        try:
                            properties = self._prepare_properties(record, db_config)
                            created_page = self.notion_updater.client.pages.create(
                                parent={"database_id": database_id},
                                properties=properties,
                            )
                            result.created_pages.append(
                                NotionPage(
                                    id=created_page["id"],
                                    database_id=database_id,
                                    properties=properties,
                                )
                            )
                            result.created_count += 1
                        except Exception as e:
                            result.errors.append(
                                f"Failed to create '{title_value}': {str(e)}"
                            )
                            if self.verbose:
                                print(f"   ❌ Error: {e}")
                    else:
                        result.created_count += 1
                        if self.verbose:
                            print("   → Would create new page")

        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to sync database '{database_name}': {str(e)}")

        return result

    def sync_all(self) -> SyncResult:
        """Sync all databases from JSON to Notion.

        Returns:
            Combined SyncResult for all databases
        """
        combined_result = SyncResult()

        # Get all database names from config
        database_names = list(self.notion_config.keys())
        print(f"Found {len(database_names)} databases to sync")

        for db_name in database_names:
            # Skip certain system databases
            if db_name in ["API Control Panel USER GEN", "Leads"]:
                if self.verbose:
                    print(f"\nSkipping system database: {db_name}")
                continue

            # Check if JSON file exists
            json_path = self.notion_config[db_name]["local_json_path"]
            if (
                not Path(json_path).exists()
                and not (Path("..") / ".." / json_path).exists()
            ):
                if self.verbose:
                    print(f"\nSkipping {db_name} - JSON file not found: {json_path}")
                combined_result.skipped_count += 1
                continue

            # Sync this database
            db_result = self.sync_database(db_name)

            # Combine results
            combined_result.created_count += db_result.created_count
            combined_result.updated_count += db_result.updated_count
            combined_result.skipped_count += db_result.skipped_count
            combined_result.errors.extend(db_result.errors)
            combined_result.created_pages.extend(db_result.created_pages)
            combined_result.updated_pages.extend(db_result.updated_pages)

            if not db_result.success:
                combined_result.success = False

        return combined_result
