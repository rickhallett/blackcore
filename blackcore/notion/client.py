"""Notion API client wrapper for Project Nassau."""

import os
import json
import time
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from datetime import datetime
from notion_client import Client
from notion_client.errors import APIResponseError
from dotenv import load_dotenv
from rich.console import Console

# --- Module-level setup ---
load_dotenv()
console = Console()

# --- Constants ---
# Define paths relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE_PATH = PROJECT_ROOT / "blackcore/config/notion_config.json"
CACHE_DIR = PROJECT_ROOT / "blackcore/models/notion_cache"

# Rate limiting configuration
RATE_LIMIT_REQUESTS_PER_SECOND = 3
RATE_LIMIT_DELAY = 1.0 / RATE_LIMIT_REQUESTS_PER_SECOND  # ~334ms

# Validation constants
MAX_TEXT_LENGTH = 2000
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
URL_REGEX = re.compile(r"^https?://[^\s]+$")
ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?)?$")


class RateLimiter:
    """Simple rate limiter to comply with Notion API limits."""

    def __init__(self, requests_per_second: float = RATE_LIMIT_REQUESTS_PER_SECOND):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_interval:
            sleep_time = self.min_interval - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()


def rate_limited(func):
    """Decorator to apply rate limiting to Notion API calls."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, "_rate_limiter"):
            self._rate_limiter.wait_if_needed()
        return func(self, *args, **kwargs)

    return wrapper


def with_retry(max_attempts: int = 3, backoff_base: float = 2.0):
    """Decorator to add retry logic with exponential backoff for API calls."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except APIResponseError as e:
                    last_exception = e

                    # Don't retry on certain error codes
                    if hasattr(e, "code"):
                        if e.code in ["invalid_request", "unauthorized", "restricted_resource"]:
                            raise  # Don't retry these errors

                    if attempt < max_attempts - 1:
                        # Calculate backoff time with jitter
                        backoff_time = (backoff_base**attempt) + random.uniform(0, 1)

                        console.print(
                            f"[yellow]API error (attempt {attempt + 1}/{max_attempts}): {str(e)}. "
                            f"Retrying in {backoff_time:.1f} seconds...[/yellow]"
                        )
                        time.sleep(backoff_time)
                    else:
                        # Last attempt failed
                        console.print(
                            f"[red]API error after {max_attempts} attempts: {str(e)}[/red]"
                        )
                except Exception as e:
                    # For non-API errors, don't retry
                    raise

            # If we get here, all attempts failed
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def validate_email(email: str) -> bool:
    """Validate email format."""
    return bool(EMAIL_REGEX.match(email))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    return bool(URL_REGEX.match(url))


