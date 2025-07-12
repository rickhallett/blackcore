"""
Data Transformer - Handles transformations for Notion sync compatibility.
"""

import json
import logging
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms JSON data to match Notion property requirements."""
    
    def __init__(self, property_mappings: Dict[str, Any], notion_schemas: Dict[str, Any]):
        self.property_mappings = property_mappings
        self.notion_schemas = notion_schemas
        self.page_id_map = {}  # Track created pages for relation linking
        
    def transform_database_records(self, database_name: str, records: List[Dict[str, Any]], stage: int = 1) -> List[Dict[str, Any]]:
        """Transform all records for a database based on the current stage."""
        if database_name not in self.property_mappings:
            logger.warning(f"No mapping configuration for database: {database_name}")
            return records
            
        transformed = []
        mapping_config = self.property_mappings[database_name]
        
        for record in records:
            transformed_record = self.transform_record(record, mapping_config, database_name, stage)
            if transformed_record:
                transformed.append(transformed_record)
                
        return transformed
        
    def transform_record(self, record: Dict[str, Any], mapping_config: Dict[str, Any], database_name: str, stage: int) -> Dict[str, Any]:
        """Transform a single record based on mapping configuration."""
        transformed = {}
        
        # Get field mappings and exclusions
        mappings = mapping_config.get('mappings', {})
        exclude = mapping_config.get('exclude', [])
        transformations = mapping_config.get('transformations', {})
        
        # Process each field in the record
        for json_field, value in record.items():
            # Skip excluded fields
            if json_field in exclude:
                continue
                
            # Get the Notion property name
            notion_field = mappings.get(json_field)
            if not notion_field:
                # Field not in mappings, skip it
                continue
                
            # Get transformation config for this field
            transform_config = transformations.get(notion_field, {})
            transform_type = transform_config.get('type')
            transform_stage = transform_config.get('stage', 1)
            
            # Skip relation fields if not in the right stage
            if transform_type == 'relation' and stage < transform_stage:
                continue
                
            # Apply transformation
            transformed_value = self.transform_value(
                value, 
                transform_type, 
                transform_config,
                database_name,
                notion_field
            )
            
            # Only add if we have a valid transformed value
            if transformed_value is not None:
                transformed[notion_field] = transformed_value
                
        return transformed
        
    def transform_value(self, value: Any, transform_type: Optional[str], config: Dict[str, Any], database_name: str, field_name: str) -> Any:
        """Transform a value based on its type."""
        if value is None or value == "":
            return None
            
        if transform_type == 'date':
            return self._transform_date(value)
        elif transform_type == 'url':
            return self._transform_url(value)
        elif transform_type == 'select':
            return self._transform_select(value, config, database_name, field_name)
        elif transform_type == 'status':
            return self._transform_status(value, config, database_name, field_name)
        elif transform_type == 'rich_text':
            return self._transform_rich_text(value, config)
        elif transform_type == 'relation':
            return self._transform_relation(value, config, database_name, field_name)
        elif config.get('extract_nested'):
            return self._extract_nested_value(value)
        else:
            # Return as-is for other types
            return value
            
    def _transform_date(self, value: Union[str, date]) -> Optional[str]:
        """Transform date to ISO format."""
        if not value:
            return None
            
        if isinstance(value, str):
            # Try various date formats
            date_formats = [
                "%Y-%m-%d",           # 2024-06-26
                "%B %d, %Y",          # June 26, 2024
                "%B %d",              # June 26
                "%B %Y",              # June 2024
                "%Y"                  # 2024
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value, fmt)
                    # For partial dates, default to first of month/year
                    if fmt == "%B %Y":
                        parsed_date = parsed_date.replace(day=1)
                    elif fmt == "%Y":
                        parsed_date = parsed_date.replace(month=1, day=1)
                    elif fmt == "%B %d":
                        # Assume current year for month-day only
                        parsed_date = parsed_date.replace(year=datetime.now().year)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue
                    
            # If no format matches, try to extract a year
            year_match = re.search(r'\b(20\d{2})\b', value)
            if year_match:
                return f"{year_match.group(1)}-01-01"
                
            logger.warning(f"Could not parse date: {value}")
            return None
            
        return value.isoformat() if hasattr(value, 'isoformat') else None
        
    def _transform_url(self, value: str) -> Optional[str]:
        """Transform and validate URL."""
        if not value or value == "":
            return None
            
        # Add protocol if missing
        if not value.startswith(('http://', 'https://')):
            value = f"https://{value}"
            
        # Validate URL
        try:
            result = urlparse(value)
            if all([result.scheme, result.netloc]):
                return value
        except Exception:
            pass
            
        logger.warning(f"Invalid URL: {value}")
        return None
        
    def _transform_select(self, value: str, config: Dict[str, Any], database_name: str, field_name: str) -> Optional[str]:
        """Transform select field value."""
        if not value:
            return config.get('default')
            
        # Extract from nested structure if needed
        if isinstance(value, dict) and 'select' in value:
            value = value['select'].get('name', '')
            
        # Check for value mappings in config
        mappings = config.get('mappings', {})
        if value in mappings:
            value = mappings[value]
            
        # Get valid options from schema
        valid_options = self._get_valid_options(database_name, field_name)
        
        # Check if value is valid
        if value in valid_options:
            return value
            
        # Try case-insensitive match
        for option in valid_options:
            if value.lower() == option.lower():
                return option
                
        # Use default if available
        default = config.get('default')
        if default and default in valid_options:
            logger.warning(f"Invalid select value '{value}' for {field_name}, using default '{default}'")
            return default
            
        logger.warning(f"No valid option for select field {field_name}: '{value}' (valid: {valid_options})")
        return None
        
    def _transform_status(self, value: str, config: Dict[str, Any], database_name: str, field_name: str) -> Optional[str]:
        """Transform status field value."""
        if not value:
            return config.get('default', 'Not started')
            
        # Get valid options from schema
        valid_options = self._get_valid_options(database_name, field_name)
        
        # Map common status values
        status_map = {
            'active': 'In progress',
            'pending': 'Not started',
            'complete': 'Done',
            'completed': 'Done'
        }
        
        # Check if value is valid
        if value in valid_options:
            return value
            
        # Try mapped value
        mapped = status_map.get(value.lower())
        if mapped and mapped in valid_options:
            return mapped
            
        # Use default
        return config.get('default', 'Not started')
        
    def _transform_rich_text(self, value: str, config: Dict[str, Any]) -> str:
        """Transform rich text field value."""
        if not value:
            return ""
            
        # Extract from nested structure if needed
        if isinstance(value, dict) and 'rich_text' in value:
            rich_text_list = value['rich_text']
            if isinstance(rich_text_list, list) and len(rich_text_list) > 0:
                value = rich_text_list[0].get('text', {}).get('content', '')
                
        # Truncate if needed
        max_length = config.get('max_length', 2000)
        if len(value) > max_length:
            logger.warning(f"Truncating rich text from {len(value)} to {max_length} characters")
            value = value[:max_length-3] + "..."
            
        return value
        
    def _transform_relation(self, value: Union[str, List[str]], config: Dict[str, Any], database_name: str, field_name: str) -> List[str]:
        """Transform relation field value (stage 3 only)."""
        # This will be populated in stage 3 with actual page IDs
        # For now, return empty list
        return []
        
    def _extract_nested_value(self, value: Any) -> Any:
        """Extract value from nested Notion export structure."""
        if isinstance(value, dict):
            # Handle nested select structure
            if 'select' in value:
                return value['select'].get('name')
            # Handle nested rich_text structure
            elif 'rich_text' in value and isinstance(value['rich_text'], list):
                if len(value['rich_text']) > 0:
                    return value['rich_text'][0].get('text', {}).get('content', '')
            # Handle other nested structures
            elif 'title' in value and isinstance(value['title'], list):
                if len(value['title']) > 0:
                    return value['title'][0].get('text', {}).get('content', '')
                    
        return value
        
    def _get_valid_options(self, database_name: str, field_name: str) -> List[str]:
        """Get valid options for a select/status field from schema."""
        # Find the schema by database name
        for db_id, schema in self.notion_schemas.items():
            if schema.get('title') == database_name:
                prop_schema = schema.get('properties', {}).get(field_name, {})
                return prop_schema.get('options', [])
        return []
        
    def set_page_id(self, database_name: str, title: str, page_id: str):
        """Store page ID for relation linking in stage 3."""
        if database_name not in self.page_id_map:
            self.page_id_map[database_name] = {}
        self.page_id_map[database_name][title] = page_id
        
    def get_page_id(self, database_name: str, title: str) -> Optional[str]:
        """Get page ID for relation linking."""
        return self.page_id_map.get(database_name, {}).get(title)
        
    def update_relations(self, record: Dict[str, Any], mapping_config: Dict[str, Any], database_name: str) -> Dict[str, Any]:
        """Update relation fields with actual page IDs (stage 3)."""
        updated = {}
        transformations = mapping_config.get('transformations', {})
        mappings = mapping_config.get('mappings', {})
        
        for json_field, notion_field in mappings.items():
            if json_field not in record:
                continue
                
            transform_config = transformations.get(notion_field, {})
            if transform_config.get('type') != 'relation':
                continue
                
            value = record[json_field]
            if not value:
                continue
                
            # Convert to list if single value
            if isinstance(value, str):
                value = [value]
                
            # Look up page IDs
            page_ids = []
            for item in value:
                # Determine target database from field name
                target_db = self._get_target_database(database_name, notion_field)
                if target_db:
                    page_id = self.get_page_id(target_db, item)
                    if page_id:
                        page_ids.append(page_id)
                    else:
                        logger.warning(f"No page ID found for '{item}' in {target_db}")
                        
            updated[notion_field] = page_ids
            
        return updated
        
    def _get_target_database(self, source_db: str, field_name: str) -> Optional[str]:
        """Determine target database for a relation field."""
        # Map field names to target databases
        relation_map = {
            "Organization": "Organizations & Bodies",
            "Linked Transgressions": "Identified Transgressions",
            "Perpetrator (Person)": "People & Contacts",
            "Perpetrator (Org)": "Organizations & Bodies",
            "Evidence": "Documents & Evidence",
            "Source Organization": "Organizations & Bodies",
            "Tagged Entities": "People & Contacts",
            "Agendas & Epics": "Agendas & Epics",
            "Related Agenda": "Agendas & Epics",
            "Actionable Tasks": "Actionable Tasks",
            "Key Documents": "Documents & Evidence",
            "People Involved": "People & Contacts",
            "Related Transgressions": "Identified Transgressions"
        }
        
        return relation_map.get(field_name)


def load_property_mappings() -> Dict[str, Any]:
    """Load property mappings from JSON file."""
    mappings_path = Path(__file__).parent / "property_mappings.json"
    with open(mappings_path, 'r') as f:
        return json.load(f)
        

def load_notion_schemas() -> Dict[str, Any]:
    """Load Notion schemas from JSON file."""
    schemas_path = Path(__file__).parent.parent.parent / "notion_schemas.json"
    with open(schemas_path, 'r') as f:
        return json.load(f)