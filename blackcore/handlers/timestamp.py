"""Handlers for timestamp properties (read-only)."""

from typing import Any, Dict
from datetime import datetime
from ..models.properties import (
    PropertyType,
    CreatedTimeProperty,
    LastEditedTimeProperty,
)
from .base import PropertyHandler


class CreatedTimeHandler(PropertyHandler):
    """Handler for created time properties."""

    property_type = PropertyType.CREATED_TIME

    def validate(self, value: Any) -> bool:
        return True

    def normalize(self, value: Any) -> Any:
        return None

    def parse(self, api_value: Dict[str, Any]) -> CreatedTimeProperty:
        return CreatedTimeProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Created time is read-only")

    def extract_plain_value(self, property_value: CreatedTimeProperty) -> datetime:
        return property_value.created_time


class LastEditedTimeHandler(PropertyHandler):
    """Handler for last edited time properties."""

    property_type = PropertyType.LAST_EDITED_TIME

    def validate(self, value: Any) -> bool:
        return True

    def normalize(self, value: Any) -> Any:
        return None

    def parse(self, api_value: Dict[str, Any]) -> LastEditedTimeProperty:
        return LastEditedTimeProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Last edited time is read-only")

    def extract_plain_value(self, property_value: LastEditedTimeProperty) -> datetime:
        return property_value.last_edited_time
