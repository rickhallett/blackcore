#!/usr/bin/env python3
"""
Fix for property formatting issues in the sync processor.
Updates the staged sync processor to properly format properties for Notion API.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def add_prepare_properties_method():
    """Add the _prepare_properties method to staged_json_sync.py"""
    
    method_code = '''
    def _prepare_properties(self, record: Dict[str, Any], db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare properties for Notion API using schema information."""
        properties = {}
        database_name = db_config.get("json_data_key", "")
        
        # Get the database schema
        schema = None
        for db_id, db_schema in self.notion_schemas.items():
            if db_schema.get('title') == database_name:
                schema = db_schema
                break
                
        if not schema:
            # Fallback to parent implementation
            return super()._prepare_properties(record, db_config)
            
        # Get property schemas
        property_schemas = schema.get('properties', {})
        
        # Process each field in the record
        for key, value in record.items():
            # Skip None values
            if value is None or value == "":
                continue
                
            # Get the property schema
            prop_schema = property_schemas.get(key, {})
            prop_type = prop_schema.get('type')
            
            # Format based on property type
            if prop_type == 'title':
                properties[key] = {
                    "title": [{"text": {"content": str(value)}}]
                }
            elif prop_type == 'rich_text':
                properties[key] = {
                    "rich_text": [{"text": {"content": str(value)}}]
                }
            elif prop_type == 'select':
                if value:  # Only set if we have a value
                    properties[key] = {
                        "select": {"name": str(value)}
                    }
            elif prop_type == 'multi_select':
                if isinstance(value, list):
                    properties[key] = {
                        "multi_select": [{"name": str(item)} for item in value if item]
                    }
                else:
                    properties[key] = {
                        "multi_select": [{"name": str(value)}]
                    }
            elif prop_type == 'status':
                if value:  # Only set if we have a value
                    properties[key] = {
                        "status": {"name": str(value)}
                    }
            elif prop_type == 'date':
                if value:
                    properties[key] = {
                        "date": {"start": str(value)}
                    }
            elif prop_type == 'checkbox':
                properties[key] = {
                    "checkbox": bool(value)
                }
            elif prop_type == 'number':
                properties[key] = {
                    "number": float(value) if value else None
                }
            elif prop_type == 'url':
                if value:
                    properties[key] = {
                        "url": str(value)
                    }
            elif prop_type == 'email':
                if value:
                    properties[key] = {
                        "email": str(value)
                    }
            elif prop_type == 'phone_number':
                if value:
                    properties[key] = {
                        "phone_number": str(value)
                    }
            elif prop_type == 'relation':
                # Relations should be handled in stage 3
                if isinstance(value, list) and all(isinstance(item, str) and '-' in item for item in value):
                    # These look like page IDs
                    properties[key] = {
                        "relation": [{"id": page_id} for page_id in value]
                    }
                # Otherwise skip for now
            elif prop_type == 'people':
                # People properties cannot be set via API unless using user IDs
                continue
            elif prop_type == 'files':
                # Files need to be URLs
                continue
            else:
                # Default to rich text for unknown types
                properties[key] = {
                    "rich_text": [{"text": {"content": str(value)}}]
                }
                
        return properties
'''
    
    # Read the current file
    file_path = Path(__file__).parent.parent / "blackcore" / "minimal" / "staged_json_sync.py"
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Find where to insert the method (after the _update_page method)
    insert_pos = content.find("    def _merge_results(")
    if insert_pos == -1:
        print("Could not find insertion point")
        return False
        
    # Insert the new method
    new_content = content[:insert_pos] + method_code + "\n" + content[insert_pos:]
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
        
    print(f"✅ Added _prepare_properties method to {file_path}")
    return True


def main():
    """Apply the fix."""
    print("Fixing property formatting in staged sync processor...")
    
    if add_prepare_properties_method():
        print("\n✅ Fix applied successfully!")
        print("\nThe sync processor will now:")
        print("  - Use the Notion schema to determine property types")
        print("  - Format each property correctly for the Notion API")
        print("  - Handle all property types (title, select, date, etc.)")
    else:
        print("\n❌ Failed to apply fix")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())