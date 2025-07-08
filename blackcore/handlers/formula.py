"""Handler for formula properties (read-only)."""

from typing import Any, Dict
from ..models.properties import PropertyType, FormulaProperty
from .base import PropertyHandler


class FormulaHandler(PropertyHandler):
    """Handler for formula properties."""
    
    property_type = PropertyType.FORMULA
    
    def validate(self, value: Any) -> bool:
        # Formula is read-only
        return True
    
    def normalize(self, value: Any) -> Any:
        # Formula is read-only
        return None
    
    def parse(self, api_value: Dict[str, Any]) -> FormulaProperty:
        return FormulaProperty(**api_value)
    
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        # Formula is read-only, cannot be set
        raise NotImplementedError("Formula properties are read-only")
    
    def extract_plain_value(self, property_value: FormulaProperty) -> Any:
        if property_value.formula:
            return property_value.formula.string or property_value.formula.number or property_value.formula.boolean
        return None
