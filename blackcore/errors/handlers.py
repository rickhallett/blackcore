"""Error handlers with context preservation for better debugging."""

import traceback
import json
from typing import Any, Dict, Optional, List, Union, Type
from datetime import datetime
from contextlib import contextmanager
import threading
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..security.audit import AuditLogger


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    API = "api"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    PROPERTY = "property"
    SYNC = "sync"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""
    operation: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "operation": self.operation,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
        }


class BaseNotionError(Exception):
    """Base exception for all Notion-related errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.context = context
        self.cause = cause
        self.severity = severity
        self.category = category
        self.retryable = retryable
        self.timestamp = datetime.utcnow()
        
        # Capture stack trace
        self.stack_trace = traceback.format_exc()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "error_message": self.message,  # Changed from "message" to avoid logging conflict
            "context": self.context.to_dict() if self.context else None,
            "cause": str(self.cause) if self.cause else None,
            "severity": self.severity.value,
            "category": self.category.value,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
        }


class NotionAPIError(BaseNotionError):
    """Error from Notion API."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        response_body: Optional[str] = None,
    ):
        # Determine if retryable based on status code
        retryable = status_code in [429, 500, 502, 503, 504] if status_code else False
        
        # Determine severity
        if status_code == 401:
            severity = ErrorSeverity.CRITICAL
        elif status_code == 429:
            severity = ErrorSeverity.HIGH
        elif status_code >= 500:
            severity = ErrorSeverity.HIGH
        else:
            severity = ErrorSeverity.MEDIUM
            
        super().__init__(
            message,
            context=context,
            severity=severity,
            category=ErrorCategory.API,
            retryable=retryable,
        )
        
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


class RateLimitError(NotionAPIError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message,
            status_code=429,
            error_code="rate_limit_exceeded",
            context=context,
        )
        self.retry_after = retry_after
        self.category = ErrorCategory.RATE_LIMIT
        self.retryable = True


class ValidationError(BaseNotionError):
    """Data validation error."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message,
            context=context,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            retryable=False,
        )
        self.field = field
        self.value = value


class PropertyError(BaseNotionError):
    """Property handling error."""
    
    def __init__(
        self,
        message: str,
        property_name: str,
        property_type: str,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PROPERTY,
            retryable=False,
        )
        self.property_name = property_name
        self.property_type = property_type


class SyncError(BaseNotionError):
    """Synchronization error."""
    
    def __init__(
        self,
        message: str,
        phase: str,
        context: Optional[ErrorContext] = None,
        partial_success: bool = False,
    ):
        super().__init__(
            message,
            context=context,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.SYNC,
            retryable=True,
        )
        self.phase = phase
        self.partial_success = partial_success


class RetryableError(BaseNotionError):
    """Generic retryable error."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
        )


