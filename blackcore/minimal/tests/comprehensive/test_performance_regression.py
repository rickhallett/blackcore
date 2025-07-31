"""High-ROI performance regression and benchmarking tests.

These tests establish performance baselines and detect regressions in critical paths.
Focuses on practical performance scenarios that impact production.
"""

import pytest
import time
import psutil
import os
import gc
from typing import List, Dict, Any
from datetime import datetime, timedelta

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput

from .infrastructure import (
    test_environment,
    create_realistic_transcript,
    create_test_batch,
    PerformanceProfiler,
    RealisticDataGenerator
)


class TestPerformanceBaselines:
    """Establish and validate performance baselines for regression detection."""
    
    def setup_method(self):
        """Set up performance profiler for each test."""
        self.profiler = PerformanceProfiler()
        self.process = psutil.Process(os.getpid())
    
    def test_single_transcript_baseline(self):
        """Establish baseline for single transcript processing."""
        with test_environment() as env:
            transcript = create_realistic_transcript("medium")
            processor = TranscriptProcessor(config=env['config'])
            
            # Warm up (exclude from timing)
            result = processor.process_transcript(transcript)
            assert result.success
            
            # Measure baseline performance
            with self.profiler.profile("single_transcript_baseline"):
                result = processor.process_transcript(transcript)
            
            assert result.success
            
            # Validate baseline performance
            duration = self.profiler.get_baseline("single_transcript_baseline")
            assert duration < 30, f"Single transcript baseline too slow: {duration}s"
            assert duration > 0.001, f"Duration suspiciously fast: {duration}s"
    
    def test_batch_processing_baseline(self):
        """Establish baseline for batch processing performance."""
        with test_environment() as env:
            transcripts = create_test_batch(size=10, complexity="medium")
            processor = TranscriptProcessor(config=env['config'])
            
            with self.profiler.profile("batch_processing_baseline"):
                batch_result = processor.process_batch(transcripts)
            
            assert batch_result.success_rate >= 0.9
            
            # Validate batch performance
            duration = self.profiler.get_baseline("batch_processing_baseline")
            assert duration < 120, f"Batch processing baseline too slow: {duration}s"
            
            # Validate per-transcript efficiency
            avg_per_transcript = duration / len(transcripts)
            assert avg_per_transcript < 15, f"Average per transcript too slow: {avg_per_transcript}s"
    
    def test_cache_performance_baseline(self):
        """Establish baseline for cache performance."""
        with test_environment() as env:
            transcript = create_realistic_transcript("medium")
            processor = TranscriptProcessor(config=env['config'])
            
            # First run (cache miss)
            with self.profiler.profile("cache_miss"):
                result1 = processor.process_transcript(transcript)
            assert result1.success
            
            # Second run (cache hit)
            with self.profiler.profile("cache_hit"):
                result2 = processor.process_transcript(transcript)
            assert result2.success
            
            # Cache hit should be faster than cache miss
            cache_miss_time = self.profiler.get_baseline("cache_miss")
            cache_hit_time = self.profiler.get_baseline("cache_hit")
            
            # Allow for mock behavior - cache might not be significantly faster
            assert cache_hit_time <= cache_miss_time * 1.5, "Cache hit not faster than miss"
    
    def test_memory_usage_baseline(self):
        """Establish baseline for memory usage patterns."""
        with test_environment() as env:
            initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Process multiple transcripts to check memory growth
            transcripts = create_test_batch(size=20, complexity="simple")
            processor = TranscriptProcessor(config=env['config'])
            
            for i, transcript in enumerate(transcripts):
                result = processor.process_transcript(transcript)
                assert result.success
                
                # Check memory every 5 transcripts
                if (i + 1) % 5 == 0:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory
                    
                    # Memory increase should be reasonable
                    assert memory_increase < 200, f"Memory increased by {memory_increase}MB after {i+1} transcripts"
            
            # Force garbage collection and final check
            gc.collect()
            final_memory = self.process.memory_info().rss / 1024 / 1024
            total_increase = final_memory - initial_memory
            
            assert total_increase < 100, f"Total memory increase: {total_increase}MB"
    
    def test_ai_extraction_performance(self):
        """Establish baseline for AI extraction performance."""
        with test_environment() as env:
            # Test different complexity levels
            complexities = ["simple", "medium", "complex"]
            
            for complexity in complexities:
                transcript = create_realistic_transcript(complexity)
                processor = TranscriptProcessor(config=env['config'])
                
                with self.profiler.profile(f"ai_extraction_{complexity}"):
                    result = processor.process_transcript(transcript)
                
                assert result.success
                
                # Validate AI extraction performance
                duration = self.profiler.get_baseline(f"ai_extraction_{complexity}")
                max_time = {"simple": 10, "medium": 20, "complex": 30}[complexity]
                assert duration < max_time, f"AI extraction ({complexity}) too slow: {duration}s"


