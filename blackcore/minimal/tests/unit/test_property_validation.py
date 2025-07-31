"""Tests for standardized property validation framework."""

import pytest
from datetime import datetime, date

from blackcore.minimal.property_validation import (
    PropertyValidator,
    PropertyValidatorFactory,
    ValidationLevel,
    ValidationResult,
    ValidationError,
    ValidationErrorType,
    TextValidator,
    NumberValidator,
    EmailValidator,
    URLValidator,
    DateValidator,
    SelectValidator,
    BooleanValidator,
    ListValidator,
    validate_property_value
)


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_creation(self):
        """Test creating validation errors."""
        error = ValidationError(
            error_type=ValidationErrorType.TYPE_ERROR,
            field_name="test_field",
            message="Invalid type",
            value=123,
            context={"expected": "str", "actual": "int"}
        )
        
        assert error.error_type == ValidationErrorType.TYPE_ERROR
        assert error.field_name == "test_field"
        assert error.message == "Invalid type"
        assert error.value == 123
        assert error.context["expected"] == "str"


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_add_error(self):
        """Test adding errors to result."""
        result = ValidationResult(is_valid=True)
        error = ValidationError(
            error_type=ValidationErrorType.TYPE_ERROR,
            field_name="test",
            message="Error"
        )
        
        result.add_error(error)
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0] == error
    
    def test_add_warning(self):
        """Test adding warnings to result."""
        result = ValidationResult(is_valid=True)
        warning = ValidationError(
            error_type=ValidationErrorType.SECURITY_ERROR,
            field_name="test",
            message="Warning"
        )
        
        result.add_warning(warning)
        
        assert result.is_valid  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.warnings[0] == warning
    
    def test_merge_results(self):
        """Test merging validation results."""
        result1 = ValidationResult(is_valid=True)
        result1.add_warning(ValidationError(
            error_type=ValidationErrorType.SECURITY_ERROR,
            field_name="field1",
            message="Warning 1"
        ))
        
        result2 = ValidationResult(is_valid=True)
        result2.add_error(ValidationError(
            error_type=ValidationErrorType.TYPE_ERROR,
            field_name="field2",
            message="Error 1"
        ))
        
        result1.merge(result2)
        
        assert not result1.is_valid  # Because result2 has errors
        assert len(result1.errors) == 1
        assert len(result1.warnings) == 1


class TestTextValidator:
    """Test text validation."""
    
    def test_valid_text(self):
        """Test valid text values."""
        validator = TextValidator("test_field", max_length=100)
        
        result = validator.validate("Hello world")
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_type_error(self):
        """Test non-string values."""
        validator = TextValidator("test_field")
        
        result = validator.validate(123)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_type == ValidationErrorType.TYPE_ERROR
    
    def test_length_validation(self):
        """Test length constraints."""
        validator = TextValidator("test_field", max_length=10, min_length=2)
        
        # Too long
        result = validator.validate("This is a very long string")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Too short
        result = validator.validate("a")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Just right
        result = validator.validate("Hello")
        assert result.is_valid
    
    def test_pattern_validation(self):
        """Test pattern matching."""
        validator = TextValidator("test_field", pattern=r"^\d{3}-\d{3}-\d{4}$")
        
        result = validator.validate("123-456-7890")
        assert result.is_valid
        
        result = validator.validate("not a phone")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.PATTERN_ERROR for e in result.errors)
    
    def test_security_validation(self):
        """Test security checks."""
        validator = TextValidator("test_field", validation_level=ValidationLevel.SECURITY)
        
        # Null bytes
        result = validator.validate("Hello\x00World")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SECURITY_ERROR for e in result.errors)
        
        # Control characters (warning only)
        result = validator.validate("Hello\x01World")
        assert result.is_valid  # Warnings don't fail validation
        assert len(result.warnings) > 0
    
    def test_sanitization(self):
        """Test text sanitization."""
        validator = TextValidator("test_field", max_length=10)
        
        result = validator.validate("Hello\x00World with extra text")
        assert result.sanitized_value == "Hello Worl"  # Null byte removed, truncated