class NonRetryableError(BaseNotionError):
    """Generic non-retryable error."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            context=context,
            severity=ErrorSeverity.HIGH,
            retryable=False,
        )


class ErrorHandler:
    """Centralized error handler with context preservation."""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """Initialize error handler.
        
        Args:
            audit_logger: Optional audit logger instance
        """
        self.audit_logger = audit_logger or AuditLogger()
        self._context_stack = threading.local()
        self.logger = logging.getLogger(__name__)
        
        # Error statistics
        self._error_counts: Dict[str, int] = {}
        self._error_history: List[BaseNotionError] = []
        self._max_history_size = 1000
        
    @contextmanager
    def error_context(self, **kwargs):
        """Context manager for error context.
        
        Usage:
            with error_handler.error_context(operation="sync_page", resource_id="123"):
                # Operations that might raise errors
                pass
        """
        # Initialize stack if needed
        if not hasattr(self._context_stack, 'contexts'):
            self._context_stack.contexts = []
            
        # Create and push context
        context = ErrorContext(**kwargs)
        self._context_stack.contexts.append(context)
        
        try:
            yield context
        finally:
            # Pop context
            if self._context_stack.contexts:
                self._context_stack.contexts.pop()
    
    def get_current_context(self) -> Optional[ErrorContext]:
        """Get current error context."""
        if hasattr(self._context_stack, 'contexts') and self._context_stack.contexts:
            return self._context_stack.contexts[-1]
        return None
    
    def handle_error(
        self,
        error: Exception,
        operation: Optional[str] = None,
        reraise: bool = True,
    ) -> Optional[BaseNotionError]:
        """Handle an error with context preservation.
        
        Args:
            error: The error to handle
            operation: Operation being performed
            reraise: Whether to re-raise the error
            
        Returns:
            Wrapped error if applicable
        """
        # Get current context
        context = self.get_current_context()
        if operation and context:
            context.operation = operation
            
        # Wrap error if needed
        if isinstance(error, BaseNotionError):
            wrapped_error = error
            if not wrapped_error.context and context:
                wrapped_error.context = context
        else:
            # Determine error type and wrap
            wrapped_error = self._wrap_error(error, context)
            
        # Log error
        self._log_error(wrapped_error)
        
        # Update statistics
        self._update_error_stats(wrapped_error)
        
        # Re-raise if requested
        if reraise:
            raise wrapped_error
            
        return wrapped_error
    
    def _wrap_error(self, error: Exception, context: Optional[ErrorContext]) -> BaseNotionError:
        """Wrap a generic exception in appropriate error type."""
        error_str = str(error)
        error_type = type(error).__name__
        
        # Check for specific error patterns
        if "rate" in error_str.lower() and "limit" in error_str.lower():
            return RateLimitError(error_str, context=context)
        elif "validation" in error_str.lower() or "invalid" in error_str.lower():
            return ValidationError(error_str, context=context)
        elif hasattr(error, 'response'):
            # HTTP error
            status_code = getattr(error.response, 'status_code', None)
            return NotionAPIError(
                error_str,
                status_code=status_code,
                context=context,
                response_body=getattr(error.response, 'text', None),
            )
        else:
            # Generic error
            return BaseNotionError(
                error_str,
                context=context,
                cause=error,
            )
    
    def _log_error(self, error: BaseNotionError) -> None:
        """Log error with appropriate severity."""
        error_dict = error.to_dict()
        
        # Log to audit trail
        self.audit_logger.log_error(
            error_type=error.__class__.__name__,
            error_message=error.message,
            stack_trace=error.stack_trace,
            context=error_dict,
        )
        
        # Log to standard logger
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error.message}", extra=error_dict)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"Error: {error.message}", extra=error_dict)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Warning: {error.message}", extra=error_dict)
        else:
            self.logger.info(f"Info: {error.message}", extra=error_dict)
    
    def _update_error_stats(self, error: BaseNotionError) -> None:
        """Update error statistics."""
        error_type = error.__class__.__name__
        
        # Update counts
        if error_type not in self._error_counts:
            self._error_counts[error_type] = 0
        self._error_counts[error_type] += 1
        
        # Add to history
        self._error_history.append(error)
        
        # Trim history if needed
        if len(self._error_history) > self._max_history_size:
            self._error_history = self._error_history[-self._max_history_size:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        recent_errors = self._error_history[-100:]  # Last 100 errors
        
        # Calculate error rate by type
        error_rates = {}
        for error in recent_errors:
            error_type = error.__class__.__name__
            if error_type not in error_rates:
                error_rates[error_type] = 0
            error_rates[error_type] += 1
            
        # Calculate severity distribution
        severity_dist = {
            severity.value: 0 for severity in ErrorSeverity
        }
        for error in recent_errors:
            severity_dist[error.severity.value] += 1
            
        return {
            "total_errors": sum(self._error_counts.values()),
            "error_counts": self._error_counts.copy(),
            "recent_error_rates": error_rates,
            "severity_distribution": severity_dist,
            "retryable_errors": sum(1 for e in recent_errors if e.retryable),
            "non_retryable_errors": sum(1 for e in recent_errors if not e.retryable),
        }
    
    def should_retry(self, error: BaseNotionError) -> bool:
        """Determine if error should be retried."""
        if not error.retryable:
            return False
            
        # Check error frequency
        error_type = error.__class__.__name__
        recent_count = sum(
            1 for e in self._error_history[-10:]
            if e.__class__.__name__ == error_type
        )
        
        # Don't retry if we're seeing too many of the same error
        if recent_count >= 5:
            return False
            
        return True
    
    def create_user_friendly_message(self, error: BaseNotionError) -> str:
        """Create user-friendly error message."""
        if isinstance(error, RateLimitError):
            if error.retry_after:
                return f"Rate limit exceeded. Please wait {error.retry_after} seconds."
            return "Rate limit exceeded. Please try again later."
        elif isinstance(error, ValidationError):
            if error.field:
                return f"Invalid value for field '{error.field}': {error.message}"
            return f"Validation error: {error.message}"
        elif isinstance(error, PropertyError):
            return f"Error with property '{error.property_name}': {error.message}"
        elif isinstance(error, NotionAPIError):
            if error.status_code == 401:
                return "Authentication failed. Please check your API key."
            elif error.status_code == 403:
                return "Access denied. Please check your permissions."
            elif error.status_code == 404:
                return "Resource not found. It may have been deleted or you may not have access."
            elif error.status_code >= 500:
                return "Notion service error. Please try again later."
        
        return f"An error occurred: {error.message}"