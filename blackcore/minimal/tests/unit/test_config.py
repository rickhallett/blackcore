"""Comprehensive unit tests for config module."""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from blackcore.minimal.config import (
    Config,
    ConfigManager,
    NotionConfig,
    AIConfig,
    ProcessingConfig,
    DatabaseConfig,
    ConfigurationError,
)


class TestDatabaseConfig:
    """Test DatabaseConfig model."""

    def test_database_config_minimal(self):
        """Test creating database config with minimal fields."""
        config = DatabaseConfig(id="db-123")
        assert config.id == "db-123"
        assert config.name is None
        assert config.mappings == {}

    def test_database_config_full(self):
        """Test creating database config with all fields."""
        config = DatabaseConfig(
            id="db-123",
            name="Test Database",
            mappings={"name": "Full Name", "email": "Email Address"},
        )
        assert config.id == "db-123"
        assert config.name == "Test Database"
        assert config.mappings["name"] == "Full Name"
        assert config.mappings["email"] == "Email Address"


class TestNotionConfig:
    """Test NotionConfig model."""

    def test_notion_config_minimal(self):
        """Test creating Notion config with minimal fields."""
        config = NotionConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.databases == {}

    def test_notion_config_with_databases(self):
        """Test creating Notion config with databases."""
        config = NotionConfig(
            api_key="test-key",
            databases={
                "people": DatabaseConfig(id="people-db"),
                "tasks": DatabaseConfig(id="tasks-db"),
            },
        )
        assert config.api_key == "test-key"
        assert "people" in config.databases
        assert config.databases["people"].id == "people-db"
        assert "tasks" in config.databases
        assert config.databases["tasks"].id == "tasks-db"


class TestAIConfig:
    """Test AIConfig model."""

    def test_ai_config_defaults(self):
        """Test AI config default values."""
        config = AIConfig()
        assert config.provider == "claude"
        assert config.api_key is None
        assert config.model == "claude-3-opus-20240514"
        assert config.max_tokens == 4000
        assert config.temperature == 0.3
        assert config.extraction_prompt is None

    def test_ai_config_custom(self):
        """Test AI config with custom values."""
        config = AIConfig(
            provider="openai",
            api_key="openai-key",
            model="gpt-4",
            max_tokens=8000,
            temperature=0.7,
            extraction_prompt="Custom prompt",
        )
        assert config.provider == "openai"
        assert config.api_key == "openai-key"
        assert config.model == "gpt-4"
        assert config.max_tokens == 8000
        assert config.temperature == 0.7
        assert config.extraction_prompt == "Custom prompt"


class TestProcessingConfig:
    """Test ProcessingConfig model."""

    def test_processing_config_defaults(self):
        """Test processing config default values."""
        config = ProcessingConfig()
        assert config.batch_size == 10
        assert config.cache_ttl == 3600
        assert config.dry_run is False
        assert config.verbose is False

    def test_processing_config_custom(self):
        """Test processing config with custom values."""
        config = ProcessingConfig(batch_size=50, cache_ttl=7200, dry_run=True, verbose=True)
        assert config.batch_size == 50
        assert config.cache_ttl == 7200
        assert config.dry_run is True
        assert config.verbose is True


