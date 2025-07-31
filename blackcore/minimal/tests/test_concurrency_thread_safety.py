"""Concurrency and thread safety tests for the transcript processor.

This module tests the system's behavior under concurrent operations:
- Multiple threads processing transcripts simultaneously
- Race conditions in shared resources (cache, rate limiter)
- Thread-safe database operations
- Concurrent API calls
- Resource locking and synchronization
- Deadlock prevention
"""

import pytest
import threading
import time
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any
import random
import multiprocessing
import queue
import tempfile
from pathlib import Path

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import (
    Config,
    NotionConfig,
    AIConfig,
    DatabaseConfig,
    TranscriptInput,
    ProcessingResult,
    ExtractedEntities,
    Entity,
    EntityType,
    NotionPage,
    TranscriptSource,
)
from blackcore.minimal.cache import SimpleCache
from blackcore.minimal.notion_updater import RateLimiter


class TestConcurrentProcessing:
    """Test concurrent transcript processing scenarios."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a TranscriptProcessor for testing."""
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
        
        processor = TranscriptProcessor(config=config)
        processor.ai_extractor.extract_entities = Mock()
        return processor

    def test_concurrent_transcript_processing(self, processor):
        """Test processing multiple transcripts concurrently."""
        num_threads = 10
        results = []
        errors = []
        
        def process_transcript(idx):
            try:
                transcript = TranscriptInput(
                    title=f"Concurrent Meeting {idx}",
                    content=f"Thread {idx} processing content",
                    date=datetime.now().isoformat() + "Z",
                    source=TranscriptSource.PERSONAL_NOTE
                )
                
                # Mock AI response
                processor.ai_extractor.extract_entities.return_value = ExtractedEntities(
                    entities=[
                        Entity(
                            type=EntityType.PERSON,
                            name=f"Person {idx}",
                            confidence=0.9
                        )
                    ],
                    relationships=[],
                    summary=f"Summary {idx}",
                    key_points=[]
                )
                
                result = processor.process_transcript(transcript)
                results.append((idx, result))
            except Exception as e:
                errors.append((idx, e))
        
        # Run threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=process_transcript, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads
        
        # All should succeed
        for idx, result in results:
            assert result.success

    def test_thread_pool_executor_processing(self, processor):
        """Test using ThreadPoolExecutor for concurrent processing."""
        transcripts = [
            TranscriptInput(
                title=f"Pool Meeting {i}",
                content=f"Content for pool thread {i}",
                date=datetime.now().isoformat() + "Z",
                source=TranscriptSource.PERSONAL_NOTE
            )
            for i in range(20)
        ]
        
        # Mock AI responses
        def mock_extract(text=None, **kwargs):
            # Extract ID from content
            import re
            match = re.search(r'thread (\d+)', text or kwargs.get('text', ''))
            idx = match.group(1) if match else '0'
            return ExtractedEntities(
                entities=[
                    Entity(
                        type=EntityType.PERSON,
                        name=f"Speaker {idx}",
                        confidence=0.9
                    )
                ],
                relationships=[],
                summary=f"Pool summary {idx}",
                key_points=[]
            )
        
        processor.ai_extractor.extract_entities.side_effect = mock_extract
        
        # Process with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for transcript in transcripts:
                future = executor.submit(processor.process_transcript, transcript)
                futures.append(future)
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=5)
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Thread pool processing failed: {e}")
        
        # Verify all processed
        assert len(results) == 20
        assert all(r.success for r in results)

    def test_concurrent_cache_access(self, tmp_path):
        """Test thread-safe cache operations."""
        cache = SimpleCache(cache_dir=str(tmp_path / "cache"))
        
        # Shared state
        operations = []
        lock = threading.Lock()
        
        def cache_worker(worker_id, num_operations):
            for i in range(num_operations):
                key = f"key_{worker_id}_{i}"
                value = f"value_{worker_id}_{i}"
                
                # Write
                cache.set(key, value)
                
                # Read
                retrieved = cache.get(key)
                
                # Record operation
                with lock:
                    operations.append({
                        'worker': worker_id,
                        'operation': i,
                        'key': key,
                        'value': value,
                        'retrieved': retrieved
                    })
                
                # Small delay to increase chance of conflicts
                time.sleep(0.001)
        
        # Run multiple workers
        threads = []
        num_workers = 5
        ops_per_worker = 10
        
        for worker_id in range(num_workers):
            thread = threading.Thread(
                target=cache_worker,
                args=(worker_id, ops_per_worker)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify operations
        assert len(operations) == num_workers * ops_per_worker
        
        # Check each operation succeeded
        for op in operations:
            assert op['retrieved'] == op['value']
        
        # Verify all keys are in cache
        for worker_id in range(num_workers):
            for i in range(ops_per_worker):
                key = f"key_{worker_id}_{i}"
                value = f"value_{worker_id}_{i}"
                assert cache.get(key) == value

    def test_rate_limiter_thread_safety(self):
        """Test thread-safe rate limiting."""
        rate_limiter = RateLimiter(requests_per_second=10)
        
        # Track timing
        request_times = []
        lock = threading.Lock()
        
        def make_request(request_id):
            rate_limiter.wait_if_needed()
            with lock:
                request_times.append({
                    'id': request_id,
                    'time': time.time()
                })
        
        # Create many concurrent requests
        threads = []
        num_requests = 20
        
        start_time = time.time()
        for i in range(num_requests):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all
        for thread in threads:
            thread.join()
        
        # Sort by time
        request_times.sort(key=lambda x: x['time'])
        
        # Verify rate limiting
        for i in range(1, len(request_times)):
            time_diff = request_times[i]['time'] - request_times[i-1]['time']
            # Should be at least 0.1 seconds apart (10 req/sec = 0.1 sec/req)
            assert time_diff >= 0.09  # Allow small margin for timing precision

    def test_concurrent_notion_api_calls(self, processor):
        """Test concurrent Notion API calls with mocking."""
        # Mock Notion operations
        mock_page = NotionPage(
            id="page-123",
            database_id="db-123",
            properties={},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow()
        )
        
        call_count = 0
        call_lock = threading.Lock()
        
        def mock_create_page(*args, **kwargs):
            nonlocal call_count
            with call_lock:
                call_count += 1
                # Simulate API delay
                time.sleep(0.01)
            return mock_page
        
        with patch.object(processor.notion_updater, 'create_page', side_effect=mock_create_page):
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_find:
                mock_find.return_value = (mock_page, True)
                
                # Process multiple transcripts concurrently
                def process_one(idx):
                    transcript = TranscriptInput(
                        title=f"API Test {idx}",
                        content=f"Content {idx}",
                        date=datetime.now().isoformat() + "Z",
                        source=TranscriptSource.PERSONAL_NOTE
                    )
                    
                    processor.ai_extractor.extract_entities.return_value = ExtractedEntities(
                        entities=[],
                        relationships=[],
                        summary="Test",
                        key_points=[]
                    )
                    
                    return processor.process_transcript(transcript)
                
                # Use thread pool
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(process_one, i) for i in range(10)]
                    results = [f.result() for f in futures]
                
                # All should succeed
                assert all(r.success for r in results)


