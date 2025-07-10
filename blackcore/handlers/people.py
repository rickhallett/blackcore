"""Handler for people properties."""

from typing import Any, Dict, List
from ..models.properties import PropertyType, PeopleProperty
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class PeopleHandler(PropertyHandler):
    """Handler for people properties."""

    property_type = PropertyType.PEOPLE

    def validate(self, value: Any) -> bool:
        """Validate people value."""
        if value is None:
            return True

        if isinstance(value, str):
            # Single user ID
            return True

        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    # User ID
                    continue
                elif isinstance(item, dict):
                    if "id" not in item and "object" not in item:
                        raise ValidationError(
                            "People item must have 'id' or be a user object",
                            field="people",
                            value=item,
                        )
                else:
                    raise ValidationError(
                        f"People items must be string or dict, got {type(item).__name__}",
                        field="people",
                    )
            return True

        raise ValidationError(
            f"People must be string or list, got {type(value).__name__}",
            field="people",
            value=value,
        )

    def normalize(self, value: Any) -> List[Dict[str, str]]:
        """Normalize people value."""
        if value is None or value == [] or value == "":
            return []

        if isinstance(value, str):
            # Single user ID
            return [{"object": "user", "id": value}]

        if isinstance(value, list):
            people = []
            for item in value:
                if isinstance(item, str):
                    people.append({"object": "user", "id": item})
                elif isinstance(item, dict):
                    if "object" not in item:
                        item["object"] = "user"
                    people.append(item)
                else:
                    raise ValidationError(
                        f"Cannot normalize {type(item).__name__} to user", field="people"
                    )
            return people

        raise ValidationError(
            f"Cannot normalize {type(value).__name__} to people", field="people", value=value
        )

    def parse(self, api_value: Dict[str, Any]) -> PeopleProperty:
        """Parse people from API response."""
        return PeopleProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format people for API submission."""
        normalized = self.normalize(value)

        return {"type": "people", "people": normalized}

    def extract_plain_value(self, property_value: PeopleProperty) -> List[str]:
        """Extract user IDs."""
        return [person.get("id", "") for person in property_value.people]
