"""Consolidated property handlers for all Notion property types."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date
import re

from blackcore.minimal.property_validation import (
    PropertyValidator,
    PropertyValidatorFactory,
    ValidationLevel,
    ValidationResult,
    ValidationError,
    ValidationErrorType
)


class PropertyHandler(ABC):
    """Base class for all property handlers."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self._validator: Optional[PropertyValidator] = None

    def validate(self, value: Any) -> bool:
        """Validate a value for this property type.
        
        This method provides backward compatibility.
        Use validate_with_details() for detailed error information.
        """
        result = self.validate_with_details(value)
        return result.is_valid
    
    def validate_with_details(self, value: Any) -> ValidationResult:
        """Validate a value and return detailed results."""
        if self._validator is None:
            # Create validator on demand
            self._validator = self._create_validator()
        return self._validator.validate(value)
    
    @abstractmethod
    def _create_validator(self) -> PropertyValidator:
        """Create the validator for this property type."""
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

    def __init__(self, is_title: bool = False, max_length: int = 2000, 
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
        self.is_title = is_title
        self.max_length = max_length
    
    def _create_validator(self) -> PropertyValidator:
        field_name = "title" if self.is_title else "rich_text"
        return PropertyValidatorFactory.create_validator(
            field_name,
            field_name,
            {"max_length": self.max_length},
            self.validation_level
        )

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
    
    def __init__(self, minimum: Optional[float] = None, maximum: Optional[float] = None,
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
        self.minimum = minimum
        self.maximum = maximum
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "number",
            "number",
            {"minimum": self.minimum, "maximum": self.maximum},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"number": float(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[float]:
        return api_value.get("number")


class SelectPropertyHandler(PropertyHandler):
    """Handles select properties."""

    def __init__(self, options: Optional[List[str]] = None,
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
        self.options = options or []
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "select",
            "select",
            {"allowed_values": self.options},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"select": {"name": str(value)}}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        select = api_value.get("select", {})
        return select.get("name") if select else None


class MultiSelectPropertyHandler(PropertyHandler):
    """Handles multi-select properties."""

    def __init__(self, options: Optional[List[str]] = None,
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
        self.options = options or []
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "multi_select",
            "multi_select",
            {"unique_items": True},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            value = [value]
        return {"multi_select": [{"name": str(v)} for v in value]}

    def parse_from_api(self, api_value: Dict[str, Any]) -> List[str]:
        multi_select = api_value.get("multi_select", [])
        return [item.get("name", "") for item in multi_select if item.get("name")]


class DatePropertyHandler(PropertyHandler):
    """Handles date properties."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "date",
            "date",
            {},
            self.validation_level
        )

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
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "checkbox",
            "checkbox",
            {},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"checkbox": bool(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> bool:
        return api_value.get("checkbox", False)


class URLPropertyHandler(PropertyHandler):
    """Handles URL properties."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "url",
            "url",
            {},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"url": str(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("url")


class EmailPropertyHandler(PropertyHandler):
    """Handles email properties."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "email",
            "email",
            {},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"email": str(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("email")


class PhonePropertyHandler(PropertyHandler):
    """Handles phone number properties."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "phone_number",
            "phone_number",
            {},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        return {"phone_number": str(value)}

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("phone_number")


class PeoplePropertyHandler(PropertyHandler):
    """Handles people properties."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "people",
            "people",
            {},
            self.validation_level
        )

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
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "files",
            "files",
            {},
            self.validation_level
        )

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
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        return PropertyValidatorFactory.create_validator(
            "relation",
            "relation",
            {},
            self.validation_level
        )

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            value = [value]
        return {"relation": [{"id": v} for v in value]}

    def parse_from_api(self, api_value: Dict[str, Any]) -> List[str]:
        relations = api_value.get("relation", [])
        return [r.get("id", "") for r in relations if r.get("id")]


class FormulaPropertyHandler(PropertyHandler):
    """Handles formula properties (read-only)."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        # Read-only property, always fails validation
        from blackcore.minimal.property_validation import PropertyValidator
        class ReadOnlyValidator(PropertyValidator):
            def _validate_type(self, value: Any) -> ValidationResult:
                result = ValidationResult(is_valid=False)
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} is read-only",
                    value=value
                ))
                return result
        return ReadOnlyValidator("formula", required=False)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Formula properties are read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Any:
        formula = api_value.get("formula", {})
        return formula.get("string") or formula.get("number") or formula.get("boolean")


class RollupPropertyHandler(PropertyHandler):
    """Handles rollup properties (read-only)."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        # Read-only property, always fails validation
        from blackcore.minimal.property_validation import PropertyValidator
        class ReadOnlyValidator(PropertyValidator):
            def _validate_type(self, value: Any) -> ValidationResult:
                result = ValidationResult(is_valid=False)
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} is read-only",
                    value=value
                ))
                return result
        return ReadOnlyValidator("rollup", required=False)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Rollup properties are read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Any:
        rollup = api_value.get("rollup", {})
        return rollup.get("number") or rollup.get("array", [])


class CreatedTimePropertyHandler(PropertyHandler):
    """Handles created time property (read-only)."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        # Read-only property, always fails validation
        from blackcore.minimal.property_validation import PropertyValidator
        class ReadOnlyValidator(PropertyValidator):
            def _validate_type(self, value: Any) -> ValidationResult:
                result = ValidationResult(is_valid=False)
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} is read-only",
                    value=value
                ))
                return result
        return ReadOnlyValidator("created_time", required=False)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Created time property is read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("created_time")


