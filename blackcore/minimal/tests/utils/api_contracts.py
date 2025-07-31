"""API contract definitions and validators for Notion API compliance."""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime


class PropertyType(Enum):
    """Notion property types."""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    CHECKBOX = "checkbox"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    URL = "url"
    RELATION = "relation"
    PEOPLE = "people"
    FILES = "files"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"
    FORMULA = "formula"
    ROLLUP = "rollup"


@dataclass
class FieldContract:
    """Contract for a single field in API response."""
    name: str
    type: type
    required: bool = True
    nullable: bool = False
    validator: Optional[callable] = None
    children: Optional[Dict[str, 'FieldContract']] = None


@dataclass
class APIContract:
    """Complete API contract for an endpoint."""
    endpoint: str
    method: str
    request_schema: Dict[str, FieldContract]
    response_schema: Dict[str, FieldContract]
    status_codes: List[int]
    rate_limit: Optional[int] = None


class ContractValidators:
    """Validators for specific field types."""
    
    @staticmethod
    def validate_uuid(value: str) -> bool:
        """Validate UUID format (with or without dashes)."""
        # Remove dashes and validate hex string of 32 chars
        clean_value = value.replace("-", "")
        return len(clean_value) == 32 and all(c in "0123456789abcdef" for c in clean_value.lower())
    
    @staticmethod
    def validate_iso_timestamp(value: str) -> bool:
        """Validate ISO 8601 timestamp."""
        try:
            # Handle timezone Z notation
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            datetime.fromisoformat(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def validate_email(value: str) -> bool:
        """Validate email format."""
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        return bool(email_pattern.match(value))
    
    @staticmethod
    def validate_url(value: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(r"^https?://[^\s]+$")
        return bool(url_pattern.match(value))
    
    @staticmethod
    def validate_color(value: str) -> bool:
        """Validate Notion color values."""
        valid_colors = [
            "default", "gray", "brown", "orange", "yellow", 
            "green", "blue", "purple", "pink", "red"
        ]
        return value in valid_colors


class NotionAPIContracts:
    """Collection of Notion API contracts."""
    
    # Common field contracts
    UUID_CONTRACT = FieldContract(
        name="id",
        type=str,
        validator=ContractValidators.validate_uuid
    )
    
    TIMESTAMP_CONTRACT = FieldContract(
        name="timestamp",
        type=str,
        validator=ContractValidators.validate_iso_timestamp
    )
    
    # Rich text item schema
    RICH_TEXT_ITEM_SCHEMA = {
        "type": FieldContract("type", str),
        "text": FieldContract(
            "text", 
            dict,
            children={
                "content": FieldContract("content", str),
                "link": FieldContract("link", dict, nullable=True)
            }
        ),
        "annotations": FieldContract(
            "annotations",
            dict,
            required=False,
            children={
                "bold": FieldContract("bold", bool, required=False),
                "italic": FieldContract("italic", bool, required=False),
                "strikethrough": FieldContract("strikethrough", bool, required=False),
                "underline": FieldContract("underline", bool, required=False),
                "code": FieldContract("code", bool, required=False),
                "color": FieldContract("color", str, required=False, validator=ContractValidators.validate_color)
            }
        ),
        "plain_text": FieldContract("plain_text", str, required=False),
        "href": FieldContract("href", str, required=False, nullable=True)
    }
    
    # Property value schemas by type
    @classmethod
    def get_property_schema(cls, prop_type: PropertyType) -> Dict[str, FieldContract]:
        """Get schema for a specific property type."""
        schemas = {
            PropertyType.TITLE: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "title": FieldContract("title", list)
            },
            PropertyType.RICH_TEXT: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "rich_text": FieldContract("rich_text", list)
            },
            PropertyType.NUMBER: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "number": FieldContract("number", (int, float, type(None)), nullable=True)
            },
            PropertyType.SELECT: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "select": FieldContract(
                    "select",
                    dict,
                    nullable=True,
                    children={
                        "id": FieldContract("id", str, required=False),
                        "name": FieldContract("name", str),
                        "color": FieldContract("color", str, validator=ContractValidators.validate_color)
                    }
                )
            },
            PropertyType.MULTI_SELECT: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "multi_select": FieldContract("multi_select", list)
            },
            PropertyType.DATE: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "date": FieldContract(
                    "date",
                    dict,
                    nullable=True,
                    children={
                        "start": FieldContract("start", str, validator=ContractValidators.validate_iso_timestamp),
                        "end": FieldContract("end", str, nullable=True, validator=ContractValidators.validate_iso_timestamp),
                        "time_zone": FieldContract("time_zone", str, nullable=True, required=False)
                    }
                )
            },
            PropertyType.CHECKBOX: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "checkbox": FieldContract("checkbox", bool)
            },
            PropertyType.EMAIL: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "email": FieldContract("email", str, nullable=True, validator=ContractValidators.validate_email)
            },
            PropertyType.PHONE_NUMBER: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "phone_number": FieldContract("phone_number", str, nullable=True)
            },
            PropertyType.URL: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "url": FieldContract("url", str, nullable=True, validator=ContractValidators.validate_url)
            },
            PropertyType.RELATION: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "relation": FieldContract("relation", list),
                "has_more": FieldContract("has_more", bool, required=False)
            },
            PropertyType.PEOPLE: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "people": FieldContract("people", list)
            },
            PropertyType.FILES: {
                "id": FieldContract("id", str, required=False),
                "type": FieldContract("type", str),
                "files": FieldContract("files", list)
            }
        }
        
        return schemas.get(prop_type, {})
    
    # Page response contract
    PAGE_RESPONSE_CONTRACT = APIContract(
        endpoint="/pages",
        method="GET",
        request_schema={},
        response_schema={
            "object": FieldContract("object", str),
            "id": UUID_CONTRACT,
            "created_time": FieldContract("created_time", str, validator=ContractValidators.validate_iso_timestamp),
            "created_by": FieldContract("created_by", dict),
            "last_edited_time": FieldContract("last_edited_time", str, validator=ContractValidators.validate_iso_timestamp),
            "last_edited_by": FieldContract("last_edited_by", dict),
            "archived": FieldContract("archived", bool),
            "icon": FieldContract("icon", dict, nullable=True, required=False),
            "cover": FieldContract("cover", dict, nullable=True, required=False),
            "properties": FieldContract("properties", dict),
            "parent": FieldContract(
                "parent",
                dict,
                children={
                    "type": FieldContract("type", str),
                    "database_id": FieldContract("database_id", str, required=False),
                    "page_id": FieldContract("page_id", str, required=False),
                    "workspace": FieldContract("workspace", bool, required=False)
                }
            ),
            "url": FieldContract("url", str)
        },
        status_codes=[200]
    )
    
    # Database query response contract
    DATABASE_QUERY_CONTRACT = APIContract(
        endpoint="/databases/{id}/query",
        method="POST",
        request_schema={
            "filter": FieldContract("filter", dict, required=False),
            "sorts": FieldContract("sorts", list, required=False),
            "start_cursor": FieldContract("start_cursor", str, required=False),
            "page_size": FieldContract("page_size", int, required=False)
        },
        response_schema={
            "object": FieldContract("object", str),
            "results": FieldContract("results", list),
            "next_cursor": FieldContract("next_cursor", str, nullable=True),
            "has_more": FieldContract("has_more", bool),
            "type": FieldContract("type", str, required=False),
            "page": FieldContract("page", dict, required=False)
        },
        status_codes=[200]
    )
    
    # Error response contract
    ERROR_RESPONSE_CONTRACT = {
        "object": FieldContract("object", str),
        "status": FieldContract("status", int),
        "code": FieldContract("code", str),
        "message": FieldContract("message", str)
    }


