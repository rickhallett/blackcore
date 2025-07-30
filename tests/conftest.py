"""Test configuration and fixtures for Notion sync tests."""

import pytest
from unittest.mock import Mock
from typing import Dict, Any, List
import time

# Mock the notion_client module to prevent import errors during testing
from notion_client.errors import APIResponseError


@pytest.fixture
def mock_notion_client():
    """Mock Notion client with rate limiting simulation."""
    client = Mock()
    client.request_count = 0
    client.rate_limit_threshold = 3
    client.rate_limit_reset_time = time.time()

    def track_rate_limit(*args, **kwargs):
        """Simulate rate limiting behavior."""
        current_time = time.time()

        # Reset counter every second
        if current_time - client.rate_limit_reset_time >= 1.0:
            client.request_count = 0
            client.rate_limit_reset_time = current_time

        client.request_count += 1

        if client.request_count > client.rate_limit_threshold:
            error = APIResponseError(
                code="rate_limited",
                message="Rate limited. Please retry after 1 second.",
            )
            error.code = "rate_limited"
            raise error

        # Return a default response
        return {"has_more": False, "results": [], "next_cursor": None}

    # Set up mock methods
    client.databases.query.side_effect = track_rate_limit
    client.databases.retrieve.side_effect = track_rate_limit
    client.databases.create.side_effect = track_rate_limit
    client.databases.update.side_effect = track_rate_limit
    client.pages.create.side_effect = track_rate_limit
    client.search.side_effect = track_rate_limit

    return client


@pytest.fixture
def sample_page_data():
    """Sample page data for testing property conversions."""
    return {
        "id": "test-page-id",
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": "Test Page Title"}]},
            "Description": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "Test description"}],
            },
            "Status": {"type": "select", "select": {"name": "Active"}},
            "Tags": {
                "type": "multi_select",
                "multi_select": [{"name": "Tag1"}, {"name": "Tag2"}],
            },
            "Priority": {"type": "number", "number": 5},
            "Is Active": {"type": "checkbox", "checkbox": True},
            "Due Date": {"type": "date", "date": {"start": "2025-07-15", "end": None}},
            "Website": {"type": "url", "url": "https://example.com"},
            "Email": {"type": "email", "email": "test@example.com"},
            "Phone": {"type": "phone_number", "phone_number": "+1234567890"},
            "Assignee": {
                "type": "people",
                "people": [
                    {
                        "object": "user",
                        "id": "user-123",
                        "name": "John Doe",
                        "person": {"email": "john@example.com"},
                    }
                ],
            },
            "Related Pages": {
                "type": "relation",
                "relation": [{"id": "related-page-1"}, {"id": "related-page-2"}],
            },
            "Attachments": {
                "type": "files",
                "files": [
                    {
                        "type": "external",
                        "name": "Document.pdf",
                        "external": {"url": "https://example.com/doc.pdf"},
                    }
                ],
            },
        },
    }


@pytest.fixture
def sample_database_schema():
    """Sample database schema for testing."""
    return {
        "id": "test-db-id",
        "title": [{"plain_text": "Test Database"}],
        "properties": {
            "Name": {"type": "title", "title": {}},
            "Description": {"type": "rich_text", "rich_text": {}},
            "Status": {
                "type": "select",
                "select": {
                    "options": [
                        {"name": "Active", "color": "green"},
                        {"name": "Inactive", "color": "red"},
                    ]
                },
            },
            "Tags": {"type": "multi_select", "multi_select": {"options": []}},
            "Priority": {"type": "number", "number": {"format": "number"}},
            "Is Active": {"type": "checkbox", "checkbox": {}},
            "Due Date": {"type": "date", "date": {}},
            "Website": {"type": "url", "url": {}},
            "Email": {"type": "email", "email": {}},
            "Phone": {"type": "phone_number", "phone_number": {}},
            "Assignee": {"type": "people", "people": {}},
            "Related Pages": {
                "type": "relation",
                "relation": {"database_id": "related-db-id"},
            },
            "Attachments": {"type": "files", "files": {}},
        },
    }


