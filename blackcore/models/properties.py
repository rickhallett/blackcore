"""Pydantic models for Notion property types."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class PropertyType(str, Enum):
    """Notion property types."""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"
    STATUS = "status"


class RichTextElement(BaseModel):
    """Rich text element."""

    type: str = "text"
    text: Dict[str, str] = Field(default_factory=lambda: {"content": ""})
    plain_text: Optional[str] = ""
    href: Optional[str] = None
    annotations: Optional[Dict[str, Union[bool, str]]] = None


class SelectOption(BaseModel):
    """Select/Status option."""

    id: Optional[str] = None
    name: str
    color: Optional[str] = None


class DateValue(BaseModel):
    """Date property value."""

    start: Union[str, date, datetime]
    end: Optional[Union[str, date, datetime]] = None
    time_zone: Optional[str] = None

    @field_validator("start", "end", mode="before")
    def parse_date(cls, v):
        """Parse date strings."""
        if isinstance(v, str):
            return v  # Keep as string for API
        elif isinstance(v, datetime):
            return v.isoformat()
        elif isinstance(v, date):
            return v.isoformat()
        return v


class FormulaValue(BaseModel):
    """Formula result value."""

    type: str  # "string", "number", "boolean", "date"
    string: Optional[str] = None
    number: Optional[float] = None
    boolean: Optional[bool] = None
    date: Optional[DateValue] = None


class RollupValue(BaseModel):
    """Rollup result value."""

    type: str  # "number", "date", "array"
    number: Optional[float] = None
    date: Optional[DateValue] = None
    array: Optional[List[Any]] = None
    function: str  # Rollup function used


# Base property value models
class BasePropertyValue(BaseModel):
    """Base class for property values."""

    id: Optional[str] = None
    type: PropertyType

    class Config:
        use_enum_values = True


class TitleProperty(BasePropertyValue):
    """Title property value."""

    type: PropertyType = PropertyType.TITLE
    title: List[RichTextElement] = Field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "TitleProperty":
        """Create from plain text."""
        return cls(title=[RichTextElement(type="text", text={"content": text}, plain_text=text)])

    def to_plain_text(self) -> str:
        """Convert to plain text."""
        return "".join(elem.plain_text or elem.text.get("content", "") for elem in self.title)


class RichTextProperty(BasePropertyValue):
    """Rich text property value."""

    type: PropertyType = PropertyType.RICH_TEXT
    rich_text: List[RichTextElement] = Field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "RichTextProperty":
        """Create from plain text."""
        return cls(
            rich_text=[RichTextElement(type="text", text={"content": text}, plain_text=text)]
        )

    def to_plain_text(self) -> str:
        """Convert to plain text."""
        return "".join(elem.plain_text or elem.text.get("content", "") for elem in self.rich_text)


class NumberProperty(BasePropertyValue):
    """Number property value."""

    type: PropertyType = PropertyType.NUMBER
    number: Optional[float] = None


class SelectProperty(BasePropertyValue):
    """Select property value."""

    type: PropertyType = PropertyType.SELECT
    select: Optional[SelectOption] = None

    @classmethod
    def from_name(cls, name: str, color: Optional[str] = None) -> "SelectProperty":
        """Create from option name."""
        return cls(select=SelectOption(name=name, color=color))


class MultiSelectProperty(BasePropertyValue):
    """Multi-select property value."""

    type: PropertyType = PropertyType.MULTI_SELECT
    multi_select: List[SelectOption] = Field(default_factory=list)

    @classmethod
    def from_names(cls, names: List[str]) -> "MultiSelectProperty":
        """Create from option names."""
        return cls(multi_select=[SelectOption(name=name) for name in names])


class StatusProperty(BasePropertyValue):
    """Status property value."""

    type: PropertyType = PropertyType.STATUS
    status: Optional[SelectOption] = None

    @classmethod
    def from_name(cls, name: str, color: Optional[str] = None) -> "StatusProperty":
        """Create from status name."""
        return cls(status=SelectOption(name=name, color=color))


class DateProperty(BasePropertyValue):
    """Date property value."""

    type: PropertyType = PropertyType.DATE
    date: Optional[DateValue] = None

    @classmethod
    def from_date(
        cls, start: Union[str, date, datetime], end: Optional[Union[str, date, datetime]] = None
    ) -> "DateProperty":
        """Create from date values."""
        return cls(date=DateValue(start=start, end=end))


class PeopleProperty(BasePropertyValue):
    """People property value."""

    type: PropertyType = PropertyType.PEOPLE
    people: List[Dict[str, str]] = Field(default_factory=list)

    @classmethod
    def from_ids(cls, user_ids: List[str]) -> "PeopleProperty":
        """Create from user IDs."""
        return cls(people=[{"object": "user", "id": uid} for uid in user_ids])


class FilesProperty(BasePropertyValue):
    """Files property value."""

    type: PropertyType = PropertyType.FILES
    files: List[Dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_urls(cls, urls: List[str], names: Optional[List[str]] = None) -> "FilesProperty":
        """Create from external URLs."""
        files = []
        for i, url in enumerate(urls):
            file_obj = {
                "type": "external",
                "name": names[i] if names and i < len(names) else f"File {i + 1}",
                "external": {"url": url},
            }
            files.append(file_obj)
        return cls(files=files)


class CheckboxProperty(BasePropertyValue):
    """Checkbox property value."""

    type: PropertyType = PropertyType.CHECKBOX
    checkbox: bool = False


class URLProperty(BasePropertyValue):
    """URL property value."""

    type: PropertyType = PropertyType.URL
    url: Optional[str] = None


class EmailProperty(BasePropertyValue):
    """Email property value."""

    type: PropertyType = PropertyType.EMAIL
    email: Optional[str] = None

    @field_validator("email")
    def validate_email(cls, v):
        """Basic email validation."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class PhoneProperty(BasePropertyValue):
    """Phone number property value."""

    type: PropertyType = PropertyType.PHONE_NUMBER
    phone_number: Optional[str] = None


