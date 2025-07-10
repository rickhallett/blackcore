"""Unit tests for error handling functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from blackcore.errors.handlers import (
    ErrorHandler,
    ErrorContext,
    BaseNotionError,
    NotionAPIError,
    RateLimitError,
    ValidationError,
    PropertyError,
    SyncError,
    ErrorSeverity,
    ErrorCategory,
)


class TestErrorContext:
    """Test error context functionality."""

    def test_error_context_creation(self):
        """Test creating error context."""
        context = ErrorContext(
            operation="test_operation",
            resource_type="page",
            resource_id="123",
            request_data={"key": "value"},
            correlation_id="corr-123",
        )

        assert context.operation == "test_operation"
        assert context.resource_type == "page"
        assert context.resource_id == "123"
        assert context.request_data == {"key": "value"}
        assert context.correlation_id == "corr-123"
        assert isinstance(context.timestamp, datetime)

    def test_error_context_to_dict(self):
        """Test converting error context to dictionary."""
        context = ErrorContext(operation="test_operation", resource_type="page")

        context_dict = context.to_dict()
        assert context_dict["operation"] == "test_operation"
        assert context_dict["resource_type"] == "page"
        assert "timestamp" in context_dict


class TestBaseNotionError:
    """Test base error functionality."""

    def test_base_error_creation(self):
        """Test creating base error."""
        error = BaseNotionError(
            message="Test error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API,
            retryable=True,
        )

        assert error.message == "Test error"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.API
        assert error.retryable is True
        assert isinstance(error.timestamp, datetime)

    def test_error_with_context(self):
        """Test error with context."""
        context = ErrorContext(operation="test_op", resource_id="123")
        error = BaseNotionError(message="Test error", context=context)

        assert error.context == context
        assert error.context.operation == "test_op"

    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        context = ErrorContext(operation="test_op")
        error = BaseNotionError(
            message="Test error",
            context=context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
        )

        error_dict = error.to_dict()
        assert error_dict["error_type"] == "BaseNotionError"
        assert error_dict["error_message"] == "Test error"
        assert error_dict["severity"] == "medium"
        assert error_dict["category"] == "validation"
        assert error_dict["context"]["operation"] == "test_op"


class TestSpecificErrors:
    """Test specific error types."""

    def test_notion_api_error(self):
        """Test NotionAPIError creation and properties."""
        error = NotionAPIError(
            message="API error",
            status_code=429,
            error_code="rate_limited",
            response_body='{"error": "rate limited"}',
        )

        assert error.status_code == 429
        assert error.error_code == "rate_limited"
        assert error.retryable is True  # 429 is retryable
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.API

    def test_notion_api_error_severity(self):
        """Test that API errors have appropriate severity."""
        # 401 should be critical
        error_401 = NotionAPIError("Unauthorized", status_code=401)
        assert error_401.severity == ErrorSeverity.CRITICAL

        # 429 should be high
        error_429 = NotionAPIError("Rate limited", status_code=429)
        assert error_429.severity == ErrorSeverity.HIGH

        # 500+ should be high
        error_500 = NotionAPIError("Server error", status_code=500)
        assert error_500.severity == ErrorSeverity.HIGH

        # Others should be medium
        error_400 = NotionAPIError("Bad request", status_code=400)
        assert error_400.severity == ErrorSeverity.MEDIUM

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(message="Rate limit exceeded", retry_after=60.0)

        assert error.retry_after == 60.0
        assert error.status_code == 429
        assert error.retryable is True
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(message="Invalid email format", field="email", value="not-an-email")

        assert error.field == "email"
        assert error.value == "not-an-email"
        assert error.retryable is False
        assert error.severity == ErrorSeverity.LOW
        assert error.category == ErrorCategory.VALIDATION

    def test_property_error(self):
        """Test PropertyError."""
        error = PropertyError(
            message="Invalid property value", property_name="Due Date", property_type="date"
        )

        assert error.property_name == "Due Date"
        assert error.property_type == "date"
        assert error.category == ErrorCategory.PROPERTY

    def test_sync_error(self):
        """Test SyncError."""
        error = SyncError(message="Sync failed", phase="validation", partial_success=True)

        assert error.phase == "validation"
        assert error.partial_success is True
        assert error.category == ErrorCategory.SYNC
        assert error.retryable is True


class TestErrorHandler:
    """Test error handler functionality."""

    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        assert hasattr(handler, "audit_logger")
        assert hasattr(handler, "_context_stack")
        assert handler._error_counts == {}
        assert handler._error_history == []

    def test_error_context_manager(self):
        """Test error context management."""
        handler = ErrorHandler()

        with handler.error_context(operation="test", resource_id="123") as context:
            assert context.operation == "test"
            assert context.resource_id == "123"

            # Context should be available
            current = handler.get_current_context()
            assert current == context

        # Context should be cleared
        assert handler.get_current_context() is None

    def test_nested_error_contexts(self):
        """Test nested error contexts."""
        handler = ErrorHandler()

        with handler.error_context(operation="outer") as outer_ctx:
            assert handler.get_current_context().operation == "outer"

            with handler.error_context(operation="inner") as inner_ctx:
                assert handler.get_current_context().operation == "inner"

            # Should return to outer context
            assert handler.get_current_context().operation == "outer"

    @patch("blackcore.errors.handlers.AuditLogger")
    def test_handle_error_with_notion_error(self, mock_audit_logger):
        """Test handling a NotionError."""
        handler = ErrorHandler(audit_logger=mock_audit_logger())

        original_error = NotionAPIError("API failed", status_code=500)

        with pytest.raises(NotionAPIError) as exc_info:
            handler.handle_error(original_error, reraise=True)

        assert exc_info.value == original_error

        # Should log the error
        handler.audit_logger.log_error.assert_called_once()

    @patch("blackcore.errors.handlers.AuditLogger")
    def test_handle_error_with_generic_exception(self, mock_audit_logger):
        """Test handling a generic exception."""
        handler = ErrorHandler(audit_logger=mock_audit_logger())

        original_error = ValueError("Something went wrong")

        with pytest.raises(BaseNotionError) as exc_info:
            handler.handle_error(original_error, reraise=True)

        # Should wrap in BaseNotionError
        assert isinstance(exc_info.value, BaseNotionError)
        assert "Something went wrong" in str(exc_info.value)

    def test_wrap_error_rate_limit_detection(self):
        """Test that rate limit errors are detected from text."""
        handler = ErrorHandler()

        # Create generic error with rate limit text
        error = Exception("Rate limit exceeded, please try again")
        wrapped = handler._wrap_error(error, None)

        assert isinstance(wrapped, RateLimitError)

    def test_wrap_error_validation_detection(self):
        """Test that validation errors are detected from text."""
        handler = ErrorHandler()

        # Create generic error with validation text
        error = Exception("Invalid value for property")
        wrapped = handler._wrap_error(error, None)

        assert isinstance(wrapped, ValidationError)

    def test_error_statistics(self):
        """Test error statistics tracking."""
        handler = ErrorHandler()

        # Generate some errors
        errors = [
            NotionAPIError("Error 1", status_code=500),
            NotionAPIError("Error 2", status_code=500),
            ValidationError("Error 3"),
            RateLimitError("Error 4"),
        ]

        for error in errors:
            handler.handle_error(error, reraise=False)

        stats = handler.get_error_stats()

        assert stats["total_errors"] == 4
        assert stats["error_counts"]["NotionAPIError"] == 2
        assert stats["error_counts"]["ValidationError"] == 1
        assert stats["error_counts"]["RateLimitError"] == 1
        assert stats["retryable_errors"] == 3  # API errors and rate limit
        assert stats["non_retryable_errors"] == 1  # Validation

    def test_should_retry_logic(self):
        """Test retry decision logic."""
        handler = ErrorHandler()

        # Retryable error should be retried
        error = RateLimitError("Rate limited")
        assert handler.should_retry(error) is True

        # Non-retryable error should not be retried
        error = ValidationError("Invalid value")
        assert handler.should_retry(error) is False

        # Too many of the same error should stop retries
        for _ in range(10):
            handler._error_history.append(RateLimitError("Rate limited"))

        error = RateLimitError("Rate limited")
        assert handler.should_retry(error) is False

    def test_user_friendly_messages(self):
        """Test generation of user-friendly error messages."""
        handler = ErrorHandler()

        # Rate limit error
        error = RateLimitError("Rate limit", retry_after=60)
        message = handler.create_user_friendly_message(error)
        assert "Please wait 60 seconds" in message

        # Validation error with field
        error = ValidationError("Bad format", field="email")
        message = handler.create_user_friendly_message(error)
        assert "Invalid value for field 'email'" in message

        # API errors
        error = NotionAPIError("Unauthorized", status_code=401)
        message = handler.create_user_friendly_message(error)
        assert "check your API key" in message

        error = NotionAPIError("Forbidden", status_code=403)
        message = handler.create_user_friendly_message(error)
        assert "check your permissions" in message

        error = NotionAPIError("Not found", status_code=404)
        message = handler.create_user_friendly_message(error)
        assert "not found" in message.lower()

        error = NotionAPIError("Server error", status_code=500)
        message = handler.create_user_friendly_message(error)
        assert "try again later" in message.lower()