@pytest.fixture
def test_data_generator():
    """Factory for generating test data."""

    def generate_people(count: int) -> List[Dict[str, Any]]:
        """Generate test people data."""
        people = []
        for i in range(count):
            people.append(
                {
                    "Full Name": f"Person {i}",
                    "Role": ["Target", "Ally", "Neutral", "Adversary", "Unknown"][
                        i % 5
                    ],
                    "Email": f"person{i}@example.com",
                    "Phone": f"+1234567{i:03d}",
                    "Organization": f"Org {i // 10}",
                    "Notes": f"Test notes for person {i}",
                    "First Contact": "2025-01-01",
                    "Is Active": i % 2 == 0,
                    "Priority": (i % 5) + 1,
                }
            )
        return people

    def generate_orgs(count: int) -> List[Dict[str, Any]]:
        """Generate test organization data."""
        orgs = []
        for i in range(count):
            orgs.append(
                {
                    "Organization Name": f"Organization {i}",
                    "Type": ["Government", "Corporate", "NGO", "Academic"][i % 4],
                    "Website": f"https://org{i}.example.com",
                    "Contact Email": f"contact@org{i}.example.com",
                    "Key People": [f"Person {i * 2}", f"Person {i * 2 + 1}"],
                    "Description": f"Test organization {i} description",
                }
            )
        return orgs

    def generate_transgressions(count: int) -> List[Dict[str, Any]]:
        """Generate test transgression data."""
        transgressions = []
        for i in range(count):
            transgressions.append(
                {
                    "Transgression ID": f"TR-{i:04d}",
                    "Description": f"Test transgression {i}",
                    "Severity": ["Low", "Medium", "High", "Critical"][i % 4],
                    "Date Identified": f"2025-01-{(i % 28) + 1:02d}",
                    "People Involved": [f"Person {i % 10}"],
                    "Organizations Involved": [f"Organization {i % 5}"],
                    "Status": ["Open", "Under Investigation", "Resolved"][i % 3],
                    "Evidence Files": [
                        {
                            "name": f"evidence_{i}.pdf",
                            "url": f"https://example.com/evidence_{i}.pdf",
                        }
                    ],
                }
            )
        return transgressions

    return {
        "generate_people": generate_people,
        "generate_orgs": generate_orgs,
        "generate_transgressions": generate_transgressions,
    }


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "People & Contacts": {
            "id": "people-db-id",
            "local_json_path": "test_data/people_contacts.json",
            "json_data_key": "People & Contacts",
            "title_property": "Full Name",
            "list_properties": ["Organization"],
            "relations": {"Organization": "Organizations & Bodies"},
        },
        "Organizations & Bodies": {
            "id": "orgs-db-id",
            "local_json_path": "test_data/organizations_bodies.json",
            "json_data_key": "Organizations & Bodies",
            "title_property": "Organization Name",
            "list_properties": ["Key People"],
            "relations": {"Key People": "People & Contacts"},
        },
        "Identified Transgressions": {
            "id": "transgressions-db-id",
            "local_json_path": "test_data/identified_transgressions.json",
            "json_data_key": "Identified Transgressions",
            "title_property": "Transgression ID",
            "list_properties": ["People Involved", "Organizations Involved"],
            "relations": {
                "People Involved": "People & Contacts",
                "Organizations Involved": "Organizations & Bodies",
            },
        },
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for tests."""
    cache_dir = tmp_path / "notion_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


class MockAPIResponseError(Exception):
    """Mock for notion_client.errors.APIResponseError."""

    def __init__(self, code=None, message="API Error"):
        self.code = code
        self.message = message
        super().__init__(message)


@pytest.fixture
def sample_people_data():
    """Provide sample people data with known duplicates."""
    return [
        {
            "id": "person-1",
            "Full Name": "John Smith",
            "Email": "john.smith@example.com",
            "Phone": "555-0123",
            "Organization": "Acme Corp",
        },
        {
            "id": "person-2",
            "Full Name": "John Smith",  # Exact duplicate
            "Email": "john.smith@example.com",
            "Phone": "555-0123",
            "Organization": "Acme Corp",
        },
        {
            "id": "person-3",
            "Full Name": "John Doe",
            "Email": "john.doe@example.com",
            "Phone": "555-0456",
            "Organization": "Beta Inc",
        },
        {
            "id": "person-4",
            "Full Name": "Jon Smith",  # Similar to John Smith
            "Email": "j.smith@acme.com",
            "Phone": "555-0123",
            "Organization": "Acme Corp",
        },
        {
            "id": "person-5",
            "Full Name": "Jane Doe",
            "Email": "jane.doe@example.com",
            "Phone": "555-0789",
            "Organization": "Gamma LLC",
        },
        {
            "id": "person-6",
            "Full Name": "Tony Powell",
            "Email": ["tony.powell@example.com", "tpowell@org.com"],  # List value
            "Phone": "555-1111",
            "Organization": ["ABC Org", "XYZ Corp"],  # List value
        },
        {
            "id": "person-7",
            "Full Name": "Tony Powell",  # Similar with some differences
            "Email": "tony.powell@example.com",
            "Phone": "555-1111",
            "Organization": "ABC Org",
            "Title": "Director",
        },
    ]
