"""API compliance validation for Notion API formats.

This module provides validation to ensure that all data sent to the Notion API
complies with their format requirements and constraints.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime, date

from blackcore.minimal.property_validation import (
    ValidationResult,
    ValidationError,
    ValidationErrorType,
    ValidationLevel
)


class NotionPropertyType(Enum):
    """Notion property types."""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"
    STATUS = "status"


@dataclass
class NotionAPIConstraints:
    """Constraints for Notion API."""
    max_text_length: int = 2000
    max_number_value: float = 9007199254740991  # JavaScript MAX_SAFE_INTEGER
    min_number_value: float = -9007199254740991
    max_multi_select_options: int = 100
    max_relation_items: int = 100
    max_files: int = 10
    max_page_size: int = 100
    max_api_payload_size: int = 2 * 1024 * 1024  # 2MB
    max_title_length: int = 2000
    max_url_length: int = 2048
    max_select_option_length: int = 100
    max_property_name_length: int = 50


class APIComplianceValidator:
    """Validates data compliance with Notion API requirements."""
    
    def __init__(self, 
                 validation_level: ValidationLevel = ValidationLevel.STANDARD,
                 constraints: Optional[NotionAPIConstraints] = None):
        """Initialize API compliance validator.
        
        Args:
            validation_level: Validation strictness level
            constraints: API constraints (uses defaults if not provided)
        """
        self.validation_level = validation_level
        self.constraints = constraints or NotionAPIConstraints()
    
    def validate_page_properties(self, properties: Dict[str, Any]) -> ValidationResult:
        """Validate page properties for API compliance.
        
        Args:
            properties: Formatted properties ready for API
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Validate property structure
        if not isinstance(properties, dict):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name="properties",
                message="Properties must be a dictionary",
                value=properties
            ))
            return result
        
        # Validate each property
        for prop_name, prop_value in properties.items():
            # Validate property name
            name_result = self._validate_property_name(prop_name)
            result.merge(name_result)
            
            # Validate property value structure
            if not isinstance(prop_value, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message=f"Property value must be a dictionary, got {type(prop_value).__name__}",
                    value=prop_value
                ))
                continue
            
            # Determine property type and validate
            prop_type = self._infer_property_type(prop_value)
            if prop_type:
                type_result = self._validate_property_value(prop_name, prop_value, prop_type)
                result.merge(type_result)
            else:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.SCHEMA_ERROR,
                    field_name=prop_name,
                    message="Unable to determine property type",
                    value=prop_value
                ))
        
        return result
    
    def validate_api_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        """Validate complete API payload.
        
        Args:
            payload: Complete API payload
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Check payload size
        import json
        payload_size = len(json.dumps(payload))
        if payload_size > self.constraints.max_api_payload_size:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name="payload",
                message=f"Payload size ({payload_size} bytes) exceeds API limit of {self.constraints.max_api_payload_size} bytes",
                value=payload
            ))
        
        # Validate parent structure
        if "parent" in payload:
            parent_result = self._validate_parent(payload["parent"])
            result.merge(parent_result)
        
        # Validate properties
        if "properties" in payload:
            props_result = self.validate_page_properties(payload["properties"])
            result.merge(props_result)
        
        # Validate children (for page content)
        if "children" in payload:
            children_result = self._validate_children(payload["children"])
            result.merge(children_result)
        
        return result
    
    def _validate_property_name(self, name: str) -> ValidationResult:
        """Validate property name."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(name, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name="property_name",
                message="Property name must be a string",
                value=name
            ))
            return result
        
        if len(name) > self.constraints.max_property_name_length:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name="property_name",
                message=f"Property name exceeds maximum length of {self.constraints.max_property_name_length}",
                value=name
            ))
        
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', name):
            result.add_warning(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name="property_name",
                message="Property name contains potentially problematic characters",
                value=name
            ))
        
        return result
    
    def _infer_property_type(self, prop_value: Dict[str, Any]) -> Optional[NotionPropertyType]:
        """Infer property type from its structure."""
        # Check for explicit type indicators
        type_map = {
            "title": NotionPropertyType.TITLE,
            "rich_text": NotionPropertyType.RICH_TEXT,
            "number": NotionPropertyType.NUMBER,
            "select": NotionPropertyType.SELECT,
            "multi_select": NotionPropertyType.MULTI_SELECT,
            "date": NotionPropertyType.DATE,
            "people": NotionPropertyType.PEOPLE,
            "files": NotionPropertyType.FILES,
            "checkbox": NotionPropertyType.CHECKBOX,
            "url": NotionPropertyType.URL,
            "email": NotionPropertyType.EMAIL,
            "phone_number": NotionPropertyType.PHONE_NUMBER,
            "relation": NotionPropertyType.RELATION,
            "status": NotionPropertyType.STATUS
        }
        
        for key, prop_type in type_map.items():
            if key in prop_value:
                return prop_type
        
        return None
    
    def _validate_property_value(self, 
                               prop_name: str, 
                               prop_value: Dict[str, Any], 
                               prop_type: NotionPropertyType) -> ValidationResult:
        """Validate property value based on its type."""
        validators = {
            NotionPropertyType.TITLE: self._validate_title,
            NotionPropertyType.RICH_TEXT: self._validate_rich_text,
            NotionPropertyType.NUMBER: self._validate_number,
            NotionPropertyType.SELECT: self._validate_select,
            NotionPropertyType.MULTI_SELECT: self._validate_multi_select,
            NotionPropertyType.DATE: self._validate_date,
            NotionPropertyType.PEOPLE: self._validate_people,
            NotionPropertyType.FILES: self._validate_files,
            NotionPropertyType.CHECKBOX: self._validate_checkbox,
            NotionPropertyType.URL: self._validate_url,
            NotionPropertyType.EMAIL: self._validate_email,
            NotionPropertyType.PHONE_NUMBER: self._validate_phone_number,
            NotionPropertyType.RELATION: self._validate_relation,
            NotionPropertyType.STATUS: self._validate_status
        }
        
        validator = validators.get(prop_type)
        if validator:
            return validator(prop_name, prop_value)
        
        # No specific validator, return success
        return ValidationResult(is_valid=True)
    
    def _validate_title(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate title property."""
        result = ValidationResult(is_valid=True)
        
        title_array = prop_value.get("title", [])
        if not isinstance(title_array, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Title must be an array of text objects",
                value=prop_value
            ))
            return result
        
        # Validate text content
        total_length = 0
        for text_obj in title_array:
            text_result = self._validate_text_object(text_obj, prop_name)
            result.merge(text_result)
            
            # Track total length
            if isinstance(text_obj, dict) and "text" in text_obj:
                content = text_obj.get("text", {}).get("content", "")
                total_length += len(content)
        
        if total_length > self.constraints.max_title_length:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=prop_name,
                message=f"Title exceeds maximum length of {self.constraints.max_title_length}",
                value=prop_value,
                context={"total_length": total_length}
            ))
        
        return result
    
    def _validate_rich_text(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate rich text property."""
        result = ValidationResult(is_valid=True)
        
        text_array = prop_value.get("rich_text", [])
        if not isinstance(text_array, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Rich text must be an array of text objects",
                value=prop_value
            ))
            return result
        
        # Validate text content
        total_length = 0
        for text_obj in text_array:
            text_result = self._validate_text_object(text_obj, prop_name)
            result.merge(text_result)
            
            # Track total length
            if isinstance(text_obj, dict) and "text" in text_obj:
                content = text_obj.get("text", {}).get("content", "")
                total_length += len(content)
        
        if total_length > self.constraints.max_text_length:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=prop_name,
                message=f"Rich text exceeds maximum length of {self.constraints.max_text_length}",
                value=prop_value,
                context={"total_length": total_length}
            ))
        
        return result
    
    def _validate_text_object(self, text_obj: Dict[str, Any], field_name: str) -> ValidationResult:
        """Validate a single text object."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(text_obj, dict):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=field_name,
                message="Text object must be a dictionary",
                value=text_obj
            ))
            return result
        
        # Must have type field
        if "type" not in text_obj:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.REQUIRED_ERROR,
                field_name=field_name,
                message="Text object missing required 'type' field",
                value=text_obj
            ))
            return result
        
        # Validate based on type
        text_type = text_obj["type"]
        if text_type == "text":
            if "text" not in text_obj:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.REQUIRED_ERROR,
                    field_name=field_name,
                    message="Text object missing required 'text' field",
                    value=text_obj
                ))
            else:
                text_content = text_obj["text"]
                if not isinstance(text_content, dict) or "content" not in text_content:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.SCHEMA_ERROR,
                        field_name=field_name,
                        message="Text object must have text.content field",
                        value=text_obj
                    ))
        
        # Validate annotations if present
        if "annotations" in text_obj:
            annotations = text_obj["annotations"]
            if not isinstance(annotations, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=field_name,
                    message="Annotations must be a dictionary",
                    value=text_obj
                ))
            else:
                # Validate annotation fields
                valid_annotations = {"bold", "italic", "strikethrough", "underline", "code", "color"}
                for key in annotations:
                    if key not in valid_annotations:
                        result.add_warning(ValidationError(
                            error_type=ValidationErrorType.SCHEMA_ERROR,
                            field_name=field_name,
                            message=f"Unknown annotation type: {key}",
                            value=text_obj
                        ))
        
        return result
    
    def _validate_number(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate number property."""
        result = ValidationResult(is_valid=True)
        
        number_value = prop_value.get("number")
        if number_value is not None:
            if not isinstance(number_value, (int, float)):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="Number value must be numeric",
                    value=prop_value
                ))
            else:
                # Check range
                if number_value > self.constraints.max_number_value:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.RANGE_ERROR,
                        field_name=prop_name,
                        message=f"Number exceeds maximum value of {self.constraints.max_number_value}",
                        value=prop_value
                    ))
                elif number_value < self.constraints.min_number_value:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.RANGE_ERROR,
                        field_name=prop_name,
                        message=f"Number below minimum value of {self.constraints.min_number_value}",
                        value=prop_value
                    ))
        
        return result
    
    def _validate_select(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate select property."""
        result = ValidationResult(is_valid=True)
        
        select_value = prop_value.get("select")
        if select_value is not None:
            if not isinstance(select_value, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="Select value must be an object",
                    value=prop_value
                ))
            elif "name" in select_value:
                name = select_value["name"]
                if not isinstance(name, str):
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.TYPE_ERROR,
                        field_name=prop_name,
                        message="Select option name must be a string",
                        value=prop_value
                    ))
                elif len(name) > self.constraints.max_select_option_length:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.LENGTH_ERROR,
                        field_name=prop_name,
                        message=f"Select option exceeds maximum length of {self.constraints.max_select_option_length}",
                        value=prop_value
                    ))
        
        return result
    
    def _validate_multi_select(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate multi-select property."""
        result = ValidationResult(is_valid=True)
        
        multi_select_array = prop_value.get("multi_select", [])
        if not isinstance(multi_select_array, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Multi-select must be an array",
                value=prop_value
            ))
            return result
        
        if len(multi_select_array) > self.constraints.max_multi_select_options:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=prop_name,
                message=f"Multi-select exceeds maximum of {self.constraints.max_multi_select_options} options",
                value=prop_value
            ))
        
        # Validate each option
        for option in multi_select_array:
            if not isinstance(option, dict) or "name" not in option:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.SCHEMA_ERROR,
                    field_name=prop_name,
                    message="Multi-select option must have 'name' field",
                    value=option
                ))
            else:
                name = option["name"]
                if not isinstance(name, str):
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.TYPE_ERROR,
                        field_name=prop_name,
                        message="Multi-select option name must be a string",
                        value=option
                    ))
                elif len(name) > self.constraints.max_select_option_length:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.LENGTH_ERROR,
                        field_name=prop_name,
                        message=f"Multi-select option exceeds maximum length of {self.constraints.max_select_option_length}",
                        value=option
                    ))
        
        return result
    
    def _validate_date(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate date property."""
        result = ValidationResult(is_valid=True)
        
        date_value = prop_value.get("date")
        if date_value is not None:
            if not isinstance(date_value, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="Date value must be an object",
                    value=prop_value
                ))
            else:
                # Validate start date
                start = date_value.get("start")
                if start is None:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.REQUIRED_ERROR,
                        field_name=prop_name,
                        message="Date must have a 'start' field",
                        value=prop_value
                    ))
                else:
                    date_result = self._validate_date_string(start, f"{prop_name}.start")
                    result.merge(date_result)
                
                # Validate end date if present
                end = date_value.get("end")
                if end is not None:
                    date_result = self._validate_date_string(end, f"{prop_name}.end")
                    result.merge(date_result)
                
                # Validate time zone if present
                time_zone = date_value.get("time_zone")
                if time_zone is not None and not isinstance(time_zone, str):
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.TYPE_ERROR,
                        field_name=prop_name,
                        message="Time zone must be a string",
                        value=prop_value
                    ))
        
        return result
    
    def _validate_date_string(self, date_str: str, field_name: str) -> ValidationResult:
        """Validate a date string."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(date_str, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=field_name,
                message="Date must be a string",
                value=date_str
            ))
            return result
        
        # Check ISO format
        try:
            # Try parsing as date
            if len(date_str) == 10:  # YYYY-MM-DD
                datetime.strptime(date_str, "%Y-%m-%d")
            else:
                # Try parsing as datetime
                if date_str.endswith('Z'):
                    datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    datetime.fromisoformat(date_str)
        except ValueError:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                field_name=field_name,
                message="Date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
                value=date_str
            ))
        
        return result
    
    def _validate_people(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate people property."""
        result = ValidationResult(is_valid=True)
        
        people_array = prop_value.get("people", [])
        if not isinstance(people_array, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="People must be an array",
                value=prop_value
            ))
            return result
        
        # Validate each person
        for person in people_array:
            if not isinstance(person, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="Person must be an object",
                    value=person
                ))
            elif "object" not in person or person["object"] != "user":
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.SCHEMA_ERROR,
                    field_name=prop_name,
                    message="Person must have object type 'user'",
                    value=person
                ))
            elif "id" not in person:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.REQUIRED_ERROR,
                    field_name=prop_name,
                    message="Person must have an ID",
                    value=person
                ))
        
        return result
    
    def _validate_files(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate files property."""
        result = ValidationResult(is_valid=True)
        
        files_array = prop_value.get("files", [])
        if not isinstance(files_array, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Files must be an array",
                value=prop_value
            ))
            return result
        
        if len(files_array) > self.constraints.max_files:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=prop_name,
                message=f"Files exceed maximum of {self.constraints.max_files}",
                value=prop_value
            ))
        
        # Validate each file
        for file_obj in files_array:
            if not isinstance(file_obj, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="File must be an object",
                    value=file_obj
                ))
            elif "type" not in file_obj:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.REQUIRED_ERROR,
                    field_name=prop_name,
                    message="File must have a type",
                    value=file_obj
                ))
            elif file_obj["type"] == "external" and "external" in file_obj:
                # Validate external file URL
                url = file_obj["external"].get("url", "")
                if not isinstance(url, str):
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.TYPE_ERROR,
                        field_name=prop_name,
                        message="File URL must be a string",
                        value=file_obj
                    ))
                elif len(url) > self.constraints.max_url_length:
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.LENGTH_ERROR,
                        field_name=prop_name,
                        message=f"File URL exceeds maximum length of {self.constraints.max_url_length}",
                        value=file_obj
                    ))
        
        return result
    
    def _validate_checkbox(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate checkbox property."""
        result = ValidationResult(is_valid=True)
        
        checkbox_value = prop_value.get("checkbox")
        if checkbox_value is not None and not isinstance(checkbox_value, bool):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Checkbox value must be a boolean",
                value=prop_value
            ))
        
        return result
    
    def _validate_url(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate URL property."""
        result = ValidationResult(is_valid=True)
        
        url_value = prop_value.get("url")
        if url_value is not None:
            if not isinstance(url_value, str):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="URL must be a string",
                    value=prop_value
                ))
            elif len(url_value) > self.constraints.max_url_length:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.LENGTH_ERROR,
                    field_name=prop_name,
                    message=f"URL exceeds maximum length of {self.constraints.max_url_length}",
                    value=prop_value
                ))
        
        return result
    
    def _validate_email(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate email property."""
        result = ValidationResult(is_valid=True)
        
        email_value = prop_value.get("email")
        if email_value is not None:
            if not isinstance(email_value, str):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="Email must be a string",
                    value=prop_value
                ))
            elif "@" not in email_value:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name=prop_name,
                    message="Email must contain @ symbol",
                    value=prop_value
                ))
        
        return result
    
    def _validate_phone_number(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate phone number property."""
        result = ValidationResult(is_valid=True)
        
        phone_value = prop_value.get("phone_number")
        if phone_value is not None and not isinstance(phone_value, str):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Phone number must be a string",
                value=prop_value
            ))
        
        return result
    
    def _validate_relation(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate relation property."""
        result = ValidationResult(is_valid=True)
        
        relation_array = prop_value.get("relation", [])
        if not isinstance(relation_array, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name=prop_name,
                message="Relation must be an array",
                value=prop_value
            ))
            return result
        
        if len(relation_array) > self.constraints.max_relation_items:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.LENGTH_ERROR,
                field_name=prop_name,
                message=f"Relation exceeds maximum of {self.constraints.max_relation_items} items",
                value=prop_value
            ))
        
        # Validate each relation
        for relation in relation_array:
            if not isinstance(relation, dict) or "id" not in relation:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.SCHEMA_ERROR,
                    field_name=prop_name,
                    message="Relation item must have an ID",
                    value=relation
                ))
        
        return result
    
    def _validate_status(self, prop_name: str, prop_value: Dict[str, Any]) -> ValidationResult:
        """Validate status property."""
        result = ValidationResult(is_valid=True)
        
        status_value = prop_value.get("status")
        if status_value is not None:
            if not isinstance(status_value, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=prop_name,
                    message="Status value must be an object",
                    value=prop_value
                ))
            elif "name" in status_value:
                name = status_value["name"]
                if not isinstance(name, str):
                    result.add_error(ValidationError(
                        error_type=ValidationErrorType.TYPE_ERROR,
                        field_name=prop_name,
                        message="Status name must be a string",
                        value=prop_value
                    ))
        
        return result
    
    def _validate_parent(self, parent: Dict[str, Any]) -> ValidationResult:
        """Validate parent structure."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(parent, dict):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name="parent",
                message="Parent must be an object",
                value=parent
            ))
            return result
        
        # Must have either database_id, page_id, or workspace
        valid_parent_types = {"database_id", "page_id", "workspace"}
        parent_type = None
        for key in parent:
            if key in valid_parent_types:
                parent_type = key
                break
        
        if not parent_type:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.SCHEMA_ERROR,
                field_name="parent",
                message="Parent must have database_id, page_id, or workspace",
                value=parent
            ))
        elif parent_type in ["database_id", "page_id"]:
            # Validate ID format (should be UUID)
            parent_id = parent[parent_type]
            if not isinstance(parent_id, str):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=f"parent.{parent_type}",
                    message=f"{parent_type} must be a string",
                    value=parent
                ))
            elif not re.match(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$', parent_id.replace("-", "")):
                result.add_warning(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    field_name=f"parent.{parent_type}",
                    message=f"{parent_type} does not appear to be a valid UUID",
                    value=parent
                ))
        
        return result
    
    def _validate_children(self, children: List[Any]) -> ValidationResult:
        """Validate page children (blocks)."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(children, list):
            result.add_error(ValidationError(
                error_type=ValidationErrorType.TYPE_ERROR,
                field_name="children",
                message="Children must be an array",
                value=children
            ))
            return result
        
        # Validate each block
        for i, block in enumerate(children):
            if not isinstance(block, dict):
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.TYPE_ERROR,
                    field_name=f"children[{i}]",
                    message="Block must be an object",
                    value=block
                ))
                continue
            
            # Must have object and type fields
            if "object" not in block or block["object"] != "block":
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.SCHEMA_ERROR,
                    field_name=f"children[{i}]",
                    message="Block must have object type 'block'",
                    value=block
                ))
            
            if "type" not in block:
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.REQUIRED_ERROR,
                    field_name=f"children[{i}]",
                    message="Block must have a type",
                    value=block
                ))
        
        return result