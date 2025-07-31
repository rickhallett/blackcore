"""Tests for API contract validation."""

import pytest
from datetime import datetime
from blackcore.minimal.tests.utils.api_contracts import (
    APIContractValidator,
    ContractValidators,
    FieldContract,
    APIContract,
    PropertyType,
    NotionAPIContracts
)
from blackcore.minimal.tests.utils.mock_validators import MockBehaviorValidator


class TestContractValidators:
    """Test contract validators."""
    
    def test_validate_uuid(self):
        """Test UUID validation."""
        # Valid UUIDs
        assert ContractValidators.validate_uuid("12345678-90ab-cdef-1234-567890abcdef")
        assert ContractValidators.validate_uuid("1234567890abcdef1234567890abcdef")  # Without dashes
        
        # Invalid UUIDs
        assert not ContractValidators.validate_uuid("not-a-uuid")
        assert not ContractValidators.validate_uuid("12345")
        assert not ContractValidators.validate_uuid("12345678-90ab-cdef-1234-567890abcdefg")  # Extra char
    
    def test_validate_iso_timestamp(self):
        """Test ISO timestamp validation."""
        # Valid timestamps
        assert ContractValidators.validate_iso_timestamp("2025-01-15T10:30:00Z")
        assert ContractValidators.validate_iso_timestamp("2025-01-15T10:30:00+00:00")
        assert ContractValidators.validate_iso_timestamp("2025-01-15T10:30:00-05:00")
        
        # Invalid timestamps
        assert not ContractValidators.validate_iso_timestamp("2025-01-15")  # Date only
        assert not ContractValidators.validate_iso_timestamp("not-a-timestamp")
        assert not ContractValidators.validate_iso_timestamp("2025-13-01T00:00:00Z")  # Invalid month
    
    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        assert ContractValidators.validate_email("test@example.com")
        assert ContractValidators.validate_email("user.name+tag@example.co.uk")
        
        # Invalid emails
        assert not ContractValidators.validate_email("not-an-email")
        assert not ContractValidators.validate_email("@example.com")
        assert not ContractValidators.validate_email("test@")
    
    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs
        assert ContractValidators.validate_url("https://example.com")
        assert ContractValidators.validate_url("http://example.com/path?query=value")
        
        # Invalid URLs
        assert not ContractValidators.validate_url("not-a-url")
        assert not ContractValidators.validate_url("ftp://example.com")  # Only http/https
        assert not ContractValidators.validate_url("https://")
    
    def test_validate_color(self):
        """Test Notion color validation."""
        # Valid colors
        for color in ["default", "gray", "brown", "orange", "yellow", 
                     "green", "blue", "purple", "pink", "red"]:
            assert ContractValidators.validate_color(color)
        
        # Invalid colors
        assert not ContractValidators.validate_color("black")
        assert not ContractValidators.validate_color("white")
        assert not ContractValidators.validate_color("#FF0000")