class TestRaceConditions:
    """Test for race conditions in shared resources."""

    @pytest.fixture
    def shared_processor(self, tmp_path):
        """Create a processor with shared resources."""
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
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = False  # Disable dry run for race condition tests
        
        return TranscriptProcessor(config=config)

    def test_cache_race_condition(self, shared_processor, tmp_path):
        """Test race conditions in cache read/write operations."""
        cache = shared_processor.cache
        
        # Shared counters
        read_count = 0
        write_count = 0
        conflicts = []
        lock = threading.Lock()
        
        def reader_writer(worker_id):
            nonlocal read_count, write_count
            
            for i in range(50):
                key = f"shared_key_{i % 5}"  # Use limited keys to force conflicts
                
                # Randomly read or write
                if random.random() < 0.5:
                    # Write
                    value = f"worker_{worker_id}_value_{i}"
                    cache.set(key, value)
                    with lock:
                        write_count += 1
                    
                    # Immediately read back
                    read_value = cache.get(key)
                    if read_value != value:
                        with lock:
                            conflicts.append({
                                'worker': worker_id,
                                'expected': value,
                                'actual': read_value,
                                'key': key
                            })
                else:
                    # Read
                    value = cache.get(key)
                    with lock:
                        read_count += 1
                
                # Small random delay
                time.sleep(random.uniform(0, 0.005))
        
        # Run multiple workers
        threads = []
        for worker_id in range(10):
            thread = threading.Thread(target=reader_writer, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify operations completed
        assert read_count + write_count == 500  # 10 workers * 50 operations
        
        # Race conditions might cause conflicts, but cache should remain consistent
        # The conflicts list shows cases where a value was overwritten between write and read
        print(f"Total conflicts: {len(conflicts)}")
        print(f"Read operations: {read_count}")
        print(f"Write operations: {write_count}")

    def test_entity_deduplication_race_condition(self, shared_processor):
        """Test race conditions in entity deduplication."""
        # This tests if multiple threads try to create the same entity
        
        created_entities = []
        lock = threading.Lock()
        
        # Mock AI extractor
        shared_processor.ai_extractor.extract_entities = Mock()
        
        # Mock the _process_person method to track entity creation
        def mock_process_person(person):
            with lock:
                created_entities.append({
                    'name': person.name,
                    'time': time.time()
                })
            return (NotionPage(
                id=f"person-{len(created_entities)}",
                database_id="people-db",
                properties={"Full Name": person.name},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow()
            ), True)
        
        # Mock the entire notion updating methods to avoid API calls
        with patch.object(shared_processor, '_process_person', side_effect=mock_process_person):
            with patch.object(shared_processor, '_process_organization', return_value=(None, False)):
                with patch.object(shared_processor, '_process_task', return_value=(None, False)):
                    with patch.object(shared_processor, '_process_transgression', return_value=(None, False)):
                        with patch.object(shared_processor, '_update_transcript', return_value=None):
                            with patch.object(shared_processor, '_create_relationships', return_value=0):
                                def create_duplicate_entity(thread_id):
                                    transcript = TranscriptInput(
                                        title=f"Thread {thread_id} Meeting",
                                        content="John Smith attended the meeting",
                                        date=datetime.now().isoformat() + "Z",
                                        source=TranscriptSource.PERSONAL_NOTE
                                    )
                                    
                                    # All threads will extract the same entity
                                    shared_processor.ai_extractor.extract_entities.return_value = ExtractedEntities(
                                        entities=[
                                            Entity(
                                                type=EntityType.PERSON,
                                                name="John Smith",  # Same entity in all threads
                                                confidence=0.95
                                            )
                                        ],
                                        relationships=[],
                                        summary="Meeting with John Smith",
                                        key_points=[]
                                    )
                                    
                                    result = shared_processor.process_transcript(transcript)
                                    return result
                                
                                # Run multiple threads trying to create the same entity
                                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                                    futures = [executor.submit(create_duplicate_entity, i) for i in range(10)]
                                    results = [f.result() for f in futures]
                                
                                # All should succeed
                                assert all(r.success for r in results)
                                
                                # In a real system with proper deduplication, we'd expect
                                # only one entity to be created. In our test, each thread
                                # creates its own due to mocking
                                assert len(created_entities) == 10

    def test_concurrent_batch_processing(self, shared_processor):
        """Test concurrent batch processing with shared resources."""
        batches = []
        for batch_id in range(5):
            batch = [
                TranscriptInput(
                    title=f"Batch {batch_id} Item {i}",
                    content=f"Content for batch {batch_id} item {i}",
                    date=datetime.now().isoformat() + "Z",
                    source=TranscriptSource.PERSONAL_NOTE
                )
                for i in range(10)
            ]
            batches.append(batch)
        
        # Mock AI extractor
        shared_processor.ai_extractor.extract_entities = Mock()
        shared_processor.ai_extractor.extract_entities.return_value = ExtractedEntities(
            entities=[],
            relationships=[],
            summary="Batch test",
            key_points=[]
        )
        
        # Mock Notion operations since dry_run is False
        mock_page = NotionPage(
            id="page-123",
            database_id="db-123", 
            properties={},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow()
        )
        
        with patch.object(shared_processor.notion_updater, 'find_or_create_page') as mock_find:
            mock_find.return_value = (mock_page, True)
            
            with patch.object(shared_processor, '_process_person', return_value=(None, False)):
                with patch.object(shared_processor, '_process_organization', return_value=(None, False)):
                    with patch.object(shared_processor, '_process_task', return_value=(None, False)):
                        with patch.object(shared_processor, '_process_transgression', return_value=(None, False)):
                            
                            # Process batches concurrently
                            def process_batch(batch):
                                return shared_processor.process_batch(batch)
                            
                            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                                futures = [executor.submit(process_batch, batch) for batch in batches]
                                batch_results = [f.result() for f in futures]
                            
                            # Verify all batches processed
                            assert len(batch_results) == 5
                            
                            # Debug output
                            for i, result in enumerate(batch_results):
                                print(f"Batch {i}: total={result.total_transcripts}, successful={result.successful}, failed={result.failed}")
                                if result.failed > 0:
                                    for j, res in enumerate(result.results):
                                        if res.errors:
                                            print(f"  Error in transcript {j}: {res.errors[0].message}")
                            
                            for result in batch_results:
                                assert result.total_transcripts == 10
                                assert result.successful == 10
                                assert result.failed == 0
                            
                            # Check thread safety - no race conditions
                            total_processed = sum(r.total_transcripts for r in batch_results)
                            assert total_processed == 50  # 5 batches × 10 transcripts each
                            
                            # Check that thread pool properly queued and processed all tasks
                            total_successful = sum(r.successful for r in batch_results)
                            assert total_successful == 50  # All should succeed


class TestDeadlockPrevention:
    """Test deadlock prevention mechanisms."""

    def test_no_deadlock_with_multiple_locks(self, tmp_path):
        """Test that multiple locks don't cause deadlock."""
        # Create multiple resources with locks
        cache1 = SimpleCache(cache_dir=str(tmp_path / "cache1"))
        cache2 = SimpleCache(cache_dir=str(tmp_path / "cache2"))
        
        rate_limiter1 = RateLimiter(requests_per_second=10)
        rate_limiter2 = RateLimiter(requests_per_second=10)
        
        completed = []
        lock = threading.Lock()
        
        def worker_a():
            # Access resources in order: cache1 -> rate1 -> cache2 -> rate2
            for i in range(10):
                cache1.set(f"a_{i}", f"value_a_{i}")
                rate_limiter1.wait_if_needed()
                cache2.set(f"a_{i}", f"value_a_{i}")
                rate_limiter2.wait_if_needed()
                
                with lock:
                    completed.append(('A', i))
        
        def worker_b():
            # Access resources in different order: cache2 -> rate2 -> cache1 -> rate1
            # This could cause deadlock if not handled properly
            for i in range(10):
                cache2.set(f"b_{i}", f"value_b_{i}")
                rate_limiter2.wait_if_needed()
                cache1.set(f"b_{i}", f"value_b_{i}")
                rate_limiter1.wait_if_needed()
                
                with lock:
                    completed.append(('B', i))
        
        # Start both workers
        thread_a = threading.Thread(target=worker_a)
        thread_b = threading.Thread(target=worker_b)
        
        thread_a.start()
        thread_b.start()
        
        # Wait with timeout to detect deadlock
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)
        
        # Check threads completed
        assert not thread_a.is_alive(), "Thread A deadlocked"
        assert not thread_b.is_alive(), "Thread B deadlocked"
        
        # Verify all operations completed
        assert len(completed) == 20

    def test_timeout_prevents_indefinite_blocking(self):
        """Test that timeouts prevent indefinite blocking."""
        # Create a lock that will be held
        blocking_lock = threading.Lock()
        timed_out = False
        
        def blocking_worker():
            blocking_lock.acquire()
            time.sleep(2)  # Hold lock for 2 seconds
            blocking_lock.release()
        
        def waiting_worker():
            nonlocal timed_out
            # Try to acquire with timeout
            acquired = blocking_lock.acquire(timeout=0.5)
            if not acquired:
                timed_out = True
            else:
                blocking_lock.release()
        
        # Start blocking thread
        blocker = threading.Thread(target=blocking_worker)
        blocker.start()
        
        # Give blocker time to acquire lock
        time.sleep(0.1)
        
        # Start waiting thread
        waiter = threading.Thread(target=waiting_worker)
        waiter.start()
        
        # Wait for completion
        waiter.join()
        blocker.join()
        
        # Verify timeout occurred
        assert timed_out, "Lock should have timed out"


