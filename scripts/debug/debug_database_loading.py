""
Purpose: A debugging script to diagnose issues with loading local JSON database files, specifically for the deduplication CLI.
Utility: Helps developers quickly identify pathing or file access problems when the deduplication CLI fails to load data. It's a targeted diagnostic tool.
""
#!/usr/bin/env python3
"""Debug database loading issue in the CLI."""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.cli.standard_mode import StandardModeCLI


async def debug_loading():
    """Debug the database loading process."""
    cli = StandardModeCLI()

    print(f"Current working directory: {Path.cwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print(f"Parent directory: {Path(__file__).parent.parent}")

    # Test different paths
    relative_path = Path("blackcore/models/json")
    print(f"\nRelative path exists: {relative_path.exists()}")
    print(f"Relative path absolute: {relative_path.absolute()}")

    # Try from parent
    parent_path = Path(__file__).parent.parent / "blackcore" / "models" / "json"
    print(f"\nParent path exists: {parent_path.exists()}")
    print(f"Parent path absolute: {parent_path.absolute()}")

    # Load databases
    print("\nLoading databases...")
    databases = await cli._load_databases()

    print(f"\nFound {len(databases)} databases:")
    for name, records in databases.items():
        print(f"  - {name}: {len(records)} records")

    # Also check specific files
    json_dir = Path("blackcore/models/json")
    if json_dir.exists():
        print(f"\nJSON files in {json_dir}:")
        for f in list(json_dir.glob("*.json"))[:5]:
            print(f"  - {f.name}")


if __name__ == "__main__":
    asyncio.run(debug_loading())