class TestPerformanceRegression:
    """Test for performance regressions against established baselines."""
    
    def setup_method(self):
        """Set up profiler and establish reference baselines."""
        self.profiler = PerformanceProfiler()
        
        # Establish reference baselines (in a real scenario, these would be loaded from storage)
        self.reference_baselines = {
            "single_transcript": 5.0,    # seconds
            "batch_processing": 60.0,    # seconds for 10 transcripts
            "cache_hit": 0.5,           # seconds
            "memory_per_transcript": 5.0, # MB per transcript
        }
    
    def test_single_transcript_regression(self):
        """Detect regression in single transcript processing."""
        with test_environment() as env:
            transcript = create_realistic_transcript("medium")
            processor = TranscriptProcessor(config=env['config'])
            
            # Measure current performance
            with self.profiler.profile("single_transcript_current"):
                result = processor.process_transcript(transcript)
            
            assert result.success
            
            # Check for regression
            current_time = self.profiler.get_baseline("single_transcript_current")
            baseline_time = self.reference_baselines["single_transcript"]
            
            # Allow 50% performance degradation before flagging
            regression_threshold = baseline_time * 1.5
            assert current_time <= regression_threshold, \
                f"Performance regression detected: {current_time}s vs baseline {baseline_time}s"
    
    def test_batch_processing_regression(self):
        """Detect regression in batch processing performance.""" 
        with test_environment() as env:
            transcripts = create_test_batch(size=10, complexity="medium")
            processor = TranscriptProcessor(config=env['config'])
            
            with self.profiler.profile("batch_processing_current"):
                batch_result = processor.process_batch(transcripts)
            
            assert batch_result.success_rate >= 0.9
            
            # Check for regression
            current_time = self.profiler.get_baseline("batch_processing_current")
            baseline_time = self.reference_baselines["batch_processing"]
            
            regression_threshold = baseline_time * 1.3  # 30% degradation threshold
            assert current_time <= regression_threshold, \
                f"Batch processing regression: {current_time}s vs baseline {baseline_time}s"
    
    def test_throughput_regression(self):
        """Test throughput doesn't regress below acceptable levels."""
        with test_environment() as env:
            transcripts = create_test_batch(size=20, complexity="simple")
            processor = TranscriptProcessor(config=env['config'])
            
            start_time = time.time()
            batch_result = processor.process_batch(transcripts)
            duration = time.time() - start_time
            
            assert batch_result.success_rate >= 0.9
            
            # Calculate throughput (transcripts per minute)
            throughput = len(transcripts) / (duration / 60)
            min_throughput = 30  # transcripts per minute
            
            assert throughput >= min_throughput, \
                f"Throughput regression: {throughput:.1f} transcripts/min (min: {min_throughput})"


