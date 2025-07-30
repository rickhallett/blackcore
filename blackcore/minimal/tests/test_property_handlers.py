"""Tests for property handlers."""

import pytest
from datetime import datetime, date

from ..property_handlers import (
    PropertyHandler,
    PropertyHandlerFactory,
    TextPropertyHandler,
    NumberPropertyHandler,
    SelectPropertyHandler,
    MultiSelectPropertyHandler,
    DatePropertyHandler,
    CheckboxPropertyHandler,
    URLPropertyHandler,
    EmailPropertyHandler,
    PhonePropertyHandler,
    RelationPropertyHandler,
)


class TestTextPropertyHandler:
    """Test text and title property handlers."""

    def test_title_handler(self):
        """Test title property handler."""
        handler = TextPropertyHandler(is_title=True)

        # Validate
        assert handler.validate("Test Title") is True
        assert handler.validate("") is True
        assert handler.validate(123) is False

        # Format for API
        formatted = handler.format_for_api("Test Title")
        assert formatted == {"title": [{"text": {"content": "Test Title"}}]}

        # Parse from API
        api_value = {"title": [{"text": {"content": "Test Title"}}]}
        assert handler.parse_from_api(api_value) == "Test Title"

    def test_rich_text_handler(self):
        """Test rich text property handler."""
        handler = TextPropertyHandler(is_title=False)

        # Format for API
        formatted = handler.format_for_api("Test content")
        assert formatted == {"rich_text": [{"text": {"content": "Test content"}}]}

        # Parse from API
        api_value = {"rich_text": [{"text": {"content": "Test content"}}]}
        assert handler.parse_from_api(api_value) == "Test content"

    def test_text_length_limit(self):
        """Test text length limiting."""
        handler = TextPropertyHandler(max_length=10)

        assert handler.validate("Short") is True
        assert handler.validate("This is too long") is False

        # Should truncate when formatting
        formatted = handler.format_for_api("This is too long")
        assert formatted["rich_text"][0]["text"]["content"] == "This is to"


class TestNumberPropertyHandler:
    """Test number property handler."""

    def test_number_validation(self):
        """Test number validation."""
        handler = NumberPropertyHandler()

        assert handler.validate(42) is True
        assert handler.validate(3.14) is True
        assert handler.validate("123") is True  # Can be converted
        assert handler.validate("not a number") is False
        assert handler.validate(None) is False

    def test_number_formatting(self):
        """Test number formatting."""
        handler = NumberPropertyHandler()

        assert handler.format_for_api(42) == {"number": 42.0}
        assert handler.format_for_api("3.14") == {"number": 3.14}

    def test_number_parsing(self):
        """Test number parsing."""
        handler = NumberPropertyHandler()

        assert handler.parse_from_api({"number": 42.0}) == 42.0
        assert handler.parse_from_api({"number": None}) is None
        assert handler.parse_from_api({}) is None


class TestSelectPropertyHandler:
    """Test select property handler."""

    def test_select_validation(self):
        """Test select validation."""
        handler = SelectPropertyHandler(options=["Option1", "Option2"])

        assert handler.validate("Option1") is True
        assert handler.validate("Option2") is True
        assert handler.validate("Option3") is False

        # Without options, any string is valid
        handler_no_options = SelectPropertyHandler()
        assert handler_no_options.validate("Anything") is True

    def test_select_formatting(self):
        """Test select formatting."""
        handler = SelectPropertyHandler()

        formatted = handler.format_for_api("Active")
        assert formatted == {"select": {"name": "Active"}}

    def test_select_parsing(self):
        """Test select parsing."""
        handler = SelectPropertyHandler()

        api_value = {"select": {"name": "Active", "color": "green"}}
        assert handler.parse_from_api(api_value) == "Active"

        assert handler.parse_from_api({"select": None}) is None


class TestMultiSelectPropertyHandler:
    """Test multi-select property handler."""

    def test_multi_select_validation(self):
        """Test multi-select validation."""
        handler = MultiSelectPropertyHandler()

        assert handler.validate(["Tag1", "Tag2"]) is True
        assert handler.validate([]) is True
        assert handler.validate("single") is False
        assert handler.validate([1, 2, 3]) is False

    def test_multi_select_formatting(self):
        """Test multi-select formatting."""
        handler = MultiSelectPropertyHandler()

        # List input
        formatted = handler.format_for_api(["Tag1", "Tag2"])
        assert formatted == {"multi_select": [{"name": "Tag1"}, {"name": "Tag2"}]}

        # Single string converted to list
        formatted_single = handler.format_for_api("Tag1")
        assert formatted_single == {"multi_select": [{"name": "Tag1"}]}

    def test_multi_select_parsing(self):
        """Test multi-select parsing."""
        handler = MultiSelectPropertyHandler()

        api_value = {
            "multi_select": [
                {"name": "Tag1", "color": "red"},
                {"name": "Tag2", "color": "blue"},
            ]
        }
        assert handler.parse_from_api(api_value) == ["Tag1", "Tag2"]


