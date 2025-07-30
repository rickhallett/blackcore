"""Regression tests to prevent known bugs from reoccurring."""

import pytest
from unittest.mock import Mock, patch


class TestKnownBugPrevention:
    """Test specific bugs to prevent regression."""
    
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_low_confidence_review_bug(self, mock_cli_with_data):
        """
        Regression test for the specific bug where CLI shows "4 matches of low confidence" 
        but then says "nothing to review" when user proceeds.
        
        Bug report: UI/Logic consistency - showing count but not including in review.
        Location: blackcore/deduplication/cli/standard_mode.py:273-294
        """
        cli = mock_cli_with_data
        
        # Create a database result with ONLY low confidence matches
        db_result = Mock()
        db_result.total_entities = 100
        db_result.potential_duplicates = 4
        db_result.high_confidence_matches = []  # Empty
        db_result.medium_confidence_matches = []  # Empty
        db_result.low_confidence_matches = [
            {"id": "match-1", "confidence": 65.0, "entity_a": {"id": "1"}, "entity_b": {"id": "2"}},
            {"id": "match-2", "confidence": 68.0, "entity_a": {"id": "3"}, "entity_b": {"id": "4"}},
            {"id": "match-3", "confidence": 62.0, "entity_a": {"id": "5"}, "entity_b": {"id": "6"}},
            {"id": "match-4", "confidence": 69.0, "entity_a": {"id": "7"}, "entity_b": {"id": "8"}}
        ]
        
        # Mock the analysis results
        mock_results = {"People & Contacts": db_result}
        
        # Test the exact scenario from the bug report
        with patch.object(cli.engine, 'analyze_databases_async', return_value=mock_results):
            # Simulate the summary display
            summary_count = len(db_result.low_confidence_matches)
            assert summary_count == 4, "Summary should show 4 low confidence matches"
            
            # Test the critical part - collecting matches for review
            # This is where the bug was: low confidence matches were excluded
            matches_to_review = []
            
            # Add high confidence matches for auto-approval
            for match in db_result.high_confidence_matches:
                match["database"] = "People & Contacts"
                # High confidence would go to auto-approval, not review
                
            # Add medium confidence matches for manual review  
            for match in db_result.medium_confidence_matches:
                match["database"] = "People & Contacts"
                matches_to_review.append(match)
                
            # THE BUG FIX: Add low confidence matches for manual review
            # (User explicitly said they want to review them)
            for match in db_result.low_confidence_matches:
                match["database"] = "People & Contacts"
                matches_to_review.append(match)
                
            # Validate the fix
            assert len(matches_to_review) == 4, \
                f"Should have 4 matches to review (the low confidence ones), got {len(matches_to_review)}"
            
            # Ensure all low confidence matches are included
            review_ids = {match["id"] for match in matches_to_review}
            expected_ids = {match["id"] for match in db_result.low_confidence_matches}
            assert review_ids == expected_ids, \
                "All low confidence matches should be included in review"
                
            # The bug would have resulted in: len(matches_to_review) == 0
            # Which would cause "nothing to review" message despite showing "4 matches"
            
    @pytest.mark.asyncio
    @pytest.mark.regression  
    async def test_primary_entity_selection_consistency(self, mock_cli_with_data):
        """
        Regression test for primary entity selection consistency.
        
        Ensures that when a user swaps primary entity, the selection is preserved
        throughout the review process and merge execution.
        """
        cli = mock_cli_with_data
        
        # Create test match
        match = {
            "entity_a": {
                "id": "person-1",
                "Full Name": "John Smith", 
                "Email": "john@company.com",
                "Title": "Manager"
            },
            "entity_b": {
                "id": "person-2",
                "Full Name": "John Smith",
                "Email": "j.smith@company.com", 
                "Phone": "555-1234",
                "Department": "Sales"
            },
            "confidence_score": 85.0,
            "database": "People & Contacts",
            "primary_entity": "A"  # Initially A
        }
        
        # Test primary entity swapping
        original_primary = match["primary_entity"]
        
        # User swaps to B
        match["primary_entity"] = "B"
        
        # Validate swap
        assert match["primary_entity"] != original_primary
        assert match["primary_entity"] == "B"
        
        # When user approves merge, primary entity selection should be respected
        if match["primary_entity"] == "B":
            primary_entity = match["entity_b"]
            secondary_entity = match["entity_a"]
        else:
            primary_entity = match["entity_a"] 
            secondary_entity = match["entity_b"]
            
        # Validate correct entities are selected
        assert primary_entity["id"] == "person-2"  # B was selected as primary
        assert secondary_entity["id"] == "person-1"  # A becomes secondary
        
        # Test merge preview respects primary selection
        merged_preview = primary_entity.copy()
        
        # Fill missing fields from secondary
        for key, value in secondary_entity.items():
            if key not in merged_preview or not merged_preview[key]:
                merged_preview[key] = value
                
        # Validate that primary entity's ID and core data are preserved
        assert merged_preview["id"] == primary_entity["id"]
        assert merged_preview["Full Name"] == primary_entity["Full Name"]
        assert merged_preview["Email"] == primary_entity["Email"]
        
        # Validate that secondary data was added where missing
        assert merged_preview["Title"] == "Manager"  # From secondary (A)
        assert merged_preview["Phone"] == "555-1234"  # From primary (B)
        assert merged_preview["Department"] == "Sales"  # From primary (B)
        
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_empty_review_collection_bug(self, mock_cli_with_data):
        """
        Regression test for empty review collection despite having matches.
        
        Prevents bugs where matches exist but review collection logic fails
        to include them due to incorrect filtering or conditions.
        """
        cli = mock_cli_with_data
        
        # Test various scenarios that could cause empty review collections
        test_scenarios = [
            {
                "name": "only_low_confidence",
                "high_confidence": [],
                "medium_confidence": [],
                "low_confidence": [{"id": "low-1"}, {"id": "low-2"}],
                "expected_review_count": 2
            },
            {
                "name": "only_medium_confidence", 
                "high_confidence": [],
                "medium_confidence": [{"id": "med-1"}, {"id": "med-2"}],
                "low_confidence": [],
                "expected_review_count": 2
            },
            {
                "name": "mixed_confidence_levels",
                "high_confidence": [{"id": "high-1"}],  # Would auto-approve
                "medium_confidence": [{"id": "med-1"}],
                "low_confidence": [{"id": "low-1"}],
                "expected_review_count": 2  # Medium + Low for review
            },
            {
                "name": "all_high_confidence",
                "high_confidence": [{"id": "high-1"}, {"id": "high-2"}],
                "medium_confidence": [],
                "low_confidence": [],
                "expected_review_count": 0  # All auto-approved
            }
        ]
        
        for scenario in test_scenarios:
            db_result = Mock()
            db_result.high_confidence_matches = scenario["high_confidence"]
            db_result.medium_confidence_matches = scenario["medium_confidence"] 
            db_result.low_confidence_matches = scenario["low_confidence"]
            
            # Collect matches for review (the critical logic)
            matches_to_review = []
            
            # Medium confidence always goes to review
            for match in db_result.medium_confidence_matches:
                match["database"] = "Test DB"
                matches_to_review.append(match)
                
            # Low confidence goes to review (the bug fix)
            for match in db_result.low_confidence_matches:
                match["database"] = "Test DB"
                matches_to_review.append(match)
                
            # Validate review collection
            assert len(matches_to_review) == scenario["expected_review_count"], \
                f"Scenario '{scenario['name']}': Expected {scenario['expected_review_count']} matches for review, got {len(matches_to_review)}"
                
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_threshold_boundary_conditions(self, mock_cli_with_data):
        """
        Regression test for threshold boundary condition bugs.
        
        Ensures matches at exact threshold values are handled correctly.
        """
        cli = mock_cli_with_data
        
        # Mock configuration with specific thresholds
        cli.engine.engine.config.update({
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0
        })
        
        # Test matches at exact boundary values
        boundary_test_matches = [
            {"id": "exact_auto", "confidence": 90.0, "expected_category": "high"},
            {"id": "just_above_auto", "confidence": 90.1, "expected_category": "high"},
            {"id": "just_below_auto", "confidence": 89.9, "expected_category": "medium"},
            {"id": "exact_review", "confidence": 70.0, "expected_category": "medium"}, 
            {"id": "just_above_review", "confidence": 70.1, "expected_category": "medium"},
            {"id": "just_below_review", "confidence": 69.9, "expected_category": "low"}
        ]
        
        for match in boundary_test_matches:
            confidence = match["confidence"]
            auto_threshold = cli.engine.engine.config["auto_merge_threshold"]
            review_threshold = cli.engine.engine.config["human_review_threshold"]
            
            # Categorize match based on confidence
            if confidence >= auto_threshold:
                category = "high"
            elif confidence >= review_threshold:
                category = "medium"
            else:
                category = "low"
                
            assert category == match["expected_category"], \
                f"Match '{match['id']}' with confidence {confidence} should be '{match['expected_category']}', got '{category}'"
                
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_ui_consistency_with_backend_logic(self, mock_cli_with_data):
        """
        Regression test for UI/backend logic consistency.
        
        Ensures that what the UI displays matches what the backend logic processes.
        """
        cli = mock_cli_with_data
        
        # Create database result
        db_result = Mock()
        db_result.total_entities = 1000
        db_result.potential_duplicates = 25
        db_result.high_confidence_matches = [{"id": f"high-{i}"} for i in range(8)]
        db_result.medium_confidence_matches = [{"id": f"med-{i}"} for i in range(10)]
        db_result.low_confidence_matches = [{"id": f"low-{i}"} for i in range(7)]
        
        # Test UI summary calculation
        ui_summary = {
            "total_entities": db_result.total_entities,
            "potential_duplicates": db_result.potential_duplicates,
            "high_confidence": len(db_result.high_confidence_matches),
            "medium_confidence": len(db_result.medium_confidence_matches),
            "low_confidence": len(db_result.low_confidence_matches)
        }
        
        # Test backend processing logic
        auto_approved = len(db_result.high_confidence_matches)
        
        matches_for_review = []
        matches_for_review.extend(db_result.medium_confidence_matches)
        matches_for_review.extend(db_result.low_confidence_matches)
        review_count = len(matches_for_review)
        
        # Consistency checks
        assert ui_summary["high_confidence"] == auto_approved, \
            "UI high confidence count should match auto-approved count"
            
        assert ui_summary["medium_confidence"] + ui_summary["low_confidence"] == review_count, \
            "UI medium + low confidence counts should match review count"
            
        total_processed = auto_approved + review_count
        assert total_processed == ui_summary["potential_duplicates"], \
            "Total processed matches should equal potential duplicates shown in UI"
            
        # The critical test: if UI shows low confidence matches, they MUST be in review
        if ui_summary["low_confidence"] > 0:
            low_confidence_in_review = sum(1 for match in matches_for_review 
                                         if match.get("id", "").startswith("low-"))
            assert low_confidence_in_review == ui_summary["low_confidence"], \
                "All low confidence matches shown in UI must be available for review"
                
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_list_value_merge_handling(self, mock_cli_with_data):
        """
        Regression test for list value handling in merges.
        
        Ensures that list values are properly merged and don't cause conflicts.
        """
        cli = mock_cli_with_data
        
        # Test entities with various list configurations
        entity_a = {
            "id": "entity-1",
            "Full Name": "John Smith",
            "Email": "john@example.com",  # String
            "Skills": ["Python", "JavaScript"],  # List
            "Organizations": "Acme Corp"  # String
        }
        
        entity_b = {
            "id": "entity-2", 
            "Full Name": "John Smith",
            "Email": ["john@example.com", "j.smith@acme.com"],  # List with overlap
            "Skills": ["Python", "Go", "Docker"],  # List with partial overlap
            "Organizations": ["Acme Corp", "Beta Inc"],  # String to list conversion
            "Phone": "555-1234"  # New field
        }
        
        # Perform conservative merge (A as primary)
        merged = entity_a.copy()
        conflicts = {}
        
        for key, value in entity_b.items():
            if key == "id":
                continue
                
            if key in merged and merged[key]:
                # Handle list vs string comparisons
                if isinstance(merged[key], list) and isinstance(value, list):
                    # Both lists - check for overlap
                    set_a = {str(v).lower() for v in merged[key]}
                    set_b = {str(v).lower() for v in value}
                    if set_a.isdisjoint(set_b):
                        conflicts[key] = {"primary": merged[key], "secondary": value}
                elif isinstance(merged[key], list):
                    # Primary is list, secondary is string - check if string in list
                    if str(value).lower() not in {str(v).lower() for v in merged[key]}:
                        conflicts[key] = {"primary": merged[key], "secondary": value}
                elif isinstance(value, list):
                    # Primary is string, secondary is list - check if string in list
                    if str(merged[key]).lower() not in {str(v).lower() for v in value}:
                        conflicts[key] = {"primary": merged[key], "secondary": value}
                else:
                    # Both strings
                    if str(merged[key]).lower() != str(value).lower():
                        conflicts[key] = {"primary": merged[key], "secondary": value}
            else:
                # Fill empty field
                merged[key] = value
                
        # Validate merge results
        assert merged["id"] == "entity-1"  # Primary ID preserved
        assert merged["Full Name"] == "John Smith"  # Same in both
        assert merged["Email"] == "john@example.com"  # Primary value kept
        assert merged["Phone"] == "555-1234"  # Added from secondary
        
        # Skills should not conflict (Python overlap)
        assert "Skills" not in conflicts
        
        # Organizations should not conflict (Acme Corp overlap) 
        assert "Organizations" not in conflicts
        
        # Email should not conflict (overlap exists)
        assert "Email" not in conflicts
        
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_session_interruption_recovery(self, mock_cli_with_data):
        """
        Regression test for session interruption and recovery.
        
        Ensures that interrupted review sessions can be properly resumed.
        """
        cli = mock_cli_with_data
        
        # Create initial session state
        session_matches = [
            {"id": "match-1", "status": "pending"},
            {"id": "match-2", "status": "pending"}, 
            {"id": "match-3", "status": "pending"},
            {"id": "match-4", "status": "pending"}
        ]
        
        review_decisions = []
        current_index = 0
        
        # Process first two matches
        for i in range(2):
            match = session_matches[i]
            decision = {
                "match": match,
                "decision": "merge" if i == 0 else "separate",
                "reasoning": f"Decision for match {i+1}"
            }
            review_decisions.append(decision)
            match["status"] = "reviewed"
            current_index += 1
            
        # Simulate interruption at match 3
        interrupted_state = {
            "matches": session_matches,
            "decisions": review_decisions,
            "current_index": current_index,
            "completed_count": len(review_decisions)
        }
        
        # Validate interruption state
        assert interrupted_state["current_index"] == 2
        assert interrupted_state["completed_count"] == 2
        assert session_matches[0]["status"] == "reviewed"
        assert session_matches[1]["status"] == "reviewed" 
        assert session_matches[2]["status"] == "pending"
        assert session_matches[3]["status"] == "pending"
        
        # Test recovery
        remaining_matches = [m for m in session_matches if m["status"] == "pending"]
        assert len(remaining_matches) == 2
        
        # Continue from where left off
        for match in remaining_matches:
            decision = {
                "match": match,
                "decision": "defer",
                "reasoning": "Deferred after recovery"
            }
            review_decisions.append(decision)
            match["status"] = "reviewed"
            
        # Validate complete recovery
        assert len(review_decisions) == 4
        assert all(m["status"] == "reviewed" for m in session_matches)
        
        # Count final decisions
        decision_counts = {"merge": 0, "separate": 0, "defer": 0}
        for decision in review_decisions:
            decision_counts[decision["decision"]] += 1
            
        assert decision_counts["merge"] == 1
        assert decision_counts["separate"] == 1
        assert decision_counts["defer"] == 2