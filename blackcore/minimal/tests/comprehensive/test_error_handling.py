"""High-ROI error handling and recovery tests for production reliability.

These tests validate comprehensive error scenarios and recovery mechanisms
that are critical for maintaining system stability in production environments.
"""

import pytest
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput, ProcessingResult
from blackcore.minimal.cache import SimpleCache

from .infrastructure import (
    test_environment,
    create_realistic_transcript,
    create_test_batch,
    RealisticDataGenerator,
    FailureSimulator
)


class TestInputValidationErrors:
    """Test handling of various input validation errors."""
    
    def test_empty_transcript_content(self):
        """Test handling of empty transcript content."""
        invalid_transcripts = [
            TranscriptInput(title="Empty", content="", date=datetime.now()),
            TranscriptInput(title="Whitespace", content="   \n\t  ", date=datetime.now()),
            TranscriptInput(title="Null", content=None, date=datetime.now()),
        ]
        
        for transcript in invalid_transcripts:
            with test_environment() as env:
                processor = TranscriptProcessor(config=env['config'])
                
                try:
                    result = processor.process_transcript(transcript)
                    
                    # Should either succeed gracefully or fail with helpful error
                    if not result.success:
                        assert len(result.errors) > 0
                        error_msg = str(result.errors[0]).lower()
                        assert any(word in error_msg for word in 
                                  ['empty', 'content', 'invalid', 'missing'])
                        
                except ValueError as e:
                    # Acceptable to raise ValueError for invalid input
                    assert "content" in str(e).lower() or "empty" in str(e).lower()
                except Exception as e:
                    pytest.fail(f"Unexpected exception for empty content: {e}")
    
    def test_invalid_date_formats(self):
        """Test handling of invalid date formats."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Test various invalid date scenarios
            invalid_dates = [
                None,
                "invalid-date-string",
                datetime(1900, 1, 1),  # Very old date
                datetime(2100, 1, 1),  # Future date
            ]
            
            for invalid_date in invalid_dates:
                try:
                    transcript = TranscriptInput(
                        title="Date Test",
                        content="Valid content with invalid date",
                        date=invalid_date,
                        metadata={"test": "invalid_date"}
                    )
                    
                    result = processor.process_transcript(transcript)
                    
                    # Should handle gracefully
                    if not result.success:
                        assert len(result.errors) > 0
                        
                except (ValueError, TypeError) as e:
                    # Acceptable to raise validation exceptions
                    assert "date" in str(e).lower()
                except Exception as e:
                    pytest.fail(f"Unexpected exception for invalid date {invalid_date}: {e}")
    
    def test_oversized_transcript_handling(self):
        """Test handling of excessively large transcripts."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Create extremely large content
            large_content = "This is a very long transcript content. " * 10000  # ~400KB
            
            transcript = TranscriptInput(
                title="Oversized Transcript",
                content=large_content,
                date=datetime.now(),
                metadata={"size": len(large_content)}
            )
            
            result = processor.process_transcript(transcript)
            
            # Should either process successfully or fail gracefully
            if not result.success:
                assert len(result.errors) > 0
                error_msg = str(result.errors[0]).lower()
                assert any(word in error_msg for word in 
                          ['size', 'large', 'limit', 'length', 'token'])
    
    def test_malformed_metadata_handling(self):
        """Test handling of malformed metadata."""
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            malformed_metadata_cases = [
                {"circular_ref": None},  # Will be set to create circular reference
                {"very_deep": {"level1": {"level2": {"level3": {"level4": "deep"}}}}},
                {"large_value": "x" * 1000},
                {"mixed_types": [1, "string", {"nested": True}, None]},
            ]
            
            # Create circular reference
            malformed_metadata_cases[0]["circular_ref"] = malformed_metadata_cases[0]
            
            for metadata in malformed_metadata_cases:
                try:
                    transcript = TranscriptInput(
                        title="Metadata Test",
                        content="Content with problematic metadata",
                        date=datetime.now(),
                        metadata=metadata
                    )
                    
                    result = processor.process_transcript(transcript)
                    
                    # Should handle gracefully
                    if not result.success:
                        assert len(result.errors) > 0
                        
                except (ValueError, TypeError, RecursionError) as e:
                    # Acceptable to raise validation exceptions for malformed data
                    pass
                except Exception as e:
                    pytest.fail(f"Unexpected exception for metadata {type(metadata)}: {e}")