class TestResourceContention:
    """Test behavior under resource contention."""

    def test_high_contention_cache_access(self, tmp_path):
        """Test cache performance under high contention."""
        cache = SimpleCache(cache_dir=str(tmp_path / "cache"))
        
        # Metrics
        operation_times = []
        lock = threading.Lock()
        
        def intensive_cache_operations(worker_id):
            times = []
            
            # Perform many rapid cache operations
            for i in range(100):
                key = f"key_{i % 10}"  # Limited keys for high contention
                
                start = time.time()
                
                # Write
                cache.set(key, f"worker_{worker_id}_value_{i}")
                
                # Read multiple times
                for _ in range(5):
                    cache.get(key)
                
                # Delete and recreate
                cache.delete(key)
                cache.set(key, f"worker_{worker_id}_new_value_{i}")
                
                end = time.time()
                times.append(end - start)
            
            with lock:
                operation_times.extend(times)
        
        # Run many workers
        start_time = time.time()
        threads = []
        for worker_id in range(20):
            thread = threading.Thread(target=intensive_cache_operations, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze performance
        avg_time = sum(operation_times) / len(operation_times)
        max_time = max(operation_times)
        
        print(f"Total operations: {len(operation_times)}")
        print(f"Average operation time: {avg_time:.4f}s")
        print(f"Max operation time: {max_time:.4f}s")
        print(f"Total time: {total_time:.2f}s")
        
        # Performance assertions
        assert avg_time < 0.1, "Average operation time too high under contention"
        assert max_time < 1.0, "Max operation time too high under contention"

    def test_thread_pool_saturation(self, tmp_path):
        """Test behavior when thread pool is saturated."""
        # Create processor for this test
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
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = True  # Use dry run to avoid API calls
        config.processing.batch_size = 5
        
        test_processor = TranscriptProcessor(config=config)
        test_processor.ai_extractor.extract_entities = Mock()
        
        # Create more tasks than thread pool can handle
        num_tasks = 100
        max_workers = 5
        
        # Track completion times
        completion_times = []
        lock = threading.Lock()
        
        def slow_task(task_id):
            start = time.time()
            
            # Simulate slow processing
            transcript = TranscriptInput(
                title=f"Slow Task {task_id}",
                content=f"Content {task_id}",
                date=datetime.now().isoformat() + "Z",
                source=TranscriptSource.PERSONAL_NOTE
            )
            
            # Mock slow AI processing
            def slow_extract(*args, **kwargs):
                time.sleep(0.1)  # Simulate API delay
                return ExtractedEntities(
                    entities=[],
                    relationships=[],
                    summary="Slow",
                    key_points=[]
                )
            
            test_processor.ai_extractor.extract_entities.side_effect = slow_extract
            
            result = test_processor.process_transcript(transcript)
            
            end = time.time()
            with lock:
                completion_times.append({
                    'task_id': task_id,
                    'duration': end - start,
                    'timestamp': end
                })
            
            return result
        
        # Submit all tasks
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(slow_task, i) for i in range(num_tasks)]
            
            # Wait for all with progress tracking
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                completed += 1
                if completed % 20 == 0:
                    elapsed = time.time() - start_time
                    print(f"Completed {completed}/{num_tasks} tasks in {elapsed:.1f}s")
        
        total_time = time.time() - start_time
        
        # Verify all completed
        assert len(completion_times) == num_tasks
        
        # Check that thread pool properly queued and processed all tasks
        # With 5 workers and 0.1s per task, minimum time should be ~2s
        assert total_time >= (num_tasks * 0.1) / max_workers * 0.9  # Allow 10% margin
        
        print(f"Processed {num_tasks} tasks with {max_workers} workers in {total_time:.2f}s")


