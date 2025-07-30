#!/usr/bin/env python3
"""
Compare Local vs Notion - Comprehensive gap analysis between local JSON files and Notion databases.

This script performs detailed comparison to identify:
- Records in Notion but not in local files
- Records in local files but not in Notion
- Property differences in existing records
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class RecordComparison:
    """Comparison result for a single record."""

    title: str
    in_local: bool
    in_notion: bool
    local_data: Optional[Dict[str, Any]] = None
    notion_data: Optional[Dict[str, Any]] = None
    property_differences: Optional[Dict[str, Any]] = None


@dataclass
class DatabaseComparison:
    """Comparison result for a database."""

    database_name: str
    local_count: int
    notion_count: int
    missing_from_local: List[RecordComparison]
    missing_from_notion: List[RecordComparison]
    in_both: List[RecordComparison]
    property_mismatches: List[RecordComparison]


class LocalNotionComparator:
    """Compares local JSON files with exported Notion data."""

    def __init__(self):
        """Initialize the comparator."""
        self.base_path = Path(__file__).parent.parent
        self.json_dir = self.base_path / "blackcore/models/json"
        self.export_dir = self.base_path / "exports/complete_notion_export"

        # Load configuration to get title properties
        config_file = self.base_path / "blackcore/config/notion_config.json"
        with open(config_file, "r") as f:
            self.notion_config = json.load(f)

        # Find the latest export
        export_files = list(self.export_dir.glob("complete_export_*.json"))
        if not export_files:
            raise FileNotFoundError("No complete export files found")

        self.latest_export = max(export_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"Using export file: {self.latest_export}")

    def load_local_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load all local JSON files."""
        logger.info("📂 Loading local JSON files...")
        local_data = {}

        for db_name, db_config in self.notion_config.items():
            local_path = self.base_path / db_config["local_json_path"]

            if local_path.exists():
                try:
                    with open(local_path, "r") as f:
                        data = json.load(f)

                    # Extract records for this database
                    json_data_key = db_config.get("json_data_key", db_name)
                    records = data.get(json_data_key, [])
                    local_data[db_name] = records

                    logger.info(f"   {db_name}: {len(records)} records")

                except Exception as e:
                    logger.error(f"   ❌ Failed to load {local_path}: {e}")
                    local_data[db_name] = []
            else:
                logger.warning(f"   ⚠️  Local file not found: {local_path}")
                local_data[db_name] = []

        return local_data

    def load_notion_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load exported Notion data."""
        logger.info("☁️  Loading exported Notion data...")

        with open(self.latest_export, "r") as f:
            export_data = json.load(f)

        notion_data = {}

        for db_name, db_result in export_data["databases"].items():
            if db_result.get("error"):
                logger.error(f"   ❌ {db_name}: {db_result['error']}")
                notion_data[db_name] = []
            else:
                records = db_result.get("records", [])
                notion_data[db_name] = records
                logger.info(f"   {db_name}: {len(records)} records")

        return notion_data

    def get_record_title(
        self, record: Dict[str, Any], db_name: str, is_notion: bool = False
    ) -> str:
        """Extract the title/primary key from a record."""
        # Get title property from config
        title_property = self.notion_config.get(db_name, {}).get(
            "title_property", "Name"
        )

        # Try configured title property first
        if title_property in record:
            title = record[title_property]
            if title:
                return str(title).strip()

        # Fallback strategies
        title_candidates = [
            "Full Name",
            "Name",
            "Organization Name",
            "Agenda Title",
            "Task Name",
            "Document Name",
            "Entry Title",
            "Event / Place Name",
            "Transgression Summary",
            "Request Name",
            "Donation ID",
            "Feature Path",
        ]

        for candidate in title_candidates:
            if candidate in record:
                title = record[candidate]
                if title:
                    return str(title).strip()

        # Last resort: use first non-empty string value
        for key, value in record.items():
            if isinstance(value, str) and value.strip():
                return str(value).strip()

        # If all else fails, use a placeholder
        return f"[No Title - {list(record.keys())[0] if record else 'Empty'}]"

    def compare_database(
        self,
        db_name: str,
        local_records: List[Dict[str, Any]],
        notion_records: List[Dict[str, Any]],
    ) -> DatabaseComparison:
        """Compare local and Notion records for a single database."""
        logger.info(f"🔍 Comparing {db_name}...")

        # Create title-to-record mappings
        local_by_title = {}
        notion_by_title = {}

        for record in local_records:
            title = self.get_record_title(record, db_name, is_notion=False)
            local_by_title[title] = record

        for record in notion_records:
            title = self.get_record_title(record, db_name, is_notion=True)
            notion_by_title[title] = record

        # Find differences
        local_titles = set(local_by_title.keys())
        notion_titles = set(notion_by_title.keys())

        missing_from_local = []
        missing_from_notion = []
        in_both = []
        property_mismatches = []

        # Records in Notion but not local
        for title in notion_titles - local_titles:
            missing_from_local.append(
                RecordComparison(
                    title=title,
                    in_local=False,
                    in_notion=True,
                    notion_data=notion_by_title[title],
                )
            )

        # Records in local but not Notion
        for title in local_titles - notion_titles:
            missing_from_notion.append(
                RecordComparison(
                    title=title,
                    in_local=True,
                    in_notion=False,
                    local_data=local_by_title[title],
                )
            )

        # Records in both - check for property differences
        for title in local_titles & notion_titles:
            local_record = local_by_title[title]
            notion_record = notion_by_title[title]

            # Compare properties (simplified comparison)
            differences = self.compare_record_properties(local_record, notion_record)

            comparison = RecordComparison(
                title=title,
                in_local=True,
                in_notion=True,
                local_data=local_record,
                notion_data=notion_record,
                property_differences=differences,
            )

            if differences:
                property_mismatches.append(comparison)
            else:
                in_both.append(comparison)

        return DatabaseComparison(
            database_name=db_name,
            local_count=len(local_records),
            notion_count=len(notion_records),
            missing_from_local=missing_from_local,
            missing_from_notion=missing_from_notion,
            in_both=in_both,
            property_mismatches=property_mismatches,
        )

    def compare_record_properties(
        self, local_record: Dict[str, Any], notion_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare properties between local and Notion records."""
        differences = {}

        # Skip Notion-specific fields in comparison
        notion_skip = {"notion_page_id", "created_time", "last_edited_time", "url"}

        # Get all unique keys
        local_keys = set(local_record.keys())
        notion_keys = set(k for k in notion_record.keys() if k not in notion_skip)
        all_keys = local_keys | notion_keys

        for key in all_keys:
            local_val = local_record.get(key)
            notion_val = notion_record.get(key)

            # Normalize None/empty values
            local_val = None if local_val in [None, "", []] else local_val
            notion_val = None if notion_val in [None, "", []] else notion_val

            if local_val != notion_val:
                differences[key] = {"local": local_val, "notion": notion_val}

        return differences

    def compare_all_databases(self) -> Dict[str, DatabaseComparison]:
        """Compare all databases."""
        logger.info("=" * 80)
        logger.info("🔍 STARTING COMPREHENSIVE LOCAL vs NOTION COMPARISON")
        logger.info("=" * 80)

        # Load data
        local_data = self.load_local_data()
        notion_data = self.load_notion_data()

        # Compare each database
        comparisons = {}

        all_databases = set(local_data.keys()) | set(notion_data.keys())

        for db_name in sorted(all_databases):
            local_records = local_data.get(db_name, [])
            notion_records = notion_data.get(db_name, [])

            comparison = self.compare_database(db_name, local_records, notion_records)
            comparisons[db_name] = comparison

        return comparisons

    def generate_summary_report(
        self, comparisons: Dict[str, DatabaseComparison]
    ) -> Dict[str, Any]:
        """Generate summary report of all comparisons."""
        logger.info("=" * 80)
        logger.info("📊 COMPARISON SUMMARY REPORT")
        logger.info("=" * 80)

        total_local = 0
        total_notion = 0
        total_missing_from_local = 0
        total_missing_from_notion = 0
        total_in_both = 0
        total_property_mismatches = 0

        for db_name, comp in comparisons.items():
            total_local += comp.local_count
            total_notion += comp.notion_count
            total_missing_from_local += len(comp.missing_from_local)
            total_missing_from_notion += len(comp.missing_from_notion)
            total_in_both += len(comp.in_both)
            total_property_mismatches += len(comp.property_mismatches)

            logger.info(f"\n{db_name}:")
            logger.info(f"  Local: {comp.local_count} | Notion: {comp.notion_count}")
            logger.info(f"  Missing from Local: {len(comp.missing_from_local)}")
            logger.info(f"  Missing from Notion: {len(comp.missing_from_notion)}")
            logger.info(f"  In Both: {len(comp.in_both)}")
            logger.info(f"  Property Mismatches: {len(comp.property_mismatches)}")

            # Show some examples of missing records
            if comp.missing_from_local:
                examples = [r.title for r in comp.missing_from_local[:3]]
                logger.info(f"    Missing from Local examples: {examples}")

            if comp.missing_from_notion:
                examples = [r.title for r in comp.missing_from_notion[:3]]
                logger.info(f"    Missing from Notion examples: {examples}")

        logger.info("=" * 80)
        logger.info("📈 TOTALS:")
        logger.info(f"  Total Local Records: {total_local}")
        logger.info(f"  Total Notion Records: {total_notion}")
        logger.info(f"  Total Missing from Local: {total_missing_from_local}")
        logger.info(f"  Total Missing from Notion: {total_missing_from_notion}")
        logger.info(f"  Total In Both: {total_in_both}")
        logger.info(f"  Total Property Mismatches: {total_property_mismatches}")

        sync_percentage = (total_in_both / max(total_local, total_notion, 1)) * 100
        logger.info(f"  Sync Percentage: {sync_percentage:.1f}%")

        return {
            "timestamp": datetime.now().isoformat(),
            "totals": {
                "local_records": total_local,
                "notion_records": total_notion,
                "missing_from_local": total_missing_from_local,
                "missing_from_notion": total_missing_from_notion,
                "in_both": total_in_both,
                "property_mismatches": total_property_mismatches,
                "sync_percentage": sync_percentage,
            },
            "databases": {
                db_name: {
                    "local_count": comp.local_count,
                    "notion_count": comp.notion_count,
                    "missing_from_local": len(comp.missing_from_local),
                    "missing_from_notion": len(comp.missing_from_notion),
                    "in_both": len(comp.in_both),
                    "property_mismatches": len(comp.property_mismatches),
                }
                for db_name, comp in comparisons.items()
            },
        }

    def save_detailed_report(
        self, comparisons: Dict[str, DatabaseComparison], summary: Dict[str, Any]
    ) -> Path:
        """Save detailed comparison report."""
        reports_dir = self.base_path / "reports" / "sync_comparison"
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"sync_comparison_{timestamp}.json"

        # Convert comparisons to serializable format
        detailed_report = {"summary": summary, "detailed_comparisons": {}}

        for db_name, comp in comparisons.items():
            detailed_report["detailed_comparisons"][db_name] = {
                "database_name": comp.database_name,
                "local_count": comp.local_count,
                "notion_count": comp.notion_count,
                "missing_from_local": [
                    {"title": r.title, "notion_data": r.notion_data}
                    for r in comp.missing_from_local
                ],
                "missing_from_notion": [
                    {"title": r.title, "local_data": r.local_data}
                    for r in comp.missing_from_notion
                ],
                "property_mismatches": [
                    {"title": r.title, "differences": r.property_differences}
                    for r in comp.property_mismatches
                ],
            }

        with open(report_file, "w") as f:
            json.dump(detailed_report, f, indent=2, default=str)

        logger.info(f"📄 Detailed report saved to: {report_file}")
        return report_file


def main():
    """Main execution."""
    try:
        # Initialize comparator
        comparator = LocalNotionComparator()

        # Perform comparison
        comparisons = comparator.compare_all_databases()

        # Generate summary
        summary = comparator.generate_summary_report(comparisons)

        # Save detailed report
        report_file = comparator.save_detailed_report(comparisons, summary)

        # Final assessment
        total_gaps = (
            summary["totals"]["missing_from_local"]
            + summary["totals"]["missing_from_notion"]
        )

        if total_gaps == 0:
            logger.info("🎉 Perfect synchronization achieved!")
            return 0
        else:
            logger.info(
                f"⚠️  Found {total_gaps} synchronization gaps that need attention"
            )
            return 1

    except Exception as e:
        logger.error(f"❌ Fatal error during comparison: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
