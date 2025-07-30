#!/usr/bin/env python3
"""
Deduplication Diagnostic Tool

Analyzes similarity scores and helps tune the deduplication system
for better accuracy on known duplicate pairs.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication import (
    SimilarityScorer,
    PersonProcessor,
    OrganizationProcessor,
    EventProcessor,
)


def create_known_duplicate_pairs():
    """Create pairs of entities that are known to be duplicates."""

    return [
        # People duplicates
        {
            "type": "People & Contacts",
            "entity_a": {
                "id": "person_1",
                "Full Name": "Anthony Smith",
                "Email": "tony.smith@example.com",
                "Phone": "01234567890",
                "Organization": "Swanage Town Council",
                "Role": "Councillor",
            },
            "entity_b": {
                "id": "person_2",
                "Full Name": "Tony Smith",
                "Email": "tony.smith@example.com",
                "Phone": "01234 567 890",
                "Organization": "STC",
                "Role": "Council Member",
            },
            "expected": "duplicate",
        },
        # Organization duplicates
        {
            "type": "Organizations & Bodies",
            "entity_a": {
                "id": "org_1",
                "Organization Name": "Swanage Town Council",
                "Website": "https://www.swanage.gov.uk",
                "Email": "info@swanage.gov.uk",
                "Category": "Local Government",
            },
            "entity_b": {
                "id": "org_2",
                "Organization Name": "STC",
                "Website": "swanage.gov.uk",
                "Email": "admin@swanage.gov.uk",
                "Category": "Council",
            },
            "expected": "duplicate",
        },
        # Event duplicates
        {
            "type": "Key Places & Events",
            "entity_a": {
                "id": "event_1",
                "Event / Place Name": "Town Council Meeting",
                "Date of Event": "2024-01-15",
                "Location": "Town Hall, Swanage",
            },
            "entity_b": {
                "id": "event_2",
                "Event / Place Name": "STC Monthly Meeting",
                "Date of Event": "2024-01-15",
                "Location": "Swanage Town Hall",
            },
            "expected": "duplicate",
        },
    ]


def analyze_similarity_scores():
    """Analyze similarity scores for known duplicate pairs."""

    print("🔍 Deduplication Diagnostic Analysis")
    print("=" * 60)

    # Initialize components
    similarity_scorer = SimilarityScorer()
    processors = {
        "People & Contacts": PersonProcessor(),
        "Organizations & Bodies": OrganizationProcessor(),
        "Key Places & Events": EventProcessor(),
    }

    known_pairs = create_known_duplicate_pairs()

    for i, pair_data in enumerate(known_pairs):
        print(f"\n📊 Analyzing Pair {i+1}: {pair_data['type']}")
        print("-" * 40)

        entity_a = pair_data["entity_a"]
        entity_b = pair_data["entity_b"]
        entity_type = pair_data["type"]
        processor = processors[entity_type]

        # Get comparison fields
        comparison_fields = processor.get_comparison_fields()
        print(f"Comparison fields: {comparison_fields}")

        # Calculate similarity scores
        similarity_scores = similarity_scorer.calculate_similarity(
            entity_a, entity_b, comparison_fields
        )

        print("\n📈 Similarity Scores:")
        for field, scores in similarity_scores.items():
            if field != "overall" and isinstance(scores, dict):
                composite = scores.get("composite", 0)
                exact = scores.get("exact", 0)
                print(f"  {field:20}: {composite:5.1f}% (exact: {exact:3.0f}%)")

        # Calculate processor confidence
        processor_confidence = processor.calculate_confidence(
            similarity_scores, entity_a, entity_b
        )
        overall_score = similarity_scores.get("overall", 0)

        # Debug abbreviation detection for organizations
        if entity_type == "Organizations & Bodies":
            org_a = entity_a.get("Organization Name", "")
            org_b = entity_b.get("Organization Name", "")
            is_abbrev = processor._could_be_abbreviation(org_a, org_b)
            print(
                f"  Debug: Abbreviation check for '{org_a}' vs '{org_b}': {is_abbrev}"
            )

        print("\n🎯 Final Scores:")
        print(f"  Overall similarity: {overall_score:5.1f}%")
        print(f"  Processor confidence: {processor_confidence:5.1f}%")

        # Check if potential duplicate
        is_potential = processor.is_potential_duplicate(entity_a, entity_b)
        print(f"  Potential duplicate: {is_potential}")

        # Show key differences if scores are low
        if processor_confidence < 70:
            print("\n⚠️  Low confidence analysis:")

            # Check exact matches
            exact_matches = []
            for field, scores in similarity_scores.items():
                if isinstance(scores, dict) and scores.get("exact", 0) == 100:
                    exact_matches.append(field)

            if exact_matches:
                print(f"    Exact matches: {exact_matches}")
            else:
                print("    No exact field matches found")

            # Show field values for comparison
            print("    Field value comparison:")
            for field in processor.get_primary_fields():
                val_a = entity_a.get(field, "")
                val_b = entity_b.get(field, "")
                print(f"      {field}: '{val_a}' vs '{val_b}'")

        print(
            f"\n✅ Expected: {pair_data['expected']} | Detected: {'duplicate' if processor_confidence >= 70 else 'not duplicate'}"
        )


def suggest_improvements():
    """Suggest improvements to the deduplication system."""

    print("\n💡 Improvement Suggestions")
    print("=" * 60)

    print("1. Lower Thresholds:")
    print("   - Current auto-merge threshold: 90%")
    print("   - Current human review threshold: 70%")
    print("   - Consider lowering to 85% and 60% respectively")

    print("\n2. Field Weighting:")
    print("   - Email exact matches should have very high weight")
    print("   - Phone number normalization needs improvement")
    print("   - Organization abbreviation detection needs enhancement")

    print("\n3. Preprocessing:")
    print("   - Implement better name normalization")
    print("   - Add nickname/abbreviation dictionaries")
    print("   - Improve website URL normalization")

    print("\n4. Algorithm Tuning:")
    print("   - Adjust composite score calculations")
    print("   - Add domain-specific bonus scores")
    print("   - Implement fuzzy date matching")


if __name__ == "__main__":
    try:
        analyze_similarity_scores()
        suggest_improvements()

    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
