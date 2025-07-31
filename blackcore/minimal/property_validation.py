"""Standardized validation framework for property handlers.

This module provides a comprehensive validation framework that standardizes
validation logic across all property handlers, integrating security validation,
schema compliance, and configurable validation levels.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
import re
from datetime import datetime, date
import ipaddress
from urllib.parse import urlparse


class ValidationLevel(Enum):
    """Validation strictness levels."""
    MINIMAL = "minimal"      # Basic type checking only
    STANDARD = "standard"    # Type + format validation
    STRICT = "strict"        # Full validation including business rules
    SECURITY = "security"    # Include security validation


class ValidationErrorType(Enum):
    """Types of validation errors."""
    TYPE_ERROR = "type_error"
    FORMAT_ERROR = "format_error"
    LENGTH_ERROR = "length_error"
    RANGE_ERROR = "range_error"
    PATTERN_ERROR = "pattern_error"
    SECURITY_ERROR = "security_error"
    REQUIRED_ERROR = "required_error"
    SCHEMA_ERROR = "schema_error"
    BUSINESS_RULE_ERROR = "business_rule_error"


@dataclass
class ValidationError:
    """Represents a validation error."""
    error_type: ValidationErrorType
    field_name: str
    message: str
    value: Any = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    sanitized_value: Any = None
    
    def add_error(self, error: ValidationError):
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: ValidationError):
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one."""
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if other.sanitized_value is not None:
            self.sanitized_value = other.sanitized_value


class PropertyValidator(ABC):
    """Base class for property validators with configurable validation levels and security checks."""
    
    def __init__(self, 
                 field_name: str,
                 required: bool = True,
                 nullable: bool = False,
                 validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.field_name = field_name
        self.required = required
        self.nullable = nullable
        self.validation_level = validation_level
        self.custom_validators: List[Callable] = []
    
    def add_custom_validator(self, validator: Callable[[Any], Union[bool, str]]):
        """Add a custom validation function."""
        self.custom_validators.append(validator)
    
    def validate(self, value: Any) -> ValidationResult:
        """Validate a value."""
        result = ValidationResult(is_valid=True)
        
        # Check null/required
        if value is None:
            if self.required and not self.nullable:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.REQUIRED_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} is required",
                    value=value
                ))
            return result
        
        # Type validation
        type_result = self._validate_type(value)
        result.merge(type_result)
        
        if not result.is_valid and self.validation_level == ValidationLevel.MINIMAL:
            return result
        
        # Format validation
        if self.validation_level.value >= ValidationLevel.STANDARD.value:
            format_result = self._validate_format(value)
            result.merge(format_result)
        
        # Business rules validation
        if self.validation_level.value >= ValidationLevel.STRICT.value:
            business_result = self._validate_business_rules(value)
            result.merge(business_result)
        
        # Security validation
        if self.validation_level == ValidationLevel.SECURITY:
            security_result = self._validate_security(value)
            result.merge(security_result)
        
        # Custom validators
        for validator in self.custom_validators:
            try:
                validator_result = validator(value)
                if isinstance(validator_result, bool) and not validator_result:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                        field_name=self.field_name,
                        message=f"Custom validation failed for {self.field_name}",
                        value=value
                    ))
                elif isinstance(validator_result, str):
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                        field_name=self.field_name,
                        message=validator_result,
                        value=value
                    ))
            except Exception as e:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.BUSINESS_RULE_ERROR,
                    field_name=self.field_name,
                    message=f"Custom validator error: {str(e)}",
                    value=value
                ))
        
        # Set sanitized value if validation passed
        if result.is_valid and hasattr(self, '_sanitize'):
            result.sanitized_value = self._sanitize(value)
        else:
            result.sanitized_value = value
        
        return result
    
    @abstractmethod
    def _validate_type(self, value: Any) -> ValidationResult:
        """Validate value type."""
        pass
    
    def _validate_format(self, value: Any) -> ValidationResult:
        """Validate value format. Override in subclasses."""
        return ValidationResult(is_valid=True)
    
    def _validate_business_rules(self, value: Any) -> ValidationResult:
        """Validate business rules. Override in subclasses."""
        return ValidationResult(is_valid=True)
    
    def _validate_security(self, value: Any) -> ValidationResult:
        """Validate security constraints. Override in subclasses."""
        return ValidationResult(is_valid=True)