class APIContractValidator:
    """Validates API responses against contracts."""
    
    def __init__(self):
        self.contracts = NotionAPIContracts()
    
    def validate_field(self, value: Any, contract: FieldContract, path: str = "") -> List[str]:
        """Validate a single field against its contract."""
        errors = []
        field_path = f"{path}.{contract.name}" if path else contract.name
        
        # Check if field is missing
        if value is None:
            if contract.required and not contract.nullable:
                errors.append(f"Required field missing: {field_path}")
                return errors
            elif contract.nullable:
                return errors
        
        # Check type
        if not isinstance(value, contract.type):
            errors.append(
                f"Type mismatch at {field_path}: expected {contract.type.__name__}, "
                f"got {type(value).__name__}"
            )
            return errors
        
        # Run custom validator if provided
        if contract.validator and value is not None:
            try:
                if not contract.validator(value):
                    errors.append(f"Validation failed for {field_path}: {value}")
            except Exception as e:
                errors.append(f"Validator error for {field_path}: {str(e)}")
        
        # Validate children if present
        if contract.children and isinstance(value, dict):
            for child_name, child_contract in contract.children.items():
                child_value = value.get(child_name)
                errors.extend(self.validate_field(child_value, child_contract, field_path))
        
        return errors
    
    def validate_response(self, response: Dict[str, Any], contract: APIContract) -> List[str]:
        """Validate an API response against a contract."""
        errors = []
        
        # Validate each field in the response schema
        for field_name, field_contract in contract.response_schema.items():
            value = response.get(field_name)
            errors.extend(self.validate_field(value, field_contract))
        
        # Check for unexpected fields
        expected_fields = set(contract.response_schema.keys())
        actual_fields = set(response.keys())
        unexpected = actual_fields - expected_fields
        
        if unexpected:
            # This is often just a warning in real APIs
            for field in unexpected:
                errors.append(f"Unexpected field in response: {field}")
        
        return errors
    
    def validate_property_value(self, prop_value: Dict[str, Any], prop_type: str) -> List[str]:
        """Validate a property value against its type contract."""
        errors = []
        
        try:
            property_enum = PropertyType(prop_type)
        except ValueError:
            errors.append(f"Unknown property type: {prop_type}")
            return errors
        
        schema = self.contracts.get_property_schema(property_enum)
        if not schema:
            errors.append(f"No schema defined for property type: {prop_type}")
            return errors
        
        # Validate against schema
        for field_name, field_contract in schema.items():
            value = prop_value.get(field_name)
            errors.extend(self.validate_field(value, field_contract, f"property[{prop_type}]"))
        
        return errors
    
    def validate_page_response(self, response: Dict[str, Any]) -> List[str]:
        """Validate a page response."""
        return self.validate_response(response, self.contracts.PAGE_RESPONSE_CONTRACT)
    
    def validate_database_query_response(self, response: Dict[str, Any]) -> List[str]:
        """Validate a database query response."""
        errors = self.validate_response(response, self.contracts.DATABASE_QUERY_CONTRACT)
        
        # Additional validation for results
        if "results" in response and isinstance(response["results"], list):
            for i, result in enumerate(response["results"]):
                if isinstance(result, dict):
                    # Each result should be a valid page
                    page_errors = self.validate_page_response(result)
                    for error in page_errors:
                        errors.append(f"In result[{i}]: {error}")
        
        return errors
    
    def validate_error_response(self, response: Dict[str, Any]) -> List[str]:
        """Validate an error response."""
        errors = []
        
        for field_name, field_contract in self.contracts.ERROR_RESPONSE_CONTRACT.items():
            value = response.get(field_name)
            errors.extend(self.validate_field(value, field_contract, "error"))
        
        return errors