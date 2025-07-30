"""Validators to ensure mock responses match real API behavior."""

from typing import Dict, Any, List
import json
from datetime import datetime


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
    """Validates overall mock behavior consistency."""
    
    def __init__(self):
        self.notion_validator = NotionAPIValidator()
        self.ai_validator = AIResponseValidator()
    
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