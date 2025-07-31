"""Test structured logging implementation."""

import logging
import json
from unittest.mock import patch, MagicMock
import pytest

from blackcore.minimal.logging_config import (
    setup_logging,
    get_logger,
    StructuredFormatter,
    log_event,
    log_error,
    log_performance,
)


class TestStructuredLogging:
    """Test suite for structured logging."""
    
    def test_setup_logging_configures_handlers(self):
        """Test that setup_logging properly configures handlers."""
        # Setup logging with JSON format
        setup_logging(format="json", level="DEBUG")
        
        # Get the root logger
        root_logger = logging.getLogger()
        
        # Should have at least one handler
        assert len(root_logger.handlers) > 0
        
        # Handler should have the correct level
        assert root_logger.level == logging.DEBUG
    
    def test_structured_formatter_json_format(self):
        """Test StructuredFormatter outputs valid JSON."""
        formatter = StructuredFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        
        # Check required fields
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["module"] == "test"
        assert parsed["line"] == 42
        assert "timestamp" in parsed
    
    def test_structured_formatter_with_extra_fields(self):
        """Test that extra fields are included in JSON output."""
        formatter = StructuredFormatter()
        
        # Create a log record with extra fields
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.user_id = "12345"
        record.action = "create_page"
        record.database_id = "abc-def-123"
        
        # Format the record
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        # Extra fields should be included
        assert parsed["user_id"] == "12345"
        assert parsed["action"] == "create_page"
        assert parsed["database_id"] == "abc-def-123"
    
    def test_structured_formatter_with_exception(self):
        """Test that exceptions are properly formatted."""
        formatter = StructuredFormatter()
        
        # Create an exception
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        # Create a log record with exception
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        # Format the record
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        # Should include exception info
        assert "exception" in parsed
        assert "ValueError: Test error" in parsed["exception"]
    
    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns properly configured logger."""
        # Setup logging
        setup_logging(format="json")
        
        # Get a logger
        logger = get_logger("test.module")
        
        # Should be a logger instance
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
    
    def test_log_event_helper(self):
        """Test log_event helper function."""
        with patch('blackcore.minimal.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Log an event
            log_event(
                "test.module",
                "page_created",
                page_id="123",
                database_id="456",
                title="Test Page"
            )
            
            # Should call info with correct message and extra fields
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            
            assert call_args[0][0] == "page_created"
            assert call_args[1]["extra"]["page_id"] == "123"
            assert call_args[1]["extra"]["database_id"] == "456"
            assert call_args[1]["extra"]["title"] == "Test Page"
    
    def test_log_error_helper(self):
        """Test log_error helper function."""
        with patch('blackcore.minimal.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Create an exception
            error = ValueError("Test error")
            
            # Log an error
            log_error(
                "test.module",
                "database_error",
                error,
                database_id="123",
                operation="create"
            )
            
            # Should call error with correct message and extra fields
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            
            assert call_args[0][0] == "database_error: Test error"
            assert call_args[1]["exc_info"] == True
            assert call_args[1]["extra"]["database_id"] == "123"
            assert call_args[1]["extra"]["operation"] == "create"
            assert call_args[1]["extra"]["error_type"] == "ValueError"
    
    def test_log_performance_helper(self):
        """Test log_performance helper function."""
        with patch('blackcore.minimal.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Log performance metrics
            log_performance(
                "test.module",
                "api_call",
                duration_ms=150.5,
                endpoint="/v1/pages",
                method="POST",
                status_code=200
            )
            
            # Should call info with correct message and extra fields
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            
            assert call_args[0][0] == "api_call completed in 150.5ms"
            assert call_args[1]["extra"]["duration_ms"] == 150.5
            assert call_args[1]["extra"]["endpoint"] == "/v1/pages"
            assert call_args[1]["extra"]["method"] == "POST"
            assert call_args[1]["extra"]["status_code"] == 200
    
    def test_setup_logging_with_file_output(self, tmp_path):
        """Test logging to file."""
        log_file = tmp_path / "test.log"
        
        # Setup logging with file output
        setup_logging(format="json", level="INFO", log_file=str(log_file))
        
        # Log a message
        logger = get_logger("test")
        logger.info("Test message", extra={"key": "value"})
        
        # Check file contents
        assert log_file.exists()
        
        with open(log_file) as f:
            line = f.readline()
            parsed = json.loads(line)
            
            assert parsed["message"] == "Test message"
            assert parsed["key"] == "value"
    
    def test_structured_logging_filters_sensitive_data(self):
        """Test that sensitive data is filtered from logs."""
        formatter = StructuredFormatter()
        
        # Create a log record with sensitive data
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="API call",
            args=(),
            exc_info=None
        )
        
        # Add fields with sensitive data
        record.api_key = "secret_abcdef123456"
        record.password = "my_password"
        record.headers = {"Authorization": "Bearer token123"}
        
        # Format the record
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        # Sensitive data should be masked
        assert parsed.get("api_key") == "[REDACTED]"
        assert parsed.get("password") == "[REDACTED]"
        assert parsed.get("headers", {}).get("Authorization") == "[REDACTED]"
    
    def test_context_manager_for_log_context(self):
        """Test context manager for adding log context."""
        from blackcore.minimal.logging_config import log_context, StructuredFormatter
        
        # Create a custom handler to capture logs
        captured_logs = []
        
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                formatter = StructuredFormatter()
                captured_logs.append(json.loads(formatter.format(record)))
        
        # Setup test logger
        logger = get_logger("test.context")
        logger.handlers.clear()
        handler = CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Use context manager
        with log_context(request_id="123", user_id="456"):
            logger.info("Inside context")
        
        # Check that context fields were added
        assert len(captured_logs) == 1
        log_entry = captured_logs[0]
        assert log_entry["message"] == "Inside context"
        assert log_entry["request_id"] == "123"
        assert log_entry["user_id"] == "456"