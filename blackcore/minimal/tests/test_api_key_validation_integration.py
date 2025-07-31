"""Integration tests for API key validation in actual classes."""

import pytest

from blackcore.minimal.notion_updater import NotionUpdater
from blackcore.minimal.ai_extractor import ClaudeProvider, OpenAIProvider


class TestAPIKeyValidationIntegration:
    """Test API key validation in actual usage."""

    def test_notion_updater_validates_api_key(self):
        """Test that NotionUpdater validates API key on initialization."""
        # Invalid keys should fail validation immediately
        invalid_keys = [
            "",
            "invalid_key",
            "secret_short",
            "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",
            None,
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValueError, match="Invalid Notion API key format"):
                NotionUpdater(key)

    def test_claude_provider_validates_api_key(self):
        """Test that ClaudeProvider validates API key on initialization."""
        # Invalid keys should fail validation immediately
        invalid_keys = [
            "",
            "invalid_key",
            "sk-ant-short",
            "sk-" + "a" * 95,  # Missing "ant-"
            "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",  # Notion key
            None,
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValueError, match="Invalid Anthropic API key format"):
                ClaudeProvider(key)

    def test_openai_provider_validates_api_key(self):
        """Test that OpenAIProvider validates API key on initialization."""
        # Invalid keys should fail validation immediately
        invalid_keys = [
            "",
            "invalid_key",
            "sk-short",
            "openai-" + "a" * 48,  # Wrong prefix
            "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",  # Notion key
            None,
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValueError, match="Invalid OpenAI API key format"):
                OpenAIProvider(key)