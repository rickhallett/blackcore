"""
Notion Schema Inspector - Queries Notion databases to get property types and valid options.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from notion_client import Client

logger = logging.getLogger(__name__)


class NotionSchemaInspector:
    """Inspects Notion database schemas to extract property types and valid options."""
    
    def __init__(self, notion_client: Client):
        self.client = notion_client
        self._schema_cache = {}
        
    def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Get the complete schema for a database."""
        if database_id in self._schema_cache:
            return self._schema_cache[database_id]
            
        try:
            db = self.client.databases.retrieve(database_id=database_id)
            schema = self._extract_schema(db)
            self._schema_cache[database_id] = schema
            return schema
        except Exception as e:
            logger.error(f"Failed to retrieve schema for database {database_id}: {e}")
            return {}
            
    def _extract_schema(self, database: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant schema information from database response."""
        properties = database.get('properties', {})
        schema = {
            'id': database['id'],
            'title': database.get('title', [{}])[0].get('plain_text', 'Unknown'),
            'properties': {}
        }
        
        for prop_name, prop_info in properties.items():
            prop_type = prop_info['type']
            prop_schema = {
                'type': prop_type,
                'id': prop_info['id']
            }
            
            # Extract type-specific information
            if prop_type == 'select':
                prop_schema['options'] = [
                    opt['name'] for opt in prop_info.get('select', {}).get('options', [])
                ]
            elif prop_type == 'multi_select':
                prop_schema['options'] = [
                    opt['name'] for opt in prop_info.get('multi_select', {}).get('options', [])
                ]
            elif prop_type == 'status':
                prop_schema['options'] = [
                    opt['name'] for opt in prop_info.get('status', {}).get('options', [])
                ]
                prop_schema['groups'] = [
                    grp['name'] for grp in prop_info.get('status', {}).get('groups', [])
                ]
            elif prop_type == 'relation':
                relation_info = prop_info.get('relation', {})
                prop_schema['database_id'] = relation_info.get('database_id')
                prop_schema['type_info'] = relation_info.get('type')
                
            schema['properties'][prop_name] = prop_schema
            
        return schema
        
    def get_select_options(self, database_id: str, property_name: str) -> List[str]:
        """Get valid options for a select/multi_select/status property."""
        schema = self.get_database_schema(database_id)
        prop = schema.get('properties', {}).get(property_name, {})
        return prop.get('options', [])
        
    def get_property_type(self, database_id: str, property_name: str) -> Optional[str]:
        """Get the type of a specific property."""
        schema = self.get_database_schema(database_id)
        prop = schema.get('properties', {}).get(property_name, {})
        return prop.get('type')
        
    def save_all_schemas(self, output_path: str):
        """Save all cached schemas to a JSON file for reference."""
        with open(output_path, 'w') as f:
            json.dump(self._schema_cache, f, indent=2)
            
    def inspect_all_databases(self, database_ids: Dict[str, str]) -> Dict[str, Any]:
        """Inspect all provided databases and return their schemas."""
        all_schemas = {}
        for db_name, db_id in database_ids.items():
            logger.info(f"Inspecting schema for {db_name} ({db_id})")
            schema = self.get_database_schema(db_id)
            all_schemas[db_name] = schema
        return all_schemas


def main():
    """Test the schema inspector with production databases."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize Notion client
    notion = Client(auth=os.getenv('NOTION_API_KEY'))
    
    # Database IDs from config
    databases = {
        "People & Contacts": "21f4753d-608e-8173-b6dc-fc6302804e69",
        "Organizations & Bodies": "21f4753d-608e-81a9-8822-f40d30259853",
        "Actionable Tasks": "21f4753d-608e-81ef-998f-ccc26b440542",
        "Intelligence & Transcripts": "21f4753d-608e-81ea-9c50-fc5b78162374",
        "Identified Transgressions": "21f4753d-608e-8140-861f-f536b3c9262b",
        "Documents & Evidence": "21f4753d-608e-8102-9750-d25682bf1128",
        "Agendas & Epics": "21f4753d-608e-8109-8a14-f46f1e05e506",
        "Key Places & Events": "21f4753d-608e-812b-a22e-c805303cb28d"
    }
    
    # Create inspector and get all schemas
    inspector = NotionSchemaInspector(notion)
    all_schemas = inspector.inspect_all_databases(databases)
    
    # Save schemas for reference
    output_path = Path(__file__).parent.parent.parent / "notion_schemas.json"
    inspector.save_all_schemas(str(output_path))
    
    print(f"Schemas saved to {output_path}")
    
    # Print summary
    for db_name, schema in all_schemas.items():
        print(f"\n{db_name}:")
        for prop_name, prop_info in schema.get('properties', {}).items():
            prop_type = prop_info['type']
            print(f"  - {prop_name}: {prop_type}", end="")
            if prop_type in ['select', 'multi_select', 'status']:
                options = prop_info.get('options', [])
                print(f" ({len(options)} options: {', '.join(options[:3])}...)")
            else:
                print()


if __name__ == "__main__":
    main()