"""Repository for Notion page operations."""

from typing import Any, Dict, List, Optional
from ..models.responses import NotionPage, ObjectType, validate_notion_response
from ..models.properties import PropertyType, parse_property_value
from ..handlers.base import property_handler_registry
from .base import BaseRepository, RepositoryError


class PageRepository(BaseRepository[NotionPage]):
    """Repository for Notion page operations."""
    
    def get_by_id(self, id: str) -> NotionPage:
        """Get page by ID.
        
        Args:
            id: Page ID
            
        Returns:
            NotionPage object
            
        Raises:
            RepositoryError: If page not found
        """
        with self._operation_context("get", id):
            try:
                # Make API call
                response = self._make_api_call(
                    "GET",
                    f"pages/{id}",
                )
                
                # Validate response
                page = validate_notion_response(response, ObjectType.PAGE)
                
                # Log data access
                self._log_data_access("read", id)
                
                return page
                
            except Exception as e:
                raise RepositoryError(f"Failed to get page {id}: {str(e)}")
    
    def create(self, data: Dict[str, Any]) -> NotionPage:
        """Create new page.
        
        Args:
            data: Page data with parent and properties
            
        Returns:
            Created page
            
        Raises:
            RepositoryError: If creation fails
        """
        with self._operation_context("create"):
            try:
                # Validate required fields
                if "parent" not in data:
                    raise RepositoryError("Page must have parent")
                if "properties" not in data:
                    raise RepositoryError("Page must have properties")
                
                # Normalize properties
                normalized_props = self._normalize_properties(data["properties"])
                
                # Prepare request data
                request_data = {
                    "parent": data["parent"],
                    "properties": normalized_props,
                }
                
                # Add optional fields
                if "icon" in data:
                    request_data["icon"] = data["icon"]
                if "cover" in data:
                    request_data["cover"] = data["cover"]
                if "children" in data:
                    request_data["children"] = data["children"]
                
                # Make API call
                response = self._make_api_call(
                    "POST",
                    "pages",
                    data=request_data,
                )
                
                # Validate response
                page = validate_notion_response(response, ObjectType.PAGE)
                
                # Log data access
                self._log_data_access("create", page.id)
                
                return page
                
            except Exception as e:
                raise RepositoryError(f"Failed to create page: {str(e)}")
    
    def update(self, id: str, data: Dict[str, Any]) -> NotionPage:
        """Update page properties.
        
        Args:
            id: Page ID
            data: Update data (properties, archived, icon, cover)
            
        Returns:
            Updated page
            
        Raises:
            RepositoryError: If update fails
        """
        with self._operation_context("update", id):
            try:
                # Prepare update data
                update_data = {}
                
                # Update properties if provided
                if "properties" in data:
                    update_data["properties"] = self._normalize_properties(
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
                    f"pages/{id}",
                    data=update_data,
                )
                
                # Validate response
                page = validate_notion_response(response, ObjectType.PAGE)
                
                # Log data access
                self._log_data_access(
                    "update",
                    id,
                    fields=list(update_data.keys())
                )
                
                return page
                
            except Exception as e:
                raise RepositoryError(f"Failed to update page {id}: {str(e)}")
    
    def delete(self, id: str) -> bool:
        """Archive page (Notion doesn't support hard delete).
        
        Args:
            id: Page ID
            
        Returns:
            True if archived
            
        Raises:
            RepositoryError: If deletion fails
        """
        with self._operation_context("delete", id):
            try:
                # Archive the page
                self.update(id, {"archived": True})
                
                # Log data access
                self._log_data_access("delete", id)
                
                return True
                
            except Exception as e:
                raise RepositoryError(f"Failed to delete page {id}: {str(e)}")
    
    def get_properties(self, id: str, property_names: List[str]) -> Dict[str, Any]:
        """Get specific properties from a page.
        
        Args:
            id: Page ID
            property_names: List of property names to retrieve
            
        Returns:
            Dictionary of property values
        """
        page = self.get_by_id(id)
        
        properties = {}
        for name in property_names:
            if name in page.properties:
                prop_data = page.properties[name]
                # Parse property value
                prop_value = parse_property_value(prop_data)
                if prop_value:
                    # Extract plain value
                    handler = property_handler_registry.get_handler(prop_value.type)
                    properties[name] = handler.extract_plain_value(prop_value)
                else:
                    properties[name] = None
            else:
                properties[name] = None
        
        return properties
    
    def update_property(self, id: str, property_name: str, value: Any) -> NotionPage:
        """Update a single property.
        
        Args:
            id: Page ID
            property_name: Property name
            value: New value
            
        Returns:
            Updated page
        """
        return self.update(id, {"properties": {property_name: value}})
    
    def add_child_page(self, parent_id: str, child_data: Dict[str, Any]) -> NotionPage:
        """Create a child page.
        
        Args:
            parent_id: Parent page ID
            child_data: Child page data
            
        Returns:
            Created child page
        """
        # Set parent
        child_data["parent"] = {"type": "page_id", "page_id": parent_id}
        
        return self.create(child_data)
    
    def _normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize properties for API submission.
        
        Args:
            properties: Raw property values
            
        Returns:
            Normalized properties
        """
        normalized = {}
        
        for name, value in properties.items():
            # Skip None values
            if value is None:
                continue
            
            # If already formatted for API, use as-is
            if isinstance(value, dict) and "type" in value:
                normalized[name] = value
            else:
                # Need to infer type and format
                # This is a simplified version - in production would need
                # to look up the property type from the database schema
                if isinstance(value, str):
                    # Could be title, rich_text, select, etc.
                    # Default to rich_text for now
                    handler = property_handler_registry.get_handler(PropertyType.RICH_TEXT)
                    normalized[name] = handler.format_for_api(value)
                elif isinstance(value, (int, float)):
                    handler = property_handler_registry.get_handler(PropertyType.NUMBER)
                    normalized[name] = handler.format_for_api(value)
                elif isinstance(value, bool):
                    handler = property_handler_registry.get_handler(PropertyType.CHECKBOX)
                    normalized[name] = handler.format_for_api(value)
                elif isinstance(value, list):
                    # Could be multi_select, people, files, etc.
                    # Default to multi_select for now
                    handler = property_handler_registry.get_handler(PropertyType.MULTI_SELECT)
                    normalized[name] = handler.format_for_api(value)
                else:
                    # Convert to string and use rich_text
                    handler = property_handler_registry.get_handler(PropertyType.RICH_TEXT)
                    normalized[name] = handler.format_for_api(str(value))
        
        return normalized
    
    def _execute_api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute the actual API call using the Notion client."""
        if method == "GET" and endpoint.startswith("pages/"):
            page_id = endpoint.replace("pages/", "")
            return self.client.pages.retrieve(page_id=page_id)
        elif method == "POST" and endpoint == "pages":
            return self.client.pages.create(**data)
        elif method == "PATCH" and endpoint.startswith("pages/"):
            page_id = endpoint.replace("pages/", "")
            return self.client.pages.update(page_id=page_id, **data)
        else:
            raise NotImplementedError(f"Unsupported operation: {method} {endpoint}")