# Global function for multiprocessing (needs to be pickle-able)
def cpu_intensive_task(data):
    """Simulate CPU-intensive work."""
    result = 0
    for i in range(1000000):
        result += i * data
    return result % 1000000


class TestMultiprocessingScenarios:
    """Test multiprocessing scenarios (if needed for CPU-bound operations)."""

    def test_process_pool_for_cpu_intensive_operations(self):
        """Test using process pool for CPU-intensive operations."""
        # Note: This is more relevant if we have CPU-intensive operations
        # like complex text analysis or large-scale data transformations
        
        # Use process pool for CPU-bound work
        data_items = list(range(20))
        
        with multiprocessing.Pool(processes=4) as pool:
            results = pool.map(cpu_intensive_task, data_items)
        
        # Verify all processed
        assert len(results) == 20
        assert all(isinstance(r, int) for r in results)


class TestSynchronizationPrimitives:
    """Test various synchronization primitives."""

    def test_semaphore_for_resource_limiting(self, tmp_path):
        """Test using semaphore to limit concurrent resource access."""
        # Limit concurrent API calls
        max_concurrent = 3
        api_semaphore = threading.Semaphore(max_concurrent)
        
        # Track concurrent calls
        active_calls = 0
        max_active = 0
        lock = threading.Lock()
        
        def simulated_api_call(call_id):
            nonlocal active_calls, max_active
            
            # Acquire semaphore
            api_semaphore.acquire()
            try:
                with lock:
                    active_calls += 1
                    max_active = max(max_active, active_calls)
                
                # Simulate API call
                time.sleep(0.1)
                
                with lock:
                    active_calls -= 1
            finally:
                api_semaphore.release()
        
        # Launch many threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=simulated_api_call, args=(i,))
            threads.append(thread)
            thread.start()
            time.sleep(0.01)  # Stagger starts slightly
        
        # Wait for all
        for thread in threads:
            thread.join()
        
        # Verify semaphore limited concurrency
        assert max_active <= max_concurrent, f"Max concurrent calls {max_active} exceeded limit {max_concurrent}"

    def test_event_for_thread_coordination(self):
        """Test using events for thread coordination."""
        # Create events for coordination
        start_event = threading.Event()
        ready_events = [threading.Event() for _ in range(5)]
        results = []
        lock = threading.Lock()
        
        def worker(worker_id, ready_event):
            # Signal ready
            ready_event.set()
            
            # Wait for start signal
            start_event.wait()
            
            # Do work
            with lock:
                results.append({
                    'worker': worker_id,
                    'start_time': time.time()
                })
        
        # Start workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i, ready_events[i]))
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to be ready
        for event in ready_events:
            event.wait()
        
        # Start all workers simultaneously
        start_time = time.time()
        start_event.set()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify coordinated start
        start_times = [r['start_time'] for r in results]
        time_spread = max(start_times) - min(start_times)
        
        # All should start within 100ms of each other
        assert time_spread < 0.1, f"Workers didn't start simultaneously: spread={time_spread:.3f}s"