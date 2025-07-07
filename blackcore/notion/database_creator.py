"""Database creation logic for Project Nassau."""

import time
from typing import Dict, List, Optional, Tuple
from blackcore.notion.client import NotionClient
from blackcore.notion.schemas.all_databases import (
    get_all_database_schemas,
    RELATION_MAPPINGS,
)
from blackcore.models.notion_properties import (
    DatabaseSchema,
    RelationProperty,
    RelationConfig,
)


class DatabaseCreator:
    """Handles creation and setup of Notion databases."""

    def __init__(self, notion_client: NotionClient, parent_page_id: str):
        """Initialize database creator.

        Args:
            notion_client: Notion API client
            parent_page_id: ID of the parent page where databases will be created
        """
        self.client = notion_client
        self.parent_page_id = parent_page_id
        self.database_ids: Dict[str, str] = {}
        self.created_databases: List[str] = []

    def create_all_databases(self, check_existing: bool = True) -> Dict[str, str]:
        """Create all Project Nassau databases.

        Args:
            check_existing: Whether to check for existing databases first

        Returns:
            Dictionary mapping database names to their IDs
        """
        print("Starting database creation process...")

        # Check for existing databases if requested
        if check_existing:
            existing = self._check_existing_databases()
            if existing:
                print(f"Found {len(existing)} existing databases:")
                for name in existing:
                    print(f"  - {name}")
                response = input("\nContinue and skip existing databases? (y/n): ")
                if response.lower() != "y":
                    print("Database creation cancelled.")
                    return {}

        # Get all database schemas
        schemas = get_all_database_schemas()

        # Phase 1: Create databases without relations
        print("\nPhase 1: Creating databases without relations...")
        for schema in schemas:
            if check_existing and schema.name in existing:
                print(f"Skipping existing database: {schema.name}")
                # Try to get the ID of existing database
                existing_dbs = self.client.search_databases(schema.name)
                if existing_dbs:
                    self.database_ids[schema.name] = existing_dbs[0]["id"]
                continue

            db_id = self._create_database_without_relations(schema)
            if db_id:
                self.database_ids[schema.name] = db_id
                self.created_databases.append(schema.name)
                print(f"✓ Created: {schema.name}")
                # Small delay to avoid rate limits
                time.sleep(0.5)

        # Phase 2: Update databases with relations
        print("\nPhase 2: Updating databases with relations...")
        self._update_all_relations()

        print(f"\nDatabase creation complete! Created {len(self.created_databases)} databases.")
        return self.database_ids

    def _check_existing_databases(self) -> List[str]:
        """Check for existing databases with matching names.

        Returns:
            List of existing database names
        """
        existing_names = []
        schemas = get_all_database_schemas()

        for schema in schemas:
            results = self.client.search_databases(schema.name)
            if results:
                existing_names.append(schema.name)

        return existing_names

    def _create_database_without_relations(self, schema: DatabaseSchema) -> Optional[str]:
        """Create a database without relation properties.

        Args:
            schema: Database schema

        Returns:
            Created database ID or None if failed
        """
        # Create a copy of properties without relations
        properties_without_relations = {}

        for prop in schema.properties:
            if not isinstance(prop, RelationProperty):
                properties_without_relations[prop.name] = prop.to_notion()

        try:
            response = self.client.create_database(
                parent_page_id=self.parent_page_id,
                title=schema.name,
                properties=properties_without_relations,
                icon=schema.icon,
                cover=schema.cover,
            )
            return response["id"]
        except Exception as e:
            print(f"Error creating database '{schema.name}': {e}")
            return None

    def _update_all_relations(self):
        """Update all databases with their relation properties."""
        for db_name, relations in RELATION_MAPPINGS.items():
            if db_name not in self.database_ids:
                print(f"Skipping relations for missing database: {db_name}")
                continue

            db_id = self.database_ids[db_name]
            relation_properties = {}

            for relation_name, target_db_name in relations.items():
                if target_db_name is None:
                    # Special case for multi-relations (Tagged Entities, Evidence)
                    # For now, we'll link to Intelligence & Transcripts as default
                    if relation_name == "Tagged Entities":
                        target_db_name = "People & Contacts"  # Default target
                    elif relation_name == "Evidence":
                        target_db_name = "Documents & Evidence"  # Default target

                if target_db_name in self.database_ids:
                    target_db_id = self.database_ids[target_db_name]

                    # Create proper relation configuration
                    relation_config = RelationConfig(database_id=target_db_id, type="dual_property")

                    # Create relation property with config
                    relation_prop = RelationProperty(name=relation_name, config=relation_config)

                    relation_properties[relation_name] = relation_prop.to_notion()
                else:
                    print(
                        f"Warning: Target database '{target_db_name}' not found for relation '{relation_name}'"
                    )

            if relation_properties:
                try:
                    self.client.update_database(database_id=db_id, properties=relation_properties)
                    print(f"✓ Updated relations for: {db_name}")
                    time.sleep(0.5)  # Rate limit protection
                except Exception as e:
                    print(f"Error updating relations for '{db_name}': {e}")

    def verify_databases(self) -> Tuple[List[str], List[str]]:
        """Verify that all databases were created successfully.

        Returns:
            Tuple of (successful databases, missing databases)
        """
        schemas = get_all_database_schemas()
        successful = []
        missing = []

        for schema in schemas:
            results = self.client.search_databases(schema.name)
            if results:
                successful.append(schema.name)
            else:
                missing.append(schema.name)

        return successful, missing

    def get_database_report(self) -> str:
        """Generate a report of created databases.

        Returns:
            Formatted report string
        """
        report = "=== Project Nassau Database Report ===\n\n"

        if not self.database_ids:
            report += "No databases found.\n"
            return report

        report += f"Total databases: {len(self.database_ids)}\n\n"

        for db_name, db_id in self.database_ids.items():
            report += f"Database: {db_name}\n"
            report += f"  ID: {db_id}\n"
            report += f"  URL: https://www.notion.so/{db_id.replace('-', '')}\n\n"

        return report
