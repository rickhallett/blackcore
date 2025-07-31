"""Test standardized error handling patterns."""

import pytest
from unittest.mock import patch, MagicMock

from blackcore.minimal.error_handling import (
    ErrorHandler,
    BlackcoreError,
    NotionAPIError,
    ValidationError,
    ProcessingError,
    ConfigurationError,
    handle_errors,
    retry_on_error,
    ErrorContext
)


class TestBlackcoreExceptions:
    """Test custom exception hierarchy."""
    
    def test_blackcore_error_base(self):
        """Test base BlackcoreError exception."""
        error = BlackcoreError("Test error", context={"key": "value"})
        assert str(error) == "Test error"
        assert error.context == {"key": "value"}
        assert error.error_code is None
    
    def test_notion_api_error(self):
        """Test NotionAPIError with API-specific details."""
        error = NotionAPIError(
            "API request failed",
            error_code="rate_limited",
            status_code=429,
            context={"endpoint": "/pages"}
        )
        assert error.error_code == "rate_limited"
        assert error.status_code == 429
        assert error.context == {"endpoint": "/pages"}
    
    def test_validation_error(self):
        """Test ValidationError with field details."""
        error = ValidationError(
            "Invalid property value",
            field_name="title",
            field_value="",
            context={"property_type": "rich_text"}
        )
        assert error.field_name == "title"
        assert error.field_value == ""
    
    def test_processing_error(self):
        """Test ProcessingError with processing details."""
        error = ProcessingError(
            "Failed to process entity",
            entity_type="person",
            context={"transcript_id": "123"}
        )
        assert error.entity_type == "person"
    
    def test_configuration_error(self):
        """Test ConfigurationError with config details."""
        error = ConfigurationError(
            "Missing API key",
            config_key="notion_api_key",
            context={"config_file": ".env"}
        )
        assert error.config_key == "notion_api_key"


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    def test_error_handler_init(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler(
            context={"module": "test"},
            log_errors=True,
            raise_on_critical=True
        )
        assert handler.context == {"module": "test"}
        assert handler.log_errors is True
        assert handler.raise_on_critical is True
    
    def test_handle_error_logging(self):
        """Test error handling with logging."""
        with patch('blackcore.minimal.error_handling.log_error') as mock_log_error:
            handler = ErrorHandler(log_errors=True)
            
            error = ValidationError("Test error", field_name="test")
            result = handler.handle_error(error)
            
            # Should log the error
            mock_log_error.assert_called_once()
            # Should return the error for further handling
            assert result is error
    
    def test_handle_error_critical_raises(self):
        """Test critical error handling raises exception."""
        handler = ErrorHandler(raise_on_critical=True)
        
        critical_error = NotionAPIError(
            "Critical API error",
            error_code="unauthorized",
            status_code=401
        )
        
        with pytest.raises(NotionAPIError):
            handler.handle_error(critical_error, critical=True)
    
    def test_handle_error_non_critical_returns(self):
        """Test non-critical error handling returns error."""
        handler = ErrorHandler(raise_on_critical=False)
        
        error = ValidationError("Non-critical error")
        result = handler.handle_error(error, critical=False)
        
        assert result is error
    
    def test_with_context(self):
        """Test context manager functionality."""
        handler = ErrorHandler(context={"base": "value"})
        
        with handler.with_context(operation="test", entity_id="123") as ctx_handler:
            assert ctx_handler.context == {
                "base": "value",
                "operation": "test",
                "entity_id": "123"
            }
        
        # Original context should be restored
        assert handler.context == {"base": "value"}
    
    def test_is_retryable_error(self):
        """Test retryable error detection."""
        handler = ErrorHandler()
        
        # Rate limited should be retryable
        rate_error = NotionAPIError("Rate limited", error_code="rate_limited")
        assert handler.is_retryable(rate_error) is True
        
        # Connection errors should be retryable
        connection_error = NotionAPIError("Connection failed", status_code=503)
        assert handler.is_retryable(connection_error) is True
        
        # Authorization errors should not be retryable
        auth_error = NotionAPIError("Unauthorized", error_code="unauthorized")
        assert handler.is_retryable(auth_error) is False
        
        # Validation errors should not be retryable
        validation_error = ValidationError("Invalid input")
        assert handler.is_retryable(validation_error) is False


class TestHandleErrorsDecorator:
    """Test @handle_errors decorator."""
    
    def test_handle_errors_success(self):
        """Test decorator allows successful execution."""
        @handle_errors()
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_handle_errors_catches_and_logs(self):
        """Test decorator catches and logs errors."""
        with patch('blackcore.minimal.error_handling.log_error') as mock_log_error:
            @handle_errors(log_errors=True)
            def failing_function():
                raise ValueError("Test error")
            
            result = failing_function()
            
            # Should log the error
            mock_log_error.assert_called_once()
            # Should return None by default
            assert result is None
    
    def test_handle_errors_with_default_return(self):
        """Test decorator with custom default return value."""
        @handle_errors(default_return="default")
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result == "default"
    
    def test_handle_errors_reraise(self):
        """Test decorator can reraise exceptions."""
        @handle_errors(reraise=True)
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
    
    def test_handle_errors_with_context(self):
        """Test decorator adds context to errors."""
        with patch('blackcore.minimal.error_handling.log_error') as mock_log_error:
            @handle_errors(
                context={"function": "test"},
                convert_to=ProcessingError
            )
            def failing_function():
                raise ValueError("Test error")
            
            result = failing_function()
            
            # Should log with context
            mock_log_error.assert_called_once()
            call_args = mock_log_error.call_args
            assert "function" in str(call_args)


class TestRetryOnErrorDecorator:
    """Test @retry_on_error decorator."""
    
    def test_retry_on_error_success_first_try(self):
        """Test decorator doesn't retry on success."""
        call_count = 0
        
        @retry_on_error(max_attempts=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_error_retries_retryable(self):
        """Test decorator retries retryable errors."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.01)
        def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NotionAPIError("Rate limited", error_code="rate_limited")
            return "success"
        
        result = failing_then_succeeding()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_on_error_no_retry_non_retryable(self):
        """Test decorator doesn't retry non-retryable errors."""
        call_count = 0
        
        @retry_on_error(max_attempts=3)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Invalid input")
        
        with pytest.raises(ValidationError):
            failing_function()
        
        assert call_count == 1
    
    def test_retry_on_error_max_attempts_reached(self):
        """Test decorator gives up after max attempts."""
        call_count = 0
        
        @retry_on_error(max_attempts=2, delay=0.01)
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise NotionAPIError("Rate limited", error_code="rate_limited")
        
        with pytest.raises(NotionAPIError):
            always_failing()
        
        assert call_count == 2


class TestErrorContext:
    """Test ErrorContext context manager."""
    
    def test_error_context_success(self):
        """Test context manager with successful operation."""
        with ErrorContext("test_operation", entity_id="123"):
            # Should complete successfully
            pass
    
    def test_error_context_enhances_blackcore_errors(self):
        """Test context manager enhances BlackcoreError exceptions."""
        try:
            with ErrorContext("test_operation", entity_id="123"):
                raise ValidationError("Test error")
        except ValidationError as e:
            assert e.context["operation"] == "test_operation"
            assert e.context["entity_id"] == "123"
    
    def test_error_context_converts_other_errors(self):
        """Test context manager converts other errors to ProcessingError."""
        try:
            with ErrorContext("test_operation", entity_id="123"):
                raise ValueError("Test error")
        except ProcessingError as e:
            assert "Test error" in str(e)
            assert e.context["operation"] == "test_operation"
            assert e.context["entity_id"] == "123"
            assert e.context["original_error"] == "ValueError"
    
    def test_error_context_with_custom_error_type(self):
        """Test context manager with custom error type."""
        try:
            with ErrorContext(
                "test_operation",
                convert_to=NotionAPIError,
                entity_id="123"
            ):
                raise ValueError("Test error")
        except NotionAPIError as e:
            assert "Test error" in str(e)
            assert e.context["operation"] == "test_operation"