class FormulaProperty(BasePropertyValue):
    """Formula property value (read-only)."""

    type: PropertyType = PropertyType.FORMULA
    formula: Optional[FormulaValue] = None


class RelationProperty(BasePropertyValue):
    """Relation property value."""

    type: PropertyType = PropertyType.RELATION
    relation: List[Dict[str, str]] = Field(default_factory=list)
    has_more: Optional[bool] = False

    @classmethod
    def from_page_ids(cls, page_ids: List[str]) -> "RelationProperty":
        """Create from related page IDs."""
        return cls(relation=[{"id": page_id} for page_id in page_ids])


class RollupProperty(BasePropertyValue):
    """Rollup property value (read-only)."""

    type: PropertyType = PropertyType.ROLLUP
    rollup: Optional[RollupValue] = None


class CreatedTimeProperty(BasePropertyValue):
    """Created time property value (read-only)."""

    type: PropertyType = PropertyType.CREATED_TIME
    created_time: datetime


class CreatedByProperty(BasePropertyValue):
    """Created by property value (read-only)."""

    type: PropertyType = PropertyType.CREATED_BY
    created_by: Dict[str, Any]


class LastEditedTimeProperty(BasePropertyValue):
    """Last edited time property value (read-only)."""

    type: PropertyType = PropertyType.LAST_EDITED_TIME
    last_edited_time: datetime


class LastEditedByProperty(BasePropertyValue):
    """Last edited by property value (read-only)."""

    type: PropertyType = PropertyType.LAST_EDITED_BY
    last_edited_by: Dict[str, Any]


