#!/usr/bin/env python3
"""
Test Staged Sync - Validates data transformations and runs dry run.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.minimal.staged_json_sync import StagedJSONSyncProcessor
from blackcore.minimal.data_transformer import DataTransformer, load_property_mappings, load_notion_schemas


def test_transformations():
    """Test data transformations on sample records."""
    print("=" * 60)
    print("TESTING DATA TRANSFORMATIONS")
    print("=" * 60)
    
    # Load configurations
    property_mappings = load_property_mappings()
    notion_schemas = load_notion_schemas()
    transformer = DataTransformer(property_mappings, notion_schemas)
    
    # Test cases
    test_cases = [
        {
            "database": "Identified Transgressions",
            "record": {
                "Transgression Summary": "Mid-survey implementation of CAPTCHA",
                "Date of Transgression": "2024-06-26",
                "Severity": "Critical",
                "Perpetrator (Person)": ["Tony Powell"],
                "Perpetrator (Org)": ["Dorset Coast Forum", "Granicus"],
                "Evidence": ["Email from Tony Powell"]
            }
        },
        {
            "database": "Documents & Evidence",
            "record": {
                "Document Name": "Test Document",
                "Document Type": {"select": {"name": "Evidence"}},
                "AI Analysis": {"rich_text": [{"text": {"content": "This is AI analysis"}}]},
                "Source Organization": {"relation": []}
            }
        },
        {
            "database": "Intelligence & Transcripts",
            "record": {
                "Entry Title": "Test Transcript",
                "Date Recorded": "June 2024",
                "Source": "Voice Memo",
                "Raw Transcript/Note": "This is a very long transcript " * 100,  # Test truncation
                "Processing Status": "Needs Processing",
                "Inferred": "Should be removed"
            }
        },
        {
            "database": "Organizations & Bodies",
            "record": {
                "Organization Name": "Test Org",
                "Organization Type": "Public Body",
                "Category": "",  # Should use default
                "Website": "example.com",  # Should add https://
                "Notes": "Should be removed"
            }
        }
    ]
    
    for test in test_cases:
        db_name = test["database"]
        record = test["record"]
        
        print(f"\n📌 Testing {db_name}")
        print(f"Input: {json.dumps(record, indent=2)}")
        
        # Test transformation
        mapping_config = property_mappings.get(db_name, {})
        transformed = transformer.transform_record(record, mapping_config, db_name, stage=1)
        
        print(f"Output: {json.dumps(transformed, indent=2)}")
        
        # Validate transformations
        issues = []
        
        # Check excluded fields are removed
        for field in mapping_config.get('exclude', []):
            if field in transformed:
                issues.append(f"❌ Field '{field}' should have been excluded")
                
        # Check field mappings
        mappings = mapping_config.get('mappings', {})
        for json_field, notion_field in mappings.items():
            if json_field in record and notion_field not in transformed:
                # Check if it's a relation field (excluded in stage 1)
                transform_config = mapping_config.get('transformations', {}).get(notion_field, {})
                if transform_config.get('type') != 'relation':
                    issues.append(f"❌ Field '{json_field}' -> '{notion_field}' missing")
                    
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ Transformation successful")
            

def test_dry_run():
    """Run a dry-run sync to test the full process."""
    print("\n" + "=" * 60)
    print("RUNNING DRY RUN SYNC")
    print("=" * 60)
    
    # Create config for dry run
    config_path = Path(__file__).parent.parent / "sync_config_prod.json"
    
    # Initialize processor
    processor = StagedJSONSyncProcessor(config_path=str(config_path))
    processor.dry_run = True
    processor.verbose = True
    
    # Run staged sync
    print("\nStarting staged sync in dry-run mode...")
    result = processor.sync_all_staged()
    
    # Print results
    print("\n" + "=" * 60)
    print("DRY RUN RESULTS")
    print("=" * 60)
    
    print(f"Success: {result.success}")
    print(f"Total created: {result.created_count}")
    print(f"Total updated: {result.updated_count}")
    print(f"Total skipped: {result.skipped_count}")
    print(f"Total errors: {len(result.errors)}")
    
    # Print stage results
    print("\nStage Results:")
    for stage, stats in result.stage_results.items():
        print(f"  Stage {stage}: Created={stats['created']}, Updated={stats['updated']}, Errors={stats['errors']}")
        
    # Print errors if any
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for i, error in enumerate(result.errors[:10]):
            print(f"  {i+1}. {error}")
        if len(result.errors) > 10:
            print(f"  ... and {len(result.errors) - 10} more")
            
    # Save dry run report
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry_run",
        "success": result.success,
        "total_created": result.created_count,
        "total_updated": result.updated_count,
        "total_skipped": result.skipped_count,
        "total_errors": len(result.errors),
        "stage_results": result.stage_results,
        "errors": result.errors
    }
    
    report_path = Path(__file__).parent.parent / "dry_run_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\nDry run report saved to: {report_path}")
    

def main():
    """Run all tests."""
    print("🧪 Testing Staged Sync Implementation")
    print("=" * 60)
    
    # Test transformations
    test_transformations()
    
    # Test dry run
    test_dry_run()
    
    print("\n✅ Testing complete!")
    

if __name__ == "__main__":
    main()