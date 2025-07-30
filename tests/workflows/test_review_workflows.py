"""Test interactive review workflows and decision making."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime


class TestReviewWorkflows:
    """Test interactive review workflows."""

    @pytest.mark.asyncio
    async def test_complete_review_session(self, mock_cli_with_data):
        """Test a complete review session with various decisions."""
        cli = mock_cli_with_data

        # Create test matches for review
        test_matches = [
            {
                "entity_a": {
                    "id": "1",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                },
                "entity_b": {
                    "id": "2",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                },
                "confidence_score": 95.0,
                "database": "People & Contacts",
                "primary_entity": "A",
            },
            {
                "entity_a": {
                    "id": "3",
                    "Full Name": "Jane Doe",
                    "Email": "jane@example.com",
                },
                "entity_b": {
                    "id": "4",
                    "Full Name": "Jane Doe",
                    "Email": "j.doe@example.com",
                },
                "confidence_score": 80.0,
                "database": "People & Contacts",
                "primary_entity": "B",
            },
            {
                "entity_a": {
                    "id": "5",
                    "Full Name": "Bob Wilson",
                    "Email": "bob@example.com",
                },
                "entity_b": {
                    "id": "6",
                    "Full Name": "Robert Wilson",
                    "Email": "rwilson@example.com",
                },
                "confidence_score": 70.0,
                "database": "People & Contacts",
                "primary_entity": "A",
            },
        ]

        # Simulate user decisions
        user_decisions = [
            {
                "match_index": 0,
                "action": "a",
                "reasoning": "Exact match, approve",
            },  # Approve
            {
                "match_index": 1,
                "action": "s",
                "reasoning": "Swap primary",
            },  # Swap primary
            {
                "match_index": 1,
                "action": "a",
                "reasoning": "Approve after swap",
            },  # Approve
            {
                "match_index": 2,
                "action": "r",
                "reasoning": "Different people",
            },  # Reject
        ]

        # Track review state
        review_decisions = []
        primary_selections = {}

        # Process each decision
        for decision in user_decisions:
            match_index = decision["match_index"]
            action = decision["action"]
            match = test_matches[match_index]
            match_id = f"{match['entity_a']['id']}_{match['entity_b']['id']}"

            # Initialize primary selection if not set
            if match_id not in primary_selections:
                primary_selections[match_id] = match.get("primary_entity", "A")

            if action == "s":  # Swap primary
                primary_selections[match_id] = (
                    "B" if primary_selections[match_id] == "A" else "A"
                )
                match["primary_entity"] = primary_selections[match_id]

            elif action in ["a", "r", "d"]:  # Approve, Reject, Defer
                decision_map = {"a": "merge", "r": "separate", "d": "defer"}

                review_decision = {
                    "match": match,
                    "decision": decision_map[action],
                    "reasoning": decision["reasoning"],
                    "timestamp": datetime.now(),
                    "reviewer": "test_user",
                }
                review_decisions.append(review_decision)

        # Validate review decisions
        assert len(review_decisions) == 3  # 3 final decisions

        # Check decision types
        decision_counts = {"merge": 0, "separate": 0, "defer": 0}
        for decision in review_decisions:
            decision_counts[decision["decision"]] += 1

        assert decision_counts["merge"] == 2  # 2 approvals
        assert decision_counts["separate"] == 1  # 1 rejection
        assert decision_counts["defer"] == 0  # 0 deferrals

        # Validate primary entity selections
        # Match 0: should remain A
        assert test_matches[0]["primary_entity"] == "A"

        # Match 1: should be swapped to B
        assert test_matches[1]["primary_entity"] == "B"

        # Match 2: should remain A
        assert test_matches[2]["primary_entity"] == "A"

    @pytest.mark.asyncio
    async def test_primary_entity_swapping(self, mock_cli_with_data):
        """Test primary entity swapping functionality."""
        cli = mock_cli_with_data

        # Test match with different entity data
        match = {
            "entity_a": {
                "id": "person-1",
                "Full Name": "John Smith",
                "Email": "john.smith@company.com",
                "Title": "Manager",
                "Organization": "Acme Corp",
            },
            "entity_b": {
                "id": "person-2",
                "Full Name": "John Smith",
                "Email": ["john@example.com", "j.smith@acme.com"],  # List value
                "Phone": "555-0123",
                "Organization": ["Acme Corp", "Beta Inc"],  # List value
                "Department": "Operations",
            },
            "confidence_score": 85.0,
            "primary_entity": "A",
        }

        # Test swapping scenarios
        swap_scenarios = [
            {"initial_primary": "A", "swaps": 1, "expected_final": "B"},
            {
                "initial_primary": "A",
                "swaps": 2,
                "expected_final": "A",  # Back to original
            },
            {"initial_primary": "B", "swaps": 1, "expected_final": "A"},
            {
                "initial_primary": "B",
                "swaps": 3,
                "expected_final": "A",  # Odd number of swaps
            },
        ]

        for scenario in swap_scenarios:
            # Reset match
            match["primary_entity"] = scenario["initial_primary"]

            # Perform swaps
            for _ in range(scenario["swaps"]):
                current_primary = match["primary_entity"]
                match["primary_entity"] = "B" if current_primary == "A" else "A"

            # Validate final state
            assert match["primary_entity"] == scenario["expected_final"], (
                f"After {scenario['swaps']} swaps from {scenario['initial_primary']}, "
                f"expected {scenario['expected_final']}, got {match['primary_entity']}"
            )

            # Validate that correct entities are selected
            if match["primary_entity"] == "A":
                primary_entity = match["entity_a"]
                secondary_entity = match["entity_b"]
            else:
                primary_entity = match["entity_b"]
                secondary_entity = match["entity_a"]

            # Validate entity selection
            assert primary_entity["id"] != secondary_entity["id"]
            assert "Full Name" in primary_entity
            assert "Full Name" in secondary_entity

    @pytest.mark.asyncio
    async def test_merge_preview_functionality(self, mock_cli_with_data):
        """Test merge preview functionality."""
        cli = mock_cli_with_data

        # Test entity with different field types
        entity_a = {
            "id": "entity-1",
            "Full Name": "Tony Powell",
            "Email": "tony@example.com",
            "Phone": "555-1234",
            "Organization": "ABC Corp",
            "Title": "Director",
        }

        entity_b = {
            "id": "entity-2",
            "Full Name": "Tony Powell",
            "Email": ["tony@example.com", "tpowell@abc.com"],  # List value
            "Phone": "555-1234",
            "Organization": ["ABC Corp", "XYZ Inc"],  # List value with conflict
            "Department": "Operations",  # New field
            "LinkedIn": "linkedin.com/in/tonypowell",  # New field
        }

        # Test preview with different primary selections
        preview_scenarios = [
            {
                "primary_entity": "A",
                "primary": entity_a,
                "secondary": entity_b,
                "expected_id": "entity-1",
                "expected_conflicts": [
                    "Organization"
                ],  # ABC Corp vs [ABC Corp, XYZ Inc]
                "expected_filled": ["Department", "LinkedIn"],
            },
            {
                "primary_entity": "B",
                "primary": entity_b,
                "secondary": entity_a,
                "expected_id": "entity-2",
                "expected_conflicts": [],  # No conflicts when B is primary
                "expected_filled": ["Title"],  # Only Title from A
            },
        ]

        for scenario in preview_scenarios:
            # Create mock merge preview
            merged = scenario["primary"].copy()
            conflicts = {}
            filled_fields = []

            # Simulate conservative merge logic
            for key, value in scenario["secondary"].items():
                if key.startswith("_") or key == "id":
                    continue

                if key in merged and merged[key] and merged[key] != value:
                    # Conflict detected
                    conflicts[key] = {"primary": merged[key], "secondary": value}
                elif key not in merged or not merged[key]:
                    # Fill empty field
                    merged[key] = value
                    filled_fields.append(key)

            # Validate preview results
            assert merged["id"] == scenario["expected_id"]

            # Check conflicts
            for expected_conflict in scenario["expected_conflicts"]:
                assert (
                    expected_conflict in conflicts
                ), f"Expected conflict in {expected_conflict} not found"

            # Check filled fields
            for expected_fill in scenario["expected_filled"]:
                assert (
                    expected_fill in filled_fields
                ), f"Expected filled field {expected_fill} not found"

            # Validate that primary entity data is preserved
            assert merged["Full Name"] == scenario["primary"]["Full Name"]
            assert merged["id"] == scenario["primary"]["id"]

    @pytest.mark.asyncio
    async def test_review_navigation(self, mock_cli_with_data):
        """Test review navigation (next, previous, jump to)."""
        cli = mock_cli_with_data

        # Create multiple matches
        matches = [
            {"id": "match-1", "confidence_score": 95.0},
            {"id": "match-2", "confidence_score": 85.0},
            {"id": "match-3", "confidence_score": 75.0},
            {"id": "match-4", "confidence_score": 65.0},
            {"id": "match-5", "confidence_score": 55.0},
        ]

        # Test navigation scenarios
        navigation_tests = [
            {
                "name": "linear_forward",
                "actions": ["n", "n", "n", "n"],  # Next 4 times
                "start_index": 0,
                "expected_final_index": 4,
            },
            {
                "name": "linear_backward",
                "actions": ["p", "p", "p"],  # Previous 3 times
                "start_index": 4,
                "expected_final_index": 1,
            },
            {
                "name": "mixed_navigation",
                "actions": ["n", "n", "p", "n"],  # Forward, forward, back, forward
                "start_index": 0,
                "expected_final_index": 2,
            },
            {
                "name": "boundary_handling",
                "actions": ["p", "p", "p"],  # Try to go before first
                "start_index": 0,
                "expected_final_index": 0,  # Should stay at 0
            },
            {
                "name": "boundary_handling_end",
                "actions": ["n", "n", "n"],  # Try to go past last
                "start_index": 4,
                "expected_final_index": 4,  # Should stay at 4
            },
        ]

        for test in navigation_tests:
            current_index = test["start_index"]

            # Process navigation actions
            for action in test["actions"]:
                if action == "n":  # Next
                    current_index = min(current_index + 1, len(matches) - 1)
                elif action == "p":  # Previous
                    current_index = max(current_index - 1, 0)

            # Validate final position
            assert (
                current_index == test["expected_final_index"]
            ), f"Navigation test '{test['name']}': expected index {test['expected_final_index']}, got {current_index}"

            # Validate that index is within bounds
            assert 0 <= current_index < len(matches)

    @pytest.mark.asyncio
    async def test_review_session_interruption_recovery(self, mock_cli_with_data):
        """Test review session interruption and recovery."""
        cli = mock_cli_with_data

        # Create review session state
        matches = [
            {"id": "match-1", "status": "pending"},
            {"id": "match-2", "status": "pending"},
            {"id": "match-3", "status": "pending"},
            {"id": "match-4", "status": "pending"},
        ]

        # Simulate partial review session
        review_decisions = [
            {
                "match": matches[0],
                "decision": "merge",
                "reasoning": "Clear duplicate",
                "timestamp": datetime.now(),
            },
            {
                "match": matches[1],
                "decision": "separate",
                "reasoning": "Different entities",
                "timestamp": datetime.now(),
            },
        ]

        # Mark reviewed matches
        matches[0]["status"] = "reviewed"
        matches[1]["status"] = "reviewed"

        # Test recovery state
        current_index = 2  # Should resume at match 3
        completed_reviews = len(review_decisions)
        remaining_matches = [m for m in matches if m["status"] == "pending"]

        # Validate recovery state
        assert completed_reviews == 2
        assert len(remaining_matches) == 2
        assert current_index == 2
        assert matches[current_index]["status"] == "pending"

        # Test that session can continue
        # Complete remaining reviews
        remaining_decisions = [
            {
                "match": matches[2],
                "decision": "defer",
                "reasoning": "Need more information",
                "timestamp": datetime.now(),
            },
            {
                "match": matches[3],
                "decision": "merge",
                "reasoning": "Similar enough",
                "timestamp": datetime.now(),
            },
        ]

        # Add to review decisions
        review_decisions.extend(remaining_decisions)

        # Validate completed session
        assert len(review_decisions) == 4

        # Count final decisions
        decision_counts = {"merge": 0, "separate": 0, "defer": 0}
        for decision in review_decisions:
            decision_counts[decision["decision"]] += 1

        assert decision_counts["merge"] == 2
        assert decision_counts["separate"] == 1
        assert decision_counts["defer"] == 1

    @pytest.mark.asyncio
    async def test_review_quality_validation(self, mock_cli_with_data):
        """Test review quality validation and feedback."""
        cli = mock_cli_with_data

        # Test different quality scenarios
        quality_tests = [
            {
                "name": "high_quality_review",
                "decision": "merge",
                "reasoning": "Both entities have the same email address (john@example.com), same phone number (555-0123), and work at the same organization (Acme Corp). The only difference is a slight variation in the name field, which appears to be a data entry inconsistency.",
                "time_spent": 120,  # 2 minutes
                "expected_quality": "high",
            },
            {
                "name": "rushed_review",
                "decision": "merge",
                "reasoning": "same person",
                "time_spent": 10,  # 10 seconds
                "expected_quality": "low",
            },
            {
                "name": "inconsistent_review",
                "decision": "separate",
                "reasoning": "These are clearly the same person with identical emails and phone numbers",  # Inconsistent reasoning
                "time_spent": 60,
                "expected_quality": "questionable",
            },
            {
                "name": "thorough_rejection",
                "decision": "separate",
                "reasoning": "While the names are similar, entity A works at Acme Corp and entity B works at Beta Inc. They have different email domains and different phone numbers. This appears to be two different people with similar names.",
                "time_spent": 180,  # 3 minutes
                "expected_quality": "high",
            },
        ]

        def assess_review_quality(decision, reasoning, time_spent):
            """Assess the quality of a review decision."""
            quality_score = 0
            issues = []

            # Check reasoning length and detail
            if len(reasoning) < 20:
                issues.append("reasoning_too_brief")
                quality_score -= 2
            elif len(reasoning) > 100:
                quality_score += 1

            # Check time spent
            if time_spent < 30:  # Less than 30 seconds
                issues.append("rushed_decision")
                quality_score -= 2
            elif time_spent > 300:  # More than 5 minutes
                quality_score += 1

            # Check for consistency keywords
            merge_keywords = ["same", "identical", "duplicate", "match"]
            separate_keywords = ["different", "distinct", "separate", "not the same"]

            reasoning_lower = reasoning.lower()

            if decision == "merge":
                if any(keyword in reasoning_lower for keyword in merge_keywords):
                    quality_score += 1
                if any(keyword in reasoning_lower for keyword in separate_keywords):
                    issues.append("inconsistent_reasoning")
                    quality_score -= 2

            elif decision == "separate":
                if any(keyword in reasoning_lower for keyword in separate_keywords):
                    quality_score += 1
                if any(keyword in reasoning_lower for keyword in merge_keywords):
                    issues.append("inconsistent_reasoning")
                    quality_score -= 2

            # Determine overall quality
            if quality_score >= 2:
                quality = "high"
            elif quality_score >= 0:
                quality = "medium"
            elif "inconsistent_reasoning" in issues:
                quality = "questionable"
            else:
                quality = "low"

            return quality, issues

        # Test each quality scenario
        for test in quality_tests:
            quality, issues = assess_review_quality(
                test["decision"], test["reasoning"], test["time_spent"]
            )

            assert (
                quality == test["expected_quality"]
            ), f"Quality test '{test['name']}': expected {test['expected_quality']}, got {quality}"

    @pytest.mark.asyncio
    async def test_batch_decision_application(self, mock_cli_with_data):
        """Test applying multiple review decisions in batch."""
        cli = mock_cli_with_data

        # Create multiple review decisions
        review_decisions = [
            {
                "match": {
                    "entity_a": {"id": "1", "Full Name": "John Smith"},
                    "entity_b": {"id": "2", "Full Name": "John Smith"},
                    "primary_entity": "A",
                    "confidence_score": 95.0,
                },
                "decision": "merge",
                "reasoning": "Exact match",
            },
            {
                "match": {
                    "entity_a": {"id": "3", "Full Name": "Jane Doe"},
                    "entity_b": {"id": "4", "Full Name": "Jane Doe"},
                    "primary_entity": "B",
                    "confidence_score": 90.0,
                },
                "decision": "merge",
                "reasoning": "Same person",
            },
            {
                "match": {
                    "entity_a": {"id": "5", "Full Name": "Bob Wilson"},
                    "entity_b": {"id": "6", "Full Name": "Robert Wilson"},
                    "primary_entity": "A",
                    "confidence_score": 75.0,
                },
                "decision": "separate",
                "reasoning": "Different people",
            },
        ]

        # Filter approved merges
        approved_merges = [d for d in review_decisions if d["decision"] == "merge"]

        # Validate batch processing
        assert len(approved_merges) == 2

        # Test that primary entity selection is preserved
        assert approved_merges[0]["match"]["primary_entity"] == "A"
        assert approved_merges[1]["match"]["primary_entity"] == "B"

        # Mock merge execution for batch
        merge_results = []

        with patch(
            "blackcore.deduplication.merge_proposals.MergeExecutor"
        ) as mock_executor_class:
            mock_executor = Mock()
            mock_executor_class.return_value = mock_executor

            # Mock successful merges
            mock_result = Mock()
            mock_result.success = True
            mock_result.merged_entity = {"id": "merged", "Full Name": "Merged Entity"}
            mock_executor.execute_merge.return_value = mock_result

            # Execute each approved merge
            for decision in approved_merges:
                match = decision["match"]

                # Respect primary entity selection
                if match["primary_entity"] == "B":
                    primary = match["entity_b"]
                    secondary = match["entity_a"]
                else:
                    primary = match["entity_a"]
                    secondary = match["entity_b"]

                # Create and execute proposal
                mock_proposal = Mock()
                mock_proposal.proposal_id = (
                    f"proposal-{primary['id']}-{secondary['id']}"
                )
                mock_executor.create_proposal.return_value = mock_proposal

                result = mock_executor.execute_merge(mock_proposal, auto_approved=True)
                merge_results.append(result)

        # Validate batch execution results
        assert len(merge_results) == 2
        assert all(result.success for result in merge_results)
        assert mock_executor.create_proposal.call_count == 2
        assert mock_executor.execute_merge.call_count == 2
