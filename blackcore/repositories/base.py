"""Base repository for data access patterns."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from contextlib import contextmanager
import logging

from notion_client import Client
from ..errors.handlers import BaseNotionError, ErrorHandler, ErrorContext
from ..security.audit import AuditLogger
from ..rate_limiting.thread_safe import ThreadSafeRateLimiter
from ..models.responses import NotionPaginatedResponse, validate_notion_response, ObjectType


T = TypeVar('T')


class RepositoryError(Exception):
    """Repository-specific error."""
    pass


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for Notion data access."""
    
    def __init__(
        self,
        client: Client,
        rate_limiter: Optional[ThreadSafeRateLimiter] = None,
        error_handler: Optional[ErrorHandler] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """Initialize repository.
        
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
    
    @abstractmethod
    def get_by_id(self, id: str) -> T:
        """Get entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity object
            
        Raises:
            RepositoryError: If entity not found or error occurs
        """
        pass
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """Create new entity.
        
        Args:
            data: Entity data
            
        Returns:
            Created entity
            
        Raises:
            RepositoryError: If creation fails
        """
        pass
    
    @abstractmethod
    def update(self, id: str, data: Dict[str, Any]) -> T:
        """Update existing entity.
        
        Args:
            id: Entity ID
            data: Update data
            
        Returns:
            Updated entity
            
        Raises:
            RepositoryError: If update fails
        """
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity (archive in Notion).
        
        Args:
            id: Entity ID
            
        Returns:
            True if deleted
            
        Raises:
            RepositoryError: If deletion fails
        """
        pass
    
    def exists(self, id: str) -> bool:
        """Check if entity exists.
        
        Args:
            id: Entity ID
            
        Returns:
            True if exists
        """
        try:
            self.get_by_id(id)
            return True
        except RepositoryError:
            return False
    
    @contextmanager
    def _operation_context(self, operation: str, resource_id: Optional[str] = None):
        """Context manager for repository operations.
        
        Args:
            operation: Operation name
            resource_id: Optional resource ID
        """
        context = ErrorContext(
            operation=f"repository.{operation}",
            resource_type=self._get_resource_type(),
            resource_id=resource_id,
        )
        
        with self.error_handler.error_context(**context.to_dict()):
            yield context
    
    def _get_resource_type(self) -> str:
        """Get resource type for this repository."""
        return self.__class__.__name__.replace("Repository", "").lower()
    
    def _make_api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Make rate-limited API call with error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            **kwargs: Additional arguments
            
        Returns:
            API response
            
        Raises:
            BaseNotionError: If API call fails
        """
        # Wait for rate limit
        wait_time = self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            self.logger.debug(f"Rate limited, waited {wait_time:.2f}s")
        
        # Log API call
        self.audit_logger.log_api_call(
            method=method,
            endpoint=endpoint,
            parameters=data,
        )
        
        try:
            # Make the actual call
            # This is a simplified version - in reality would use the client methods
            response = self._execute_api_call(method, endpoint, data, **kwargs)
            
            # Log success
            self.audit_logger.log_api_call(
                method=method,
                endpoint=endpoint,
                parameters=data,
                response_status=200,
            )
            
            return response
            
        except Exception as e:
            # Log error
            self.audit_logger.log_api_call(
                method=method,
                endpoint=endpoint,
                parameters=data,
                error=str(e),
            )
            
            # Re-raise with context
            self.error_handler.handle_error(e)
    
    def _execute_api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute the actual API call.
        
        This should be overridden by subclasses to use the appropriate
        client method.
        """
        raise NotImplementedError("Subclasses must implement _execute_api_call")
    
    def _paginate_results(
        self,
        query_func,
        **query_params
    ) -> List[Any]:
        """Paginate through all results.
        
        Args:
            query_func: Function to call for queries
            **query_params: Query parameters
            
        Returns:
            All results
        """
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            # Add pagination params
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            # Make query
            response = query_func(**query_params)
            
            # Validate response
            if isinstance(response, dict):
                paginated = validate_notion_response(response, ObjectType.LIST)
                results.extend(paginated.results)
                has_more = paginated.has_more
                start_cursor = paginated.next_cursor
            else:
                # Non-paginated response
                results.append(response)
                has_more = False
        
        return results
    
    def _log_data_access(
        self,
        operation: str,
        resource_id: str,
        fields: Optional[List[str]] = None,
    ) -> None:
        """Log data access for compliance.
        
        Args:
            operation: Operation type
            resource_id: Resource ID
            fields: Fields accessed
        """
        self.audit_logger.log_data_access(
            operation=operation,
            resource_type=self._get_resource_type(),
            resource_id=resource_id,
            fields_accessed=fields,
        )
    
    def batch_get(self, ids: List[str]) -> List[T]:
        """Get multiple entities by IDs.
        
        Args:
            ids: List of entity IDs
            
        Returns:
            List of entities (may contain None for not found)
        """
        results = []
        for id in ids:
            try:
                entity = self.get_by_id(id)
                results.append(entity)
            except RepositoryError:
                results.append(None)
        
        return results
    
    def batch_create(self, items: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities.
        
        Args:
            items: List of entity data
            
        Returns:
            List of created entities
            
        Raises:
            RepositoryError: If any creation fails
        """
        results = []
        for item in items:
            entity = self.create(item)
            results.append(entity)
        
        return results
    
    def batch_update(self, updates: Dict[str, Dict[str, Any]]) -> List[T]:
        """Update multiple entities.
        
        Args:
            updates: Dict of {id: update_data}
            
        Returns:
            List of updated entities
            
        Raises:
            RepositoryError: If any update fails
        """
        results = []
        for id, data in updates.items():
            entity = self.update(id, data)
            results.append(entity)
        
        return results
    
    def batch_delete(self, ids: List[str]) -> List[bool]:
        """Delete multiple entities.
        
        Args:
            ids: List of entity IDs
            
        Returns:
            List of deletion results
        """
        results = []
        for id in ids:
            try:
                result = self.delete(id)
                results.append(result)
            except RepositoryError:
                results.append(False)
        
        return results