"""Notion API client wrapper for Project Nassau."""

import os
from typing import Dict, List, Optional, Any
from notion_client import Client
from notion_client.errors import APIResponseError
from dotenv import load_dotenv


class NotionClient:
    """Wrapper for Notion API client with rate limiting and error handling."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Notion client.

        Args:
            api_key: Notion API key. If not provided, will load from environment.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        if not self.api_key:
            raise ValueError("NOTION_API_KEY not found in environment or provided")

        self.client = Client(auth=self.api_key)
        self._database_cache: Dict[str, str] = {}

    def create_database(
        self,
        parent_page_id: str,
        title: str,
        properties: Dict[str, Any],
        icon: Optional[Dict[str, str]] = None,
        cover: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a new database in Notion.

        Args:
            parent_page_id: ID of the parent page where database will be created
            title: Database title
            properties: Dictionary of property definitions
            icon: Optional icon configuration
            cover: Optional cover configuration

        Returns:
            Created database object
        """
        try:
            database_data = {
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "title": [{"type": "text", "text": {"content": title}}],
                "properties": properties,
            }

            if icon:
                database_data["icon"] = icon
            if cover:
                database_data["cover"] = cover

            response = self.client.databases.create(**database_data)

            # Cache the database ID for later use
            self._database_cache[title] = response["id"]

            return response

        except APIResponseError as e:
            print(f"Error creating database '{title}': {e}")
            raise

    def update_database(
        self,
        database_id: str,
        properties: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing database.

        Args:
            database_id: ID of the database to update
            properties: Updated property definitions
            title: Updated title

        Returns:
            Updated database object
        """
        try:
            update_data = {}

            if properties:
                update_data["properties"] = properties

            if title:
                update_data["title"] = [{"type": "text", "text": {"content": title}}]

            return self.client.databases.update(database_id=database_id, **update_data)

        except APIResponseError as e:
            print(f"Error updating database {database_id}: {e}")
            raise

    def search_databases(self, title: str) -> List[Dict[str, Any]]:
        """Search for databases by title.

        Args:
            title: Database title to search for

        Returns:
            List of matching databases
        """
        try:
            response = self.client.search(filter={"property": "object", "value": "database"})

            # Filter results by title
            databases = []
            for result in response.get("results", []):
                db_title = self._extract_title(result)
                if db_title and title.lower() in db_title.lower():
                    databases.append(result)

            return databases

        except APIResponseError as e:
            print(f"Error searching databases: {e}")
            raise

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get a database by ID.

        Args:
            database_id: ID of the database

        Returns:
            Database object
        """
        try:
            return self.client.databases.retrieve(database_id=database_id)
        except APIResponseError as e:
            print(f"Error retrieving database {database_id}: {e}")
            raise

    def list_all_databases(self) -> List[Dict[str, Any]]:
        """List all accessible databases.

        Returns:
            List of all databases
        """
        try:
            response = self.client.search(filter={"property": "object", "value": "database"})
            return response.get("results", [])
        except APIResponseError as e:
            print(f"Error listing databases: {e}")
            raise

    def get_cached_database_id(self, title: str) -> Optional[str]:
        """Get cached database ID by title.

        Args:
            title: Database title

        Returns:
            Database ID if cached, None otherwise
        """
        return self._database_cache.get(title)

    @staticmethod
    def _extract_title(database: Dict[str, Any]) -> Optional[str]:
        """Extract title from database object.

        Args:
            database: Database object from API

        Returns:
            Title string or None
        """
        title_list = database.get("title", [])
        if title_list and len(title_list) > 0:
            return title_list[0].get("text", {}).get("content", "")
        return None
