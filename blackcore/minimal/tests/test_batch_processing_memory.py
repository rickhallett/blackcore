"""Large batch processing and memory usage tests for the transcript processor.

This module tests the system's ability to handle large-scale processing:
- Processing hundreds/thousands of transcripts
- Memory efficiency during batch operations
- Resource cleanup and garbage collection
- Concurrent processing limits
- Performance degradation patterns
"""

import pytest
import gc
import time
import psutil
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import concurrent.futures
from typing import List, Dict, Any
import tracemalloc

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import (
    TranscriptInput,
    ProcessingResult,
    BatchResult,
    Config,
    NotionConfig,
    AIConfig,
    DatabaseConfig,
    ExtractedEntities,
    Entity,
    EntityType,
    NotionPage,
)


class TestLargeBatchProcessing:
    """Test suite for large-scale batch processing scenarios."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a TranscriptProcessor instance for testing."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(
                api_key="sk-ant-" + "a" * 95,
                provider="claude",
                model="claude-3-sonnet-20240229"
            ),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = True  # Avoid actual API calls
        config.processing.batch_size = 10
        
        processor = TranscriptProcessor(config=config)
        processor.ai_extractor.extract_entities = Mock()
        return processor

    @pytest.fixture
    def mock_ai_response(self):
        """Generate mock AI response for testing."""
        def generate_response(i: int) -> ExtractedEntities:
            return ExtractedEntities(
                entities=[
                    Entity(
                        type=EntityType.PERSON,
                        name=f"Person {i}",
                        confidence=0.95,
                        context=f"Speaker {i} in meeting"
                    ),
                    Entity(
                        type=EntityType.ORGANIZATION,
                        name=f"Org {i}",
                        confidence=0.90,
                        context=f"Organization {i} mentioned"
                    ),
                    Entity(
                        type=EntityType.TASK,
                        name=f"Task {i}",
                        confidence=0.85,
                        context=f"Action item {i}"
                    ),
                ],
                relationships=[],
                summary=f"Meeting {i} summary",
                key_points=[f"Point {i}.1", f"Point {i}.2"]
            )
        return generate_response

    def generate_transcripts(self, count: int) -> List[TranscriptInput]:
        """Generate a large number of test transcripts."""
        transcripts = []
        base_date = datetime.now()
        
        for i in range(count):
            transcript = TranscriptInput(
                title=f"Meeting {i} - Large Batch Test",
                content=f"""Speaker {i}: Welcome to meeting {i}.
                
                We need to discuss the following items:
                1. Project status for Org {i}
                2. Task assignments for Person {i}
                3. Budget review for Q{(i % 4) + 1}
                
                This is a longer content block to simulate real transcript data.
                """ * 10,  # Make content reasonably large
                date=(base_date - timedelta(days=i)).isoformat() + "Z",
                source="personal_note"
            )
            transcripts.append(transcript)
        
        return transcripts

    def test_large_batch_processing_100_transcripts(self, processor, mock_ai_response):
        """Test processing 100 transcripts in a batch."""
        transcripts = self.generate_transcripts(100)
        
        # Mock AI responses
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = [mock_ai_response(i) for i in range(100)]
            
            # Mock Notion updater
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Process batch
                start_time = time.time()
                result = processor.process_batch(transcripts)
                duration = time.time() - start_time
                
                # Verify results
                assert result.total_transcripts == 100
                assert result.successful == 100
                assert result.failed == 0
                assert result.success_rate == 1.0
                
                # Performance check - should complete in reasonable time
                assert duration < 60  # Should process 100 transcripts in under 60 seconds
                
                # Verify batch size was respected
                assert len(result.results) == 100

    def test_large_batch_processing_1000_transcripts(self, processor, mock_ai_response):
        """Test processing 1000 transcripts - stress test."""
        transcripts = self.generate_transcripts(1000)
        
        # Mock responses
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = [mock_ai_response(i) for i in range(1000)]
            
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Process in batches
                start_time = time.time()
                result = processor.process_batch(transcripts)
                duration = time.time() - start_time
                
                # Verify results
                assert result.total_transcripts == 1000
                assert result.successful >= 950  # Allow for some failures in stress test
                assert result.success_rate >= 0.95
                
                # Log performance metrics
                print(f"\nProcessed 1000 transcripts in {duration:.2f} seconds")
                print(f"Average time per transcript: {duration/1000:.3f} seconds")

    def test_memory_usage_during_batch_processing(self, processor, mock_ai_response):
        """Test memory usage patterns during large batch processing."""
        # Get process info
        process = psutil.Process(os.getpid())
        
        # Start memory tracking
        tracemalloc.start()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process batches of increasing size
        batch_sizes = [10, 50, 100, 200]
        memory_usage = []
        
        for size in batch_sizes:
            transcripts = self.generate_transcripts(size)
            
            with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
                mock_extract.side_effect = [mock_ai_response(i) for i in range(size)]
                
                mock_page = NotionPage(
                    id="page-123",
                    database_id="db-123",
                    properties={},
                    created_time=datetime.utcnow(),
                    last_edited_time=datetime.utcnow()
                )
                
                with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                    mock_create.return_value = (mock_page, True)
                    
                    # Process batch
                    gc.collect()  # Clean before measurement
                    pre_batch_memory = process.memory_info().rss / 1024 / 1024
                    
                    result = processor.process_batch(transcripts)
                    
                    post_batch_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = post_batch_memory - pre_batch_memory
                    memory_usage.append((size, memory_increase))
                    
                    # Force garbage collection
                    gc.collect()
        
        # Stop memory tracking
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Verify memory usage is reasonable
        for size, increase in memory_usage:
            # Memory increase should be roughly proportional to batch size
            # Allow up to 1MB per transcript as reasonable overhead
            assert increase < size * 1.0, f"Excessive memory use for batch size {size}: {increase:.2f} MB"
        
        # Check for memory leaks - final memory should be close to initial
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_leak = final_memory - initial_memory
        assert memory_leak < 50, f"Potential memory leak detected: {memory_leak:.2f} MB increase"

    def test_concurrent_batch_processing(self, processor, mock_ai_response):
        """Test concurrent processing of multiple batches."""
        # Create multiple small batches
        batches = [self.generate_transcripts(20) for _ in range(5)]
        
        # Mock responses
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = [mock_ai_response(i) for i in range(100)]
            
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Process batches concurrently
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_batch = {
                        executor.submit(processor.process_batch, batch): i 
                        for i, batch in enumerate(batches)
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_id = future_to_batch[future]
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as exc:
                            pytest.fail(f"Batch {batch_id} failed: {exc}")
                
                # Verify all batches processed successfully
                assert len(results) == 5
                total_processed = sum(r.total_transcripts for r in results)
                assert total_processed == 100
                
                # Check thread safety - no race conditions
                total_successful = sum(r.successful for r in results)
                assert total_successful >= 95  # Allow small failure rate

    def test_batch_processing_with_failures(self, processor, mock_ai_response):
        """Test batch processing behavior with intermittent failures."""
        transcripts = self.generate_transcripts(50)
        
        # Mock AI responses with some failures
        responses = []
        for i in range(50):
            if i % 10 == 5:  # Fail every 10th request
                responses.append(Exception(f"Simulated AI failure for transcript {i}"))
            else:
                responses.append(mock_ai_response(i))
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = responses
            
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Process batch
                result = processor.process_batch(transcripts)
                
                # Verify partial success
                assert result.total_transcripts == 50
                assert result.failed == 5
                assert result.successful == 45
                assert result.success_rate == 0.9
                
                # Check failed results have error info
                failed_results = [r for r in result.results if not r.success]
                assert len(failed_results) == 5
                for failed in failed_results:
                    assert len(failed.errors) > 0
                    assert "Simulated AI failure" in str(failed.errors[0])

    def test_batch_processing_memory_pressure(self, processor, mock_ai_response):
        """Test batch processing under memory pressure conditions."""
        # Generate large transcripts (simulate memory pressure)
        large_content = "x" * 100000  # 100KB per transcript
        transcripts = []
        
        for i in range(50):
            transcript = TranscriptInput(
                title=f"Large Transcript {i}",
                content=large_content + f"\nUnique content for transcript {i}",
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            )
            transcripts.append(transcript)
        
        # Mock responses
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = [mock_ai_response(i) for i in range(50)]
            
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Monitor memory during processing
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss / 1024 / 1024
                
                # Process batch
                result = processor.process_batch(transcripts)
                
                # Check memory after processing
                gc.collect()
                final_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = final_memory - initial_memory
                
                # Verify successful processing
                assert result.success_rate >= 0.9
                
                # Memory increase should be reasonable even with large transcripts
                # Allow up to 100MB increase for 50 large transcripts
                assert memory_increase < 100, f"Excessive memory use: {memory_increase:.2f} MB"

    def test_batch_processing_performance_degradation(self, processor, mock_ai_response):
        """Test for performance degradation with increasing batch sizes."""
        batch_sizes = [10, 20, 50, 100]
        processing_times = []
        
        for size in batch_sizes:
            transcripts = self.generate_transcripts(size)
            
            with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
                mock_extract.side_effect = [mock_ai_response(i) for i in range(size)]
                
                mock_page = NotionPage(
                    id="page-123",
                    database_id="db-123",
                    properties={},
                    created_time=datetime.utcnow(),
                    last_edited_time=datetime.utcnow()
                )
                
                with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                    mock_create.return_value = (mock_page, True)
                    
                    # Measure processing time
                    start_time = time.time()
                    result = processor.process_batch(transcripts)
                    duration = time.time() - start_time
                    
                    processing_times.append((size, duration))
                    
                    # Verify successful processing
                    assert result.success_rate >= 0.95
        
        # Check for linear or better scaling
        for i in range(1, len(processing_times)):
            prev_size, prev_time = processing_times[i-1]
            curr_size, curr_time = processing_times[i]
            
            # Time should scale roughly linearly with size
            expected_time = prev_time * (curr_size / prev_size)
            # Allow 20% overhead for larger batches
            assert curr_time <= expected_time * 1.2, \
                f"Performance degradation: {curr_size} items took {curr_time:.2f}s, expected ~{expected_time:.2f}s"

    def test_batch_processing_resource_cleanup(self, processor, mock_ai_response, tmp_path):
        """Test proper resource cleanup after batch processing."""
        # Process multiple batches
        for batch_num in range(3):
            transcripts = self.generate_transcripts(30)
            
            with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
                mock_extract.side_effect = [mock_ai_response(i) for i in range(30)]
                
                mock_page = NotionPage(
                    id=f"page-{batch_num}",
                    database_id="db-123",
                    properties={},
                    created_time=datetime.utcnow(),
                    last_edited_time=datetime.utcnow()
                )
                
                with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                    mock_create.return_value = (mock_page, True)
                    
                    # Count open file descriptors before
                    process = psutil.Process(os.getpid())
                    open_files_before = len(process.open_files())
                    
                    # Process batch
                    result = processor.process_batch(transcripts)
                    assert result.success_rate >= 0.95
                    
                    # Force cleanup
                    gc.collect()
                    
                    # Count open file descriptors after
                    open_files_after = len(process.open_files())
                    
                    # Should not leak file descriptors
                    assert open_files_after <= open_files_before + 2, \
                        f"Potential file descriptor leak: {open_files_after - open_files_before} new descriptors"
        
        # Check cache directory is not growing unbounded
        cache_dir = tmp_path / "cache"
        if cache_dir.exists():
            cache_files = list(cache_dir.rglob("*"))
            # Should have reasonable number of cache files
            assert len(cache_files) < 100, f"Cache directory has {len(cache_files)} files"


class TestMemoryEfficiency:
    """Test memory efficiency and optimization strategies."""

    @pytest.fixture
    def memory_processor(self, tmp_path):
        """Create processor optimized for memory testing."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(
                api_key="sk-ant-" + "a" * 95,
                provider="claude",
                model="claude-3-sonnet-20240229"
            ),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = True
        config.processing.batch_size = 5  # Smaller batch size for memory efficiency
        
        return TranscriptProcessor(config=config)

    def test_streaming_batch_processing(self, memory_processor):
        """Test memory-efficient streaming batch processing."""
        # Create generator for transcripts (memory efficient)
        def transcript_generator(count: int):
            for i in range(count):
                yield TranscriptInput(
                    title=f"Streaming Transcript {i}",
                    content=f"Content for transcript {i}" * 100,
                    date=datetime.now().isoformat() + "Z",
                    source="personal_note"
                )
        
        # Mock AI and Notion responses
        mock_response = ExtractedEntities(
            entities=[Entity(type=EntityType.PERSON, name="Test", confidence=0.9)],
            relationships=[],
            summary="Test",
            key_points=[]
        )
        
        with patch.object(memory_processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = mock_response
            
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(memory_processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Process in streaming fashion
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss / 1024 / 1024
                
                # Convert generator to list for batch processing
                # In real implementation, we'd process in chunks
                transcripts = list(transcript_generator(100))
                result = memory_processor.process_batch(transcripts)
                
                final_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = final_memory - initial_memory
                
                # Verify efficient memory usage
                assert result.success_rate >= 0.95
                assert memory_increase < 20, f"Memory increase too high: {memory_increase:.2f} MB"

    def test_cache_memory_management(self, memory_processor, tmp_path):
        """Test cache memory management and eviction."""
        # Generate many unique transcripts to stress cache
        transcripts = []
        for i in range(50):
            transcript = TranscriptInput(
                title=f"Cache Test {i}",
                content=f"Unique content {i} that should be cached" * 50,
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            )
            transcripts.append(transcript)
        
        mock_response = ExtractedEntities(
            entities=[Entity(type=EntityType.TASK, name="Task", confidence=0.9)],
            relationships=[],
            summary="Summary",
            key_points=[]
        )
        
        with patch.object(memory_processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = mock_response
            
            mock_page = NotionPage(
                id="page-123",
                database_id="db-123",
                properties={},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            )
            
            with patch.object(memory_processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_create.return_value = (mock_page, True)
                
                # Process transcripts
                result = memory_processor.process_batch(transcripts)
                
                # Check cache directory size
                cache_dir = tmp_path / "cache"
                if cache_dir.exists():
                    total_cache_size = sum(
                        f.stat().st_size for f in cache_dir.rglob("*") if f.is_file()
                    ) / 1024 / 1024  # MB
                    
                    # Cache should not grow unbounded
                    assert total_cache_size < 50, f"Cache too large: {total_cache_size:.2f} MB"
                
                # Process same transcripts again (should use cache)
                mock_extract.reset_mock()
                result2 = memory_processor.process_batch(transcripts[:25])
                
                # Should have minimal AI calls due to caching
                assert mock_extract.call_count < 5, "Cache not being used effectively"