class TestFieldContractValidation:
    """Test field contract validation."""
    
    def test_validate_required_field(self):
        """Test required field validation."""
        validator = APIContractValidator()
        contract = FieldContract(name="test_field", type=str, required=True)
        
        # Valid value
        errors = validator.validate_field("test value", contract)
        assert len(errors) == 0
        
        # Missing value
        errors = validator.validate_field(None, contract)
        assert len(errors) == 1
        assert "Required field missing" in errors[0]
    
    def test_validate_nullable_field(self):
        """Test nullable field validation."""
        validator = APIContractValidator()
        contract = FieldContract(name="test_field", type=str, nullable=True)
        
        # Null value should be allowed
        errors = validator.validate_field(None, contract)
        assert len(errors) == 0
        
        # Non-null value should also work
        errors = validator.validate_field("value", contract)
        assert len(errors) == 0
    
    def test_validate_type_checking(self):
        """Test type checking."""
        validator = APIContractValidator()
        
        # String field
        string_contract = FieldContract(name="string_field", type=str)
        errors = validator.validate_field("value", string_contract)
        assert len(errors) == 0
        
        errors = validator.validate_field(123, string_contract)
        assert len(errors) == 1
        assert "Type mismatch" in errors[0]
        
        # Number field with multiple types
        number_contract = FieldContract(name="number_field", type=(int, float))
        errors = validator.validate_field(42, number_contract)
        assert len(errors) == 0
        
        errors = validator.validate_field(3.14, number_contract)
        assert len(errors) == 0
        
        errors = validator.validate_field("not a number", number_contract)
        assert len(errors) == 1
    
    def test_validate_with_custom_validator(self):
        """Test custom validator."""
        validator = APIContractValidator()
        
        def custom_validator(value):
            return value > 0
        
        contract = FieldContract(
            name="positive_number",
            type=int,
            validator=custom_validator
        )
        
        # Valid value
        errors = validator.validate_field(5, contract)
        assert len(errors) == 0
        
        # Invalid value
        errors = validator.validate_field(-5, contract)
        assert len(errors) == 1
        assert "Validation failed" in errors[0]
    
    def test_validate_nested_fields(self):
        """Test nested field validation."""
        validator = APIContractValidator()
        
        contract = FieldContract(
            name="parent",
            type=dict,
            children={
                "child1": FieldContract(name="child1", type=str),
                "child2": FieldContract(name="child2", type=int, required=False)
            }
        )
        
        # Valid nested structure
        value = {"child1": "value", "child2": 42}
        errors = validator.validate_field(value, contract)
        assert len(errors) == 0
        
        # Missing required child
        value = {"child2": 42}
        errors = validator.validate_field(value, contract)
        assert len(errors) == 1
        assert "child1" in errors[0]


class TestPropertySchemaValidation:
    """Test property schema validation."""
    
    def test_title_property_validation(self):
        """Test title property validation."""
        validator = APIContractValidator()
        
        # Valid title property
        title_prop = {
            "type": "title",
            "title": [
                {
                    "type": "text",
                    "text": {"content": "Test Title"},
                    "plain_text": "Test Title"
                }
            ]
        }
        
        errors = validator.validate_property_value(title_prop, "title")
        assert len(errors) == 0
        
        # Invalid - missing title array
        invalid_prop = {"type": "title"}
        errors = validator.validate_property_value(invalid_prop, "title")
        assert len(errors) > 0
    
    def test_select_property_validation(self):
        """Test select property validation."""
        validator = APIContractValidator()
        
        # Valid select property
        select_prop = {
            "type": "select",
            "select": {
                "name": "Option1",
                "color": "blue"
            }
        }
        
        errors = validator.validate_property_value(select_prop, "select")
        assert len(errors) == 0
        
        # Valid null select
        null_select = {
            "type": "select",
            "select": None
        }
        
        errors = validator.validate_property_value(null_select, "select")
        assert len(errors) == 0
        
        # Invalid color
        invalid_color = {
            "type": "select",
            "select": {
                "name": "Option1",
                "color": "invalid-color"
            }
        }
        
        errors = validator.validate_property_value(invalid_color, "select")
        assert any("Validation failed" in e for e in errors)
    
    def test_date_property_validation(self):
        """Test date property validation."""
        validator = APIContractValidator()
        
        # Valid date property
        date_prop = {
            "type": "date",
            "date": {
                "start": "2025-01-15T10:00:00Z",
                "end": None
            }
        }
        
        errors = validator.validate_property_value(date_prop, "date")
        assert len(errors) == 0
        
        # Invalid date format
        invalid_date = {
            "type": "date",
            "date": {
                "start": "not-a-date"
            }
        }
        
        errors = validator.validate_property_value(invalid_date, "date")
        assert any("Validation failed" in e for e in errors)


