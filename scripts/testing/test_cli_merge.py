#!/usr/bin/env python3
"""
Test script to verify CLI merge functionality works correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.merge_proposals import MergeExecutor


def test_cli_merge_scenario():
    """Test a merge scenario similar to what the CLI would execute."""

    print("Testing CLI merge scenario...")
    print("=" * 60)

    # Simulate entities from the People database
    entity_a = {
        "id": "person-1",
        "Full Name": "Tony Powell",
        "Email": "tony.powell@example.com",
        "Phone": "555-0123",
        "Organization": ["ABC Organization", "XYZ Corp"],  # List value
        "Title": "Director",
    }

    entity_b = {
        "id": "person-2",
        "Full Name": "Tony Powell",
        "Email": ["tony.powell@example.com", "tpowell@abc.org"],  # List value
        "Phone": "555-0123",
        "Organization": "ABC Organization",
        "Department": "Operations",
        "LinkedIn": "linkedin.com/in/tonypowell",
    }

    # Create match object similar to CLI
    match = {
        "entity_a": entity_a,
        "entity_b": entity_b,
        "confidence_score": 92.5,
        "entity_type": "Person",
        "primary_entity": "B",  # User selected B as primary
        "evidence": {"name_match": True, "email_match": True, "phone_match": True},
    }

    # Initialize merge executor (simulating CLI config)
    merge_config = {"safety_mode": True, "enable_ai_analysis": False}
    merge_executor = MergeExecutor(merge_config)

    # Determine primary/secondary based on user selection
    if match["primary_entity"] == "B":
        primary = entity_b
        secondary = entity_a
        print("User selected Entity B as primary")
    else:
        primary = entity_a
        secondary = entity_b
        print("User selected Entity A as primary")

    # Create proposal
    print("\nCreating merge proposal...")
    proposal = merge_executor.create_proposal(
        primary_entity=primary,
        secondary_entity=secondary,
        confidence_score=match["confidence_score"],
        evidence=match["evidence"],
        entity_type=match["entity_type"],
    )

    print(f"Proposal ID: {proposal.proposal_id}")
    print(f"Merge strategy: {proposal.merge_strategy}")

    # Execute merge (auto-approved by user in CLI)
    print("\nExecuting merge...")
    result = merge_executor.execute_merge(proposal, auto_approved=True)

    if result.success:
        print("✅ Merge successful!")
        print("\nMerged entity:")
        for key, value in result.merged_entity.items():
            if not key.startswith("_"):
                print(f"  {key}: {value}")

        # Verify primary entity was respected
        print("\nVerification:")
        print(
            f"  Primary entity ID preserved: {result.merged_entity.get('id') == primary.get('id')}"
        )
        print(
            f"  Primary entity LinkedIn preserved: {result.merged_entity.get('LinkedIn') == 'linkedin.com/in/tonypowell'}"
        )
        print(
            f"  Secondary entity Organization merged: {'XYZ Corp' in str(result.merged_entity.get('Organization', ''))}"
        )
    else:
        print("❌ Merge failed!")
        print(f"Errors: {result.errors}")
        return False

    return True


if __name__ == "__main__":
    success = test_cli_merge_scenario()

    print("\n" + "=" * 60)
    if success:
        print("✅ CLI merge test passed")
    else:
        print("❌ CLI merge test failed")
        sys.exit(1)
