"""Handlers for user properties (read-only)."""

from typing import Any, Dict
from ..models.properties import PropertyType, CreatedByProperty, LastEditedByProperty
from .base import PropertyHandler


class CreatedByHandler(PropertyHandler):
    """Handler for created by properties."""
    
    property_type = PropertyType.CREATED_BY
    
    def validate(self, value: Any) -> bool:
        return True
    
    def normalize(self, value: Any) -> Any:
        return None
    
    def parse(self, api_value: Dict[str, Any]) -> CreatedByProperty:
        return CreatedByProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Created by is read-only")
    
    def extract_plain_value(self, property_value: CreatedByProperty) -> str:
        user = property_value.created_by
        return user.get("name") or user.get("id", "")


class LastEditedByHandler(PropertyHandler):
    """Handler for last edited by properties."""
    
    property_type = PropertyType.LAST_EDITED_BY
    
    def validate(self, value: Any) -> bool:
        return True
    
    def normalize(self, value: Any) -> Any:
        return None
    
    def parse(self, api_value: Dict[str, Any]) -> LastEditedByProperty:
        return LastEditedByProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Last edited by is read-only")
    
    def extract_plain_value(self, property_value: LastEditedByProperty) -> str:
        user = property_value.last_edited_by
        return user.get("name") or user.get("id", "")
