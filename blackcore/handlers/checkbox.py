"""Handler for checkbox properties."""

from typing import Any, Dict
from ..models.properties import PropertyType, CheckboxProperty
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class CheckboxHandler(PropertyHandler):
    """Handler for checkbox properties."""
    
    property_type = PropertyType.CHECKBOX
    
    def validate(self, value: Any) -> bool:
        """Validate checkbox value."""
        if value is None:
            return True
        if isinstance(value, bool):
            return True
        raise ValidationError(
            f"Checkbox must be boolean, got {type(value).__name__}",
            field="checkbox",
            value=value
        )
    
    def normalize(self, value: Any) -> bool:
        """Normalize checkbox value."""
        if value is None:
            return False
        return bool(value)
    
    def parse(self, api_value: Dict[str, Any]) -> CheckboxProperty:
        """Parse checkbox from API response."""
        return CheckboxProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format checkbox for API submission."""
        normalized = self.normalize(value)
        return {
            "type": "checkbox",
            "checkbox": normalized
        }
    
    def extract_plain_value(self, property_value: CheckboxProperty) -> bool:
        """Extract checkbox value."""
        return property_value.checkbox