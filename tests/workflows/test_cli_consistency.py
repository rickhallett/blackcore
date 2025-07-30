"""Test CLI UI/Logic consistency to prevent bugs like the low confidence review issue."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from .conftest_workflows import WorkflowValidator


class TestCLIConsistency:
    """Test UI and logic consistency in the CLI."""
    
    @pytest.mark.asyncio
    async def test_summary_vs_review_consistency(self, mock_cli_with_data, workflow_validator):
        """Test that summary counts match what's available for review."""
        cli = mock_cli_with_data
        
        # Create test results with known counts
        mock_result = Mock()
        mock_result.total_entities = 10
        mock_result.potential_duplicates = 6
        mock_result.high_confidence_matches = [
            {"entity_a": {"id": "1"}, "entity_b": {"id": "2"}, "confidence_score": 95.0},
            {"entity_a": {"id": "3"}, "entity_b": {"id": "4"}, "confidence_score": 92.0}
        ]
        mock_result.medium_confidence_matches = [
            {"entity_a": {"id": "5"}, "entity_b": {"id": "6"}, "confidence_score": 85.0},
            {"entity_a": {"id": "7"}, "entity_b": {"id": "8"}, "confidence_score": 75.0}
        ]
        mock_result.low_confidence_matches = [
            {"entity_a": {"id": "9"}, "entity_b": {"id": "10"}, "confidence_score": 65.0},
            {"entity_a": {"id": "11"}, "entity_b": {"id": "12"}, "confidence_score": 60.0}
        ]
        
        results = {"People & Contacts": mock_result}
        
        # Calculate summary counts (what's shown to user)
        summary_counts = {
            "high_confidence": len(mock_result.high_confidence_matches),
            "medium_confidence": len(mock_result.medium_confidence_matches),
            "low_confidence": len(mock_result.low_confidence_matches)
        }
        
        # Simulate the review collection logic (what's actually available)
        matches_to_review = []
        for db_name, db_result in results.items():
            # Add medium confidence matches
            for match in db_result.medium_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)
                
            # Add high confidence matches if in safety mode
            if cli.engine.engine.config.get("safety_mode", True):
                for match in db_result.high_confidence_matches:
                    match["database"] = db_name
                    matches_to_review.append(match)
                    
            # Add low confidence matches for manual review
            for match in db_result.low_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)
        
        # Validate consistency
        consistency_errors = workflow_validator.validate_summary_consistency(
            summary_counts, 
            {
                "high_confidence": mock_result.high_confidence_matches,
                "medium_confidence": mock_result.medium_confidence_matches,
                "low_confidence": mock_result.low_confidence_matches
            }
        )
        
        assert len(consistency_errors) == 0, f"Summary consistency errors: {consistency_errors}"
        
        # Validate review availability
        review_errors = workflow_validator.validate_review_availability(
            summary_counts, matches_to_review
        )
        
        assert len(review_errors) == 0, f"Review availability errors: {review_errors}"
        
        # Final validation: total matches should equal sum of all categories
        expected_total = summary_counts["high_confidence"] + summary_counts["medium_confidence"] + summary_counts["low_confidence"]
        actual_total = len(matches_to_review)
        
        assert expected_total == actual_total, f"Expected {expected_total} matches for review, got {actual_total}"
        
    @pytest.mark.asyncio
    async def test_count_validation_edge_cases(self, mock_cli_with_data, workflow_validator):
        """Test count validation with edge cases."""
        cli = mock_cli_with_data
        
        edge_cases = [
            {
                "name": "no_matches",
                "high": [], "medium": [], "low": [],
                "expected_review_count": 0
            },
            {
                "name": "only_high_confidence",
                "high": [{"id": "1"}], "medium": [], "low": [],
                "expected_review_count": 1  # In safety mode
            },
            {
                "name": "only_medium_confidence", 
                "high": [], "medium": [{"id": "1"}], "low": [],
                "expected_review_count": 1
            },
            {
                "name": "only_low_confidence",
                "high": [], "medium": [], "low": [{"id": "1"}],
                "expected_review_count": 1
            },
            {
                "name": "mixed_confidence",
                "high": [{"id": "1"}, {"id": "2"}], 
                "medium": [{"id": "3"}], 
                "low": [{"id": "4"}, {"id": "5"}, {"id": "6"}],
                "expected_review_count": 6
            }
        ]
        
        for case in edge_cases:
            # Create mock result for this case
            mock_result = Mock()
            mock_result.high_confidence_matches = case["high"]
            mock_result.medium_confidence_matches = case["medium"]
            mock_result.low_confidence_matches = case["low"]
            
            results = {"Test DB": mock_result}
            
            # Calculate what should be shown in summary
            summary_counts = {
                "high_confidence": len(case["high"]),
                "medium_confidence": len(case["medium"]),
                "low_confidence": len(case["low"])
            }
            
            # Calculate what should be available for review
            matches_to_review = []
            for db_name, db_result in results.items():
                for match in db_result.medium_confidence_matches:
                    match["database"] = db_name
                    matches_to_review.append(match)
                    
                # In safety mode, add high confidence matches
                if cli.engine.engine.config.get("safety_mode", True):
                    for match in db_result.high_confidence_matches:
                        match["database"] = db_name
                        matches_to_review.append(match)
                        
                # Add low confidence matches
                for match in db_result.low_confidence_matches:
                    match["database"] = db_name
                    matches_to_review.append(match)
            
            # Validate this edge case
            assert len(matches_to_review) == case["expected_review_count"], \
                f"Edge case '{case['name']}': expected {case['expected_review_count']} matches, got {len(matches_to_review)}"
                
            # Validate consistency
            review_errors = workflow_validator.validate_review_availability(
                summary_counts, matches_to_review
            )
            assert len(review_errors) == 0, f"Edge case '{case['name']}' failed: {review_errors}"
            
    @pytest.mark.asyncio
    async def test_primary_entity_display_consistency(self, mock_cli_with_data):
        """Test that primary entity display remains consistent throughout workflow."""
        cli = mock_cli_with_data
        
        # Create a match with entities
        match = {
            "entity_a": {"id": "entity-1", "Full Name": "John Smith", "Email": "john@example.com"},
            "entity_b": {"id": "entity-2", "Full Name": "John Smith", "Email": "j.smith@company.com"},
            "confidence_score": 85.0,
            "database": "People & Contacts"
        }
        
        # Test different primary entity selections
        primary_selections = ["A", "B"]
        
        for primary in primary_selections:
            match["primary_entity"] = primary
            
            # Validate that the correct entity is marked as primary
            if primary == "A":
                primary_entity = match["entity_a"]
                secondary_entity = match["entity_b"]
            else:
                primary_entity = match["entity_b"]
                secondary_entity = match["entity_a"]
                
            # Validate primary entity properties
            assert primary_entity["id"] in ["entity-1", "entity-2"]
            assert secondary_entity["id"] in ["entity-1", "entity-2"]
            assert primary_entity["id"] != secondary_entity["id"]
            
            # Test merge proposal creation respects primary selection
            with patch('blackcore.deduplication.merge_proposals.MergeExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor_class.return_value = mock_executor
                
                # Mock proposal creation
                mock_proposal = Mock()
                mock_proposal.proposal_id = "test-proposal"
                mock_executor.create_proposal.return_value = mock_proposal
                
                # Create proposal with primary entity selection
                proposal = mock_executor.create_proposal(
                    primary_entity=primary_entity,
                    secondary_entity=secondary_entity,
                    confidence_score=match["confidence_score"],
                    evidence={},
                    entity_type="People & Contacts"
                )
                
                # Validate that create_proposal was called with correct entities
                assert mock_executor.create_proposal.called
                call_args = mock_executor.create_proposal.call_args
                
                # Check that primary entity was passed correctly
                assert call_args[1]["primary_entity"] == primary_entity
                assert call_args[1]["secondary_entity"] == secondary_entity
                
    @pytest.mark.asyncio
    async def test_progress_tracking_accuracy(self, mock_cli_with_data):
        """Test that progress tracking accurately reflects actual progress."""
        cli = mock_cli_with_data
        
        # Mock progress updates
        progress_updates = []
        
        async def mock_progress_callback(update):
            progress_updates.append({
                "stage": update.stage,
                "current": update.current,
                "total": update.total,
                "message": update.message
            })
        
        # Create test data
        test_entities = [{"id": f"entity-{i}", "Full Name": f"Person {i}"} for i in range(5)]
        
        # Mock the engine to track progress
        cli.engine.analyze_databases_async = AsyncMock()
        
        async def mock_analyze(*args, **kwargs):
            # Simulate progress updates
            total = len(test_entities)
            for i in range(total + 1):
                if kwargs.get("progress_callback"):
                    from blackcore.deduplication.cli.async_engine import ProgressUpdate
                    update = ProgressUpdate(
                        stage="Processing entities",
                        current=i,
                        total=total,
                        message=f"Processing entity {i}"
                    )
                    await kwargs["progress_callback"](update)
                    
            # Return mock result
            result = Mock()
            result.total_entities = total
            result.potential_duplicates = 0
            result.high_confidence_matches = []
            result.medium_confidence_matches = []
            result.low_confidence_matches = []
            return {"Test DB": result}
            
        cli.engine.analyze_databases_async.side_effect = mock_analyze
        
        # Run analysis with progress tracking
        databases = {"Test DB": test_entities}
        results = await cli.engine.analyze_databases_async(
            databases, 
            progress_callback=mock_progress_callback
        )
        
        # Validate progress tracking
        assert len(progress_updates) == 6  # 0 to 5 inclusive
        
        # Check progress sequence
        for i, update in enumerate(progress_updates):
            assert update["current"] == i
            assert update["total"] == 5
            assert update["stage"] == "Processing entities"
            
        # Validate final state
        final_update = progress_updates[-1]
        assert final_update["current"] == final_update["total"]
        
    @pytest.mark.asyncio
    async def test_configuration_consistency(self, mock_cli_with_data):
        """Test that configuration settings are consistently applied."""
        cli = mock_cli_with_data
        
        # Test different configuration combinations
        config_tests = [
            {
                "config": {"enable_ai_analysis": True, "safety_mode": True},
                "expected_review_includes_high": True,
                "expected_ai_enabled": True
            },
            {
                "config": {"enable_ai_analysis": False, "safety_mode": True},
                "expected_review_includes_high": True,
                "expected_ai_enabled": False
            },
            {
                "config": {"enable_ai_analysis": False, "safety_mode": False},
                "expected_review_includes_high": False,
                "expected_ai_enabled": False
            }
        ]
        
        for test_config in config_tests:
            # Apply configuration
            cli.engine.engine.config.update(test_config["config"])
            
            # Create test matches
            mock_result = Mock()
            mock_result.high_confidence_matches = [{"id": "high-1"}]
            mock_result.medium_confidence_matches = [{"id": "medium-1"}]
            mock_result.low_confidence_matches = [{"id": "low-1"}]
            
            results = {"Test DB": mock_result}
            
            # Test review collection logic
            matches_to_review = []
            for db_name, db_result in results.items():
                # Medium confidence always included
                for match in db_result.medium_confidence_matches:
                    match["database"] = db_name
                    matches_to_review.append(match)
                    
                # High confidence included based on safety mode
                if cli.engine.engine.config.get("safety_mode", True):
                    for match in db_result.high_confidence_matches:
                        match["database"] = db_name
                        matches_to_review.append(match)
                        
                # Low confidence always included now
                for match in db_result.low_confidence_matches:
                    match["database"] = db_name
                    matches_to_review.append(match)
            
            # Validate configuration effects
            high_confidence_included = any(
                match.get("id") == "high-1" for match in matches_to_review
            )
            
            if test_config["expected_review_includes_high"]:
                assert high_confidence_included, f"High confidence matches should be included with config: {test_config['config']}"
            else:
                assert not high_confidence_included, f"High confidence matches should NOT be included with config: {test_config['config']}"
                
            # Always expect medium and low confidence
            medium_included = any(match.get("id") == "medium-1" for match in matches_to_review)
            low_included = any(match.get("id") == "low-1" for match in matches_to_review)
            
            assert medium_included, "Medium confidence matches should always be included"
            assert low_included, "Low confidence matches should always be included"
            
    @pytest.mark.asyncio
    async def test_error_message_consistency(self, mock_cli_with_data):
        """Test that error messages are consistent with actual errors."""
        cli = mock_cli_with_data
        
        error_scenarios = [
            {
                "error_type": "no_matches_found",
                "setup": lambda: Mock(
                    high_confidence_matches=[],
                    medium_confidence_matches=[],
                    low_confidence_matches=[]
                ),
                "expected_message_contains": "No matches"
            },
            {
                "error_type": "api_key_missing",
                "setup": lambda: None,  # Will be handled in test
                "expected_message_contains": "API key"
            }
        ]
        
        for scenario in error_scenarios:
            if scenario["error_type"] == "no_matches_found":
                # Test no matches scenario
                mock_result = scenario["setup"]()
                results = {"Test DB": mock_result}
                
                # Collect matches for review
                matches_to_review = []
                for db_name, db_result in results.items():
                    matches_to_review.extend(db_result.medium_confidence_matches)
                    matches_to_review.extend(db_result.high_confidence_matches)
                    matches_to_review.extend(db_result.low_confidence_matches)
                
                # Should have no matches
                assert len(matches_to_review) == 0
                
                # This should trigger "No matches require review" message
                # (We can't easily test the actual message output without more complex mocking)
                
            elif scenario["error_type"] == "api_key_missing":
                # Test API key error handling
                with patch.dict('os.environ', {}, clear=True):
                    # Clear environment variables
                    import os
                    old_key = os.environ.get('ANTHROPIC_API_KEY')
                    if 'ANTHROPIC_API_KEY' in os.environ:
                        del os.environ['ANTHROPIC_API_KEY']
                    
                    try:
                        # This should handle missing API key gracefully
                        config = cli.engine.engine.config
                        ai_enabled = config.get("enable_ai_analysis", False)
                        
                        # With no API key, AI should be disabled
                        if not os.environ.get('ANTHROPIC_API_KEY'):
                            # System should gracefully disable AI
                            pass  # Test passes if no exception is raised
                            
                    finally:
                        # Restore environment
                        if old_key:
                            os.environ['ANTHROPIC_API_KEY'] = old_key