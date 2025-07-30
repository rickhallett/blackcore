#!/usr/bin/env python3
"""
Run a demo of the deduplication CLI.

This script sets up a controlled environment to demonstrate the CLI functionality.
"""

import sys
import os
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

# Add to Python path
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("Blackcore Deduplication CLI Demo")
print("="*60)
print()
print("This will launch the interactive deduplication CLI.")
print("The CLI will guide you through:")
print("  1. Database selection")
print("  2. Threshold configuration")
print("  3. Running analysis")
print("  4. Reviewing matches")
print()
print("Press Ctrl+C at any time to exit.")
print()
input("Press Enter to start...")

# Run the CLI
os.system("python scripts/dedupe_cli.py")