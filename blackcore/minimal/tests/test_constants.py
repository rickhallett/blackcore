"""Test that magic numbers are properly extracted to constants."""

import pytest
from blackcore.minimal import constants
from blackcore.minimal.notion_updater import NotionUpdater, RateLimiter
from blackcore.minimal.cache import SimpleCache
from blackcore.minimal.ai_extractor import ClaudeProvider, OpenAIProvider
from blackcore.minimal.config import ConfigManager


class TestConstants:
    """Test suite for constants usage."""
    
    def test_rate_limiter_constants(self):
        """Test that RateLimiter uses constants instead of magic numbers."""
        # Check that constants exist
        assert hasattr(constants, 'DEFAULT_RATE_LIMIT')
        assert constants.DEFAULT_RATE_LIMIT == 3.0
        
        # RateLimiter should use the constant
        rate_limiter = RateLimiter()
        assert rate_limiter.min_interval == 1.0 / constants.DEFAULT_RATE_LIMIT
    
    def test_notion_updater_constants(self):
        """Test that NotionUpdater uses constants for configuration."""
        # Check constants
        assert hasattr(constants, 'DEFAULT_RETRY_ATTEMPTS')
        assert hasattr(constants, 'DEFAULT_POOL_CONNECTIONS')
        assert hasattr(constants, 'DEFAULT_POOL_MAXSIZE')
        assert hasattr(constants, 'CONNECT_TIMEOUT')
        assert hasattr(constants, 'READ_TIMEOUT')
        assert hasattr(constants, 'NOTION_API_VERSION')
        
        assert constants.DEFAULT_RETRY_ATTEMPTS == 3
        assert constants.DEFAULT_POOL_CONNECTIONS == 10
        assert constants.DEFAULT_POOL_MAXSIZE == 10
        assert constants.CONNECT_TIMEOUT == 10.0
        assert constants.READ_TIMEOUT == 60.0
        assert constants.NOTION_API_VERSION == "2022-06-28"
    
    def test_cache_constants(self):
        """Test that SimpleCache uses constants."""
        # Check constants
        assert hasattr(constants, 'DEFAULT_CACHE_TTL')
        assert hasattr(constants, 'CACHE_FILE_PERMISSIONS')
        assert hasattr(constants, 'CACHE_DIR_PERMISSIONS')
        
        assert constants.DEFAULT_CACHE_TTL == 3600
        assert constants.CACHE_FILE_PERMISSIONS == 0o600
        assert constants.CACHE_DIR_PERMISSIONS == 0o700
    
    def test_ai_provider_constants(self):
        """Test that AI providers use constants."""
        # Check constants
        assert hasattr(constants, 'CLAUDE_DEFAULT_MODEL')
        assert hasattr(constants, 'OPENAI_DEFAULT_MODEL')
        assert hasattr(constants, 'AI_MAX_TOKENS')
        assert hasattr(constants, 'AI_TEMPERATURE')
        
        assert constants.CLAUDE_DEFAULT_MODEL == "claude-3-sonnet-20240229"
        assert constants.OPENAI_DEFAULT_MODEL == "gpt-4"
        assert constants.AI_MAX_TOKENS == 4000
        assert constants.AI_TEMPERATURE == 0.3
    
    def test_config_constants(self):
        """Test that ConfigManager uses constants."""
        # Check constants  
        assert hasattr(constants, 'DEFAULT_BATCH_SIZE')
        assert hasattr(constants, 'DEDUPLICATION_THRESHOLD')
        assert hasattr(constants, 'LLM_SCORER_TEMPERATURE')
        assert hasattr(constants, 'LLM_SCORER_BATCH_SIZE')
        
        assert constants.DEFAULT_BATCH_SIZE == 10
        assert constants.DEDUPLICATION_THRESHOLD == 90.0
        assert constants.LLM_SCORER_TEMPERATURE == 0.1
        assert constants.LLM_SCORER_BATCH_SIZE == 5
    
    def test_api_key_validation_constants(self):
        """Test that API key validation uses constants."""
        # Check constants
        assert hasattr(constants, 'NOTION_KEY_PREFIX')
        assert hasattr(constants, 'NOTION_KEY_LENGTH')
        assert hasattr(constants, 'ANTHROPIC_KEY_PREFIX')
        assert hasattr(constants, 'ANTHROPIC_KEY_LENGTH')
        assert hasattr(constants, 'OPENAI_KEY_PREFIX')
        assert hasattr(constants, 'OPENAI_KEY_LENGTH')
        
        assert constants.NOTION_KEY_PREFIX == "secret_"
        assert constants.NOTION_KEY_LENGTH == 43
        assert constants.ANTHROPIC_KEY_PREFIX == "sk-ant-"
        assert constants.ANTHROPIC_KEY_LENGTH == 95
        assert constants.OPENAI_KEY_PREFIX == "sk-"
        assert constants.OPENAI_KEY_LENGTH == 48
    
    def test_http_status_codes(self):
        """Test that HTTP status codes are constants."""
        # Check constants
        assert hasattr(constants, 'HTTP_TOO_MANY_REQUESTS')
        assert hasattr(constants, 'HTTP_INTERNAL_SERVER_ERROR')
        assert hasattr(constants, 'HTTP_BAD_GATEWAY')
        assert hasattr(constants, 'HTTP_SERVICE_UNAVAILABLE')
        assert hasattr(constants, 'HTTP_GATEWAY_TIMEOUT')
        
        assert constants.HTTP_TOO_MANY_REQUESTS == 429
        assert constants.HTTP_INTERNAL_SERVER_ERROR == 500
        assert constants.HTTP_BAD_GATEWAY == 502
        assert constants.HTTP_SERVICE_UNAVAILABLE == 503
        assert constants.HTTP_GATEWAY_TIMEOUT == 504
    
    def test_retry_strategy_constants(self):
        """Test retry strategy constants."""
        # Check constants
        assert hasattr(constants, 'RETRY_TOTAL_ATTEMPTS')
        assert hasattr(constants, 'RETRY_BACKOFF_FACTOR')
        assert hasattr(constants, 'RETRY_STATUS_FORCELIST')
        
        assert constants.RETRY_TOTAL_ATTEMPTS == 3
        assert constants.RETRY_BACKOFF_FACTOR == 1
        assert constants.RETRY_STATUS_FORCELIST == [429, 500, 502, 503, 504]
    
    def test_prompt_injection_patterns(self):
        """Test prompt injection pattern constants."""
        # Check constants
        assert hasattr(constants, 'PROMPT_INJECTION_PATTERNS')
        
        expected_patterns = [
            "\n\nHuman:",
            "\n\nAssistant:",
            "\n\nSystem:",
            "\n\nUser:",
            "\n\nAI:",
        ]
        assert constants.PROMPT_INJECTION_PATTERNS == expected_patterns
    
    def test_notion_property_limits(self):
        """Test Notion property limit constants."""
        # Check constants
        assert hasattr(constants, 'NOTION_TEXT_LIMIT')
        assert hasattr(constants, 'NOTION_ARRAY_LIMIT')
        assert hasattr(constants, 'NOTION_PAGE_SIZE_LIMIT')
        
        assert constants.NOTION_TEXT_LIMIT == 2000
        assert constants.NOTION_ARRAY_LIMIT == 100
        assert constants.NOTION_PAGE_SIZE_LIMIT == 100