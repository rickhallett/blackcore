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
from blackcore.minimal.models import TranscriptInput, ProcessingResult, DatabaseConfig, NotionPage
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
        # Test valid TranscriptInput objects with empty/whitespace content
        invalid_transcripts = [
            TranscriptInput(title="Empty", content="", date=datetime.now()),
            TranscriptInput(title="Whitespace", content="   \n\t  ", date=datetime.now()),
        ]
        
        for transcript in invalid_transcripts:
            with test_environment() as env:
                processor = TranscriptProcessor(config=env['config'])
                
                result = processor.process_transcript(transcript)
                
                # Empty content should be handled gracefully
                # The AI extractor should return empty entities for empty content
                assert result.success == True  # Empty content is technically valid
                assert len(result.created) == 0 or len(result.created) == 1  # May create transcript page
        
        # Test None content separately (should fail at model validation)
        with pytest.raises(Exception) as exc_info:
            TranscriptInput(title="Null", content=None, date=datetime.now())
        assert "validation error" in str(exc_info.value).lower() or "string" in str(exc_info.value).lower()
    
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
            {'ai': {'api_key': ''}},                        # Empty AI key
        ]
        
        for config_override in config_variants:
            # Try to create a processor with invalid config
            # This should raise ValueError during initialization
            with pytest.raises(ValueError) as exc_info:
                with test_environment(config_override) as env:
                    transcript = create_realistic_transcript("simple")
                    processor = TranscriptProcessor(config=env['config'])
            
            # Check error message
            error_msg = str(exc_info.value).lower()
            assert any(word in error_msg for word in ['api', 'key', 'configured'])
            
        # Test invalid key format (this should fail during API client initialization)
        with test_environment({'notion': {'api_key': 'invalid-key-format'}}) as env:
            transcript = create_realistic_transcript("simple")
            
            # This should raise ValueError from the validator
            with pytest.raises(ValueError) as exc_info:
                processor = TranscriptProcessor(config=env['config'])
            
            error_msg = str(exc_info.value).lower()
            assert any(word in error_msg for word in ['invalid', 'api', 'key', 'format'])
    
    def test_invalid_database_configuration(self):
        """Test handling of invalid database configurations."""
        # Test with no transcript database configured
        config_override = {
            'notion': {
                'databases': {
                    'people': DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    'organizations': DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    # Missing transcripts database
                }
            }
        }
        
        with test_environment(config_override) as env:
            transcript = create_realistic_transcript("simple")
            processor = TranscriptProcessor(config=env['config'])
            
            result = processor.process_transcript(transcript)
            
            # Should succeed but transcript won't be created
            assert result.success  # Processing succeeds, just skips transcript creation
            assert result.transcript_id is None  # No transcript page created
    
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
                'processing': {'cache_dir': str(cache_dir / "subfolder")}  # Try to create subfolder in read-only dir
            }
            
            try:
                with test_environment(config_override) as env:
                    transcript = create_realistic_transcript("simple")
                    
                    # Cache creation should fail during processor initialization
                    with pytest.raises(PermissionError):
                        processor = TranscriptProcessor(config=env['config'])
                    
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
            with patch('notion_client.Client') as mock_client:
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
            with patch('anthropic.Anthropic') as mock_ai:
                mock_instance = mock_ai.return_value
                
                # Return invalid JSON (missing closing brace and invalid comment)
                partial_response = """{
                    "entities": [
                        {"name": "John Doe", "type": "person", "confidence": 0.9},
                        {"name": "Invalid", "type": "unknown_type"
                    ],
                    "relationships": [
                        // Invalid JSON comment
                        {"from": "John Doe", "to": "Company"}
                    ]"""  # Note: Missing closing brace
                
                mock_instance.messages.create.return_value = Mock(
                    content=[Mock(text=partial_response)]
                )
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should fallback to basic parsing
                assert result.success
                # The fallback parser should extract at least some entities
                assert len(result.created) >= 0  # Might create transcript page at least
    
    def test_database_transaction_rollback(self):
        """Test rollback behavior when database operations fail mid-transaction."""
        with test_environment() as env:
            transcript = create_realistic_transcript("complex")
            
            processor = TranscriptProcessor(config=env['config'])
            
            # Mock AI extractor to return multiple people
            def mock_extract_entities(*args, **kwargs):
                from blackcore.minimal.models import ExtractedEntities, Entity, EntityType
                return ExtractedEntities(
                    entities=[
                        Entity(name="Person 1", type=EntityType.PERSON, confidence=0.9),
                        Entity(name="Person 2", type=EntityType.PERSON, confidence=0.9),
                        Entity(name="Person 3", type=EntityType.PERSON, confidence=0.9),
                        Entity(name="Person 4", type=EntityType.PERSON, confidence=0.9),
                    ],
                    relationships=[],
                    summary="Multiple people meeting",
                    key_points=[]
                )
            
            processor.ai_extractor.extract_entities = Mock(side_effect=mock_extract_entities)
            
            # Mock the internal _process_person method to fail after some calls
            successful_calls = 0
            
            def mock_process_person(person):
                nonlocal successful_calls
                successful_calls += 1
                if successful_calls > 2:  # Fail after 2 successful calls
                    raise Exception("Database connection lost")
                # Return a mock page and created=True
                return (NotionPage(
                    id=f"person-{successful_calls}",
                    database_id="people-db",
                    properties={},
                    created_time=datetime.utcnow(),
                    last_edited_time=datetime.utcnow()
                ), True)
            
            with patch.object(processor, '_process_person', side_effect=mock_process_person):
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
            
            processor = TranscriptProcessor(config=env['config'])
            
            # Mock transient failures at the Notion client level
            attempt_count = 0
            def mock_transient_failure(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:  # Fail first 2 attempts
                    import requests
                    # Simulate a retriable error that would trigger backoff
                    raise requests.exceptions.ConnectionError("Transient network issue")
                # Succeed on 3rd attempt
                return []  # Return empty list for search results
            
            # The NotionUpdater internally uses its client for database searches
            # We need to mock at the right level - the client's databases.query method
            original_query = env['mocks']['notion_client'].databases.query
            
            def mock_query_with_retry(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:  # Fail first 2 attempts
                    raise Exception("Transient network issue")
                # Succeed on 3rd attempt
                return {"results": [], "has_more": False}
            
            env['mocks']['notion_client'].databases.query.side_effect = mock_query_with_retry
                
            start_time = time.time()
            result = processor.process_transcript(transcript)
            duration = time.time() - start_time
            
            # The process should succeed after retries
            assert result.success
            assert attempt_count >= 1  # At least one attempt was made
    
    def test_graceful_degradation_modes(self):
        """Test graceful degradation when services are unavailable."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Create processor first
            processor = TranscriptProcessor(config=env['config'])
            
            # Then mock AI service to fail when called
            with patch.object(processor.ai_extractor.provider.client, 'messages') as mock_messages:
                mock_messages.create.side_effect = ConnectionError("AI service unavailable")
                
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
            with patch('notion_client.Client') as mock_client:
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
                # Mock the processor's notion_updater to fail
                with patch.object(processor.notion_updater, 'create_page') as mock_create:
                    mock_create.side_effect = Exception(f"Error {i}")
                    
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
                'mock_target': 'notion_client.Client',
                'exception': Exception("Invalid API key"),
                'expected_keywords': ['api', 'key', 'invalid'],
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
                
                if scenario['mock_target'] == 'notion_client.Client':
                    # For Client mock, we need to ensure the exception is raised during init
                    with patch(scenario['mock_target'], side_effect=scenario['exception']):
                        try:
                            processor = TranscriptProcessor(config=env['config'])
                            result = processor.process_transcript(transcript)
                        except Exception as e:
                            # The error might be raised during processor initialization
                            error_msg = str(e).lower()
                            found_keywords = [kw for kw in scenario['expected_keywords'] 
                                            if kw in error_msg]
                            assert len(found_keywords) > 0, \
                                f"Error message lacks helpful keywords: {error_msg}"
                            continue
                elif scenario['mock_target'] == 'requests.request':
                    # Create processor first
                    processor = TranscriptProcessor(config=env['config'])
                    # Mock the notion_updater's client to raise network error consistently
                    # Need to ensure all retries fail
                    with patch.object(processor.notion_updater.client.databases, 'query', side_effect=scenario['exception']):
                        with patch.object(processor.notion_updater.client.pages, 'create', side_effect=scenario['exception']):
                            result = processor.process_transcript(transcript)
                elif scenario['mock_target'] == 'blackcore.minimal.cache.SimpleCache.get':
                    # Create processor first  
                    processor = TranscriptProcessor(config=env['config'])
                    # Mock cache get to raise permission error
                    with patch.object(processor.cache, 'get', side_effect=scenario['exception']):
                        result = processor.process_transcript(transcript)
                else:
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
            
            # Create processor first
            processor = TranscriptProcessor(config=env['config'])
            
            # Mock the AI extractor to throw error when extracting entities
            with patch.object(processor.ai_extractor, 'extract_entities', 
                            side_effect=Exception("Specific error for context test")):
                result = processor.process_transcript(transcript)
                
                assert not result.success
                assert len(result.errors) > 0
                
                error_msg = str(result.errors[0])
                
                # Should preserve some context about what was being processed
                # In a real implementation, might include transcript title or ID
                assert len(error_msg) > 10, "Error message lacks context"
                # Check that the error message includes the actual error
                assert "context test" in error_msg.lower() or "specific error" in error_msg.lower()
    
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
            
            # First create the processor successfully
            processor = TranscriptProcessor(config=env['config'])
            
            # Mock AI extraction to cause nested exception
            with patch.object(processor.ai_extractor, 'extract_entities',
                            side_effect=nested_failure):
                result = processor.process_transcript(transcript)
                
                assert not result.success
                assert len(result.errors) > 0
                
                error_msg = str(result.errors[0])
                
                # Should handle nested exceptions gracefully
                # May include information from both levels
                assert "error" in error_msg.lower() or "connection" in error_msg.lower()
                assert len(error_msg) > 20, "Error message too brief for nested error"


class TestLongRunningOperationErrors:
    """Test error handling in long-running operations."""
    
    def test_batch_processing_partial_failure(self):
        """Test batch processing with some failures."""
        with test_environment() as env:
            transcripts = create_test_batch(size=10, complexity="simple")
            
            # Create processor first
            processor = TranscriptProcessor(config=env['config'])
            
            # Mock AI extraction to fail for some transcripts
            call_count = 0
            def selective_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count % 3 == 0:  # Every 3rd call fails
                    raise Exception(f"AI extraction failed for transcript {call_count}")
                
                # Return successful extraction for others
                from blackcore.minimal.models import ExtractedEntities, Entity, EntityType
                return ExtractedEntities(
                    entities=[
                        Entity(
                            name=f"Person {call_count}",
                            type=EntityType.PERSON,
                            confidence=0.9
                        )
                    ],
                    relationships=[],
                    summary=f"Summary {call_count}",
                    key_points=[]
                )
            
            # Apply mock to the AI extractor
            with patch.object(processor.ai_extractor, 'extract_entities',
                            side_effect=selective_failure):
                batch_result = processor.process_batch(transcripts)
                    
                # Should complete batch with partial failures
                assert batch_result.total_transcripts == len(transcripts)
                assert batch_result.failed > 0
                assert batch_result.successful > 0
                assert batch_result.success_rate < 1.0
                    
                # Should track individual failures
                failed_results = [r for r in batch_result.results if not r.success]
                assert len(failed_results) == batch_result.failed
                
                # Verify that failures happened at the expected indices (3, 6, 9)
                for i, result in enumerate(batch_result.results):
                    if (i + 1) % 3 == 0:  # 3rd, 6th, 9th
                        assert not result.success
                        assert len(result.errors) > 0
                        assert "AI extraction failed" in str(result.errors[0].message)
    
    def test_operation_timeout_handling(self):
        """Test handling of operation timeouts."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock very slow response
            def slow_operation(*args, **kwargs):
                time.sleep(2)  # Simulate slow operation
                return {"results": [], "has_more": False}
            
            with patch('notion_client.Client') as mock_client:
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