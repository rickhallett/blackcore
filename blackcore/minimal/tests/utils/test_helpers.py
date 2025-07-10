"""Test helper utilities."""

import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock
from datetime import datetime

from blackcore.minimal.config import Config, NotionConfig, AIConfig, DatabaseConfig
from blackcore.minimal.models import NotionPage


def create_test_config(
    notion_api_key: str = "test-api-key",
    ai_provider: str = "claude",
    ai_api_key: str = "test-ai-key",
    cache_dir: Optional[str] = None,
    dry_run: bool = False,
) -> Config:
    """Create a test configuration."""
    if cache_dir is None:
        cache_dir = tempfile.mkdtemp()

    return Config(
        notion=NotionConfig(
            api_key=notion_api_key,
            databases={
                "people": DatabaseConfig(
                    id="db-people-123",
                    name="People & Contacts",
                    mappings={
                        "name": "Full Name",
                        "email": "Email",
                        "role": "Role",
                        "company": "Organization",
                    },
                ),
                "organizations": DatabaseConfig(
                    id="db-org-456",
                    name="Organizations",
                    mappings={"name": "Name", "type": "Type", "location": "Location"},
                ),
                "tasks": DatabaseConfig(
                    id="db-tasks-789",
                    name="Tasks",
                    mappings={
                        "name": "Title",
                        "status": "Status",
                        "assignee": "Assigned To",
                        "due_date": "Due Date",
                    },
                ),
            },
        ),
        ai=AIConfig(
            provider=ai_provider,
            api_key=ai_api_key,
            model="claude-3" if ai_provider == "claude" else "gpt-4",
            max_tokens=4000,
            temperature=0.7,
        ),
        cache_dir=cache_dir,
        cache_ttl=3600,
        dry_run=dry_run,
    )


def create_mock_notion_client():
    """Create a mock Notion client."""
    mock = MagicMock()

    # Mock pages.create
    mock.pages.create.return_value = {"id": "page-123", "properties": {}}

    # Mock pages.update
    mock.pages.update.return_value = {"id": "page-123", "properties": {}}

    # Mock databases.query
    mock.databases.query.return_value = {"results": [], "has_more": False}

    # Mock databases.retrieve
    mock.databases.retrieve.return_value = {"id": "db-123", "properties": {}}

    return mock


def create_mock_ai_client(provider: str = "claude"):
    """Create a mock AI client."""
    mock = MagicMock()

    if provider == "claude":
        # Mock Claude client
        mock.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({"entities": [], "relationships": []}))]
        )
    else:
        # Mock OpenAI client
        mock.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content=json.dumps({"entities": [], "relationships": []}))
                )
            ]
        )

    return mock


def assert_notion_page_equal(actual: NotionPage, expected: NotionPage):
    """Assert two NotionPage objects are equal."""
    assert actual.id == expected.id
    assert actual.url == expected.url
    assert actual.properties == expected.properties
    assert actual.created_time == expected.created_time
    assert actual.last_edited_time == expected.last_edited_time


def create_temp_cache_dir():
    """Create a temporary cache directory."""
    return tempfile.mkdtemp(prefix="test_cache_")


def cleanup_temp_dir(path: str):
    """Clean up a temporary directory."""
    if Path(path).exists():
        shutil.rmtree(path)


class MockResponse:
    """Mock HTTP response for API testing."""

    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def mock_datetime_now(target_time: datetime):
    """Create a mock for datetime.now()."""
    mock = Mock()
    mock.now.return_value = target_time
    return mock


def assert_properties_formatted(properties: Dict[str, Any], expected_types: Dict[str, str]):
    """Assert that properties are correctly formatted for Notion API."""
    for prop_name, prop_type in expected_types.items():
        assert prop_name in properties
        prop_value = properties[prop_name]

        if prop_type == "title":
            assert "title" in prop_value
            assert isinstance(prop_value["title"], list)
        elif prop_type == "rich_text":
            assert "rich_text" in prop_value
            assert isinstance(prop_value["rich_text"], list)
        elif prop_type == "number":
            assert "number" in prop_value
        elif prop_type == "checkbox":
            assert "checkbox" in prop_value
            assert isinstance(prop_value["checkbox"], bool)
        elif prop_type == "select":
            assert "select" in prop_value
        elif prop_type == "multi_select":
            assert "multi_select" in prop_value
            assert isinstance(prop_value["multi_select"], list)
        elif prop_type == "date":
            assert "date" in prop_value
        elif prop_type == "email":
            assert "email" in prop_value
        elif prop_type == "phone_number":
            assert "phone_number" in prop_value
        elif prop_type == "url":
            assert "url" in prop_value
        elif prop_type == "relation":
            assert "relation" in prop_value
            assert isinstance(prop_value["relation"], list)