class TextValidator(PropertyValidator):
    """Validator for text properties."""
    
    def __init__(self, 
                 field_name: str,
                 max_length: int = 2000,
                 min_length: int = 0,
                 pattern: Optional[str] = None,
                 **kwargs):
        super().__init__(field_name, **kwargs)
        self.max_length = max_length
        self.min_length = min_length
        self.pattern = re.compile(pattern) if pattern else None
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not isinstance(value, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a string",
                value=value,
                context={"expected_type": "str", "actual_type": type(value).__name__}
            ))
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, str):
            return result
        
        # Length validation
        if len(value) > self.max_length:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} exceeds maximum length of {self.max_length}",
                value=value,
                context={"max_length": self.max_length, "actual_length": len(value)}
            ))
        
        if len(value) < self.min_length:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} is below minimum length of {self.min_length}",
                value=value,
                context={"min_length": self.min_length, "actual_length": len(value)}
            ))
        
        # Pattern validation
        if self.pattern and not self.pattern.match(value):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.PATTERN_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} does not match required pattern",
                value=value,
                context={"pattern": self.pattern.pattern}
            ))
        
        return result
    
    def _validate_security(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, str):
            return result
        
        # Check for null bytes
        if '\x00' in value:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.SECURITY_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} contains null bytes",
                value=value
            ))
        
        # Check for control characters
        control_chars = sum(1 for c in value if ord(c) < 32 and c not in '\n\t\r')
        if control_chars > 0:
            result.add_warning(ValidationError(
                error_type=ValidationErrorType.SECURITY_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} contains {control_chars} control characters",
                value=value
            ))
        
        return result
    
    def _sanitize(self, value: str) -> str:
        """Sanitize text value."""
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Truncate to max length
        if len(value) > self.max_length:
            value = value[:self.max_length]
        
        # Remove dangerous control characters
        value = ''.join(
            char for char in value 
            if char in '\n\t\r' or ord(char) >= 32
        )
        
        return value


class NumberValidator(PropertyValidator):
    """Validator for number properties."""
    
    def __init__(self,
                 field_name: str,
                 minimum: Optional[Union[int, float]] = None,
                 maximum: Optional[Union[int, float]] = None,
                 allow_integers_only: bool = False,
                 **kwargs):
        super().__init__(field_name, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.allow_integers_only = allow_integers_only
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if self.allow_integers_only:
            if not isinstance(value, int) or isinstance(value, bool):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} must be an integer",
                    value=value,
                    context={"expected_type": "int", "actual_type": type(value).__name__}
                ))
        else:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} must be a number",
                    value=value,
                    context={"expected_types": ["int", "float"], "actual_type": type(value).__name__}
                ))
        
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return result
        
        # Range validation
        if self.minimum is not None and value < self.minimum:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.RANGE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} is below minimum value of {self.minimum}",
                value=value,
                context={"minimum": self.minimum, "actual": value}
            ))
        
        if self.maximum is not None and value > self.maximum:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.RANGE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} is above maximum value of {self.maximum}",
                value=value,
                context={"maximum": self.maximum, "actual": value}
            ))
        
        return result


class EmailValidator(PropertyValidator):
    """Validator for email properties."""
    
    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}"
        r"[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not isinstance(value, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a string",
                value=value,
                context={"expected_type": "str", "actual_type": type(value).__name__}
            ))
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, str):
            return result
        
        # Length check
        if len(value) > 254:  # RFC 5321
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} exceeds maximum email length of 254",
                value=value
            ))
            return result
        
        # Basic format check
        if not self.EMAIL_REGEX.match(value):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} is not a valid email format",
                value=value
            ))
            return result
        
        # Additional checks
        if '@' not in value:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must contain @ symbol",
                value=value
            ))
            return result
        
        local, domain = value.rsplit('@', 1)
        
        # Local part checks
        if len(local) > 64:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} local part exceeds 64 characters",
                value=value
            ))
        
        if local.startswith('.') or local.endswith('.') or '..' in local:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} has invalid dot placement",
                value=value
            ))
        
        # Domain checks
        if len(domain) > 253:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} domain part exceeds 253 characters",
                value=value
            ))
        
        if domain.startswith('.') or domain.endswith('.') or '..' in domain:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} has invalid domain format",
                value=value
            ))
        
        return result


