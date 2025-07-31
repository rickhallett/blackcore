"""Validators to ensure mock responses match real API behavior."""

from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime
from blackcore.minimal.tests.utils.api_contracts import (
    APIContractValidator,
    PropertyType,
    NotionAPIContracts
)
from blackcore.minimal.tests.utils.schema_loader import (
    NotionAPISchemaLoader,
    SchemaValidator
)


class NotionAPIValidator:
    """Validates that mock responses match Notion API format."""
    
    @staticmethod
    def validate_page_response(response: Dict[str, Any]) -> bool:
        """Validate a page response matches Notion API format."""
        required_fields = ["id", "object", "created_time", "last_edited_time"]
        
        for field in required_fields:
            if field not in response:
                return False
        
        # Validate object type
        if response["object"] != "page":
            return False
        
        # Validate ID format (should be UUID-like)
        if not isinstance(response["id"], str) or len(response["id"]) < 8:
            return False
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(response["created_time"].replace('Z', '+00:00'))
            datetime.fromisoformat(response["last_edited_time"].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return False
        
        return True
    
    @staticmethod
    def validate_database_query_response(response: Dict[str, Any]) -> bool:
        """Validate a database query response matches Notion API format."""
        required_fields = ["results", "has_more"]
        
        for field in required_fields:
            if field not in response:
                return False
        
        # Validate results is a list
        if not isinstance(response["results"], list):
            return False
        
        # Validate has_more is boolean
        if not isinstance(response["has_more"], bool):
            return False
        
        return True
    
    @staticmethod
    def validate_property_format(prop_value: Dict[str, Any], prop_type: str) -> bool:
        """Validate property format matches Notion API."""
        if "type" not in prop_value:
            return False
        
        expected_formats = {
            "title": {"type": "title", "title": list},
            "rich_text": {"type": "rich_text", "rich_text": list},
            "number": {"type": "number", "number": (int, float, type(None))},
            "select": {"type": "select", "select": (dict, type(None))},
            "multi_select": {"type": "multi_select", "multi_select": list},
            "date": {"type": "date", "date": (dict, type(None))},
            "checkbox": {"type": "checkbox", "checkbox": bool},
            "email": {"type": "email", "email": (str, type(None))},
            "phone_number": {"type": "phone_number", "phone_number": (str, type(None))},
            "url": {"type": "url", "url": (str, type(None))},
            "relation": {"type": "relation", "relation": list},
            "people": {"type": "people", "people": list},
        }
        
        if prop_type not in expected_formats:
            return False
        
        expected = expected_formats[prop_type]
        
        # Check type field
        if prop_value.get("type") != expected["type"]:
            return False
        
        # Check main property field exists and has correct type
        main_field = expected["type"]
        if main_field not in prop_value:
            return False
        
        expected_type = expected[main_field]
        actual_value = prop_value[main_field]
        
        if isinstance(expected_type, tuple):
            if not isinstance(actual_value, expected_type):
                return False
        else:
            if not isinstance(actual_value, expected_type):
                return False
        
        return True


class AIResponseValidator:
    """Validates that mock AI responses match expected format."""
    
    @staticmethod
    def validate_entity_extraction_response(response_text: str) -> bool:
        """Validate AI entity extraction response format."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return False
        
        # Must have entities and relationships keys
        if "entities" not in data or "relationships" not in data:
            return False
        
        # Both must be lists
        if not isinstance(data["entities"], list) or not isinstance(data["relationships"], list):
            return False
        
        # Validate entity structure
        for entity in data["entities"]:
            if not isinstance(entity, dict):
                return False
            
            required_fields = ["name", "type"]
            for field in required_fields:
                if field not in entity:
                    return False
            
            # Type must be a valid entity type
            valid_types = ["person", "organization", "task", "event", "place", "transgression"]
            if entity["type"] not in valid_types:
                return False
        
        # Validate relationship structure
        for relationship in data["relationships"]:
            if not isinstance(relationship, dict):
                return False
            
            required_fields = ["source_entity", "source_type", "target_entity", 
                              "target_type", "relationship_type"]
            for field in required_fields:
                if field not in relationship:
                    return False
        
        return True


class MockBehaviorValidator:
    """Validates overall mock behavior consistency with API contract testing."""
    
    def __init__(self):
        self.notion_validator = NotionAPIValidator()
        self.ai_validator = AIResponseValidator()
        self.contract_validator = APIContractValidator()
        self.schema_loader = NotionAPISchemaLoader()
        self.schema_validator = SchemaValidator(self.schema_loader)
    
    def validate_mock_notion_client(self, mock_client) -> List[str]:
        """Validate mock Notion client behavior."""
        errors = []
        
        # Test page creation
        try:
            response = mock_client.pages.create(
                parent={"database_id": "test-db"},
                properties={"Name": {"rich_text": [{"text": {"content": "Test"}}]}}
            )
            if not self.notion_validator.validate_page_response(response):
                errors.append("Page creation response format invalid")
        except Exception as e:
            errors.append(f"Page creation failed: {e}")
        
        # Test database query
        try:
            response = mock_client.databases.query(database_id="test-db")
            if not self.notion_validator.validate_database_query_response(response):
                errors.append("Database query response format invalid")
        except Exception as e:
            errors.append(f"Database query failed: {e}")
        
        return errors
    
    def validate_mock_ai_client(self, mock_client) -> List[str]:
        """Validate mock AI client behavior."""
        errors = []
        
        try:
            response = mock_client.messages.create(
                messages=[{"role": "user", "content": "Extract entities from: John works at Acme Corp"}]
            )
            response_text = response.content[0].text
            if not self.ai_validator.validate_entity_extraction_response(response_text):
                errors.append("AI response format invalid")
        except Exception as e:
            errors.append(f"AI client failed: {e}")
        
        return errors
    
    def validate_with_contract(self, mock_client) -> List[str]:
        """Validate mock responses against API contracts."""
        errors = []
        
        # Test page creation with contract validation
        try:
            response = mock_client.pages.create(
                parent={"database_id": "test-db"},
                properties={
                    "Title": {"title": [{"text": {"content": "Test Page"}}]},
                    "Description": {"rich_text": [{"text": {"content": "Test description"}}]},
                    "Status": {"select": {"name": "Active"}},
                    "Priority": {"number": 5},
                    "Done": {"checkbox": True}
                }
            )
            
            # Validate response against contract
            contract_errors = self.contract_validator.validate_page_response(response)
            if contract_errors:
                errors.extend([f"Contract violation: {e}" for e in contract_errors])
                
            # Validate individual properties
            if "properties" in response:
                for prop_name, prop_value in response["properties"].items():
                    if isinstance(prop_value, dict) and "type" in prop_value:
                        prop_errors = self.contract_validator.validate_property_value(
                            prop_value, prop_value["type"]
                        )
                        if prop_errors:
                            errors.extend([f"Property {prop_name}: {e}" for e in prop_errors])
            
        except Exception as e:
            errors.append(f"Contract validation failed: {e}")
        
        # Test database query with contract validation
        try:
            response = mock_client.databases.query(
                database_id="test-db",
                filter={"property": "Status", "select": {"equals": "Active"}},
                sorts=[{"property": "Created", "direction": "descending"}],
                page_size=10
            )
            
            contract_errors = self.contract_validator.validate_database_query_response(response)
            if contract_errors:
                errors.extend([f"Query contract violation: {e}" for e in contract_errors])
                
        except Exception as e:
            errors.append(f"Query contract validation failed: {e}")
        
        # Test error response validation
        try:
            # Simulate an error response
            error_response = {
                "object": "error",
                "status": 400,
                "code": "invalid_request",
                "message": "Invalid database ID"
            }
            
            error_contract_errors = self.contract_validator.validate_error_response(error_response)
            if error_contract_errors:
                errors.extend([f"Error response contract violation: {e}" for e in error_contract_errors])
                
        except Exception as e:
            errors.append(f"Error response validation failed: {e}")
        
        return errors
    
    def validate_property_types(self, mock_client) -> List[str]:
        """Validate all property types against contracts."""
        errors = []
        
        property_test_cases = {
            "title": {"title": [{"text": {"content": "Test Title"}, "plain_text": "Test Title"}]},
            "rich_text": {"rich_text": [{"text": {"content": "Rich text"}, "plain_text": "Rich text"}]},
            "number": {"number": 42},
            "select": {"select": {"name": "Option1", "color": "blue"}},
            "multi_select": {"multi_select": [{"name": "Tag1", "color": "red"}, {"name": "Tag2", "color": "green"}]},
            "date": {"date": {"start": "2025-01-01", "end": None}},
            "checkbox": {"checkbox": True},
            "email": {"email": "test@example.com"},
            "phone_number": {"phone_number": "+1-555-0123"},
            "url": {"url": "https://example.com"},
            "relation": {"relation": [{"id": "related-page-id"}], "has_more": False},
            "people": {"people": [{"object": "user", "id": "user-id"}]},
            "files": {"files": [{"type": "external", "name": "file.pdf", "external": {"url": "https://example.com/file.pdf"}}]}
        }
        
        for prop_type, test_value in property_test_cases.items():
            # Add type field
            test_value["type"] = prop_type
            test_value["id"] = f"prop-{prop_type}"
            
            prop_errors = self.contract_validator.validate_property_value(test_value, prop_type)
            if prop_errors:
                errors.extend([f"Property type {prop_type}: {e}" for e in prop_errors])
        
        return errors
    
    def validate_response_consistency(self, response1: Dict[str, Any], response2: Dict[str, Any]) -> List[str]:
        """Validate that two responses have consistent structure."""
        errors = []
        
        # Check if both responses have the same top-level keys
        keys1 = set(response1.keys())
        keys2 = set(response2.keys())
        
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1
        
        if missing_in_2:
            errors.append(f"Keys missing in second response: {missing_in_2}")
        if missing_in_1:
            errors.append(f"Keys missing in first response: {missing_in_1}")
        
        # Check if object types match
        if response1.get("object") != response2.get("object"):
            errors.append(
                f"Object type mismatch: {response1.get('object')} vs {response2.get('object')}"
            )
        
        return errors
    
    def validate_mock_behavior_compliance(self, mock_client) -> Dict[str, List[str]]:
        """Comprehensive validation of mock client behavior."""
        results = {
            "basic_validation": self.validate_mock_notion_client(mock_client),
            "contract_validation": self.validate_with_contract(mock_client),
            "property_validation": self.validate_property_types(mock_client),
            "schema_validation": self.validate_with_schema(mock_client),
            "ai_validation": self.validate_mock_ai_client(mock_client) if hasattr(mock_client, 'messages') else []
        }
        
        # Summary
        total_errors = sum(len(errors) for errors in results.values())
        results["summary"] = [
            f"Total validation errors: {total_errors}",
            f"Passed basic validation: {len(results['basic_validation']) == 0}",
            f"Passed contract validation: {len(results['contract_validation']) == 0}",
            f"Passed property validation: {len(results['property_validation']) == 0}",
            f"Passed schema validation: {len(results['schema_validation']) == 0}"
        ]
        
        return results
    
    def validate_with_schema(self, mock_client) -> List[str]:
        """Validate mock responses against API documentation schemas."""
        errors = []
        
        # Test page response against schema
        try:
            response = mock_client.pages.create(
                parent={"database_id": "test-db"},
                properties={
                    "Title": {"title": [{"text": {"content": "Schema Test"}}]}
                }
            )
            
            # Validate against page schema
            schema_errors = self.schema_validator.validate(response, "page")
            if schema_errors:
                errors.extend([f"Page schema: {e}" for e in schema_errors])
                
        except Exception as e:
            errors.append(f"Page schema validation failed: {e}")
        
        # Test database query response against schema
        try:
            response = mock_client.databases.query(database_id="test-db")
            
            schema_errors = self.schema_validator.validate(response, "database_query_response")
            if schema_errors:
                errors.extend([f"Query schema: {e}" for e in schema_errors])
                
        except Exception as e:
            errors.append(f"Query schema validation failed: {e}")
        
        # Test property schemas
        try:
            # Create a page with various property types
            response = mock_client.pages.create(
                parent={"database_id": "test-db"},
                properties={
                    "Title": {
                        "id": "title",
                        "type": "title",
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": "Test"},
                                "plain_text": "Test"
                            }
                        ]
                    },
                    "Number": {
                        "id": "number",
                        "type": "number",
                        "number": 42
                    },
                    "Select": {
                        "id": "select",
                        "type": "select",
                        "select": {
                            "name": "Option1",
                            "color": "blue"
                        }
                    }
                }
            )
            
            # Validate each property against its schema
            if "properties" in response:
                for prop_name, prop_value in response["properties"].items():
                    if prop_value.get("type") == "title":
                        prop_errors = self.schema_validator.validate(prop_value, "property_title")
                        if prop_errors:
                            errors.extend([f"Title property: {e}" for e in prop_errors])
                    elif prop_value.get("type") == "number":
                        prop_errors = self.schema_validator.validate(prop_value, "property_number")
                        if prop_errors:
                            errors.extend([f"Number property: {e}" for e in prop_errors])
                    elif prop_value.get("type") == "select":
                        prop_errors = self.schema_validator.validate(prop_value, "property_select")
                        if prop_errors:
                            errors.extend([f"Select property: {e}" for e in prop_errors])
                            
        except Exception as e:
            errors.append(f"Property schema validation failed: {e}")
        
        return errors
    
    def validate_api_documentation_compliance(self, response: Dict[str, Any], 
                                            endpoint: str) -> List[str]:
        """Validate that a response complies with API documentation."""
        errors = []
        
        # Map endpoints to schema names
        schema_mapping = {
            "/pages": "page",
            "/databases/query": "database_query_response",
            "/databases": "database",
            "/search": "search_response"
        }
        
        schema_name = schema_mapping.get(endpoint)
        if not schema_name:
            errors.append(f"No schema mapping for endpoint: {endpoint}")
            return errors
        
        # Check if schema exists
        schema = self.schema_loader.get_schema(schema_name)
        if not schema:
            errors.append(f"Schema not found: {schema_name}")
            return errors
        
        # Validate against schema
        validation_errors = self.schema_validator.validate(response, schema_name)
        errors.extend(validation_errors)
        
        return errors