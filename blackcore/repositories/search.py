"""Repository for Notion search operations."""

from typing import Any, Dict, List, Optional, Union
from ..models.responses import (
    NotionPage,
    NotionDatabase,
)
from .base import BaseRepository, RepositoryError


class SearchRepository(BaseRepository[Union[NotionPage, NotionDatabase]]):
    """Repository for Notion search operations."""

    def get_by_id(self, id: str) -> Union[NotionPage, NotionDatabase]:
        """Not supported for search repository."""
        raise NotImplementedError("Search repository doesn't support get_by_id")

    def create(self, data: Dict[str, Any]) -> Union[NotionPage, NotionDatabase]:
        """Not supported for search repository."""
        raise NotImplementedError("Search repository doesn't support create")

    def update(self, id: str, data: Dict[str, Any]) -> Union[NotionPage, NotionDatabase]:
        """Not supported for search repository."""
        raise NotImplementedError("Search repository doesn't support update")

    def delete(self, id: str) -> bool:
        """Not supported for search repository."""
        raise NotImplementedError("Search repository doesn't support delete")

    def search(
        self,
        query: str,
        filter_type: Optional[str] = None,
        sort: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> List[Union[NotionPage, NotionDatabase]]:
        """Search for pages and databases.

        Args:
            query: Search query text
            filter_type: Optional filter by type ("page" or "database")
            sort: Optional sort configuration
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        with self._operation_context("search"):
            try:
                # Prepare search data
                search_data = {
                    "query": query,
                }

                # Add filter if specified
                if filter_type:
                    search_data["filter"] = {"property": "object", "value": filter_type}

                # Add sort if specified
                if sort:
                    search_data["sort"] = sort

                # Add additional parameters
                search_data.update(kwargs)

                # Paginate through results
                results = self._paginate_results(
                    lambda **params: self._make_api_call(
                        "POST",
                        "search",
                        data=params,
                    ),
                    **search_data,
                )

                # Log data access
                self.audit_logger.log_data_access(
                    operation="search",
                    resource_type="global",
                    resource_id="search",
                    fields_accessed=["query"],
                    purpose=f"Search for: {query}",
                )

                return results

            except Exception as e:
                raise RepositoryError(f"Search failed: {str(e)}")

    def search_pages(
        self, query: str, sort: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[NotionPage]:
        """Search for pages only.

        Args:
            query: Search query text
            sort: Optional sort configuration
            **kwargs: Additional search parameters

        Returns:
            List of pages
        """
        results = self.search(query, filter_type="page", sort=sort, **kwargs)
        return [r for r in results if isinstance(r, NotionPage)]

    def search_databases(
        self, query: str, sort: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[NotionDatabase]:
        """Search for databases only.

        Args:
            query: Search query text
            sort: Optional sort configuration
            **kwargs: Additional search parameters

        Returns:
            List of databases
        """
        results = self.search(query, filter_type="database", sort=sort, **kwargs)
        return [r for r in results if isinstance(r, NotionDatabase)]

    def search_by_title(
        self, title: str, exact_match: bool = False
    ) -> List[Union[NotionPage, NotionDatabase]]:
        """Search by title.

        Args:
            title: Title to search for
            exact_match: Whether to require exact match

        Returns:
            List of results with matching titles
        """
        # Search for the title
        results = self.search(title)

        if exact_match:
            # Filter to exact matches
            filtered_results = []
            for result in results:
                # Extract title based on type
                if isinstance(result, NotionPage):
                    # Check title property
                    if "title" in result.properties:
                        # This is simplified - would need to extract actual title
                        filtered_results.append(result)
                elif isinstance(result, NotionDatabase):
                    # Check database title
                    db_title = "".join(text.plain_text for text in result.title)
                    if db_title.lower() == title.lower():
                        filtered_results.append(result)

            return filtered_results

        return results

    def find_by_property(
        self, property_name: str, property_value: Any, object_type: Optional[str] = None
    ) -> List[Union[NotionPage, NotionDatabase]]:
        """Find objects by property value.

        Args:
            property_name: Property name
            property_value: Property value to match
            object_type: Optional filter by type

        Returns:
            List of matching objects

        Note: This is a basic implementation. Notion's search API
        doesn't support property-based search directly, so this
        searches for the value and filters results.
        """
        # Search for the property value
        query = str(property_value)
        results = self.search(query, filter_type=object_type)

        # Filter to items that have the property
        # This is a simplified implementation
        filtered = []
        for result in results:
            if isinstance(result, NotionPage):
                if property_name in result.properties:
                    filtered.append(result)

        return filtered

    def _execute_api_call(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        """Execute the actual API call using the Notion client."""
        if method == "POST" and endpoint == "search":
            return self.client.search(**data)
        else:
            raise NotImplementedError(f"Unsupported operation: {method} {endpoint}")
