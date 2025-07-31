"""Tests for schema validation against API documentation."""

import pytest
from datetime import datetime
from blackcore.minimal.tests.utils.schema_loader import (
    SchemaType,
    SchemaDefinition,
    NotionAPISchemaLoader,
    SchemaValidator
)


class TestSchemaDefinition:
    """Test schema definition structures."""
    
    def test_create_simple_schema(self):
        """Test creating a simple schema definition."""
        schema = SchemaDefinition(
            name="test_string",
            type=SchemaType.STRING,
            description="A test string field",
            required=True,
            nullable=False
        )
        
        assert schema.name == "test_string"
        assert schema.type == SchemaType.STRING
        assert schema.required is True
        assert schema.nullable is False
    
    def test_create_object_schema(self):
        """Test creating an object schema with properties."""
        schema = SchemaDefinition(
            name="test_object",
            type=SchemaType.OBJECT,
            properties={
                "field1": SchemaDefinition(name="field1", type=SchemaType.STRING),
                "field2": SchemaDefinition(name="field2", type=SchemaType.NUMBER, nullable=True)
            }
        )
        
        assert schema.type == SchemaType.OBJECT
        assert len(schema.properties) == 2
        assert schema.properties["field1"].type == SchemaType.STRING
        assert schema.properties["field2"].nullable is True
    
    def test_create_array_schema(self):
        """Test creating an array schema."""
        item_schema = SchemaDefinition(name="item", type=SchemaType.STRING)
        schema = SchemaDefinition(
            name="test_array",
            type=SchemaType.ARRAY,
            items=item_schema
        )
        
        assert schema.type == SchemaType.ARRAY
        assert schema.items is not None
        assert schema.items.type == SchemaType.STRING
    
    def test_create_enum_schema(self):
        """Test creating an enum schema."""
        schema = SchemaDefinition(
            name="color",
            type=SchemaType.ENUM,
            enum_values=["red", "green", "blue"]
        )
        
        assert schema.type == SchemaType.ENUM
        assert len(schema.enum_values) == 3
        assert "red" in schema.enum_values


class TestNotionAPISchemaLoader:
    """Test Notion API schema loader."""
    
    def test_builtin_schemas_loaded(self):
        """Test that built-in schemas are loaded."""
        loader = NotionAPISchemaLoader()
        
        # Check page schema
        page_schema = loader.get_schema("page")
        assert page_schema is not None
        assert page_schema.type == SchemaType.OBJECT
        assert "id" in page_schema.properties
        assert "properties" in page_schema.properties
        
        # Check database query response schema
        query_schema = loader.get_schema("database_query_response")
        assert query_schema is not None
        assert "results" in query_schema.properties
        assert "has_more" in query_schema.properties
    
    def test_property_schemas_loaded(self):
        """Test that property schemas are loaded."""
        loader = NotionAPISchemaLoader()
        
        # Check title property
        title_schema = loader.get_schema("property_title")
        assert title_schema is not None
        assert "title" in title_schema.properties
        assert title_schema.properties["title"].type == SchemaType.ARRAY
        
        # Check number property
        number_schema = loader.get_schema("property_number")
        assert number_schema is not None
        assert "number" in number_schema.properties
        assert number_schema.properties["number"].nullable is True
    
    def test_register_custom_schema(self):
        """Test registering a custom schema."""
        loader = NotionAPISchemaLoader()
        
        custom_schema = SchemaDefinition(
            name="custom_type",
            type=SchemaType.OBJECT,
            properties={
                "custom_field": SchemaDefinition(name="custom_field", type=SchemaType.STRING)
            }
        )
        
        loader.register_schema(custom_schema)
        
        retrieved = loader.get_schema("custom_type")
        assert retrieved is not None
        assert retrieved.name == "custom_type"
        assert "custom_field" in retrieved.properties


