"""Structured logging configuration for the minimal module."""

import logging
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import threading
from contextlib import contextmanager

from . import constants


# Thread-local storage for context
_context = threading.local()


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    # Sensitive field names to redact
    SENSITIVE_FIELDS = {
        "api_key", "password", "token", "secret", "authorization",
        "api_token", "access_token", "refresh_token", "private_key"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Add any context from thread-local storage
        if hasattr(_context, 'data'):
            log_data.update(_context.data)
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "getMessage", "exc_info", "exc_text",
                "stack_info"
            }:
                # Redact sensitive fields
                if self._is_sensitive_field(key):
                    log_data[key] = "[REDACTED]"
                elif isinstance(value, dict) and key == "headers":
                    # Special handling for headers
                    log_data[key] = self._redact_headers(value)
                else:
                    log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name indicates sensitive data.
        
        Args:
            field_name: The field name to check
            
        Returns:
            True if the field should be redacted
        """
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.SENSITIVE_FIELDS)
    
    def _redact_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive headers.
        
        Args:
            headers: Dictionary of headers
            
        Returns:
            Headers with sensitive values redacted
        """
        redacted = {}
        for key, value in headers.items():
            if self._is_sensitive_field(key):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = value
        return redacted


def setup_logging(
    format: str = "json",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> None:
    """Configure structured logging for the application.
    
    Args:
        format: Log format ("json" or "text")
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Set the logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create formatter
    if format == "json":
        formatter = StructuredFormatter()
    else:
        # Traditional text format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Disable propagation for specific noisy loggers
    for logger_name in ["urllib3", "requests", "httpx"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_event(logger_name: str, event: str, **kwargs) -> None:
    """Log a structured event.
    
    Args:
        logger_name: Name of the logger to use
        event: Event name/type
        **kwargs: Additional fields to include in the log
    """
    logger = get_logger(logger_name)
    logger.info(event, extra=kwargs)


def log_error(
    logger_name: str,
    event: str,
    error: Exception,
    **kwargs
) -> None:
    """Log a structured error.
    
    Args:
        logger_name: Name of the logger to use
        event: Event name/type
        error: The exception that occurred
        **kwargs: Additional fields to include in the log
    """
    logger = get_logger(logger_name)
    kwargs["error_type"] = type(error).__name__
    logger.error(f"{event}: {str(error)}", exc_info=True, extra=kwargs)


def log_performance(
    logger_name: str,
    operation: str,
    duration_ms: float,
    **kwargs
) -> None:
    """Log performance metrics.
    
    Args:
        logger_name: Name of the logger to use
        operation: Operation name
        duration_ms: Duration in milliseconds
        **kwargs: Additional fields to include in the log
    """
    logger = get_logger(logger_name)
    kwargs["duration_ms"] = duration_ms
    logger.info(f"{operation} completed in {duration_ms}ms", extra=kwargs)


@contextmanager
def log_context(**kwargs):
    """Context manager to add fields to all logs within the context.
    
    Args:
        **kwargs: Fields to add to logs
        
    Example:
        with log_context(request_id="123", user_id="456"):
            logger.info("Processing request")  # Will include request_id and user_id
    """
    # Initialize thread-local data if needed
    if not hasattr(_context, 'data'):
        _context.data = {}
    
    # Save the old context
    old_context = _context.data.copy()
    
    # Update with new context
    _context.data.update(kwargs)
    
    try:
        yield
    finally:
        # Restore old context
        _context.data = old_context


class Timer:
    """Context manager for timing operations.
    
    Example:
        with Timer() as timer:
            # Do some work
            pass
        log_performance("module", "operation", timer.duration_ms)
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000