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

        assert "Invalid property type" in str(exc_info.value)


class TestTitleHandler:
    """Test title property handler."""

    @pytest.fixture
    def handler(self):
        return TitleHandler()

    def test_validate_string(self, handler):
        """Test validation of string values."""
        assert handler.validate("Test Title") is True
        assert handler.validate("") is True
        assert handler.validate(None) is True

    def test_validate_string_too_long(self, handler):
        """Test validation rejects strings that are too long."""
        long_string = "a" * 2001

        with pytest.raises(ValidationError) as exc_info:
            handler.validate(long_string)

        assert "too long" in str(exc_info.value)
        assert exc_info.value.field == "title"

    def test_validate_list(self, handler):
        """Test validation of rich text element lists."""
        rich_text = [{"type": "text", "text": {"content": "Hello"}}]
        assert handler.validate(rich_text) is True

    def test_validate_invalid_type(self, handler):
        """Test validation rejects invalid types."""
        with pytest.raises(ValidationError) as exc_info:
            handler.validate(123)

        assert "must be string or list" in str(exc_info.value)

    def test_normalize_string(self, handler):
        """Test normalization of string to rich text elements."""
        normalized = handler.normalize("Test Title")

        assert len(normalized) == 1
        assert normalized[0].type == "text"
        assert normalized[0].text["content"] == "Test Title"
        assert normalized[0].plain_text == "Test Title"

    def test_normalize_empty(self, handler):
        """Test normalization of empty values."""
        assert handler.normalize(None) == []
        assert handler.normalize("") == []

    def test_format_for_api(self, handler):
        """Test formatting for API submission."""
        formatted = handler.format_for_api("Test Title")

        assert formatted["type"] == "title"
        assert len(formatted["title"]) == 1
        assert formatted["title"][0]["type"] == "text"
        assert formatted["title"][0]["text"]["content"] == "Test Title"

    def test_parse_from_api(self, handler):
        """Test parsing from API response."""
        api_data = {
            "id": "title",
            "type": "title",
            "title": [
                {"type": "text", "text": {"content": "Test Title"}, "plain_text": "Test Title"}
            ],
        }

        parsed = handler.parse(api_data)
        assert isinstance(parsed, TitleProperty)
        assert parsed.to_plain_text() == "Test Title"

    def test_extract_plain_value(self, handler):
        """Test extracting plain text value."""
        prop = TitleProperty.from_text("Test Title")
        plain = handler.extract_plain_value(prop)
        assert plain == "Test Title"


class TestNumberHandler:
    """Test number property handler."""

    @pytest.fixture
    def handler(self):
        return NumberHandler()

    def test_validate_numbers(self, handler):
        """Test validation of numeric values."""
        assert handler.validate(42) is True
        assert handler.validate(3.14) is True
        assert handler.validate(0) is True
        assert handler.validate(-10.5) is True
        assert handler.validate(None) is True

    def test_validate_numeric_string(self, handler):
        """Test validation of numeric strings."""
        assert handler.validate("123") is True
        assert handler.validate("3.14") is True
        assert handler.validate("-42") is True

    def test_validate_invalid_string(self, handler):
        """Test validation rejects non-numeric strings."""
        with pytest.raises(ValidationError) as exc_info:
            handler.validate("not a number")

        assert "Cannot parse" in str(exc_info.value)

    def test_validate_special_floats(self, handler):
        """Test validation rejects NaN and infinity."""
        with pytest.raises(ValidationError) as exc_info:
            handler.validate(float("nan"))
        assert "cannot be NaN" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            handler.validate(float("inf"))
        assert "cannot be infinity" in str(exc_info.value)

    def test_normalize_numbers(self, handler):
        """Test normalization of numbers."""
        assert handler.normalize(42) == 42.0
        assert handler.normalize(3.14) == 3.14
        assert handler.normalize("123") == 123.0
        assert handler.normalize("1,234.56") == 1234.56
        assert handler.normalize(None) is None
        assert handler.normalize("") is None

    def test_format_for_api(self, handler):
        """Test formatting for API submission."""
        formatted = handler.format_for_api(42)

        assert formatted["type"] == "number"
        assert formatted["number"] == 42.0


class TestSelectHandler:
    """Test select property handler."""

    @pytest.fixture
    def handler(self):
        return SelectHandler()

    def test_validate_string(self, handler):
        """Test validation of string values."""
        assert handler.validate("Option 1") is True
        assert handler.validate(None) is True

    def test_validate_dict(self, handler):
        """Test validation of option dictionaries."""
        option = {"name": "Option 1", "color": "blue"}
        assert handler.validate(option) is True

    def test_validate_long_name(self, handler):
        """Test validation rejects names that are too long."""
        long_name = "a" * 101

        with pytest.raises(ValidationError) as exc_info:
            handler.validate(long_name)

        assert "too long" in str(exc_info.value)

    def test_normalize_string(self, handler):
        """Test normalization of string to option."""
        normalized = handler.normalize("Option 1")

        assert normalized.name == "Option 1"
        assert normalized.color is None

    def test_format_for_api(self, handler):
        """Test formatting for API submission."""
        formatted = handler.format_for_api("Option 1")

        assert formatted["type"] == "select"
        assert formatted["select"]["name"] == "Option 1"


