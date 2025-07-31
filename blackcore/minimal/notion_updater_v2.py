"""Refactored Notion updater using repository pattern."""

from typing import Optional
import logging

from .repositories import PageRepository, DatabaseRepository
from .services import TranscriptService
from .notion_updater import RateLimiter


class NotionUpdaterV2:
    """Refactored Notion client using repository pattern."""

    def __init__(self, api_key: str, rate_limit: float = 3.0, retry_attempts: int = 3):
        """Initialize Notion updater with repositories.

        Args:
            api_key: Notion API key
            rate_limit: Requests per second limit
            retry_attempts: Number of retry attempts for failed requests
        """
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit)
        self.logger = logging.getLogger(__name__)

        # Initialize client
        try:
            from notion_client import Client
            self.client = Client(auth=api_key)
        except ImportError:
            raise ImportError(
                "notion-client is required. Install with: pip install notion-client"
            )

        # Initialize repositories
        self.page_repo = PageRepository(self.client, self.rate_limiter)
        self.db_repo = DatabaseRepository(self.client, self.rate_limiter)
        
        # Set retry attempts on repositories
        self.page_repo.retry_attempts = retry_attempts
        self.db_repo.retry_attempts = retry_attempts

        # Initialize service
        self.transcript_service = TranscriptService(self.page_repo, self.db_repo)

    def get_database_schema(self, database_id: str) -> dict:
        """Get database schema.

        Args:
            database_id: Database ID

        Returns:
            Database properties schema
        """
        return self.db_repo.get_schema(database_id)

    def create_page(self, database_id: str, properties: dict) -> dict:
        """Create a new page in a database.

        Args:
            database_id: Database ID
            properties: Page properties

        Returns:
            Created page data
        """
        page_data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        return self.page_repo.create(page_data)

    def update_page(self, page_id: str, properties: dict) -> dict:
        """Update an existing page.

        Args:
            page_id: Page ID
            properties: Properties to update

        Returns:
            Updated page data
        """
        return self.page_repo.update(page_id, {"properties": properties})

    def find_page_by_title(self, database_id: str, title: str, 
                          title_property: str = "Name") -> Optional[dict]:
        """Find a page by title.

        Args:
            database_id: Database ID
            title: Title to search for
            title_property: Name of title property

        Returns:
            Page data or None
        """
        return self.page_repo.find_by_property(
            database_id, title_property, title, "title"
        )

    def query_database(self, database_id: str, filter: Optional[dict] = None,
                      sorts: Optional[list] = None) -> list:
        """Query a database.

        Args:
            database_id: Database ID
            filter: Optional filter
            sorts: Optional sorts

        Returns:
            List of pages
        """
        return self.page_repo.query_database(database_id, filter, sorts)

    def process_entities(self, entities, database_mapping):
        """Process extracted entities using the service layer.

        Args:
            entities: Extracted entities
            database_mapping: Mapping of entity types to database IDs

        Returns:
            Processing result
        """
        return self.transcript_service.process_extracted_entities(
            entities, database_mapping
        )

    # Backward compatibility methods
    def create_or_update_page(self, database_id: str, properties: dict,
                             title_property: str = "Name") -> tuple:
        """Create or update a page (backward compatible).

        Args:
            database_id: Database ID
            properties: Page properties
            title_property: Name of title property

        Returns:
            Tuple of (page_dict, was_created)
        """
        # Extract title
        title_value = None
        if title_property in properties:
            title_prop = properties[title_property]
            if isinstance(title_prop, dict) and "title" in title_prop:
                title_items = title_prop["title"]
                if title_items and isinstance(title_items, list):
                    title_value = title_items[0].get("text", {}).get("content", "")

        # Try to find existing page
        if title_value:
            existing = self.find_page_by_title(database_id, title_value, title_property)
            if existing:
                # Update existing
                updated = self.update_page(existing["id"], properties)
                return updated, False

        # Create new page
        created = self.create_page(database_id, properties)
        return created, True