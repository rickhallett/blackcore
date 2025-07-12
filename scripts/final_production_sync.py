#!/usr/bin/env python3
"""
Final production sync with explicit environment setup and monitoring.
"""

import os
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Set environment variable
os.environ['NOTION_API_KEY'] = '***REMOVED***'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.staged_json_sync import StagedJSONSyncProcessor
from scripts.sync_production import ProductionSyncLogger


def main():
    """Main entry point for final production sync."""
    # Set up paths
    base_path = Path(__file__).parent.parent
    log_dir = base_path / "logs" / "sync"
    config_path = base_path / "sync_config_prod.json"
    
    # Initialize logger
    logger = ProductionSyncLogger(log_dir)
    
    logging.info("=" * 60)
    logging.info("🚀 BLACKCORE FINAL PRODUCTION SYNC TO NOTION")
    logging.info("=" * 60)
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Config: {config_path}")
    logging.info(f"Notion API Key: {os.environ.get('NOTION_API_KEY', 'NOT SET')[:20]}...")
    logging.info("")
    
    try:
        # Initialize sync processor
        logging.info("Initializing staged sync processor...")
        processor = StagedJSONSyncProcessor(config_path=str(config_path))
        
        # Override settings for production
        processor.dry_run = False
        processor.verbose = True
        
        # Log first record to verify property preparation
        logging.info("\nTesting property preparation on first record...")
        test_db = "People & Contacts"
        test_records = processor._load_json_data(processor.notion_config[test_db]["local_json_path"])
        if test_records:
            test_record = test_records[0]
            mapping_config = processor.property_mappings.get(test_db, {})
            transformed = processor.transformer.transform_record(test_record, mapping_config, test_db, stage=1)
            properties = processor._prepare_properties(transformed, processor.notion_config[test_db])
            logging.info(f"Sample record: {list(test_record.keys())}")
            logging.info(f"Prepared properties: {list(properties.keys())}")
            logging.info(f"Sample property format: {json.dumps(list(properties.values())[0] if properties else {}, indent=2)}")
        
        # Perform staged sync
        logging.info("\nStarting staged synchronization...")
        start_time = time.time()
        result = processor.sync_all_staged()
        duration = time.time() - start_time
        
        # Log stage results
        for stage, stats in result.stage_results.items():
            stage_info = {
                "stage": stage,
                "created": stats['created'],
                "updated": stats['updated'],
                "skipped": stats['skipped'],
                "errors": stats['errors']
            }
            logger.sync_results["database_details"][f"Stage {stage}"] = stage_info
            
        # Update totals
        logger.sync_results["total_created"] = result.created_count
        logger.sync_results["total_updated"] = result.updated_count
        logger.sync_results["total_skipped"] = result.skipped_count
        logger.sync_results["total_errors"] = len(result.errors)
        
        # Log created pages
        for page in result.created_pages:
            page_info = {
                "page_id": page.id,
                "database_id": page.database_id,
                "timestamp": datetime.now().isoformat()
            }
            logger.sync_results["created_pages"].append(page_info)
            
        # Log errors
        for error in result.errors:
            error_info = {
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            logger.sync_results["errors"].append(error_info)
            
        # Finalize and save report
        logger.finalize()
        
        # Print summary
        logging.info(f"\n{'='*60}")
        logging.info("📊 FINAL SYNC SUMMARY")
        logging.info(f"{'='*60}")
        logging.info(f"Total pages created: {result.created_count}")
        logging.info(f"Total pages updated: {result.updated_count}")
        logging.info(f"Total errors: {len(result.errors)}")
        logging.info(f"Duration: {duration:.2f} seconds")
        
        # Show successful creations
        if result.created_count > 0:
            logging.info(f"\n✅ Successfully created {result.created_count} pages!")
            
            # Save page ID mappings
            mappings_path = base_path / "page_id_mappings.json"
            with open(mappings_path, 'w') as f:
                json.dump(processor.transformer.page_id_map, f, indent=2)
            logging.info(f"Page ID mappings saved to: {mappings_path}")
            
        # Show errors summary
        if len(result.errors) > 0:
            logging.error(f"\n❌ Encountered {len(result.errors)} errors:")
            # Group errors by type
            error_types = {}
            for error in result.errors:
                error_key = error.split(':')[0]
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error_type, count in error_types.items():
                logging.error(f"  - {error_type}: {count} occurrences")
        
        return 0 if len(result.errors) == 0 else 1
        
    except Exception as e:
        logging.error(f"❌ Fatal error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())