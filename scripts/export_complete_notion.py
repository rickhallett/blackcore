#!/usr/bin/env python3
"""
Complete Notion Export - Export ALL records from ALL Notion databases with pagination.

This script performs a comprehensive export of the entire Notion workspace,
ensuring 100% data capture with proper pagination and rate limiting.
"""

import os
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Set environment variable
os.environ['NOTION_API_KEY'] = '***REMOVED***'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.notion_schema_inspector import NotionSchemaInspector
from notion_client import Client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NotionCompleteExporter:
    """Complete Notion workspace exporter with pagination and rate limiting."""
    
    def __init__(self):
        """Initialize the exporter."""
        self.client = Client(auth=os.environ['NOTION_API_KEY'])
        self.schema_inspector = NotionSchemaInspector(self.client)
        self.base_path = Path(__file__).parent.parent
        
        # Load existing config to get database IDs
        self.config_path = self.base_path / "blackcore/config/notion_config.json"
        with open(self.config_path) as f:
            self.notion_config = json.load(f)
            
        # Rate limiting
        self.request_count = 0
        self.start_time = time.time()
        self.min_request_interval = 1.0 / 3.0  # 3 requests per second
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        self.request_count += 1
        
    def export_database_with_pagination(self, database_id: str, database_name: str) -> Dict[str, Any]:
        """Export all records from a single database with proper pagination."""
        logger.info(f"🔄 Exporting {database_name} (ID: {database_id})...")
        
        all_pages = []
        has_more = True
        start_cursor = None
        page_count = 0
        
        try:
            while has_more:
                self._rate_limit()
                
                # Build query parameters
                query_params = {
                    "database_id": database_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                    
                # Make API request
                response = self.client.databases.query(**query_params)
                
                # Extract results
                results = response.get("results", [])
                all_pages.extend(results)
                page_count += len(results)
                
                # Check pagination
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
                
                logger.info(f"   Fetched {len(results)} records (total: {page_count})")
                
            # Process and simplify properties
            simplified_pages = []
            for page in all_pages:
                simplified_page = self._simplify_page_properties(page)
                simplified_pages.append(simplified_page)
                
            logger.info(f"✅ Exported {page_count} records from {database_name}")
            
            return {
                "database_name": database_name,
                "database_id": database_id,
                "total_records": page_count,
                "export_timestamp": datetime.now().isoformat(),
                "records": simplified_pages
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to export {database_name}: {str(e)}")
            return {
                "database_name": database_name,
                "database_id": database_id,
                "error": str(e),
                "export_timestamp": datetime.now().isoformat(),
                "total_records": 0,
                "records": []
            }
            
    def _simplify_page_properties(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Notion page properties to simplified format."""
        properties = page.get("properties", {})
        simplified = {
            "notion_page_id": page["id"],
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "url": page.get("url")
        }
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            
            try:
                if prop_type == "title":
                    value = prop_data["title"][0]["plain_text"] if prop_data["title"] else None
                elif prop_type == "rich_text":
                    value = prop_data["rich_text"][0]["plain_text"] if prop_data["rich_text"] else None
                elif prop_type == "select":
                    value = prop_data["select"]["name"] if prop_data["select"] else None
                elif prop_type == "multi_select":
                    value = [item["name"] for item in prop_data["multi_select"]] if prop_data["multi_select"] else []
                elif prop_type == "status":
                    value = prop_data["status"]["name"] if prop_data["status"] else None
                elif prop_type == "date":
                    value = prop_data["date"]["start"] if prop_data["date"] else None
                elif prop_type == "number":
                    value = prop_data["number"]
                elif prop_type == "checkbox":
                    value = prop_data["checkbox"]
                elif prop_type == "url":
                    value = prop_data["url"]
                elif prop_type == "email":
                    value = prop_data["email"]
                elif prop_type == "phone_number":
                    value = prop_data["phone_number"]
                elif prop_type == "people":
                    value = [{"id": person["id"], "name": person.get("name", "")} for person in prop_data["people"]] if prop_data["people"] else []
                elif prop_type == "files":
                    value = [{"url": file.get("file", {}).get("url", ""), "name": file.get("name", "")} for file in prop_data["files"]] if prop_data["files"] else []
                elif prop_type == "relation":
                    value = [{"id": rel["id"]} for rel in prop_data["relation"]] if prop_data["relation"] else []
                elif prop_type == "formula":
                    formula_type = prop_data["formula"]["type"]
                    if formula_type in ["string", "number", "boolean", "date"]:
                        value = prop_data["formula"][formula_type]
                    else:
                        value = None
                elif prop_type == "rollup":
                    rollup_type = prop_data["rollup"]["type"]
                    if rollup_type == "array":
                        value = [item.get("title", [{}])[0].get("plain_text", "") if item.get("title") else str(item) for item in prop_data["rollup"]["array"]]
                    else:
                        value = prop_data["rollup"].get(rollup_type)
                elif prop_type in ["created_time", "last_edited_time"]:
                    value = prop_data[prop_type]
                elif prop_type in ["created_by", "last_edited_by"]:
                    value = {"id": prop_data[prop_type]["id"], "name": prop_data[prop_type].get("name", "")} if prop_data[prop_type] else None
                else:
                    # Unknown property type, store raw data
                    value = prop_data
                    
                simplified[prop_name] = value
                
            except Exception as e:
                logger.warning(f"Error processing property '{prop_name}' of type '{prop_type}': {e}")
                simplified[prop_name] = None
                
        return simplified
        
    def export_all_databases(self) -> Dict[str, Any]:
        """Export all databases in the Notion workspace."""
        logger.info("=" * 80)
        logger.info("🚀 STARTING COMPLETE NOTION WORKSPACE EXPORT")
        logger.info("=" * 80)
        
        export_results = {
            "export_timestamp": datetime.now().isoformat(),
            "total_databases": len(self.notion_config),
            "databases": {},
            "summary": {
                "successful_exports": 0,
                "failed_exports": 0,
                "total_records": 0
            }
        }
        
        # Export each database
        for db_name, db_config in self.notion_config.items():
            database_id = db_config["id"]
            
            # Export database
            result = self.export_database_with_pagination(database_id, db_name)
            export_results["databases"][db_name] = result
            
            # Update summary
            if result.get("error"):
                export_results["summary"]["failed_exports"] += 1
            else:
                export_results["summary"]["successful_exports"] += 1
                export_results["summary"]["total_records"] += result["total_records"]
                
        # Log final summary
        logger.info("=" * 80)
        logger.info("📊 EXPORT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total databases: {export_results['total_databases']}")
        logger.info(f"Successful exports: {export_results['summary']['successful_exports']}")
        logger.info(f"Failed exports: {export_results['summary']['failed_exports']}")
        logger.info(f"Total records exported: {export_results['summary']['total_records']}")
        logger.info(f"Total API requests: {self.request_count}")
        logger.info(f"Export duration: {time.time() - self.start_time:.2f} seconds")
        
        return export_results
        
    def save_export_results(self, export_results: Dict[str, Any]):
        """Save export results to files."""
        export_dir = self.base_path / "exports" / "complete_notion_export"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Save complete results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        complete_file = export_dir / f"complete_export_{timestamp}.json"
        
        with open(complete_file, 'w') as f:
            json.dump(export_results, f, indent=2, default=str)
            
        logger.info(f"📁 Complete export saved to: {complete_file}")
        
        # Save individual database files
        for db_name, db_data in export_results["databases"].items():
            if not db_data.get("error") and db_data["records"]:
                # Create filename-safe name
                safe_name = db_name.lower().replace(" ", "_").replace("&", "and")
                db_file = export_dir / f"{safe_name}_{timestamp}.json"
                
                # Save in format compatible with local JSON structure
                db_export = {db_name: db_data["records"]}
                
                with open(db_file, 'w') as f:
                    json.dump(db_export, f, indent=2, default=str)
                    
                logger.info(f"📄 {db_name} saved to: {db_file}")
                
        return export_dir


def main():
    """Main export execution."""
    try:
        # Initialize exporter
        exporter = NotionCompleteExporter()
        
        # Perform complete export
        results = exporter.export_all_databases()
        
        # Save results
        export_dir = exporter.save_export_results(results)
        
        # Final status
        if results["summary"]["failed_exports"] == 0:
            logger.info("🎉 Complete export successful!")
            return 0
        else:
            logger.warning(f"⚠️  Export completed with {results['summary']['failed_exports']} failures")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Fatal error during export: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())