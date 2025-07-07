"""Pydantic models for Notion property types."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from enum import Enum


class PropertyType(str, Enum):
    """Notion property types."""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    URL = "url"
    FILES = "files"
    RELATION = "relation"
    NUMBER = "number"
    CHECKBOX = "checkbox"


class SelectOption(BaseModel):
    """Select or multi-select option."""

    name: str
    color: Optional[str] = "default"


class RelationConfig(BaseModel):
    """Relation property configuration."""

    database_id: str
    type: str = "dual_property"
    dual_property_name: Optional[str] = None


class PropertySchema(BaseModel):
    """Base property schema."""

    name: str
    type: PropertyType

    def to_notion(self) -> Dict[str, Any]:
        """Convert to Notion API format."""
        return {"type": self.type.value}


class TitleProperty(PropertySchema):
    """Title property schema."""

    type: PropertyType = PropertyType.TITLE

    def to_notion(self) -> Dict[str, Any]:
        return {"title": {}}


class RichTextProperty(PropertySchema):
    """Rich text property schema."""

    type: PropertyType = PropertyType.RICH_TEXT

    def to_notion(self) -> Dict[str, Any]:
        return {"rich_text": {}}


class SelectProperty(PropertySchema):
    """Select property schema."""

    type: PropertyType = PropertyType.SELECT
    options: List[SelectOption]

    def to_notion(self) -> Dict[str, Any]:
        return {
            "select": {"options": [{"name": opt.name, "color": opt.color} for opt in self.options]}
        }


class MultiSelectProperty(PropertySchema):
    """Multi-select property schema."""

    type: PropertyType = PropertyType.MULTI_SELECT
    options: List[SelectOption]

    def to_notion(self) -> Dict[str, Any]:
        return {
            "multi_select": {
                "options": [{"name": opt.name, "color": opt.color} for opt in self.options]
            }
        }


class DateProperty(PropertySchema):
    """Date property schema."""

    type: PropertyType = PropertyType.DATE

    def to_notion(self) -> Dict[str, Any]:
        return {"date": {}}


class PeopleProperty(PropertySchema):
    """People property schema."""

    type: PropertyType = PropertyType.PEOPLE

    def to_notion(self) -> Dict[str, Any]:
        return {"people": {}}


class EmailProperty(PropertySchema):
    """Email property schema."""

    type: PropertyType = PropertyType.EMAIL

    def to_notion(self) -> Dict[str, Any]:
        return {"email": {}}


class PhoneProperty(PropertySchema):
    """Phone number property schema."""

    type: PropertyType = PropertyType.PHONE_NUMBER

    def to_notion(self) -> Dict[str, Any]:
        return {"phone_number": {}}


class URLProperty(PropertySchema):
    """URL property schema."""

    type: PropertyType = PropertyType.URL

    def to_notion(self) -> Dict[str, Any]:
        return {"url": {}}


class FilesProperty(PropertySchema):
    """Files property schema."""

    type: PropertyType = PropertyType.FILES

    def to_notion(self) -> Dict[str, Any]:
        return {"files": {}}


class RelationProperty(PropertySchema):
    """Relation property schema."""

    type: PropertyType = PropertyType.RELATION
    config: Optional[RelationConfig] = None

    def to_notion(self) -> Dict[str, Any]:
        if not self.config:
            # Return placeholder for initial creation
            return {"relation": {"database_id": "placeholder", "type": "dual_property"}}

        relation_data = {"database_id": self.config.database_id}
        
        # For dual_property type, we need to include the dual_property configuration
        if self.config.type == "dual_property":
            if self.config.dual_property_name:
                relation_data["dual_property"] = {
                    "synced_property_name": self.config.dual_property_name
                }
            else:
                # Auto-generate a synced property name if not provided
                relation_data["dual_property"] = {}
        elif self.config.type == "single_property":
            relation_data["single_property"] = {}
        else:
            # Default to dual_property with empty config
            relation_data["dual_property"] = {}

        return {"relation": relation_data}


PropertyUnion = Union[
    TitleProperty,
    RichTextProperty,
    SelectProperty,
    MultiSelectProperty,
    DateProperty,
    PeopleProperty,
    EmailProperty,
    PhoneProperty,
    URLProperty,
    FilesProperty,
    RelationProperty,
]


class DatabaseSchema(BaseModel):
    """Database schema with properties."""

    name: str
    properties: List[PropertyUnion]
    icon: Optional[Dict[str, str]] = None
    cover: Optional[Dict[str, str]] = None

    def to_notion_properties(self) -> Dict[str, Any]:
        """Convert properties to Notion API format."""
        notion_properties = {}

        for prop in self.properties:
            notion_properties[prop.name] = prop.to_notion()

        return notion_properties
