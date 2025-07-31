"""Database repository for Notion database operations."""

from typing import Dict, Any, List, Optional
from .base import BaseRepository, RepositoryError


class DatabaseRepository(BaseRepository):
    """Repository for Notion database operations."""

    def get_by_id(self, database_id: str) -> Dict[str, Any]:
        """Get database by ID.

        Args:
            database_id: Notion database ID

        Returns:
            Database data including schema

        Raises:
            RepositoryError: If database not found or error occurs
        """
        try:
            return self._make_api_call("databases.retrieve", database_id=database_id)
        except Exception as e:
            raise RepositoryError(f"Failed to get database {database_id}: {e}")

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new database.

        Args:
            data: Database data with parent, title, and properties

        Returns:
            Created database

        Raises:
            RepositoryError: If creation fails
        """
        try:
            return self._make_api_call("databases.create", **data)
        except Exception as e:
            raise RepositoryError(f"Failed to create database: {e}")

    def update(self, database_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing database.

        Args:
            database_id: Database ID
            data: Update data (title, description, properties)

        Returns:
            Updated database

        Raises:
            RepositoryError: If update fails
        """
        try:
            return self._make_api_call("databases.update", database_id=database_id, **data)
        except Exception as e:
            raise RepositoryError(f"Failed to update database {database_id}: {e}")

    def get_schema(self, database_id: str) -> Dict[str, Any]:
        """Get database schema (properties).

        Args:
            database_id: Database ID

        Returns:
            Dictionary of property definitions

        Raises:
            RepositoryError: If retrieval fails
        """
        try:
            database = self.get_by_id(database_id)
            return database.get("properties", {})
        except Exception as e:
            raise RepositoryError(f"Failed to get schema for database {database_id}: {e}")

    def list_databases(self, start_cursor: Optional[str] = None, 
                      page_size: int = 100) -> List[Dict[str, Any]]:
        """List all databases the integration has access to.

        Args:
            start_cursor: Optional pagination cursor
            page_size: Page size (max 100)

        Returns:
            List of databases
        """
        # Note: Notion API doesn't have a direct list databases endpoint
        # You need to use search with filter
        query_params = {
            "filter": {"value": "database", "property": "object"},
            "page_size": min(page_size, 100)
        }
        
        return self._paginate_results("search", **query_params)

    def find_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Find a database by title.

        Args:
            title: Database title to search for

        Returns:
            First matching database or None
        """
        try:
            results = self._make_api_call(
                "search",
                query=title,
                filter={"value": "database", "property": "object"},
                page_size=10
            )
            
            # Filter results to exact title match
            for db in results.get("results", []):
                db_title = self._extract_title(db)
                if db_title and db_title.lower() == title.lower():
                    return db
                    
            return None
        except Exception as e:
            self.logger.warning(f"Failed to find database by title '{title}': {e}")
            return None

    def _extract_title(self, database: Dict[str, Any]) -> Optional[str]:
        """Extract title from database object.

        Args:
            database: Database object

        Returns:
            Title text or None
        """
        title_prop = database.get("title", [])
        if title_prop and isinstance(title_prop, list):
            for text_obj in title_prop:
                if text_obj.get("type") == "text":
                    return text_obj.get("text", {}).get("content", "")
        return None

    def get_property_info(self, database_id: str, property_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific property.

        Args:
            database_id: Database ID
            property_name: Property name

        Returns:
            Property definition or None if not found
        """
        schema = self.get_schema(database_id)
        return schema.get(property_name)