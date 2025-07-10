"""Tests for transcript processor module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ..transcript_processor import TranscriptProcessor
from ..models import (
    TranscriptInput,
    ProcessingResult,
    BatchResult,
    Entity,
    EntityType,
    ExtractedEntities,
    NotionPage,
    Config,
    NotionConfig,
    AIConfig,
    DatabaseConfig,
)


class TestTranscriptProcessor:
    """Test main transcript processor."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return Config(
            notion=NotionConfig(
                api_key="notion-key",
                databases={
                    "people": DatabaseConfig(id="people-db", name="People"),
                    "organizations": DatabaseConfig(id="org-db", name="Organizations"),
                    "tasks": DatabaseConfig(id="task-db", name="Tasks"),
                    "transcripts": DatabaseConfig(id="transcript-db", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="trans-db", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="ai-key"),
        )

    @pytest.fixture
    def mock_extracted_entities(self):
        """Create mock extracted entities."""
        return ExtractedEntities(
            entities=[
                Entity(name="John Doe", type=EntityType.PERSON, properties={"role": "Mayor"}),
                Entity(name="Town Council", type=EntityType.ORGANIZATION),
                Entity(name="Review Survey", type=EntityType.TASK, properties={"status": "To-Do"}),
            ],
            relationships=[],
            summary="Meeting about survey concerns",
            key_points=["Survey methodology questioned"],
        )

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_processor_init(self, mock_cache, mock_updater, mock_extractor, mock_config):
        """Test processor initialization."""
        processor = TranscriptProcessor(config=mock_config)

        assert processor.config == mock_config
        mock_extractor.assert_called_once_with(
            provider="claude", api_key="ai-key", model="claude-3-sonnet-20240229"
        )
        mock_updater.assert_called_once_with(api_key="notion-key", rate_limit=3.0, retry_attempts=3)

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_process_transcript_success(
        self,
        mock_cache,
        mock_updater_class,
        mock_extractor_class,
        mock_config,
        mock_extracted_entities,
    ):
        """Test successful transcript processing."""
        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract_entities.return_value = mock_extracted_entities
        mock_extractor_class.return_value = mock_extractor

        mock_page = NotionPage(
            id="page-123",
            database_id="db-123",
            properties={},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        mock_updater = Mock()
        mock_updater.find_or_create_page.return_value = (mock_page, True)
        mock_updater_class.return_value = mock_updater

        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache.return_value = mock_cache_instance

        # Create processor and transcript
        processor = TranscriptProcessor(config=mock_config)
        transcript = TranscriptInput(
            title="Test Meeting",
            content="Meeting content about survey...",
            date=datetime(2025, 1, 9),
        )

        # Process
        result = processor.process_transcript(transcript)

        # Verify
        assert result.success is True
        assert len(result.created) > 0
        assert result.processing_time > 0

        # Check AI extraction was called
        mock_extractor.extract_entities.assert_called_once()

        # Check entities were created
        assert mock_updater.find_or_create_page.call_count >= 3  # 3 entities

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_process_transcript_dry_run(
        self,
        mock_cache,
        mock_updater_class,
        mock_extractor_class,
        mock_config,
        mock_extracted_entities,
    ):
        """Test dry run mode."""
        # Modify config for dry run
        mock_config.processing.dry_run = True

        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract_entities.return_value = mock_extracted_entities
        mock_extractor_class.return_value = mock_extractor

        mock_updater = Mock()
        mock_updater_class.return_value = mock_updater

        # Process
        processor = TranscriptProcessor(config=mock_config)
        transcript = TranscriptInput(title="Test", content="Content")
        result = processor.process_transcript(transcript)

        # Verify
        assert result.success is True
        # No Notion updates should have been made
        mock_updater.find_or_create_page.assert_not_called()
        mock_updater.create_page.assert_not_called()

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_process_transcript_with_cache(
        self, mock_cache_class, mock_updater_class, mock_extractor_class, mock_config
    ):
        """Test processing with cached results."""
        # Setup cache to return cached entities
        cached_data = {
            "entities": [{"name": "Cached Person", "type": "person"}],
            "relationships": [],
            "summary": "Cached summary",
        }

        mock_cache = Mock()
        mock_cache.get.return_value = cached_data
        mock_cache_class.return_value = mock_cache

        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        mock_updater = Mock()
        mock_updater.find_or_create_page.return_value = (Mock(), True)
        mock_updater_class.return_value = mock_updater

        # Process
        processor = TranscriptProcessor(config=mock_config)
        transcript = TranscriptInput(title="Test", content="Content")
        result = processor.process_transcript(transcript)

        # AI extraction should not have been called
        mock_extractor.extract_entities.assert_not_called()

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_process_transcript_error_handling(
        self, mock_cache, mock_updater_class, mock_extractor_class, mock_config
    ):
        """Test error handling during processing."""
        # Setup extractor to raise error
        mock_extractor = Mock()
        mock_extractor.extract_entities.side_effect = Exception("AI API error")
        mock_extractor_class.return_value = mock_extractor

        # Process
        processor = TranscriptProcessor(config=mock_config)
        transcript = TranscriptInput(title="Test", content="Content")
        result = processor.process_transcript(transcript)

        # Verify
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type in ["Exception", "ValueError"]
        assert result.errors[0].stage == "processing"

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_process_batch(
        self,
        mock_cache,
        mock_updater_class,
        mock_extractor_class,
        mock_config,
        mock_extracted_entities,
    ):
        """Test batch processing."""
        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract_entities.return_value = mock_extracted_entities
        mock_extractor_class.return_value = mock_extractor

        mock_page = NotionPage(
            id="page-123",
            database_id="db-123",
            properties={},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        mock_updater = Mock()
        mock_updater.find_or_create_page.return_value = (mock_page, True)
        mock_updater_class.return_value = mock_updater

        # Create transcripts
        transcripts = [
            TranscriptInput(title="Meeting 1", content="Content 1"),
            TranscriptInput(title="Meeting 2", content="Content 2"),
            TranscriptInput(title="Meeting 3", content="Content 3"),
        ]

        # Process batch
        processor = TranscriptProcessor(config=mock_config)
        batch_result = processor.process_batch(transcripts)

        # Verify
        assert batch_result.total_transcripts == 3
        assert batch_result.successful == 3
        assert batch_result.failed == 0
        assert batch_result.success_rate == 1.0
        assert len(batch_result.results) == 3

    def test_validate_config_missing_keys(self, mock_config):
        """Test configuration validation."""
        # Remove API key
        mock_config.notion.api_key = ""

        with pytest.raises(ValueError, match="Notion API key not configured"):
            TranscriptProcessor(config=mock_config)

        # Fix Notion key, break AI key
        mock_config.notion.api_key = "key"
        mock_config.ai.api_key = ""

        with pytest.raises(ValueError, match="AI API key not configured"):
            TranscriptProcessor(config=mock_config)