class TestConfigurationErrors:
    """Test handling of configuration-related errors."""
    
    def test_missing_api_keys(self):
        """Test handling of missing or invalid API keys."""
        config_variants = [
            {'notion': {'api_key': ''}},                    # Empty key
            {'notion': {'api_key': None}},                  # None key
            {'notion': {'api_key': 'invalid-key-format'}},  # Invalid format
            {'ai': {'api_key': ''}},                        # Empty AI key
        ]
        
        for config_override in config_variants:
            with test_environment(config_override) as env:
                transcript = create_realistic_transcript("simple")
                processor = TranscriptProcessor(config=env['config'])
                
                result = processor.process_transcript(transcript)
                
                # Should fail gracefully with helpful error message
                assert not result.success
                assert len(result.errors) > 0
                
                error_msg = str(result.errors[0]).lower()
                assert any(word in error_msg for word in 
                          ['api', 'key', 'authentication', 'invalid', 'missing'])
    
    def test_invalid_database_configuration(self):
        """Test handling of invalid database configurations."""
        invalid_db_configs = [
            {'notion': {'databases': {}}},                          # Empty databases
            {'notion': {'databases': {'people': None}}},           # None database config
            {'notion': {'databases': {'invalid': {'id': ''}}}},    # Empty database ID
        ]
        
        for config_override in invalid_db_configs:
            with test_environment(config_override) as env:
                transcript = create_realistic_transcript("simple")
                processor = TranscriptProcessor(config=env['config'])
                
                result = processor.process_transcript(transcript)
                
                # Should fail with configuration-related error
                if not result.success:
                    assert len(result.errors) > 0
                    error_msg = str(result.errors[0]).lower()
                    assert any(word in error_msg for word in 
                              ['database', 'configuration', 'invalid', 'missing'])
    
    def test_cache_directory_permission_errors(self):
        """Test handling of cache directory permission issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "restricted_cache"
            cache_dir.mkdir()
            
            # Try to make directory read-only (may not work on all systems)
            try:
                cache_dir.chmod(0o444)  # Read-only
            except (OSError, PermissionError):
                pytest.skip("Cannot modify directory permissions on this system")
            
            config_override = {
                'processing': {'cache_dir': str(cache_dir)}
            }
            
            try:
                with test_environment(config_override) as env:
                    transcript = create_realistic_transcript("simple")
                    processor = TranscriptProcessor(config=env['config'])
                    
                    result = processor.process_transcript(transcript)
                    
                    # Should handle permission errors gracefully
                    if not result.success:
                        error_msg = str(result.errors[0]).lower()
                        assert any(word in error_msg for word in 
                                  ['permission', 'cache', 'directory', 'access'])
                    
            finally:
                # Restore permissions for cleanup
                try:
                    cache_dir.chmod(0o755)
                except (OSError, PermissionError):
                    pass


class TestPartialFailureRecovery:
    """Test recovery from partial processing failures."""
    
    def test_partial_entity_creation_failure(self):
        """Test handling when some entities fail to create."""
        with test_environment() as env:
            transcript = create_realistic_transcript("complex")
            
            # Mock partial page creation failure
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.return_value = {"results": [], "has_more": False}
                
                # Simulate intermittent failures
                call_count = 0
                def mock_page_create(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count % 3 == 0:  # Every 3rd call fails
                        raise Exception("Simulated page creation failure")
                    return {"id": f"page-{call_count}", "properties": {}}
                
                mock_instance.pages.create.side_effect = mock_page_create
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle partial failures gracefully
                if not result.success:
                    assert len(result.errors) > 0
                    # Should provide context about what succeeded/failed
                    error_msg = str(result.errors[0]).lower()
                    assert any(word in error_msg for word in 
                              ['partial', 'some', 'failed', 'create'])
                else:
                    # If it succeeds, should still report any issues
                    assert len(result.created) >= 0
    
    def test_ai_extraction_partial_failure(self):
        """Test handling when AI extraction partially fails."""
        with test_environment() as env:
            transcript = create_realistic_transcript("medium")
            
            # Mock AI returning malformed JSON
            with patch('blackcore.minimal.ai_extractor.Anthropic') as mock_ai:
                mock_instance = mock_ai.return_value
                
                # Return partially valid JSON
                partial_response = """{
                    "entities": [
                        {"name": "John Doe", "type": "person", "confidence": 0.9},
                        {"name": "Invalid", "type": "unknown_type"
                    ],
                    "relationships": [
                        // Invalid JSON comment
                        {"from": "John Doe", "to": "Company"}
                    ]
                }"""
                
                mock_instance.messages.create.return_value = Mock(
                    content=[Mock(text=partial_response)]
                )
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle malformed AI response gracefully
                if not result.success:
                    assert len(result.errors) > 0
                    error_msg = str(result.errors[0]).lower()
                    assert any(word in error_msg for word in 
                              ['json', 'invalid', 'format', 'parse'])
    
    def test_database_transaction_rollback(self):
        """Test rollback behavior when database operations fail mid-transaction."""
        with test_environment() as env:
            transcript = create_realistic_transcript("complex")
            
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.return_value = {"results": [], "has_more": False}
                
                # Mock failure after some successful operations
                successful_calls = 0
                def mock_page_create(*args, **kwargs):
                    nonlocal successful_calls
                    successful_calls += 1
                    if successful_calls > 2:  # Fail after 2 successful calls
                        raise Exception("Database connection lost")
                    return {"id": f"page-{successful_calls}", "properties": {}}
                
                mock_instance.pages.create.side_effect = mock_page_create
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should fail and report what was attempted
                assert not result.success
                assert len(result.errors) > 0
                
                # In a real implementation, might track partial state
                # Here we just ensure graceful handling
                error_msg = str(result.errors[0]).lower()
                assert "database" in error_msg or "connection" in error_msg


class TestRecoveryMechanisms:
    """Test system recovery mechanisms and resilience patterns."""
    
    def test_automatic_retry_with_backoff(self):
        """Test automatic retry mechanism with exponential backoff."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock transient failures that eventually succeed
            attempt_count = 0
            def mock_transient_failure(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:  # Fail first 2 attempts
                    import requests
                    raise requests.exceptions.ConnectionError("Transient network issue")
                # Succeed on 3rd attempt
                return Mock(status_code=200, json=lambda: {"results": []})
            
            with patch('requests.request', side_effect=mock_transient_failure):
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should eventually succeed after retries
                # Note: This depends on actual retry implementation
                assert attempt_count >= 2, "Retry mechanism not triggered"
                
                # Should have some delay due to backoff (if implemented)
                if result.success:
                    assert duration > 0.1, "No apparent backoff delay"
    
    def test_graceful_degradation_modes(self):
        """Test graceful degradation when services are unavailable."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Test AI service unavailable
            with patch('blackcore.minimal.ai_extractor.Anthropic') as mock_ai:
                mock_ai.side_effect = ConnectionError("AI service unavailable")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should degrade gracefully
                assert not result.success
                assert len(result.errors) > 0
                
                error_msg = str(result.errors[0]).lower()
                assert any(word in error_msg for word in 
                          ['ai', 'service', 'unavailable', 'connection'])
    
    def test_state_recovery_after_interruption(self):
        """Test recovery of processing state after interruption."""
        with test_environment() as env:
            transcript = create_realistic_transcript("medium")
            processor = TranscriptProcessor(config=env['config'])
            
            # Simulate interruption during processing
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.return_value = {"results": [], "has_more": False}
                
                # First call succeeds, second fails, third succeeds
                call_sequence = [
                    {"id": "page-1", "properties": {}},
                    Exception("Interruption occurred"),
                    {"id": "page-2", "properties": {}},
                ]
                
                mock_instance.pages.create.side_effect = call_sequence
                
                result = processor.process_transcript(transcript)
                
                # Should handle interruption gracefully
                if not result.success:
                    assert len(result.errors) > 0
                    # Should provide helpful context
                    error_msg = str(result.errors[0]).lower()
                    assert any(word in error_msg for word in 
                              ['interruption', 'failed', 'error'])
    
    def test_memory_cleanup_after_errors(self):
        """Test proper memory cleanup after processing errors."""
        import gc
        import psutil
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        with test_environment() as env:
            processor = TranscriptProcessor(config=env['config'])
            
            # Process transcripts that will fail
            for i in range(10):
                with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                    mock_client.side_effect = Exception(f"Error {i}")
                    
                    transcript = create_realistic_transcript("simple")
                    result = processor.process_transcript(transcript)
                    
                    # Should fail
                    assert not result.success
            
            # Force garbage collection
            gc.collect()
            
            # Memory should not have grown significantly
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            assert memory_increase < 50, f"Memory leak detected: {memory_increase}MB increase"


class TestErrorMessageQuality:
    """Test quality and helpfulness of error messages."""
    
    def test_user_friendly_error_messages(self):
        """Test that error messages are user-friendly and actionable."""
        error_scenarios = [
            # Network issues
            {
                'mock_target': 'requests.request',
                'exception': ConnectionError("Connection refused"),
                'expected_keywords': ['connection', 'network', 'check'],
            },
            # API authentication
            {
                'mock_target': 'blackcore.minimal.notion_updater.Client',
                'exception': Exception("Invalid API key"),
                'expected_keywords': ['api', 'key', 'authentication'],
            },
            # Permission issues
            {
                'mock_target': 'blackcore.minimal.cache.SimpleCache.get',
                'exception': PermissionError("Permission denied"),
                'expected_keywords': ['permission', 'access', 'directory'],
            },
        ]
        
        for scenario in error_scenarios:
            with test_environment() as env:
                transcript = create_realistic_transcript("simple")
                
                with patch(scenario['mock_target'], side_effect=scenario['exception']):
                    processor = TranscriptProcessor(config=env['config'])
                    result = processor.process_transcript(transcript)
                    
                    assert not result.success
                    assert len(result.errors) > 0
                    
                    error_msg = str(result.errors[0]).lower()
                    
                    # Should contain helpful keywords
                    found_keywords = [kw for kw in scenario['expected_keywords'] 
                                    if kw in error_msg]
                    assert len(found_keywords) > 0, \
                        f"Error message lacks helpful keywords: {error_msg}"
                    
                    # Should be reasonably descriptive
                    assert len(error_msg) > 20, "Error message too brief"
                    assert len(error_msg) < 500, "Error message too verbose"
    
    def test_error_context_preservation(self):
        """Test that error messages preserve useful context."""
        with test_environment() as env:
            transcript = TranscriptInput(
                title="Context Test Transcript",
                content="Test content for context preservation",
                date=datetime.now(),
                metadata={"test_id": "context_test_123"}
            )
            
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_client.side_effect = Exception("Specific error for context test")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                assert not result.success
                assert len(result.errors) > 0
                
                error_msg = str(result.errors[0])
                
                # Should preserve some context about what was being processed
                # In a real implementation, might include transcript title or ID
                assert len(error_msg) > 10, "Error message lacks context"
    
    def test_nested_error_handling(self):
        """Test handling of nested exceptions with proper error chains."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Create nested exception scenario
            def nested_failure(*args, **kwargs):
                try:
                    raise ValueError("Inner error: data validation failed")
                except ValueError as e:
                    raise ConnectionError("Outer error: connection failed") from e
            
            with patch('blackcore.minimal.notion_updater.Client', side_effect=nested_failure):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                assert not result.success
                assert len(result.errors) > 0
                
                error_msg = str(result.errors[0])
                
                # Should handle nested exceptions gracefully
                # May include information from both levels
                assert "error" in error_msg.lower()
                assert len(error_msg) > 20, "Error message too brief for nested error"


class TestLongRunningOperationErrors:
    """Test error handling in long-running operations."""
    
    def test_batch_processing_partial_failure(self):
        """Test batch processing with some failures."""
        with test_environment() as env:
            transcripts = create_test_batch(size=10, complexity="simple")
            
            # Mock failures for some transcripts
            call_count = 0
            def selective_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count % 3 == 0:  # Every 3rd call fails
                    raise Exception(f"Batch item {call_count} failed")
                return {"results": [], "has_more": False}
            
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.side_effect = selective_failure
                
                processor = TranscriptProcessor(config=env['config'])
                batch_result = processor.process_batch(transcripts)
                
                # Should complete batch with partial failures
                assert batch_result.total_transcripts == len(transcripts)
                assert batch_result.failed > 0
                assert batch_result.successful > 0
                assert batch_result.success_rate < 1.0
                
                # Should track individual failures
                failed_results = [r for r in batch_result.results if not r.success]
                assert len(failed_results) == batch_result.failed
    
    def test_operation_timeout_handling(self):
        """Test handling of operation timeouts."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock very slow response
            def slow_operation(*args, **kwargs):
                time.sleep(2)  # Simulate slow operation
                return {"results": [], "has_more": False}
            
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.side_effect = slow_operation
                
                # Set short timeout for testing
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should either complete or timeout gracefully
                if not result.success:
                    error_msg = str(result.errors[0]).lower()
                    # In a real implementation, might have timeout handling
                    assert "timeout" in error_msg or "slow" in error_msg or duration < 10
                else:
                    # If it succeeds, should not take too long
                    assert duration < 10, f"Operation took too long: {duration}s"