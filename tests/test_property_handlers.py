"""Unit tests for property handlers."""

import pytest
from datetime import datetime, date

from blackcore.handlers.base import PropertyHandlerRegistry, property_handler_registry
from blackcore.handlers.text import TitleHandler, RichTextHandler
from blackcore.handlers.number import NumberHandler
from blackcore.handlers.select import SelectHandler, MultiSelectHandler, StatusHandler
from blackcore.handlers.date import DateHandler
from blackcore.handlers.people import PeopleHandler
from blackcore.models.properties import (
    PropertyType,
    TitleProperty,
    RichTextProperty,
    NumberProperty,
    SelectProperty,
    MultiSelectProperty,
    DateProperty,
    PeopleProperty,
)
from blackcore.errors.handlers import ValidationError


class TestPropertyHandlerRegistry:
    """Test property handler registry."""

    def test_registry_initialization(self):
        """Test that registry initializes properly."""
        registry = PropertyHandlerRegistry()
        assert registry._handlers == {}
        assert registry._initialized is False

    def test_auto_registration(self):
        """Test automatic handler registration."""
        registry = PropertyHandlerRegistry()

        # Getting a handler should trigger auto-registration
        handler = registry.get_handler(PropertyType.TITLE)

        assert isinstance(handler, TitleHandler)
        assert registry._initialized is True
        assert PropertyType.TITLE in registry._handlers

    def test_get_handler_by_string(self):
        """Test getting handler by string property type."""
        handler = property_handler_registry.get_handler("rich_text")
        assert isinstance(handler, RichTextHandler)

    def test_get_handler_not_found(self):
        """Test error when handler not found."""
        registry = PropertyHandlerRegistry()
        registry._initialized = True  # Skip auto-registration

        with pytest.raises(KeyError) as exc_info:
            registry.get_handler("non_existent_type")

        assert "No handler registered" in str(exc_info.value)


