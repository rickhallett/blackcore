"""Consolidated property handlers for all Notion property types."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, date
import re


class PropertyHandler(ABC):
    """Base class for all property handlers."""

    @abstractmethod
    def validate(self, value: Any) -> bool:
        """Validate a value for this property type."""
        pass

    @abstractmethod
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format a value for Notion API submission."""
        pass

    @abstractmethod
    def parse_from_api(self, api_value: Dict[str, Any]) -> Any:
        """Parse a value from Notion API response."""
        pass


class TextPropertyHandler(PropertyHandler):
    """Handles text and title properties."""

    def __init__(self, is_title: bool = False, max_length: int = 2000):
        self.is_title = is_title
        self.max_length = max_length

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return len(value) <= self.max_length

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        text = str(value)[: self.max_length]

        if self.is_title:
            return {"title": [{"text": {"content": text}}]}
        else:
            return {"rich_text": [{"text": {"content": text}}]}

    def parse_from_api(self, api_value: Dict[str, Any]) -> str:
        if self.is_title and "title" in api_value:
            texts = api_value["title"]
        elif "rich_text" in api_value:
            texts = api_value["rich_text"]
        else:
            return ""

        return "".join(t.get("text", {}).get("content", "") for t in texts)


class NumberPropertyHandler(PropertyHandler):
    """Handles number properties."""

    def validate(self, value: Any) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"number": float(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[float]:
        return api_value.get("number")


class SelectPropertyHandler(PropertyHandler):
    """Handles select properties."""

    def __init__(self, options: Optional[List[str]] = None):
        self.options = options or []

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return not self.options or value in self.options

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"select": {"name": str(value)}}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        select = api_value.get("select", {})
        return select.get("name") if select else None