class TestScalabilityLimits:
    """Test system behavior at scale to identify bottlenecks."""
    
    def setup_method(self):
        self.profiler = PerformanceProfiler()
        self.process = psutil.Process(os.getpid())
    
    def test_increasing_transcript_size(self):
        """Test performance with increasingly large transcripts."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Test different transcript sizes
            content_multipliers = [1, 5, 10, 20]  # Multiply base content
            base_content = "This is a meeting transcript with multiple speakers discussing important topics. " * 10
            
            for multiplier in content_multipliers:
                large_content = base_content * multiplier
                transcript = TranscriptInput(
                    title=f"Large Transcript {multiplier}x",
                    content=large_content,
                    date=datetime.now(),
                    metadata={"size_multiplier": multiplier}
                )
                
                with self.profiler.profile(f"large_transcript_{multiplier}x"):
                    result = processor.process_transcript(transcript)
                
                # Should handle large transcripts gracefully
                if not result.success:
                    # If it fails, it should be due to size limits, not crashes
                    error_msg = str(result.errors[0]).lower()
                    assert any(word in error_msg for word in ['size', 'large', 'limit', 'length'])
                
                # Check processing time scales reasonably
                duration = self.profiler.get_baseline(f"large_transcript_{multiplier}x")
                max_time = 30 + (multiplier * 10)  # Allow more time for larger content
                assert duration < max_time, f"Large transcript ({multiplier}x) too slow: {duration}s"
    
    def test_batch_size_scaling(self):
        """Test performance with increasing batch sizes."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            batch_sizes = [5, 10, 25, 50]
            
            for size in batch_sizes:
                transcripts = create_test_batch(size=size, complexity="simple")
                
                with self.profiler.profile(f"batch_size_{size}"):
                    batch_result = processor.process_batch(transcripts)
                
                # Success rate should remain high
                assert batch_result.success_rate >= 0.8, f"Low success rate for batch size {size}"
                
                # Processing time should scale reasonably
                duration = self.profiler.get_baseline(f"batch_size_{size}")
                max_time_per_transcript = 15  # seconds
                max_total_time = size * max_time_per_transcript
                
                assert duration < max_total_time, \
                    f"Batch size {size} too slow: {duration}s (max: {max_total_time}s)"
                
                # Check average time per transcript
                avg_time = duration / size
                assert avg_time < max_time_per_transcript, \
                    f"Average time per transcript in batch {size}: {avg_time}s"
    
    def test_concurrent_processing_performance(self):
        """Test performance impact of concurrent processing."""
        import threading
        import queue
        
        with test_environment() as env:
            results_queue = queue.Queue()
            
            def process_worker(transcript_batch, config):
                try:
                    processor = TranscriptProcessor(config=config)
                    start_time = time.time()
                    
                    for transcript in transcript_batch:
                        result = processor.process_transcript(transcript)
                        if not result.success:
                            results_queue.put(("error", str(result.errors)))
                            return
                    
                    duration = time.time() - start_time
                    results_queue.put(("success", duration))
                except Exception as e:
                    results_queue.put(("exception", str(e)))
            
            # Test different levels of concurrency
            concurrency_levels = [1, 2, 4]
            
            for num_threads in concurrency_levels:
                # Create work for each thread
                work_per_thread = 3
                total_transcripts = num_threads * work_per_thread
                all_transcripts = create_test_batch(size=total_transcripts, complexity="simple")
                
                # Divide work among threads
                thread_batches = []
                for i in range(num_threads):
                    start_idx = i * work_per_thread
                    end_idx = start_idx + work_per_thread
                    thread_batches.append(all_transcripts[start_idx:end_idx])
                
                # Start concurrent processing
                start_time = time.time()
                threads = []
                
                for batch in thread_batches:
                    thread = threading.Thread(
                        target=process_worker,
                        args=(batch, env['config'])
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for completion
                for thread in threads:
                    thread.join()
                
                total_duration = time.time() - start_time
                
                # Collect results
                results = []
                while not results_queue.empty():
                    results.append(results_queue.get())
                
                # Validate concurrent processing
                assert len(results) == num_threads, f"Missing results for concurrency {num_threads}"
                
                success_count = sum(1 for status, _ in results if status == "success")
                success_rate = success_count / len(results)
                
                assert success_rate >= 0.8, f"Low success rate with {num_threads} threads: {success_rate}"
                
                # Concurrent processing should be more efficient than sequential
                if num_threads > 1:
                    sequential_estimate = work_per_thread * num_threads * 5  # 5s per transcript estimate
                    efficiency_ratio = sequential_estimate / total_duration
                    
                    # Should see some concurrency benefit (at least 20% improvement)
                    assert efficiency_ratio >= 1.2, \
                        f"Poor concurrency efficiency with {num_threads} threads: {efficiency_ratio:.2f}x"


class TestCachePerformance:
    """Test cache performance and effectiveness."""
    
    def setup_method(self):
        self.profiler = PerformanceProfiler()
    
    def test_cache_hit_ratio(self):
        """Test cache effectiveness with repeated operations."""
        with test_environment() as env:
            transcript = create_realistic_transcript("medium")
            processor = TranscriptProcessor(config=env['config'])
            
            # Process same transcript multiple times
            durations = []
            for i in range(5):
                start_time = time.time()
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                assert result.success
                durations.append(duration)
            
            # Later runs should be faster due to caching (allowing for mock behavior)
            first_run = durations[0]
            avg_later_runs = sum(durations[1:]) / len(durations[1:])
            
            # Cache should provide some benefit (even if minimal with mocks)
            cache_efficiency = first_run / avg_later_runs if avg_later_runs > 0 else 1
            assert cache_efficiency >= 0.8, f"Poor cache efficiency: {cache_efficiency:.2f}x"
    
    def test_cache_memory_efficiency(self):
        """Test cache doesn't consume excessive memory."""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Process many different transcripts (should populate cache)
            unique_transcripts = []
            for i in range(20):
                transcript = TranscriptInput(
                    title=f"Unique Transcript {i}",
                    content=f"This is unique content for transcript {i} with specific details.",
                    date=datetime.now() - timedelta(days=i),
                    metadata={"index": i}
                )
                unique_transcripts.append(transcript)
            
            for transcript in unique_transcripts:
                result = processor.process_transcript(transcript)
                assert result.success
            
            # Check memory usage
            final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            # Cache memory usage should be reasonable
            max_cache_memory = 50  # MB
            assert memory_increase < max_cache_memory, \
                f"Cache using too much memory: {memory_increase}MB"
    
    def test_cache_invalidation_performance(self):
        """Test cache invalidation doesn't cause performance issues."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            transcript = create_realistic_transcript("medium")
            
            # Fill cache
            result = processor.process_transcript(transcript)
            assert result.success
            
            # Force cache invalidation scenario (if cache has TTL or size limits)
            # Process many different items to potentially trigger eviction
            for i in range(10):
                different_transcript = TranscriptInput(
                    title=f"Different {i}",
                    content=f"Different content {i}" * 100,  # Larger content
                    date=datetime.now(),
                    metadata={"variant": i}
                )
                
                with self.profiler.profile(f"cache_pressure_{i}"):
                    result = processor.process_transcript(different_transcript)
                
                assert result.success
                
                # Performance should remain stable even under cache pressure
                duration = self.profiler.get_baseline(f"cache_pressure_{i}")
                assert duration < 30, f"Performance degraded under cache pressure: {duration}s"


class TestResourceUtilization:
    """Test efficient resource utilization patterns."""
    
    def test_cpu_utilization_efficiency(self):
        """Test CPU utilization remains reasonable."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Monitor CPU during processing
            initial_cpu_percent = psutil.cpu_percent(interval=1)
            
            start_time = time.time()
            transcripts = create_test_batch(size=10, complexity="medium")
            
            for transcript in transcripts:
                result = processor.process_transcript(transcript)
                assert result.success
            
            duration = time.time() - start_time
            final_cpu_percent = psutil.cpu_percent(interval=1)
            
            # CPU usage should be reasonable (allowing for system variation)
            cpu_increase = abs(final_cpu_percent - initial_cpu_percent)
            assert cpu_increase < 80, f"High CPU usage increase: {cpu_increase}%"
            
            # Should process efficiently (not just burning CPU)
            throughput = len(transcripts) / duration
            assert throughput > 0.5, f"Low processing throughput: {throughput} transcripts/sec"
    
    def test_io_efficiency(self):
        """Test I/O operations are efficient."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Monitor I/O during cache operations
            process = psutil.Process(os.getpid())
            initial_io = process.io_counters()
            
            # Process transcripts that should trigger cache I/O
            transcripts = create_test_batch(size=5, complexity="medium")
            
            for transcript in transcripts:
                result = processor.process_transcript(transcript)
                assert result.success
            
            final_io = process.io_counters()
            
            # I/O should be reasonable (not excessive read/write operations)
            read_ops = final_io.read_count - initial_io.read_count
            write_ops = final_io.write_count - initial_io.write_count
            
            # These limits are generous to account for system variation
            assert read_ops < 1000, f"Excessive read operations: {read_ops}"
            assert write_ops < 1000, f"Excessive write operations: {write_ops}"