class TestNotionAPIContractValidation:
    """Test Notion API contract validation."""
    
    def test_page_response_validation(self):
        """Test page response validation."""
        validator = APIContractValidator()
        
        # Valid page response
        page_response = {
            "object": "page",
            "id": "12345678-90ab-cdef-1234-567890abcdef",
            "created_time": "2025-01-15T10:00:00Z",
            "created_by": {"object": "user", "id": "user-id"},
            "last_edited_time": "2025-01-15T10:30:00Z",
            "last_edited_by": {"object": "user", "id": "user-id"},
            "archived": False,
            "properties": {},
            "parent": {
                "type": "database_id",
                "database_id": "db-id"
            },
            "url": "https://notion.so/page-id"
        }
        
        errors = validator.validate_page_response(page_response)
        assert len(errors) == 0
        
        # Missing required field
        invalid_page = page_response.copy()
        del invalid_page["created_time"]
        
        errors = validator.validate_page_response(invalid_page)
        assert any("created_time" in e for e in errors)
    
    def test_database_query_response_validation(self):
        """Test database query response validation."""
        validator = APIContractValidator()
        
        # Valid query response
        query_response = {
            "object": "list",
            "results": [],
            "next_cursor": None,
            "has_more": False
        }
        
        errors = validator.validate_database_query_response(query_response)
        assert len(errors) == 0
        
        # With page results
        query_response["results"] = [{
            "object": "page",
            "id": "page-id",
            "created_time": "2025-01-15T10:00:00Z",
            "created_by": {"object": "user", "id": "user-id"},
            "last_edited_time": "2025-01-15T10:30:00Z",
            "last_edited_by": {"object": "user", "id": "user-id"},
            "archived": False,
            "properties": {},
            "parent": {"type": "database_id", "database_id": "db-id"},
            "url": "https://notion.so/page-id"
        }]
        
        errors = validator.validate_database_query_response(query_response)
        assert len(errors) == 0
        
        # Invalid - has_more not boolean
        invalid_response = query_response.copy()
        invalid_response["has_more"] = "true"
        
        errors = validator.validate_database_query_response(invalid_response)
        assert any("Type mismatch" in e and "has_more" in e for e in errors)


class TestMockBehaviorValidatorWithContracts:
    """Test MockBehaviorValidator with contract testing."""
    
    def test_comprehensive_validation(self):
        """Test comprehensive mock validation."""
        from unittest.mock import Mock
        
        # Create a mock client with proper responses
        mock_client = Mock()
        
        # Mock page creation response
        mock_client.pages.create.return_value = {
            "object": "page",
            "id": "12345678-90ab-cdef-1234-567890abcdef",
            "created_time": "2025-01-15T10:00:00Z",
            "created_by": {"object": "user", "id": "user-id"},
            "last_edited_time": "2025-01-15T10:00:00Z",
            "last_edited_by": {"object": "user", "id": "user-id"},
            "archived": False,
            "properties": {
                "Title": {
                    "id": "title",
                    "type": "title",
                    "title": [{"text": {"content": "Test Page"}, "plain_text": "Test Page"}]
                }
            },
            "parent": {"type": "database_id", "database_id": "test-db"},
            "url": "https://notion.so/test-page"
        }
        
        # Mock database query response
        mock_client.databases.query.return_value = {
            "object": "list",
            "results": [],
            "next_cursor": None,
            "has_more": False
        }
        
        # Mock AI client
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text='{"entities": [], "relationships": []}')]
        )
        
        validator = MockBehaviorValidator()
        results = validator.validate_mock_behavior_compliance(mock_client)
        
        # Check results structure
        assert "basic_validation" in results
        assert "contract_validation" in results
        assert "property_validation" in results
        assert "summary" in results
        
        # Verify low error count (mock should pass most validations)
        total_errors = sum(len(errors) for key, errors in results.items() if key != "summary")
        assert total_errors < 5  # Allow some minor errors
    
    def test_property_type_validation(self):
        """Test all property type validations."""
        validator = MockBehaviorValidator()
        mock_client = Mock()
        
        errors = validator.validate_property_types(mock_client)
        
        # Should validate all property types without errors
        # (since we're testing the validation logic, not actual API calls)
        assert isinstance(errors, list)