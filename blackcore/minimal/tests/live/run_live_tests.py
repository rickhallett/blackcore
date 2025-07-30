#!/usr/bin/env python3
"""Convenience script for running live API integration tests."""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run live tests with proper environment setup."""
    
    # Check if we're in the right directory
    script_dir = Path(__file__).parent
    if not (script_dir / "test_live_ai_extraction.py").exists():
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
        print("   Example: ENABLE_LIVE_AI_TESTS=true python run_live_tests.py")
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
    print("🔧 Live Test Configuration:")
    print(f"   AI Tests: {'✅ Enabled' if os.getenv('ENABLE_LIVE_AI_TESTS') == 'true' else '❌ Disabled'}")
    print(f"   Notion Tests: {'✅ Enabled' if os.getenv('ENABLE_LIVE_NOTION_TESTS') == 'true' else '❌ Disabled'}")
    print(f"   Spend Limit: ${os.getenv('LIVE_TEST_SPEND_LIMIT', '10.00')}")
    print(f"   Max AI Calls: {os.getenv('LIVE_TEST_MAX_AI_CALLS', '50')}")
    print(f"   API Key Set: {'✅ Yes' if os.getenv('LIVE_TEST_AI_API_KEY') else '❌ No'}")
    print()
    
    # Build pytest command
    cmd = ["python", "-m", "pytest", str(script_dir), "-v", "-s"]
    
    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    print(f"🚀 Running: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Run the tests
        result = subprocess.run(cmd, cwd=script_dir.parent.parent.parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()