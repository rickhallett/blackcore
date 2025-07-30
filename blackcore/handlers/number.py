"""Handler for number properties."""

from typing import Any, Dict, Optional
from ..models.properties import PropertyType, NumberProperty
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class NumberHandler(PropertyHandler):
    """Handler for number properties."""

    property_type = PropertyType.NUMBER

    def validate(self, value: Any) -> bool:
        """Validate number value."""
        if value is None:
            return True

        if isinstance(value, (int, float)):
            # Check for special float values
            if value != value:  # NaN check
                raise ValidationError("Number cannot be NaN", field="number", value=value)
            if value == float("inf") or value == float("-inf"):
                raise ValidationError("Number cannot be infinity", field="number", value=value)
            return True

        if isinstance(value, str):
            # Try to parse string as number
            try:
                float_val = float(value)
                # Validate parsed value
                return self.validate(float_val)
            except ValueError:
                raise ValidationError(
                    f"Cannot parse '{value}' as number", field="number", value=value
                )

        raise ValidationError(
            f"Number must be int, float, or numeric string, got {type(value).__name__}",
            field="number",
            value=value,
        )

    def normalize(self, value: Any) -> Optional[float]:
        """Normalize number value."""
        if value is None or value == "":
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Handle special cases
            cleaned = value.strip()
            if cleaned == "":
                return None

            # Remove common formatting
            cleaned = cleaned.replace(",", "")

            try:
                return float(cleaned)
            except ValueError:
                raise ValidationError(
                    f"Cannot parse '{value}' as number", field="number", value=value
                )

        # Try to convert other types
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Cannot convert {type(value).__name__} to number",
                field="number",
                value=value,
            )

    def parse(self, api_value: Dict[str, Any]) -> NumberProperty:
        """Parse number from API response."""
        return NumberProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format number for API submission."""
        normalized = self.normalize(value)

        return {"type": "number", "number": normalized}

    def extract_plain_value(self, property_value: NumberProperty) -> Optional[float]:
        """Extract number value."""
        return property_value.number
