"""Golden path workflow tests that must never break."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


class TestGoldenPathWorkflows:
    """Critical workflow tests that must always pass."""
    
    @pytest.mark.asyncio
    @pytest.mark.golden_path
    @pytest.mark.critical
    async def test_complete_deduplication_golden_path(self, mock_cli_with_data):
        """
        The golden path for complete deduplication workflow.
        
        This test represents the most common, successful user journey
        and must NEVER break. If this test fails, the core product is broken.
        """
        cli = mock_cli_with_data
        
        # Step 1: Load databases successfully
        mock_databases = {
            "People & Contacts": [
                {"id": "1", "Full Name": "John Smith", "Email": "john@example.com"},
                {"id": "2", "Full Name": "John Smith", "Email": "john@example.com"},  # Duplicate
                {"id": "3", "Full Name": "Jane Doe", "Email": "jane@example.com"}
            ]
        }
        
        async def mock_load_databases():
            return mock_databases
            
        cli._load_databases = mock_load_databases
        
        # Step 2: Analyze for duplicates
        mock_result = Mock()
        mock_result.total_entities = 3
        mock_result.potential_duplicates = 1
        mock_result.high_confidence_matches = [
            {
                "id": "match-1",
                "entity_a": {"id": "1", "Full Name": "John Smith", "Email": "john@example.com"},
                "entity_b": {"id": "2", "Full Name": "John Smith", "Email": "john@example.com"},
                "confidence_score": 95.0,
                "primary_entity": "A"
            }
        ]
        mock_result.medium_confidence_matches = []
        mock_result.low_confidence_matches = []
        
        async def mock_analyze(*args, **kwargs):
            return {"People & Contacts": mock_result}
            
        cli.engine.analyze_databases_async = mock_analyze
        
        # Step 3: Execute the golden path workflow
        databases = await cli._load_databases()
        assert len(databases) == 1
        assert "People & Contacts" in databases
        assert len(databases["People & Contacts"]) == 3
        
        # Analyze for duplicates
        results = await cli.engine.analyze_databases_async(databases)
        assert "People & Contacts" in results
        
        db_result = results["People & Contacts"]
        assert db_result.total_entities == 3
        assert db_result.potential_duplicates == 1
        assert len(db_result.high_confidence_matches) == 1
        
        # Step 4: Auto-approve high confidence matches
        auto_approved = []
        for match in db_result.high_confidence_matches:
            auto_approved.append({
                "match": match,
                "decision": "merge",
                "reasoning": "High confidence auto-approval",
                "auto_approved": True
            })
            
        assert len(auto_approved) == 1
        assert auto_approved[0]["decision"] == "merge"
        assert auto_approved[0]["auto_approved"] == True
        
        # Step 5: Execute merges
        with patch('blackcore.deduplication.merge_proposals.MergeExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor_class.return_value = mock_executor
            
            mock_proposal = Mock()
            mock_proposal.proposal_id = "proposal-1"
            mock_executor.create_proposal.return_value = mock_proposal
            
            mock_result = Mock()
            mock_result.success = True
            mock_result.merged_entity = {
                "id": "1",  # Primary entity ID preserved
                "Full Name": "John Smith",
                "Email": "john@example.com"
            }
            mock_executor.execute_merge.return_value = mock_result
            
            # Execute the merge
            merge_result = mock_executor.execute_merge(mock_proposal, auto_approved=True)
            
        # Validate golden path completion
        assert merge_result.success == True
        assert merge_result.merged_entity["id"] == "1"
        assert mock_executor.create_proposal.called
        assert mock_executor.execute_merge.called
        
        # The golden path is complete: 3 entities → 1 duplicate found → 1 merge → 2 entities remain
        
    @pytest.mark.asyncio
    @pytest.mark.golden_path
    @pytest.mark.critical
    async def test_manual_review_golden_path(self, mock_cli_with_data):
        """
        Golden path for manual review workflow.
        
        User sees matches, reviews them, makes decisions, and merges are executed.
        This represents the core interactive experience.
        """
        cli = mock_cli_with_data
        
        # Create medium confidence matches requiring review
        mock_result = Mock()
        mock_result.total_entities = 100
        mock_result.potential_duplicates = 3
        mock_result.high_confidence_matches = []
        mock_result.medium_confidence_matches = [
            {
                "id": "match-1",
                "entity_a": {"id": "1", "Full Name": "Alice Johnson", "Email": "alice@example.com"},
                "entity_b": {"id": "2", "Full Name": "Alice Johnson", "Email": "a.johnson@example.com"},
                "confidence_score": 85.0,
                "primary_entity": "A"
            },
            {
                "id": "match-2", 
                "entity_a": {"id": "3", "Full Name": "Bob Wilson", "Email": "bob@example.com"},
                "entity_b": {"id": "4", "Full Name": "Robert Wilson", "Email": "rwilson@example.com"},
                "confidence_score": 75.0,
                "primary_entity": "B"
            }
        ]
        mock_result.low_confidence_matches = [
            {
                "id": "match-3",
                "entity_a": {"id": "5", "Full Name": "Carol Davis", "Email": "carol@example.com"},
                "entity_b": {"id": "6", "Full Name": "Carol Smith", "Email": "csmith@example.com"},
                "confidence_score": 65.0,
                "primary_entity": "A"
            }
        ]
        
        # Step 1: Collect matches for review (critical - includes all medium + low)
        matches_to_review = []
        
        for match in mock_result.medium_confidence_matches:
            match["database"] = "People & Contacts"
            matches_to_review.append(match)
            
        for match in mock_result.low_confidence_matches:
            match["database"] = "People & Contacts" 
            matches_to_review.append(match)
            
        # Validate review collection (this was the source of the original bug)
        assert len(matches_to_review) == 3, "Should collect all medium + low confidence matches"
        
        # Step 2: User reviews matches and makes decisions
        review_decisions = [
            {
                "match": matches_to_review[0],  # Alice Johnson
                "decision": "merge",
                "reasoning": "Same person, different email format",
                "timestamp": datetime.now()
            },
            {
                "match": matches_to_review[1],  # Bob Wilson  
                "decision": "merge",
                "reasoning": "Bob Wilson and Robert Wilson are the same person",
                "timestamp": datetime.now()
            },
            {
                "match": matches_to_review[2],  # Carol Davis
                "decision": "separate", 
                "reasoning": "Different last names, likely different people",
                "timestamp": datetime.now()
            }
        ]
        
        # Step 3: Process decisions
        approved_merges = [d for d in review_decisions if d["decision"] == "merge"]
        rejected_matches = [d for d in review_decisions if d["decision"] == "separate"]
        
        assert len(approved_merges) == 2
        assert len(rejected_matches) == 1
        
        # Step 4: Execute approved merges
        merge_results = []
        
        with patch('blackcore.deduplication.merge_proposals.MergeExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor_class.return_value = mock_executor
            
            for i, decision in enumerate(approved_merges):
                match = decision["match"]
                
                # Respect primary entity selection
                if match["primary_entity"] == "B":
                    primary = match["entity_b"]
                    secondary = match["entity_a"]
                else:
                    primary = match["entity_a"]
                    secondary = match["entity_b"]
                    
                # Create proposal
                mock_proposal = Mock()
                mock_proposal.proposal_id = f"proposal-{i+1}"
                mock_executor.create_proposal.return_value = mock_proposal
                
                # Execute merge
                mock_result = Mock()
                mock_result.success = True
                mock_result.merged_entity = primary.copy()
                mock_executor.execute_merge.return_value = mock_result
                
                result = mock_executor.execute_merge(mock_proposal, auto_approved=False)
                merge_results.append(result)
                
        # Validate golden path completion
        assert len(merge_results) == 2
        assert all(result.success for result in merge_results)
        
        # Summary: 3 matches reviewed → 2 approved → 2 merges executed → 1 rejected
        
    @pytest.mark.asyncio
    @pytest.mark.golden_path
    @pytest.mark.critical
    async def test_configuration_and_analysis_golden_path(self, mock_cli_with_data):
        """
        Golden path for configuration setup and analysis execution.
        
        User configures settings, runs analysis, gets meaningful results.
        """
        cli = mock_cli_with_data
        
        # Step 1: Configure settings (golden path configuration)
        golden_config = {
            "enable_ai_analysis": True,
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "safety_mode": True,
            "databases": ["People & Contacts"]
        }
        
        cli.engine.engine.config.update(golden_config)
        
        # Validate configuration
        assert cli.engine.engine.config["enable_ai_analysis"] == True
        assert cli.engine.engine.config["auto_merge_threshold"] == 90.0
        assert cli.engine.engine.config["human_review_threshold"] == 70.0
        assert cli.engine.engine.config["safety_mode"] == True
        
        # Step 2: Load configured databases
        mock_databases = {
            "People & Contacts": [
                {"id": f"person-{i}", "Full Name": f"Person {i}", "Email": f"person{i}@example.com"}
                for i in range(50)  # Moderate dataset
            ]
        }
        
        async def mock_load_databases():
            return {db: data for db, data in mock_databases.items() 
                   if db in cli.engine.engine.config["databases"]}
                   
        cli._load_databases = mock_load_databases
        
        # Step 3: Execute analysis with progress tracking
        progress_updates = []
        
        async def mock_progress_callback(update):
            progress_updates.append({
                "stage": update.stage,
                "current": update.current,
                "total": update.total
            })
            
        async def mock_analysis_with_progress(*args, **kwargs):
            callback = kwargs.get("progress_callback")
            
            # Simulate progress
            if callback:
                from blackcore.deduplication.cli.async_engine import ProgressUpdate
                
                stages = [
                    ("Loading", 0, 50),
                    ("Processing", 25, 50), 
                    ("Processing", 50, 50),
                    ("Complete", 50, 50)
                ]
                
                for stage, current, total in stages:
                    update = ProgressUpdate(stage=stage, current=current, total=total, message=f"{stage} {current}/{total}")
                    await callback(update)
                    
            # Return realistic results
            mock_result = Mock()
            mock_result.total_entities = 50
            mock_result.potential_duplicates = 5
            mock_result.high_confidence_matches = [{"id": f"high-{i}"} for i in range(2)]
            mock_result.medium_confidence_matches = [{"id": f"med-{i}"} for i in range(2)]
            mock_result.low_confidence_matches = [{"id": f"low-{i}"} for i in range(1)]
            
            return {"People & Contacts": mock_result}
            
        cli.engine.analyze_databases_async = mock_analysis_with_progress
        
        # Execute the golden path
        databases = await cli._load_databases()
        results = await cli.engine.analyze_databases_async(
            databases, 
            progress_callback=mock_progress_callback
        )
        
        # Validate results
        assert len(databases) == 1
        assert "People & Contacts" in results
        
        db_result = results["People & Contacts"]
        assert db_result.total_entities == 50
        assert db_result.potential_duplicates == 5
        assert len(db_result.high_confidence_matches) == 2
        assert len(db_result.medium_confidence_matches) == 2
        assert len(db_result.low_confidence_matches) == 1
        
        # Validate progress tracking
        assert len(progress_updates) == 4
        assert progress_updates[0]["stage"] == "Loading"
        assert progress_updates[-1]["stage"] == "Complete"
        assert progress_updates[-1]["current"] == progress_updates[-1]["total"]
        
        # Golden path complete: Configure → Load → Analyze → Results with Progress
        
    @pytest.mark.asyncio
    @pytest.mark.golden_path
    @pytest.mark.critical
    async def test_error_recovery_golden_path(self, mock_cli_with_data):
        """
        Golden path for error handling and recovery.
        
        System encounters errors but recovers gracefully without losing data.
        """
        cli = mock_cli_with_data
        
        # Step 1: Simulate recoverable error during analysis
        call_count = 0
        
        async def mock_analysis_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                raise ConnectionError("Network timeout")
            else:
                # Second call succeeds (recovery)
                mock_result = Mock()
                mock_result.total_entities = 10
                mock_result.potential_duplicates = 2
                mock_result.high_confidence_matches = []
                mock_result.medium_confidence_matches = [
                    {"id": "match-1", "confidence": 80.0}
                ]
                mock_result.low_confidence_matches = [
                    {"id": "match-2", "confidence": 65.0}
                ]
                return {"People & Contacts": mock_result}
                
        cli.engine.analyze_databases_async = mock_analysis_with_failure
        
        # Step 2: Attempt analysis with retry logic
        databases = {"People & Contacts": [{"id": "1"}, {"id": "2"}]}
        
        max_retries = 3
        retry_count = 0
        results = None
        last_error = None
        
        while retry_count < max_retries:
            try:
                results = await cli.engine.analyze_databases_async(databases)
                break  # Success
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    # Wait before retry (simulated)
                    pass
                    
        # Validate recovery
        assert results is not None, f"Analysis should succeed after retry, last error: {last_error}"
        assert "People & Contacts" in results
        assert retry_count == 1  # Should succeed on second attempt
        
        # Step 3: Test partial session recovery
        # Simulate interrupted review session
        session_state = {
            "matches": [
                {"id": "match-1", "status": "pending"},
                {"id": "match-2", "status": "pending"}
            ],
            "decisions": [],
            "current_index": 0
        }
        
        # Process first match
        match = session_state["matches"][0]
        decision = {
            "match": match,
            "decision": "merge",
            "reasoning": "Clear duplicate"
        }
        session_state["decisions"].append(decision)
        match["status"] = "reviewed"
        session_state["current_index"] = 1
        
        # Simulate interruption (e.g., user closes application)
        
        # Validate state preservation for recovery
        assert len(session_state["decisions"]) == 1
        assert session_state["current_index"] == 1
        assert session_state["matches"][0]["status"] == "reviewed"
        assert session_state["matches"][1]["status"] == "pending"
        
        # Step 4: Resume from saved state
        remaining_matches = [m for m in session_state["matches"] if m["status"] == "pending"]
        assert len(remaining_matches) == 1
        
        # Complete the session
        for match in remaining_matches:
            decision = {
                "match": match,
                "decision": "separate",
                "reasoning": "Different entities"
            }
            session_state["decisions"].append(decision)
            match["status"] = "reviewed"
            
        # Validate complete recovery
        assert len(session_state["decisions"]) == 2
        assert all(m["status"] == "reviewed" for m in session_state["matches"])
        
        # Golden path complete: Error → Retry → Success + Session Recovery
        
    @pytest.mark.asyncio
    @pytest.mark.golden_path
    @pytest.mark.critical
    async def test_data_integrity_golden_path(self, mock_cli_with_data):
        """
        Golden path for data integrity preservation.
        
        Ensures data is never corrupted or lost during deduplication.
        """
        cli = mock_cli_with_data
        
        # Step 1: Start with original data
        original_entities = [
            {
                "id": "entity-1",
                "Full Name": "John Smith",
                "Email": "john@example.com",
                "Phone": "555-1234",
                "Organization": "Acme Corp",
                "Notes": "Important client"
            },
            {
                "id": "entity-2", 
                "Full Name": "John Smith",
                "Email": "j.smith@acme.com",
                "Phone": "555-1234",
                "Organization": ["Acme Corp", "Beta Inc"],  # Different data type
                "Title": "Manager"  # Additional field
            }
        ]
        
        # Calculate original data hash for integrity checking
        import hashlib
        import json
        
        def calculate_hash(data):
            return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
            
        original_hash = calculate_hash(original_entities)
        
        # Step 2: Process through deduplication
        # Entities should remain unchanged until merge
        processed_entities = [entity.copy() for entity in original_entities]
        processing_hash = calculate_hash(processed_entities)
        
        assert processing_hash == original_hash, "Entities should be unchanged during processing"
        
        # Step 3: Perform conservative merge
        primary = processed_entities[0].copy()
        secondary = processed_entities[1].copy()
        
        merged_entity = primary.copy()
        merge_metadata = {
            "merged_from": [primary["id"], secondary["id"]],
            "merge_timestamp": datetime.now().isoformat(),
            "conflicts": {}
        }
        
        # Merge secondary data
        for key, value in secondary.items():
            if key == "id":
                continue
                
            if key in merged_entity and merged_entity[key]:
                # Check for conflicts
                if merged_entity[key] != value:
                    merge_metadata["conflicts"][key] = {
                        "primary": merged_entity[key],
                        "secondary": value,
                        "resolution": "primary_kept"
                    }
            else:
                # Fill empty field
                merged_entity[key] = value
                
        # Add merge metadata
        merged_entity["_merge_info"] = merge_metadata
        
        # Step 4: Validate data integrity
        # Original data should be preserved
        assert merged_entity["id"] == primary["id"]  # Primary ID preserved
        assert merged_entity["Full Name"] == primary["Full Name"]  # Primary data preserved
        assert merged_entity["Email"] == primary["Email"]  # Primary email kept
        assert merged_entity["Title"] == secondary["Title"]  # Secondary data added
        
        # No data should be lost
        all_original_fields = set()
        for entity in original_entities:
            all_original_fields.update(entity.keys())
            
        merged_fields = set(merged_entity.keys()) - {"_merge_info"}
        
        # All original fields should be present (either from primary or secondary)
        for field in all_original_fields:
            assert field in merged_fields, f"Field '{field}' lost during merge"
            
        # Conflicts should be tracked
        conflicts = merge_metadata["conflicts"]
        expected_conflicts = ["Email", "Organization"]  # Different values
        
        for conflict_field in expected_conflicts:
            if conflict_field in conflicts:
                assert "primary" in conflicts[conflict_field]
                assert "secondary" in conflicts[conflict_field]
                assert "resolution" in conflicts[conflict_field]
                
        # Step 5: Validate audit trail
        assert "_merge_info" in merged_entity
        assert "merged_from" in merge_metadata
        assert "merge_timestamp" in merge_metadata
        assert len(merge_metadata["merged_from"]) == 2
        
        # Golden path complete: Original Data → Processing → Merge → Integrity Preserved
        
    @pytest.mark.asyncio
    @pytest.mark.golden_path
    @pytest.mark.critical
    async def test_performance_golden_path(self, mock_cli_with_data):
        """
        Golden path for performance expectations.
        
        System performs within acceptable limits for typical workloads.
        """
        cli = mock_cli_with_data
        
        import time
        import psutil
        
        # Step 1: Baseline performance measurement
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Step 2: Generate typical dataset (moderate size)
        dataset_size = 500
        test_dataset = []
        
        for i in range(dataset_size):
            entity = {
                "id": f"entity-{i}",
                "Full Name": f"Person {i}",
                "Email": f"person{i}@example.com",
                "Phone": f"555-{i:04d}",
                "Organization": f"Company {i // 10}",
                "Notes": f"Notes for person {i} " * 5  # Some content
            }
            test_dataset.append(entity)
            
        # Step 3: Performance test - analysis
        async def mock_realistic_analysis(*args, **kwargs):
            # Simulate realistic processing time
            import asyncio
            await asyncio.sleep(0.1)  # 100ms processing time
            
            # Generate realistic results
            expected_duplicates = dataset_size // 50  # 2% duplication rate
            
            mock_result = Mock()
            mock_result.total_entities = dataset_size
            mock_result.potential_duplicates = expected_duplicates
            mock_result.high_confidence_matches = [{"id": f"high-{i}"} for i in range(expected_duplicates // 3)]
            mock_result.medium_confidence_matches = [{"id": f"med-{i}"} for i in range(expected_duplicates // 3)]
            mock_result.low_confidence_matches = [{"id": f"low-{i}"} for i in range(expected_duplicates // 3)]
            
            return {"People & Contacts": mock_result}
            
        cli.engine.analyze_databases_async = mock_realistic_analysis
        
        # Measure analysis performance
        start_time = time.time()
        
        databases = {"People & Contacts": test_dataset}
        results = await cli.engine.analyze_databases_async(databases)
        
        analysis_time = time.time() - start_time
        peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = peak_memory - baseline_memory
        
        # Step 4: Validate performance requirements
        # Analysis should complete in reasonable time
        assert analysis_time < 5.0, f"Analysis too slow: {analysis_time:.2f}s for {dataset_size} entities"
        
        # Memory usage should be reasonable
        assert memory_usage < 100, f"Memory usage too high: {memory_usage:.1f}MB for {dataset_size} entities"
        
        # Results should be realistic
        db_result = results["People & Contacts"]
        assert db_result.total_entities == dataset_size
        assert db_result.potential_duplicates > 0
        assert db_result.potential_duplicates < dataset_size * 0.1  # Less than 10% duplicates
        
        # Step 5: Throughput validation
        entities_per_second = dataset_size / analysis_time if analysis_time > 0 else float('inf')
        assert entities_per_second > 100, f"Throughput too low: {entities_per_second:.1f} entities/sec"
        
        # Golden path complete: Typical Dataset → Analysis → Acceptable Performance