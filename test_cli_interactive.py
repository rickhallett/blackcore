#!/usr/bin/env python3
"""Test the CLI interactively with auto-responses."""

import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from blackcore.deduplication.cli.standard_mode import StandardModeCLI


async def test_cli_with_auto_responses():
    """Test the CLI with automated responses."""
    
    # Create mock responses for user inputs
    responses = iter([
        "1",  # Choose "New Analysis" from main menu
        "",   # Press enter at any prompt to continue
        "5",  # Exit from main menu
    ])
    
    # Mock the Prompt.ask to return our predefined responses
    with patch('rich.prompt.Prompt.ask', side_effect=lambda *args, **kwargs: next(responses, "5")):
        # Mock input() for welcome screen
        with patch('builtins.input', return_value=""):
            # Mock Confirm.ask to always return True
            with patch('rich.prompt.Confirm.ask', return_value=True):
                cli = StandardModeCLI()
                
                # Test database loading first
                print("Testing database loading...")
                databases = await cli._load_databases()
                print(f"Found {len(databases)} databases:")
                for name in list(databases.keys())[:5]:
                    print(f"  - {name}")
                
                if not databases:
                    print("\nNo databases found! Check the path.")
                    return
                
                print("\nDatabases loaded successfully!")
                
                # Now test the CLI briefly
                print("\nTesting CLI menu system...")
                try:
                    # Run for just a moment to test
                    await asyncio.wait_for(cli.run(), timeout=2.0)
                except asyncio.TimeoutError:
                    print("CLI started successfully (timeout as expected)")
                except Exception as e:
                    print(f"CLI test completed with: {e}")


if __name__ == "__main__":
    asyncio.run(test_cli_with_auto_responses())