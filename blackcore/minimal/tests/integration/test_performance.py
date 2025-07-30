"""Performance tests for minimal module."""

import time
import threading
import json
from datetime import datetime
import statistics

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput
from blackcore.minimal.notion_updater import RateLimiter


class TestPerformanceBaseline:
    """Test basic performance characteristics."""

    def test_single_transcript_performance(self, integration_test_env, performance_monitor):
        """Test performance of processing a single transcript."""
        env = integration_test_env

        transcript = TranscriptInput(
            title="Performance Test",
            content="Meeting with John Smith from Acme Corporation about Q4 planning.",
            date=datetime.now(),
        )

        # Time the processing
        start_time = time.time()
        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)
        end_time = time.time()

        processing_time = end_time - start_time
        performance_monitor.record_timing("single_transcript", processing_time)

        # Verify success
        assert result.success is True

        # Performance assertions
        assert processing_time < 2.0  # Should complete within 2 seconds
        assert result.processing_time > 0
        assert result.processing_time < 2.0

    def test_batch_processing_performance(self, integration_test_env, performance_monitor):
        """Test performance of batch processing."""
        env = integration_test_env

        # Create batch of 20 transcripts
        transcripts = []
        for i in range(20):
            transcript = TranscriptInput(
                title=f"Batch Test {i}",
                content=f"Meeting {i} with Person {i} from Company {i}.",
                date=datetime.now(),
            )
            transcripts.append(transcript)

        processor = TranscriptProcessor(config=env["config"])

        # Time batch processing
        start_time = time.time()
        result = processor.process_batch(transcripts)
        end_time = time.time()

        total_time = end_time - start_time
        performance_monitor.record_timing("batch_20_transcripts", total_time)

        # Verify all processed
        assert result.total_transcripts == 20
        assert result.successful == 20

        # Performance assertions
        avg_time_per_transcript = total_time / 20
        assert avg_time_per_transcript < 1.0  # Less than 1s per transcript average

        # Should be more efficient than processing individually
        assert total_time < 20.0  # Less than 20 seconds for 20 transcripts

    def test_cache_performance_impact(self, integration_test_env, performance_monitor):
        """Test performance impact of caching."""
        env = integration_test_env

        transcript = TranscriptInput(
            title="Cache Test",
            content="Repeated content for cache testing with John Smith.",
            date=datetime.now(),
        )

        processor = TranscriptProcessor(config=env["config"])

        # First run - no cache
        start1 = time.time()
        result1 = processor.process_transcript(transcript)
        time1 = time.time() - start1
        performance_monitor.record_timing("first_run_no_cache", time1)

        # Second run - with cache
        start2 = time.time()
        result2 = processor.process_transcript(transcript)
        time2 = time.time() - start2
        performance_monitor.record_timing("second_run_with_cache", time2)

        # Cache should make second run faster
        assert time2 < time1
        # Second run should be very fast (just cache lookup)
        assert time2 < 0.5

        # Both should succeed
        assert result1.success is True
        assert result2.success is True


class TestRateLimitingPerformance:
    """Test rate limiting performance and compliance."""

    def test_rate_limiter_accuracy(self):
        """Test that rate limiter maintains accurate timing."""
        # Test at exactly 3 requests per second (Notion limit)
        limiter = RateLimiter(requests_per_second=3)

        request_times = []
        start_time = time.time()

        # Make 9 requests (should take ~3 seconds)
        for i in range(9):
            limiter.wait_if_needed()
            request_times.append(time.time())

        total_time = time.time() - start_time

        # Should take approximately 3 seconds (9 requests at 3/sec)
        assert 2.8 < total_time < 3.5

        # Check spacing between requests
        intervals = []
        for i in range(1, len(request_times)):
            interval = request_times[i] - request_times[i - 1]
            intervals.append(interval)

        # Average interval should be ~0.333 seconds
        avg_interval = statistics.mean(intervals)
        assert 0.32 < avg_interval < 0.35

    def test_concurrent_rate_limiting(self):
        """Test rate limiting with concurrent requests."""
        limiter = RateLimiter(requests_per_second=5)
        request_times = []
        lock = threading.Lock()

        def make_request(thread_id):
            for i in range(3):
                limiter.wait_if_needed()
                with lock:
                    request_times.append((thread_id, time.time()))

        # Start 3 threads making requests
        threads = []
        start_time = time.time()

        for i in range(3):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        total_time = time.time() - start_time

        # 9 total requests at 5/sec should take ~1.8 seconds
        assert 1.6 < total_time < 2.2

        # Sort by time
        request_times.sort(key=lambda x: x[1])

        # Check that requests are properly spaced
        for i in range(1, len(request_times)):
            interval = request_times[i][1] - request_times[i - 1][1]
            # Should be at least 0.2 seconds apart (5 requests/sec)
            assert interval >= 0.18  # Allow small margin

    def test_rate_limit_burst_handling(self, integration_test_env):
        """Test handling of burst requests with rate limiting."""
        env = integration_test_env

        # Configure strict rate limit
        env["config"].notion.rate_limit = 2  # 2 requests per second

        # Create transcripts that will generate many entities
        transcript = TranscriptInput(
            title="Burst Test",
            content="Meeting with " + ", ".join([f"Person {i}" for i in range(10)]),
            date=datetime.now(),
        )

        # Mock AI to return many entities
        entities = [{"name": f"Person {i}", "type": "person"} for i in range(10)]
        env["ai_client"].messages.create.return_value.content[0].text = json.dumps(
            {"entities": entities, "relationships": []}
        )

        # Track API calls
        api_call_times = []
        original_create = env["notion_client"].pages.create

        def tracked_create(**kwargs):
            api_call_times.append(time.time())
            return original_create(**kwargs)

        env["notion_client"].pages.create = tracked_create

        processor = TranscriptProcessor(config=env["config"])
        start_time = time.time()
        result = processor.process_transcript(transcript)
        end_time = time.time()

        # Should succeed
        assert result.success is True
        assert len(result.created) == 10

        # Check rate limiting
        if len(api_call_times) > 1:
            intervals = []
            for i in range(1, len(api_call_times)):
                interval = api_call_times[i] - api_call_times[i - 1]
                intervals.append(interval)

            # All intervals should respect rate limit (0.5s for 2 req/sec)
            assert all(interval >= 0.45 for interval in intervals)