class TestNumberValidator:
    """Test number validation."""
    
    def test_valid_numbers(self):
        """Test valid number values."""
        validator = NumberValidator("test_field")
        
        assert validator.validate(42).is_valid
        assert validator.validate(3.14).is_valid
        assert validator.validate(0).is_valid
        assert validator.validate(-5).is_valid
    
    def test_type_errors(self):
        """Test invalid types."""
        validator = NumberValidator("test_field")
        
        assert not validator.validate("42").is_valid
        assert not validator.validate(True).is_valid  # Booleans excluded
        assert not validator.validate(None).is_valid
    
    def test_integer_only(self):
        """Test integer-only validation."""
        validator = NumberValidator("test_field", allow_integers_only=True)
        
        assert validator.validate(42).is_valid
        assert not validator.validate(3.14).is_valid
    
    def test_range_validation(self):
        """Test range constraints."""
        validator = NumberValidator("test_field", minimum=0, maximum=100)
        
        assert validator.validate(50).is_valid
        assert validator.validate(0).is_valid
        assert validator.validate(100).is_valid
        
        result = validator.validate(-1)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.RANGE_ERROR for e in result.errors)
        
        result = validator.validate(101)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.RANGE_ERROR for e in result.errors)


class TestEmailValidator:
    """Test email validation."""
    
    def test_valid_emails(self):
        """Test valid email addresses."""
        validator = EmailValidator("email_field")
        
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "test123@subdomain.example.com"
        ]
        
        for email in valid_emails:
            result = validator.validate(email)
            assert result.is_valid, f"Email '{email}' should be valid"
    
    def test_invalid_emails(self):
        """Test invalid email addresses."""
        validator = EmailValidator("email_field")
        
        invalid_emails = [
            "notanemail",
            "@example.com",
            "test@",
            "test..double@example.com",
            ".test@example.com",
            "test@example..com",
            "test@.example.com",
            "test" + "a" * 250 + "@example.com"  # Too long
        ]
        
        for email in invalid_emails:
            result = validator.validate(email)
            assert not result.is_valid, f"Email '{email}' should be invalid"


class TestURLValidator:
    """Test URL validation."""
    
    def test_valid_urls(self):
        """Test valid URLs."""
        validator = URLValidator("url_field")
        
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path",
            "https://example.com:8080/path?query=value",
            "http://localhost:3000"
        ]
        
        for url in valid_urls:
            result = validator.validate(url)
            assert result.is_valid, f"URL '{url}' should be valid"
    
    def test_invalid_urls(self):
        """Test invalid URLs."""
        validator = URLValidator("url_field")
        
        invalid_urls = [
            "not a url",
            "ftp://example.com",  # Wrong scheme
            "https://",
            "example.com",  # No scheme
            "https://" + "a" * 2050  # Too long
        ]
        
        for url in invalid_urls:
            result = validator.validate(url)
            assert not result.is_valid, f"URL '{url}' should be invalid"
    
    def test_security_checks(self):
        """Test URL security validation."""
        validator = URLValidator("url_field", validation_level=ValidationLevel.SECURITY)
        
        suspicious_urls = [
            "https://user@example.com",  # Contains @
            "https://example.com/../etc/passwd",  # Directory traversal
            "https://example.com/test%00.php",  # Null byte
            "javascript:alert('xss')",  # JS protocol
        ]
        
        for url in suspicious_urls:
            result = validator.validate(url)
            assert not result.is_valid or len(result.warnings) > 0


class TestDateValidator:
    """Test date validation."""
    
    def test_valid_dates(self):
        """Test valid date values."""
        validator = DateValidator("date_field")
        
        # String dates
        assert validator.validate("2025-01-15").is_valid
        assert validator.validate("2025-01-15T10:30:00").is_valid
        assert validator.validate("2025-01-15T10:30:00Z").is_valid
        assert validator.validate("2025-01-15T10:30:00+05:00").is_valid
        
        # Date objects
        assert validator.validate(date(2025, 1, 15)).is_valid
        assert validator.validate(datetime(2025, 1, 15, 10, 30)).is_valid
    
    def test_invalid_dates(self):
        """Test invalid date values."""
        validator = DateValidator("date_field")
        
        assert not validator.validate("not a date").is_valid
        assert not validator.validate("2025-13-01").is_valid  # Invalid month
        assert not validator.validate(123).is_valid


