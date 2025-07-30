"""Performance tests for large datasets and scalability."""

import pytest
import time
import asyncio
import psutil
import gc
from unittest.mock import Mock, patch
from typing import List, Dict, Any


class TestLargeDatasetPerformance:
    """Test performance with large datasets."""
    
    def generate_large_dataset(self, size: int) -> List[Dict[str, Any]]:
        """Generate a large dataset for testing."""
        dataset = []
        
        # Create varied data to simulate real-world scenarios
        for i in range(size):
            # Create some intentional duplicates (every 50th record)
            base_index = i - (i % 50) if i % 50 == 0 and i > 0 else i
            
            person = {
                "id": f"person-{i}",
                "Full Name": f"Person {base_index}",
                "Email": f"person{base_index}@example.com",
                "Phone": f"555-{base_index:04d}",
                "Organization": f"Company {base_index // 10}",
                "Title": f"Title {base_index % 5}",
                "Department": f"Dept {base_index % 3}",
                "Notes": f"Notes for person {base_index} " * 10,  # Larger text field
                "Skills": [f"Skill {j}" for j in range(base_index % 5)],  # Variable list size
                "Projects": [f"Project {k}" for k in range(base_index % 3)]
            }
            
            # Add some variation for non-duplicates
            if i % 50 != 0:
                person["Full Name"] = f"Person {i}"
                person["Email"] = f"person{i}@example.com"
                
            dataset.append(person)
            
        return dataset
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_dataset_analysis_performance(self, mock_cli_with_data):
        """Test performance with large datasets (1000+ entities)."""
        cli = mock_cli_with_data
        
        # Test different dataset sizes
        dataset_sizes = [100, 500, 1000, 2000]
        performance_results = {}
        
        for size in dataset_sizes:
            # Generate test dataset
            large_dataset = self.generate_large_dataset(size)
            
            # Mock database loading
            async def mock_load_large():
                return {"People & Contacts": large_dataset}
            
            cli._load_databases = mock_load_large
            
            # Mock analysis with realistic results
            expected_duplicates = size // 50  # Every 50th is a duplicate
            mock_result = Mock()
            mock_result.total_entities = size
            mock_result.potential_duplicates = expected_duplicates
            mock_result.high_confidence_matches = [{"id": f"match-{i}"} for i in range(expected_duplicates // 3)]
            mock_result.medium_confidence_matches = [{"id": f"match-{i}"} for i in range(expected_duplicates // 3)]
            mock_result.low_confidence_matches = [{"id": f"match-{i}"} for i in range(expected_duplicates // 3)]
            
            # Monitor performance
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Mock the analysis to simulate processing time
            async def mock_analysis_with_delay(*args, **kwargs):
                # Simulate processing time proportional to dataset size
                await asyncio.sleep(size / 10000)  # Scale delay with size
                return {"People & Contacts": mock_result}
            
            cli.engine.analyze_databases_async = mock_analysis_with_delay
            
            # Run analysis
            databases = await cli._load_databases()
            results = await cli.engine.analyze_databases_async(databases)
            
            # Measure performance
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            processing_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            performance_results[size] = {
                "processing_time": processing_time,
                "memory_usage": memory_usage,
                "entities_per_second": size / processing_time if processing_time > 0 else float('inf'),
                "memory_per_entity": memory_usage / size if size > 0 else 0
            }
            
            # Validate results
            assert results["People & Contacts"].total_entities == size
            assert results["People & Contacts"].potential_duplicates == expected_duplicates
            
            # Performance assertions
            assert processing_time < 10.0, f"Processing time too high for {size} entities: {processing_time}s"
            assert memory_usage < 500, f"Memory usage too high for {size} entities: {memory_usage}MB"
            
            # Force garbage collection
            gc.collect()
            
        # Analyze performance scaling
        for i, size in enumerate(dataset_sizes[1:], 1):
            prev_size = dataset_sizes[i-1]
            
            # Check that performance scales reasonably
            size_ratio = size / prev_size
            time_ratio = performance_results[size]["processing_time"] / performance_results[prev_size]["processing_time"]
            
            # Time should scale sub-linearly (better than O(n²))
            assert time_ratio < size_ratio * 2, \
                f"Performance degradation too severe: {size} entities took {time_ratio:.2f}x longer than {prev_size} entities"
                
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self, mock_cli_with_data):
        """Test memory usage patterns during processing."""
        cli = mock_cli_with_data
        
        # Test dataset
        dataset = self.generate_large_dataset(1000)
        
        async def mock_load_dataset():
            return {"People & Contacts": dataset}
        
        cli._load_databases = mock_load_dataset
        
        # Monitor memory throughout the process
        memory_checkpoints = []
        
        def record_memory(checkpoint_name):
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            memory_checkpoints.append({"checkpoint": checkpoint_name, "memory_mb": memory_mb})
            
        # Baseline memory
        record_memory("baseline")
        
        # Load data
        databases = await cli._load_databases()
        record_memory("after_data_load")
        
        # Mock analysis with memory tracking
        async def mock_memory_aware_analysis(*args, **kwargs):
            record_memory("analysis_start")
            
            # Simulate memory usage during analysis
            # Create temporary data structures
            temp_data = [{"temp": f"data_{i}"} for i in range(len(dataset))]
            record_memory("analysis_peak")
            
            # Clean up temporary data
            del temp_data
            gc.collect()
            record_memory("analysis_cleanup")
            
            # Return results
            mock_result = Mock()
            mock_result.total_entities = len(dataset)
            mock_result.potential_duplicates = 20
            mock_result.high_confidence_matches = []
            mock_result.medium_confidence_matches = []
            mock_result.low_confidence_matches = []
            
            return {"People & Contacts": mock_result}
        
        cli.engine.analyze_databases_async = mock_memory_aware_analysis
        
        # Run analysis
        results = await cli.engine.analyze_databases_async(databases)
        record_memory("analysis_complete")
        
        # Validate memory usage patterns
        baseline_memory = memory_checkpoints[0]["memory_mb"]
        peak_memory = max(checkpoint["memory_mb"] for checkpoint in memory_checkpoints)
        final_memory = memory_checkpoints[-1]["memory_mb"]
        
        # Memory should increase during processing but not excessively
        memory_increase = peak_memory - baseline_memory
        assert memory_increase < 200, f"Memory increase too large: {memory_increase}MB"
        
        # Memory should be cleaned up after processing
        memory_cleanup = peak_memory - final_memory
        assert memory_cleanup > 0, "No memory cleanup detected"
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, mock_cli_with_data):
        """Test performance under concurrent processing."""
        cli = mock_cli_with_data
        
        # Create multiple smaller datasets
        datasets = [
            self.generate_large_dataset(200) for _ in range(5)
        ]
        
        async def create_mock_analysis(dataset_index):
            """Create a mock analysis function for a specific dataset."""
            async def mock_analysis(*args, **kwargs):
                # Simulate processing time
                await asyncio.sleep(0.1)
                
                dataset = datasets[dataset_index]
                mock_result = Mock()
                mock_result.total_entities = len(dataset)
                mock_result.potential_duplicates = len(dataset) // 50
                mock_result.high_confidence_matches = []
                mock_result.medium_confidence_matches = []
                mock_result.low_confidence_matches = []
                
                return {f"Dataset_{dataset_index}": mock_result}
            
            return mock_analysis
        
        # Test concurrent analysis
        start_time = time.time()
        
        # Create concurrent analysis tasks
        tasks = []
        for i in range(len(datasets)):
            mock_cli = Mock()
            mock_cli.engine = Mock()
            mock_cli.engine.analyze_databases_async = await create_mock_analysis(i)
            
            task = mock_cli.engine.analyze_databases_async({f"Dataset_{i}": datasets[i]})
            tasks.append(task)
        
        # Run all analyses concurrently
        results = await asyncio.gather(*tasks)
        
        concurrent_time = time.time() - start_time
        
        # Test sequential analysis for comparison
        start_time = time.time()
        
        for i in range(len(datasets)):
            mock_analysis = await create_mock_analysis(i)
            await mock_analysis({f"Dataset_{i}": datasets[i]})
        
        sequential_time = time.time() - start_time
        
        # Validate concurrent performance
        assert len(results) == len(datasets)
        
        # Concurrent should be faster than sequential
        performance_improvement = sequential_time / concurrent_time
        assert performance_improvement > 1.5, \
            f"Concurrent processing should be faster: {performance_improvement:.2f}x improvement"
            
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_progress_tracking_performance(self, mock_cli_with_data):
        """Test performance impact of progress tracking."""
        cli = mock_cli_with_data
        
        dataset = self.generate_large_dataset(500)
        
        async def mock_load_dataset():
            return {"People & Contacts": dataset}
        
        cli._load_databases = mock_load_dataset
        
        # Test with progress tracking
        progress_updates = []
        
        async def mock_progress_callback(update):
            progress_updates.append({
                "stage": update.stage,
                "current": update.current,
                "total": update.total,
                "timestamp": time.time()
            })
        
        async def mock_analysis_with_progress(*args, **kwargs):
            callback = kwargs.get("progress_callback")
            total = len(dataset)
            
            # Simulate progress updates
            for i in range(0, total + 1, total // 10):  # 10% increments
                if callback:
                    from blackcore.deduplication.cli.async_engine import ProgressUpdate
                    update = ProgressUpdate(
                        stage="Processing",
                        current=min(i, total),
                        total=total,
                        message=f"Processing entity {i}"
                    )
                    await callback(update)
                
                # Simulate some work
                await asyncio.sleep(0.01)
            
            mock_result = Mock()
            mock_result.total_entities = total
            mock_result.potential_duplicates = 10
            mock_result.high_confidence_matches = []
            mock_result.medium_confidence_matches = []
            mock_result.low_confidence_matches = []
            
            return {"People & Contacts": mock_result}
        
        cli.engine.analyze_databases_async = mock_analysis_with_progress
        
        # Run with progress tracking
        start_time = time.time()
        databases = await cli._load_databases()
        results = await cli.engine.analyze_databases_async(
            databases, 
            progress_callback=mock_progress_callback
        )
        progress_time = time.time() - start_time
        
        # Run without progress tracking
        start_time = time.time()
        results_no_progress = await cli.engine.analyze_databases_async(databases)
        no_progress_time = time.time() - start_time
        
        # Validate progress tracking
        assert len(progress_updates) >= 10  # Should have at least 10 updates
        
        # Check progress sequence
        for i, update in enumerate(progress_updates[1:], 1):
            prev_update = progress_updates[i-1]
            assert update["current"] >= prev_update["current"]  # Should be non-decreasing
            
        # Performance impact should be minimal
        overhead = (progress_time - no_progress_time) / no_progress_time if no_progress_time > 0 else 0
        assert overhead < 0.2, f"Progress tracking overhead too high: {overhead:.2%}"
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_match_review_performance(self, mock_cli_with_data):
        """Test performance when reviewing large numbers of matches."""
        cli = mock_cli_with_data
        
        # Create many matches to review
        num_matches = 100
        matches_to_review = []
        
        for i in range(num_matches):
            match = {
                "entity_a": {
                    "id": f"entity-{i*2}",
                    "Full Name": f"Person {i}",
                    "Email": f"person{i}@example.com"
                },
                "entity_b": {
                    "id": f"entity-{i*2+1}",
                    "Full Name": f"Person {i}",
                    "Email": f"person{i}@company.com"
                },
                "confidence_score": 80.0 + (i % 20),  # Vary confidence
                "database": "People & Contacts",
                "primary_entity": "A"
            }
            matches_to_review.append(match)
        
        # Test batch decision processing
        start_time = time.time()
        
        review_decisions = []
        for i, match in enumerate(matches_to_review):
            # Simulate quick decisions for performance test
            decision = "merge" if i % 3 == 0 else "separate"
            
            review_decision = {
                "match": match,
                "decision": decision,
                "reasoning": f"Decision {i}",
                "timestamp": time.time()
            }
            review_decisions.append(review_decision)
        
        decision_time = time.time() - start_time
        
        # Test merge execution performance
        approved_merges = [d for d in review_decisions if d["decision"] == "merge"]
        
        start_time = time.time()
        
        with patch('blackcore.deduplication.merge_proposals.MergeExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor_class.return_value = mock_executor
            
            # Mock fast merge execution
            def mock_create_proposal(*args, **kwargs):
                proposal = Mock()
                proposal.proposal_id = f"proposal-{len(approved_merges)}"
                return proposal
            
            def mock_execute_merge(proposal, auto_approved=False):
                result = Mock()
                result.success = True
                result.merged_entity = {"id": "merged", "Full Name": "Merged"}
                return result
            
            mock_executor.create_proposal.side_effect = mock_create_proposal
            mock_executor.execute_merge.side_effect = mock_execute_merge
            
            # Execute all merges
            for decision in approved_merges:
                match = decision["match"]
                
                proposal = mock_executor.create_proposal(
                    primary_entity=match["entity_a"],
                    secondary_entity=match["entity_b"],
                    confidence_score=match["confidence_score"],
                    evidence={},
                    entity_type="People & Contacts"
                )
                
                result = mock_executor.execute_merge(proposal, auto_approved=True)
        
        merge_time = time.time() - start_time
        
        # Validate performance
        assert len(review_decisions) == num_matches
        assert len(approved_merges) == num_matches // 3  # Every 3rd approved
        
        # Performance benchmarks
        decisions_per_second = num_matches / decision_time if decision_time > 0 else float('inf')
        merges_per_second = len(approved_merges) / merge_time if merge_time > 0 else float('inf')
        
        assert decisions_per_second > 50, f"Decision processing too slow: {decisions_per_second:.1f} decisions/sec"
        assert merges_per_second > 10, f"Merge execution too slow: {merges_per_second:.1f} merges/sec"
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, mock_cli_with_data):
        """Test for memory leaks during repeated operations."""
        cli = mock_cli_with_data
        
        # Baseline memory
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Perform repeated operations
        num_iterations = 10
        memory_samples = []
        
        for iteration in range(num_iterations):
            # Generate fresh dataset each iteration
            dataset = self.generate_large_dataset(100)
            
            async def mock_load_iteration():
                return {"People & Contacts": dataset}
            
            cli._load_databases = mock_load_iteration
            
            # Mock analysis
            async def mock_analysis(*args, **kwargs):
                # Create and destroy temporary objects
                temp_objects = [{"data": f"temp_{i}"} for i in range(1000)]
                
                mock_result = Mock()
                mock_result.total_entities = len(dataset)
                mock_result.potential_duplicates = 2
                mock_result.high_confidence_matches = []
                mock_result.medium_confidence_matches = []
                mock_result.low_confidence_matches = []
                
                # Clean up temp objects
                del temp_objects
                
                return {"People & Contacts": mock_result}
            
            cli.engine.analyze_databases_async = mock_analysis
            
            # Run iteration
            databases = await cli._load_databases()
            results = await cli.engine.analyze_databases_async(databases)
            
            # Force garbage collection
            gc.collect()
            
            # Sample memory
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
        # Analyze memory trend
        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory
        
        # Calculate trend (should be stable or slightly increasing)
        if len(memory_samples) > 5:
            # Check if memory keeps growing significantly
            first_half_avg = sum(memory_samples[:len(memory_samples)//2]) / (len(memory_samples)//2)
            second_half_avg = sum(memory_samples[len(memory_samples)//2:]) / (len(memory_samples) - len(memory_samples)//2)
            
            growth_rate = (second_half_avg - first_half_avg) / first_half_avg
            
            # Allow some growth but not excessive
            assert growth_rate < 0.2, f"Potential memory leak detected: {growth_rate:.2%} growth rate"
        
        # Total memory growth should be reasonable
        assert memory_growth < 50, f"Excessive memory growth: {memory_growth:.1f}MB after {num_iterations} iterations"