class TestConfig:
    """Test main Config model."""

    def test_config_minimal(self):
        """Test creating config with minimal fields."""
        config = Config(notion=NotionConfig(api_key="test-key"), ai=AIConfig())
        assert config.notion.api_key == "test-key"
        assert config.ai.provider == "claude"
        assert config.processing.batch_size == 10
        assert config.cache_dir == ".cache"
        assert config.cache_ttl == 3600

    def test_config_full(self):
        """Test creating config with all fields."""
        config = Config(
            notion=NotionConfig(
                api_key="test-key", databases={"people": DatabaseConfig(id="people-db")}
            ),
            ai=AIConfig(provider="openai", api_key="ai-key"),
            processing=ProcessingConfig(batch_size=20, dry_run=True),
            cache_dir="/tmp/cache",
            cache_ttl=7200,
        )
        assert config.notion.api_key == "test-key"
        assert config.ai.provider == "openai"
        assert config.processing.batch_size == 20
        assert config.processing.dry_run is True
        assert config.cache_dir == "/tmp/cache"
        assert config.cache_ttl == 7200


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_load_from_dict(self):
        """Test loading config from dictionary."""
        config_dict = {
            "notion": {"api_key": "test-key", "databases": {"people": {"id": "people-db"}}},
            "ai": {"provider": "openai", "api_key": "ai-key"},
        }

        config = ConfigManager.load_from_dict(config_dict)
        assert config.notion.api_key == "test-key"
        assert config.ai.provider == "openai"
        assert "people" in config.notion.databases

    def test_load_from_file_json(self):
        """Test loading config from JSON file."""
        config_data = {"notion": {"api_key": "file-key"}, "ai": {"provider": "claude"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = ConfigManager.load_from_file(temp_path)
            assert config.notion.api_key == "file-key"
            assert config.ai.provider == "claude"
        finally:
            os.unlink(temp_path)

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager.load_from_file("/non/existent/file.json")
        assert "not found" in str(exc_info.value)

    def test_load_from_file_invalid_json(self):
        """Test loading from file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigManager.load_from_file(temp_path)
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    @patch.dict(
        os.environ,
        {
            "NOTION_API_KEY": "env-notion-key",
            "OPENAI_API_KEY": "env-openai-key",
            "BLACKCORE_DRY_RUN": "true",
            "BLACKCORE_VERBOSE": "1",
            "BLACKCORE_BATCH_SIZE": "25",
        },
    )
    def test_load_from_env(self):
        """Test loading config from environment variables."""
        config = ConfigManager.load_from_env()
        assert config.notion.api_key == "env-notion-key"
        assert config.ai.api_key == "env-openai-key"
        assert config.processing.dry_run is True
        assert config.processing.verbose is True
        assert config.processing.batch_size == 25

    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_empty(self):
        """Test loading from empty environment."""
        config = ConfigManager.load_from_env()
        assert config.notion.api_key is None
        assert config.ai.api_key is None
        assert config.processing.dry_run is False

    def test_deep_merge_dicts(self):
        """Test deep merging of dictionaries."""
        base = {"a": 1, "b": {"c": 2, "d": 3}, "e": [1, 2, 3]}
        override = {"a": 10, "b": {"c": 20, "f": 4}, "g": 5}

        result = ConfigManager._deep_merge(base, override)
        assert result["a"] == 10  # Overridden
        assert result["b"]["c"] == 20  # Overridden nested
        assert result["b"]["d"] == 3  # Preserved from base
        assert result["b"]["f"] == 4  # Added from override
        assert result["e"] == [1, 2, 3]  # Preserved list
        assert result["g"] == 5  # Added new key

    def test_deep_merge_none_values(self):
        """Test deep merge handles None values."""
        base = {"a": 1, "b": {"c": 2}}
        override = {"a": None, "b": None}

        result = ConfigManager._deep_merge(base, override)
        assert result["a"] is None
        assert result["b"] is None

    def test_validate_config_valid(self):
        """Test validating a valid config."""
        config = Config(notion=NotionConfig(api_key="test-key"), ai=AIConfig(api_key="ai-key"))
        ConfigManager.validate_config(config)  # Should not raise

    def test_validate_config_missing_notion_key(self):
        """Test validating config with missing Notion API key."""
        config = Config(notion=NotionConfig(api_key=None), ai=AIConfig(api_key="ai-key"))
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager.validate_config(config)
        assert "Notion API key" in str(exc_info.value)

    def test_validate_config_missing_ai_key(self):
        """Test validating config with missing AI API key."""
        config = Config(notion=NotionConfig(api_key="test-key"), ai=AIConfig(api_key=None))
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager.validate_config(config)
        assert "API key not configured" in str(exc_info.value)

    def test_validate_config_invalid_ai_provider(self):
        """Test validating config with invalid AI provider."""
        config = Config(
            notion=NotionConfig(api_key="test-key"), ai=AIConfig(provider="invalid", api_key="key")
        )
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager.validate_config(config)
        assert "Invalid AI provider" in str(exc_info.value)

    def test_load_combined_config(self):
        """Test loading config from file with env overrides."""
        # Create config file
        file_config = {
            "notion": {"api_key": "file-key"},
            "ai": {"provider": "claude", "max_tokens": 2000},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(file_config, f)
            temp_path = f.name

        try:
            with patch.dict(
                os.environ, {"NOTION_API_KEY": "env-override-key", "BLACKCORE_DRY_RUN": "true"}
            ):
                config = ConfigManager.load(config_path=temp_path)
                # Environment should override file
                assert config.notion.api_key == "env-override-key"
                # File value preserved when no env override
                assert config.ai.max_tokens == 2000
                # Env adds new value
                assert config.processing.dry_run is True
        finally:
            os.unlink(temp_path)

    def test_load_with_invalid_path(self):
        """Test load with invalid config path."""
        with pytest.raises(ConfigurationError):
            ConfigManager.load(config_path="/invalid/path.json")

    def test_boolean_env_parsing(self):
        """Test parsing boolean values from environment."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),
            ("random", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"BLACKCORE_DRY_RUN": env_value}):
                config = ConfigManager.load_from_env()
                assert config.processing.dry_run == expected, f"Failed for {env_value}"

    def test_database_config_from_env(self):
        """Test loading database configs from environment."""
        with patch.dict(
            os.environ,
            {
                "NOTION_API_KEY": "test-key",
                "NOTION_DB_PEOPLE": "people-db-id",
                "NOTION_DB_TASKS": "tasks-db-id",
            },
        ):
            config = ConfigManager.load_from_env()
            assert "people" in config.notion.databases
            assert config.notion.databases["people"].id == "people-db-id"
            assert "tasks" in config.notion.databases
            assert config.notion.databases["tasks"].id == "tasks-db-id"
