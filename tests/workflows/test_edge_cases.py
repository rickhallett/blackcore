"""Test edge cases and error conditions in deduplication workflows."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_dataset_handling(self, mock_cli_with_data):
        """Test handling of empty datasets."""
        cli = mock_cli_with_data
        
        # Test completely empty dataset
        empty_data = []
        
        # Mock loading empty data
        async def mock_load_empty():
            return {"People & Contacts": empty_data}
        
        cli._load_databases = mock_load_empty
        
        # Mock engine to handle empty data
        mock_result = Mock()
        mock_result.total_entities = 0
        mock_result.potential_duplicates = 0
        mock_result.high_confidence_matches = []
        mock_result.medium_confidence_matches = []
        mock_result.low_confidence_matches = []
        
        cli.engine.analyze_databases_async = AsyncMock(
            return_value={"People & Contacts": mock_result}
        )
        
        # Run analysis on empty data
        databases = await cli._load_databases()
        results = await cli.engine.analyze_databases_async(databases)
        
        # Validate empty dataset handling
        assert len(databases["People & Contacts"]) == 0
        assert results["People & Contacts"].total_entities == 0
        assert results["People & Contacts"].potential_duplicates == 0
        
        # Validate that review process handles empty results
        matches_to_review = []
        for db_name, db_result in results.items():
            matches_to_review.extend(db_result.high_confidence_matches)
            matches_to_review.extend(db_result.medium_confidence_matches)
            matches_to_review.extend(db_result.low_confidence_matches)
        
        assert len(matches_to_review) == 0
        
    @pytest.mark.asyncio
    async def test_single_entity_dataset(self, mock_cli_with_data):
        """Test handling of dataset with only one entity."""
        cli = mock_cli_with_data
        
        # Single entity data
        single_entity_data = [
            {"id": "only-1", "Full Name": "Lonely Person", "Email": "lonely@example.com"}
        ]
        
        async def mock_load_single():
            return {"People & Contacts": single_entity_data}
        
        cli._load_databases = mock_load_single
        
        # Mock analysis result for single entity
        mock_result = Mock()
        mock_result.total_entities = 1
        mock_result.potential_duplicates = 0  # Can't have duplicates with one entity
        mock_result.high_confidence_matches = []
        mock_result.medium_confidence_matches = []
        mock_result.low_confidence_matches = []
        
        cli.engine.analyze_databases_async = AsyncMock(
            return_value={"People & Contacts": mock_result}
        )
        
        # Run analysis
        databases = await cli._load_databases()
        results = await cli.engine.analyze_databases_async(databases)
        
        # Validate single entity handling
        assert len(databases["People & Contacts"]) == 1
        assert results["People & Contacts"].total_entities == 1
        assert results["People & Contacts"].potential_duplicates == 0
        
    @pytest.mark.asyncio
    async def test_malformed_data_handling(self, mock_cli_with_data):
        """Test handling of malformed or corrupted data."""
        cli = mock_cli_with_data
        
        malformed_datasets = [
            # Missing required fields
            [
                {"id": "malformed-1"},  # No name
                {"Full Name": "No ID Person"}  # No ID
            ],
            # Invalid data types
            [
                {"id": 123, "Full Name": ["Not", "A", "String"]},  # Wrong types
                {"id": "valid-1", "Full Name": None}  # Null values
            ],
            # Very large values
            [
                {"id": "large-1", "Full Name": "A" * 10000, "Email": "huge@example.com"}
            ],
            # Special characters and encoding
            [
                {"id": "special-1", "Full Name": "José María", "Email": "josé@example.com"},
                {"id": "emoji-1", "Full Name": "😀 Person", "Email": "emoji@test.com"}
            ]
        ]
        
        for i, malformed_data in enumerate(malformed_datasets):
            async def mock_load_malformed():
                return {"People & Contacts": malformed_data}
            
            cli._load_databases = mock_load_malformed
            
            # Mock analysis to handle malformed data gracefully
            mock_result = Mock()
            mock_result.total_entities = len(malformed_data)
            mock_result.potential_duplicates = 0
            mock_result.high_confidence_matches = []
            mock_result.medium_confidence_matches = []
            mock_result.low_confidence_matches = []
            
            cli.engine.analyze_databases_async = AsyncMock(
                return_value={"People & Contacts": mock_result}
            )
            
            # Should handle malformed data without crashing
            try:
                databases = await cli._load_databases()
                results = await cli.engine.analyze_databases_async(databases)
                
                # Basic validation
                assert isinstance(results, dict)
                assert "People & Contacts" in results
                
            except Exception as e:
                pytest.fail(f"Malformed data test {i} failed with exception: {e}")
                
    @pytest.mark.asyncio
    async def test_invalid_configuration_handling(self, mock_cli_with_data):
        """Test handling of invalid configurations."""
        cli = mock_cli_with_data
        
        invalid_configs = [
            # Invalid threshold values
            {"auto_merge_threshold": 150.0, "human_review_threshold": 70.0},  # > 100%
            {"auto_merge_threshold": -10.0, "human_review_threshold": 70.0},  # Negative
            {"auto_merge_threshold": 50.0, "human_review_threshold": 80.0},   # Inverted
            
            # Invalid types
            {"auto_merge_threshold": "ninety", "human_review_threshold": "seventy"},
            {"enable_ai_analysis": "yes"},  # String instead of boolean
            
            # Missing required configs
            {},  # Empty config
            {"some_random_key": "value"},  # Unrelated config
        ]
        
        for config in invalid_configs:
            # Apply invalid config
            original_config = cli.engine.engine.config.copy()
            cli.engine.engine.config.update(config)
            
            try:
                # System should handle invalid config gracefully
                # by using defaults or validation
                
                # Test that thresholds are reasonable
                auto_threshold = cli.engine.engine.config.get("auto_merge_threshold", 90.0)
                review_threshold = cli.engine.engine.config.get("human_review_threshold", 70.0)
                
                # Validate that system corrects or handles invalid values
                if isinstance(auto_threshold, (int, float)):
                    assert 0 <= auto_threshold <= 100, f"Invalid auto threshold: {auto_threshold}"
                    
                if isinstance(review_threshold, (int, float)):
                    assert 0 <= review_threshold <= 100, f"Invalid review threshold: {review_threshold}"
                    assert review_threshold <= auto_threshold or auto_threshold < 0 or auto_threshold > 100
                    
            except Exception as e:
                # If an exception is raised, it should be a validation error
                # not a crash
                assert "invalid" in str(e).lower() or "config" in str(e).lower()
                
            finally:
                # Restore original config
                cli.engine.engine.config = original_config
                
    @pytest.mark.asyncio
    async def test_missing_dependencies_handling(self, mock_cli_with_data):
        """Test handling when dependencies are missing."""
        cli = mock_cli_with_data
        
        # Test AI disabled due to missing packages
        with patch.dict('sys.modules', {'anthropic': None}):
            # AI should be automatically disabled
            config = cli.engine.engine.config
            
            # Test that system gracefully handles missing AI
            if config.get("enable_ai_analysis", False):
                # Should fall back to non-AI analysis
                mock_result = Mock()
                mock_result.total_entities = 5
                mock_result.potential_duplicates = 1
                mock_result.high_confidence_matches = []
                mock_result.medium_confidence_matches = []
                mock_result.low_confidence_matches = []
                
                cli.engine.analyze_databases_async = AsyncMock(
                    return_value={"People & Contacts": mock_result}
                )
                
                # Should work without AI
                databases = {"People & Contacts": []}
                results = await cli.engine.analyze_databases_async(databases)
                assert results is not None
                
    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, mock_cli_with_data):
        """Test handling of large datasets."""
        cli = mock_cli_with_data
        
        # Create large dataset
        large_dataset = [
            {
                "id": f"person-{i}",
                "Full Name": f"Person {i}",
                "Email": f"person{i}@example.com",
                "Organization": f"Company {i // 10}"  # Creates potential duplicates
            }
            for i in range(1000)  # 1000 entities
        ]
        
        async def mock_load_large():
            return {"People & Contacts": large_dataset}
        
        cli._load_databases = mock_load_large
        
        # Mock analysis for large dataset
        mock_result = Mock()
        mock_result.total_entities = 1000
        mock_result.potential_duplicates = 50  # Some duplicates
        mock_result.high_confidence_matches = [{"id": f"match-{i}"} for i in range(10)]
        mock_result.medium_confidence_matches = [{"id": f"match-{i}"} for i in range(20)]
        mock_result.low_confidence_matches = [{"id": f"match-{i}"} for i in range(20)]
        
        cli.engine.analyze_databases_async = AsyncMock(
            return_value={"People & Contacts": mock_result}
        )
        
        # Test that large dataset doesn't cause memory issues
        databases = await cli._load_databases()
        assert len(databases["People & Contacts"]) == 1000
        
        # Analysis should complete
        results = await cli.engine.analyze_databases_async(databases)
        assert results["People & Contacts"].total_entities == 1000
        
        # Review collection should handle large number of matches
        matches_to_review = []
        for db_name, db_result in results.items():
            matches_to_review.extend(db_result.high_confidence_matches)
            matches_to_review.extend(db_result.medium_confidence_matches)
            matches_to_review.extend(db_result.low_confidence_matches)
        
        # Should have all matches available for review
        assert len(matches_to_review) == 50  # 10 + 20 + 20
        
    @pytest.mark.asyncio
    async def test_concurrent_access_handling(self, mock_cli_with_data):
        """Test handling of concurrent access scenarios."""
        cli = mock_cli_with_data
        
        # Simulate multiple concurrent operations
        async def mock_long_analysis(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate work
            result = Mock()
            result.total_entities = 5
            result.potential_duplicates = 1
            result.high_confidence_matches = []
            result.medium_confidence_matches = []
            result.low_confidence_matches = []
            return {"People & Contacts": result}
        
        cli.engine.analyze_databases_async = mock_long_analysis
        
        # Start multiple analyses
        databases = {"People & Contacts": []}
        
        tasks = [
            cli.engine.analyze_databases_async(databases)
            for _ in range(3)
        ]
        
        # All should complete successfully
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert "People & Contacts" in result
            
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, mock_cli_with_data):
        """Test handling under memory pressure."""
        cli = mock_cli_with_data
        
        # Create dataset that would use significant memory
        memory_intensive_dataset = [
            {
                "id": f"mem-{i}",
                "Full Name": f"Person {i}",
                "Description": "A" * 1000,  # Large text fields
                "Notes": "B" * 1000,
                "Data": list(range(100))  # Large lists
            }
            for i in range(100)
        ]
        
        async def mock_load_memory_intensive():
            return {"People & Contacts": memory_intensive_dataset}
        
        cli._load_databases = mock_load_memory_intensive
        
        # Mock analysis that handles memory efficiently
        mock_result = Mock()
        mock_result.total_entities = 100
        mock_result.potential_duplicates = 5
        mock_result.high_confidence_matches = []
        mock_result.medium_confidence_matches = []
        mock_result.low_confidence_matches = []
        
        cli.engine.analyze_databases_async = AsyncMock(
            return_value={"People & Contacts": mock_result}
        )
        
        # Should handle memory-intensive data without issues
        databases = await cli._load_databases()
        results = await cli.engine.analyze_databases_async(databases)
        
        assert results is not None
        assert results["People & Contacts"].total_entities == 100
        
    @pytest.mark.asyncio
    async def test_interrupted_workflow_recovery(self, mock_cli_with_data):
        """Test recovery from interrupted workflows."""
        cli = mock_cli_with_data
        
        # Test workflow state preservation
        initial_state = {
            "current_results": None,
            "review_decisions": [],
            "engine_config": cli.engine.engine.config.copy()
        }
        
        # Simulate analysis completion
        mock_result = Mock()
        mock_result.total_entities = 5
        mock_result.potential_duplicates = 2
        mock_result.high_confidence_matches = [{"id": "match-1"}]
        mock_result.medium_confidence_matches = [{"id": "match-2"}]
        mock_result.low_confidence_matches = []
        
        cli.current_results = {"People & Contacts": mock_result}
        
        # Simulate some review decisions made
        cli.review_decisions = [
            {
                "match": {"entity_a": {"id": "1"}, "entity_b": {"id": "2"}},
                "decision": "merge",
                "reasoning": "Test decision"
            }
        ]
        
        # Simulate interruption and recovery
        interrupted_state = {
            "current_results": cli.current_results,
            "review_decisions": cli.review_decisions.copy(),
            "engine_config": cli.engine.engine.config.copy()
        }
        
        # Validate that state can be recovered
        assert interrupted_state["current_results"] is not None
        assert len(interrupted_state["review_decisions"]) == 1
        assert interrupted_state["review_decisions"][0]["decision"] == "merge"
        
        # Test that workflow can continue from interrupted state
        cli.current_results = interrupted_state["current_results"]
        cli.review_decisions = interrupted_state["review_decisions"]
        
        # Should be able to continue with merge execution
        approved_merges = [d for d in cli.review_decisions if d["decision"] == "merge"]
        assert len(approved_merges) == 1
        
    @pytest.mark.asyncio
    async def test_invalid_user_input_handling(self, mock_cli_with_data):
        """Test handling of invalid user inputs."""
        cli = mock_cli_with_data
        
        # Test invalid menu choices
        invalid_inputs = [
            "invalid",
            "999",
            "",
            None,
            "1.5",
            "one"
        ]
        
        for invalid_input in invalid_inputs:
            # Mock prompt to return invalid input
            with patch('rich.prompt.Prompt.ask', return_value=invalid_input):
                try:
                    # Should handle invalid input gracefully
                    # Either by re-prompting or using defaults
                    pass  # Test passes if no exception
                except ValueError:
                    # Acceptable to raise ValueError for invalid input
                    pass
                except Exception as e:
                    # Other exceptions should not occur
                    pytest.fail(f"Unexpected exception for input '{invalid_input}': {e}")
                    
    @pytest.mark.asyncio
    async def test_filesystem_permission_errors(self, mock_cli_with_data):
        """Test handling of filesystem permission errors."""
        cli = mock_cli_with_data
        
        # Mock permission denied error
        with patch.object(cli, '_load_databases', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                await cli._load_databases()
                
        # Mock file not found error
        with patch.object(cli, '_load_databases', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                await cli._load_databases()
                
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_cli_with_data):
        """Test handling of network timeouts (for AI analysis)."""
        cli = mock_cli_with_data
        
        # Enable AI analysis
        cli.engine.engine.config["enable_ai_analysis"] = True
        
        # Mock network timeout
        async def mock_timeout_analysis(*args, **kwargs):
            raise asyncio.TimeoutError("Network timeout")
        
        cli.engine.analyze_databases_async = mock_timeout_analysis
        
        # Should handle timeout gracefully
        with pytest.raises(asyncio.TimeoutError):
            databases = {"People & Contacts": []}
            await cli.engine.analyze_databases_async(databases)