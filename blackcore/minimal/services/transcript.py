"""Service layer for transcript processing business logic."""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from ..models import NotionPage, ProcessingResult, ExtractedEntities
from ..repositories import PageRepository, DatabaseRepository
from ..property_handlers import PropertyHandlerFactory


class TranscriptService:
    """Service for transcript processing business logic."""

    def __init__(self, page_repo: PageRepository, db_repo: DatabaseRepository):
        """Initialize transcript service.

        Args:
            page_repo: Page repository instance
            db_repo: Database repository instance
        """
        self.page_repo = page_repo
        self.db_repo = db_repo
        self.property_factory = PropertyHandlerFactory()
        self.logger = logging.getLogger(__name__)

    def process_extracted_entities(
        self, entities: ExtractedEntities, database_mapping: Dict[str, str]
    ) -> ProcessingResult:
        """Process extracted entities and create/update Notion pages.

        Args:
            entities: Extracted entities from AI
            database_mapping: Mapping of entity types to database IDs

        Returns:
            Processing result with created/updated pages
        """
        result = ProcessingResult(
            transcript_id="",  # Will be set by caller
            created_pages=[],
            updated_pages=[],
            errors=[]
        )

        # Process each entity type
        for entity_type, entity_list in entities.get_entities_by_type().items():
            database_id = database_mapping.get(entity_type)
            if not database_id:
                self.logger.warning(f"No database mapping for entity type: {entity_type}")
                continue

            # Get database schema
            try:
                schema = self.db_repo.get_schema(database_id)
            except Exception as e:
                result.errors.append(f"Failed to get schema for {entity_type}: {e}")
                continue

            # Process each entity
            for entity in entity_list:
                try:
                    page = self._process_entity(entity, database_id, schema)
                    if page:
                        if hasattr(page, 'is_new') and page.is_new:
                            result.created_pages.append(page)
                        else:
                            result.updated_pages.append(page)
                except Exception as e:
                    result.errors.append(f"Failed to process {entity.name}: {e}")

        return result

    def _process_entity(
        self, entity: Any, database_id: str, schema: Dict[str, Any]
    ) -> Optional[NotionPage]:
        """Process a single entity.

        Args:
            entity: Entity to process
            database_id: Target database ID
            schema: Database schema

        Returns:
            Created or updated page, or None
        """
        # Find title property
        title_property = self._find_title_property(schema)
        if not title_property:
            raise ValueError("No title property found in database schema")

        # Check if entity already exists
        existing_page = self.page_repo.find_by_property(
            database_id, title_property, entity.name, "title"
        )

        if existing_page:
            # Update existing page
            return self._update_entity_page(existing_page, entity, schema)
        else:
            # Create new page
            return self._create_entity_page(entity, database_id, schema, title_property)

    def _create_entity_page(
        self, entity: Any, database_id: str, schema: Dict[str, Any], title_property: str
    ) -> NotionPage:
        """Create a new page for an entity.

        Args:
            entity: Entity data
            database_id: Target database ID
            schema: Database schema
            title_property: Name of title property

        Returns:
            Created page
        """
        # Build properties
        properties = self._build_entity_properties(entity, schema, title_property)

        # Create page data
        page_data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }

        # Create the page
        created_page = self.page_repo.create(page_data)

        # Convert to NotionPage model
        notion_page = NotionPage(
            id=created_page["id"],
            properties=created_page.get("properties", {}),
            parent=created_page.get("parent", {}),
            url=created_page.get("url", "")
        )
        notion_page.is_new = True  # Mark as new for tracking

        return notion_page

    def _update_entity_page(
        self, existing_page: Dict[str, Any], entity: Any, schema: Dict[str, Any]
    ) -> NotionPage:
        """Update an existing page with entity data.

        Args:
            existing_page: Existing Notion page
            entity: Entity data
            schema: Database schema

        Returns:
            Updated page
        """
        # Build update properties (excluding title to avoid overwriting)
        properties = {}
        
        # Add entity properties
        for key, value in entity.properties.items():
            if key in schema and value:
                prop_type = schema[key].get("type")
                handler = self.property_factory.get_handler(prop_type)
                if handler:
                    properties[key] = handler.to_notion(value)

        # Update the page
        if properties:
            updated_page = self.page_repo.update(existing_page["id"], {"properties": properties})
        else:
            updated_page = existing_page

        # Convert to NotionPage model
        return NotionPage(
            id=updated_page["id"],
            properties=updated_page.get("properties", {}),
            parent=updated_page.get("parent", {}),
            url=updated_page.get("url", "")
        )

    def _build_entity_properties(
        self, entity: Any, schema: Dict[str, Any], title_property: str
    ) -> Dict[str, Any]:
        """Build Notion properties from entity data.

        Args:
            entity: Entity data
            schema: Database schema
            title_property: Name of title property

        Returns:
            Properties dict for Notion API
        """
        properties = {}

        # Set title
        properties[title_property] = {
            "title": [{"text": {"content": entity.name}}]
        }

        # Add other properties
        for key, value in entity.properties.items():
            if key in schema and value:
                prop_type = schema[key].get("type")
                handler = self.property_factory.get_handler(prop_type)
                if handler:
                    properties[key] = handler.to_notion(value)

        # Add metadata
        if "Created" in schema:
            properties["Created"] = {
                "date": {"start": datetime.now().isoformat()}
            }

        return properties

    def _find_title_property(self, schema: Dict[str, Any]) -> Optional[str]:
        """Find the title property in a database schema.

        Args:
            schema: Database schema

        Returns:
            Name of title property or None
        """
        for prop_name, prop_def in schema.items():
            if prop_def.get("type") == "title":
                return prop_name
        return None

    def link_entities(self, result: ProcessingResult) -> None:
        """Create relationships between entities.

        Analyzes the relationships in ExtractedEntities and creates
        relation properties between pages in Notion databases.
        
        Args:
            result: Processing result with created/updated pages
        """
        if not hasattr(result, 'extracted_entities') or not result.extracted_entities:
            self.logger.info("No extracted entities available for relationship linking")
            return

        relationships_created = 0
        
        # Create a mapping of entity names to page IDs
        entity_name_to_id = {}
        for page in result.created_pages + result.updated_pages:
            # Extract entity name from page properties
            for prop_name, prop_value in page.properties.items():
                if prop_name in ["Full Name", "Organization Name", "Task Name", "Name", "Title"]:
                    if isinstance(prop_value, str):
                        entity_name_to_id[prop_value] = page.id
                        break

        # Process relationships from extracted entities
        for relationship in result.extracted_entities.relationships:
            source_id = entity_name_to_id.get(relationship.source_entity)
            target_id = entity_name_to_id.get(relationship.target_entity)
            
            if not source_id or not target_id:
                self.logger.warning(
                    f"Cannot link relationship: missing entity IDs for "
                    f"{relationship.source_entity} -> {relationship.target_entity}"
                )
                continue

            try:
                # Determine relation property based on relationship type
                relation_property = self._get_relation_property(relationship.relationship_type)
                
                if relation_property:
                    # Add the relationship
                    self.page_repo.add_relation(source_id, relation_property, [target_id])
                    relationships_created += 1
                    
                    self.logger.info(
                        f"Created relationship: {relationship.source_entity} -> "
                        f"{relationship.target_entity} ({relationship.relationship_type})"
                    )
                else:
                    self.logger.warning(
                        f"No relation property mapping for relationship type: "
                        f"{relationship.relationship_type}"
                    )
                    
            except Exception as e:
                self.logger.error(
                    f"Failed to create relationship {relationship.source_entity} -> "
                    f"{relationship.target_entity}: {e}"
                )

        self.logger.info(f"Created {relationships_created} entity relationships")

    def _get_relation_property(self, relationship_type: str) -> Optional[str]:
        """Get the relation property name for a relationship type.
        
        Args:
            relationship_type: Type of relationship (e.g., "works_for", "assigned_to")
            
        Returns:
            Notion property name for the relationship, or None if not supported
        """
        # Mapping of relationship types to Notion property names
        # This should be configurable in the future
        relation_mappings = {
            "works_for": "Organization",
            "member_of": "Organization", 
            "employed_by": "Organization",
            "assigned_to": "Assignee",
            "responsible_for": "Responsible Person",
            "reports_to": "Manager",
            "manages": "Direct Reports",
            "collaborates_with": "Collaborators",
            "mentions": "Related People",
            "involves": "Involved Parties"
        }
        
        return relation_mappings.get(relationship_type.lower())