class URLValidator(PropertyValidator):
    """Validator for URL properties."""
    
    ALLOWED_SCHEMES = ['http', 'https']
    URL_REGEX = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not isinstance(value, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a string",
                value=value,
                context={"expected_type": "str", "actual_type": type(value).__name__}
            ))
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, str):
            return result
        
        # Length check
        if len(value) > 2048:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} exceeds maximum URL length of 2048",
                value=value
            ))
            return result
        
        # Basic format check
        if not self.URL_REGEX.match(value):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} is not a valid URL format",
                value=value
            ))
            return result
        
        # Parse URL
        try:
            parsed = urlparse(value)
            
            if parsed.scheme not in self.ALLOWED_SCHEMES:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} must use http or https scheme",
                    value=value,
                    context={"scheme": parsed.scheme, "allowed": self.ALLOWED_SCHEMES}
                ))
            
            if not parsed.netloc:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} must have a valid hostname",
                    value=value
                ))
                
        except Exception as e:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} URL parsing failed: {str(e)}",
                value=value
            ))
        
        return result
    
    def _validate_security(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, str):
            return result
        
        # Check for suspicious patterns
        suspicious_patterns = [
            (r'@', 'contains @ symbol (potential phishing)'),
            (r'\.\.', 'contains directory traversal pattern'),
            (r'%00', 'contains null byte'),
            (r'%0[dD]%0[aA]', 'contains CRLF injection pattern'),
            (r'<script', 'contains potential XSS'),
            (r'javascript:', 'contains javascript protocol'),
            (r'data:', 'contains data protocol'),
        ]
        
        for pattern, description in suspicious_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.SECURITY_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} {description}",
                    value=value,
                    context={"pattern": pattern}
                ))
        
        return result


class DateValidator(PropertyValidator):
    """Validator for date properties."""
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, (str, datetime, date)):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a date string, datetime, or date object",
                value=value,
                context={"expected_types": ["str", "datetime", "date"], 
                        "actual_type": type(value).__name__}
            ))
        
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if isinstance(value, str):
            # Try to parse the date string
            try:
                # Handle ISO format with Z suffix
                if value.endswith('Z'):
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    datetime.fromisoformat(value)
            except ValueError:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name=self.field_name,
                    message=f"{self.field_name} is not a valid ISO date format",
                    value=value
                ))
        
        return result


class SelectValidator(PropertyValidator):
    """Validator for select/enum properties."""
    
    def __init__(self,
                 field_name: str,
                 allowed_values: Optional[List[str]] = None,
                 case_sensitive: bool = True,
                 **kwargs):
        super().__init__(field_name, **kwargs)
        self.allowed_values = allowed_values or []
        self.case_sensitive = case_sensitive
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not isinstance(value, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a string",
                value=value,
                context={"expected_type": "str", "actual_type": type(value).__name__}
            ))
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, str):
            return result
        
        if self.allowed_values:
            if self.case_sensitive:
                if value not in self.allowed_values:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.FORMAT_ERROR,
                        field_name=self.field_name,
                        message=f"{self.field_name} must be one of: {', '.join(self.allowed_values)}",
                        value=value,
                        context={"allowed_values": self.allowed_values}
                    ))
            else:
                lower_allowed = [v.lower() for v in self.allowed_values]
                if value.lower() not in lower_allowed:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.FORMAT_ERROR,
                        field_name=self.field_name,
                        message=f"{self.field_name} must be one of: {', '.join(self.allowed_values)}",
                        value=value,
                        context={"allowed_values": self.allowed_values}
                    ))
        
        return result


class BooleanValidator(PropertyValidator):
    """Validator for boolean/checkbox properties."""
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not isinstance(value, bool):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a boolean",
                value=value,
                context={"expected_type": "bool", "actual_type": type(value).__name__}
            ))
        return result


