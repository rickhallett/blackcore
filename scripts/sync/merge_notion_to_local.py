#!/usr/bin/env python3
"""
Merge Notion to Local - Add missing Notion records to local JSON files.

This script takes the comparison report and adds all records that exist in Notion
but are missing from local JSON files, achieving better synchronization.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NotionToLocalMerger:
    """Merges missing Notion records into local JSON files."""

    def __init__(self):
        """Initialize the merger."""
        self.base_path = Path(__file__).parent.parent
        self.json_dir = self.base_path / "blackcore/models/json"
        self.reports_dir = self.base_path / "reports/sync_comparison"

        # Find latest comparison report
        report_files = list(self.reports_dir.glob("sync_comparison_*.json"))
        if not report_files:
            raise FileNotFoundError(
                "No comparison reports found. Run compare_local_notion.py first."
            )

        self.latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"Using comparison report: {self.latest_report}")

        # Load configuration
        config_file = self.base_path / "blackcore/config/notion_config.json"
        with open(config_file, "r") as f:
            self.notion_config = json.load(f)

    def load_comparison_report(self) -> Dict[str, Any]:
        """Load the latest comparison report."""
        with open(self.latest_report, "r") as f:
            return json.load(f)

    def backup_local_file(self, db_name: str) -> Path:
        """Create backup of local JSON file before modification."""
        db_config = self.notion_config[db_name]
        local_path = self.base_path / db_config["local_json_path"]

        if not local_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = local_path.with_suffix(f".backup_{timestamp}.json")

        shutil.copy2(local_path, backup_path)
        logger.info(f"   📋 Backed up to: {backup_path}")

        return backup_path

    def clean_notion_record_for_local(
        self, notion_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Clean Notion record for local JSON format."""
        cleaned = {}

        # Skip Notion-specific metadata
        skip_fields = {"notion_page_id", "created_time", "last_edited_time", "url"}

        for key, value in notion_record.items():
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

                # Handle relation fields (keep as-is for now, will handle in sync)
                cleaned[key] = value

        return cleaned

    def merge_database(
        self, db_name: str, missing_records: List[Dict[str, Any]]
    ) -> bool:
        """Merge missing Notion records into local database file."""
        try:
            logger.info(f"🔄 Merging {len(missing_records)} records into {db_name}...")

            # Backup existing file
            backup_path = self.backup_local_file(db_name)

            # Load current local data
            db_config = self.notion_config[db_name]
            local_path = self.base_path / db_config["local_json_path"]
            json_data_key = db_config.get("json_data_key", db_name)

            if local_path.exists():
                with open(local_path, "r") as f:
                    local_data = json.load(f)
            else:
                local_data = {}

            # Ensure the database key exists
            if json_data_key not in local_data:
                local_data[json_data_key] = []

            current_records = local_data[json_data_key]
            initial_count = len(current_records)

            # Clean and add missing records
            added_count = 0
            for missing_record in missing_records:
                notion_data = missing_record["notion_data"]
                cleaned_record = self.clean_notion_record_for_local(notion_data)

                if cleaned_record:  # Only add if there's meaningful data
                    current_records.append(cleaned_record)
                    added_count += 1
                    logger.info(f"   ➕ Added: {missing_record['title']}")

            # Save updated data
            with open(local_path, "w") as f:
                json.dump(local_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Merged {added_count} records into {db_name}")
            logger.info(
                f"   📊 Before: {initial_count} | After: {len(current_records)}"
            )

            return True

        except Exception as e:
            logger.error(f"❌ Failed to merge {db_name}: {str(e)}")

            # Restore backup if it exists
            if backup_path and backup_path.exists():
                local_path = (
                    self.base_path / self.notion_config[db_name]["local_json_path"]
                )
                shutil.copy2(backup_path, local_path)
                logger.info("   🔄 Restored backup")

            return False

    def merge_all_missing_records(self) -> Dict[str, Any]:
        """Merge all missing records from the comparison report."""
        logger.info("=" * 80)
        logger.info("🔄 MERGING MISSING NOTION RECORDS TO LOCAL FILES")
        logger.info("=" * 80)

        # Load comparison report
        report = self.load_comparison_report()

        results = {
            "timestamp": datetime.now().isoformat(),
            "databases_processed": {},
            "summary": {
                "total_databases": 0,
                "successful_merges": 0,
                "failed_merges": 0,
                "total_records_added": 0,
            },
        }

        # Process each database with missing records
        for db_name, db_comparison in report["detailed_comparisons"].items():
            missing_from_local = db_comparison.get("missing_from_local", [])

            if missing_from_local:
                results["summary"]["total_databases"] += 1

                logger.info(
                    f"\n📂 {db_name}: {len(missing_from_local)} missing records"
                )

                # Merge missing records
                success = self.merge_database(db_name, missing_from_local)

                results["databases_processed"][db_name] = {
                    "missing_count": len(missing_from_local),
                    "merge_successful": success,
                    "records_attempted": len(missing_from_local),
                }

                if success:
                    results["summary"]["successful_merges"] += 1
                    results["summary"]["total_records_added"] += len(missing_from_local)
                else:
                    results["summary"]["failed_merges"] += 1

            else:
                logger.info(f"✅ {db_name}: No missing records")

        return results

    def generate_merge_report(self, results: Dict[str, Any]) -> Path:
        """Generate detailed merge report."""
        logger.info("=" * 80)
        logger.info("📊 MERGE SUMMARY")
        logger.info("=" * 80)

        summary = results["summary"]
        logger.info(f"Databases processed: {summary['total_databases']}")
        logger.info(f"Successful merges: {summary['successful_merges']}")
        logger.info(f"Failed merges: {summary['failed_merges']}")
        logger.info(f"Total records added: {summary['total_records_added']}")

        # Log database details
        for db_name, db_result in results["databases_processed"].items():
            status = "✅ SUCCESS" if db_result["merge_successful"] else "❌ FAILED"
            logger.info(f"\n{db_name}: {status}")
            logger.info(f"  Records added: {db_result['records_attempted']}")

        # Save detailed report
        reports_dir = self.base_path / "reports" / "merge_operations"
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"notion_to_local_merge_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"\n📄 Detailed merge report saved to: {report_file}")
        return report_file

    def verify_merge_results(self) -> Dict[str, Any]:
        """Verify the merge by running a quick comparison."""
        logger.info("🔍 Verifying merge results...")

        # Quick count verification
        verification = {}

        for db_name, db_config in self.notion_config.items():
            local_path = self.base_path / db_config["local_json_path"]
            json_data_key = db_config.get("json_data_key", db_name)

            if local_path.exists():
                try:
                    with open(local_path, "r") as f:
                        data = json.load(f)

                    records = data.get(json_data_key, [])
                    verification[db_name] = len(records)

                except Exception as e:
                    logger.error(f"   ❌ Error reading {db_name}: {e}")
                    verification[db_name] = -1
            else:
                verification[db_name] = 0

        # Log verification results
        total_local_after = sum(count for count in verification.values() if count >= 0)
        logger.info(f"📊 Total local records after merge: {total_local_after}")

        return verification


def main():
    """Main execution."""
    try:
        # Initialize merger
        merger = NotionToLocalMerger()

        # Perform merge
        results = merger.merge_all_missing_records()

        # Generate report
        report_file = merger.generate_merge_report(results)

        # Verify results
        verification = merger.verify_merge_results()

        # Final assessment
        if results["summary"]["failed_merges"] == 0:
            logger.info(
                "🎉 All missing Notion records successfully merged to local files!"
            )
            logger.info("   Ready to proceed with bidirectional sync verification.")
            return 0
        else:
            logger.warning(
                f"⚠️  Merge completed with {results['summary']['failed_merges']} failures"
            )
            return 1

    except Exception as e:
        logger.error(f"❌ Fatal error during merge: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
