"""Page repository for Notion page operations."""

from typing import Dict, Any, List, Optional
from .base import BaseRepository, RepositoryError


class PageRepository(BaseRepository):
    """Repository for Notion page operations."""

    def get_by_id(self, page_id: str) -> Dict[str, Any]:
        """Get page by ID.

        Args:
            page_id: Notion page ID

        Returns:
            Page data

        Raises:
            RepositoryError: If page not found or error occurs
        """
        try:
            return self._make_api_call("pages.retrieve", page_id=page_id)
        except Exception as e:
            raise RepositoryError(f"Failed to get page {page_id}: {e}")

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new page.

        Args:
            data: Page data with parent and properties

        Returns:
            Created page

        Raises:
            RepositoryError: If creation fails
        """
        try:
            return self._make_api_call("pages.create", **data)
        except Exception as e:
            raise RepositoryError(f"Failed to create page: {e}")

    def update(self, page_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing page.

        Args:
            page_id: Page ID
            data: Update data (properties)

        Returns:
            Updated page

        Raises:
            RepositoryError: If update fails
        """
        try:
            return self._make_api_call("pages.update", page_id=page_id, **data)
        except Exception as e:
            raise RepositoryError(f"Failed to update page {page_id}: {e}")

    def archive(self, page_id: str) -> Dict[str, Any]:
        """Archive a page.

        Args:
            page_id: Page ID

        Returns:
            Archived page

        Raises:
            RepositoryError: If archiving fails
        """
        try:
            return self._make_api_call("pages.update", page_id=page_id, archived=True)
        except Exception as e:
            raise RepositoryError(f"Failed to archive page {page_id}: {e}")

    def query_database(self, database_id: str, filter: Optional[Dict] = None, 
                      sorts: Optional[List[Dict]] = None, start_cursor: Optional[str] = None,
                      page_size: int = 100) -> List[Dict[str, Any]]:
        """Query pages in a database.

        Args:
            database_id: Database ID
            filter: Optional filter
            sorts: Optional sorts
            start_cursor: Optional pagination cursor
            page_size: Page size (max 100)

        Returns:
            List of pages
        """
        query_params = {
            "database_id": database_id,
            "page_size": min(page_size, 100)
        }
        
        if filter:
            query_params["filter"] = filter
        if sorts:
            query_params["sorts"] = sorts

        return self._paginate_results("databases.query", **query_params)

    def find_by_property(self, database_id: str, property_name: str, 
                        value: Any, property_type: str = "title") -> Optional[Dict[str, Any]]:
        """Find a page by property value.

        Args:
            database_id: Database ID
            property_name: Property name
            value: Property value to search for
            property_type: Property type (title, rich_text, select, etc.)

        Returns:
            First matching page or None
        """
        # Build filter based on property type
        if property_type == "title":
            filter_obj = {
                "property": property_name,
                "title": {"equals": value}
            }
        elif property_type == "rich_text":
            filter_obj = {
                "property": property_name,
                "rich_text": {"equals": value}
            }
        elif property_type == "select":
            filter_obj = {
                "property": property_name,
                "select": {"equals": value}
            }
        else:
            # Generic equals filter
            filter_obj = {
                "property": property_name,
                property_type: {"equals": value}
            }

        results = self.query_database(database_id, filter=filter_obj, page_size=1)
        return results[0] if results else None

    def get_property_value(self, page_id: str, property_id: str) -> Any:
        """Get a specific property value from a page.

        Args:
            page_id: Page ID
            property_id: Property ID

        Returns:
            Property value

        Raises:
            RepositoryError: If retrieval fails
        """
        try:
            return self._make_api_call(
                "pages.properties.retrieve",
                page_id=page_id,
                property_id=property_id
            )
        except Exception as e:
            raise RepositoryError(f"Failed to get property {property_id} from page {page_id}: {e}")