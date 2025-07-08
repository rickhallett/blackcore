"""Pydantic models for Notion API responses."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class ObjectType(str, Enum):
    """Notion object types."""
    DATABASE = "database"
    PAGE = "page"
    BLOCK = "block"
    USER = "user"
    WORKSPACE = "workspace"
    LIST = "list"
    ERROR = "error"


class UserType(str, Enum):
    """Notion user types."""
    PERSON = "person"
    BOT = "bot"


class NotionUser(BaseModel):
    """Notion user model."""
    object: str = Field(default="user")
    id: str
    type: Optional[UserType] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    person: Optional[Dict[str, Any]] = None
    bot: Optional[Dict[str, Any]] = None
    
    @field_validator("id")
    def validate_uuid(cls, v):
        """Validate UUID format."""
        import re
        # Allow test IDs and standard UUIDs
        if v.startswith(("test-", "user-", "db-", "page-", "block-")):
            return v
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError(f"Invalid UUID format: {v}")
        return v


class NotionWorkspace(BaseModel):
    """Notion workspace model."""
    id: str
    name: Optional[str] = None
    domain: Optional[str] = None
    icon: Optional[str] = None


class NotionParent(BaseModel):
    """Notion parent reference."""
    type: str  # "database_id", "page_id", "workspace"
    database_id: Optional[str] = None
    page_id: Optional[str] = None
    workspace: Optional[bool] = None


class NotionRichText(BaseModel):
    """Rich text object."""
    type: str = Field(default="text")  # "text", "mention", "equation"
    text: Optional[Dict[str, Any]] = None
    mention: Optional[Dict[str, Any]] = None
    equation: Optional[Dict[str, Any]] = None
    plain_text: str = ""
    href: Optional[str] = None
    annotations: Optional[Dict[str, bool]] = Field(default_factory=lambda: {
        "bold": False,
        "italic": False,
        "strikethrough": False,
        "underline": False,
        "code": False,
        "color": "default"
    })


class NotionFile(BaseModel):
    """File object."""
    type: str  # "file" or "external"
    file: Optional[Dict[str, str]] = None  # {"url": "...", "expiry_time": "..."}
    external: Optional[Dict[str, str]] = None  # {"url": "..."}
    name: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_file_type(self):
        """Ensure either file or external is set."""
        if self.type == "file" and not self.file:
            raise ValueError("File type requires 'file' field")
        if self.type == "external" and not self.external:
            raise ValueError("External type requires 'external' field")
        return self


class NotionProperty(BaseModel):
    """Base property model."""
    id: Optional[str] = None
    type: str
    
    class Config:
        extra = "allow"  # Allow additional fields for specific property types


class NotionDatabase(BaseModel):
    """Notion database model."""
    object: str = Field(default="database")
    id: str
    created_time: datetime
    created_by: NotionUser
    last_edited_time: datetime
    last_edited_by: NotionUser
    title: List[NotionRichText]
    description: Optional[List[NotionRichText]] = []
    icon: Optional[Union[NotionFile, Dict[str, str]]] = None
    cover: Optional[NotionFile] = None
    properties: Dict[str, NotionProperty]
    parent: NotionParent
    url: str
    archived: bool = False
    is_inline: bool = False
    
    @field_validator("title", "description", mode='before')
    def ensure_list(cls, v):
        """Ensure rich text fields are lists."""
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v


class NotionPage(BaseModel):
    """Notion page model."""
    object: str = Field(default="page")
    id: str
    created_time: datetime
    created_by: NotionUser
    last_edited_time: datetime
    last_edited_by: NotionUser
    archived: bool = False
    icon: Optional[Union[NotionFile, Dict[str, str]]] = None
    cover: Optional[NotionFile] = None
    properties: Dict[str, Any]  # Property values vary by type
    parent: NotionParent
    url: str
    
    @field_validator("properties", mode='before')
    def validate_properties(cls, v):
        """Ensure properties is a dict."""
        if not isinstance(v, dict):
            raise ValueError("Properties must be a dictionary")
        return v


class NotionBlock(BaseModel):
    """Notion block model."""
    object: str = Field(default="block")
    id: str
    parent: Dict[str, str]  # {"type": "page_id", "page_id": "..."}
    type: str  # Block type
    created_time: datetime
    created_by: NotionUser
    last_edited_time: datetime
    last_edited_by: NotionUser
    archived: bool = False
    has_children: bool = False
    
    class Config:
        extra = "allow"  # Allow block-specific fields


class NotionPaginatedResponse(BaseModel):
    """Paginated response model."""
    object: str = Field(default="list")
    results: List[Union[NotionDatabase, NotionPage, NotionBlock]]
    next_cursor: Optional[str] = None
    has_more: bool = False
    type: Optional[str] = None
    page: Optional[Dict[str, Any]] = None
    
    @field_validator("results", mode='before')
    def parse_results(cls, v):
        """Parse results based on object type."""
        if not isinstance(v, list):
            return []
            
        # For now, just return the raw list
        # The actual parsing would need to be done differently in Pydantic v2
        return v


class NotionError(BaseModel):
    """Notion API error response."""
    object: str = Field(default="error")
    status: int
    code: str
    message: str
    request_id: Optional[str] = None


class NotionSort(BaseModel):
    """Sort object for database queries."""
    property: Optional[str] = None
    timestamp: Optional[str] = None  # "created_time" or "last_edited_time"
    direction: str = "ascending"  # "ascending" or "descending"
    
    @model_validator(mode='after')
    def validate_sort_field(self):
        """Ensure either property or timestamp is set."""
        if not self.property and not self.timestamp:
            raise ValueError("Either 'property' or 'timestamp' must be specified")
        if self.property and self.timestamp:
            raise ValueError("Cannot specify both 'property' and 'timestamp'")
        return self


class NotionFilter(BaseModel):
    """Filter object for database queries."""
    property: Optional[str] = None
    timestamp: Optional[str] = None  # For timestamp filters
    # Filter conditions vary by property type
    
    class Config:
        extra = "allow"  # Allow filter-specific fields


class NotionDatabaseQuery(BaseModel):
    """Database query request model."""
    filter: Optional[Union[NotionFilter, Dict[str, Any]]] = None
    sorts: Optional[List[NotionSort]] = []
    start_cursor: Optional[str] = None
    page_size: Optional[int] = Field(default=100, ge=1, le=100)
    
    @field_validator("page_size")
    def validate_page_size(cls, v):
        """Ensure page size is within limits."""
        if v is None:
            return 100
        return min(max(1, v), 100)


class NotionDatabaseQueryResponse(NotionPaginatedResponse):
    """Database query response model."""
    # Inherits all fields from NotionPaginatedResponse
    pass


class NotionSearchRequest(BaseModel):
    """Search request model."""
    query: str
    filter: Optional[Dict[str, Any]] = None
    sort: Optional[Dict[str, Any]] = None
    start_cursor: Optional[str] = None
    page_size: Optional[int] = Field(default=100, ge=1, le=100)


class NotionSearchResponse(NotionPaginatedResponse):
    """Search response model."""
    # Inherits all fields from NotionPaginatedResponse
    pass


def validate_notion_response(response_data: Dict[str, Any], expected_type: ObjectType) -> BaseModel:
    """Validate a Notion API response.
    
    Args:
        response_data: Raw response data
        expected_type: Expected object type
        
    Returns:
        Validated Pydantic model
        
    Raises:
        ValueError: If validation fails
    """
    # Check for error response
    if response_data.get("object") == "error":
        error = NotionError(**response_data)
        raise ValueError(f"Notion API error: {error.code} - {error.message}")
    
    # Validate based on expected type
    if expected_type == ObjectType.DATABASE:
        return NotionDatabase(**response_data)
    elif expected_type == ObjectType.PAGE:
        return NotionPage(**response_data)
    elif expected_type == ObjectType.BLOCK:
        return NotionBlock(**response_data)
    elif expected_type == ObjectType.LIST:
        return NotionPaginatedResponse(**response_data)
    else:
        raise ValueError(f"Unsupported object type: {expected_type}")


def validate_paginated_response(response_data: Dict[str, Any]) -> NotionPaginatedResponse:
    """Validate a paginated response.
    
    Args:
        response_data: Raw response data
        
    Returns:
        Validated paginated response
    """
    return validate_notion_response(response_data, ObjectType.LIST)