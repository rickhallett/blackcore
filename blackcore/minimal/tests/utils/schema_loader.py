"""Schema loader and validator for Notion API documentation compliance."""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class SchemaType(Enum):
    """Types of schema definitions."""
    OBJECT = "object"
    ARRAY = "array" 
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    NULL = "null"
    ANY = "any"
    UNION = "union"
    ENUM = "enum"


@dataclass
class SchemaDefinition:
    """A schema definition from API documentation."""
    name: str
    type: SchemaType
    description: Optional[str] = None
    required: bool = True
    nullable: bool = False
    properties: Dict[str, 'SchemaDefinition'] = field(default_factory=dict)
    items: Optional['SchemaDefinition'] = None  # For arrays
    enum_values: Optional[List[Any]] = None  # For enums
    union_types: Optional[List['SchemaDefinition']] = None  # For unions
    pattern: Optional[str] = None  # For string validation
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    format: Optional[str] = None  # e.g., "date-time", "email", "uri"


class NotionAPISchemaLoader:
    """Loads and manages Notion API schemas from documentation."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        self.schema_dir = schema_dir or Path(__file__).parent / "schemas"
        self.schemas: Dict[str, SchemaDefinition] = {}
        self._load_builtin_schemas()
    
    def _load_builtin_schemas(self):
        """Load built-in Notion API schemas based on documentation."""
        # Page object schema
        self.schemas["page"] = SchemaDefinition(
            name="page",
            type=SchemaType.OBJECT,
            description="A Notion page object",
            properties={
                "object": SchemaDefinition(
                    name="object",
                    type=SchemaType.ENUM,
                    enum_values=["page"],
                    description="Always 'page'"
                ),
                "id": SchemaDefinition(
                    name="id",
                    type=SchemaType.STRING,
                    pattern=r"^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$",
                    description="Unique identifier for the page"
                ),
                "created_time": SchemaDefinition(
                    name="created_time",
                    type=SchemaType.STRING,
                    format="date-time",
                    description="Date and time when page was created"
                ),
                "created_by": SchemaDefinition(
                    name="created_by",
                    type=SchemaType.OBJECT,
                    description="User who created the page",
                    properties={
                        "object": SchemaDefinition(name="object", type=SchemaType.STRING),
                        "id": SchemaDefinition(name="id", type=SchemaType.STRING)
                    }
                ),
                "last_edited_time": SchemaDefinition(
                    name="last_edited_time",
                    type=SchemaType.STRING,
                    format="date-time",
                    description="Date and time when page was last edited"
                ),
                "last_edited_by": SchemaDefinition(
                    name="last_edited_by",
                    type=SchemaType.OBJECT,
                    description="User who last edited the page",
                    properties={
                        "object": SchemaDefinition(name="object", type=SchemaType.STRING),
                        "id": SchemaDefinition(name="id", type=SchemaType.STRING)
                    }
                ),
                "archived": SchemaDefinition(
                    name="archived",
                    type=SchemaType.BOOLEAN,
                    description="Whether the page is archived"
                ),
                "icon": SchemaDefinition(
                    name="icon",
                    type=SchemaType.OBJECT,
                    nullable=True,
                    required=False,
                    description="Page icon"
                ),
                "cover": SchemaDefinition(
                    name="cover",
                    type=SchemaType.OBJECT,
                    nullable=True,
                    required=False,
                    description="Page cover image"
                ),
                "properties": SchemaDefinition(
                    name="properties",
                    type=SchemaType.OBJECT,
                    description="Page property values"
                ),
                "parent": SchemaDefinition(
                    name="parent",
                    type=SchemaType.OBJECT,
                    description="Parent of the page",
                    properties={
                        "type": SchemaDefinition(
                            name="type",
                            type=SchemaType.ENUM,
                            enum_values=["database_id", "page_id", "workspace"],
                        ),
                        "database_id": SchemaDefinition(
                            name="database_id",
                            type=SchemaType.STRING,
                            required=False
                        ),
                        "page_id": SchemaDefinition(
                            name="page_id",
                            type=SchemaType.STRING,
                            required=False
                        ),
                        "workspace": SchemaDefinition(
                            name="workspace",
                            type=SchemaType.BOOLEAN,
                            required=False
                        )
                    }
                ),
                "url": SchemaDefinition(
                    name="url",
                    type=SchemaType.STRING,
                    format="uri",
                    description="The URL of the Notion page"
                )
            }
        )
        
        # Database query response schema
        self.schemas["database_query_response"] = SchemaDefinition(
            name="database_query_response",
            type=SchemaType.OBJECT,
            description="Response from database query endpoint",
            properties={
                "object": SchemaDefinition(
                    name="object",
                    type=SchemaType.ENUM,
                    enum_values=["list"]
                ),
                "results": SchemaDefinition(
                    name="results",
                    type=SchemaType.ARRAY,
                    items=self.schemas["page"],
                    description="Array of page objects"
                ),
                "next_cursor": SchemaDefinition(
                    name="next_cursor",
                    type=SchemaType.STRING,
                    nullable=True,
                    description="Cursor for pagination"
                ),
                "has_more": SchemaDefinition(
                    name="has_more",
                    type=SchemaType.BOOLEAN,
                    description="Whether there are more results"
                ),
                "type": SchemaDefinition(
                    name="type",
                    type=SchemaType.STRING,
                    required=False,
                    description="Type of results"
                ),
                "page": SchemaDefinition(
                    name="page",
                    type=SchemaType.OBJECT,
                    required=False,
                    description="Pagination info"
                )
            }
        )
        
        # Rich text schema
        self.schemas["rich_text"] = SchemaDefinition(
            name="rich_text",
            type=SchemaType.OBJECT,
            description="Rich text object",
            properties={
                "type": SchemaDefinition(
                    name="type",
                    type=SchemaType.ENUM,
                    enum_values=["text", "mention", "equation"]
                ),
                "text": SchemaDefinition(
                    name="text",
                    type=SchemaType.OBJECT,
                    required=False,
                    properties={
                        "content": SchemaDefinition(name="content", type=SchemaType.STRING),
                        "link": SchemaDefinition(
                            name="link",
                            type=SchemaType.OBJECT,
                            nullable=True,
                            required=False,
                            properties={
                                "url": SchemaDefinition(name="url", type=SchemaType.STRING, format="uri")
                            }
                        )
                    }
                ),
                "annotations": SchemaDefinition(
                    name="annotations",
                    type=SchemaType.OBJECT,
                    required=False,
                    properties={
                        "bold": SchemaDefinition(name="bold", type=SchemaType.BOOLEAN, required=False),
                        "italic": SchemaDefinition(name="italic", type=SchemaType.BOOLEAN, required=False),
                        "strikethrough": SchemaDefinition(name="strikethrough", type=SchemaType.BOOLEAN, required=False),
                        "underline": SchemaDefinition(name="underline", type=SchemaType.BOOLEAN, required=False),
                        "code": SchemaDefinition(name="code", type=SchemaType.BOOLEAN, required=False),
                        "color": SchemaDefinition(
                            name="color",
                            type=SchemaType.ENUM,
                            required=False,
                            enum_values=["default", "gray", "brown", "orange", "yellow", 
                                       "green", "blue", "purple", "pink", "red"]
                        )
                    }
                ),
                "plain_text": SchemaDefinition(name="plain_text", type=SchemaType.STRING, required=False),
                "href": SchemaDefinition(name="href", type=SchemaType.STRING, nullable=True, required=False)
            }
        )
        
        # Property schemas
        self._load_property_schemas()
    
    def _load_property_schemas(self):
        """Load property type schemas."""
        # Title property
        self.schemas["property_title"] = SchemaDefinition(
            name="property_title",
            type=SchemaType.OBJECT,
            properties={
                "id": SchemaDefinition(name="id", type=SchemaType.STRING, required=False),
                "type": SchemaDefinition(name="type", type=SchemaType.ENUM, enum_values=["title"]),
                "title": SchemaDefinition(
                    name="title",
                    type=SchemaType.ARRAY,
                    items=self.schemas["rich_text"]
                )
            }
        )
        
        # Number property
        self.schemas["property_number"] = SchemaDefinition(
            name="property_number",
            type=SchemaType.OBJECT,
            properties={
                "id": SchemaDefinition(name="id", type=SchemaType.STRING, required=False),
                "type": SchemaDefinition(name="type", type=SchemaType.ENUM, enum_values=["number"]),
                "number": SchemaDefinition(
                    name="number",
                    type=SchemaType.NUMBER,
                    nullable=True
                )
            }
        )
        
        # Select property
        self.schemas["property_select"] = SchemaDefinition(
            name="property_select",
            type=SchemaType.OBJECT,
            properties={
                "id": SchemaDefinition(name="id", type=SchemaType.STRING, required=False),
                "type": SchemaDefinition(name="type", type=SchemaType.ENUM, enum_values=["select"]),
                "select": SchemaDefinition(
                    name="select",
                    type=SchemaType.OBJECT,
                    nullable=True,
                    properties={
                        "id": SchemaDefinition(name="id", type=SchemaType.STRING, required=False),
                        "name": SchemaDefinition(name="name", type=SchemaType.STRING),
                        "color": SchemaDefinition(
                            name="color",
                            type=SchemaType.ENUM,
                            enum_values=["default", "gray", "brown", "orange", "yellow",
                                       "green", "blue", "purple", "pink", "red"]
                        )
                    }
                )
            }
        )
        
        # Add more property schemas as needed...
    
    def load_schema_from_file(self, file_path: Path) -> Optional[SchemaDefinition]:
        """Load a schema from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return self._parse_schema_data(data)
        except Exception as e:
            print(f"Error loading schema from {file_path}: {e}")
            return None
    
    def _parse_schema_data(self, data: Dict[str, Any]) -> SchemaDefinition:
        """Parse schema data into SchemaDefinition."""
        schema_type = SchemaType(data.get("type", "object"))
        
        schema = SchemaDefinition(
            name=data.get("name", ""),
            type=schema_type,
            description=data.get("description"),
            required=data.get("required", True),
            nullable=data.get("nullable", False),
            pattern=data.get("pattern"),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            format=data.get("format"),
            enum_values=data.get("enum")
        )
        
        # Parse properties for objects
        if schema_type == SchemaType.OBJECT and "properties" in data:
            for prop_name, prop_data in data["properties"].items():
                schema.properties[prop_name] = self._parse_schema_data(prop_data)
        
        # Parse items for arrays
        if schema_type == SchemaType.ARRAY and "items" in data:
            schema.items = self._parse_schema_data(data["items"])
        
        # Parse union types
        if "oneOf" in data or "anyOf" in data:
            schema.type = SchemaType.UNION
            union_data = data.get("oneOf", data.get("anyOf", []))
            schema.union_types = [self._parse_schema_data(u) for u in union_data]
        
        return schema
    
    def get_schema(self, schema_name: str) -> Optional[SchemaDefinition]:
        """Get a schema by name."""
        return self.schemas.get(schema_name)
    
    def register_schema(self, schema: SchemaDefinition):
        """Register a new schema."""
        self.schemas[schema.name] = schema


