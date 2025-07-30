#!/usr/bin/env python3
"""
Production sync script for Blackcore JSON to Notion sync.
Provides comprehensive logging and error handling for production runs.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.json_sync import JSONSyncProcessor


class ProductionSyncLogger:
    """Enhanced logging for production sync operations."""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up file logging
        self.log_file = self.log_dir / f"sync_{self.timestamp}.log"
        self.report_file = self.log_dir / f"sync_report_{self.timestamp}.json"
        
        # Configure logging
        self._setup_logging()
        
        # Track sync results
        self.sync_results = {
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "databases_synced": [],
            "total_created": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "created_pages": [],
            "updated_pages": [],
            "errors": [],
            "database_details": {}
        }
        
    def _setup_logging(self):
        """Configure logging to both file and console."""
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter('%(message)s')
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    def log_database_sync(self, db_name: str, result: Any):
        """Log results from syncing a specific database."""
        db_details = {
            "name": db_name,
            "created": result.created_count,
            "updated": result.updated_count,
            "skipped": result.skipped_count,
            "errors": len(result.errors),
            "success": result.success,
            "created_page_ids": [page.id for page in result.created_pages],
            "updated_page_ids": [page.id for page in result.updated_pages],
            "error_messages": result.errors
        }
        
        self.sync_results["database_details"][db_name] = db_details
        self.sync_results["databases_synced"].append(db_name)
        
        # Update totals
        self.sync_results["total_created"] += result.created_count
        self.sync_results["total_updated"] += result.updated_count
        self.sync_results["total_skipped"] += result.skipped_count
        self.sync_results["total_errors"] += len(result.errors)
        
        # Log created pages with details
        for page in result.created_pages:
            page_info = {
                "database": db_name,
                "page_id": page.id,
                "database_id": page.database_id,
                "timestamp": datetime.now().isoformat()
            }
            self.sync_results["created_pages"].append(page_info)
            logging.info(f"✅ Created page in {db_name}: {page.id}")
            
        # Log updated pages
        for page in result.updated_pages:
            page_info = {
                "database": db_name,
                "page_id": page.id,
                "database_id": page.database_id,
                "timestamp": datetime.now().isoformat()
            }
            self.sync_results["updated_pages"].append(page_info)
            logging.info(f"📝 Updated page in {db_name}: {page.id}")
            
        # Log errors
        for error in result.errors:
            error_info = {
                "database": db_name,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            self.sync_results["errors"].append(error_info)
            logging.error(f"❌ Error in {db_name}: {error}")
            
    def finalize(self):
        """Finalize logging and save report."""
        self.sync_results["end_time"] = datetime.now().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(self.sync_results["start_time"])
        end = datetime.fromisoformat(self.sync_results["end_time"])
        self.sync_results["duration_seconds"] = (end - start).total_seconds()
        
        # Save JSON report
        with open(self.report_file, 'w') as f:
            json.dump(self.sync_results, f, indent=2)
            
        logging.info(f"\n📄 Detailed report saved to: {self.report_file}")
        logging.info(f"📋 Full log saved to: {self.log_file}")


def main():
    """Main entry point for production sync."""
    # Set up paths
    base_path = Path(__file__).parent.parent
    log_dir = base_path / "logs" / "sync"
    config_path = base_path / "sync_config_prod.json"
    
    # Initialize logger
    logger = ProductionSyncLogger(log_dir)
    
    logging.info("=" * 60)
    logging.info("🚀 BLACKCORE PRODUCTION SYNC TO NOTION")
    logging.info("=" * 60)
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Config: {config_path}")
    logging.info("")
    
    try:
        # Initialize sync processor
        logging.info("Initializing sync processor...")
        processor = JSONSyncProcessor(config_path=str(config_path))
        
        # Override settings from config
        processor.dry_run = False
        processor.verbose = True
        
        # Get list of databases
        databases = list(processor.notion_config.keys())
        logging.info(f"Found {len(databases)} databases in notion_config.json")
        logging.info("")
        
        # Sync each database individually for better tracking
        for db_name in databases:
            # Skip system databases
            if db_name in ["API Control Panel USER GEN", "Leads", "NSTCG Gamification Profiles", 
                          "Donations", "NSTCG Feature Flags"]:
                logging.info(f"⏭️  Skipping system database: {db_name}")
                continue
                
            # Check if JSON file exists
            db_config = processor.notion_config[db_name]
            json_path = Path(db_config["local_json_path"])
            
            if not json_path.exists() and not (Path("..") / ".." / json_path).exists():
                logging.warning(f"⚠️  Skipping {db_name} - JSON file not found: {json_path}")
                continue
                
            logging.info(f"\n{'='*50}")
            logging.info(f"📂 Syncing: {db_name}")
            logging.info(f"{'='*50}")
            
            try:
                # Perform sync
                start_time = time.time()
                result = processor.sync_database(db_name)
                duration = time.time() - start_time
                
                # Log results
                logger.log_database_sync(db_name, result)
                
                logging.info(f"⏱️  Sync completed in {duration:.2f} seconds")
                logging.info(f"   Created: {result.created_count}")
                logging.info(f"   Updated: {result.updated_count}")
                logging.info(f"   Skipped: {result.skipped_count}")
                if result.errors:
                    logging.info(f"   Errors: {len(result.errors)}")
                    
            except Exception as e:
                logging.error(f"❌ Failed to sync {db_name}: {str(e)}")
                logger.sync_results["errors"].append({
                    "database": db_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
        # Finalize and save report
        logger.finalize()
        
        # Print summary
        logging.info(f"\n{'='*60}")
        logging.info("📊 SYNC SUMMARY")
        logging.info(f"{'='*60}")
        logging.info(f"Total databases processed: {len(logger.sync_results['databases_synced'])}")
        logging.info(f"Total pages created: {logger.sync_results['total_created']}")
        logging.info(f"Total pages updated: {logger.sync_results['total_updated']}")
        logging.info(f"Total pages skipped: {logger.sync_results['total_skipped']}")
        logging.info(f"Total errors: {logger.sync_results['total_errors']}")
        logging.info(f"Duration: {logger.sync_results['duration_seconds']:.2f} seconds")
        logging.info(f"{'='*60}")
        
        # Return success/failure
        return 0 if logger.sync_results['total_errors'] == 0 else 1
        
    except Exception as e:
        logging.error(f"❌ Fatal error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())