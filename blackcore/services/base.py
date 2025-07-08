"""Base service class for business logic."""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from notion_client import Client
from ..repositories.base import BaseRepository
from ..errors.handlers import ErrorHandler
from ..security.audit import AuditLogger
from ..rate_limiting.thread_safe import ThreadSafeRateLimiter


class ServiceError(Exception):
    """Service layer error."""
    pass


class BaseService(ABC):
    """Abstract base service for business logic."""
    
    def __init__(
        self,
        client: Client,
        rate_limiter: Optional[ThreadSafeRateLimiter] = None,
        error_handler: Optional[ErrorHandler] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """Initialize service.
        
        Args:
            client: Notion API client
            rate_limiter: Optional rate limiter
            error_handler: Optional error handler
            audit_logger: Optional audit logger
        """
        self.client = client
        self.rate_limiter = rate_limiter or ThreadSafeRateLimiter()
        self.error_handler = error_handler or ErrorHandler()
        self.audit_logger = audit_logger or AuditLogger()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize repositories
        self._init_repositories()
    
    @abstractmethod
    def _init_repositories(self) -> None:
        """Initialize required repositories."""
        pass
    
    def _create_repository(self, repository_class: type) -> BaseRepository:
        """Create a repository instance with shared dependencies.
        
        Args:
            repository_class: Repository class to instantiate
            
        Returns:
            Repository instance
        """
        return repository_class(
            client=self.client,
            rate_limiter=self.rate_limiter,
            error_handler=self.error_handler,
            audit_logger=self.audit_logger,
        )
    
    def log_operation(self, operation: str, **details) -> None:
        """Log a service operation.
        
        Args:
            operation: Operation name
            **details: Operation details
        """
        self.logger.info(
            f"Service operation: {operation}",
            extra={"operation": operation, **details}
        )
        
        # Also log to audit trail
        self.audit_logger.log_data_access(
            operation=operation,
            resource_type="service",
            resource_id=self.__class__.__name__,
            purpose=f"Service operation: {operation}",
        )