class TestMultiSelectHandler:
    """Test multi-select property handler."""

    @pytest.fixture
    def handler(self):
        return MultiSelectHandler()

    def test_validate_string(self, handler):
        """Test validation of single string value."""
        assert handler.validate("Option 1") is True

    def test_validate_list(self, handler):
        """Test validation of option lists."""
        options = ["Option 1", "Option 2", "Option 3"]
        assert handler.validate(options) is True

    def test_validate_mixed_list(self, handler):
        """Test validation of mixed string/dict lists."""
        options = ["Option 1", {"name": "Option 2", "color": "red"}]
        assert handler.validate(options) is True

    def test_normalize_string(self, handler):
        """Test normalization of single string."""
        normalized = handler.normalize("Option 1")

        assert len(normalized) == 1
        assert normalized[0].name == "Option 1"

    def test_normalize_list(self, handler):
        """Test normalization of option list."""
        normalized = handler.normalize(["Option 1", "Option 2"])

        assert len(normalized) == 2
        assert normalized[0].name == "Option 1"
        assert normalized[1].name == "Option 2"

    def test_format_for_api(self, handler):
        """Test formatting for API submission."""
        formatted = handler.format_for_api(["Option 1", "Option 2"])

        assert formatted["type"] == "multi_select"
        assert len(formatted["multi_select"]) == 2
        assert formatted["multi_select"][0]["name"] == "Option 1"


class TestDateHandler:
    """Test date property handler."""

    @pytest.fixture
    def handler(self):
        return DateHandler()

    def test_validate_date_types(self, handler):
        """Test validation of date types."""
        assert handler.validate("2024-01-01") is True
        assert handler.validate(date(2024, 1, 1)) is True
        assert handler.validate(datetime(2024, 1, 1, 12, 0)) is True
        assert handler.validate(None) is True

    def test_validate_date_dict(self, handler):
        """Test validation of date dictionaries."""
        date_dict = {"start": "2024-01-01", "end": "2024-01-31"}
        assert handler.validate(date_dict) is True

    def test_validate_missing_start(self, handler):
        """Test validation rejects dates without start."""
        with pytest.raises(ValidationError) as exc_info:
            handler.validate({"end": "2024-01-31"})

        assert "must have 'start'" in str(exc_info.value)

    def test_normalize_string(self, handler):
        """Test normalization of date string."""
        normalized = handler.normalize("2024-01-01")

        assert normalized.start == "2024-01-01"
        assert normalized.end is None

    def test_normalize_date_object(self, handler):
        """Test normalization of date object."""
        normalized = handler.normalize(date(2024, 1, 1))

        assert normalized.start == "2024-01-01"

    def test_format_for_api(self, handler):
        """Test formatting for API submission."""
        formatted = handler.format_for_api("2024-01-01")

        assert formatted["type"] == "date"
        assert formatted["date"]["start"] == "2024-01-01"


class TestPeopleHandler:
    """Test people property handler."""

    @pytest.fixture
    def handler(self):
        return PeopleHandler()

    def test_validate_string(self, handler):
        """Test validation of user ID string."""
        assert handler.validate("user-123") is True

    def test_validate_list(self, handler):
        """Test validation of user ID list."""
        assert handler.validate(["user-1", "user-2"]) is True

    def test_validate_user_objects(self, handler):
        """Test validation of user object list."""
        users = [{"object": "user", "id": "user-1"}, {"object": "user", "id": "user-2"}]
        assert handler.validate(users) is True

    def test_normalize_string(self, handler):
        """Test normalization of single user ID."""
        normalized = handler.normalize("user-123")

        assert len(normalized) == 1
        assert normalized[0]["object"] == "user"
        assert normalized[0]["id"] == "user-123"

    def test_normalize_list(self, handler):
        """Test normalization of user ID list."""
        normalized = handler.normalize(["user-1", "user-2"])

        assert len(normalized) == 2
        assert all(u["object"] == "user" for u in normalized)
        assert normalized[0]["id"] == "user-1"
        assert normalized[1]["id"] == "user-2"

    def test_format_for_api(self, handler):
        """Test formatting for API submission."""
        formatted = handler.format_for_api(["user-1", "user-2"])

        assert formatted["type"] == "people"
        assert len(formatted["people"]) == 2
        assert formatted["people"][0]["id"] == "user-1"
