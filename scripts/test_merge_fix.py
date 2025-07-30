#!/usr/bin/env python3
"""
Test script to verify the merge fix for list values.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.merge_proposals import MergeExecutor, MergeProposal


def test_merge_with_list_values():
    """Test merging entities with list values."""
    
    # Create test entities with list values (non-conflicting)
    entity_a = {
        "id": "test-a",
        "Full Name": "John Doe",
        "Email": ["john@example.com", "j.doe@company.com"],  # List value
        "Phone": "555-1234",
        "Organization": "Acme Corp",
        "Title": "Engineer"
    }
    
    entity_b = {
        "id": "test-b", 
        "Full Name": "John Doe",
        "Email": ["john@example.com", "j.doe@company.com"],  # Same list value
        "Phone": "555-1234",  # Same value
        "Organization": "Acme Corp",  # Same value
        "Department": ["Engineering", "R&D"],  # List value in new field
        "Skills": ["Python", "JavaScript"]  # List value in new field
    }
    
    # Create merge executor
    executor = MergeExecutor()
    
    # Create proposal
    print("Creating merge proposal...")
    proposal = executor.create_proposal(
        primary_entity=entity_a,
        secondary_entity=entity_b,
        confidence_score=95.0,
        evidence={"test": True},
        entity_type="Person"
    )
    
    print(f"\nProposal created: {proposal.proposal_id}")
    print(f"Safety checks: {proposal.safety_checks}")
    print(f"Risk factors: {proposal.risk_factors}")
    print(f"Merge strategy: {proposal.merge_strategy}")
    
    # Execute merge
    print("\nExecuting merge...")
    result = executor.execute_merge(proposal, auto_approved=True)
    
    if result.success:
        print("✅ Merge successful!")
        print("\nMerged entity:")
        for key, value in result.merged_entity.items():
            if not key.startswith("_"):
                print(f"  {key}: {value}")
    else:
        print("❌ Merge failed!")
        print(f"Errors: {result.errors}")
        
    return result.success


if __name__ == "__main__":
    print("Testing merge with list values...")
    print("=" * 60)
    
    success = test_merge_with_list_values()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test passed - merge handles list values correctly")
    else:
        print("❌ Test failed - merge has issues with list values")
        sys.exit(1)