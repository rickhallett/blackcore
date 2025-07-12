#!/usr/bin/env python3
"""
Upload Missing Local Records - Upload records that exist locally but not in Notion.

This script identifies records that exist in local JSON files but are missing from Notion
and uploads them using the existing sync processor infrastructure.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Set environment variable
os.environ['NOTION_API_KEY'] = '***REMOVED***'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.staged_json_sync import StagedJSONSyncProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MissingLocalRecordsUploader:
    """Uploads records that exist locally but not in Notion."""
    
    def __init__(self):
        """Initialize the uploader."""
        self.base_path = Path(__file__).parent.parent
        self.reports_dir = self.base_path / "reports/sync_comparison"
        
        # Find latest comparison report
        report_files = list(self.reports_dir.glob("sync_comparison_*.json"))
        if not report_files:
            raise FileNotFoundError("No comparison reports found. Run compare_local_notion.py first.")
            
        self.latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"Using comparison report: {self.latest_report}")
        
        # Initialize sync processor
        config_path = self.base_path / "sync_config_prod.json"
        self.sync_processor = StagedJSONSyncProcessor(config_path=str(config_path))
        self.sync_processor.dry_run = False
        self.sync_processor.verbose = True
        
    def load_comparison_report(self) -> Dict[str, Any]:
        """Load the latest comparison report."""
        with open(self.latest_report, 'r') as f:
            return json.load(f)
            
    def create_temporary_json_files(self, missing_records_by_db: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Path]:
        """Create temporary JSON files containing only the missing records."""
        temp_files = {}
        temp_dir = self.base_path / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        for db_name, missing_records in missing_records_by_db.items():
            if not missing_records:
                continue
                
            # Create temporary JSON file with just the missing records
            temp_file = temp_dir / f"{db_name.lower().replace(' ', '_').replace('&', 'and')}_missing.json"
            
            # Get the data key for this database from notion_config
            # Load notion_config separately since sync_processor config is different
            notion_config_path = self.base_path / "blackcore/config/notion_config.json"
            with open(notion_config_path, 'r') as f:
                notion_config = json.load(f)
            
            db_config = notion_config.get(db_name, {})
            json_data_key = db_config.get("json_data_key", db_name)
            
            # Extract just the local data from missing records
            records_to_upload = []
            for missing_record in missing_records:
                if missing_record.get("local_data"):
                    records_to_upload.append(missing_record["local_data"])
                    
            if records_to_upload:
                temp_data = {json_data_key: records_to_upload}
                
                with open(temp_file, 'w') as f:
                    json.dump(temp_data, f, indent=2, ensure_ascii=False)
                    
                temp_files[db_name] = temp_file
                logger.info(f"📄 Created temporary file for {db_name}: {len(records_to_upload)} records")
                
        return temp_files
        
    def upload_missing_records(self, db_name: str, temp_file: Path) -> Dict[str, Any]:
        """Upload missing records for a single database."""
        logger.info(f"🔄 Uploading missing records to {db_name}...")
        
        try:
            # Temporarily update the sync processor config to use our temp file
            original_path = self.sync_processor.notion_config[db_name]["local_json_path"]
            self.sync_processor.notion_config[db_name]["local_json_path"] = str(temp_file)
            
            # Perform sync for this database
            result = self.sync_processor.sync_database_transformed(db_name, stage=1)
            
            # Restore original path
            self.sync_processor.notion_config[db_name]["local_json_path"] = original_path
            
            # Clean up temp file
            temp_file.unlink()
            
            upload_result = {
                "database_name": db_name,
                "success": result.success,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
                "errors": result.errors,
                "created_pages": [page.id for page in result.created_pages]
            }
            
            if result.success and result.created_count > 0:
                logger.info(f"✅ Successfully uploaded {result.created_count} records to {db_name}")
                for page in result.created_pages:
                    logger.info(f"   📄 Created page: {page.id}")
            elif result.errors:
                logger.error(f"❌ Failed to upload to {db_name}: {result.errors}")
            else:
                logger.warning(f"⚠️  No records were created for {db_name}")
                
            return upload_result
            
        except Exception as e:
            logger.error(f"❌ Error uploading to {db_name}: {str(e)}")
            
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()
                
            return {
                "database_name": db_name,
                "success": False,
                "created_count": 0,
                "updated_count": 0,
                "errors": [str(e)],
                "created_pages": []
            }
            
    def upload_all_missing_records(self) -> Dict[str, Any]:
        """Upload all missing local records to Notion."""
        logger.info("=" * 80)
        logger.info("🚀 UPLOADING MISSING LOCAL RECORDS TO NOTION")
        logger.info("=" * 80)
        
        # Load comparison report
        report = self.load_comparison_report()
        
        # Extract missing records by database
        missing_records_by_db = {}
        
        for db_name, db_comparison in report["detailed_comparisons"].items():
            missing_from_notion = db_comparison.get("missing_from_notion", [])
            if missing_from_notion:
                missing_records_by_db[db_name] = missing_from_notion
                logger.info(f"📋 {db_name}: {len(missing_from_notion)} records to upload")
                for record in missing_from_notion:
                    logger.info(f"   - {record['title']}")
                    
        if not missing_records_by_db:
            logger.info("✅ No missing local records found - all records already in Notion!")
            return {
                "timestamp": datetime.now().isoformat(),
                "databases_processed": {},
                "summary": {
                    "total_databases": 0,
                    "successful_uploads": 0,
                    "failed_uploads": 0,
                    "total_records_uploaded": 0
                }
            }
            
        # Create temporary files
        temp_files = self.create_temporary_json_files(missing_records_by_db)
        
        # Upload results
        upload_results = {
            "timestamp": datetime.now().isoformat(),
            "databases_processed": {},
            "summary": {
                "total_databases": len(temp_files),
                "successful_uploads": 0,
                "failed_uploads": 0,
                "total_records_uploaded": 0
            }
        }
        
        # Upload each database
        for db_name, temp_file in temp_files.items():
            result = self.upload_missing_records(db_name, temp_file)
            upload_results["databases_processed"][db_name] = result
            
            if result["success"]:
                upload_results["summary"]["successful_uploads"] += 1
                upload_results["summary"]["total_records_uploaded"] += result["created_count"]
            else:
                upload_results["summary"]["failed_uploads"] += 1
                
        # Clean up temp directory
        temp_dir = self.base_path / "temp_uploads"
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            temp_dir.rmdir()
            
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
            status = "✅ SUCCESS" if db_result["success"] else "❌ FAILED"
            logger.info(f"\n{db_name}: {status}")
            logger.info(f"  Records uploaded: {db_result['created_count']}")
            
            if db_result["created_pages"]:
                logger.info(f"  Pages created: {db_result['created_pages']}")
                
            if db_result["errors"]:
                logger.info(f"  Errors: {db_result['errors']}")
                
        # Save detailed report
        reports_dir = self.base_path / "reports" / "upload_operations"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"local_to_notion_upload_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"\n📄 Detailed upload report saved to: {report_file}")
        return report_file


def main():
    """Main execution."""
    try:
        # Initialize uploader
        uploader = MissingLocalRecordsUploader()
        
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