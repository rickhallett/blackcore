"""High-ROI network resilience tests for production reliability.

These tests simulate common network issues that occur in production environments
and validate that the system handles them gracefully.
"""

import pytest
import time
import requests
from unittest.mock import patch, MagicMock, Mock
from requests.exceptions import ConnectionError, Timeout, HTTPError

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput
from blackcore.minimal.notion_updater import NotionUpdater
from blackcore.minimal.ai_extractor import AIExtractor

from .infrastructure import (
    test_environment,
    create_realistic_transcript,
    FailureSimulator
)


class TestNetworkFailures:
    """Test handling of network failures - very high ROI tests."""
    
    def test_complete_network_failure_recovery(self):
        """Test graceful handling when network is completely unavailable."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Simulate complete network failure
            def mock_request(*args, **kwargs):
                raise ConnectionError("Network is unreachable")
            
            with patch('requests.request', side_effect=mock_request):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should fail gracefully with helpful error
                assert not result.success
                assert len(result.errors) > 0
                
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['network', 'connection', 'unreachable', 'api'])
    
    def test_intermittent_network_failures(self):
        """Test handling of flaky network connections."""
        failure_simulator = FailureSimulator()
        
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Simulate 50% failure rate
            with failure_simulator.partial_api_failure(success_rate=0.5):
                processor = TranscriptProcessor(config=env['config'])
                
                # Try multiple times to test retry behavior
                results = []
                for _ in range(5):
                    result = processor.process_transcript(transcript)
                    results.append(result.success)
                
                # Should have some successes due to retry logic
                success_rate = sum(results) / len(results)
                assert success_rate > 0, "No successes with intermittent failures"
    
    def test_api_timeout_handling(self):
        """Test handling of API timeouts."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Simulate API timeout
            def mock_timeout_request(*args, **kwargs):
                time.sleep(0.1)  # Small delay
                raise Timeout("Request timed out")
            
            with patch('requests.request', side_effect=mock_timeout_request):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle timeout gracefully
                assert not result.success
                assert len(result.errors) > 0
                
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['timeout', 'slow', 'response'])
    
    def test_slow_api_responses(self):
        """Test handling of very slow API responses."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock slow but successful responses
            def mock_slow_request(*args, **kwargs):
                time.sleep(2)  # 2 second delay
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"results": []}
                return mock_response
            
            with patch('requests.request', side_effect=mock_slow_request):
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should complete but might be slow
                # In production, we'd want timeout handling
                if result.success:
                    assert duration < 30, "Processing took too long with slow API"
    
    def test_http_error_responses(self):
        """Test handling of HTTP error responses (4xx, 5xx)."""
        error_codes = [400, 401, 403, 404, 429, 500, 502, 503, 504]
        
        for status_code in error_codes:
            with test_environment() as env:
                transcript = create_realistic_transcript("simple")
                
                # Mock HTTP error response
                def mock_http_error(*args, **kwargs):
                    mock_response = Mock()
                    mock_response.status_code = status_code
                    mock_response.raise_for_status.side_effect = HTTPError(f"HTTP {status_code}")
                    return mock_response
                
                with patch('requests.request', side_effect=mock_http_error):
                    processor = TranscriptProcessor(config=env['config'])
                    result = processor.process_transcript(transcript)
                    
                    # Should handle HTTP errors gracefully
                    assert not result.success
                    assert len(result.errors) > 0
                    
                    error_message = str(result.errors[0])
                    assert str(status_code) in error_message or "http" in error_message.lower()
    
    def test_rate_limiting_handling(self):
        """Test handling of API rate limiting."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock rate limiting response
            def mock_rate_limit(*args, **kwargs):
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.headers = {"Retry-After": "1"}
                mock_response.raise_for_status.side_effect = HTTPError("Rate limited")
                return mock_response
            
            with patch('requests.request', side_effect=mock_rate_limit):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle rate limiting
                assert not result.success
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['rate', 'limit', 'too many', '429'])