class ListValidator(PropertyValidator):
    """Validator for list properties (multi-select, people, files, relations)."""
    
    def __init__(self,
                 field_name: str,
                 item_validator: Optional[PropertyValidator] = None,
                 min_items: int = 0,
                 max_items: Optional[int] = None,
                 unique_items: bool = False,
                 **kwargs):
        super().__init__(field_name, **kwargs)
        self.item_validator = item_validator
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
    
    def _validate_type(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not isinstance(value, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must be a list",
                value=value,
                context={"expected_type": "list", "actual_type": type(value).__name__}
            ))
        return result
    
    def _validate_format(self, value: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, list):
            return result
        
        # Length validation
        if len(value) < self.min_items:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must have at least {self.min_items} items",
                value=value,
                context={"min_items": self.min_items, "actual_count": len(value)}
            ))
        
        if self.max_items is not None and len(value) > self.max_items:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must have at most {self.max_items} items",
                value=value,
                context={"max_items": self.max_items, "actual_count": len(value)}
            ))
        
        # Uniqueness validation
        if self.unique_items and len(value) != len(set(str(v) for v in value)):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=self.field_name,
                message=f"{self.field_name} must contain unique items",
                value=value
            ))
        
        # Item validation
        if self.item_validator:
            for i, item in enumerate(value):
                item_result = self.item_validator.validate(item)
                if not item_result.is_valid:
                    for error in item_result.errors:
                        error.field_name = f"{self.field_name}[{i}]"
                        result.add_error(error)
        
        return result


class PropertyValidatorFactory:
    """Factory for creating property validators."""
    
    @staticmethod
    def create_validator(property_type: str, 
                        field_name: str,
                        config: Optional[Dict[str, Any]] = None,
                        validation_level: ValidationLevel = ValidationLevel.STANDARD) -> PropertyValidator:
        """Create a validator for a property type.
        
        Args:
            property_type: Notion property type
            field_name: Field name for error messages
            config: Optional configuration for the validator
            validation_level: Validation strictness level
            
        Returns:
            PropertyValidator instance
        """
        config = config or {}
        # Remove 'type' from config if present
        clean_config = {k: v for k, v in config.items() if k != 'type'}
        clean_config['validation_level'] = validation_level
        clean_config['field_name'] = field_name
        
        validators = {
            'title': lambda: TextValidator(**clean_config),
            'rich_text': lambda: TextValidator(**clean_config),
            'number': lambda: NumberValidator(**clean_config),
            'select': lambda: SelectValidator(**clean_config),
            'multi_select': lambda: ListValidator(
                item_validator=TextValidator(f"{field_name}_item", required=True),
                **clean_config
            ),
            'date': lambda: DateValidator(**clean_config),
            'checkbox': lambda: BooleanValidator(**clean_config),
            'email': lambda: EmailValidator(**clean_config),
            'phone_number': lambda: TextValidator(
                pattern=r'.*\d+.*',  # Must contain at least one digit
                **clean_config
            ),
            'url': lambda: URLValidator(**clean_config),
            'people': lambda: ListValidator(
                item_validator=TextValidator(f"{field_name}_item", required=True),
                **clean_config
            ),
            'files': lambda: ListValidator(
                item_validator=URLValidator(f"{field_name}_item", required=True),
                **clean_config
            ),
            'relation': lambda: ListValidator(
                item_validator=TextValidator(f"{field_name}_item", required=True),
                **clean_config
            ),
        }
        
        if property_type not in validators:
            raise ValueError(f"Unsupported property type: {property_type}")
        
        return validators[property_type]()


def validate_property_value(property_type: str,
                          field_name: str, 
                          value: Any,
                          config: Optional[Dict[str, Any]] = None,
                          validation_level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
    """Convenience function to validate a property value.
    
    Args:
        property_type: Notion property type
        field_name: Field name for error messages
        value: Value to validate
        config: Optional configuration for the validator
        validation_level: Validation strictness level
        
    Returns:
        ValidationResult
    """
    validator = PropertyValidatorFactory.create_validator(
        property_type, field_name, config, validation_level
    )
    return validator.validate(value)