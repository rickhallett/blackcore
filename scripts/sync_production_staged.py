#!/usr/bin/env python3
"""
Production Staged Sync Script for Blackcore JSON to Notion sync.
Uses the enhanced staged sync processor with data transformations.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.staged_json_sync import StagedJSONSyncProcessor
from scripts.sync_production import ProductionSyncLogger


def main():
    """Main entry point for production staged sync."""
    # Set up paths
    base_path = Path(__file__).parent.parent
    log_dir = base_path / "logs" / "sync"
    config_path = base_path / "sync_config_prod.json"

    # Initialize logger
    logger = ProductionSyncLogger(log_dir)

    logging.info("=" * 60)
    logging.info("🚀 BLACKCORE STAGED PRODUCTION SYNC TO NOTION")
    logging.info("=" * 60)
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Config: {config_path}")
    logging.info("")

    try:
        # Initialize sync processor
        logging.info("Initializing staged sync processor...")
        processor = StagedJSONSyncProcessor(config_path=str(config_path))

        # Override settings for production
        processor.dry_run = False
        processor.verbose = True

        # Perform staged sync
        logging.info("Starting staged synchronization...")
        start_time = time.time()
        result = processor.sync_all_staged()
        duration = time.time() - start_time

        # Log stage results
        for stage, stats in result.stage_results.items():
            stage_info = {
                "stage": stage,
                "created": stats["created"],
                "updated": stats["updated"],
                "skipped": stats["skipped"],
                "errors": stats["errors"],
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
                "timestamp": datetime.now().isoformat(),
            }
            logger.sync_results["created_pages"].append(page_info)

        # Log updated pages
        for page in result.updated_pages:
            page_info = {
                "page_id": page.id,
                "database_id": page.database_id,
                "timestamp": datetime.now().isoformat(),
            }
            logger.sync_results["updated_pages"].append(page_info)

        # Log errors
        for error in result.errors:
            error_info = {"error": error, "timestamp": datetime.now().isoformat()}
            logger.sync_results["errors"].append(error_info)

        # Finalize and save report
        logger.finalize()

        # Print summary
        logging.info(f"\n{'='*60}")
        logging.info("📊 STAGED SYNC SUMMARY")
        logging.info(f"{'='*60}")
        logging.info(
            f"Total databases processed: {len(processor.STAGE_1_DATABASES + processor.STAGE_2_DATABASES)}"
        )
        logging.info(f"Total pages created: {result.created_count}")
        logging.info(f"Total pages updated: {result.updated_count}")
        logging.info(f"Total pages skipped: {result.skipped_count}")
        logging.info(f"Total errors: {len(result.errors)}")
        logging.info(f"Duration: {duration:.2f} seconds")

        # Print stage breakdown
        logging.info("\nStage Breakdown:")
        for stage, stats in result.stage_results.items():
            logging.info(
                f"  Stage {stage}: Created={stats['created']}, Updated={stats['updated']}, Errors={stats['errors']}"
            )

        logging.info(f"{'='*60}")

        # Print success message if no errors
        if len(result.errors) == 0:
            logging.info("\n✅ ALL DATA SUCCESSFULLY SYNCED TO NOTION!")

            # Save page ID mappings for future reference
            mappings_path = base_path / "page_id_mappings.json"
            with open(mappings_path, "w") as f:
                json.dump(processor.transformer.page_id_map, f, indent=2)
            logging.info(f"\nPage ID mappings saved to: {mappings_path}")
        else:
            logging.error(f"\n❌ Sync completed with {len(result.errors)} errors")
            for i, error in enumerate(result.errors[:10]):
                logging.error(f"  {i+1}. {error}")
            if len(result.errors) > 10:
                logging.error(f"  ... and {len(result.errors) - 10} more")

        # Return success/failure
        return 0 if len(result.errors) == 0 else 1

    except Exception as e:
        logging.error(f"❌ Fatal error: {str(e)}")
        import traceback

        logging.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
