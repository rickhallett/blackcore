"""Handler for rollup properties (read-only)."""

from typing import Any, Dict
from ..models.properties import PropertyType, RollupProperty
from .base import PropertyHandler


class RollupHandler(PropertyHandler):
    """Handler for rollup properties."""

    property_type = PropertyType.ROLLUP

    def validate(self, value: Any) -> bool:
        # Rollup is read-only
        return True

    def normalize(self, value: Any) -> Any:
        # Rollup is read-only
        return None

    def parse(self, api_value: Dict[str, Any]) -> RollupProperty:
        return RollupProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        # Rollup is read-only, cannot be set
        raise NotImplementedError("Rollup properties are read-only")

    def extract_plain_value(self, property_value: RollupProperty) -> Any:
        if property_value.rollup:
            return (
                property_value.rollup.number
                or property_value.rollup.date
                or property_value.rollup.array
            )
        return None
