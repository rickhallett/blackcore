"""Audit logging for security and compliance."""

import json
import structlog
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path
import hashlib
import threading
from contextlib import contextmanager


class AuditLogger:
    """Provides comprehensive audit logging for all operations."""

    def __init__(self, log_file: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            log_file: Optional path to audit log file
        """
        self.log_file = log_file or Path("logs/audit.log")
        self.log_file.parent.mkdir(exist_ok=True)

        # Configure structured logging
        self.logger = structlog.get_logger("audit")
        self._configure_logger()

        # Thread-local storage for context
        self._context = threading.local()

    def _configure_logger(self):
        """Configure structured logger with proper processors."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._add_audit_context,
                self._sanitize_sensitive_data,
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _add_audit_context(self, logger, method_name, event_dict):
        """Add audit context to log entries."""
        # Add standard audit fields
        event_dict["audit_timestamp"] = datetime.utcnow().isoformat()
        event_dict["audit_version"] = "1.0"

        # Add context from thread-local storage
        if hasattr(self._context, "user_id"):
            event_dict["user_id"] = self._context.user_id
        if hasattr(self._context, "session_id"):
            event_dict["session_id"] = self._context.session_id
        if hasattr(self._context, "request_id"):
            event_dict["request_id"] = self._context.request_id
        if hasattr(self._context, "ip_address"):
            event_dict["ip_address"] = self._context.ip_address

        return event_dict

    def _sanitize_sensitive_data(self, logger, method_name, event_dict):
        """Remove or mask sensitive data from logs."""
        sensitive_keys = [
            "password",
            "api_key",
            "token",
            "secret",
            "credential",
            "ssn",
            "credit_card",
            "private_key",
            "notion_api_key",
        ]

        def sanitize_value(key: str, value: Any) -> Any:
            """Sanitize a single value."""
            key_lower = key.lower()

            # Check if key contains sensitive terms
            if any(term in key_lower for term in sensitive_keys):
                if isinstance(value, str):
                    # Show partial value for debugging
                    if len(value) > 8:
                        return f"{value[:4]}...{value[-4:]}"
                    else:
                        return "***REDACTED***"
                else:
                    return "***REDACTED***"

            # Recursively sanitize nested structures
            if isinstance(value, dict):
                return {k: sanitize_value(k, v) for k, v in value.items()}
            elif isinstance(value, list):
                return [sanitize_value(f"item_{i}", v) for i, v in enumerate(value)]

            return value

        # Sanitize all values in event dict
        for key, value in list(event_dict.items()):
            event_dict[key] = sanitize_value(key, value)

        return event_dict

    @contextmanager
    def audit_context(self, **kwargs):
        """Context manager to set audit context.

        Usage:
            with audit_logger.audit_context(user_id="123", session_id="abc"):
                # All logs within this context will include user_id and session_id
                audit_logger.log_api_call(...)
        """
        # Save previous context
        previous_context = {}
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                previous_context[key] = getattr(self._context, key)
            setattr(self._context, key, value)

        try:
            yield
        finally:
            # Restore previous context
            for key in kwargs:
                if key in previous_context:
                    setattr(self._context, key, previous_context[key])
                else:
                    delattr(self._context, key)

    def log_api_call(
        self,
        method: str,
        endpoint: str,
        parameters: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log an API call for audit trail.

        Args:
            method: HTTP method or API method name
            endpoint: API endpoint or resource
            parameters: Request parameters
            response_status: HTTP response status code
            duration_ms: Call duration in milliseconds
            error: Error message if call failed
        """
        log_data = {
            "event_type": "api_call",
            "method": method,
            "endpoint": endpoint,
            "success": error is None,
        }

        if parameters:
            log_data["parameters"] = parameters
        if response_status:
            log_data["response_status"] = response_status
        if duration_ms:
            log_data["duration_ms"] = duration_ms
        if error:
            log_data["error"] = error

        self.logger.info("api_call", **log_data)

    def log_data_access(
        self,
        operation: str,
        resource_type: str,
        resource_id: str,
        fields_accessed: Optional[List[str]] = None,
        purpose: Optional[str] = None,
    ) -> None:
        """Log data access for compliance.

        Args:
            operation: Type of operation (read, write, delete)
            resource_type: Type of resource accessed
            resource_id: ID of resource
            fields_accessed: Specific fields that were accessed
            purpose: Business purpose for access
        """
        log_data = {
            "event_type": "data_access",
            "operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }

        if fields_accessed:
            log_data["fields_accessed"] = fields_accessed
        if purpose:
            log_data["purpose"] = purpose

        # Generate access hash for integrity
        access_string = f"{operation}:{resource_type}:{resource_id}"
        log_data["access_hash"] = hashlib.sha256(access_string.encode()).hexdigest()[
            :16
        ]

        self.logger.info("data_access", **log_data)

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security-related events.

        Args:
            event_type: Type of security event
            severity: Severity level (info, warning, error, critical)
            description: Human-readable description
            details: Additional event details
        """
        log_data = {
            "event_type": "security",
            "security_event_type": event_type,
            "severity": severity,
            "description": description,
        }

        if details:
            log_data["details"] = details

        # Log at appropriate level
        if severity == "critical":
            self.logger.critical("security_event", **log_data)
        elif severity == "error":
            self.logger.error("security_event", **log_data)
        elif severity == "warning":
            self.logger.warning("security_event", **log_data)
        else:
            self.logger.info("security_event", **log_data)

    def log_authentication(
        self, action: str, success: bool, method: str, reason: Optional[str] = None
    ) -> None:
        """Log authentication attempts.

        Args:
            action: Authentication action (login, logout, refresh)
            success: Whether authentication succeeded
            method: Authentication method used
            reason: Reason for failure if applicable
        """
        log_data = {
            "event_type": "authentication",
            "action": action,
            "success": success,
            "method": method,
        }

        if reason:
            log_data["reason"] = reason

        if success:
            self.logger.info("authentication", **log_data)
        else:
            self.logger.warning("authentication_failed", **log_data)

    def log_authorization(
        self, resource: str, action: str, granted: bool, reason: Optional[str] = None
    ) -> None:
        """Log authorization decisions.

        Args:
            resource: Resource being accessed
            action: Action being attempted
            granted: Whether access was granted
            reason: Reason for decision
        """
        log_data = {
            "event_type": "authorization",
            "resource": resource,
            "action": action,
            "granted": granted,
        }

        if reason:
            log_data["reason"] = reason

        if granted:
            self.logger.info("authorization", **log_data)
        else:
            self.logger.warning("authorization_denied", **log_data)

    def log_configuration_change(
        self, setting: str, old_value: Any, new_value: Any, reason: Optional[str] = None
    ) -> None:
        """Log configuration changes for audit.

        Args:
            setting: Configuration setting changed
            old_value: Previous value
            new_value: New value
            reason: Reason for change
        """
        log_data = {
            "event_type": "configuration_change",
            "setting": setting,
            "old_value": old_value,
            "new_value": new_value,
        }

        if reason:
            log_data["reason"] = reason

        self.logger.info("configuration_change", **log_data)

    def log_secret_rotation(self, secret_name: str) -> None:
        """Log secret rotation events.

        Args:
            secret_name: Name of rotated secret (not the value!)
        """
        log_data = {
            "event_type": "secret_rotation",
            "secret_name": secret_name,
            "rotation_timestamp": datetime.utcnow().isoformat(),
        }

        self.logger.info("secret_rotation", **log_data)

    def log_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log application errors for debugging.

        Args:
            error_type: Type/class of error
            error_message: Error message
            stack_trace: Optional stack trace
            context: Additional error context
        """
        log_data = {
            "event_type": "error",
            "error_type": error_type,
            "error_message": error_message,
        }

        if stack_trace:
            log_data["stack_trace"] = stack_trace
        if context:
            log_data["error_context"] = context

        self.logger.error("application_error", **log_data)

    def get_audit_trail(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit trail for specified period.

        Args:
            start_date: Start of period
            end_date: End of period
            filters: Optional filters to apply

        Returns:
            List of audit log entries
        """
        # This is a placeholder - in production, this would query
        # a proper audit log storage system (e.g., Elasticsearch)
        entries = []

        if self.log_file.exists():
            with open(self.log_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(
                            entry.get("audit_timestamp", "")
                        )

                        if start_date <= entry_time <= end_date:
                            if self._matches_filters(entry, filters):
                                entries.append(entry)

                    except (json.JSONDecodeError, ValueError):
                        continue

        return entries

    def _matches_filters(
        self, entry: Dict[str, Any], filters: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if entry matches filters."""
        if not filters:
            return True

        for key, value in filters.items():
            if key not in entry:
                return False
            if entry[key] != value:
                return False

        return True
