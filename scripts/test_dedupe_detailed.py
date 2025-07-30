#!/usr/bin/env python3
"""Test deduplication with detailed debugging."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from blackcore.deduplication import DeduplicationEngine


def test_analysis_sync():
    """Test the analysis with debugging."""

    # Test data with clear duplicates
    test_data = [
        {
            "id": "1",
            "Full Name": "Anthony Smith",
            "Email": "tony@example.com",
            "Phone": "555-1234",
        },
        {
            "id": "2",
            "Full Name": "Tony Smith",
            "Email": "tony@example.com",
            "Phone": "555-1234",
        },
        {
            "id": "3",
            "Full Name": "Jane Doe",
            "Email": "jane@example.com",
            "Phone": "555-5678",
        },
    ]

    print("Test data:")
    for record in test_data:
        print(f"  {record}")

    # Create engine
    engine = DeduplicationEngine()

    # Update config
    engine.config.update(
        {
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "enable_ai_analysis": False,
            "safety_mode": True,
        }
    )

    print("\nConfiguration:")
    print(f"  Auto-merge threshold: {engine.config['auto_merge_threshold']}%")
    print(f"  Review threshold: {engine.config['human_review_threshold']}%")

    print("\nRunning analysis...")
    result = engine.analyze_database("People & Contacts", test_data, enable_ai=False)

    print("\nResults:")
    print(f"  Total entities: {result.total_entities}")
    print(f"  Potential duplicates: {result.potential_duplicates}")
    print(f"  High confidence: {len(result.high_confidence_matches)}")
    print(f"  Medium confidence: {len(result.medium_confidence_matches)}")
    print(f"  Low confidence: {len(result.low_confidence_matches)}")

    # Check if processor is working
    processor = engine.processors.get("People & Contacts")
    if processor:
        print("\nProcessor check:")
        print(f"  Processor type: {type(processor).__name__}")

        # Test direct comparison
        is_dup = processor.is_potential_duplicate(test_data[0], test_data[1])
        print(f"  Direct comparison (Anthony vs Tony): {is_dup}")

        # Test similarity
        scores = engine.similarity_scorer.calculate_similarity(
            test_data[0], test_data[1], processor.get_comparison_fields()
        )
        print("\n  Similarity scores:")
        for field, score in scores.items():
            if isinstance(score, dict):
                print(f"    {field}: {score.get('composite', 0):.1f}%")

        # Calculate confidence
        confidence = processor.calculate_confidence(scores, test_data[0], test_data[1])
        print(f"\n  Final confidence: {confidence:.1f}%")

    # Show all matches found
    all_matches = (
        result.high_confidence_matches
        + result.medium_confidence_matches
        + result.low_confidence_matches
    )

    if all_matches:
        print("\nAll matches found:")
        for match in all_matches:
            e1 = match["entity_a"]["Full Name"]
            e2 = match["entity_b"]["Full Name"]
            conf = match["confidence_score"]
            print(f"  - {e1} <-> {e2} ({conf:.1f}%)")
    else:
        print("\nNo matches found!")


if __name__ == "__main__":
    test_analysis_sync()
