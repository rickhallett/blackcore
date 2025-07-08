"""Handlers for text-based properties (title, rich_text)."""

from typing import Any, Dict, List, Union
from ..models.properties import (
    PropertyType,
    TitleProperty,
    RichTextProperty,
    RichTextElement,
)
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class TitleHandler(PropertyHandler):
    """Handler for title properties."""
    
    property_type = PropertyType.TITLE
    
    def validate(self, value: Any) -> bool:
        """Validate title value."""
        if value is None:
            return True
        
        if isinstance(value, str):
            if len(value) > 2000:
                raise ValidationError(
                    "Title too long (max 2000 characters)",
                    field="title",
                    value=value[:50] + "..."
                )
            return True
        
        if isinstance(value, list):
            # List of rich text elements
            total_length = 0
            for element in value:
                if not isinstance(element, dict):
                    raise ValidationError(
                        "Title elements must be dictionaries",
                        field="title"
                    )
                if "text" in element and "content" in element["text"]:
                    total_length += len(element["text"]["content"])
            
            if total_length > 2000:
                raise ValidationError(
                    "Title too long (max 2000 characters)",
                    field="title"
                )
            return True
        
        raise ValidationError(
            f"Title must be string or list, got {type(value).__name__}",
            field="title",
            value=value
        )
    
    def normalize(self, value: Any) -> List[RichTextElement]:
        """Normalize title value."""
        if value is None or value == "":
            return []
        
        if isinstance(value, str):
            return [RichTextElement(
                type="text",
                text={"content": value},
                plain_text=value
            )]
        
        if isinstance(value, list):
            normalized = []
            for element in value:
                if isinstance(element, RichTextElement):
                    normalized.append(element)
                elif isinstance(element, dict):
                    normalized.append(RichTextElement(**element))
                else:
                    # Convert to string
                    text = str(element)
                    normalized.append(RichTextElement(
                        type="text",
                        text={"content": text},
                        plain_text=text
                    ))
            return normalized
        
        # Convert any other type to string
        text = str(value)
        return [RichTextElement(
            type="text",
            text={"content": text},
            plain_text=text
        )]
    
    def parse(self, api_value: Dict[str, Any]) -> TitleProperty:
        """Parse title from API response."""
        return TitleProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format title for API submission."""
        normalized = self.normalize(value)
        
        return {
            "type": "title",
            "title": [elem.model_dump(exclude_none=True) for elem in normalized]
        }
    
    def extract_plain_value(self, property_value: TitleProperty) -> str:
        """Extract plain text from title property."""
        return property_value.to_plain_text()


class RichTextHandler(PropertyHandler):
    """Handler for rich text properties."""
    
    property_type = PropertyType.RICH_TEXT
    
    def validate(self, value: Any) -> bool:
        """Validate rich text value."""
        if value is None:
            return True
        
        if isinstance(value, str):
            if len(value) > 2000:
                raise ValidationError(
                    "Rich text too long (max 2000 characters)",
                    field="rich_text",
                    value=value[:50] + "..."
                )
            return True
        
        if isinstance(value, list):
            # List of rich text elements
            total_length = 0
            for element in value:
                if not isinstance(element, dict):
                    raise ValidationError(
                        "Rich text elements must be dictionaries",
                        field="rich_text"
                    )
                if "text" in element and "content" in element["text"]:
                    total_length += len(element["text"]["content"])
            
            if total_length > 2000:
                raise ValidationError(
                    "Rich text too long (max 2000 characters)",
                    field="rich_text"
                )
            return True
        
        raise ValidationError(
            f"Rich text must be string or list, got {type(value).__name__}",
            field="rich_text",
            value=value
        )
    
    def normalize(self, value: Any) -> List[RichTextElement]:
        """Normalize rich text value."""
        if value is None or value == "":
            return []
        
        if isinstance(value, str):
            return [RichTextElement(
                type="text",
                text={"content": value},
                plain_text=value
            )]
        
        if isinstance(value, list):
            normalized = []
            for element in value:
                if isinstance(element, RichTextElement):
                    normalized.append(element)
                elif isinstance(element, dict):
                    normalized.append(RichTextElement(**element))
                else:
                    # Convert to string
                    text = str(element)
                    normalized.append(RichTextElement(
                        type="text",
                        text={"content": text},
                        plain_text=text
                    ))
            return normalized
        
        # Convert any other type to string
        text = str(value)
        return [RichTextElement(
            type="text",
            text={"content": text},
            plain_text=text
        )]
    
    def parse(self, api_value: Dict[str, Any]) -> RichTextProperty:
        """Parse rich text from API response."""
        return RichTextProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format rich text for API submission."""
        normalized = self.normalize(value)
        
        return {
            "type": "rich_text",
            "rich_text": [elem.model_dump(exclude_none=True) for elem in normalized]
        }
    
    def extract_plain_value(self, property_value: RichTextProperty) -> str:
        """Extract plain text from rich text property."""
        return property_value.to_plain_text()