class LastEditedTimePropertyHandler(PropertyHandler):
    """Handles last edited time property (read-only)."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        super().__init__(validation_level)
    
    def _create_validator(self) -> PropertyValidator:
        # Read-only property, always fails validation
        from blackcore.minimal.property_validation import PropertyValidator
        class ReadOnlyValidator(PropertyValidator):
            def _validate_type(self, value: Any) -> ValidationResult:
                result = ValidationResult(is_valid=False)
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} is read-only",
                    value=value
                ))
                return result
        return ReadOnlyValidator("last_edited_time", required=False)

    def format_for_api(self, value: Any) -> Dict[str, Any]:
        raise NotImplementedError("Last edited time property is read-only")

    def parse_from_api(self, api_value: Dict[str, Any]) -> Optional[str]:
        return api_value.get("last_edited_time")


class PropertyHandlerFactory:
    """Factory for creating property handlers based on type."""

    HANDLERS = {
        "title": lambda **kwargs: TextPropertyHandler(is_title=True, **kwargs),
        "rich_text": lambda **kwargs: TextPropertyHandler(is_title=False, **kwargs),
        "number": lambda **kwargs: NumberPropertyHandler(**kwargs),
        "select": lambda **kwargs: SelectPropertyHandler(**kwargs),
        "multi_select": lambda **kwargs: MultiSelectPropertyHandler(**kwargs),
        "date": lambda **kwargs: DatePropertyHandler(**kwargs),
        "checkbox": lambda **kwargs: CheckboxPropertyHandler(**kwargs),
        "url": lambda **kwargs: URLPropertyHandler(**kwargs),
        "email": lambda **kwargs: EmailPropertyHandler(**kwargs),
        "phone_number": lambda **kwargs: PhonePropertyHandler(**kwargs),
        "people": lambda **kwargs: PeoplePropertyHandler(**kwargs),
        "files": lambda **kwargs: FilesPropertyHandler(**kwargs),
        "relation": lambda **kwargs: RelationPropertyHandler(**kwargs),
        "formula": lambda **kwargs: FormulaPropertyHandler(**kwargs),
        "rollup": lambda **kwargs: RollupPropertyHandler(**kwargs),
        "created_time": lambda **kwargs: CreatedTimePropertyHandler(**kwargs),
        "last_edited_time": lambda **kwargs: LastEditedTimePropertyHandler(**kwargs),
    }

    @classmethod
    def create(cls, property_type: str, validation_level: ValidationLevel = ValidationLevel.STANDARD, **kwargs) -> PropertyHandler:
        """Create a property handler for the given type.

        Args:
            property_type: The Notion property type
            validation_level: Validation strictness level
            **kwargs: Additional arguments for the handler

        Returns:
            PropertyHandler instance

        Raises:
            ValueError: If property type is not supported
        """
        if property_type not in cls.HANDLERS:
            raise ValueError(f"Unsupported property type: {property_type}")

        handler_factory = cls.HANDLERS[property_type]
        kwargs['validation_level'] = validation_level
        return handler_factory(**kwargs)
