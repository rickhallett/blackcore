"""Simplified Notion API client for database updates."""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import NotionPage
from .property_handlers import PropertyHandlerFactory
from . import constants
from .logging_config import get_logger, log_event, log_error, log_performance, Timer
from .error_handling import (
    ErrorHandler, 
    NotionAPIError, 
    ValidationError,
    handle_errors,
    retry_on_error,
    ErrorContext
)

logger = get_logger(__name__)


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, requests_per_second: float = constants.DEFAULT_RATE_LIMIT):
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
                log_event(
                    __name__,
                    "rate_limit_throttle",
                    sleep_ms=sleep_time * 1000,
                    requests_per_second=1.0 / self.min_interval
                )
                time.sleep(sleep_time)

            self.last_request_time = time.time()


class NotionUpdater:
    """Simplified Notion client for creating and updating database entries with rate limiting and error handling."""

    def __init__(
        self,
        api_key: str,
        rate_limit: float = constants.DEFAULT_RATE_LIMIT,
        retry_attempts: int = constants.DEFAULT_RETRY_ATTEMPTS,
        pool_connections: int = constants.DEFAULT_POOL_CONNECTIONS,
        pool_maxsize: int = constants.DEFAULT_POOL_MAXSIZE,
    ):
        """Initialize Notion updater.

        Args:
            api_key: Notion API key
            rate_limit: Requests per second limit
            retry_attempts: Number of retry attempts for failed requests
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in the pool
        """
        # Validate API key
        from .validators import validate_api_key
        if not validate_api_key(api_key, "notion"):
            raise ValueError("Invalid Notion API key format")
            
        self.api_key = api_key
        self.retry_attempts = retry_attempts
        self.rate_limiter = RateLimiter(rate_limit)
        self.timeout = (10.0, 60.0)  # (connect timeout, read timeout)
        
        # Setup HTTP session with connection pooling
        self.session = self._create_session(pool_connections, pool_maxsize)

        # Lazy import to avoid dependency if not needed
        try:
            from notion_client import Client

            # Pass session to client if supported, otherwise it will use its own
            self.client = Client(auth=api_key, session=self.session)
        except ImportError:
            raise ImportError(
                "notion-client package required. Install with: pip install notion-client"
            )
        except TypeError:
            # If the client doesn't support session parameter, create without it
            self.client = Client(auth=api_key)
            # Store session reference for potential manual usage
            self.client._session = self.session
    
    def _create_session(self, pool_connections: int, pool_maxsize: int) -> requests.Session:
        """Create and configure HTTP session with connection pooling.
        
        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in the pool
            
        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=constants.RETRY_TOTAL_ATTEMPTS,
            backoff_factor=constants.RETRY_BACKOFF_FACTOR,
            status_forcelist=constants.RETRY_STATUS_FORCELIST,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        # Create adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        # Mount adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": constants.NOTION_API_VERSION
        })
        
        return session
    
    def close(self):
        """Close the HTTP session and clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
    
    def __enter__(self):
        """Support using NotionUpdater as a context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting context."""
        self.close()
        return False

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
        with Timer() as timer:
            response = self._execute_with_retry(
                lambda: self.client.pages.create(
                    parent={"database_id": database_id}, properties=formatted_properties
                )
            )
        
        page = self._parse_page_response(response)
        
        log_event(
            __name__,
            "page_created",
            page_id=page.id,
            database_id=database_id,
            properties_count=len(properties),
            duration_ms=timer.duration_ms
        )
        
        return page

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
        with Timer() as timer:
            response = self._execute_with_retry(
                lambda: self.client.pages.update(
                    page_id=page_id, properties=formatted_properties
                )
            )
        
        page = self._parse_page_response(response)
        
        log_event(
            __name__,
            "page_updated",
            page_id=page_id,
            properties_count=len(properties),
            duration_ms=timer.duration_ms
        )
        
        return page

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
                with ErrorContext("format_property", property_name=prop_name, convert_to=ValidationError):
                    handler = PropertyHandlerFactory.create(prop_type)
                    if handler.validate(value):
                        formatted[prop_name] = handler.format_for_api(value)
                    else:
                        raise ValidationError(
                            f"Property validation failed for '{prop_name}'",
                            field_name=prop_name,
                            field_value=value,
                            context={"property_type": prop_type}
                        )
            except ValidationError as e:
                # Log validation error but continue processing other properties
                log_error(
                    __name__,
                    "property_format_validation_failed",
                    e,
                    property_name=prop_name,
                    property_type=prop_type,
                    value_type=type(value).__name__
                )

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

        # Support multiple property filters with AND logic
        if len(filter_query) > 1:
            filters = []
            for prop_name, value in filter_query.items():
                if isinstance(value, str):
                    filters.append({"property": prop_name, "rich_text": {"equals": value}})
                elif isinstance(value, (int, float)):
                    filters.append({"property": prop_name, "number": {"equals": value}})
                elif isinstance(value, bool):
                    filters.append({"property": prop_name, "checkbox": {"equals": value}})
            
            if filters:
                return {"and": filters}
        
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
                    with ErrorContext("parse_property", property_name=prop_name, convert_to=ValidationError):
                        handler = PropertyHandlerFactory.create(prop_type)
                        properties[prop_name] = handler.parse_from_api(prop_data)
                except ValidationError as e:
                    # Log parsing error but continue with other properties
                    log_error(
                        __name__,
                        "property_parse_failed",
                        e,
                        property_name=prop_name,
                        property_type=prop_type
                    )

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
            NotionAPIError: If all retries fail
        """
        error_handler = ErrorHandler(
            context={"operation": "notion_api_call"},
            log_errors=True
        )
        
        attempts = max_attempts or self.retry_attempts
        last_error = None

        for attempt in range(attempts):
            try:
                return func()
            except Exception as e:
                # Convert to NotionAPIError if needed
                if not isinstance(e, NotionAPIError):
                    # Try to extract Notion-specific error details
                    error_code = getattr(e, "code", None)
                    status_code = getattr(e, "status", None) or getattr(e, "status_code", None)
                    
                    notion_error = NotionAPIError(
                        f"Notion API error: {str(e)}",
                        error_code=error_code,
                        status_code=status_code,
                        context={
                            "attempt": attempt + 1,
                            "max_attempts": attempts,
                            "original_error": type(e).__name__
                        }
                    )
                else:
                    notion_error = e
                    notion_error.context.update({
                        "attempt": attempt + 1,
                        "max_attempts": attempts
                    })
                
                last_error = notion_error

                # Check if error is retryable using standardized logic
                if not error_handler.is_retryable(notion_error):
                    # Log and raise non-retryable errors immediately
                    error_handler.handle_error(notion_error, critical=True)

                if attempt < attempts - 1:
                    # Log retry attempt
                    wait_time = (2**attempt) + 0.1
                    log_event(
                        __name__,
                        "notion_api_retry",
                        attempt=attempt + 1,
                        max_attempts=attempts,
                        wait_time=wait_time,
                        error=str(notion_error)
                    )
                    time.sleep(wait_time)

        # All retries failed - log and raise
        error_handler.handle_error(last_error, critical=True)
