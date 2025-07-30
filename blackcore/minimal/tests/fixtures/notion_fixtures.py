"""Notion API response fixtures."""

from typing import Dict, Any

# Successful page creation response
NOTION_PAGE_RESPONSE = {
    "object": "page",
    "id": "page-123-456",
    "created_time": "2025-01-10T12:00:00.000Z",
    "last_edited_time": "2025-01-10T12:00:00.000Z",
    "created_by": {"object": "user", "id": "user-123"},
    "last_edited_by": {"object": "user", "id": "user-123"},
    "cover": None,
    "icon": None,
    "parent": {"type": "database_id", "database_id": "db-123"},
    "archived": False,
    "properties": {
        "Name": {
            "id": "title",
            "type": "title",
            "title": [{"type": "text", "text": {"content": "Test Page"}}],
        },
        "Status": {
            "id": "status",
            "type": "select",
            "select": {"name": "Active", "color": "green"},
        },
    },
    "url": "https://www.notion.so/Test-Page-123456",
}

# Database schema response
DATABASE_SCHEMA_RESPONSE = {
    "object": "database",
    "id": "db-123",
    "title": [{"type": "text", "text": {"content": "Test Database"}}],
    "properties": {
        "Name": {"id": "title", "name": "Name", "type": "title", "title": {}},
        "Email": {"id": "email", "name": "Email", "type": "email", "email": {}},
        "Phone": {"id": "phone", "name": "Phone", "type": "phone_number", "phone_number": {}},
        "Status": {
            "id": "status",
            "name": "Status",
            "type": "select",
            "select": {
                "options": [
                    {"name": "Active", "color": "green"},
                    {"name": "Inactive", "color": "red"},
                ]
            },
        },
        "Tags": {
            "id": "tags",
            "name": "Tags",
            "type": "multi_select",
            "multi_select": {
                "options": [
                    {"name": "Important", "color": "red"},
                    {"name": "Review", "color": "blue"},
                ]
            },
        },
        "Created": {"id": "created", "name": "Created", "type": "created_time", "created_time": {}},
    },
}

# Search results with pagination
SEARCH_RESULTS_RESPONSE = {
    "object": "list",
    "results": [
        NOTION_PAGE_RESPONSE,
        {
            **NOTION_PAGE_RESPONSE,
            "id": "page-789-012",
            "properties": {
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [{"type": "text", "text": {"content": "Another Page"}}],
                }
            },
        },
    ],
    "has_more": True,
    "next_cursor": "cursor-123",
}

# Rate limit error response
RATE_LIMIT_ERROR = {
    "object": "error",
    "status": 429,
    "code": "rate_limited",
    "message": "You have been rate limited. Please try again later.",
}

# Validation error response
VALIDATION_ERROR = {
    "object": "error",
    "status": 400,
    "code": "validation_error",
    "message": "body.properties.Email.email should be a string",
}

# Not found error
NOT_FOUND_ERROR = {
    "object": "error",
    "status": 404,
    "code": "object_not_found",
    "message": "Could not find database with id: db-invalid",
}

# Property value examples
PROPERTY_VALUES = {
    "title": [{"type": "text", "text": {"content": "Sample Title"}}],
    "rich_text": [{"type": "text", "text": {"content": "Sample text content"}}],
    "number": 42,
    "checkbox": True,
    "select": {"name": "Option 1"},
    "multi_select": [{"name": "Tag 1"}, {"name": "Tag 2"}],
    "date": {"start": "2025-01-10"},
    "people": [{"object": "user", "id": "user-123"}],
    "files": [
        {
            "name": "document.pdf",
            "type": "external",
            "external": {"url": "https://example.com/doc.pdf"},
        }
    ],
    "email": "test@example.com",
    "phone_number": "+1-555-123-4567",
    "url": "https://example.com",
    "relation": [{"id": "related-page-123"}],
}


def create_mock_page(page_id: str = "page-123", **properties) -> Dict[str, Any]:
    """Create a mock Notion page response with custom properties."""
    base = NOTION_PAGE_RESPONSE.copy()
    base["id"] = page_id

    if properties:
        base["properties"] = {}
        for name, value in properties.items():
            if name == "title" or name == "Name":
                base["properties"]["Name"] = {
                    "type": "title",
                    "title": [{"type": "text", "text": {"content": value}}],
                }
            else:
                # Simplified - would need proper type handling in real implementation
                base["properties"][name] = {
                    "type": "rich_text",
                    "rich_text": [{"type": "text", "text": {"content": str(value)}}],
                }

    return base


def create_error_response(status: int, code: str, message: str) -> Dict[str, Any]:
    """Create a mock error response."""
    return {"object": "error", "status": status, "code": code, "message": message}
