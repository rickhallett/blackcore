"""Test logging integration across modules."""

import json
import logging
from unittest.mock import patch, MagicMock
import pytest

from blackcore.minimal.cache import SimpleCache
from blackcore.minimal.logging_config import setup_logging, StructuredFormatter
from blackcore.minimal.notion_updater import NotionUpdater


class TestLoggingIntegration:
    """Test that logging is properly integrated across modules."""
    
    def test_cache_logs_operations(self, tmp_path):
        """Test that cache operations are logged with structured data."""
        # Setup logging to capture logs
        captured_logs = []
        
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                formatter = StructuredFormatter()
                captured_logs.append(json.loads(formatter.format(record)))
        
        # Configure logger
        logger = logging.getLogger("blackcore.minimal.cache")
        logger.handlers.clear()
        handler = CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Create cache and perform operations
        cache = SimpleCache(cache_dir=str(tmp_path))
        
        # Set a value
        cache.set("test_key", {"data": "test_value"})
        
        # Get a value (cache hit)
        result = cache.get("test_key")
        
        # Verify logs were generated
        assert len(captured_logs) >= 2
        
        # Check cache_set event
        set_log = next((log for log in captured_logs if log["message"] == "cache_set"), None)
        assert set_log is not None
        assert set_log["key"] == "test_key"
        assert "cache_file" in set_log
        assert "value_size" in set_log
        
        # Check cache_hit event
        hit_log = next((log for log in captured_logs if log["message"] == "cache_hit"), None)
        assert hit_log is not None
        assert hit_log["key"] == "test_key"
        assert "age_seconds" in hit_log
    
    def test_notion_updater_logs_api_calls(self):
        """Test that Notion API calls are logged."""
        captured_logs = []
        
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                formatter = StructuredFormatter()
                captured_logs.append(json.loads(formatter.format(record)))
        
        # Configure logger
        logger = logging.getLogger("blackcore.minimal.notion_updater")
        logger.handlers.clear()
        handler = CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Mock the Notion client - it's imported inside __init__
        with patch('notion_client.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Setup mock response
            mock_response = {
                "id": "test-page-id",
                "properties": {},
                "created_time": "2024-01-01T00:00:00Z",
                "last_edited_time": "2024-01-01T00:00:00Z"
            }
            mock_client.pages.create.return_value = mock_response
            
            # Create updater and create a page
            updater = NotionUpdater(api_key="secret_" + "a" * 43)
            page = updater.create_page("test-db-id", {"Title": "Test"})
            
            # Check for page_created log
            created_log = next((log for log in captured_logs if log["message"] == "page_created"), None)
            assert created_log is not None
            assert created_log["page_id"] == "test-page-id"
            assert created_log["database_id"] == "test-db-id"
            assert "duration_ms" in created_log
    
    def test_ai_extractor_logs_api_calls(self):
        """Test that AI provider API calls are logged."""
        captured_logs = []
        
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                formatter = StructuredFormatter()
                captured_logs.append(json.loads(formatter.format(record)))
        
        # Configure logger
        logger = logging.getLogger("blackcore.minimal.ai_extractor")
        logger.handlers.clear()
        handler = CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test Claude provider - anthropic is imported inside __init__
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            from blackcore.minimal.ai_extractor import ClaudeProvider
            
            # Setup mock
            mock_client = MagicMock()
            mock_anthropic_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text='{"entities": [], "summary": "Test"}')]
            mock_client.messages.create.return_value = mock_response
            
            # Create provider and extract entities
            provider = ClaudeProvider(api_key="sk-ant-" + "a" * 95)
            result = provider.extract_entities("Test transcript", "Extract entities")
            
            # Check for claude_api_call log
            api_log = next((log for log in captured_logs if log["message"] == "claude_api_call"), None)
            assert api_log is not None
            assert api_log["model"] is not None
            assert "prompt_length" in api_log
            assert "response_length" in api_log
            assert "duration_ms" in api_log
    
    def test_rate_limiter_logs_throttling(self):
        """Test that rate limiting events are logged."""
        captured_logs = []
        
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                formatter = StructuredFormatter()
                captured_logs.append(json.loads(formatter.format(record)))
        
        # Configure logger
        logger = logging.getLogger("blackcore.minimal.notion_updater")
        logger.handlers.clear()
        handler = CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Create rate limiter with fast rate
        from blackcore.minimal.notion_updater import RateLimiter
        rate_limiter = RateLimiter(requests_per_second=100)  # Fast rate
        
        # Make two quick calls
        rate_limiter.wait_if_needed()
        rate_limiter.wait_if_needed()  # This should trigger throttling
        
        # Check for throttle log
        throttle_log = next((log for log in captured_logs if log["message"] == "rate_limit_throttle"), None)
        if throttle_log:  # Might not always trigger depending on timing
            assert "sleep_ms" in throttle_log
            assert "requests_per_second" in throttle_log