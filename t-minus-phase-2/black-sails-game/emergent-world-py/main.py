#!/usr/bin/env python3
"""Main entry point for emergent world demo."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from examples.simple_world import run_simulation


if __name__ == "__main__":
    print("🌍 Emergent World Engine - Python Implementation")
    print("=" * 60)
    print()
    print("This demo creates a simple world with:")
    print("- 1 Merchant NPC (greedy personality)")
    print("- 2 Adventurer NPCs (curious personalities)")
    print("- Market trading system")
    print("- LLM-powered decision making (if API keys set)")
    print()
    print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY for AI features")
    print()
    print("Starting simulation...")
    print()
    
    try:
        asyncio.run(run_simulation(duration=30))
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise