Purpose: The main entry point for the interactive deduplication CLI. It uses `argparse` to handle command-line arguments and launches the appropriate CLI mode.
Utility: Provides a user-facing interface for the powerful deduplication engine, making it accessible to non-developers or for guided interactive sessions.

#!/usr/bin/env python3
"""
Standalone entry point for the Blackcore Deduplication CLI.

Supports multiple modes:
- Simple: Basic deduplication with minimal configuration
- Standard: Interactive interface with guided workflows (default)
- Expert: Advanced features with full control
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.cli.standard_mode import StandardModeCLI


def main():
    """Main entry point for the deduplication CLI."""
    parser = argparse.ArgumentParser(
        description="Blackcore Deduplication Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in standard mode (default)
  python dedupe_cli.py
  
  # Run in standard mode explicitly
  python dedupe_cli.py --mode standard
  
  # Show version
  python dedupe_cli.py --version

Available modes:
  standard: Interactive interface with guided workflows (recommended)
  simple:   Basic deduplication with minimal options (future)
  expert:   Advanced features with full control (future)
""",
    )

    parser.add_argument(
        "--mode",
        choices=["simple", "standard", "expert"],
        default="standard",
        help="CLI mode to use (default: standard)",
    )

    parser.add_argument(
        "--version", action="version", version="Blackcore Deduplication CLI v1.0.0"
    )

    parser.add_argument("--config", type=Path, help="Path to configuration file")

    args = parser.parse_args()

    # Currently only standard mode is implemented
    if args.mode == "standard":
        cli = StandardModeCLI()

        # Load config if provided
        if args.config and args.config.exists():
            cli.config_wizard.load_config(args.config)

        # Run the CLI
        try:
            asyncio.run(cli.run())
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print(f"Mode '{args.mode}' is not yet implemented. Using standard mode.")
        cli = StandardModeCLI()
        asyncio.run(cli.run())


if __name__ == "__main__":
    main()