class MultiSelectPropertyHandler(PropertyHandler):
    """Handles multi-select properties."""

    def __init__(self, options: Optional[List[str]] = None):
        self.options = options or []

    def validate(self, value: Any) -> bool:
        if not isinstance(value, list):
            return False
        return all(isinstance(v, str) for v in value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            value = [value]
        return {"multi_select": [{"name": str(v)} for v in value]}

    def parse_from_api(self, api_value: Dict[str, Any]) -> List[str]:
        multi_select = api_value.get("multi_select", [])
        return [item.get("name", "") for item in multi_select if item.get("name")]


class DatePropertyHandler(PropertyHandler):
    """Handles date properties."""

    def validate(self, value: Any) -> bool:
        if isinstance(value, (datetime, date)):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True
            except ValueError:
                return False
        return False

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            date_str = value
        elif isinstance(value, datetime):
            date_str = value.isoformat()
        elif isinstance(value, date):
            date_str = value.isoformat()
        else:
            raise ValueError(f"Invalid date value: {value}")

        return {"date": {"start": date_str}}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        date_obj = api_value.get("date", {})
        return date_obj.get("start") if date_obj else None


class CheckboxPropertyHandler(PropertyHandler):
    """Handles checkbox properties."""

    def validate(self, value: Any) -> bool:
        return isinstance(value, bool)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"checkbox": bool(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> bool:
        return api_value.get("checkbox", False)


class URLPropertyHandler(PropertyHandler):
    """Handles URL properties."""

    URL_REGEX = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.URL_REGEX.match(value))

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"url": str(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("url")


class EmailPropertyHandler(PropertyHandler):
    """Handles email properties."""

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.EMAIL_REGEX.match(value))

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"email": str(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("email")


class PhonePropertyHandler(PropertyHandler):
    """Handles phone number properties."""

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        # Basic validation - just check it has some digits
        return any(c.isdigit() for c in value)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"phone_number": str(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("phone_number")


class PeoplePropertyHandler(PropertyHandler):
    """Handles people properties."""

    def validate(self, value: Any) -> bool:
        if isinstance(value, str):
            return True
        if isinstance(value, list):
            return all(isinstance(v, str) for v in value)
        return False

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            value = [value]
        # Note: In real usage, these would be user IDs, not names
        # This is simplified for the minimal implementation
        return {"people": [{"object": "user", "id": v} for v in value]}

    def parse_from_api(self, api_value: Dict[str, Any]) -> List[str]:
        people = api_value.get("people", [])
        return [p.get("id", "") for p in people if p.get("id")]


class FilesPropertyHandler(PropertyHandler):
    """Handles files & media properties."""

    def validate(self, value: Any) -> bool:
        if isinstance(value, str):
            return value.startswith(("http://", "https://"))
        if isinstance(value, list):
            return all(
                isinstance(v, str) and v.startswith(("http://", "https://"))
                for v in value
            )
        return False

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            value = [value]
        return {
            "files": [
                {"name": f"File {i + 1}", "external": {"url": url}}
                for i, url in enumerate(value)
            ]
        }

    def parse_from_api(self, api_value: Dict[str, Any]) -> List[str]:
        files = api_value.get("files", [])
        urls = []
        for f in files:
            if "external" in f:
                urls.append(f["external"].get("url", ""))
            elif "file" in f:
                urls.append(f["file"].get("url", ""))
        return [u for u in urls if u]


class RelationPropertyHandler(PropertyHandler):
    """Handles relation properties."""

    def validate(self, value: Any) -> bool:
        if isinstance(value, str):
            return True
        if isinstance(value, list):
            return all(isinstance(v, str) for v in value)
        return False

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            value = [value]
        return {"relation": [{"id": v} for v in value]}

    def parse_from_api(self, api_value: Dict[str, Any]) -> List[str]:
        relations = api_value.get("relation", [])
        return [r.get("id", "") for r in relations if r.get("id")]


class FormulaPropertyHandler(PropertyHandler):
    """Handles formula properties (read-only)."""

    def validate(self, value: Any) -> bool:
        return False  # Formulas are read-only

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Formula properties are read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Any:
        formula = api_value.get("formula", {})
        return formula.get("string") or formula.get("number") or formula.get("boolean")


class RollupPropertyHandler(PropertyHandler):
    """Handles rollup properties (read-only)."""

    def validate(self, value: Any) -> bool:
        return False  # Rollups are read-only

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Rollup properties are read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Any:
        rollup = api_value.get("rollup", {})
        return rollup.get("number") or rollup.get("array", [])


class CreatedTimePropertyHandler(PropertyHandler):
    """Handles created time property (read-only)."""

    def validate(self, value: Any) -> bool:
        return False  # Created time is read-only

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Created time property is read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("created_time")


class LastEditedTimePropertyHandler(PropertyHandler):
    """Handles last edited time property (read-only)."""

    def validate(self, value: Any) -> bool:
        return False  # Last edited time is read-only

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Last edited time property is read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("last_edited_time")


class PropertyHandlerFactory:
    """Factory for creating property handlers based on type."""

    HANDLERS = {
        "title": lambda: TextPropertyHandler(is_title=True),
        "rich_text": lambda: TextPropertyHandler(is_title=False),
        "number": NumberPropertyHandler,
        "select": SelectPropertyHandler,
        "multi_select": MultiSelectPropertyHandler,
        "date": DatePropertyHandler,
        "checkbox": CheckboxPropertyHandler,
        "url": URLPropertyHandler,
        "email": EmailPropertyHandler,
        "phone_number": PhonePropertyHandler,
        "people": PeoplePropertyHandler,
        "files": FilesPropertyHandler,
        "relation": RelationPropertyHandler,
        "formula": FormulaPropertyHandler,
        "rollup": RollupPropertyHandler,
        "created_time": CreatedTimePropertyHandler,
        "last_edited_time": LastEditedTimePropertyHandler,
    }

    @classmethod
    def create(cls, property_type: str, **kwargs) -> PropertyHandler:
        """Create a property handler for the given type.

        Args:
            property_type: The Notion property type
            **kwargs: Additional arguments for the handler

        Returns:
            PropertyHandler instance

        Raises:
            ValueError: If property type is not supported
        """
        if property_type not in cls.HANDLERS:
            raise ValueError(f"Unsupported property type: {property_type}")

        handler_class = cls.HANDLERS[property_type]
        return handler_class(**kwargs) if kwargs else handler_class()