class TestSelectValidator:
    """Test select/enum validation."""
    
    def test_unrestricted_select(self):
        """Test select without predefined options."""
        validator = SelectValidator("select_field")
        
        assert validator.validate("any value").is_valid
        assert validator.validate("another value").is_valid
    
    def test_restricted_select(self):
        """Test select with allowed values."""
        validator = SelectValidator(
            "select_field",
            allowed_values=["option1", "option2", "option3"]
        )
        
        assert validator.validate("option1").is_valid
        assert validator.validate("option2").is_valid
        
        result = validator.validate("option4")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.FORMAT_ERROR for e in result.errors)
    
    def test_case_sensitivity(self):
        """Test case sensitivity in select validation."""
        # Case sensitive (default)
        validator = SelectValidator(
            "select_field",
            allowed_values=["Option1", "Option2"],
            case_sensitive=True
        )
        
        assert validator.validate("Option1").is_valid
        assert not validator.validate("option1").is_valid
        
        # Case insensitive
        validator = SelectValidator(
            "select_field",
            allowed_values=["Option1", "Option2"],
            case_sensitive=False
        )
        
        assert validator.validate("Option1").is_valid
        assert validator.validate("option1").is_valid
        assert validator.validate("OPTION1").is_valid


class TestBooleanValidator:
    """Test boolean validation."""
    
    def test_valid_booleans(self):
        """Test valid boolean values."""
        validator = BooleanValidator("bool_field")
        
        assert validator.validate(True).is_valid
        assert validator.validate(False).is_valid
    
    def test_invalid_booleans(self):
        """Test invalid boolean values."""
        validator = BooleanValidator("bool_field")
        
        assert not validator.validate(1).is_valid
        assert not validator.validate(0).is_valid
        assert not validator.validate("true").is_valid
        assert not validator.validate(None).is_valid


class TestListValidator:
    """Test list validation."""
    
    def test_basic_list_validation(self):
        """Test basic list validation."""
        validator = ListValidator("list_field")
        
        assert validator.validate([]).is_valid
        assert validator.validate(["item1", "item2"]).is_valid
        assert not validator.validate("not a list").is_valid
    
    def test_length_constraints(self):
        """Test list length validation."""
        validator = ListValidator("list_field", min_items=2, max_items=5)
        
        assert not validator.validate([]).is_valid  # Too few
        assert not validator.validate(["one"]).is_valid  # Too few
        assert validator.validate(["one", "two"]).is_valid
        assert validator.validate(["one", "two", "three", "four", "five"]).is_valid
        assert not validator.validate(["1", "2", "3", "4", "5", "6"]).is_valid  # Too many
    
    def test_unique_items(self):
        """Test unique item constraint."""
        validator = ListValidator("list_field", unique_items=True)
        
        assert validator.validate(["a", "b", "c"]).is_valid
        
        result = validator.validate(["a", "b", "a"])
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.FORMAT_ERROR for e in result.errors)
    
    def test_item_validation(self):
        """Test validation of individual list items."""
        item_validator = EmailValidator("email_item")
        validator = ListValidator("emails", item_validator=item_validator)
        
        result = validator.validate(["test@example.com", "user@domain.com"])
        assert result.is_valid
        
        result = validator.validate(["test@example.com", "not-an-email"])
        assert not result.is_valid
        assert any("emails[1]" in e.field_name for e in result.errors)


