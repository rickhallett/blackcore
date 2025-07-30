"""Comprehensive unit tests for config module."""

import pytest
import json
import os
import tempfile
from unittest.mock import patch

from blackcore.minimal.config import ConfigManager
from blackcore.minimal.models import Config, NotionConfig, AIConfig, DatabaseConfig, ProcessingConfig


class TestDatabaseConfig:
    """Test DatabaseConfig model."""

    def test_database_config_minimal(self):
        """Test creating database config with minimal fields."""
        config = DatabaseConfig(id="db-123", name="Test DB")
        assert config.id == "db-123"
        assert config.name == "Test DB"
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
        config = NotionConfig(api_key="test-key", databases={})
        assert config.api_key == "test-key"
        assert config.databases == {}

    def test_notion_config_with_databases(self):
        """Test creating Notion config with databases."""
        config = NotionConfig(
            api_key="test-key",
            databases={
                "people": DatabaseConfig(id="people-db", name="People"),
                "tasks": DatabaseConfig(id="tasks-db", name="Tasks"),
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
        config = AIConfig(api_key="test-ai-key")
        assert config.provider == "claude"
        assert config.api_key == "test-ai-key"
        assert config.model == "claude-3-sonnet-20240229"
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
        config = ProcessingConfig(
            batch_size=50, cache_ttl=7200, dry_run=True, verbose=True
        )
        assert config.batch_size == 50
        assert config.cache_ttl == 7200
        assert config.dry_run is True
        assert config.verbose is True


class TestConfig:
    """Test main Config model."""

    def test_config_minimal(self):
        """Test creating config with minimal fields."""
        config = Config(
            notion=NotionConfig(api_key="test-key", databases={}),
            ai=AIConfig(api_key="ai-key"),
        )
        assert config.notion.api_key == "test-key"
        assert config.ai.provider == "claude"
        assert config.processing.batch_size == 10
        assert config.processing.cache_dir == ".cache"
        assert config.processing.cache_ttl == 3600

    def test_config_full(self):
        """Test creating config with all fields."""
        config = Config(
            notion=NotionConfig(
                api_key="test-key",
                databases={"people": DatabaseConfig(id="people-db", name="People")},
            ),
            ai=AIConfig(provider="openai", api_key="ai-key"),
            processing=ProcessingConfig(
                batch_size=20, 
                dry_run=True,
                cache_dir="/tmp/cache",
                cache_ttl=7200
            ),
        )
        assert config.notion.api_key == "test-key"
        assert config.ai.provider == "openai"
        assert config.processing.batch_size == 20
        assert config.processing.dry_run is True
        assert config.processing.cache_dir == "/tmp/cache"
        assert config.processing.cache_ttl == 7200