class TestNotionAPIResilience:
    """Test Notion API specific resilience scenarios."""
    
    def test_notion_database_unavailable(self):
        """Test handling when Notion database is unavailable."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock Notion database unavailable
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.side_effect = Exception("Database not found")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle database unavailability
                assert not result.success
                assert len(result.errors) > 0
    
    def test_notion_authentication_failure(self):
        """Test handling of Notion authentication failures."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock authentication failure
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_client.side_effect = Exception("Invalid API key")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle auth failure gracefully
                assert not result.success
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['authentication', 'api key', 'invalid', 'unauthorized'])
    
    def test_notion_partial_page_creation_failure(self):
        """Test handling when some pages fail to create."""
        with test_environment() as env:
            transcript = create_realistic_transcript("complex")
            
            # Mock partial page creation failure
            with patch('blackcore.minimal.notion_updater.Client') as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.databases.query.return_value = {"results": [], "has_more": False}
                
                # First page creation succeeds, second fails
                mock_instance.pages.create.side_effect = [
                    {"id": "page-123", "properties": {}},  # Success
                    Exception("Failed to create page"),    # Failure
                    {"id": "page-456", "properties": {}},  # Success
                ]
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle partial failures gracefully
                # Might succeed partially or fail completely depending on implementation
                if not result.success:
                    assert len(result.errors) > 0
    
    def test_notion_quota_exceeded(self):
        """Test handling of Notion API quota exceeded."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock quota exceeded
            def mock_quota_exceeded(*args, **kwargs):
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.headers = {"Retry-After": "3600"}  # 1 hour
                mock_response.raise_for_status.side_effect = HTTPError("Quota exceeded")
                return mock_response
            
            with patch('requests.request', side_effect=mock_quota_exceeded):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle quota gracefully
                assert not result.success
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['quota', 'limit', 'exceeded', 'rate'])


class TestAIAPIResilience:  
    """Test AI API specific resilience scenarios."""
    
    def test_ai_api_unavailable(self):
        """Test handling when AI API is unavailable."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock AI API unavailable
            with patch('blackcore.minimal.ai_extractor.Anthropic') as mock_client:
                mock_client.side_effect = ConnectionError("AI API unavailable")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle AI API unavailability
                assert not result.success
                assert len(result.errors) > 0
    
    def test_ai_invalid_response_format(self):
        """Test handling of invalid AI response format."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock invalid AI response
            with patch('blackcore.minimal.ai_extractor.Anthropic') as mock_ai:
                mock_instance = mock_ai.return_value
                mock_instance.messages.create.return_value = Mock(
                    content=[Mock(text="This is not valid JSON")]
                )
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle invalid AI response
                assert not result.success
                assert len(result.errors) > 0
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['invalid', 'json', 'format', 'response'])
    
    def test_ai_token_limit_exceeded(self):
        """Test handling of AI token limit exceeded."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock token limit exceeded
            with patch('blackcore.minimal.ai_extractor.Anthropic') as mock_ai:
                mock_instance = mock_ai.return_value
                mock_instance.messages.create.side_effect = Exception("Token limit exceeded")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle token limit gracefully
                assert not result.success
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['token', 'limit', 'exceeded', 'too long'])