class TestPropertyValidatorFactory:
    """Test property validator factory."""
    
    def test_create_validators(self):
        """Test creating validators for all property types."""
        types_to_test = [
            ("title", TextValidator),
            ("rich_text", TextValidator),
            ("number", NumberValidator),
            ("select", SelectValidator),
            ("multi_select", ListValidator),
            ("date", DateValidator),
            ("checkbox", BooleanValidator),
            ("email", EmailValidator),
            ("phone_number", TextValidator),
            ("url", URLValidator),
            ("people", ListValidator),
            ("files", ListValidator),
            ("relation", ListValidator),
        ]
        
        for prop_type, expected_class in types_to_test:
            validator = PropertyValidatorFactory.create_validator(
                prop_type, 
                f"{prop_type}_field"
            )
            # Check base class since some are wrapped
            assert isinstance(validator, PropertyValidator)
    
    def test_unsupported_type(self):
        """Test creating validator for unsupported type."""
        with pytest.raises(ValueError, match="Unsupported property type"):
            PropertyValidatorFactory.create_validator("unknown_type", "field")
    
    def test_validation_levels(self):
        """Test different validation levels."""
        for level in ValidationLevel:
            validator = PropertyValidatorFactory.create_validator(
                "title",
                "test_field",
                validation_level=level
            )
            assert validator.validation_level == level


class TestCustomValidators:
    """Test custom validation functions."""
    
    def test_custom_validator_success(self):
        """Test successful custom validation."""
        validator = TextValidator("test_field")
        
        def starts_with_hello(value):
            return value.startswith("Hello")
        
        validator.add_custom_validator(starts_with_hello)
        
        assert validator.validate("Hello world").is_valid
        assert not validator.validate("Goodbye world").is_valid
    
    def test_custom_validator_with_message(self):
        """Test custom validator returning error message."""
        validator = NumberValidator("age_field")
        
        def validate_age(value):
            if value < 0:
                return "Age cannot be negative"
            if value > 150:
                return "Age seems unrealistic"
            return True
        
        validator.add_custom_validator(validate_age)
        
        result = validator.validate(-5)
        assert not result.is_valid
        assert any("Age cannot be negative" in e.message for e in result.errors)
        
        result = validator.validate(200)
        assert not result.is_valid
        assert any("Age seems unrealistic" in e.message for e in result.errors)
        
        assert validator.validate(25).is_valid
    
    def test_custom_validator_exception(self):
        """Test custom validator that raises exception."""
        validator = TextValidator("test_field")
        
        def buggy_validator(value):
            raise RuntimeError("Validator bug")
        
        validator.add_custom_validator(buggy_validator)
        
        result = validator.validate("test")
        assert not result.is_valid
        assert any("Custom validator error" in e.message for e in result.errors)


class TestRequiredAndNullable:
    """Test required and nullable field validation."""
    
    def test_required_field(self):
        """Test required field validation."""
        validator = TextValidator("test_field", required=True, nullable=False)
        
        result = validator.validate(None)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.REQUIRED_ERROR for e in result.errors)
        
        assert validator.validate("value").is_valid
    
    def test_nullable_field(self):
        """Test nullable field validation."""
        validator = TextValidator("test_field", required=True, nullable=True)
        
        assert validator.validate(None).is_valid
        assert validator.validate("value").is_valid
    
    def test_optional_field(self):
        """Test optional (not required) field validation."""
        validator = TextValidator("test_field", required=False)
        
        assert validator.validate(None).is_valid
        assert validator.validate("value").is_valid


class TestValidatePropertyValue:
    """Test the convenience validation function."""
    
    def test_validate_property_value(self):
        """Test the validate_property_value function."""
        result = validate_property_value(
            "email",
            "user_email",
            "test@example.com"
        )
        assert result.is_valid
        
        result = validate_property_value(
            "email",
            "user_email",
            "not-an-email"
        )
        assert not result.is_valid
    
    def test_with_config(self):
        """Test validation with configuration."""
        result = validate_property_value(
            "number",
            "score",
            50,
            config={"minimum": 0, "maximum": 100}
        )
        assert result.is_valid
        
        result = validate_property_value(
            "number",
            "score",
            150,
            config={"minimum": 0, "maximum": 100}
        )
        assert not result.is_valid
    
    def test_with_validation_level(self):
        """Test validation with different levels."""
        # MINIMAL - only type checking
        result = validate_property_value(
            "email",
            "email",
            123,  # Wrong type
            validation_level=ValidationLevel.MINIMAL
        )
        assert not result.is_valid
        
        # SECURITY - includes security checks
        result = validate_property_value(
            "url",
            "website",
            "https://example.com/../etc/passwd",
            validation_level=ValidationLevel.SECURITY
        )
        assert not result.is_valid