class TestTitleHandler:
    """Test title property handler."""

    def test_title_property(self):
        """Test title property simplification."""
        page = {
            "id": "test-id",
            "properties": {"Name": {"type": "title", "title": [{"plain_text": "Test Title"}]}},
        }

        result = NotionClient.simplify_page_properties(page)

        assert result["Name"] == "Test Title"
        assert result["notion_page_id"] == "test-id"

    def test_rich_text_property(self):
        """Test rich text property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Description": {
                    "type": "rich_text",
                    "rich_text": [{"plain_text": "Test description text"}],
                }
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Description"] == "Test description text"

    def test_select_property(self):
        """Test select property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Status": {"type": "select", "select": {"name": "Active", "color": "green"}}
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Status"] == "Active"

    def test_multi_select_property(self):
        """Test multi-select property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Tags": {
                    "type": "multi_select",
                    "multi_select": [
                        {"name": "Tag1", "color": "blue"},
                        {"name": "Tag2", "color": "red"},
                    ],
                }
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Tags"] == ["Tag1", "Tag2"]

    def test_number_property(self):
        """Test number property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Priority": {"type": "number", "number": 42},
                "Score": {"type": "number", "number": 3.14},
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Priority"] == 42
        assert result["Score"] == 3.14

    def test_checkbox_property(self):
        """Test checkbox property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Is Active": {"type": "checkbox", "checkbox": True},
                "Is Complete": {"type": "checkbox", "checkbox": False},
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Is Active"] is True
        assert result["Is Complete"] is False

    def test_date_property(self):
        """Test date property simplification."""
        # Simple date
        page = {
            "id": "test-id",
            "properties": {
                "Due Date": {"type": "date", "date": {"start": "2025-07-15", "end": None}}
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Due Date"] == "2025-07-15"

        # Date range
        page["properties"]["Date Range"] = {
            "type": "date",
            "date": {"start": "2025-07-15", "end": "2025-07-20"},
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Date Range"] == {"start": "2025-07-15", "end": "2025-07-20"}

    def test_url_property(self):
        """Test URL property simplification."""
        page = {
            "id": "test-id",
            "properties": {"Website": {"type": "url", "url": "https://example.com"}},
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Website"] == "https://example.com"

    def test_email_property(self):
        """Test email property simplification."""
        page = {
            "id": "test-id",
            "properties": {"Contact Email": {"type": "email", "email": "test@example.com"}},
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Contact Email"] == "test@example.com"

    def test_phone_number_property(self):
        """Test phone number property simplification."""
        page = {
            "id": "test-id",
            "properties": {"Phone": {"type": "phone_number", "phone_number": "+1234567890"}},
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Phone"] == "+1234567890"

    def test_people_property(self):
        """Test people property simplification with various user types."""
        # User with name
        page = {
            "id": "test-id",
            "properties": {
                "Assignee": {
                    "type": "people",
                    "people": [{"object": "user", "id": "user-123", "name": "John Doe"}],
                }
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Assignee"] == "John Doe"

        # User with email only
        page["properties"]["Manager"] = {
            "type": "people",
            "people": [
                {"object": "user", "id": "user-456", "person": {"email": "jane@example.com"}}
            ],
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Manager"] == "jane@example.com"

        # Empty people property
        page["properties"]["Nobody"] = {"type": "people", "people": []}

        result = NotionClient.simplify_page_properties(page)
        assert result["Nobody"] is None

    def test_relation_property(self):
        """Test relation property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Related Pages": {
                    "type": "relation",
                    "relation": [{"id": "page-1"}, {"id": "page-2"}],
                }
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Related Pages"] == ["page-1", "page-2"]

    def test_files_property(self):
        """Test files property simplification."""
        page = {
            "id": "test-id",
            "properties": {
                "Attachments": {
                    "type": "files",
                    "files": [
                        {
                            "type": "external",
                            "name": "Document.pdf",
                            "external": {"url": "https://example.com/doc.pdf"},
                        },
                        {
                            "type": "file",
                            "name": "Image.png",
                            "file": {"url": "https://notion.so/image.png"},
                        },
                    ],
                }
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert len(result["Attachments"]) == 2
        assert result["Attachments"][0]["name"] == "Document.pdf"
        assert result["Attachments"][0]["url"] == "https://example.com/doc.pdf"
        assert result["Attachments"][1]["name"] == "Image.png"
        assert result["Attachments"][1]["url"] == "https://notion.so/image.png"

    def test_empty_properties(self):
        """Test handling of empty/null properties."""
        page = {
            "id": "test-id",
            "properties": {
                "Empty Title": {"type": "title", "title": []},
                "No Select": {"type": "select", "select": None},
                "No Number": {"type": "number", "number": None},
            },
        }

        result = NotionClient.simplify_page_properties(page)
        assert result["Empty Title"] is None
        assert result["No Select"] is None
        assert result["No Number"] is None


class TestPropertyBuilding:
    """Test build_payload_properties for all property types."""

    def test_title_property_building(self):
        """Test building title property payload."""
        schema = {"properties": {"Name": {"type": "title"}}}
        local_data = {"Name": "Test Title"}

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert "Name" in result
        assert result["Name"]["title"][0]["text"]["content"] == "Test Title"

    def test_text_length_limit(self):
        """Test that text properties enforce 2000 character limit."""
        schema = {"properties": {"Title": {"type": "title"}, "Description": {"type": "rich_text"}}}

        long_text = "x" * 3000
        local_data = {"Title": long_text, "Description": long_text}

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert len(result["Title"]["title"][0]["text"]["content"]) == 2000
        assert len(result["Description"]["rich_text"][0]["text"]["content"]) == 2000

    def test_multi_select_property_building(self):
        """Test building multi-select property payload."""
        schema = {"properties": {"Tags": {"type": "multi_select"}}}
        local_data = {"Tags": ["Tag1", "Tag2", "Tag3"]}

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert "Tags" in result
        assert len(result["Tags"]["multi_select"]) == 3
        assert result["Tags"]["multi_select"][0]["name"] == "Tag1"

    def test_number_property_building(self):
        """Test building number property payload."""
        schema = {"properties": {"Integer": {"type": "number"}, "Float": {"type": "number"}}}
        local_data = {"Integer": 42, "Float": 3.14}

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert result["Integer"]["number"] == 42
        assert result["Float"]["number"] == 3.14

    def test_checkbox_property_building(self):
        """Test building checkbox property payload."""
        schema = {"properties": {"Active": {"type": "checkbox"}}}
        local_data = {"Active": True}

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert result["Active"]["checkbox"] is True

    def test_date_property_building(self):
        """Test building date property payload."""
        schema = {"properties": {"Simple Date": {"type": "date"}, "Date Range": {"type": "date"}}}
        local_data = {
            "Simple Date": "2025-07-15",
            "Date Range": {"start": "2025-07-15", "end": "2025-07-20"},
        }

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert result["Simple Date"]["date"]["start"] == "2025-07-15"
        assert "end" not in result["Simple Date"]["date"]

        assert result["Date Range"]["date"]["start"] == "2025-07-15"
        assert result["Date Range"]["date"]["end"] == "2025-07-20"

    def test_url_email_phone_building(self):
        """Test building URL, email, and phone properties."""
        schema = {
            "properties": {
                "Website": {"type": "url"},
                "Email": {"type": "email"},
                "Phone": {"type": "phone_number"},
            }
        }
        local_data = {
            "Website": "https://example.com",
            "Email": "test@example.com",
            "Phone": "+1234567890",
        }

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert result["Website"]["url"] == "https://example.com"
        assert result["Email"]["email"] == "test@example.com"
        assert result["Phone"]["phone_number"] == "+1234567890"

    def test_files_property_building(self):
        """Test building files property payload."""
        schema = {"properties": {"Attachments": {"type": "files"}}}
        local_data = {
            "Attachments": [
                {"name": "Document.pdf", "url": "https://example.com/doc.pdf"},
                {"name": "Image.png", "url": "https://example.com/img.png"},
            ]
        }

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert "Attachments" in result
        assert len(result["Attachments"]["files"]) == 2
        assert result["Attachments"]["files"][0]["type"] == "external"
        assert result["Attachments"]["files"][0]["name"] == "Document.pdf"
        assert result["Attachments"]["files"][0]["external"]["url"] == "https://example.com/doc.pdf"

    def test_relation_property_building(self):
        """Test building relation property payload."""
        schema = {"properties": {"Related Items": {"type": "relation"}}}
        local_data = {"Related Items": ["Item 1", "Item 2"]}
        relation_lookups = {
            "Related Items": {
                "target_db": "Items Database",
                "id_map": {"Item 1": "item-1-id", "Item 2": "item-2-id"},
            }
        }

        result = NotionClient.build_payload_properties(schema, local_data, relation_lookups)

        assert "Related Items" in result
        assert len(result["Related Items"]["relation"]) == 2
        assert result["Related Items"]["relation"][0]["id"] == "item-1-id"
        assert result["Related Items"]["relation"][1]["id"] == "item-2-id"

    def test_null_property_handling(self):
        """Test that null properties are skipped."""
        schema = {
            "properties": {
                "Name": {"type": "title"},
                "Description": {"type": "rich_text"},
                "Status": {"type": "select"},
            }
        }
        local_data = {"Name": "Test", "Description": None, "Status": None}

        result = NotionClient.build_payload_properties(schema, local_data, {})

        assert "Name" in result
        assert "Description" not in result
        assert "Status" not in result

    def test_type_validation(self):
        """Test that properties validate their types."""
        schema = {
            "properties": {
                "Number": {"type": "number"},
                "Checkbox": {"type": "checkbox"},
                "Multi Select": {"type": "multi_select"},
            }
        }
        local_data = {
            "Number": "not a number",  # Wrong type
            "Checkbox": "not a bool",  # Wrong type
            "Multi Select": "not a list",  # Wrong type
        }

        result = NotionClient.build_payload_properties(schema, local_data, {})

        # Properties with wrong types should be skipped
        assert "Number" not in result
        assert "Checkbox" not in result
        assert "Multi Select" not in result


class TestPropertyRoundTrip:
    """Test that properties can be simplified and rebuilt correctly."""

    def test_all_properties_round_trip(self, sample_page_data, sample_database_schema):
        """Test round-trip conversion for all property types."""
        # Simplify the page data
        simplified = NotionClient.simplify_page_properties(sample_page_data)

        # Build it back
        relation_lookups = {
            "Related Pages": {
                "target_db": "Test Database",
                "id_map": {"related-page-1": "related-page-1", "related-page-2": "related-page-2"},
            }
        }

        # For round-trip, we need to map the simplified relation IDs back
        simplified["Related Pages"] = ["related-page-1", "related-page-2"]

        rebuilt = NotionClient.build_payload_properties(
            sample_database_schema, simplified, relation_lookups
        )

        # Verify key properties maintained their values
        assert rebuilt["Name"]["title"][0]["text"]["content"] == "Test Page Title"
        assert rebuilt["Description"]["rich_text"][0]["text"]["content"] == "Test description"
        assert rebuilt["Status"]["select"]["name"] == "Active"
        assert rebuilt["Priority"]["number"] == 5
        assert rebuilt["Is Active"]["checkbox"] is True
        assert rebuilt["Due Date"]["date"]["start"] == "2025-07-15"
        assert rebuilt["Website"]["url"] == "https://example.com"
        assert rebuilt["Email"]["email"] == "test@example.com"
        assert rebuilt["Phone"]["phone_number"] == "+1234567890"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
