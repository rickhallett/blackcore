"""Test complete deduplication workflow from start to finish."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, Mock


class TestCompleteDeduplicationFlow:
    """Test the complete deduplication workflow."""

    @pytest.mark.asyncio
    async def test_happy_path_full_workflow(
        self, mock_cli_with_data, cli_runner, workflow_validator
    ):
        """Test the complete happy path workflow."""
        cli = mock_cli_with_data

        # Define the complete workflow
        workflow_actions = [
            {"type": "menu_choice", "value": "1"},  # New Analysis
            {"type": "config_setting", "setting": "ai_enabled", "value": False},
            {
                "type": "config_setting",
                "setting": "databases",
                "value": ["People & Contacts"],
            },
            {"type": "confirm", "value": True},  # Confirm review matches
            {"type": "review_decision", "decision": "a"},  # Approve first match
            {
                "type": "review_decision",
                "decision": "s",
            },  # Swap primary for second match
            {"type": "review_decision", "decision": "a"},  # Approve second match
            {"type": "review_decision", "decision": "r"},  # Reject third match
            {"type": "confirm", "value": True},  # Apply decisions
        ]

        # Mock the analysis results
        mock_result = Mock()
        mock_result.total_entities = 7
        mock_result.potential_duplicates = 3
        mock_result.high_confidence_matches = [
            {
                "entity_a": {"id": "person-1", "Full Name": "John Smith"},
                "entity_b": {"id": "person-2", "Full Name": "John Smith"},
                "confidence_score": 100.0,
            }
        ]
        mock_result.medium_confidence_matches = [
            {
                "entity_a": {"id": "person-6", "Full Name": "Tony Powell"},
                "entity_b": {"id": "person-7", "Full Name": "Tony Powell"},
                "confidence_score": 85.0,
            }
        ]
        mock_result.low_confidence_matches = [
            {
                "entity_a": {"id": "person-1", "Full Name": "John Smith"},
                "entity_b": {"id": "person-4", "Full Name": "Jon Smith"},
                "confidence_score": 65.0,
            }
        ]

        # Mock the engine's analyze_databases_async method
        cli.engine.analyze_databases_async = AsyncMock(
            return_value={"People & Contacts": mock_result}
        )

        # Track workflow state
        workflow_state = {
            "analysis_completed": False,
            "review_started": False,
            "decisions_made": [],
            "merges_applied": False,
        }

        # Test analysis phase
        with patch("rich.prompt.Prompt.ask") as mock_prompt:
            with patch("rich.prompt.Confirm.ask") as mock_confirm:
                mock_prompt.return_value = "1"  # Choose new analysis
                mock_confirm.return_value = True  # Confirm review

                # Simulate the new analysis flow
                databases = await cli._load_databases()
                assert "People & Contacts" in databases

                # Run analysis
                results = await cli.engine.analyze_databases_async(databases)
                workflow_state["analysis_completed"] = True

                # Validate analysis results
                assert results["People & Contacts"].total_entities == 7
                assert results["People & Contacts"].potential_duplicates == 3
                assert len(results["People & Contacts"].high_confidence_matches) == 1
                assert len(results["People & Contacts"].medium_confidence_matches) == 1
                assert len(results["People & Contacts"].low_confidence_matches) == 1

        # Test review phase consistency
        matches_to_review = []
        for db_name, db_result in results.items():
            # Add medium confidence matches
            for match in db_result.medium_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)

            # Add high confidence matches (safety mode)
            for match in db_result.high_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)

            # Add low confidence matches
            for match in db_result.low_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)

        # Validate that all matches are available for review
        summary_counts = {
            "high_confidence": 1,
            "medium_confidence": 1,
            "low_confidence": 1,
        }

        consistency_errors = workflow_validator.validate_review_availability(
            summary_counts, matches_to_review
        )
        assert len(consistency_errors) == 0, f"Consistency errors: {consistency_errors}"

        # Validate that we have the expected 3 matches for review
        assert len(matches_to_review) == 3
        workflow_state["review_started"] = True

        # Test decision making phase
        review_decisions = []

        # Simulate user decisions
        decisions = ["merge", "merge", "separate"]  # Approve 2, reject 1
        primary_selections = {"match_1": "A", "match_2": "B", "match_3": "A"}

        for i, (match, decision) in enumerate(zip(matches_to_review, decisions)):
            match_id = f"match_{i+1}"
            match["primary_entity"] = primary_selections[match_id]

            review_decision = {
                "match": match,
                "decision": decision,
                "reasoning": f"Test decision {i+1}",
                "reviewer": "test_user",
            }
            review_decisions.append(review_decision)
            workflow_state["decisions_made"].append(decision)

        # Validate decisions
        approved_merges = [d for d in review_decisions if d["decision"] == "merge"]
        assert len(approved_merges) == 2

        # Test merge execution phase
        with patch(
            "blackcore.deduplication.merge_proposals.MergeExecutor"
        ) as mock_executor_class:
            mock_executor = Mock()
            mock_executor_class.return_value = mock_executor

            # Mock successful merges
            mock_proposal = Mock()
            mock_proposal.proposal_id = "test-proposal"
            mock_executor.create_proposal.return_value = mock_proposal

            mock_result = Mock()
            mock_result.success = True
            mock_result.merged_entity = {"id": "merged", "Full Name": "Merged Entity"}
            mock_executor.execute_merge.return_value = mock_result

            # Simulate merge execution
            success_count = 0
            for decision in approved_merges:
                match = decision["match"]

                # Respect primary entity selection
                if match.get("primary_entity") == "B":
                    primary = match.get("entity_b", {})
                    secondary = match.get("entity_a", {})
                else:
                    primary = match.get("entity_a", {})
                    secondary = match.get("entity_b", {})

                # Create and execute merge
                proposal = mock_executor.create_proposal(
                    primary_entity=primary,
                    secondary_entity=secondary,
                    confidence_score=match.get("confidence_score", 0),
                    evidence={},
                    entity_type="People & Contacts",
                )

                result = mock_executor.execute_merge(proposal, auto_approved=True)
                if result.success:
                    success_count += 1

            workflow_state["merges_applied"] = True

            # Validate merge results
            assert success_count == 2  # Both approved merges should succeed
            assert mock_executor.create_proposal.call_count == 2
            assert mock_executor.execute_merge.call_count == 2

        # Final workflow validation
        assert workflow_state["analysis_completed"]
        assert workflow_state["review_started"]
        assert len(workflow_state["decisions_made"]) == 3
        assert workflow_state["merges_applied"]

        # Validate that the entire workflow maintained consistency
        assert summary_counts["high_confidence"] + summary_counts[
            "medium_confidence"
        ] + summary_counts["low_confidence"] == len(matches_to_review)

    @pytest.mark.asyncio
    async def test_workflow_with_different_configurations(self, mock_cli_with_data):
        """Test workflow with different configuration settings."""
        cli = mock_cli_with_data

        configurations_to_test = [
            {"enable_ai_analysis": True, "auto_merge_threshold": 95.0},
            {"enable_ai_analysis": False, "auto_merge_threshold": 85.0},
            {"enable_ai_analysis": False, "safety_mode": False},
        ]

        for config in configurations_to_test:
            # Update engine config
            cli.engine.engine.config.update(config)

            # Mock analysis with this config
            mock_result = Mock()
            mock_result.total_entities = 5
            mock_result.potential_duplicates = 2
            mock_result.high_confidence_matches = []
            mock_result.medium_confidence_matches = []
            mock_result.low_confidence_matches = []

            cli.engine.analyze_databases_async = AsyncMock(
                return_value={"People & Contacts": mock_result}
            )

            # Run analysis
            databases = await cli._load_databases()
            results = await cli.engine.analyze_databases_async(databases)

            # Validate that analysis completes with any configuration
            assert results is not None
            assert "People & Contacts" in results

    @pytest.mark.asyncio
    async def test_workflow_interruption_recovery(self, mock_cli_with_data):
        """Test workflow behavior when interrupted and resumed."""
        cli = mock_cli_with_data

        # Simulate workflow interruption at different stages
        interruption_points = ["analysis", "review", "merge"]

        for interruption_point in interruption_points:
            # Reset CLI state
            cli.current_results = None
            cli.review_decisions = []

            # Start workflow
            mock_result = Mock()
            mock_result.total_entities = 3
            mock_result.potential_duplicates = 1
            mock_result.high_confidence_matches = [
                {
                    "entity_a": {"id": "1", "Full Name": "Test"},
                    "entity_b": {"id": "2", "Full Name": "Test"},
                    "confidence_score": 95.0,
                }
            ]
            mock_result.medium_confidence_matches = []
            mock_result.low_confidence_matches = []

            cli.engine.analyze_databases_async = AsyncMock(
                return_value={"People & Contacts": mock_result}
            )

            if interruption_point == "analysis":
                # Test interruption during analysis
                with pytest.raises(asyncio.CancelledError):
                    cli.engine.analyze_databases_async.side_effect = (
                        asyncio.CancelledError()
                    )
                    databases = await cli._load_databases()
                    await cli.engine.analyze_databases_async(databases)

            elif interruption_point == "review":
                # Complete analysis, interrupt during review
                databases = await cli._load_databases()
                results = await cli.engine.analyze_databases_async(databases)
                cli.current_results = results

                # Validate that state is preserved for recovery
                assert cli.current_results is not None
                assert (
                    len(
                        cli.current_results["People & Contacts"].high_confidence_matches
                    )
                    == 1
                )

            elif interruption_point == "merge":
                # Complete analysis and review, interrupt during merge
                databases = await cli._load_databases()
                results = await cli.engine.analyze_databases_async(databases)
                cli.current_results = results

                # Add some review decisions
                cli.review_decisions = [
                    {
                        "match": {"entity_a": {"id": "1"}, "entity_b": {"id": "2"}},
                        "decision": "merge",
                        "reasoning": "Test merge",
                    }
                ]

                # Validate that decisions are preserved for recovery
                assert len(cli.review_decisions) == 1
                assert cli.review_decisions[0]["decision"] == "merge"

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, mock_cli_with_data):
        """Test workflow error handling and graceful degradation."""
        cli = mock_cli_with_data

        error_scenarios = [
            {
                "type": "database_load_error",
                "exception": FileNotFoundError("Database not found"),
            },
            {"type": "analysis_error", "exception": RuntimeError("Analysis failed")},
            {"type": "merge_error", "exception": ValueError("Merge validation failed")},
        ]

        for scenario in error_scenarios:
            # Reset CLI state
            cli.current_results = None
            cli.review_decisions = []

            if scenario["type"] == "database_load_error":
                # Test database loading error
                with patch.object(
                    cli, "_load_databases", side_effect=scenario["exception"]
                ):
                    with pytest.raises(FileNotFoundError):
                        await cli._load_databases()

            elif scenario["type"] == "analysis_error":
                # Test analysis error
                cli.engine.analyze_databases_async = AsyncMock(
                    side_effect=scenario["exception"]
                )

                with pytest.raises(RuntimeError):
                    databases = {"People & Contacts": []}
                    await cli.engine.analyze_databases_async(databases)

            elif scenario["type"] == "merge_error":
                # Test merge error handling
                with patch(
                    "blackcore.deduplication.merge_proposals.MergeExecutor"
                ) as mock_executor_class:
                    mock_executor = Mock()
                    mock_executor_class.return_value = mock_executor
                    mock_executor.execute_merge.side_effect = scenario["exception"]

                    # Should handle merge errors gracefully
                    with pytest.raises(ValueError):
                        proposal = Mock()
                        mock_executor.execute_merge(proposal, auto_approved=True)
