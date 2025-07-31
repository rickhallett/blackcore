"""Tests for API compliance validation."""

import pytest
import json
from datetime import datetime, date

from blackcore.minimal.api_compliance_validator import (
    APIComplianceValidator,
    NotionAPIConstraints,
    NotionPropertyType,
    ValidationLevel,
    ValidationError,
    ValidationErrorType
)


class TestAPIComplianceValidator:
    """Test API compliance validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = APIComplianceValidator()
    
    def test_validate_page_properties_valid(self):
        """Test validation of valid page properties."""
        properties = {
            "Title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "Test Page"}
                    }
                ]
            },
            "Description": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "Test description"}
                    }
                ]
            },
            "Number": {
                "number": 42
            }
        }
        
        result = self.validator.validate_page_properties(properties)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_page_properties_invalid_structure(self):
        """Test validation with invalid property structure."""
        # Not a dictionary
        result = self.validator.validate_page_properties("invalid")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
        
        # Property value not a dictionary
        properties = {
            "Title": "invalid value"
        }
        result = self.validator.validate_page_properties(properties)
        assert not result.is_valid
        assert any(e.field_name == "Title" for e in result.errors)
    
    def test_validate_property_name(self):
        """Test property name validation."""
        # Valid name
        result = self.validator._validate_property_name("Valid Property Name")
        assert result.is_valid
        
        # Too long
        long_name = "a" * 51
        result = self.validator._validate_property_name(long_name)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Invalid characters (warning only)
        result = self.validator._validate_property_name("Name/With:Special*Chars")
        assert result.is_valid  # Still valid but has warnings
        assert len(result.warnings) > 0
        assert any(e.error_type == ValidationErrorType.FORMAT_ERROR for e in result.warnings)
    
    def test_validate_title_property(self):
        """Test title property validation."""
        # Valid title
        prop_value = {
            "title": [
                {
                    "type": "text",
                    "text": {"content": "Test Title"},
                    "annotations": {
                        "bold": False,
                        "italic": False
                    }
                }
            ]
        }
        result = self.validator._validate_title("Title", prop_value)
        assert result.is_valid
        
        # Title too long
        long_text = "a" * 2001
        prop_value = {
            "title": [
                {
                    "type": "text",
                    "text": {"content": long_text}
                }
            ]
        }
        result = self.validator._validate_title("Title", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Invalid structure - not an array
        prop_value = {"title": "not an array"}
        result = self.validator._validate_title("Title", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_rich_text_property(self):
        """Test rich text property validation."""
        # Valid rich text
        prop_value = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": "Some text"}
                }
            ]
        }
        result = self.validator._validate_rich_text("Description", prop_value)
        assert result.is_valid
        
        # Text too long
        long_text = "a" * 2001
        prop_value = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": long_text}
                }
            ]
        }
        result = self.validator._validate_rich_text("Description", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
    
    def test_validate_text_object(self):
        """Test text object validation."""
        # Valid text object
        text_obj = {
            "type": "text",
            "text": {"content": "Hello"},
            "annotations": {
                "bold": True,
                "italic": False,
                "color": "red"
            }
        }
        result = self.validator._validate_text_object(text_obj, "field")
        assert result.is_valid
        
        # Missing type
        text_obj = {"text": {"content": "Hello"}}
        result = self.validator._validate_text_object(text_obj, "field")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.REQUIRED_ERROR for e in result.errors)
        
        # Missing text field for text type
        text_obj = {"type": "text"}
        result = self.validator._validate_text_object(text_obj, "field")
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.REQUIRED_ERROR for e in result.errors)
        
        # Invalid annotation
        text_obj = {
            "type": "text",
            "text": {"content": "Hello"},
            "annotations": {
                "unknown_annotation": True
            }
        }
        result = self.validator._validate_text_object(text_obj, "field")
        assert result.is_valid  # Still valid but has warnings
        assert len(result.warnings) > 0
    
    def test_validate_number_property(self):
        """Test number property validation."""
        # Valid number
        prop_value = {"number": 42.5}
        result = self.validator._validate_number("Count", prop_value)
        assert result.is_valid
        
        # Number too large
        prop_value = {"number": 9007199254740992}  # Exceeds MAX_SAFE_INTEGER
        result = self.validator._validate_number("Count", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.RANGE_ERROR for e in result.errors)
        
        # Number too small
        prop_value = {"number": -9007199254740992}
        result = self.validator._validate_number("Count", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.RANGE_ERROR for e in result.errors)
        
        # Invalid type
        prop_value = {"number": "not a number"}
        result = self.validator._validate_number("Count", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_select_property(self):
        """Test select property validation."""
        # Valid select
        prop_value = {"select": {"name": "Option 1"}}
        result = self.validator._validate_select("Status", prop_value)
        assert result.is_valid
        
        # Select option too long
        long_name = "a" * 101
        prop_value = {"select": {"name": long_name}}
        result = self.validator._validate_select("Status", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Invalid structure
        prop_value = {"select": "not an object"}
        result = self.validator._validate_select("Status", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_multi_select_property(self):
        """Test multi-select property validation."""
        # Valid multi-select
        prop_value = {
            "multi_select": [
                {"name": "Tag1"},
                {"name": "Tag2"}
            ]
        }
        result = self.validator._validate_multi_select("Tags", prop_value)
        assert result.is_valid
        
        # Too many options
        options = [{"name": f"Tag{i}"} for i in range(101)]
        prop_value = {"multi_select": options}
        result = self.validator._validate_multi_select("Tags", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Invalid option structure
        prop_value = {
            "multi_select": [
                {"invalid": "structure"}
            ]
        }
        result = self.validator._validate_multi_select("Tags", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SCHEMA_ERROR for e in result.errors)
    
    def test_validate_date_property(self):
        """Test date property validation."""
        # Valid date with start only
        prop_value = {
            "date": {
                "start": "2024-01-15"
            }
        }
        result = self.validator._validate_date("Due Date", prop_value)
        assert result.is_valid
        
        # Valid date with start and end
        prop_value = {
            "date": {
                "start": "2024-01-15",
                "end": "2024-01-20",
                "time_zone": "America/New_York"
            }
        }
        result = self.validator._validate_date("Period", prop_value)
        assert result.is_valid
        
        # Missing start
        prop_value = {"date": {"end": "2024-01-20"}}
        result = self.validator._validate_date("Date", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.REQUIRED_ERROR for e in result.errors)
        
        # Invalid date format
        prop_value = {
            "date": {
                "start": "January 15, 2024"
            }
        }
        result = self.validator._validate_date("Date", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.FORMAT_ERROR for e in result.errors)
        
        # Valid datetime with timezone
        prop_value = {
            "date": {
                "start": "2024-01-15T10:30:00+00:00"
            }
        }
        result = self.validator._validate_date("Date", prop_value)
        assert result.is_valid
    
    def test_validate_people_property(self):
        """Test people property validation."""
        # Valid people
        prop_value = {
            "people": [
                {"object": "user", "id": "user-id-123"}
            ]
        }
        result = self.validator._validate_people("Assignee", prop_value)
        assert result.is_valid
        
        # Missing object type
        prop_value = {
            "people": [
                {"id": "user-id-123"}
            ]
        }
        result = self.validator._validate_people("Assignee", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SCHEMA_ERROR for e in result.errors)
        
        # Missing ID
        prop_value = {
            "people": [
                {"object": "user"}
            ]
        }
        result = self.validator._validate_people("Assignee", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.REQUIRED_ERROR for e in result.errors)
    
    def test_validate_files_property(self):
        """Test files property validation."""
        # Valid external file
        prop_value = {
            "files": [
                {
                    "type": "external",
                    "external": {"url": "https://example.com/file.pdf"}
                }
            ]
        }
        result = self.validator._validate_files("Attachments", prop_value)
        assert result.is_valid
        
        # Too many files
        files = []
        for i in range(11):
            files.append({
                "type": "external",
                "external": {"url": f"https://example.com/file{i}.pdf"}
            })
        prop_value = {"files": files}
        result = self.validator._validate_files("Attachments", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # URL too long
        long_url = "https://example.com/" + "a" * 2030
        prop_value = {
            "files": [
                {
                    "type": "external",
                    "external": {"url": long_url}
                }
            ]
        }
        result = self.validator._validate_files("Attachments", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
    
    def test_validate_checkbox_property(self):
        """Test checkbox property validation."""
        # Valid checkbox
        prop_value = {"checkbox": True}
        result = self.validator._validate_checkbox("Is Complete", prop_value)
        assert result.is_valid
        
        prop_value = {"checkbox": False}
        result = self.validator._validate_checkbox("Is Complete", prop_value)
        assert result.is_valid
        
        # Invalid type
        prop_value = {"checkbox": "yes"}
        result = self.validator._validate_checkbox("Is Complete", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_url_property(self):
        """Test URL property validation."""
        # Valid URL
        prop_value = {"url": "https://example.com"}
        result = self.validator._validate_url("Website", prop_value)
        assert result.is_valid
        
        # URL too long
        long_url = "https://example.com/" + "a" * 2030
        prop_value = {"url": long_url}
        result = self.validator._validate_url("Website", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Invalid type
        prop_value = {"url": 12345}
        result = self.validator._validate_url("Website", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_email_property(self):
        """Test email property validation."""
        # Valid email
        prop_value = {"email": "test@example.com"}
        result = self.validator._validate_email("Email", prop_value)
        assert result.is_valid
        
        # Invalid email (no @)
        prop_value = {"email": "notanemail"}
        result = self.validator._validate_email("Email", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.FORMAT_ERROR for e in result.errors)
        
        # Invalid type
        prop_value = {"email": 12345}
        result = self.validator._validate_email("Email", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_phone_number_property(self):
        """Test phone number property validation."""
        # Valid phone number
        prop_value = {"phone_number": "+1-555-123-4567"}
        result = self.validator._validate_phone_number("Phone", prop_value)
        assert result.is_valid
        
        # Invalid type
        prop_value = {"phone_number": 5551234567}
        result = self.validator._validate_phone_number("Phone", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_relation_property(self):
        """Test relation property validation."""
        # Valid relation
        prop_value = {
            "relation": [
                {"id": "page-id-123"},
                {"id": "page-id-456"}
            ]
        }
        result = self.validator._validate_relation("Related Pages", prop_value)
        assert result.is_valid
        
        # Too many relations
        relations = [{"id": f"page-id-{i}"} for i in range(101)]
        prop_value = {"relation": relations}
        result = self.validator._validate_relation("Related Pages", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        
        # Missing ID
        prop_value = {
            "relation": [
                {"invalid": "structure"}
            ]
        }
        result = self.validator._validate_relation("Related Pages", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SCHEMA_ERROR for e in result.errors)
    
    def test_validate_status_property(self):
        """Test status property validation."""
        # Valid status
        prop_value = {"status": {"name": "In Progress"}}
        result = self.validator._validate_status("Project Status", prop_value)
        assert result.is_valid
        
        # Invalid structure
        prop_value = {"status": "In Progress"}
        result = self.validator._validate_status("Project Status", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.TYPE_ERROR for e in result.errors)
    
    def test_validate_parent(self):
        """Test parent structure validation."""
        # Valid database parent
        parent = {"database_id": "12345678-90ab-cdef-1234-567890abcdef"}
        result = self.validator._validate_parent(parent)
        assert result.is_valid
        
        # Valid page parent
        parent = {"page_id": "abcdef12-3456-7890-abcd-ef1234567890"}
        result = self.validator._validate_parent(parent)
        assert result.is_valid
        
        # Valid workspace parent
        parent = {"workspace": True}
        result = self.validator._validate_parent(parent)
        assert result.is_valid
        
        # Missing parent type
        parent = {"unknown": "value"}
        result = self.validator._validate_parent(parent)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SCHEMA_ERROR for e in result.errors)
        
        # Invalid UUID format (warning only)
        parent = {"database_id": "not-a-uuid"}
        result = self.validator._validate_parent(parent)
        assert result.is_valid  # Still valid but has warnings
        assert len(result.warnings) > 0
    
    def test_validate_children(self):
        """Test children (blocks) validation."""
        # Valid children
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello"}}]}
            }
        ]
        result = self.validator._validate_children(children)
        assert result.is_valid
        
        # Invalid object type
        children = [
            {
                "object": "page",
                "type": "paragraph"
            }
        ]
        result = self.validator._validate_children(children)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.SCHEMA_ERROR for e in result.errors)
        
        # Missing type
        children = [
            {
                "object": "block"
            }
        ]
        result = self.validator._validate_children(children)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.REQUIRED_ERROR for e in result.errors)
    
    def test_validate_api_payload(self):
        """Test complete API payload validation."""
        # Valid payload
        payload = {
            "parent": {"database_id": "12345678-90ab-cdef-1234-567890abcdef"},
            "properties": {
                "Title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": "Test Page"}
                        }
                    ]
                }
            }
        }
        
        result = self.validator.validate_api_payload(payload)
        assert result.is_valid
        
        # Payload too large
        # Create a large payload
        large_text = "a" * 1000000
        payload = {
            "properties": {
                "Content": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": large_text}
                        }
                    ]
                }
            }
        }
        
        result = self.validator.validate_api_payload(payload)
        # Should have size error
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        # Check for either payload size or text length error
        assert any("Payload size" in e.message or "Rich text exceeds" in e.message for e in result.errors)
    
    def test_infer_property_type(self):
        """Test property type inference."""
        # Title
        prop = {"title": []}
        assert self.validator._infer_property_type(prop) == NotionPropertyType.TITLE
        
        # Rich text
        prop = {"rich_text": []}
        assert self.validator._infer_property_type(prop) == NotionPropertyType.RICH_TEXT
        
        # Number
        prop = {"number": 42}
        assert self.validator._infer_property_type(prop) == NotionPropertyType.NUMBER
        
        # Unknown
        prop = {"unknown": "value"}
        assert self.validator._infer_property_type(prop) is None
    
    def test_validation_levels(self):
        """Test different validation levels."""
        # Strict validator
        strict_validator = APIComplianceValidator(
            validation_level=ValidationLevel.STRICT
        )
        
        # Security validator
        security_validator = APIComplianceValidator(
            validation_level=ValidationLevel.SECURITY
        )
        
        # Both should work the same for API compliance
        properties = {
            "Title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "Test"}
                    }
                ]
            }
        }
        
        result1 = strict_validator.validate_page_properties(properties)
        result2 = security_validator.validate_page_properties(properties)
        
        assert result1.is_valid
        assert result2.is_valid
    
    def test_custom_constraints(self):
        """Test with custom API constraints."""
        # Custom constraints with lower limits
        constraints = NotionAPIConstraints(
            max_text_length=100,
            max_title_length=50,
            max_multi_select_options=5
        )
        
        validator = APIComplianceValidator(constraints=constraints)
        
        # Text exceeding custom limit
        prop_value = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": "a" * 101}
                }
            ]
        }
        
        result = validator._validate_rich_text("Description", prop_value)
        assert not result.is_valid
        assert any(e.error_type == ValidationErrorType.LENGTH_ERROR for e in result.errors)
        assert any("100" in e.message for e in result.errors)  # Should mention custom limit