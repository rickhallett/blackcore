"""Simplified Notion API client for database updates."""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .models import NotionPage
from .property_handlers import PropertyHandlerFactory


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, requests_per_second: float = 3.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit.
        
        This method is thread-safe and ensures that multiple threads
        respect the rate limit when making concurrent requests.
        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()


class NotionUpdater:
    """Simplified Notion client for creating and updating database entries."""

    def __init__(self, api_key: str, rate_limit: float = 3.0, retry_attempts: int = 3):
        """Initialize Notion updater.

        Args:
            api_key: Notion API key
            rate_limit: Requests per second limit
            retry_attempts: Number of retry attempts for failed requests
        """
        # Validate API key
        from .validators import validate_api_key
        if not validate_api_key(api_key, "notion"):
            raise ValueError("Invalid Notion API key format")
            
        self.api_key = api_key
        self.retry_attempts = retry_attempts
        self.rate_limiter = RateLimiter(rate_limit)

        # Lazy import to avoid dependency if not needed
        try:
            from notion_client import Client

            self.client = Client(auth=api_key)
        except ImportError:
            raise ImportError(
                "notion-client package required. Install with: pip install notion-client"
            )

    def create_page(self, database_id: str, properties: Dict[str, Any]) -> NotionPage:
        """Create a new page in a database.

        Args:
            database_id: The database ID
            properties: Properties for the new page

        Returns:
            Created NotionPage
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Format properties for API
        formatted_properties = self._format_properties(properties)

        # Create page with retries
        response = self._execute_with_retry(
            lambda: self.client.pages.create(
                parent={"database_id": database_id}, properties=formatted_properties
            )
        )

        return self._parse_page_response(response)

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> NotionPage:
        """Update an existing page.

        Args:
            page_id: The page ID to update
            properties: Properties to update

        Returns:
            Updated NotionPage
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Format properties for API
        formatted_properties = self._format_properties(properties)

        # Update page with retries
        response = self._execute_with_retry(
            lambda: self.client.pages.update(
                page_id=page_id, properties=formatted_properties
            )
        )

        return self._parse_page_response(response)

    def find_page(
        self, database_id: str, filter_query: Dict[str, Any]
    ) -> Optional[NotionPage]:
        """Find a page by property values.

        Args:
            database_id: The database ID to search
            filter_query: Query filter (e.g., {"Full Name": "John Doe"})

        Returns:
            Found NotionPage or None
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Build Notion filter
        notion_filter = self._build_filter(filter_query)

        # Query database
        response = self._execute_with_retry(
            lambda: self.client.databases.query(
                database_id=database_id, filter=notion_filter, page_size=1
            )
        )

        results = response.get("results", [])
        if results:
            return self._parse_page_response(results[0])
        return None

    def find_or_create_page(
        self, database_id: str, properties: Dict[str, Any], match_property: str
    ) -> Tuple[NotionPage, bool]:
        """Find an existing page or create a new one.

        Args:
            database_id: The database ID
            properties: Properties for the page
            match_property: Property name to use for matching (e.g., "Full Name")

        Returns:
            Tuple of (NotionPage, created) where created is True if page was created
        """
        # Try to find existing page
        if match_property in properties:
            existing = self.find_page(
                database_id, {match_property: properties[match_property]}
            )
            if existing:
                # Update existing page
                updated = self.update_page(existing.id, properties)
                return updated, False

        # Create new page
        created = self.create_page(database_id, properties)
        return created, True

    def add_relation(
        self, page_id: str, relation_property: str, target_page_ids: List[str]
    ) -> NotionPage:
        """Add relation(s) to a page.

        Args:
            page_id: The page to update
            relation_property: Name of the relation property
            target_page_ids: List of page IDs to relate to

        Returns:
            Updated NotionPage
        """
        # Get current relations
        page = self._get_page(page_id)
        current_relations = self._get_relation_ids(page, relation_property)

        # Merge with new relations
        all_relations = list(set(current_relations + target_page_ids))

        # Update the page
        return self.update_page(page_id, {relation_property: all_relations})

    def search_database(
        self, database_id: str, query: str, limit: int = 10
    ) -> List[NotionPage]:
        """Search for pages in a database.

        Args:
            database_id: The database ID to search
            query: Search query text
            limit: Maximum number of results

        Returns:
            List of NotionPage objects matching the query
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Use database query with title contains filter
        filter_params = {
            "filter": {
                "or": [
                    {"property": "Full Name", "title": {"contains": query}},
                    {"property": "Organization Name", "title": {"contains": query}},
                    {"property": "Task Name", "title": {"contains": query}},
                    {"property": "Name", "title": {"contains": query}},
                    {"property": "Title", "title": {"contains": query}},
                ]
            },
            "page_size": limit,
        }

        try:
            response = self._execute_with_retry(
                lambda: self.client.databases.query(
                    database_id=database_id, **filter_params
                )
            )

            pages = []
            for page_data in response.get("results", []):
                pages.append(self._parse_page_response(page_data))

            return pages
        except Exception:
            # If filter fails, try without filter (some databases may have different schemas)
            try:
                response = self._execute_with_retry(
                    lambda: self.client.databases.query(
                        database_id=database_id, page_size=limit
                    )
                )

                # Filter results manually
                pages = []
                query_lower = query.lower()
                for page_data in response.get("results", []):
                    page = self._parse_page_response(page_data)
                    # Check if query matches any text property
                    for prop_value in page.properties.values():
                        if (
                            isinstance(prop_value, str)
                            and query_lower in prop_value.lower()
                        ):
                            pages.append(page)
                            break

                return pages[:limit]
            except Exception:
                # Return empty list if all search attempts fail
                return []

    def get_database_schema(self, database_id: str) -> Dict[str, str]:
        """Get the property schema for a database.

        Args:
            database_id: The database ID

        Returns:
            Dict mapping property names to their types
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        response = self._execute_with_retry(
            lambda: self.client.databases.retrieve(database_id)
        )

        schema = {}
        for prop_name, prop_data in response.get("properties", {}).items():
            schema[prop_name] = prop_data.get("type", "unknown")

        return schema

    def _format_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Format properties for Notion API.

        Args:
            properties: Raw property values

        Returns:
            Formatted properties for API
        """
        formatted = {}

        for prop_name, value in properties.items():
            if value is None:
                continue

            # Try to infer property type from value
            if isinstance(value, bool):
                prop_type = "checkbox"
            elif isinstance(value, (int, float)):
                prop_type = "number"
            elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                # Could be multi-select, people, or relation
                # For now, default to multi-select
                prop_type = "multi_select"
            elif "@" in str(value):
                prop_type = "email"
            elif str(value).startswith(("http://", "https://")):
                prop_type = "url"
            else:
                # Default to text
                prop_type = "rich_text"

            # Create handler and format
            try:
                handler = PropertyHandlerFactory.create(prop_type)
                if handler.validate(value):
                    formatted[prop_name] = handler.format_for_api(value)
            except Exception as e:
                print(f"Warning: Failed to format property '{prop_name}': {e}")

        return formatted

    def _build_filter(self, filter_query: Dict[str, Any]) -> Dict[str, Any]:
        """Build a Notion filter from simple query.

        Args:
            filter_query: Simple query like {"Full Name": "John Doe"}

        Returns:
            Notion API filter object
        """
        if not filter_query:
            return {}

        # For now, support single property filters
        if len(filter_query) == 1:
            prop_name, value = next(iter(filter_query.items()))

            # Build appropriate filter based on value type
            if isinstance(value, str):
                return {"property": prop_name, "rich_text": {"equals": value}}
            elif isinstance(value, (int, float)):
                return {"property": prop_name, "number": {"equals": value}}
            elif isinstance(value, bool):
                return {"property": prop_name, "checkbox": {"equals": value}}

        # TODO: Support more complex filters
        return {}

    def _parse_page_response(self, response: Dict[str, Any]) -> NotionPage:
        """Parse API response into NotionPage model.

        Args:
            response: Raw API response

        Returns:
            NotionPage instance
        """
        # Parse properties
        properties = {}
        for prop_name, prop_data in response.get("properties", {}).items():
            prop_type = prop_data.get("type")
            if prop_type:
                try:
                    handler = PropertyHandlerFactory.create(prop_type)
                    properties[prop_name] = handler.parse_from_api(prop_data)
                except Exception as e:
                    print(f"Warning: Failed to parse property '{prop_name}': {e}")

        return NotionPage(
            id=response["id"],
            database_id=response.get("parent", {}).get("database_id", ""),
            properties=properties,
            created_time=datetime.fromisoformat(
                response["created_time"].replace("Z", "+00:00")
            ),
            last_edited_time=datetime.fromisoformat(
                response["last_edited_time"].replace("Z", "+00:00")
            ),
            url=response.get("url"),
        )

    def _get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a page by ID.

        Args:
            page_id: The page ID

        Returns:
            Raw page data
        """
        self.rate_limiter.wait_if_needed()
        return self._execute_with_retry(lambda: self.client.pages.retrieve(page_id))

    def _get_relation_ids(
        self, page: Dict[str, Any], relation_property: str
    ) -> List[str]:
        """Extract relation IDs from a page.

        Args:
            page: Raw page data
            relation_property: Name of relation property

        Returns:
            List of related page IDs
        """
        prop_data = page.get("properties", {}).get(relation_property, {})
        relations = prop_data.get("relation", [])
        return [r["id"] for r in relations if "id" in r]

    def _execute_with_retry(self, func, max_attempts: Optional[int] = None):
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            max_attempts: Override default retry attempts

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        attempts = max_attempts or self.retry_attempts
        last_error = None

        for attempt in range(attempts):
            try:
                return func()
            except Exception as e:
                last_error = e

                # Check if error is retryable
                error_code = getattr(e, "code", None)
                if error_code in ["invalid_request", "unauthorized"]:
                    # Don't retry these errors
                    raise

                if attempt < attempts - 1:
                    # Exponential backoff
                    wait_time = (2**attempt) + 0.1
                    print(
                        f"API error (attempt {attempt + 1}/{attempts}): {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)

        # All retries failed
        raise last_error
