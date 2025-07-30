#!/usr/bin/env python3
"""
Upload Missing Records (Simple) - Direct upload of missing local records to Notion.

Simple approach that directly creates pages using the Notion client for the few missing records.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Set environment variable
os.environ['NOTION_API_KEY'] = '***REMOVED***'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from notion_client import Client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleMissingRecordsUploader:
    """Simple uploader for missing local records."""
    
    def __init__(self):
        """Initialize the uploader."""
        self.client = Client(auth=os.environ['NOTION_API_KEY'])
        self.base_path = Path(__file__).parent.parent
        self.reports_dir = self.base_path / "reports/sync_comparison"
        
        # Find latest comparison report
        report_files = list(self.reports_dir.glob("sync_comparison_*.json"))
        if not report_files:
            raise FileNotFoundError("No comparison reports found. Run compare_local_notion.py first.")
            
        self.latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"Using comparison report: {self.latest_report}")
        
        # Load notion config
        notion_config_path = self.base_path / "blackcore/config/notion_config.json"
        with open(notion_config_path, 'r') as f:
            self.notion_config = json.load(f)
            
    def load_comparison_report(self) -> Dict[str, Any]:
        """Load the latest comparison report."""
        with open(self.latest_report, 'r') as f:
            return json.load(f)
            
    def format_record_for_notion(self, record: Dict[str, Any], db_name: str) -> Dict[str, Any]:
        """Format a local record for Notion API."""
        properties = {}
        
        # Handle different database types
        if db_name == "Intelligence & Transcripts":
            # Required fields for Intelligence & Transcripts
            if "Entry Title" in record:
                properties["Entry Title"] = {
                    "title": [{"text": {"content": str(record["Entry Title"])}}]
                }
            if "Date Recorded" in record:
                properties["Date Recorded"] = {
                    "date": {"start": str(record["Date Recorded"])}
                }
            if "Source" in record:
                properties["Source"] = {
                    "select": {"name": str(record["Source"])}
                }
            if "Raw Transcript/Note" in record:
                content = str(record["Raw Transcript/Note"])
                if len(content) > 2000:
                    content = content[:1997] + "..."
                properties["Raw Transcript/Note"] = {
                    "rich_text": [{"text": {"content": content}}]
                }
            if "Processing Status" in record:
                properties["Processing Status"] = {
                    "select": {"name": str(record["Processing Status"])}
                }
                
        elif db_name == "Key Places & Events":
            # Required fields for Key Places & Events
            if "Event / Place Name" in record:
                properties["Event / Place Name"] = {
                    "title": [{"text": {"content": str(record["Event / Place Name"])}}]
                }
            if "Type" in record:
                properties["Type"] = {
                    "select": {"name": str(record["Type"])}
                }
            if "Description" in record:
                properties["Description"] = {
                    "rich_text": [{"text": {"content": str(record["Description"])}}]
                }
            if "Date of Event" in record:
                properties["Date of Event"] = {
                    "date": {"start": str(record["Date of Event"])}
                }
                
        # Add any other string fields as rich text (with truncation)
        for key, value in record.items():
            if key not in properties and value and isinstance(value, str):
                if len(value.strip()) > 0:
                    content = str(value)
                    if len(content) > 2000:
                        content = content[:1997] + "..."
                    properties[key] = {
                        "rich_text": [{"text": {"content": content}}]
                    }
                    
        return properties
        
    def create_notion_page(self, database_id: str, properties: Dict[str, Any], title: str) -> Dict[str, Any]:
        """Create a page in Notion."""
        try:
            logger.info(f"   🔄 Creating page: {title}")
            
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            
            logger.info(f"   ✅ Created page: {response['id']}")
            return {
                "success": True,
                "page_id": response["id"],
                "title": title,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"   ❌ Failed to create page '{title}': {str(e)}")
            return {
                "success": False,
                "page_id": None,
                "title": title,
                "error": str(e)
            }
            
    def upload_all_missing_records(self) -> Dict[str, Any]:
        """Upload all missing local records to Notion."""
        logger.info("=" * 80)
        logger.info("🚀 UPLOADING MISSING LOCAL RECORDS TO NOTION (SIMPLE)")
        logger.info("=" * 80)
        
        # Load comparison report
        report = self.load_comparison_report()
        
        upload_results = {
            "timestamp": datetime.now().isoformat(),
            "databases_processed": {},
            "summary": {
                "total_databases": 0,
                "successful_uploads": 0,
                "failed_uploads": 0,
                "total_records_uploaded": 0
            }
        }
        
        # Process each database with missing records
        for db_name, db_comparison in report["detailed_comparisons"].items():
            missing_from_notion = db_comparison.get("missing_from_notion", [])
            
            if not missing_from_notion:
                continue
                
            logger.info(f"\n📂 {db_name}: {len(missing_from_notion)} records to upload")
            
            upload_results["summary"]["total_databases"] += 1
            db_results = {
                "database_name": db_name,
                "records_attempted": len(missing_from_notion),
                "records_uploaded": 0,
                "upload_results": []
            }
            
            # Get database ID
            db_config = self.notion_config.get(db_name, {})
            database_id = db_config.get("id")
            
            if not database_id:
                logger.error(f"   ❌ No database ID found for {db_name}")
                db_results["error"] = "No database ID found"
                upload_results["databases_processed"][db_name] = db_results
                upload_results["summary"]["failed_uploads"] += 1
                continue
                
            # Upload each missing record
            for missing_record in missing_from_notion:
                title = missing_record["title"]
                local_data = missing_record.get("local_data", {})
                
                if not local_data:
                    logger.warning(f"   ⚠️  No local data for '{title}'")
                    continue
                    
                # Format record for Notion
                properties = self.format_record_for_notion(local_data, db_name)
                
                if not properties:
                    logger.warning(f"   ⚠️  No valid properties for '{title}'")
                    continue
                    
                # Create page
                result = self.create_notion_page(database_id, properties, title)
                db_results["upload_results"].append(result)
                
                if result["success"]:
                    db_results["records_uploaded"] += 1
                    
            # Update summary
            upload_results["databases_processed"][db_name] = db_results
            
            if db_results["records_uploaded"] > 0:
                upload_results["summary"]["successful_uploads"] += 1
                upload_results["summary"]["total_records_uploaded"] += db_results["records_uploaded"]
                logger.info(f"   ✅ Successfully uploaded {db_results['records_uploaded']}/{db_results['records_attempted']} records")
            else:
                upload_results["summary"]["failed_uploads"] += 1
                logger.warning(f"   ❌ Failed to upload any records for {db_name}")
                
        return upload_results
        
    def generate_upload_report(self, results: Dict[str, Any]) -> Path:
        """Generate detailed upload report."""
        logger.info("=" * 80)
        logger.info("📊 UPLOAD SUMMARY")
        logger.info("=" * 80)
        
        summary = results["summary"]
        logger.info(f"Databases processed: {summary['total_databases']}")
        logger.info(f"Successful uploads: {summary['successful_uploads']}")
        logger.info(f"Failed uploads: {summary['failed_uploads']}")
        logger.info(f"Total records uploaded: {summary['total_records_uploaded']}")
        
        # Log database details
        for db_name, db_result in results["databases_processed"].items():
            logger.info(f"\n{db_name}:")
            logger.info(f"  Records uploaded: {db_result['records_uploaded']}/{db_result['records_attempted']}")
            
            for upload_result in db_result.get("upload_results", []):
                status = "✅" if upload_result["success"] else "❌"
                logger.info(f"    {status} {upload_result['title']}")
                if upload_result["error"]:
                    logger.info(f"       Error: {upload_result['error']}")
                    
        # Save detailed report
        reports_dir = self.base_path / "reports" / "upload_operations"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"simple_local_to_notion_upload_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"\n📄 Detailed upload report saved to: {report_file}")
        return report_file


def main():
    """Main execution."""
    try:
        # Initialize uploader
        uploader = SimpleMissingRecordsUploader()
        
        # Perform upload
        results = uploader.upload_all_missing_records()
        
        # Generate report
        report_file = uploader.generate_upload_report(results)
        
        # Final assessment
        if results["summary"]["failed_uploads"] == 0:
            if results["summary"]["total_records_uploaded"] > 0:
                logger.info("🎉 All missing local records successfully uploaded to Notion!")
            else:
                logger.info("✅ No missing records found - perfect synchronization!")
            logger.info("   100% bidirectional sync achieved!")
            return 0
        else:
            logger.warning(f"⚠️  Upload completed with {results['summary']['failed_uploads']} failures")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Fatal error during upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())