class SchemaValidator:
    """Validates data against schema definitions."""
    
    def __init__(self, schema_loader: Optional[NotionAPISchemaLoader] = None):
        self.schema_loader = schema_loader or NotionAPISchemaLoader()
    
    def validate(self, data: Any, schema: Union[str, SchemaDefinition]) -> List[str]:
        """Validate data against a schema."""
        if isinstance(schema, str):
            schema_def = self.schema_loader.get_schema(schema)
            if not schema_def:
                return [f"Schema '{schema}' not found"]
            schema = schema_def
        
        return self._validate_value(data, schema, path="")
    
    def _validate_value(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate a value against a schema definition."""
        errors = []
        field_path = f"{path}.{schema.name}" if path else schema.name
        
        # Check null/None
        if value is None:
            if schema.required and not schema.nullable:
                errors.append(f"Required field missing: {field_path}")
            return errors
        
        # Validate based on type
        if schema.type == SchemaType.OBJECT:
            errors.extend(self._validate_object(value, schema, field_path))
        elif schema.type == SchemaType.ARRAY:
            errors.extend(self._validate_array(value, schema, field_path))
        elif schema.type == SchemaType.STRING:
            errors.extend(self._validate_string(value, schema, field_path))
        elif schema.type == SchemaType.NUMBER:
            errors.extend(self._validate_number(value, schema, field_path))
        elif schema.type == SchemaType.BOOLEAN:
            errors.extend(self._validate_boolean(value, schema, field_path))
        elif schema.type == SchemaType.ENUM:
            errors.extend(self._validate_enum(value, schema, field_path))
        elif schema.type == SchemaType.UNION:
            errors.extend(self._validate_union(value, schema, field_path))
        
        return errors
    
    def _validate_object(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate an object."""
        errors = []
        
        if not isinstance(value, dict):
            errors.append(f"Expected object at {path}, got {type(value).__name__}")
            return errors
        
        # Validate properties
        for prop_name, prop_schema in schema.properties.items():
            prop_value = value.get(prop_name)
            errors.extend(self._validate_value(prop_value, prop_schema, path))
        
        # Check for unexpected properties (could be a warning)
        expected_props = set(schema.properties.keys())
        actual_props = set(value.keys())
        unexpected = actual_props - expected_props
        
        # For now, we'll just note unexpected properties as info
        # In strict mode, these could be errors
        
        return errors
    
    def _validate_array(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate an array."""
        errors = []
        
        if not isinstance(value, list):
            errors.append(f"Expected array at {path}, got {type(value).__name__}")
            return errors
        
        # Validate each item
        if schema.items:
            for i, item in enumerate(value):
                errors.extend(self._validate_value(item, schema.items, f"{path}[{i}]"))
        
        return errors
    
    def _validate_string(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate a string."""
        errors = []
        
        if not isinstance(value, str):
            errors.append(f"Expected string at {path}, got {type(value).__name__}")
            return errors
        
        # Check pattern
        if schema.pattern:
            if not re.match(schema.pattern, value):
                errors.append(f"String at {path} does not match pattern: {schema.pattern}")
        
        # Check format
        if schema.format:
            if not self._validate_format(value, schema.format):
                errors.append(f"String at {path} does not match format: {schema.format}")
        
        return errors
    
    def _validate_number(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate a number."""
        errors = []
        
        if not isinstance(value, (int, float)):
            errors.append(f"Expected number at {path}, got {type(value).__name__}")
            return errors
        
        # Check minimum
        if schema.minimum is not None and value < schema.minimum:
            errors.append(f"Number at {path} is below minimum: {value} < {schema.minimum}")
        
        # Check maximum
        if schema.maximum is not None and value > schema.maximum:
            errors.append(f"Number at {path} is above maximum: {value} > {schema.maximum}")
        
        return errors
    
    def _validate_boolean(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate a boolean."""
        errors = []
        
        if not isinstance(value, bool):
            errors.append(f"Expected boolean at {path}, got {type(value).__name__}")
        
        return errors
    
    def _validate_enum(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate an enum value."""
        errors = []
        
        if schema.enum_values and value not in schema.enum_values:
            errors.append(f"Value at {path} not in allowed values: {value} not in {schema.enum_values}")
        
        return errors
    
    def _validate_union(self, value: Any, schema: SchemaDefinition, path: str) -> List[str]:
        """Validate a union type (oneOf/anyOf)."""
        if not schema.union_types:
            return []
        
        # Try each union type
        for union_schema in schema.union_types:
            errors = self._validate_value(value, union_schema, path)
            if not errors:
                # Valid for at least one type
                return []
        
        # Not valid for any type
        return [f"Value at {path} does not match any of the expected types"]
    
    def _validate_format(self, value: str, format_type: str) -> bool:
        """Validate string format."""
        if format_type == "date-time":
            # ISO 8601 datetime
            try:
                from datetime import datetime
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                datetime.fromisoformat(value)
                return True
            except:
                return False
        elif format_type == "email":
            return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value))
        elif format_type == "uri":
            return bool(re.match(r"^https?://[^\s]+$", value))
        
        # Unknown format, assume valid
        return True