def validate_iso_date(date_str: str) -> bool:
    """Validate ISO 8601 date format."""
    if not ISO_DATE_REGEX.match(date_str):
        return False
    try:
        # Additional validation to ensure it's a valid date
        if "T" in date_str:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Truncate text to maximum length."""
    return text[:max_length] if len(text) > max_length else text


class NotionClient:
    """A centralized client to handle all Notion API interactions."""

    def __init__(self):
        api_key = os.getenv("NOTION_API_KEY")
        if not api_key:
            raise ValueError("NOTION_API_KEY not found in .env file.")
        self.client = Client(auth=api_key)
        self._database_cache: Dict[str, str] = {}
        self._rate_limiter = RateLimiter()

    @rate_limited
    @with_retry()
    def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Retrieves the full schema for a single database."""
        return self.client.databases.retrieve(database_id=database_id)

    @rate_limited
    @with_retry()
    def discover_databases(self) -> List[Dict[str, Any]]:
        """Searches the workspace for all databases accessible by the integration."""
        console.print("Searching for databases in the Notion workspace...", style="yellow")
        response = self.client.search(filter={"property": "object", "value": "database"})
        databases = response.get("results", [])

        if not databases:
            console.print("[bold yellow]Warning:[/] No databases found.", style="yellow")
        else:
            console.print(f"Found {len(databases)} accessible database(s).", style="green")
        return databases

    @rate_limited
    @with_retry()
    def get_all_database_pages(self, database_id: str) -> List[Dict[str, Any]]:
        """Gets all pages from a database, handling pagination."""
        pages = []
        has_more = True
        start_cursor = None

        while has_more:
            response = self.client.databases.query(
                database_id=database_id, page_size=100, start_cursor=start_cursor
            )
            pages.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor", None)

        return pages

    @staticmethod
    def simplify_page_properties(page: Dict[str, Any]) -> Dict[str, Any]:
        """Converts a Notion page object to our simple key-value format."""
        properties = page.get("properties", {})
        simple_page = {"notion_page_id": page["id"]}
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            if not prop_type or not prop_data.get(prop_type):
                simple_page[prop_name] = None
                continue

            if prop_type == "title":
                value = prop_data["title"][0]["plain_text"] if prop_data["title"] else None
            elif prop_type == "rich_text":
                value = prop_data["rich_text"][0]["plain_text"] if prop_data["rich_text"] else None
            elif prop_type == "select":
                value = prop_data["select"]["name"] if prop_data["select"] else None
            elif prop_type == "people":
                if prop_data["people"]:
                    # Handle people property - can be users with email or non-users with name
                    people_list = []
                    for person in prop_data["people"]:
                        if person.get("object") == "user":
                            # Try to get name, fallback to email
                            name = person.get("name")
                            if not name and "person" in person and "email" in person["person"]:
                                name = person["person"]["email"]
                            if name:
                                people_list.append(name)
                    value = people_list[0] if people_list else None
                else:
                    value = None
            elif prop_type == "relation":
                value = [item.get("id") for item in prop_data["relation"]]
            elif prop_type == "date":
                date_obj = prop_data.get("date")
                if date_obj:
                    value = date_obj.get("start")
                    # Include end date if it exists (for date ranges)
                    if date_obj.get("end"):
                        value = {"start": date_obj["start"], "end": date_obj["end"]}
                else:
                    value = None
            elif prop_type == "checkbox":
                value = prop_data.get("checkbox", False)
            elif prop_type == "number":
                value = prop_data.get("number")
            elif prop_type == "url":
                value = prop_data.get("url")
            elif prop_type == "email":
                value = prop_data.get("email")
            elif prop_type == "phone_number":
                value = prop_data.get("phone_number")
            elif prop_type == "multi_select":
                options = prop_data.get("multi_select", [])
                value = [opt.get("name") for opt in options if opt.get("name")]
            elif prop_type == "files":
                files = prop_data.get("files", [])
                value = []
                for file in files:
                    if file.get("type") == "external":
                        value.append(
                            {"name": file.get("name"), "url": file.get("external", {}).get("url")}
                        )
                    elif file.get("type") == "file":
                        value.append(
                            {"name": file.get("name"), "url": file.get("file", {}).get("url")}
                        )
            else:
                value = None
            simple_page[prop_name] = value
        return simple_page

    @rate_limited
    @with_retry()
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

    @rate_limited
    @with_retry()
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

    @rate_limited
    @with_retry()
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

    @rate_limited
    @with_retry()
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

    @rate_limited
    @with_retry()
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

    @rate_limited
    @with_retry()
    def create_page(self, database_id: str, properties: Dict[str, Any]):
        """Creates a new page in the specified database."""
        payload = {"parent": {"database_id": database_id}, "properties": properties}
        try:
            return self.client.pages.create(**payload)
        except Exception as e:
            console.print(f"[bold red]API Error creating page:[/] {e}")
            return None

    @staticmethod
    def build_payload_properties(
        schema: Dict[str, Any],
        local_data: Dict[str, Any],
        relation_lookups: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Constructs the complex 'properties' object for a Notion API request."""
        payload_props = {}
        schema_props = schema.get("properties", {})

        for prop_name, prop_details in schema_props.items():
            prop_type = prop_details["type"]
            local_value = local_data.get(prop_name)

            if local_value is None:
                continue

            if prop_type == "title":
                payload_props[prop_name] = {
                    "title": [{"text": {"content": truncate_text(str(local_value))}}]
                }
            elif prop_type == "rich_text":
                payload_props[prop_name] = {
                    "rich_text": [{"text": {"content": truncate_text(str(local_value))}}]
                }
            elif prop_type == "select" and isinstance(local_value, str):
                # Note: We can't validate select options without fetching them from the schema
                # The API will create new options if they don't exist (depending on DB settings)
                payload_props[prop_name] = {
                    "select": {"name": truncate_text(local_value, 100)}
                }  # Select options have shorter limits
            elif prop_type == "multi_select" and isinstance(local_value, list):
                payload_props[prop_name] = {
                    "multi_select": [{"name": str(opt)} for opt in local_value]
                }
            elif prop_type == "number" and (isinstance(local_value, (int, float))):
                payload_props[prop_name] = {"number": local_value}
            elif prop_type == "checkbox" and isinstance(local_value, bool):
                payload_props[prop_name] = {"checkbox": local_value}
            elif prop_type == "date":
                if isinstance(local_value, str):
                    # Simple date string - validate format
                    if validate_iso_date(local_value):
                        payload_props[prop_name] = {"date": {"start": local_value}}
                    else:
                        console.print(
                            f"[yellow]Warning: Invalid date format for '{prop_name}': {local_value}. Expected ISO 8601 format (YYYY-MM-DD).[/yellow]"
                        )
                elif isinstance(local_value, dict) and "start" in local_value:
                    # Date range with start and optional end
                    start_date = local_value["start"]
                    if validate_iso_date(start_date):
                        date_obj = {"start": start_date}
                        if "end" in local_value and validate_iso_date(local_value["end"]):
                            date_obj["end"] = local_value["end"]
                        payload_props[prop_name] = {"date": date_obj}
                    else:
                        console.print(
                            f"[yellow]Warning: Invalid date format for '{prop_name}' start date: {start_date}.[/yellow]"
                        )
            elif prop_type == "url" and isinstance(local_value, str):
                if validate_url(local_value):
                    payload_props[prop_name] = {"url": local_value}
                else:
                    console.print(
                        f"[yellow]Warning: Invalid URL format for '{prop_name}': {local_value}.[/yellow]"
                    )
            elif prop_type == "email" and isinstance(local_value, str):
                if validate_email(local_value):
                    payload_props[prop_name] = {"email": local_value}
                else:
                    console.print(
                        f"[yellow]Warning: Invalid email format for '{prop_name}': {local_value}.[/yellow]"
                    )
            elif prop_type == "phone_number" and isinstance(local_value, str):
                payload_props[prop_name] = {"phone_number": local_value}
            elif prop_type == "files" and isinstance(local_value, list):
                files_list = []
                for file_info in local_value:
                    if isinstance(file_info, dict) and "url" in file_info:
                        files_list.append(
                            {
                                "type": "external",
                                "name": file_info.get("name", "File"),
                                "external": {"url": file_info["url"]},
                            }
                        )
                if files_list:
                    payload_props[prop_name] = {"files": files_list}
            elif prop_type == "relation" and isinstance(local_value, list):
                target_db_name = relation_lookups.get(prop_name, {}).get("target_db")
                id_map = relation_lookups.get(prop_name, {}).get("id_map", {})

                if not target_db_name:
                    continue

                relation_ids = []
                for name in local_value:
                    page_id = id_map.get(name)
                    if page_id:
                        relation_ids.append({"id": page_id})
                    else:
                        console.print(
                            f"\n[bold yellow]Warning:[/] Could not find page with title '[bold cyan]{name}[/]' in database '[bold cyan]{target_db_name}[/]' to create relation.",
                            style="yellow",
                        )

                if relation_ids:
                    payload_props[prop_name] = {"relation": relation_ids}
            # Note: People properties require user IDs which need to be fetched separately

        return payload_props


def save_config_to_file(databases: List[Dict[str, Any]]):
    """
    Generates and saves the configuration file by discovering all databases,
    their properties, and their relations in a two-pass process.
    """
    db_config = {}
    client = NotionClient()

    # --- Pass 1: Discover all databases and create an ID-to-Name map ---
    console.print("Pass 1: Discovering all databases and building an ID map...", style="yellow")
    id_to_name_map = {
        db["id"]: (db.get("title", [])[0]["plain_text"] if db.get("title") else "Untitled")
        for db in databases
    }
    console.print(f"Mapped {len(id_to_name_map)} database IDs to names.", style="green")

    # --- Pass 2: Fetch schema for each database and resolve relations ---
    console.print("\nPass 2: Fetching schemas and resolving relations...", style="yellow")
    for db in databases:
        db_id = db["id"]
        db_title = id_to_name_map.get(db_id, "Untitled Database")

        console.print(f"  -> Processing '[bold cyan]{db_title}[/]'...", end="")

        try:
            schema = client.get_database_schema(db_id)
            properties = schema.get("properties", {})

            title_property_name = "Name"
            discovered_relations = {}

            for prop_name, prop_details in properties.items():
                if prop_details.get("type") == "title":
                    title_property_name = prop_name

                if prop_details.get("type") == "relation":
                    relation_details = prop_details.get("relation", {})
                    target_db_id = relation_details.get("database_id")
                    if target_db_id and target_db_id in id_to_name_map:
                        target_db_name = id_to_name_map[target_db_id]
                        discovered_relations[prop_name] = target_db_name

            console.print(
                f" found title '[magenta]{title_property_name}[/]' and {len(discovered_relations)} relation(s)."
            )

            db_config[db_title] = {
                "id": db_id,
                "local_json_path": f"blackcore/models/json/{db_title.lower().replace(' & ', '_').replace(' ', '_')}.json",
                "json_data_key": db_title,
                "title_property": title_property_name,
                "list_properties": list(
                    discovered_relations.keys()
                ),  # Default list properties to all discovered relations
                "relations": discovered_relations,
            }
        except Exception as e:
            console.print(f"\n[bold red]Error fetching schema for {db_title}:[/] {e}")

    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(db_config, f, indent=4, ensure_ascii=False)
    console.print(
        f"\n[bold green]Success![/] Configuration written to '[bold]{CONFIG_FILE_PATH}[/]'."
    )


def load_config_from_file() -> Dict[str, Any]:
    """Loads the database configuration from the JSON file."""
    if not CONFIG_FILE_PATH.exists():
        console.print(f"[bold red]Error:[/] Configuration file '{CONFIG_FILE_PATH}' not found.")
        return None
    with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
