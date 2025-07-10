"""Handler for date properties."""

from typing import Any, Dict, Optional, Union
from datetime import datetime, date
from ..models.properties import PropertyType, DateProperty, DateValue
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class DateHandler(PropertyHandler):
    """Handler for date properties."""

    property_type = PropertyType.DATE

    def validate(self, value: Any) -> bool:
        """Validate date value."""
        if value is None:
            return True

        if isinstance(value, (str, date, datetime)):
            return True

        if isinstance(value, dict):
            if "start" not in value:
                raise ValidationError("Date must have 'start' field", field="date", value=value)
            return True

        raise ValidationError(
            f"Date must be string, date, datetime, or dict, got {type(value).__name__}",
            field="date",
            value=value,
        )

    def normalize(self, value: Any) -> Optional[DateValue]:
        """Normalize date value."""
        if value is None or value == "":
            return None

        if isinstance(value, (str, date, datetime)):
            return DateValue(start=value)

        if isinstance(value, dict):
            return DateValue(**value)

        if isinstance(value, DateValue):
            return value

        raise ValidationError(
            f"Cannot normalize {type(value).__name__} to date", field="date", value=value
        )

    def parse(self, api_value: Dict[str, Any]) -> DateProperty:
        """Parse date from API response."""
        return DateProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format date for API submission."""
        normalized = self.normalize(value)

        return {
            "type": "date",
            "date": normalized.model_dump(exclude_none=True) if normalized else None,
        }

    def extract_plain_value(self, property_value: DateProperty) -> Optional[str]:
        """Extract date value as ISO string."""
        if property_value.date:
            return property_value.date.start
        return None
