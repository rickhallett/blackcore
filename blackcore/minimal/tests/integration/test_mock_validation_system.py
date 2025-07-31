"""Integration tests for the complete mock validation system."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from blackcore.minimal.tests.utils.mock_validators import MockBehaviorValidator
from blackcore.minimal.tests.utils.api_contracts import PropertyType
from blackcore.minimal.tests.utils.schema_loader import SchemaDefinition, SchemaType


class TestMockValidationSystem:
    """Test the complete mock validation system."""
    
    @pytest.fixture
    def create_compliant_mock(self):
        """Create a mock client that passes all validations."""
        mock_client = Mock()
        
        # Setup page creation
        def create_page(**kwargs):
            timestamp = datetime.utcnow().isoformat() + "Z"
            return {
                "object": "page",
                "id": "12345678-90ab-cdef-1234-567890abcdef",
                "created_time": timestamp,
                "created_by": {"object": "user", "id": "user-123"},
                "last_edited_time": timestamp,
                "last_edited_by": {"object": "user", "id": "user-123"},
                "archived": False,
                "properties": kwargs.get("properties", {}),
                "parent": kwargs.get("parent", {}),
                "url": "https://notion.so/test-page"
            }
        
        mock_client.pages.create = Mock(side_effect=create_page)
        
        # Setup database query
        def query_database(**kwargs):
            return {
                "object": "list",
                "results": [],
                "next_cursor": None,
                "has_more": False
            }
        
        mock_client.databases.query = Mock(side_effect=query_database)
        
        # Setup AI client
        mock_ai_response = Mock()
        mock_ai_response.content = [Mock(text='{"entities": [], "relationships": []}')]
        mock_client.messages.create = Mock(return_value=mock_ai_response)
        
        return mock_client
    
    @pytest.fixture
    def create_non_compliant_mock(self):
        """Create a mock client with validation errors."""
        mock_client = Mock()
        
        # Page creation with missing fields
        def create_bad_page(**kwargs):
            return {
                "object": "page",
                "id": "not-a-valid-uuid",  # Invalid UUID
                # Missing created_time
                "properties": kwargs.get("properties", {})
            }
        
        mock_client.pages.create = Mock(side_effect=create_bad_page)
        
        # Database query with wrong types
        def query_bad_database(**kwargs):
            return {
                "object": "list",
                "results": "not-a-list",  # Should be list
                "has_more": "true"  # Should be boolean
            }
        
        mock_client.databases.query = Mock(side_effect=query_bad_database)
        
        return mock_client
    
    def test_compliant_mock_passes_all_validations(self, create_compliant_mock):
        """Test that a compliant mock passes all validations."""
        mock_client = create_compliant_mock
        validator = MockBehaviorValidator()
        
        results = validator.validate_mock_behavior_compliance(mock_client)
        
        # Check each validation category
        assert len(results["basic_validation"]) == 0
        assert len(results["contract_validation"]) == 0
        assert len(results["property_validation"]) == 0
        assert len(results["schema_validation"]) == 0
        assert len(results["ai_validation"]) == 0
        
        # Check summary
        assert "Total validation errors: 0" in results["summary"][0]
        assert all("Passed" in s and "True" in s for s in results["summary"][1:] if "ai_validation" not in s)
    
    def test_non_compliant_mock_fails_validations(self, create_non_compliant_mock):
        """Test that a non-compliant mock fails validations."""
        mock_client = create_non_compliant_mock
        validator = MockBehaviorValidator()
        
        results = validator.validate_mock_behavior_compliance(mock_client)
        
        # Should have errors in multiple categories
        assert len(results["basic_validation"]) > 0
        assert any("format invalid" in e for e in results["basic_validation"])
        
        # Check that errors are properly reported
        total_errors = sum(len(errors) for key, errors in results.items() if key != "summary")
        assert total_errors > 0
        assert f"Total validation errors: {total_errors}" in results["summary"][0]
    
    def test_property_validation_comprehensive(self, create_compliant_mock):
        """Test comprehensive property validation."""
        mock_client = create_compliant_mock
        
        # Override page creation to return all property types
        def create_page_with_all_props(**kwargs):
            timestamp = datetime.utcnow().isoformat() + "Z"
            return {
                "object": "page",
                "id": "12345678-90ab-cdef-1234-567890abcdef",
                "created_time": timestamp,
                "created_by": {"object": "user", "id": "user-123"},
                "last_edited_time": timestamp,
                "last_edited_by": {"object": "user", "id": "user-123"},
                "archived": False,
                "parent": {"type": "database_id", "database_id": "db-123"},
                "url": "https://notion.so/test-page",
                "properties": {
                    "Title": {
                        "id": "title",
                        "type": "title",
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": "Test Title"},
                                "plain_text": "Test Title",
                                "annotations": {
                                    "bold": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                    "code": False,
                                    "color": "default"
                                }
                            }
                        ]
                    },
                    "Description": {
                        "id": "desc",
                        "type": "rich_text",
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "Test description"},
                                "plain_text": "Test description"
                            }
                        ]
                    },
                    "Priority": {
                        "id": "priority",
                        "type": "number",
                        "number": 5
                    },
                    "Status": {
                        "id": "status",
                        "type": "select",
                        "select": {
                            "id": "status-1",
                            "name": "In Progress",
                            "color": "blue"
                        }
                    },
                    "Tags": {
                        "id": "tags",
                        "type": "multi_select",
                        "multi_select": [
                            {"id": "tag-1", "name": "Important", "color": "red"},
                            {"id": "tag-2", "name": "Urgent", "color": "orange"}
                        ]
                    },
                    "Due Date": {
                        "id": "due",
                        "type": "date",
                        "date": {
                            "start": "2025-01-20T00:00:00Z",
                            "end": None,
                            "time_zone": None
                        }
                    },
                    "Done": {
                        "id": "done",
                        "type": "checkbox",
                        "checkbox": True
                    },
                    "Email": {
                        "id": "email",
                        "type": "email",
                        "email": "test@example.com"
                    },
                    "Phone": {
                        "id": "phone",
                        "type": "phone_number",
                        "phone_number": "+1-555-0123"
                    },
                    "Website": {
                        "id": "url",
                        "type": "url",
                        "url": "https://example.com"
                    },
                    "Related": {
                        "id": "related",
                        "type": "relation",
                        "relation": [
                            {"id": "related-page-1"},
                            {"id": "related-page-2"}
                        ],
                        "has_more": False
                    },
                    "Assignee": {
                        "id": "people",
                        "type": "people",
                        "people": [
                            {
                                "object": "user",
                                "id": "user-456",
                                "name": "John Doe",
                                "avatar_url": None,
                                "type": "person",
                                "person": {"email": "john@example.com"}
                            }
                        ]
                    }
                }
            }
        
        mock_client.pages.create = Mock(side_effect=create_page_with_all_props)
        
        validator = MockBehaviorValidator()
        results = validator.validate_with_schema(mock_client)
        
        # Should pass all property validations
        assert len(results) == 0
    
    def test_schema_validation_edge_cases(self):
        """Test schema validation edge cases."""
        validator = MockBehaviorValidator()
        
        # Test with invalid timestamp format
        response = {
            "object": "page",
            "id": "12345678-90ab-cdef-1234-567890abcdef",
            "created_time": "2025-01-15",  # Missing time component
            "created_by": {"object": "user", "id": "user-123"},
            "last_edited_time": "invalid-timestamp",
            "last_edited_by": {"object": "user", "id": "user-123"},
            "archived": False,
            "properties": {},
            "parent": {"type": "database_id", "database_id": "db-123"},
            "url": "https://notion.so/test"
        }
        
        errors = validator.schema_validator.validate(response, "page")
        assert len(errors) > 0
        assert any("does not match format" in e for e in errors)
    
    def test_custom_schema_registration(self):
        """Test registering and validating custom schemas."""
        validator = MockBehaviorValidator()
        
        # Create a custom schema
        custom_schema = SchemaDefinition(
            name="custom_response",
            type=SchemaType.OBJECT,
            properties={
                "status": SchemaDefinition(
                    name="status",
                    type=SchemaType.ENUM,
                    enum_values=["success", "error", "pending"]
                ),
                "data": SchemaDefinition(
                    name="data",
                    type=SchemaType.OBJECT,
                    nullable=True
                ),
                "message": SchemaDefinition(
                    name="message",
                    type=SchemaType.STRING,
                    required=False
                )
            }
        )
        
        # Register the schema
        validator.schema_loader.register_schema(custom_schema)
        
        # Test valid response
        valid_response = {
            "status": "success",
            "data": {"result": "test"},
            "message": "Operation completed"
        }
        
        errors = validator.schema_validator.validate(valid_response, "custom_response")
        assert len(errors) == 0
        
        # Test invalid response
        invalid_response = {
            "status": "unknown",  # Not in enum
            "data": "not-an-object"  # Wrong type
        }
        
        errors = validator.schema_validator.validate(invalid_response, "custom_response")
        assert len(errors) > 0
    
    def test_api_endpoint_compliance(self):
        """Test API endpoint compliance validation."""
        validator = MockBehaviorValidator()
        
        # Test valid page response
        page_response = {
            "object": "page",
            "id": "12345678-90ab-cdef-1234-567890abcdef",
            "created_time": "2025-01-15T10:00:00Z",
            "created_by": {"object": "user", "id": "user-123"},
            "last_edited_time": "2025-01-15T10:00:00Z",
            "last_edited_by": {"object": "user", "id": "user-123"},
            "archived": False,
            "properties": {},
            "parent": {"type": "database_id", "database_id": "db-123"},
            "url": "https://notion.so/test"
        }
        
        errors = validator.validate_api_documentation_compliance(page_response, "/pages")
        assert len(errors) == 0
        
        # Test invalid endpoint
        errors = validator.validate_api_documentation_compliance({}, "/unknown/endpoint")
        assert any("No schema mapping" in e for e in errors)