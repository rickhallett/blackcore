"""Handler for files properties."""

from typing import Any, Dict, List
from ..models.properties import PropertyType, FilesProperty
from ..errors.handlers import ValidationError
from .base import PropertyHandler


class FilesHandler(PropertyHandler):
    """Handler for files properties."""

    property_type = PropertyType.FILES

    def validate(self, value: Any) -> bool:
        """Validate files value."""
        if value is None:
            return True

        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    # URL string
                    continue
                elif isinstance(item, dict):
                    if "url" not in item and "name" not in item:
                        raise ValidationError("File item must have 'url' or 'name'", field="files")
                else:
                    raise ValidationError(
                        f"File items must be string or dict, got {type(item).__name__}",
                        field="files",
                    )
            return True

        raise ValidationError(
            f"Files must be list, got {type(value).__name__}", field="files", value=value
        )

    def normalize(self, value: Any) -> List[Dict[str, Any]]:
        """Normalize files value."""
        if value is None or value == []:
            return []

        if isinstance(value, list):
            files = []
            for i, item in enumerate(value):
                if isinstance(item, str):
                    # Convert URL to file object
                    files.append(
                        {"type": "external", "name": f"File {i + 1}", "external": {"url": item}}
                    )
                elif isinstance(item, dict):
                    # Ensure proper structure
                    if "type" not in item:
                        item["type"] = "external"
                    files.append(item)
            return files

        raise ValidationError(
            f"Cannot normalize {type(value).__name__} to files", field="files", value=value
        )

    def parse(self, api_value: Dict[str, Any]) -> FilesProperty:
        """Parse files from API response."""
        return FilesProperty(**api_value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format files for API submission."""
        normalized = self.normalize(value)

        return {"type": "files", "files": normalized}

    def extract_plain_value(self, property_value: FilesProperty) -> List[Dict[str, Any]]:
        """Extract file information."""
        return property_value.files
