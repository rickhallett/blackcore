"""Lightweight base repository for data access patterns."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import time


class RepositoryError(Exception):
    """Repository-specific error."""
    pass


class BaseRepository(ABC):
    """Abstract base repository for Notion data access."""

    def __init__(self, client, rate_limiter=None):
        """Initialize repository.

        Args:
            client: Notion API client
            rate_limiter: Optional rate limiter
        """
        self.client = client
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(self.__class__.__name__)
        self.retry_attempts = 3
        self.retry_delay = 1.0

    @abstractmethod
    def get_by_id(self, id: str) -> Dict[str, Any]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new entity."""
        pass

    @abstractmethod
    def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing entity."""
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

    def _make_api_call(self, method: str, *args, **kwargs) -> Any:
        """Make rate-limited API call with retry logic.

        Args:
            method: Client method name
            *args: Method arguments
            **kwargs: Method keyword arguments

        Returns:
            API response

        Raises:
            RepositoryError: If API call fails after retries
        """
        # Apply rate limiting
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        # Get the actual method
        api_method = getattr(self.client, method)

        # Retry logic
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                response = api_method(*args, **kwargs)
                return response
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"API call failed (attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        # All retries failed
        raise RepositoryError(f"API call failed after {self.retry_attempts} attempts: {last_error}")

    def _paginate_results(self, method: str, **query_params) -> List[Dict[str, Any]]:
        """Paginate through all results.

        Args:
            method: Client method to call
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
            response = self._make_api_call(method, **query_params)

            # Extract results
            if "results" in response:
                results.extend(response["results"])
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            else:
                # Non-paginated response
                results.append(response)
                has_more = False

        return results

    def batch_get(self, ids: List[str]) -> List[Optional[Dict[str, Any]]]:
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

    def batch_create(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple entities.

        Args:
            items: List of entity data

        Returns:
            List of created entities
        """
        results = []
        for item in items:
            entity = self.create(item)
            results.append(entity)

        return results

    def batch_update(self, updates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update multiple entities.

        Args:
            updates: Dict of {id: update_data}

        Returns:
            List of updated entities
        """
        results = []
        for id, data in updates.items():
            entity = self.update(id, data)
            results.append(entity)

        return results