class TestSchemaValidator:
    """Test schema validation."""
    
    def test_validate_simple_types(self):
        """Test validation of simple types."""
        validator = SchemaValidator()
        
        # String validation
        string_schema = SchemaDefinition(name="test", type=SchemaType.STRING)
        assert validator.validate("hello", string_schema) == []
        assert len(validator.validate(123, string_schema)) > 0
        
        # Number validation
        number_schema = SchemaDefinition(name="test", type=SchemaType.NUMBER)
        assert validator.validate(42, number_schema) == []
        assert validator.validate(3.14, number_schema) == []
        assert len(validator.validate("not a number", number_schema)) > 0
        
        # Boolean validation
        bool_schema = SchemaDefinition(name="test", type=SchemaType.BOOLEAN)
        assert validator.validate(True, bool_schema) == []
        assert validator.validate(False, bool_schema) == []
        assert len(validator.validate(1, bool_schema)) > 0
    
    def test_validate_nullable_fields(self):
        """Test validation of nullable fields."""
        validator = SchemaValidator()
        
        # Non-nullable field
        non_nullable = SchemaDefinition(name="test", type=SchemaType.STRING, nullable=False)
        errors = validator.validate(None, non_nullable)
        assert len(errors) > 0
        assert "Required field missing" in errors[0]
        
        # Nullable field
        nullable = SchemaDefinition(name="test", type=SchemaType.STRING, nullable=True)
        assert validator.validate(None, nullable) == []
        assert validator.validate("value", nullable) == []
    
    def test_validate_enum(self):
        """Test enum validation."""
        validator = SchemaValidator()
        
        enum_schema = SchemaDefinition(
            name="status",
            type=SchemaType.ENUM,
            enum_values=["active", "inactive", "pending"]
        )
        
        assert validator.validate("active", enum_schema) == []
        assert validator.validate("pending", enum_schema) == []
        
        errors = validator.validate("invalid", enum_schema)
        assert len(errors) > 0
        assert "not in allowed values" in errors[0]
    
    def test_validate_pattern(self):
        """Test string pattern validation."""
        validator = SchemaValidator()
        
        uuid_schema = SchemaDefinition(
            name="id",
            type=SchemaType.STRING,
            pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
        )
        
        assert validator.validate("12345678-90ab-cdef-1234-567890abcdef", uuid_schema) == []
        
        errors = validator.validate("not-a-uuid", uuid_schema)
        assert len(errors) > 0
        assert "does not match pattern" in errors[0]
    
    def test_validate_format(self):
        """Test string format validation."""
        validator = SchemaValidator()
        
        # Date-time format
        datetime_schema = SchemaDefinition(
            name="timestamp",
            type=SchemaType.STRING,
            format="date-time"
        )
        
        assert validator.validate("2025-01-15T10:00:00Z", datetime_schema) == []
        assert len(validator.validate("not a date", datetime_schema)) > 0
        
        # Email format
        email_schema = SchemaDefinition(
            name="email",
            type=SchemaType.STRING,
            format="email"
        )
        
        assert validator.validate("test@example.com", email_schema) == []
        assert len(validator.validate("not-an-email", email_schema)) > 0
        
        # URI format
        uri_schema = SchemaDefinition(
            name="url",
            type=SchemaType.STRING,
            format="uri"
        )
        
        assert validator.validate("https://example.com", uri_schema) == []
        assert len(validator.validate("not a url", uri_schema)) > 0
    
    def test_validate_number_constraints(self):
        """Test number constraint validation."""
        validator = SchemaValidator()
        
        constrained_schema = SchemaDefinition(
            name="score",
            type=SchemaType.NUMBER,
            minimum=0,
            maximum=100
        )
        
        assert validator.validate(50, constrained_schema) == []
        assert validator.validate(0, constrained_schema) == []
        assert validator.validate(100, constrained_schema) == []
        
        errors = validator.validate(-10, constrained_schema)
        assert len(errors) > 0
        assert "below minimum" in errors[0]
        
        errors = validator.validate(150, constrained_schema)
        assert len(errors) > 0
        assert "above maximum" in errors[0]
    
    def test_validate_object(self):
        """Test object validation."""
        validator = SchemaValidator()
        
        person_schema = SchemaDefinition(
            name="person",
            type=SchemaType.OBJECT,
            properties={
                "name": SchemaDefinition(name="name", type=SchemaType.STRING),
                "age": SchemaDefinition(name="age", type=SchemaType.NUMBER),
                "email": SchemaDefinition(
                    name="email", 
                    type=SchemaType.STRING, 
                    format="email",
                    nullable=True
                )
            }
        )
        
        # Valid object
        valid_person = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        assert validator.validate(valid_person, person_schema) == []
        
        # Missing required field
        invalid_person = {
            "age": 30
        }
        errors = validator.validate(invalid_person, person_schema)
        assert len(errors) > 0
        assert "name" in errors[0]
        
        # Invalid type
        invalid_type = {
            "name": "John",
            "age": "thirty",  # Should be number
            "email": None
        }
        errors = validator.validate(invalid_type, invalid_type)
        assert len(errors) > 0
    
    def test_validate_array(self):
        """Test array validation."""
        validator = SchemaValidator()
        
        string_array_schema = SchemaDefinition(
            name="tags",
            type=SchemaType.ARRAY,
            items=SchemaDefinition(name="tag", type=SchemaType.STRING)
        )
        
        # Valid array
        assert validator.validate(["tag1", "tag2", "tag3"], string_array_schema) == []
        
        # Invalid - not an array
        errors = validator.validate("not an array", string_array_schema)
        assert len(errors) > 0
        assert "Expected array" in errors[0]
        
        # Invalid item type
        errors = validator.validate(["tag1", 123, "tag3"], string_array_schema)
        assert len(errors) > 0
        assert "[1]" in errors[0]  # Error at index 1
    
    def test_validate_notion_page_response(self):
        """Test validation of a Notion page response."""
        validator = SchemaValidator()
        
        # Valid page response
        page_response = {
            "object": "page",
            "id": "12345678-90ab-cdef-1234-567890abcdef",
            "created_time": "2025-01-15T10:00:00Z",
            "created_by": {"object": "user", "id": "user-123"},
            "last_edited_time": "2025-01-15T10:30:00Z",
            "last_edited_by": {"object": "user", "id": "user-123"},
            "archived": False,
            "properties": {},
            "parent": {
                "type": "database_id",
                "database_id": "db-123"
            },
            "url": "https://notion.so/page-123"
        }
        
        errors = validator.validate(page_response, "page")
        assert errors == []
        
        # Invalid - missing required field
        invalid_page = page_response.copy()
        del invalid_page["created_time"]
        
        errors = validator.validate(invalid_page, "page")
        assert len(errors) > 0
        assert "created_time" in errors[0]
    
    def test_validate_union_type(self):
        """Test union type validation."""
        validator = SchemaValidator()
        
        # Create a union schema (string or number)
        union_schema = SchemaDefinition(
            name="string_or_number",
            type=SchemaType.UNION,
            union_types=[
                SchemaDefinition(name="string_option", type=SchemaType.STRING),
                SchemaDefinition(name="number_option", type=SchemaType.NUMBER)
            ]
        )
        
        # Valid values
        assert validator.validate("hello", union_schema) == []
        assert validator.validate(42, union_schema) == []
        
        # Invalid value
        errors = validator.validate(True, union_schema)
        assert len(errors) > 0
        assert "does not match any of the expected types" in errors[0]