#!/usr/bin/env python3
"""Test deduplication analysis directly."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from blackcore.deduplication.cli import AsyncDeduplicationEngine


async def test_analysis():
    """Test the analysis directly without UI."""
    
    # Load test data
    test_data = {
        "Test People": [
            {"id": "1", "Full Name": "Anthony Smith", "Email": "tony@example.com"},
            {"id": "2", "Full Name": "Tony Smith", "Email": "tony@example.com"},
            {"id": "3", "Full Name": "Jane Doe", "Email": "jane@example.com"},
        ]
    }
    
    # Configure
    config = {
        "auto_merge_threshold": 90.0,
        "human_review_threshold": 70.0,
        "enable_ai_analysis": False,
        "safety_mode": True
    }
    
    print("Initializing engine...")
    engine = AsyncDeduplicationEngine(config)
    
    print("\nRunning analysis...")
    
    # Simple progress callback
    async def progress_callback(update):
        print(f"  {update.stage}: {update.current}/{update.total}")
    
    results = await engine.analyze_databases_async(
        test_data,
        progress_callback=progress_callback
    )
    
    print("\nResults:")
    for db_name, result in results.items():
        print(f"\n{db_name}:")
        print(f"  Total entities: {result.total_entities}")
        print(f"  Potential duplicates: {result.potential_duplicates}")
        
        if result.high_confidence_matches:
            print("\n  High confidence matches:")
            for match in result.high_confidence_matches:
                e1 = match["entity_a"]["Full Name"]
                e2 = match["entity_b"]["Full Name"]
                conf = match["confidence_score"]
                print(f"    - {e1} <-> {e2} ({conf:.1f}%)")
    
    await engine.shutdown()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(test_analysis())