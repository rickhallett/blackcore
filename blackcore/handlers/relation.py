"""Handler for relation properties."""

from typing import Any, Dict, List
from ..models.properties import PropertyType, RelationProperty
from .base import PropertyHandler


class RelationHandler(PropertyHandler):
    """Handler for relation properties."""
    
    property_type = PropertyType.RELATION
    
    def validate(self, value: Any) -> bool:
        return True
    
    def normalize(self, value: Any) -> List[Dict[str, str]]:
        if value is None:
            return []
        if isinstance(value, list):
            return [{"id": str(v)} for v in value]
        return []
    
    def parse(self, api_value: Dict[str, Any]) -> RelationProperty:
        return RelationProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        normalized = self.normalize(value)
        return {
            "type": "relation",
            "relation": normalized
        }
    
    def extract_plain_value(self, property_value: RelationProperty) -> List[str]:
        return [rel.get("id", "") for rel in property_value.relation]
