#!/usr/bin/env python3
"""Convenience script for running transcript library validation tests.

This script specifically runs the structured transcript library tests
with proper cost tracking and validation reporting.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run transcript library tests with proper environment setup."""
    
    # Check if we're in the right directory
    script_dir = Path(__file__).parent
    if not (script_dir / "transcript_library.py").exists():
        print("❌ Error: Run this script from the tests/live/ directory")
        sys.exit(1)
    
    # Check for environment configuration
    env_file = script_dir / ".env"
    env_example = script_dir / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print(f"📝 No .env file found. Consider copying .env.example to .env:")
        print(f"   cp {env_example} {env_file}")
        print(f"   # Then edit .env with your test API keys")
        print()
    
    # Check if live tests are enabled
    if os.getenv("ENABLE_LIVE_AI_TESTS", "false").lower() != "true":
        print("⚠️  Live AI tests are disabled.")
        print("   Set ENABLE_LIVE_AI_TESTS=true to enable them.")
        print("   Example: ENABLE_LIVE_AI_TESTS=true python run_transcript_library_tests.py")
        print()
        
        # Still allow running to see skipped tests
        response = input("Run anyway to see test structure? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            sys.exit(0)
    
    # Check for API key
    if not os.getenv("LIVE_TEST_AI_API_KEY"):
        print("⚠️  No LIVE_TEST_AI_API_KEY found.")
        print("   Add your test API key to environment or .env file")
        print()
    
    # Display current configuration
    print("🔧 Transcript Library Test Configuration:")
    print(f"   AI Tests: {'✅ Enabled' if os.getenv('ENABLE_LIVE_AI_TESTS') == 'true' else '❌ Disabled'}")
    print(f"   Spend Limit: ${os.getenv('LIVE_TEST_SPEND_LIMIT', '10.00')}")
    print(f"   Max AI Calls: {os.getenv('LIVE_TEST_MAX_AI_CALLS', '50')}")
    print(f"   API Key Set: {'✅ Yes' if os.getenv('LIVE_TEST_AI_API_KEY') else '❌ No'}")
    print()
    
    # Show available test options
    print("📚 Available Test Modes:")
    print("   1. Systematic validation (all transcripts individually)")
    print("   2. Comprehensive report (batch analysis)")
    print("   3. Specific transcript tests (original format)")
    print("   4. Consistency testing")
    print("   5. All transcript library tests")
    print()
    
    # Get user choice or use command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = input("Select test mode (1-5, or 'all'): ").strip()
    
    # Build pytest command based on selection
    base_cmd = ["python", "-m", "pytest", str(script_dir), "-v", "-s"]
    
    if mode == "1" or mode == "systematic":
        cmd = base_cmd + ["-k", "test_transcript_library_systematic_validation"]
        print("🚀 Running systematic transcript validation...")
        
    elif mode == "2" or mode == "report":
        cmd = base_cmd + ["-k", "test_transcript_library_comprehensive_report"]
        print("🚀 Running comprehensive validation report...")
        
    elif mode == "3" or mode == "specific":
        cmd = base_cmd + ["-k", "test_simple_meeting_transcript_ai_extraction or test_security_incident_transcript_ai_extraction or test_complex_multi_organization_transcript"]
        print("🚀 Running specific transcript tests...")
        
    elif mode == "4" or mode == "consistency":
        cmd = base_cmd + ["-k", "test_ai_extraction_consistency"]
        print("🚀 Running consistency testing...")
        
    elif mode == "5" or mode == "all" or mode == "":
        cmd = base_cmd + ["-k", "transcript"]
        print("🚀 Running all transcript library tests...")
        
    else:
        print(f"❌ Invalid mode: {mode}")
        print("   Valid options: 1, 2, 3, 4, 5, all, systematic, report, specific, consistency")
        sys.exit(1)
    
    # Add any additional command line arguments
    if len(sys.argv) > 2:
        cmd.extend(sys.argv[2:])
    
    print(f"📋 Command: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        # Run the tests
        result = subprocess.run(cmd, cwd=script_dir.parent.parent.parent)
        
        print("=" * 80)
        if result.returncode == 0:
            print("✅ All transcript library tests completed successfully!")
        else:
            print(f"❌ Some tests failed (exit code: {result.returncode})")
            
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()