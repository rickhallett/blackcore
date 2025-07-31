"""Standardized error handling patterns for the minimal module."""

import time
import functools
from typing import Any, Dict, Optional, Type, Union, Callable
from contextlib import contextmanager

from .logging_config import get_logger, log_error

logger = get_logger(__name__)


class BlackcoreError(Exception):
    """Base exception for all Blackcore-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}


class NotionAPIError(BlackcoreError):
    """Error from Notion API operations."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)
        self.status_code = status_code


class ValidationError(BlackcoreError):
    """Error from data validation operations."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Any = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context=context)
        self.field_name = field_name
        self.field_value = field_value


class ProcessingError(BlackcoreError):
    """Error from entity processing operations."""
    
    def __init__(
        self,
        message: str,
        entity_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context=context)
        self.entity_type = entity_type


class ConfigurationError(BlackcoreError):
    """Error from configuration validation and setup issues."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context=context)
        self.config_key = config_key


class ErrorHandler:
    """Centralized error handling with consistent logging and context propagation for debugging."""
    
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        log_errors: bool = True,
        raise_on_critical: bool = True
    ):
        """Initialize error handler.
        
        Args:
            context: Base context to include with all errors
            log_errors: Whether to log errors when handled
            raise_on_critical: Whether to raise critical errors
        """
        self.context = context or {}
        self.log_errors = log_errors
        self.raise_on_critical = raise_on_critical
    
    def handle_error(
        self,
        error: Exception,
        critical: bool = False,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Exception:
        """Handle an error with consistent logging and context.
        
        Args:
            error: The exception to handle
            critical: Whether this is a critical error
            additional_context: Additional context for this error
            
        Returns:
            The error (possibly enhanced)
            
        Raises:
            Exception: If critical=True and raise_on_critical=True
        """
        # Enhance error with context if it's a BlackcoreError
        if isinstance(error, BlackcoreError):
            # Merge contexts
            error.context.update(self.context)
            if additional_context:
                error.context.update(additional_context)
        
        # Log the error if enabled
        if self.log_errors:
            log_error(
                __name__,
                "error_handled",
                error,
                critical=critical,
                error_type=type(error).__name__,
                **self.context,
                **(additional_context or {})
            )
        
        # Raise critical errors if configured
        if critical and self.raise_on_critical:
            raise error
        
        return error
    
    @contextmanager
    def with_context(self, **context_updates):
        """Temporarily add context for error handling in a block.
        
        Args:
            **context_updates: Additional context key-value pairs
            
        Yields:
            ErrorHandler with updated context
        """
        # Save original context
        original_context = self.context.copy()
        
        # Update context
        self.context.update(context_updates)
        
        try:
            yield self
        finally:
            # Restore original context
            self.context = original_context
    
    def is_retryable(self, error: Exception) -> bool:
        """Determine if an error is retryable.
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error should be retried
        """
        # Check for specific retryable conditions
        if isinstance(error, NotionAPIError):
            # Rate limiting and server errors are retryable
            if error.error_code in ["rate_limited", "internal_server_error"]:
                return True
            if error.status_code and error.status_code >= 500:
                return True
            # Client errors (4xx) are generally not retryable
            if error.status_code and 400 <= error.status_code < 500:
                return False
        
        # Validation and configuration errors are not retryable
        if isinstance(error, (ValidationError, ConfigurationError)):
            return False
        
        # Network-related errors might be retryable
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True
        
        # By default, ProcessingErrors might be retryable
        if isinstance(error, ProcessingError):
            return True
        
        # Unknown errors - be conservative and don't retry
        return False


def handle_errors(
    log_errors: bool = True,
    reraise: bool = False,
    default_return: Any = None,
    context: Optional[Dict[str, Any]] = None,
    convert_to: Optional[Type[BlackcoreError]] = None
):
    """Decorator to handle errors in functions consistently.
    
    Args:
        log_errors: Whether to log caught errors
        reraise: Whether to reraise the exception after handling
        default_return: Value to return if error is caught and not reraised
        context: Additional context to include with errors
        convert_to: Convert non-BlackcoreError exceptions to this type
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(
                context=context,
                log_errors=log_errors,
                raise_on_critical=reraise
            )
            
            try:
                return func(*args, **kwargs)
            except BlackcoreError as e:
                handler.handle_error(e, critical=reraise)
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # Convert to BlackcoreError if requested
                if convert_to and issubclass(convert_to, BlackcoreError):
                    blackcore_error = convert_to(
                        f"Error in {func.__name__}: {str(e)}",
                        context={
                            **(context or {}),
                            "original_error": type(e).__name__,
                            "function": func.__name__
                        }
                    )
                    handler.handle_error(blackcore_error, critical=reraise)
                    if reraise:
                        raise blackcore_error
                    return default_return
                else:
                    # Handle as generic error
                    handler.handle_error(e, critical=reraise)
                    if reraise:
                        raise
                    return default_return
        
        return wrapper
    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    context: Optional[Dict[str, Any]] = None
):
    """Decorator to retry functions on retryable errors.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each attempt
        context: Additional context for error handling
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(context=context)
            last_error = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    # Check if error is retryable
                    if not handler.is_retryable(e):
                        # Not retryable - raise immediately
                        raise
                    
                    # If this was the last attempt, raise the error
                    if attempt == max_attempts - 1:
                        raise
                    
                    # Log retry attempt
                    if handler.log_errors:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed, retrying in {current_delay}s",
                            extra={
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay": current_delay,
                                **(context or {})
                            }
                        )
                    
                    # Wait before retry
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # Should never reach here due to the raise in the loop
            raise last_error
        
        return wrapper
    return decorator


@contextmanager
def ErrorContext(
    operation: str,
    convert_to: Type[BlackcoreError] = ProcessingError,
    **context
):
    """Context manager to automatically enhance errors with context.
    
    Args:
        operation: Name of the operation being performed
        convert_to: Type to convert non-BlackcoreError exceptions to
        **context: Additional context key-value pairs
        
    Raises:
        BlackcoreError: Enhanced with context information
    """
    full_context = {
        "operation": operation,
        **context
    }
    
    try:
        yield
    except BlackcoreError as e:
        # Enhance existing BlackcoreError with context
        e.context.update(full_context)
        raise
    except Exception as e:
        # Convert other exceptions to BlackcoreError with context
        blackcore_error = convert_to(
            f"Error during {operation}: {str(e)}",
            context={
                **full_context,
                "original_error": type(e).__name__
            }
        )
        raise blackcore_error from e