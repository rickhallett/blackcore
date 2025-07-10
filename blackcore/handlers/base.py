"""Base property handler and registry."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union
from ..models.properties import PropertyType, BasePropertyValue
from ..errors.handlers import PropertyError, ValidationError, ErrorContext


class PropertyHandler(ABC):
    """Abstract base class for property handlers."""

    property_type: PropertyType

    def __init__(self):
        """Initialize property handler."""
        if not hasattr(self, "property_type"):
            raise NotImplementedError("Property handler must define property_type")

    @abstractmethod
    def validate(self, value: Any) -> bool:
        """Validate a property value.

        Args:
            value: Value to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If value is invalid
        """
        pass

    @abstractmethod
    def normalize(self, value: Any) -> Any:
        """Normalize a property value for API submission.

        Args:
            value: Value to normalize

        Returns:
            Normalized value
        """
        pass

    @abstractmethod
    def parse(self, api_value: Dict[str, Any]) -> BasePropertyValue:
        """Parse a property value from API response.

        Args:
            api_value: Raw API value

        Returns:
            Parsed property value
        """
        pass

    @abstractmethod
    def format_for_api(self, value: Any) -> Dict[str, Any]:
        """Format a value for API submission.

        Args:
            value: Value to format

        Returns:
            API-formatted value
        """
        pass

    def extract_plain_value(self, property_value: BasePropertyValue) -> Any:
        """Extract plain value from property value object.

        Args:
            property_value: Property value object

        Returns:
            Plain value (string, number, etc.)
        """
        # Default implementation - can be overridden
        return None

    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle property-specific errors.

        Args:
            error: The error that occurred
            context: Additional context
        """
        error_context = ErrorContext(
            operation="property_handling",
            resource_type="property",
            metadata={"property_type": self.property_type.value, **(context or {})},
        )

        if isinstance(error, ValidationError):
            raise error
        else:
            raise PropertyError(
                f"Error handling {self.property_type.value} property: {str(error)}",
                property_name=context.get("property_name", "unknown"),
                property_type=self.property_type.value,
                context=error_context,
            )


class PropertyHandlerRegistry:
    """Registry for property handlers."""

    def __init__(self):
        """Initialize registry."""
        self._handlers: Dict[PropertyType, PropertyHandler] = {}
        self._initialized = False

    def register(self, handler: PropertyHandler) -> None:
        """Register a property handler.

        Args:
            handler: Handler to register
        """
        if not isinstance(handler, PropertyHandler):
            raise TypeError("Handler must be a PropertyHandler instance")

        self._handlers[handler.property_type] = handler

    def get_handler(self, property_type: Union[PropertyType, str]) -> PropertyHandler:
        """Get handler for a property type.

        Args:
            property_type: Property type

        Returns:
            Property handler

        Raises:
            KeyError: If no handler registered for type
        """
        if not self._initialized:
            self._auto_register_handlers()

        if isinstance(property_type, str):
            try:
                property_type = PropertyType(property_type)
            except ValueError:
                raise KeyError(f"Invalid property type: {property_type}")

        if property_type not in self._handlers:
            raise KeyError(f"No handler registered for property type: {property_type.value}")

        return self._handlers[property_type]

    def _auto_register_handlers(self) -> None:
        """Auto-register all available handlers."""
        # Import here to avoid circular imports
        from .text import TitleHandler, RichTextHandler
        from .number import NumberHandler
        from .select import SelectHandler, MultiSelectHandler, StatusHandler
        from .date import DateHandler
        from .people import PeopleHandler
        from .files import FilesHandler
        from .checkbox import CheckboxHandler
        from .url import URLHandler, EmailHandler, PhoneHandler
        from .relation import RelationHandler
        from .formula import FormulaHandler
        from .rollup import RollupHandler
        from .timestamp import CreatedTimeHandler, LastEditedTimeHandler
        from .user import CreatedByHandler, LastEditedByHandler

        # Register all handlers
        handlers = [
            TitleHandler(),
            RichTextHandler(),
            NumberHandler(),
            SelectHandler(),
            MultiSelectHandler(),
            StatusHandler(),
            DateHandler(),
            PeopleHandler(),
            FilesHandler(),
            CheckboxHandler(),
            URLHandler(),
            EmailHandler(),
            PhoneHandler(),
            RelationHandler(),
            FormulaHandler(),
            RollupHandler(),
            CreatedTimeHandler(),
            LastEditedTimeHandler(),
            CreatedByHandler(),
            LastEditedByHandler(),
        ]

        for handler in handlers:
            self.register(handler)

        self._initialized = True

    def validate_value(self, property_type: Union[PropertyType, str], value: Any) -> bool:
        """Validate a value using appropriate handler.

        Args:
            property_type: Property type
            value: Value to validate

        Returns:
            True if valid
        """
        handler = self.get_handler(property_type)
        return handler.validate(value)

    def normalize_value(self, property_type: Union[PropertyType, str], value: Any) -> Any:
        """Normalize a value using appropriate handler.

        Args:
            property_type: Property type
            value: Value to normalize

        Returns:
            Normalized value
        """
        handler = self.get_handler(property_type)
        return handler.normalize(value)

    def parse_api_value(self, api_value: Dict[str, Any]) -> Optional[BasePropertyValue]:
        """Parse an API value using appropriate handler.

        Args:
            api_value: Raw API value with 'type' field

        Returns:
            Parsed property value or None
        """
        if not api_value or "type" not in api_value:
            return None

        try:
            property_type = PropertyType(api_value["type"])
            handler = self.get_handler(property_type)
            return handler.parse(api_value)
        except (ValueError, KeyError):
            return None

    def format_for_api(self, property_type: Union[PropertyType, str], value: Any) -> Dict[str, Any]:
        """Format a value for API submission.

        Args:
            property_type: Property type
            value: Value to format

        Returns:
            API-formatted value
        """
        handler = self.get_handler(property_type)
        return handler.format_for_api(value)


# Global registry instance
property_handler_registry = PropertyHandlerRegistry()
