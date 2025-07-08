"""Repository for Notion database operations."""

from typing import Any, Dict, List, Optional
from ..models.responses import (
    NotionDatabase,
    NotionPage,
    NotionDatabaseQuery,
    ObjectType,
    validate_notion_response,
    validate_paginated_response,
)
from ..models.properties import PropertyType
from ..handlers.base import property_handler_registry
from .base import BaseRepository, RepositoryError


class DatabaseRepository(BaseRepository[NotionDatabase]):
    """Repository for Notion database operations."""
    
    def get_by_id(self, id: str) -> NotionDatabase:
        """Get database by ID.
        
        Args:
            id: Database ID
            
        Returns:
            NotionDatabase object
            
        Raises:
            RepositoryError: If database not found
        """
        with self._operation_context("get", id):
            try:
                # Make API call
                response = self._make_api_call(
                    "GET",
                    f"databases/{id}",
                )
                
                # Validate response
                database = validate_notion_response(response, ObjectType.DATABASE)
                
                # Log data access
                self._log_data_access("read", id)
                
                return database
                
            except Exception as e:
                raise RepositoryError(f"Failed to get database {id}: {str(e)}")
    
    def create(self, data: Dict[str, Any]) -> NotionDatabase:
        """Create new database.
        
        Args:
            data: Database data with parent, title, and properties
            
        Returns:
            Created database
            
        Raises:
            RepositoryError: If creation fails
        """
        with self._operation_context("create"):
            try:
                # Validate required fields
                if "parent" not in data:
                    raise RepositoryError("Database must have parent")
                if "title" not in data:
                    raise RepositoryError("Database must have title")
                if "properties" not in data:
                    raise RepositoryError("Database must have properties")
                
                # Prepare request data
                request_data = {
                    "parent": data["parent"],
                    "title": self._format_title(data["title"]),
                    "properties": self._format_database_properties(data["properties"]),
                }
                
                # Add optional fields
                if "description" in data:
                    request_data["description"] = self._format_title(data["description"])
                if "icon" in data:
                    request_data["icon"] = data["icon"]
                if "cover" in data:
                    request_data["cover"] = data["cover"]
                if "is_inline" in data:
                    request_data["is_inline"] = bool(data["is_inline"])
                
                # Make API call
                response = self._make_api_call(
                    "POST",
                    "databases",
                    data=request_data,
                )
                
                # Validate response
                database = validate_notion_response(response, ObjectType.DATABASE)
                
                # Log data access
                self._log_data_access("create", database.id)
                
                return database
                
            except Exception as e:
                raise RepositoryError(f"Failed to create database: {str(e)}")
    
    def update(self, id: str, data: Dict[str, Any]) -> NotionDatabase:
        """Update database configuration.
        
        Args:
            id: Database ID
            data: Update data (title, description, properties, etc.)
            
        Returns:
            Updated database
            
        Raises:
            RepositoryError: If update fails
        """
        with self._operation_context("update", id):
            try:
                # Prepare update data
                update_data = {}
                
                # Update title if provided
                if "title" in data:
                    update_data["title"] = self._format_title(data["title"])
                
                # Update description if provided
                if "description" in data:
                    update_data["description"] = self._format_title(data["description"])
                
                # Update properties if provided
                if "properties" in data:
                    update_data["properties"] = self._format_database_properties(
                        data["properties"]
                    )
                
                # Update other fields
                if "archived" in data:
                    update_data["archived"] = bool(data["archived"])
                if "icon" in data:
                    update_data["icon"] = data["icon"]
                if "cover" in data:
                    update_data["cover"] = data["cover"]
                
                # Make API call
                response = self._make_api_call(
                    "PATCH",
                    f"databases/{id}",
                    data=update_data,
                )
                
                # Validate response
                database = validate_notion_response(response, ObjectType.DATABASE)
                
                # Log data access
                self._log_data_access(
                    "update",
                    id,
                    fields=list(update_data.keys())
                )
                
                return database
                
            except Exception as e:
                raise RepositoryError(f"Failed to update database {id}: {str(e)}")
    
    def delete(self, id: str) -> bool:
        """Archive database (Notion doesn't support hard delete).
        
        Args:
            id: Database ID
            
        Returns:
            True if archived
            
        Raises:
            RepositoryError: If deletion fails
        """
        with self._operation_context("delete", id):
            try:
                # Archive the database
                self.update(id, {"archived": True})
                
                # Log data access
                self._log_data_access("delete", id)
                
                return True
                
            except Exception as e:
                raise RepositoryError(f"Failed to delete database {id}: {str(e)}")
    
    def query(
        self,
        database_id: str,
        query: Optional[NotionDatabaseQuery] = None,
        **kwargs
    ) -> List[NotionPage]:
        """Query database for pages.
        
        Args:
            database_id: Database ID
            query: Query object
            **kwargs: Additional query parameters
            
        Returns:
            List of pages matching query
        """
        with self._operation_context("query", database_id):
            try:
                # Prepare query data
                query_data = {}
                
                if query:
                    query_dict = query.dict(exclude_none=True)
                    query_data.update(query_dict)
                
                # Add kwargs
                query_data.update(kwargs)
                
                # Paginate through results
                pages = self._paginate_results(
                    lambda **params: self._make_api_call(
                        "POST",
                        f"databases/{database_id}/query",
                        data=params,
                    ),
                    **query_data
                )
                
                # Log data access
                self._log_data_access(
                    "query",
                    database_id,
                    fields=["pages"]
                )
                
                return pages
                
            except Exception as e:
                raise RepositoryError(
                    f"Failed to query database {database_id}: {str(e)}"
                )
    
    def get_all_pages(self, database_id: str) -> List[NotionPage]:
        """Get all pages in a database.
        
        Args:
            database_id: Database ID
            
        Returns:
            All pages in database
        """
        return self.query(database_id)
    
    def add_property(
        self,
        database_id: str,
        property_name: str,
        property_config: Dict[str, Any]
    ) -> NotionDatabase:
        """Add a property to database schema.
        
        Args:
            database_id: Database ID
            property_name: Name of new property
            property_config: Property configuration
            
        Returns:
            Updated database
        """
        # Get current database to preserve existing properties
        database = self.get_by_id(database_id)
        
        # Add new property
        properties = {
            prop_name: prop.model_dump() for prop_name, prop in database.properties.items()
        }
        properties[property_name] = property_config
        
        # Update database
        return self.update(database_id, {"properties": properties})
    
    def remove_property(self, database_id: str, property_name: str) -> NotionDatabase:
        """Remove a property from database schema.
        
        Args:
            database_id: Database ID
            property_name: Name of property to remove
            
        Returns:
            Updated database
        """
        # Get current database
        database = self.get_by_id(database_id)
        
        # Remove property by setting to null
        properties = {
            prop_name: prop.model_dump() for prop_name, prop in database.properties.items()
        }
        properties[property_name] = None
        
        # Update database
        return self.update(database_id, {"properties": properties})
    
    def rename_property(
        self,
        database_id: str,
        old_name: str,
        new_name: str
    ) -> NotionDatabase:
        """Rename a database property.
        
        Args:
            database_id: Database ID
            old_name: Current property name
            new_name: New property name
            
        Returns:
            Updated database
        """
        # Get current database
        database = self.get_by_id(database_id)
        
        if old_name not in database.properties:
            raise RepositoryError(f"Property '{old_name}' not found in database")
        
        # Get property config
        prop_config = database.properties[old_name].dict()
        prop_config["name"] = new_name
        
        # Update property
        return self.update(database_id, {"properties": {old_name: prop_config}})
    
    def _format_title(self, title: Any) -> List[Dict[str, Any]]:
        """Format title for API submission."""
        if isinstance(title, str):
            return [{
                "type": "text",
                "text": {"content": title}
            }]
        elif isinstance(title, list):
            return title
        else:
            return [{
                "type": "text",
                "text": {"content": str(title)}
            }]
    
    def _format_database_properties(
        self,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format database property definitions."""
        formatted = {}
        
        for name, config in properties.items():
            if config is None:
                # Remove property
                formatted[name] = None
            elif isinstance(config, dict):
                # Ensure required fields
                if "type" not in config and name not in config:
                    raise RepositoryError(
                        f"Property '{name}' must have 'type' field"
                    )
                formatted[name] = config
            else:
                raise RepositoryError(
                    f"Property '{name}' config must be dict or None"
                )
        
        return formatted
    
    def _execute_api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute the actual API call using the Notion client."""
        if method == "GET" and endpoint.startswith("databases/"):
            database_id = endpoint.replace("databases/", "")
            return self.client.databases.retrieve(database_id=database_id)
        elif method == "POST" and endpoint == "databases":
            return self.client.databases.create(**data)
        elif method == "PATCH" and endpoint.startswith("databases/"):
            database_id = endpoint.replace("databases/", "")
            return self.client.databases.update(database_id=database_id, **data)
        elif method == "POST" and "/query" in endpoint:
            database_id = endpoint.replace("databases/", "").replace("/query", "")
            return self.client.databases.query(database_id=database_id, **data)
        else:
            raise NotImplementedError(f"Unsupported operation: {method} {endpoint}")