class TestRecoveryMechanisms:
    """Test recovery and retry mechanisms."""
    
    def test_retry_logic_with_backoff(self):
        """Test that retry logic works with exponential backoff."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock intermittent failures that eventually succeed
            call_count = 0
            def mock_intermittent_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:  # Fail first 2 times
                    raise ConnectionError("Temporary network issue")
                # Succeed on 3rd try
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"results": []}
                return mock_response
            
            with patch('requests.request', side_effect=mock_intermittent_failure):
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should eventually succeed after retries
                # Note: This depends on actual retry implementation
                assert call_count >= 2, "Retry logic not working"
                
                # Should have some delay due to backoff
                if result.success:
                    assert duration > 0.5, "No backoff delay detected"
    
    def test_circuit_breaker_behavior(self):
        """Test circuit breaker pattern if implemented."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock consistent failures
            def mock_consistent_failure(*args, **kwargs):
                raise ConnectionError("Service is down")
            
            with patch('requests.request', side_effect=mock_consistent_failure):
                processor = TranscriptProcessor(config=env['config'])
                
                # Try multiple times to trigger circuit breaker
                results = []
                durations = []
                
                for _ in range(5):
                    start_time = time.time()
                    result = processor.process_transcript(transcript)
                    duration = time.time() - start_time
                    
                    results.append(result.success)
                    durations.append(duration)
                
                # All should fail
                assert not any(results), "Some requests succeeded unexpectedly"
                
                # Later requests might be faster if circuit breaker is open
                # Note: This test structure assumes circuit breaker implementation
    
    def test_graceful_degradation(self):
        """Test graceful degradation when services are partially available."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock AI working but Notion failing
            with patch('blackcore.minimal.notion_updater.Client') as mock_notion:
                mock_notion.side_effect = ConnectionError("Notion API down")
                
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should fail but provide useful information
                assert not result.success
                assert len(result.errors) > 0
                
                # Error should indicate which service failed
                error_message = str(result.errors[0]).lower()
                assert "notion" in error_message or "api" in error_message


class TestNetworkConditionSimulation:
    """Test various network conditions that occur in production."""
    
    def test_high_latency_handling(self):
        """Test handling of high network latency."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock high latency responses
            def mock_high_latency(*args, **kwargs):
                time.sleep(5)  # 5 second delay
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"results": []}
                return mock_response
            
            with patch('requests.request', side_effect=mock_high_latency):
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should handle high latency
                if result.success:
                    assert duration >= 5, "High latency not simulated properly"
                else:
                    # Might timeout, which is acceptable
                    error_message = str(result.errors[0]).lower()
                    assert "timeout" in error_message or "slow" in error_message
    
    def test_connection_drops_during_processing(self):
        """Test handling of connection drops during processing."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock connection that drops mid-request
            call_count = 0
            def mock_connection_drop(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call succeeds partially then drops
                    time.sleep(0.1)
                    raise ConnectionError("Connection reset by peer")
                else:
                    # Subsequent calls might succeed
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"results": []}
                    return mock_response
            
            with patch('requests.request', side_effect=mock_connection_drop):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle connection drops
                # Either succeeds on retry or fails gracefully
                if not result.success:
                    assert len(result.errors) > 0
                    error_message = str(result.errors[0]).lower()
                    assert any(word in error_message for word in 
                              ['connection', 'reset', 'dropped', 'network'])
    
    def test_dns_resolution_failures(self):
        """Test handling of DNS resolution failures."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock DNS resolution failure
            def mock_dns_failure(*args, **kwargs):
                raise ConnectionError("Name or service not known")
            
            with patch('requests.request', side_effect=mock_dns_failure):
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                
                # Should handle DNS failures gracefully
                assert not result.success
                assert len(result.errors) > 0
                
                error_message = str(result.errors[0]).lower()
                assert any(word in error_message for word in 
                          ['name', 'service', 'dns', 'resolution', 'unknown'])


# Performance impact tests
class TestNetworkFailurePerformance:
    """Test performance impact of network failures."""
    
    def test_failure_detection_speed(self):
        """Test that failures are detected quickly."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock immediate failure
            def mock_immediate_failure(*args, **kwargs):
                raise ConnectionError("Immediate failure")
            
            with patch('requests.request', side_effect=mock_immediate_failure):
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should fail quickly
                assert not result.success
                assert duration < 10, f"Failure detection too slow: {duration}s"
    
    def test_timeout_configuration_effectiveness(self):
        """Test that configured timeouts are respected."""
        with test_environment() as env:
            transcript = create_realistic_transcript("simple")
            
            # Mock hanging request
            def mock_hanging_request(*args, **kwargs):
                time.sleep(60)  # Very long delay
                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response
            
            with patch('requests.request', side_effect=mock_hanging_request):
                start_time = time.time()
                processor = TranscriptProcessor(config=env['config'])
                result = processor.process_transcript(transcript)
                duration = time.time() - start_time
                
                # Should timeout before 60 seconds
                assert duration < 30, f"Timeout not working: {duration}s"
                
                if not result.success:
                    error_message = str(result.errors[0]).lower()
                    assert "timeout" in error_message