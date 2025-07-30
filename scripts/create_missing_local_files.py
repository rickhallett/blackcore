#!/usr/bin/env python3
"""
Create Missing Local Files - Generate local JSON files for databases that exist only in Notion.

This script takes the exported Notion data and creates properly formatted local JSON files
for the 5 databases that don't currently have local equivalents.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MissingLocalFilesCreator:
    """Creates missing local JSON files from exported Notion data."""
    
    def __init__(self):
        """Initialize the creator."""
        self.base_path = Path(__file__).parent.parent
        self.json_dir = self.base_path / "blackcore/models/json"
        self.export_dir = self.base_path / "exports/complete_notion_export"
        
        # Databases that need local files created
        self.missing_databases = {
            "Leads": "leads_20250712_112322.json",
            "API Control Panel USER GEN": "api_control_panel_user_gen_20250712_112322.json",
            "NSTCG Gamification Profiles": "nstcg_gamification_profiles_20250712_112322.json", 
            "Donations": "donations_20250712_112322.json",
            "NSTCG Feature Flags": "nstcg_feature_flags_20250712_112322.json"
        }
        
        # Target local filenames
        self.local_filenames = {
            "Leads": "leads.json",
            "API Control Panel USER GEN": "api_control_panel_user_gen.json",
            "NSTCG Gamification Profiles": "nstcg_gamification_profiles.json",
            "Donations": "donations.json", 
            "NSTCG Feature Flags": "nstcg_feature_flags.json"
        }
        
    def clean_record_for_local(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean exported Notion record for local JSON format."""
        cleaned = {}
        
        # Skip Notion-specific metadata
        skip_fields = {
            "notion_page_id", "created_time", "last_edited_time", "url"
        }
        
        for key, value in record.items():
            if key not in skip_fields:
                # Handle None values
                if value is None:
                    continue
                    
                # Handle empty lists  
                if isinstance(value, list) and len(value) == 0:
                    continue
                    
                # Handle empty strings
                if isinstance(value, str) and value.strip() == "":
                    continue
                    
                # Handle relation fields (convert to simple format)
                if isinstance(value, list) and all(isinstance(item, dict) and "id" in item for item in value):
                    # This is a relation field, extract just the IDs or convert to titles if available
                    continue  # Skip relations for now, will handle in sync
                    
                cleaned[key] = value
                
        return cleaned
        
    def create_local_file(self, db_name: str, export_filename: str, local_filename: str) -> bool:
        """Create a local JSON file from exported Notion data."""
        try:
            logger.info(f"🔄 Creating local file for {db_name}...")
            
            # Load exported data
            export_file = self.export_dir / export_filename
            if not export_file.exists():
                logger.error(f"❌ Export file not found: {export_file}")
                return False
                
            with open(export_file, 'r') as f:
                export_data = json.load(f)
                
            # Extract records
            records = export_data.get(db_name, [])
            if not records:
                logger.warning(f"⚠️  No records found for {db_name}")
                return False
                
            logger.info(f"   Found {len(records)} records to process")
            
            # Clean records for local format
            cleaned_records = []
            for record in records:
                cleaned = self.clean_record_for_local(record)
                if cleaned:  # Only add if there's meaningful data
                    cleaned_records.append(cleaned)
                    
            logger.info(f"   Cleaned to {len(cleaned_records)} records")
            
            # Create local JSON structure
            local_data = {db_name: cleaned_records}
            
            # Save to local file
            local_file = self.json_dir / local_filename
            
            # Backup existing file if it exists
            if local_file.exists():
                backup_file = local_file.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                local_file.rename(backup_file)
                logger.info(f"   📋 Existing file backed up to: {backup_file}")
                
            with open(local_file, 'w') as f:
                json.dump(local_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"✅ Created local file: {local_file}")
            logger.info(f"   📊 Records: {len(cleaned_records)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create local file for {db_name}: {str(e)}")
            return False
            
    def create_all_missing_files(self) -> Dict[str, bool]:
        """Create all missing local files."""
        logger.info("=" * 80)
        logger.info("🚀 CREATING MISSING LOCAL JSON FILES")
        logger.info("=" * 80)
        
        results = {}
        
        # Ensure target directory exists
        self.json_dir.mkdir(parents=True, exist_ok=True)
        
        # Create each missing file
        for db_name, export_filename in self.missing_databases.items():
            local_filename = self.local_filenames[db_name]
            success = self.create_local_file(db_name, export_filename, local_filename)
            results[db_name] = success
            
        # Summary
        logger.info("=" * 80)
        logger.info("📊 CREATION SUMMARY")
        logger.info("=" * 80)
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        for db_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"{db_name}: {status}")
            
        logger.info(f"\nTotal: {successful}/{total} files created successfully")
        
        return results
        
    def update_notion_config(self) -> bool:
        """Update notion_config.json to include the new databases."""
        try:
            logger.info("🔄 Updating notion_config.json with new databases...")
            
            config_file = self.base_path / "blackcore/config/notion_config.json"
            
            # Load existing config
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Add new database configurations
            new_configs = {
                "Leads": {
                    "id": "2174753d-608e-80ac-b6be-cf0e623262fe",
                    "local_json_path": "blackcore/models/json/leads.json",
                    "json_data_key": "Leads",
                    "title_property": "Request Name",
                    "list_properties": [],
                    "relations": {}
                },
                "API Control Panel USER GEN": {
                    "id": "2254753d-608e-814f-8701-ca8112cd1de7",
                    "local_json_path": "blackcore/models/json/api_control_panel_user_gen.json",
                    "json_data_key": "API Control Panel USER GEN",
                    "title_property": "Name",
                    "list_properties": [],
                    "relations": {}
                },
                "NSTCG Gamification Profiles": {
                    "id": "21d4753d-608e-81a4-9bdc-ef5920c5ec30",
                    "local_json_path": "blackcore/models/json/nstcg_gamification_profiles.json",
                    "json_data_key": "NSTCG Gamification Profiles",
                    "title_property": "Name",
                    "list_properties": ["Submission"],
                    "relations": {"Submission": "Leads"}
                },
                "Donations": {
                    "id": "21d4753d-608e-801a-86b3-d494a6df0e97",
                    "local_json_path": "blackcore/models/json/donations.json",
                    "json_data_key": "Donations",
                    "title_property": "Donation ID",
                    "list_properties": [],
                    "relations": {}
                },
                "NSTCG Feature Flags": {
                    "id": "21e4753d-608e-81c5-9ac2-c39e279a2948",
                    "local_json_path": "blackcore/models/json/nstcg_feature_flags.json",
                    "json_data_key": "NSTCG Feature Flags", 
                    "title_property": "Feature Path",
                    "list_properties": [],
                    "relations": {}
                }
            }
            
            # Add to existing config (only if not already present)
            updated = False
            for db_name, db_config in new_configs.items():
                if db_name not in config:
                    config[db_name] = db_config
                    updated = True
                    logger.info(f"   ➕ Added {db_name} to config")
                else:
                    logger.info(f"   ⚠️  {db_name} already in config, skipping")
                    
            if updated:
                # Backup existing config
                backup_file = config_file.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                config_file.rename(backup_file)
                logger.info(f"   📋 Config backed up to: {backup_file}")
                
                # Save updated config
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                    
                logger.info("✅ notion_config.json updated successfully")
            else:
                logger.info("ℹ️  No config updates needed")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update notion_config.json: {str(e)}")
            return False


def main():
    """Main execution."""
    try:
        # Initialize creator
        creator = MissingLocalFilesCreator()
        
        # Create missing files
        results = creator.create_all_missing_files()
        
        # Update config if files were created successfully
        successful_files = [db for db, success in results.items() if success]
        if successful_files:
            creator.update_notion_config()
            
        # Final status
        if all(results.values()):
            logger.info("🎉 All missing local files created successfully!")
            return 0
        else:
            failed = [db for db, success in results.items() if not success]
            logger.error(f"❌ Failed to create files for: {', '.join(failed)}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())