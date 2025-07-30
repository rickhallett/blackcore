"""Handlers for select-based properties (select, multi_select, status)."""

from typing import Any, Dict, List, Optional
from ..models.properties import (
    PropertyType,
    SelectProperty,
    MultiSelectProperty,
    StatusProperty,
    SelectOption,
)
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class SelectHandler(PropertyHandler):
    """Handler for select properties."""

    property_type = PropertyType.SELECT

    def validate(self, value: Any) -> bool:
        """Validate select value."""
        if value is None:
            return True

        if isinstance(value, str):
            if len(value) > 100:
                raise ValidationError(
                    "Select option name too long (max 100 characters)",
                    field="select",
                    value=value,
                )
            return True

        if isinstance(value, dict):
            if "name" not in value:
                raise ValidationError(
                    "Select option must have 'name' field", field="select", value=value
                )
            if len(value["name"]) > 100:
                raise ValidationError(
                    "Select option name too long (max 100 characters)",
                    field="select",
                    value=value["name"],
                )
            return True

        raise ValidationError(
            f"Select must be string or dict, got {type(value).__name__}",
            field="select",
            value=value,
        )

    def normalize(self, value: Any) -> Optional[SelectOption]:
        """Normalize select value."""
        if value is None or value == "":
            return None

        if isinstance(value, str):
            return SelectOption(name=value)

        if isinstance(value, dict):
            return SelectOption(**value)

        if isinstance(value, SelectOption):
            return value

        # Convert to string
        return SelectOption(name=str(value))

    def parse(self, api_value: Dict[str, Any]) -> SelectProperty:
        """Parse select from API response."""
        return SelectProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format select for API submission."""
        normalized = self.normalize(value)

        return {
            "type": "select",
            "select": normalized.model_dump(exclude_none=True) if normalized else None,
        }

    def extract_plain_value(self, property_value: SelectProperty) -> Optional[str]:
        """Extract select option name."""
        return property_value.select.name if property_value.select else None


class MultiSelectHandler(PropertyHandler):
    """Handler for multi-select properties."""

    property_type = PropertyType.MULTI_SELECT

    def validate(self, value: Any) -> bool:
        """Validate multi-select value."""
        if value is None:
            return True

        if isinstance(value, str):
            # Single string value
            if len(value) > 100:
                raise ValidationError(
                    "Multi-select option name too long (max 100 characters)",
                    field="multi_select",
                    value=value,
                )
            return True

        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    if len(item) > 100:
                        raise ValidationError(
                            "Multi-select option name too long (max 100 characters)",
                            field="multi_select",
                            value=item,
                        )
                elif isinstance(item, dict):
                    if "name" not in item:
                        raise ValidationError(
                            "Multi-select option must have 'name' field",
                            field="multi_select",
                            value=item,
                        )
                    if len(item["name"]) > 100:
                        raise ValidationError(
                            "Multi-select option name too long (max 100 characters)",
                            field="multi_select",
                            value=item["name"],
                        )
                else:
                    raise ValidationError(
                        f"Multi-select items must be string or dict, got {type(item).__name__}",
                        field="multi_select",
                    )
            return True

        raise ValidationError(
            f"Multi-select must be string or list, got {type(value).__name__}",
            field="multi_select",
            value=value,
        )

    def normalize(self, value: Any) -> List[SelectOption]:
        """Normalize multi-select value."""
        if value is None or value == [] or value == "":
            return []

        if isinstance(value, str):
            # Single string becomes single-item list
            return [SelectOption(name=value)]

        if isinstance(value, list):
            options = []
            for item in value:
                if isinstance(item, str):
                    options.append(SelectOption(name=item))
                elif isinstance(item, dict):
                    options.append(SelectOption(**item))
                elif isinstance(item, SelectOption):
                    options.append(item)
                else:
                    # Convert to string
                    options.append(SelectOption(name=str(item)))
            return options

        # Single non-list value
        return [SelectOption(name=str(value))]

    def parse(self, api_value: Dict[str, Any]) -> MultiSelectProperty:
        """Parse multi-select from API response."""
        return MultiSelectProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format multi-select for API submission."""
        normalized = self.normalize(value)

        return {
            "type": "multi_select",
            "multi_select": [opt.model_dump(exclude_none=True) for opt in normalized],
        }

    def extract_plain_value(self, property_value: MultiSelectProperty) -> List[str]:
        """Extract multi-select option names."""
        return [opt.name for opt in property_value.multi_select]


class StatusHandler(PropertyHandler):
    """Handler for status properties."""

    property_type = PropertyType.STATUS

    def validate(self, value: Any) -> bool:
        """Validate status value."""
        # Status validation is similar to select
        if value is None:
            return True

        if isinstance(value, str):
            if len(value) > 100:
                raise ValidationError(
                    "Status name too long (max 100 characters)",
                    field="status",
                    value=value,
                )
            return True

        if isinstance(value, dict):
            if "name" not in value:
                raise ValidationError("Status must have 'name' field", field="status", value=value)
            if len(value["name"]) > 100:
                raise ValidationError(
                    "Status name too long (max 100 characters)",
                    field="status",
                    value=value["name"],
                )
            return True

        raise ValidationError(
            f"Status must be string or dict, got {type(value).__name__}",
            field="status",
            value=value,
        )

    def normalize(self, value: Any) -> Optional[SelectOption]:
        """Normalize status value."""
        if value is None or value == "":
            return None

        if isinstance(value, str):
            return SelectOption(name=value)

        if isinstance(value, dict):
            return SelectOption(**value)

        if isinstance(value, SelectOption):
            return value

        # Convert to string
        return SelectOption(name=str(value))

    def parse(self, api_value: Dict[str, Any]) -> StatusProperty:
        """Parse status from API response."""
        return StatusProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format status for API submission."""
        normalized = self.normalize(value)

        return {
            "type": "status",
            "status": normalized.dict(exclude_none=True) if normalized else None,
        }

    def extract_plain_value(self, property_value: StatusProperty) -> Optional[str]:
        """Extract status name."""
        return property_value.status.name if property_value.status else None
