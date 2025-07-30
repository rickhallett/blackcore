#!/usr/bin/env python3
"""
Test script for the Deduplication CLI.

Verifies that all components are properly integrated and working.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.cli import (
    StandardModeCLI,
    UIComponents,
    ConfigurationWizard,
    AsyncDeduplicationEngine
)


async def test_components():
    """Test individual CLI components."""
    print("Testing Deduplication CLI Components...\n")
    
    # Test 1: UI Components
    print("1. Testing UI Components...")
    try:
        ui = UIComponents()
        
        # Test welcome panel
        welcome = ui.create_welcome_panel()
        print("   ✓ Welcome panel created")
        
        # Test main menu
        menu = ui.create_main_menu()
        print("   ✓ Main menu created")
        
        # Test database selection table
        test_dbs = {
            "People & Contacts": {"record_count": 100, "selected": True},
            "Organizations": {"record_count": 50, "selected": False}
        }
        table = ui.create_database_selection_table(test_dbs)
        print("   ✓ Database selection table created")
        
        # Test threshold panel
        threshold_panel = ui.create_threshold_config_panel(90, 70)
        print("   ✓ Threshold configuration panel created")
        
    except Exception as e:
        print(f"   ✗ UI Components test failed: {e}")
        return False
        
    # Test 2: Configuration Wizard
    print("\n2. Testing Configuration Wizard...")
    try:
        wizard = ConfigurationWizard()
        
        # Test default config
        config = wizard._load_default_config()
        assert "thresholds" in config
        assert "ai" in config
        assert "processing" in config
        print("   ✓ Default configuration loaded")
        
        # Test quick config
        quick_config = wizard.quick_config()
        assert quick_config["thresholds"]["auto_merge"] == 90.0
        print("   ✓ Quick configuration works")
        
    except Exception as e:
        print(f"   ✗ Configuration Wizard test failed: {e}")
        return False
        
    # Test 3: Async Engine
    print("\n3. Testing Async Engine...")
    try:
        engine = AsyncDeduplicationEngine()
        
        # Test configuration update
        engine.update_config({"auto_merge_threshold": 95.0})
        print("   ✓ Configuration update works")
        
        # Test statistics
        stats = engine.get_statistics()
        assert isinstance(stats, dict)
        print("   ✓ Statistics retrieval works")
        
        # Cleanup
        await engine.shutdown()
        print("   ✓ Engine shutdown works")
        
    except Exception as e:
        print(f"   ✗ Async Engine test failed: {e}")
        return False
        
    # Test 4: Main CLI Integration
    print("\n4. Testing Main CLI Integration...")
    try:
        cli = StandardModeCLI()
        
        # Test initialization
        assert cli.console is not None
        assert cli.ui is not None
        assert cli.config_wizard is not None
        print("   ✓ CLI initialization successful")
        
        # Test database loading
        databases = await cli._load_databases()
        print(f"   ✓ Found {len(databases)} databases")
        
    except Exception as e:
        print(f"   ✗ Main CLI test failed: {e}")
        return False
        
    print("\n✅ All tests passed!")
    return True


async def test_minimal_workflow():
    """Test a minimal workflow without user interaction."""
    print("\n\nTesting Minimal Workflow...\n")
    
    try:
        # Create test data
        test_data = {
            "Test Database": [
                {"id": "1", "Full Name": "John Smith", "Email": "john@example.com"},
                {"id": "2", "Full Name": "J Smith", "Email": "john@example.com"},
                {"id": "3", "Full Name": "Jane Doe", "Email": "jane@example.com"}
            ]
        }
        
        # Initialize engine
        config = {
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "enable_ai_analysis": False,  # Disable AI for testing
            "safety_mode": True
        }
        
        engine = AsyncDeduplicationEngine(config)
        
        print("1. Analyzing test data...")
        
        # Simple progress callback
        async def progress_callback(update):
            print(f"   {update.stage}: {update.current}/{update.total}")
            
        # Run analysis
        results = await engine.analyze_databases_async(
            test_data,
            progress_callback=progress_callback
        )
        
        print("\n2. Analysis Results:")
        for db_name, result in results.items():
            print(f"   Database: {db_name}")
            print(f"   Total entities: {result.total_entities}")
            print(f"   Potential duplicates: {result.potential_duplicates}")
            print(f"   High confidence matches: {len(result.high_confidence_matches)}")
            
        await engine.shutdown()
        print("\n✅ Workflow test completed!")
        
    except Exception as e:
        print(f"\n✗ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Deduplication CLI Test Suite")
    print("=" * 60)
    
    # Run component tests
    components_ok = await test_components()
    
    # Run workflow test
    workflow_ok = await test_minimal_workflow()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Components: {'✅ PASS' if components_ok else '❌ FAIL'}")
    print(f"  Workflow: {'✅ PASS' if workflow_ok else '❌ FAIL'}")
    print("=" * 60)
    
    return 0 if (components_ok and workflow_ok) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))