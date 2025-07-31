"""Test API key validation functionality."""

import pytest

from blackcore.minimal.validators import validate_api_key


class TestAPIKeyValidation:
    """Test suite for API key validation."""

    def test_valid_notion_api_key(self):
        """Test that valid Notion API keys pass validation."""
        # Valid Notion keys start with "secret_" followed by 43 alphanumeric chars
        valid_keys = [
            "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",
            "secret_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0uvw",
            "secret_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefg",
        ]
        
        for key in valid_keys:
            assert validate_api_key(key, "notion") is True

    def test_invalid_notion_api_key(self):
        """Test that invalid Notion API keys fail validation."""
        invalid_keys = [
            "",  # Empty
            "secret_",  # Too short
            "secret_123",  # Too short
            "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH",  # Too long
            "1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",  # Missing prefix
            "Secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",  # Wrong case
            "secret_123456789@abcdefghijklmnopqrstuvwxyzABCDEFG",  # Invalid char
            "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",  # Wrong prefix
            None,  # None value
        ]
        
        for key in invalid_keys:
            assert validate_api_key(key, "notion") is False

    def test_valid_anthropic_api_key(self):
        """Test that valid Anthropic API keys pass validation."""
        # Valid Anthropic keys start with "sk-ant-" followed by 95 chars
        valid_keys = [
            "sk-ant-" + "a" * 95,
            "sk-ant-" + "1234567890" * 9 + "12345",  # 95 chars
            "sk-ant-" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-" + "a" * 32,
        ]
        
        for key in valid_keys:
            assert validate_api_key(key, "anthropic") is True

    def test_invalid_anthropic_api_key(self):
        """Test that invalid Anthropic API keys fail validation."""
        invalid_keys = [
            "",  # Empty
            "sk-ant-",  # Too short
            "sk-ant-123",  # Too short
            "sk-ant-" + "a" * 94,  # Too short by 1
            "sk-ant-" + "a" * 96,  # Too long by 1
            "sk-" + "a" * 95,  # Missing "ant-"
            "SK-ANT-" + "a" * 95,  # Wrong case
            "sk-ant-" + "a" * 90 + "@#$%^",  # Invalid chars (but hyphen is allowed)
            None,  # None value
        ]
        
        for key in invalid_keys:
            assert validate_api_key(key, "anthropic") is False

    def test_valid_openai_api_key(self):
        """Test that valid OpenAI API keys pass validation."""
        # Valid OpenAI keys start with "sk-" followed by 48 alphanumeric chars
        valid_keys = [
            "sk-" + "a" * 48,
            "sk-" + "1234567890" * 4 + "12345678",  # 48 chars
            "sk-" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",  # 48 chars
        ]
        
        for key in valid_keys:
            assert validate_api_key(key, "openai") is True

    def test_invalid_openai_api_key(self):
        """Test that invalid OpenAI API keys fail validation."""
        invalid_keys = [
            "",  # Empty
            "sk-",  # Too short
            "sk-123",  # Too short
            "sk-" + "a" * 47,  # Too short by 1
            "sk-" + "a" * 49,  # Too long by 1
            "openai-" + "a" * 48,  # Wrong prefix
            "SK-" + "a" * 48,  # Wrong case
            "sk-" + "a" * 40 + "@#$%^&*()",  # Invalid chars
            None,  # None value
        ]
        
        for key in invalid_keys:
            assert validate_api_key(key, "openai") is False

    def test_unknown_provider(self):
        """Test that unknown providers allow any non-empty key."""
        keys = [
            "any-key-format",
            "1234567890",
            "test_key_123",
            "!@#$%^&*()",
        ]
        
        for key in keys:
            assert validate_api_key(key, "unknown_provider") is True
        
        # But empty/None should still fail
        assert validate_api_key("", "unknown_provider") is False
        assert validate_api_key(None, "unknown_provider") is False

    def test_case_insensitive_provider(self):
        """Test that provider names are case-insensitive."""
        key = "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG"
        
        assert validate_api_key(key, "notion") is True
        assert validate_api_key(key, "Notion") is True
        assert validate_api_key(key, "NOTION") is True
        assert validate_api_key(key, "NoTiOn") is True

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled properly."""
        # Keys with whitespace should be invalid
        notion_key = "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG"
        
        assert validate_api_key(f" {notion_key}", "notion") is False
        assert validate_api_key(f"{notion_key} ", "notion") is False
        assert validate_api_key(f" {notion_key} ", "notion") is False
        assert validate_api_key(f"\n{notion_key}\n", "notion") is False

    def test_anthropic_hyphen_allowed(self):
        """Test that hyphens are allowed in Anthropic keys."""
        # Anthropic keys can contain hyphens
        valid_key = "sk-ant-" + "a" * 40 + "-" * 5 + "b" * 50
        assert validate_api_key(valid_key, "anthropic") is True
        
        # But other special chars are not
        invalid_key = "sk-ant-" + "a" * 40 + "@#$%" + "b" * 51
        assert validate_api_key(invalid_key, "anthropic") is False