# Property value factory
def create_property_value(property_type: PropertyType, value: Any) -> BasePropertyValue:
    """Create a property value from type and raw value.

    Args:
        property_type: The property type
        value: The raw value

    Returns:
        Appropriate property value instance
    """
    if property_type == PropertyType.TITLE:
        if isinstance(value, str):
            return TitleProperty.from_text(value)
        elif isinstance(value, list):
            return TitleProperty(title=value)
        else:
            return TitleProperty(title=[])

    elif property_type == PropertyType.RICH_TEXT:
        if isinstance(value, str):
            return RichTextProperty.from_text(value)
        elif isinstance(value, list):
            return RichTextProperty(rich_text=value)
        else:
            return RichTextProperty(rich_text=[])

    elif property_type == PropertyType.NUMBER:
        return NumberProperty(number=value)

    elif property_type == PropertyType.SELECT:
        if isinstance(value, str):
            return SelectProperty.from_name(value)
        elif isinstance(value, dict):
            return SelectProperty(select=SelectOption(**value))
        else:
            return SelectProperty(select=None)

    elif property_type == PropertyType.MULTI_SELECT:
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return MultiSelectProperty.from_names(value)
        elif isinstance(value, list):
            return MultiSelectProperty(multi_select=[SelectOption(**v) for v in value])
        else:
            return MultiSelectProperty(multi_select=[])

    elif property_type == PropertyType.DATE:
        if isinstance(value, (str, date, datetime)):
            return DateProperty.from_date(value)
        elif isinstance(value, dict):
            return DateProperty(date=DateValue(**value))
        else:
            return DateProperty(date=None)

    elif property_type == PropertyType.PEOPLE:
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return PeopleProperty.from_ids(value)
        elif isinstance(value, list):
            return PeopleProperty(people=value)
        else:
            return PeopleProperty(people=[])

    elif property_type == PropertyType.FILES:
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return FilesProperty.from_urls(value)
        elif isinstance(value, list):
            return FilesProperty(files=value)
        else:
            return FilesProperty(files=[])

    elif property_type == PropertyType.CHECKBOX:
        return CheckboxProperty(checkbox=bool(value))

    elif property_type == PropertyType.URL:
        return URLProperty(url=str(value) if value else None)

    elif property_type == PropertyType.EMAIL:
        return EmailProperty(email=str(value) if value else None)

    elif property_type == PropertyType.PHONE_NUMBER:
        return PhoneProperty(phone_number=str(value) if value else None)

    elif property_type == PropertyType.RELATION:
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return RelationProperty.from_page_ids(value)
        elif isinstance(value, list):
            return RelationProperty(relation=value)
        else:
            return RelationProperty(relation=[])

    else:
        # For read-only properties, return a basic property value
        return BasePropertyValue(type=property_type)


def parse_property_value(property_data: Dict[str, Any]) -> Optional[BasePropertyValue]:
    """Parse a property value from API response.

    Args:
        property_data: Raw property data from API

    Returns:
        Parsed property value or None
    """
    if not property_data or "type" not in property_data:
        return None

    try:
        prop_type = PropertyType(property_data["type"])

        # Extract the actual value based on type
        if prop_type == PropertyType.TITLE:
            return TitleProperty(**property_data)
        elif prop_type == PropertyType.RICH_TEXT:
            return RichTextProperty(**property_data)
        elif prop_type == PropertyType.NUMBER:
            return NumberProperty(**property_data)
        elif prop_type == PropertyType.SELECT:
            return SelectProperty(**property_data)
        elif prop_type == PropertyType.MULTI_SELECT:
            return MultiSelectProperty(**property_data)
        elif prop_type == PropertyType.DATE:
            return DateProperty(**property_data)
        elif prop_type == PropertyType.PEOPLE:
            return PeopleProperty(**property_data)
        elif prop_type == PropertyType.FILES:
            return FilesProperty(**property_data)
        elif prop_type == PropertyType.CHECKBOX:
            return CheckboxProperty(**property_data)
        elif prop_type == PropertyType.URL:
            return URLProperty(**property_data)
        elif prop_type == PropertyType.EMAIL:
            return EmailProperty(**property_data)
        elif prop_type == PropertyType.PHONE_NUMBER:
            return PhoneProperty(**property_data)
        elif prop_type == PropertyType.FORMULA:
            return FormulaProperty(**property_data)
        elif prop_type == PropertyType.RELATION:
            return RelationProperty(**property_data)
        elif prop_type == PropertyType.ROLLUP:
            return RollupProperty(**property_data)
        elif prop_type == PropertyType.CREATED_TIME:
            return CreatedTimeProperty(**property_data)
        elif prop_type == PropertyType.CREATED_BY:
            return CreatedByProperty(**property_data)
        elif prop_type == PropertyType.LAST_EDITED_TIME:
            return LastEditedTimeProperty(**property_data)
        elif prop_type == PropertyType.LAST_EDITED_BY:
            return LastEditedByProperty(**property_data)
        elif prop_type == PropertyType.STATUS:
            return StatusProperty(**property_data)
        else:
            return None

    except Exception:
        return None
