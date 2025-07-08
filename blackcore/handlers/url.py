"""Handlers for URL, email, and phone properties."""

from typing import Any, Dict, Optional
from ..models.properties import PropertyType, URLProperty, EmailProperty, PhoneProperty
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class URLHandler(PropertyHandler):
    """Handler for URL properties."""
    
    property_type = PropertyType.URL
    
    def validate(self, value: Any) -> bool:
        """Validate URL value."""
        if value is None:
            return True
        if isinstance(value, str):
            return True
        raise ValidationError(
            f"URL must be string, got {type(value).__name__}",
            field="url",
            value=value
        )
    
    def normalize(self, value: Any) -> Optional[str]:
        """Normalize URL value."""
        if value is None or value == "":
            return None
        return str(value)
    
    def parse(self, api_value: Dict[str, Any]) -> URLProperty:
        """Parse URL from API response."""
        return URLProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format URL for API submission."""
        normalized = self.normalize(value)
        return {
            "type": "url",
            "url": normalized
        }
    
    def extract_plain_value(self, property_value: URLProperty) -> Optional[str]:
        """Extract URL value."""
        return property_value.url


class EmailHandler(PropertyHandler):
    """Handler for email properties."""
    
    property_type = PropertyType.EMAIL
    
    def validate(self, value: Any) -> bool:
        """Validate email value."""
        if value is None:
            return True
        if isinstance(value, str):
            if "@" in value:
                return True
            raise ValidationError(
                "Invalid email format",
                field="email",
                value=value
            )
        raise ValidationError(
            f"Email must be string, got {type(value).__name__}",
            field="email",
            value=value
        )
    
    def normalize(self, value: Any) -> Optional[str]:
        """Normalize email value."""
        if value is None or value == "":
            return None
        return str(value)
    
    def parse(self, api_value: Dict[str, Any]) -> EmailProperty:
        """Parse email from API response."""
        return EmailProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format email for API submission."""
        normalized = self.normalize(value)
        return {
            "type": "email",
            "email": normalized
        }
    
    def extract_plain_value(self, property_value: EmailProperty) -> Optional[str]:
        """Extract email value."""
        return property_value.email


class PhoneHandler(PropertyHandler):
    """Handler for phone number properties."""
    
    property_type = PropertyType.PHONE_NUMBER
    
    def validate(self, value: Any) -> bool:
        """Validate phone value."""
        if value is None:
            return True
        if isinstance(value, str):
            return True
        raise ValidationError(
            f"Phone must be string, got {type(value).__name__}",
            field="phone_number",
            value=value
        )
    
    def normalize(self, value: Any) -> Optional[str]:
        """Normalize phone value."""
        if value is None or value == "":
            return None
        return str(value)
    
    def parse(self, api_value: Dict[str, Any]) -> PhoneProperty:
        """Parse phone from API response."""
        return PhoneProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format phone for API submission."""
        normalized = self.normalize(value)
        return {
            "type": "phone_number",
            "phone_number": normalized
        }
    
    def extract_plain_value(self, property_value: PhoneProperty) -> Optional[str]:
        """Extract phone value."""
        return property_value.phone_number