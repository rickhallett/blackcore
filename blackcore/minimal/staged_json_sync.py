"""
Staged JSON Sync - Enhanced sync processor with data transformation and staged synchronization.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .json_sync import JSONSyncProcessor, SyncResult
from .data_transformer import (
    DataTransformer,
    load_property_mappings,
    load_notion_schemas,
)
from .notion_schema_inspector import NotionSchemaInspector
from .models import NotionPage

logger = logging.getLogger(__name__)


@dataclass
class StagedSyncResult(SyncResult):
    """Extended sync result with stage information."""

    stage: int = 1
    stage_results: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    transformed_records: int = 0
    page_id_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)


class StagedJSONSyncProcessor(JSONSyncProcessor):
    """Enhanced sync processor with staged synchronization and data transformation."""

    # Define sync stages
    STAGE_1_DATABASES = [
        "People & Contacts",
        "Organizations & Bodies",
        "Agendas & Epics",
    ]

    STAGE_2_DATABASES = [
        "Documents & Evidence",
        "Intelligence & Transcripts",
        "Identified Transgressions",
        "Actionable Tasks",
        "Key Places & Events",
    ]

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the staged sync processor."""
        super().__init__(config_path)

        # Load transformation configurations
        self.property_mappings = load_property_mappings()
        self.notion_schemas = load_notion_schemas()

        # Initialize transformer
        self.transformer = DataTransformer(self.property_mappings, self.notion_schemas)

        # Initialize schema inspector
        self.schema_inspector = NotionSchemaInspector(self.notion_updater.client)

        # Track sync progress
        self.sync_stage = 1
        self.created_pages = {}  # database_name -> {title -> page_id}

    def sync_all_staged(self) -> StagedSyncResult:
        """Perform staged synchronization of all databases."""
        combined_result = StagedSyncResult()

        logger.info("=" * 60)
        logger.info("STARTING STAGED SYNCHRONIZATION")
        logger.info("=" * 60)

        # Stage 1: Create entities without relations
        logger.info("\n📌 STAGE 1: Creating base entities (no relations)")
        stage1_result = self._sync_stage(1, self.STAGE_1_DATABASES)
        combined_result = self._merge_results(combined_result, stage1_result, 1)

        # Stage 2: Create dependent entities without relations
        logger.info("\n📌 STAGE 2: Creating dependent entities (no relations)")
        stage2_result = self._sync_stage(2, self.STAGE_2_DATABASES)
        combined_result = self._merge_results(combined_result, stage2_result, 2)

        # Stage 3: Update all entities with relations
        logger.info("\n📌 STAGE 3: Updating all entities with relations")
        stage3_result = self._sync_relations()
        combined_result = self._merge_results(combined_result, stage3_result, 3)

        logger.info("\n" + "=" * 60)
        logger.info("STAGED SYNCHRONIZATION COMPLETE")
        logger.info("=" * 60)

        return combined_result

    def _sync_stage(self, stage: int, database_names: List[str]) -> StagedSyncResult:
        """Sync a specific stage of databases."""
        stage_result = StagedSyncResult(stage=stage)
        self.sync_stage = stage

        for db_name in database_names:
            if self.verbose:
                logger.info(f"\n→ Processing {db_name}...")

            # Check if database exists in our config
            if db_name not in self.notion_config:
                logger.warning(f"  ⚠️  {db_name} not in notion_config.json, skipping")
                stage_result.skipped_count += 1
                continue

            # Sync the database
            db_result = self.sync_database_transformed(db_name, stage)

            # Merge results
            stage_result.created_count += db_result.created_count
            stage_result.updated_count += db_result.updated_count
            stage_result.skipped_count += db_result.skipped_count
            stage_result.errors.extend(db_result.errors)
            stage_result.created_pages.extend(db_result.created_pages)
            stage_result.updated_pages.extend(db_result.updated_pages)

            if not db_result.success:
                stage_result.success = False

        return stage_result

    def sync_database_transformed(
        self, database_name: str, stage: int = 1
    ) -> SyncResult:
        """Sync a single database with data transformation."""
        result = SyncResult()

        try:
            # Get database configuration
            db_config = self.notion_config.get(database_name)
            if not db_config:
                result.success = False
                result.errors.append(
                    f"Database '{database_name}' not found in configuration"
                )
                return result

            database_id = db_config["id"]
            json_path = db_config["local_json_path"]
            json_data_key = db_config.get("json_data_key", database_name)
            title_property = db_config.get("title_property", "Name")

            if self.verbose:
                print(f"\n📂 Syncing database: {database_name}")
                print(f"   JSON path: {json_path}")
                print(f"   Database ID: {database_id}")
                print(f"   Stage: {stage}")

            # Load JSON data
            records = self._load_json_data(json_path)

            # Apply transformations
            if database_name in self.property_mappings:
                original_count = len(records)
                records = self.transformer.transform_database_records(
                    database_name, records, stage
                )
                if self.verbose:
                    print(f"   Transformed {len(records)}/{original_count} records")

            if self.verbose:
                print(f"   Found {len(records)} records to process")

            # Process each record
            for record in records:
                title_value = self._get_title_value(record, database_name)
                if not title_value:
                    result.skipped_count += 1
                    continue

                if self.verbose:
                    print(f"\n   Processing: {title_value}")

                # In stage 1 & 2, create/update without relations
                # In stage 3, only update relations
                if stage < 3:
                    # Prepare properties for Notion API
                    formatted_properties = self._prepare_properties(record, db_config)

                    # Check if page exists
                    existing_page = self._find_existing_page(
                        database_id, title_property, str(title_value)
                    )

                    if existing_page:
                        # Update existing page
                        if self._update_page(
                            existing_page["id"],
                            formatted_properties,
                            result,
                            title_value,
                        ):
                            # Store page ID for relations
                            self.transformer.set_page_id(
                                database_name, title_value, existing_page["id"]
                            )
                    else:
                        # Create new page
                        created_page_id = self._create_page(
                            database_id, formatted_properties, result, title_value
                        )
                        if created_page_id:
                            # Store page ID for relations
                            self.transformer.set_page_id(
                                database_name, title_value, created_page_id
                            )

        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to sync database '{database_name}': {str(e)}")
            logger.error(f"Error syncing {database_name}: {e}", exc_info=True)

        return result

    def _sync_relations(self) -> StagedSyncResult:
        """Stage 3: Update all pages with relations."""
        result = StagedSyncResult(stage=3)

        # Get all databases
        all_databases = list(set(self.STAGE_1_DATABASES + self.STAGE_2_DATABASES))

        for db_name in all_databases:
            if db_name not in self.notion_config:
                continue

            db_config = self.notion_config[db_name]
            database_id = db_config["id"]
            json_path = db_config["local_json_path"]
            title_property = db_config.get("title_property", "Name")

            # Check if we have mappings for this database
            if db_name not in self.property_mappings:
                continue

            mapping_config = self.property_mappings[db_name]

            # Check if this database has any relation fields
            has_relations = any(
                t.get("type") == "relation"
                for t in mapping_config.get("transformations", {}).values()
            )

            if not has_relations:
                continue

            if self.verbose:
                print(f"\n→ Updating relations for {db_name}...")

            # Load original records
            records = self._load_json_data(json_path)

            # Process each record
            updated_count = 0
            for record in records:
                title_value = self._get_title_value(record, db_name)
                if not title_value:
                    continue

                # Get the page ID
                page_id = self.transformer.get_page_id(db_name, title_value)
                if not page_id:
                    # Try to find it in Notion
                    existing_page = self._find_existing_page(
                        database_id, title_property, str(title_value)
                    )
                    if existing_page:
                        page_id = existing_page["id"]
                        self.transformer.set_page_id(db_name, title_value, page_id)
                    else:
                        logger.warning(
                            f"No page found for '{title_value}' in {db_name}"
                        )
                        continue

                # Get relation updates
                relation_updates = self.transformer.update_relations(
                    record, mapping_config, db_name
                )

                if relation_updates:
                    # Update the page with relations
                    if not self.dry_run:
                        try:
                            self.notion_updater.client.pages.update(
                                page_id=page_id, properties=relation_updates
                            )
                            updated_count += 1
                            if self.verbose:
                                print(f"   ✅ Updated relations for: {title_value}")
                        except Exception as e:
                            result.errors.append(
                                f"Failed to update relations for '{title_value}': {str(e)}"
                            )
                            logger.error(f"Error updating relations: {e}")
                    else:
                        updated_count += 1
                        if self.verbose:
                            print(f"   → Would update relations for: {title_value}")

            result.updated_count += updated_count
            if self.verbose:
                print(f"   Updated {updated_count} pages with relations")

        return result

    def _get_title_value(
        self, record: Dict[str, Any], database_name: str
    ) -> Optional[str]:
        """Get the title value from a record."""
        if database_name in self.property_mappings:
            title_property = self.property_mappings[database_name].get("title_property")
            if title_property and title_property in record:
                return record[title_property]

        # Fallback to first string value
        for value in record.values():
            if isinstance(value, str) and value:
                return value
        return None

    def _create_page(
        self,
        database_id: str,
        properties: Dict[str, Any],
        result: SyncResult,
        title: str,
    ) -> Optional[str]:
        """Create a new page and return its ID."""
        if self.verbose:
            print("   → Creating new page...")

        if not self.dry_run:
            try:
                created_page = self.notion_updater.client.pages.create(
                    parent={"database_id": database_id}, properties=properties
                )
                page_id = created_page["id"]
                result.created_pages.append(
                    NotionPage(
                        id=page_id,
                        database_id=database_id,
                        properties=properties,
                        created_time=created_page["created_time"],
                        last_edited_time=created_page["last_edited_time"],
                        url=created_page.get("url"),
                    )
                )
                result.created_count += 1
                if self.verbose:
                    print(f"   ✅ Created page: {page_id}")
                return page_id
            except Exception as e:
                result.errors.append(f"Failed to create '{title}': {str(e)}")
                if self.verbose:
                    print(f"   ❌ Error: {e}")
                return None
        else:
            result.created_count += 1
            if self.verbose:
                print("   → Would create new page")
            return None

    def _update_page(
        self, page_id: str, properties: Dict[str, Any], result: SyncResult, title: str
    ) -> bool:
        """Update an existing page."""
        if self.verbose:
            print("   → Found existing page, updating...")

        if not self.dry_run:
            try:
                self.notion_updater.client.pages.update(
                    page_id=page_id, properties=properties
                )
                result.updated_count += 1
                if self.verbose:
                    print(f"   ✅ Updated page: {page_id}")
                return True
            except Exception as e:
                result.errors.append(f"Failed to update '{title}': {str(e)}")
                if self.verbose:
                    print(f"   ❌ Error: {e}")
                return False
        else:
            result.updated_count += 1
            if self.verbose:
                print("   → Would update existing page")
            return True

    def _prepare_properties(
        self, record: Dict[str, Any], db_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare properties for Notion API using schema information."""
        properties = {}
        database_name = db_config.get("json_data_key", "")

        # Get the database schema
        schema = None
        for db_id, db_schema in self.notion_schemas.items():
            if db_schema.get("title") == database_name:
                schema = db_schema
                break

        if not schema:
            # Fallback to parent implementation
            return super()._prepare_properties(record, db_config)

        # Get property schemas
        property_schemas = schema.get("properties", {})

        # Process each field in the record
        for key, value in record.items():
            # Skip None values
            if value is None or value == "":
                continue

            # Get the property schema
            prop_schema = property_schemas.get(key, {})
            prop_type = prop_schema.get("type")

            # Format based on property type
            if prop_type == "title":
                properties[key] = {"title": [{"text": {"content": str(value)}}]}
            elif prop_type == "rich_text":
                properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}
            elif prop_type == "select":
                if value:  # Only set if we have a value
                    properties[key] = {"select": {"name": str(value)}}
            elif prop_type == "multi_select":
                if isinstance(value, list):
                    properties[key] = {
                        "multi_select": [{"name": str(item)} for item in value if item]
                    }
                else:
                    properties[key] = {"multi_select": [{"name": str(value)}]}
            elif prop_type == "status":
                if value:  # Only set if we have a value
                    properties[key] = {"status": {"name": str(value)}}
            elif prop_type == "date":
                if value:
                    properties[key] = {"date": {"start": str(value)}}
            elif prop_type == "checkbox":
                properties[key] = {"checkbox": bool(value)}
            elif prop_type == "number":
                properties[key] = {"number": float(value) if value else None}
            elif prop_type == "url":
                if value:
                    properties[key] = {"url": str(value)}
            elif prop_type == "email":
                if value:
                    properties[key] = {"email": str(value)}
            elif prop_type == "phone_number":
                if value:
                    properties[key] = {"phone_number": str(value)}
            elif prop_type == "relation":
                # Relations should be handled in stage 3
                if isinstance(value, list) and all(
                    isinstance(item, str) and "-" in item for item in value
                ):
                    # These look like page IDs
                    properties[key] = {
                        "relation": [{"id": page_id} for page_id in value]
                    }
                # Otherwise skip for now
            elif prop_type == "people":
                # People properties cannot be set via API unless using user IDs
                continue
            elif prop_type == "files":
                # Files need to be URLs
                continue
            else:
                # Default to rich text for unknown types
                properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}

        return properties

    def _merge_results(
        self, combined: StagedSyncResult, stage_result: StagedSyncResult, stage: int
    ) -> StagedSyncResult:
        """Merge stage results into combined result."""
        combined.created_count += stage_result.created_count
        combined.updated_count += stage_result.updated_count
        combined.skipped_count += stage_result.skipped_count
        combined.errors.extend(stage_result.errors)
        combined.created_pages.extend(stage_result.created_pages)
        combined.updated_pages.extend(stage_result.updated_pages)

        if not stage_result.success:
            combined.success = False

        # Store stage-specific results
        combined.stage_results[stage] = {
            "created": stage_result.created_count,
            "updated": stage_result.updated_count,
            "skipped": stage_result.skipped_count,
            "errors": len(stage_result.errors),
        }

        return combined