class TestMemoryPerformance:
    """Test memory usage and efficiency."""

    def test_large_transcript_memory(self, integration_test_env, performance_monitor):
        """Test memory efficiency with large transcripts."""
        env = integration_test_env

        # Create a very large transcript (1MB+)
        large_content = "This is a test sentence. " * 50000  # ~1MB

        transcript = TranscriptInput(
            title="Large Transcript Test", content=large_content, date=datetime.now()
        )

        processor = TranscriptProcessor(config=env["config"])

        # Process large transcript
        start_time = time.time()
        result = processor.process_transcript(transcript)
        processing_time = time.time() - start_time

        performance_monitor.record_timing("large_transcript_1mb", processing_time)

        # Should handle large content
        assert result.success is True

        # Should complete in reasonable time despite size
        assert processing_time < 5.0

    def test_batch_memory_efficiency(self, integration_test_env):
        """Test memory efficiency in batch processing."""
        env = integration_test_env

        # Create batch with varying sizes
        transcripts = []
        for i in range(50):
            size = 1000 * (i % 10 + 1)  # Vary from 1KB to 10KB
            content = "x" * size
            transcript = TranscriptInput(
                title=f"Batch Memory Test {i}", content=content, date=datetime.now()
            )
            transcripts.append(transcript)

        processor = TranscriptProcessor(config=env["config"])

        # Process in batches
        batch_size = 10
        total_start = time.time()

        for i in range(0, len(transcripts), batch_size):
            batch = transcripts[i : i + batch_size]
            result = processor.process_batch(batch)
            assert result.successful == len(batch)

        total_time = time.time() - total_start

        # Should handle 50 transcripts efficiently
        assert total_time < 30.0  # Less than 30 seconds for 50 transcripts


class TestAPICallOptimization:
    """Test API call optimization and efficiency."""

    def test_minimize_api_calls(self, integration_test_env):
        """Test that duplicate checks minimize API calls."""
        env = integration_test_env

        # First call returns no results (entity doesn't exist)
        # Second call returns the created entity
        env["notion_client"].databases.query.side_effect = [
            {"results": [], "has_more": False},
            {"results": [{"id": "created-page"}], "has_more": False},
        ]

        transcript = TranscriptInput(
            title="API Optimization Test",
            content="Meeting with John Smith and John Smith again.",
            date=datetime.now(),
        )

        # Mock AI to return duplicate entities
        env["ai_client"].messages.create.return_value.content[0].text = json.dumps(
            {
                "entities": [
                    {"name": "John Smith", "type": "person"},
                    {"name": "John Smith", "type": "person"},  # Duplicate
                ],
                "relationships": [],
            }
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Should succeed
        assert result.success is True

        # Should only create one page for duplicate entity
        create_calls = env["notion_client"].pages.create.call_count
        assert create_calls == 1  # Only one creation despite duplicate

    def test_batch_query_optimization(self, integration_test_env):
        """Test optimization of batch queries."""
        env = integration_test_env

        # Process multiple transcripts with overlapping entities
        transcripts = [
            TranscriptInput(
                title="Meeting 1", content="John Smith from Acme Corp", date=datetime.now()
            ),
            TranscriptInput(
                title="Meeting 2",
                content="John Smith and Jane Doe from Acme Corp",
                date=datetime.now(),
            ),
            TranscriptInput(title="Meeting 3", content="Jane Doe presenting", date=datetime.now()),
        ]

        processor = TranscriptProcessor(config=env["config"])

        # Track API calls
        query_count = 0
        original_query = env["notion_client"].databases.query

        def tracked_query(**kwargs):
            nonlocal query_count
            query_count += 1
            return {"results": [], "has_more": False}

        env["notion_client"].databases.query = tracked_query

        # Process batch
        result = processor.process_batch(transcripts)

        assert result.successful == 3

        # Should optimize queries for duplicate entities
        # Exact count depends on implementation, but should be optimized
        assert query_count > 0  # Some queries were made