class TestDatePropertyHandler:
    """Test date property handler."""

    def test_date_validation(self):
        """Test date validation."""
        handler = DatePropertyHandler()

        assert handler.validate(datetime.now()) is True
        assert handler.validate(date.today()) is True
        assert handler.validate("2025-01-09") is True
        assert handler.validate("2025-01-09T14:00:00") is True
        assert handler.validate("invalid date") is False

    def test_date_formatting(self):
        """Test date formatting."""
        handler = DatePropertyHandler()

        # String input
        formatted = handler.format_for_api("2025-01-09")
        assert formatted == {"date": {"start": "2025-01-09"}}

        # Datetime input
        dt = datetime(2025, 1, 9, 14, 0, 0)
        formatted_dt = handler.format_for_api(dt)
        assert formatted_dt == {"date": {"start": dt.isoformat()}}

    def test_date_parsing(self):
        """Test date parsing."""
        handler = DatePropertyHandler()

        api_value = {"date": {"start": "2025-01-09", "end": None}}
        assert handler.parse_from_api(api_value) == "2025-01-09"


class TestCheckboxPropertyHandler:
    """Test checkbox property handler."""

    def test_checkbox_validation(self):
        """Test checkbox validation."""
        handler = CheckboxPropertyHandler()

        assert handler.validate(True) is True
        assert handler.validate(False) is True
        assert handler.validate("true") is False
        assert handler.validate(1) is False

    def test_checkbox_formatting(self):
        """Test checkbox formatting."""
        handler = CheckboxPropertyHandler()

        assert handler.format_for_api(True) == {"checkbox": True}
        assert handler.format_for_api(False) == {"checkbox": False}


class TestURLPropertyHandler:
    """Test URL property handler."""

    def test_url_validation(self):
        """Test URL validation."""
        handler = URLPropertyHandler()

        assert handler.validate("https://example.com") is True
        assert handler.validate("http://localhost:8080") is True
        assert handler.validate("https://example.com/path?query=value") is True
        assert handler.validate("not a url") is False
        assert handler.validate("ftp://example.com") is False  # Only http/https

    def test_url_formatting(self):
        """Test URL formatting."""
        handler = URLPropertyHandler()

        formatted = handler.format_for_api("https://example.com")
        assert formatted == {"url": "https://example.com"}


class TestEmailPropertyHandler:
    """Test email property handler."""

    def test_email_validation(self):
        """Test email validation."""
        handler = EmailPropertyHandler()

        assert handler.validate("user@example.com") is True
        assert handler.validate("user.name+tag@example.co.uk") is True
        assert handler.validate("invalid.email") is False
        assert handler.validate("@example.com") is False
        assert handler.validate("user@") is False

    def test_email_formatting(self):
        """Test email formatting."""
        handler = EmailPropertyHandler()

        formatted = handler.format_for_api("user@example.com")
        assert formatted == {"email": "user@example.com"}


class TestPhonePropertyHandler:
    """Test phone property handler."""

    def test_phone_validation(self):
        """Test phone validation."""
        handler = PhonePropertyHandler()

        assert handler.validate("+1-555-123-4567") is True
        assert handler.validate("555-123-4567") is True
        assert handler.validate("5551234567") is True
        assert handler.validate("no digits here") is False

    def test_phone_formatting(self):
        """Test phone formatting."""
        handler = PhonePropertyHandler()

        formatted = handler.format_for_api("+1-555-123-4567")
        assert formatted == {"phone_number": "+1-555-123-4567"}


class TestRelationPropertyHandler:
    """Test relation property handler."""

    def test_relation_validation(self):
        """Test relation validation."""
        handler = RelationPropertyHandler()

        assert handler.validate("page-id-123") is True
        assert handler.validate(["id1", "id2"]) is True
        assert handler.validate([]) is True
        assert handler.validate(123) is False

    def test_relation_formatting(self):
        """Test relation formatting."""
        handler = RelationPropertyHandler()

        # Single ID
        formatted = handler.format_for_api("page-id-123")
        assert formatted == {"relation": [{"id": "page-id-123"}]}

        # Multiple IDs
        formatted_multi = handler.format_for_api(["id1", "id2"])
        assert formatted_multi == {"relation": [{"id": "id1"}, {"id": "id2"}]}

    def test_relation_parsing(self):
        """Test relation parsing."""
        handler = RelationPropertyHandler()

        api_value = {"relation": [{"id": "id1"}, {"id": "id2"}]}
        assert handler.parse_from_api(api_value) == ["id1", "id2"]


class TestPropertyHandlerFactory:
    """Test property handler factory."""

    def test_create_handlers(self):
        """Test creating handlers by type."""
        # Title
        handler = PropertyHandlerFactory.create("title")
        assert isinstance(handler, TextPropertyHandler)
        assert handler.is_title is True

        # Number
        handler = PropertyHandlerFactory.create("number")
        assert isinstance(handler, NumberPropertyHandler)

        # Select with options
        handler = PropertyHandlerFactory.create("select", options=["A", "B"])
        assert isinstance(handler, SelectPropertyHandler)
        assert handler.options == ["A", "B"]

    def test_unsupported_type(self):
        """Test creating unsupported handler type."""
        with pytest.raises(ValueError, match="Unsupported property type"):
            PropertyHandlerFactory.create("unsupported_type")

    def test_all_supported_types(self):
        """Test all supported property types can be created."""
        supported_types = [
            "title",
            "rich_text",
            "number",
            "select",
            "multi_select",
            "date",
            "checkbox",
            "url",
            "email",
            "phone_number",
            "people",
            "files",
            "relation",
            "formula",
            "rollup",
            "created_time",
            "last_edited_time",
        ]

        for prop_type in supported_types:
            handler = PropertyHandlerFactory.create(prop_type)
            assert isinstance(handler, PropertyHandler)
