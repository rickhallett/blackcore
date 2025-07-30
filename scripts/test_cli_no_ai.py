#!/usr/bin/env python3
"""Test the CLI without AI to ensure it works."""

import sys
import os
from pathlib import Path

# Ensure no API keys are set
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import after clearing environment
from blackcore.deduplication import DeduplicationEngine


def test_engine_without_ai():
    """Test that the engine works without AI."""
    print("Testing deduplication engine without AI...")

    # Create engine - should not fail even without API keys
    engine = DeduplicationEngine()

    # Check configuration
    print(f"AI analysis enabled: {engine.config.get('enable_ai_analysis')}")
    print(f"LLM analyzer initialized: {engine.llm_analyzer is not None}")

    # Test data
    test_data = [
        {"id": "1", "Full Name": "Tony Powell", "Organization": "Dorset Coast Forum"},
        {
            "id": "2",
            "Full Name": "Tony Powell",
            "Organization": "Dorset Coast Forum (DCF)",
        },
    ]

    # Run analysis
    result = engine.analyze_database("People & Contacts", test_data, enable_ai=False)

    print("\nAnalysis complete:")
    print(f"  Total entities: {result.total_entities}")
    print(f"  Duplicates found: {result.potential_duplicates}")

    if result.high_confidence_matches:
        match = result.high_confidence_matches[0]
        print("\nFound match:")
        print(
            f"  {match['entity_a']['Full Name']} <-> {match['entity_b']['Full Name']}"
        )
        print(f"  Confidence: {match['confidence_score']:.1f}%")

    print("\n✅ Engine works without AI!")
    return True


if __name__ == "__main__":
    try:
        test_engine_without_ai()
        print("\nNow you can run the CLI safely:")
        print("  python scripts/dedupe_cli.py")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
