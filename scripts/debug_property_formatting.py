#!/usr/bin/env python3
"""
Debug Property Formatting - Comprehensive debugging of the property formatting pipeline.

This script compares the working test script format with the sync processor format
to identify exactly where the property formatting fails.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

# Set environment variable
os.environ['NOTION_API_KEY'] = '***REMOVED***'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.staged_json_sync import StagedJSONSyncProcessor
from blackcore.minimal.data_transformer import DataTransformer, load_property_mappings, load_notion_schemas
from blackcore.minimal.notion_schema_inspector import NotionSchemaInspector
from notion_client import Client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PropertyDebugInfo:
    """Debug information for a single property."""
    original_value: Any
    transformed_value: Any
    formatted_value: Any
    expected_type: str
    actual_format: Dict[str, Any]


class PropertyFormattingDebugger:
    """Debug the property formatting pipeline step by step."""
    
    def __init__(self):
        """Initialize the debugger."""
        self.base_path = Path(__file__).parent.parent
        self.config_path = self.base_path / "sync_config_prod.json"
        
        # Initialize components
        self.processor = StagedJSONSyncProcessor(config_path=str(self.config_path))
        self.notion_client = Client(auth=os.environ['NOTION_API_KEY'])
        
        # Set up for debugging
        self.processor.dry_run = True
        self.processor.verbose = True
        
    def debug_all_databases(self) -> Dict[str, Dict[str, Any]]:
        """Debug property formatting for all databases."""
        logger.info("=" * 80)
        logger.info("🔍 DEBUGGING PROPERTY FORMATTING PIPELINE")
        logger.info("=" * 80)
        
        debug_results = {}
        
        # Get databases to test
        test_databases = [
            "People & Contacts",
            "Organizations & Bodies", 
            "Intelligence & Transcripts",
            "Identified Transgressions"
        ]
        
        for db_name in test_databases:
            if db_name in self.processor.notion_config:
                logger.info(f"\n{'='*60}")
                logger.info(f"🔍 DEBUGGING: {db_name}")
                logger.info(f"{'='*60}")
                
                debug_results[db_name] = self.debug_database(db_name)
                
        return debug_results
        
    def debug_database(self, database_name: str) -> Dict[str, Any]:
        """Debug property formatting for a single database."""
        db_config = self.processor.notion_config[database_name]
        database_id = db_config["id"]
        json_path = db_config["local_json_path"]
        
        logger.info(f"📂 Database: {database_name}")
        logger.info(f"📄 JSON Path: {json_path}")
        logger.info(f"🔑 Database ID: {database_id}")
        
        # Load one record
        records = self.processor._load_json_data(json_path)
        if not records:
            logger.warning(f"⚠️  No records found in {json_path}")
            return {"error": "No records found"}
            
        test_record = records[0]
        logger.info(f"📋 Testing with record: {list(test_record.keys())}")
        
        debug_info = {
            "original_record": test_record,
            "steps": {},
            "final_comparison": {}
        }
        
        # Step 1: Show original record
        logger.info(f"\n🔸 STEP 1: Original Record")
        self._log_record_structure(test_record, "Original")
        debug_info["steps"]["1_original"] = test_record
        
        # Step 2: Apply transformations
        logger.info(f"\n🔸 STEP 2: Data Transformation")
        mapping_config = self.processor.property_mappings.get(database_name, {})
        transformed_record = self.processor.transformer.transform_record(
            test_record, mapping_config, database_name, stage=1
        )
        self._log_record_structure(transformed_record, "Transformed")
        debug_info["steps"]["2_transformed"] = transformed_record
        
        # Step 3: Prepare properties (sync processor way)
        logger.info(f"\n🔸 STEP 3: Sync Processor Property Preparation")
        sync_properties = self.processor._prepare_properties(transformed_record, db_config)
        self._log_properties_format(sync_properties, "Sync Processor")
        debug_info["steps"]["3_sync_properties"] = sync_properties
        
        # Step 4: Manual property preparation (test script way)
        logger.info(f"\n🔸 STEP 4: Manual Property Preparation (Test Script Style)")
        manual_properties = self._prepare_properties_manual(transformed_record, database_name)
        self._log_properties_format(manual_properties, "Manual/Test Script")
        debug_info["steps"]["4_manual_properties"] = manual_properties
        
        # Step 5: Compare formats
        logger.info(f"\n🔸 STEP 5: Format Comparison")
        comparison = self._compare_property_formats(sync_properties, manual_properties)
        self._log_comparison(comparison)
        debug_info["final_comparison"] = comparison
        
        # Step 6: Test API calls
        logger.info(f"\n🔸 STEP 6: API Call Testing")
        api_results = self._test_api_calls(database_id, sync_properties, manual_properties)
        debug_info["api_test_results"] = api_results
        
        return debug_info
        
    def _log_record_structure(self, record: Dict[str, Any], label: str):
        """Log the structure of a record."""
        logger.info(f"  {label} Record Structure:")
        for key, value in record.items():
            value_type = type(value).__name__
            if isinstance(value, str):
                preview = value[:50] + "..." if len(value) > 50 else value
                logger.info(f"    {key}: {value_type} = '{preview}'")
            elif isinstance(value, list):
                logger.info(f"    {key}: {value_type}[{len(value)}] = {value[:2] if len(value) > 2 else value}")
            else:
                logger.info(f"    {key}: {value_type} = {value}")
                
    def _log_properties_format(self, properties: Dict[str, Any], label: str):
        """Log the format of prepared properties."""
        logger.info(f"  {label} Properties ({len(properties)} fields):")
        for key, value in properties.items():
            logger.info(f"    {key}: {json.dumps(value, indent=6)}")
            
    def _prepare_properties_manual(self, record: Dict[str, Any], database_name: str) -> Dict[str, Any]:
        """Manually prepare properties like the test script does."""
        properties = {}
        
        # Simple manual mapping based on common patterns
        for key, value in record.items():
            if not value or value == "":
                continue
                
            # Determine property type by name patterns
            if "name" in key.lower() or "title" in key.lower() or key == "Full Name":
                properties[key] = {
                    "title": [{"text": {"content": str(value)}}]
                }
            elif "date" in key.lower():
                properties[key] = {
                    "date": {"start": str(value)}
                }
            elif "status" in key.lower() and database_name in ["People & Contacts"]:
                properties[key] = {
                    "select": {"name": str(value)}
                }
            elif key in ["Role", "Severity", "Source", "Processing Status", "Category"]:
                properties[key] = {
                    "select": {"name": str(value)}
                }
            elif key in ["Notes", "Description", "Raw Transcript/Note", "Details"]:
                properties[key] = {
                    "rich_text": [{"text": {"content": str(value)}}]
                }
            else:
                # Default to rich text
                properties[key] = {
                    "rich_text": [{"text": {"content": str(value)}}]
                }
                
        return properties
        
    def _compare_property_formats(self, sync_props: Dict[str, Any], manual_props: Dict[str, Any]) -> Dict[str, Any]:
        """Compare the two property formatting approaches."""
        comparison = {
            "sync_only": [],
            "manual_only": [],
            "different_format": [],
            "identical": []
        }
        
        all_keys = set(sync_props.keys()) | set(manual_props.keys())
        
        for key in all_keys:
            if key in sync_props and key not in manual_props:
                comparison["sync_only"].append(key)
            elif key in manual_props and key not in sync_props:
                comparison["manual_only"].append(key)
            elif key in sync_props and key in manual_props:
                sync_val = sync_props[key]
                manual_val = manual_props[key]
                
                if sync_val == manual_val:
                    comparison["identical"].append(key)
                else:
                    comparison["different_format"].append({
                        "key": key,
                        "sync": sync_val,
                        "manual": manual_val
                    })
                    
        return comparison
        
    def _log_comparison(self, comparison: Dict[str, Any]):
        """Log the comparison results."""
        logger.info("  🔍 Property Format Comparison:")
        
        if comparison["identical"]:
            logger.info(f"    ✅ Identical ({len(comparison['identical'])}): {comparison['identical']}")
            
        if comparison["sync_only"]:
            logger.info(f"    📤 Sync Only ({len(comparison['sync_only'])}): {comparison['sync_only']}")
            
        if comparison["manual_only"]:
            logger.info(f"    📥 Manual Only ({len(comparison['manual_only'])}): {comparison['manual_only']}")
            
        if comparison["different_format"]:
            logger.info(f"    ⚠️  Different Format ({len(comparison['different_format'])}):")
            for diff in comparison["different_format"]:
                logger.info(f"      {diff['key']}:")
                logger.info(f"        Sync: {json.dumps(diff['sync'])}")
                logger.info(f"        Manual: {json.dumps(diff['manual'])}")
                
    def _test_api_calls(self, database_id: str, sync_props: Dict[str, Any], manual_props: Dict[str, Any]) -> Dict[str, Any]:
        """Test actual API calls with both property formats."""
        results = {
            "sync_format": {"success": False, "error": None},
            "manual_format": {"success": False, "error": None}
        }
        
        # Test sync processor format
        logger.info("  🔸 Testing Sync Processor Format:")
        try:
            response = self.notion_client.pages.create(
                parent={"database_id": database_id},
                properties=sync_props
            )
            results["sync_format"]["success"] = True
            results["sync_format"]["page_id"] = response["id"]
            logger.info(f"    ✅ SUCCESS: Created page {response['id']}")
        except Exception as e:
            results["sync_format"]["error"] = str(e)
            logger.error(f"    ❌ FAILED: {str(e)}")
            
        # Test manual format
        logger.info("  🔸 Testing Manual Format:")
        try:
            response = self.notion_client.pages.create(
                parent={"database_id": database_id},
                properties=manual_props
            )
            results["manual_format"]["success"] = True
            results["manual_format"]["page_id"] = response["id"]
            logger.info(f"    ✅ SUCCESS: Created page {response['id']}")
        except Exception as e:
            results["manual_format"]["error"] = str(e)
            logger.error(f"    ❌ FAILED: {str(e)}")
            
        return results
        
    def save_debug_report(self, debug_results: Dict[str, Any]):
        """Save comprehensive debug report."""
        report_path = self.base_path / "logs" / "property_formatting_debug_report.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(debug_results, f, indent=2, default=str)
            
        logger.info(f"\n📋 Debug report saved to: {report_path}")


def main():
    """Main entry point for property formatting debugger."""
    debugger = PropertyFormattingDebugger()
    
    try:
        # Run debugging
        debug_results = debugger.debug_all_databases()
        
        # Save report
        debugger.save_debug_report(debug_results)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 DEBUG SUMMARY")
        logger.info("=" * 80)
        
        for db_name, results in debug_results.items():
            if "api_test_results" in results:
                api_results = results["api_test_results"]
                sync_success = api_results["sync_format"]["success"]
                manual_success = api_results["manual_format"]["success"]
                
                logger.info(f"\n{db_name}:")
                logger.info(f"  Sync Format:   {'✅ SUCCESS' if sync_success else '❌ FAILED'}")
                logger.info(f"  Manual Format: {'✅ SUCCESS' if manual_success else '❌ FAILED'}")
                
                if not sync_success:
                    logger.info(f"  Sync Error: {api_results['sync_format']['error']}")
                if not manual_success:
                    logger.info(f"  Manual Error: {api_results['manual_format']['error']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Fatal error in debugger: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())