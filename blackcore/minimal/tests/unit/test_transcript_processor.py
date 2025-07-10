"""Comprehensive unit tests for transcript processor module."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call
import tempfile

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import (
    TranscriptInput,
    ProcessingResult,
    BatchResult,
    ExtractedEntities,
    Entity,
    EntityType,
    Relationship,
    NotionPage,
    ProcessingError,
)
from blackcore.minimal.config import Config, NotionConfig, AIConfig, DatabaseConfig

from ..fixtures import (
    SIMPLE_TRANSCRIPT,
    COMPLEX_TRANSCRIPT,
    EMPTY_TRANSCRIPT,
    SPECIAL_CHARS_TRANSCRIPT,
    BATCH_TRANSCRIPTS,
)
from ..utils import create_test_config, create_mock_notion_client, create_mock_ai_client


class TestTranscriptProcessorInit:
    """Test TranscriptProcessor initialization."""

    def test_init_with_config_object(self):
        """Test initialization with Config object."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)
            assert processor.config == config

    def test_init_with_config_path(self):
        """Test initialization with config file path."""
        config_data = {"notion": {"api_key": "test-key"}, "ai": {"api_key": "ai-key"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            import json

            json.dump(config_data, f)
            f.flush()

            with (
                patch("blackcore.minimal.transcript_processor.AIExtractor"),
                patch("blackcore.minimal.transcript_processor.NotionUpdater"),
                patch("blackcore.minimal.transcript_processor.SimpleCache"),
            ):
                processor = TranscriptProcessor(config_path=f.name)
                assert processor.config.notion.api_key == "test-key"

    def test_init_no_config(self):
        """Test initialization with no config (loads from env)."""
        with (
            patch("blackcore.minimal.transcript_processor.ConfigManager.load") as mock_load,
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            mock_load.return_value = create_test_config()
            processor = TranscriptProcessor()
            mock_load.assert_called_once_with(config_path=None)

    def test_init_with_both_config_and_path(self):
        """Test initialization with both config object and path raises error."""
        config = create_test_config()

        with pytest.raises(ValueError) as exc_info:
            TranscriptProcessor(config=config, config_path="path.json")
        assert "both config object and config_path" in str(exc_info.value)

    def test_validate_config_warnings(self, capsys):
        """Test configuration validation warnings."""
        config = create_test_config()
        # Remove some database IDs to trigger warnings
        config.notion.databases["people"].id = None
        config.notion.databases["organizations"] = DatabaseConfig(id=None, name="Orgs")

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)
            captured = capsys.readouterr()
            assert "Warning: Database ID not configured for 'people'" in captured.out
            assert "Warning: Database ID not configured for 'organizations'" in captured.out


class TestEntityExtraction:
    """Test entity extraction functionality."""

    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_extract_entities_from_cache(self, mock_cache_class):
        """Test extracting entities from cache."""
        # Setup cache hit
        mock_cache = Mock()
        cached_data = {"entities": [{"name": "John Doe", "type": "person"}], "relationships": []}
        mock_cache.get.return_value = cached_data
        mock_cache_class.return_value = mock_cache

        config = create_test_config()
        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
        ):
            processor = TranscriptProcessor(config=config)
            extracted = processor._extract_entities(SIMPLE_TRANSCRIPT)

            # Should use cache, not call AI
            assert len(extracted.entities) == 1
            assert extracted.entities[0].name == "John Doe"
            mock_cache.get.assert_called_once()

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_extract_entities_cache_miss(self, mock_cache_class, mock_extractor_class):
        """Test extracting entities when cache misses."""
        # Setup cache miss
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache_class.return_value = mock_cache

        # Setup AI response
        mock_extractor = Mock()
        extracted = ExtractedEntities(
            entities=[Entity(name="Jane Doe", type=EntityType.PERSON)], relationships=[]
        )
        mock_extractor.extract_entities.return_value = extracted
        mock_extractor_class.return_value = mock_extractor

        config = create_test_config()
        with patch("blackcore.minimal.transcript_processor.NotionUpdater"):
            processor = TranscriptProcessor(config=config)
            result = processor._extract_entities(SIMPLE_TRANSCRIPT)

            # Should call AI and cache result
            assert len(result.entities) == 1
            assert result.entities[0].name == "Jane Doe"
            mock_extractor.extract_entities.assert_called_once()
            mock_cache.set.assert_called_once()


class TestEntityProcessing:
    """Test individual entity processing."""

    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    def test_process_person_success(self, mock_updater_class):
        """Test successfully processing a person entity."""
        # Setup mock
        mock_page = NotionPage(
            id="person-123",
            database_id="people-db",
            properties={"Name": "John Doe"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )
        mock_updater = Mock()
        mock_updater.find_or_create_page.return_value = (mock_page, True)
        mock_updater_class.return_value = mock_updater

        config = create_test_config()
        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)
            person = Entity(
                name="John Doe",
                type=EntityType.PERSON,
                properties={"role": "CEO", "email": "john@example.com"},
            )

            page, created = processor._process_person(person)

            assert page == mock_page
            assert created is True
            mock_updater.find_or_create_page.assert_called_once()

            # Check properties were mapped correctly
            call_args = mock_updater.find_or_create_page.call_args
            properties = call_args[1]["properties"]
            assert properties["Full Name"] == "John Doe"
            assert properties["Role"] == "CEO"

    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    def test_process_person_no_database(self, mock_updater_class):
        """Test processing person when database not configured."""
        config = create_test_config()
        config.notion.databases.pop("people")  # Remove people database

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)
            person = Entity(name="John Doe", type=EntityType.PERSON)

            page, created = processor._process_person(person)

            assert page is None
            assert created is False

    def test_process_organization_success(self):
        """Test successfully processing an organization entity."""
        # Similar to person test but for organizations
        config = create_test_config()
        config.notion.databases["organizations"] = DatabaseConfig(
            id="org-db", name="Organizations", mappings={"name": "Name", "type": "Type"}
        )

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            mock_page = NotionPage(
                id="org-123",
                database_id="org-db",
                properties={"Name": "ACME Corp"},
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow(),
            )
            mock_updater = Mock()
            mock_updater.find_or_create_page.return_value = (mock_page, False)
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)
            org = Entity(
                name="ACME Corp", type=EntityType.ORGANIZATION, properties={"type": "Corporation"}
            )

            page, created = processor._process_organization(org)

            assert page == mock_page
            assert created is False

    def test_process_task_event_place(self):
        """Test processing other entity types (tasks, events, places)."""
        config = create_test_config()

        # Add more database configs
        config.notion.databases["events"] = DatabaseConfig(
            id="events-db", mappings={"name": "Title", "date": "Date"}
        )
        config.notion.databases["places"] = DatabaseConfig(
            id="places-db", mappings={"name": "Name", "address": "Address"}
        )

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            mock_updater = Mock()
            mock_updater.find_or_create_page.return_value = (Mock(id="page-id"), True)
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)

            # Should handle these entity types without error
            task = Entity(name="Review contracts", type=EntityType.TASK)
            event = Entity(name="Board meeting", type=EntityType.EVENT)
            place = Entity(name="NYC HQ", type=EntityType.PLACE)

            # Process method should handle all types
            extracted = ExtractedEntities(entities=[task, event, place])

            # This would be called internally, but we can test the logic
            # by checking that proper databases are configured


class TestRelationshipCreation:
    """Test relationship creation functionality."""

    def test_create_relationships_not_implemented(self):
        """Test that relationship creation is not yet implemented."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)

            relationships = [
                Relationship(
                    source_entity="John Doe",
                    source_type=EntityType.PERSON,
                    target_entity="ACME Corp",
                    target_type=EntityType.ORGANIZATION,
                    relationship_type="works_for",
                )
            ]

            entity_map = {"John Doe": "person-123", "ACME Corp": "org-456"}

            # Currently this method doesn't do anything
            processor._create_relationships(relationships, entity_map)
            # No assertion needed - just ensure it doesn't crash


class TestDryRunMode:
    """Test dry run mode functionality."""

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_dry_run_mode(self, mock_cache_class, mock_extractor_class, capsys):
        """Test processing in dry run mode."""
        config = create_test_config(dry_run=True)

        # Setup mocks
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache_class.return_value = mock_cache

        extracted = ExtractedEntities(
            entities=[
                Entity(name="John Doe", type=EntityType.PERSON),
                Entity(name="ACME Corp", type=EntityType.ORGANIZATION),
            ],
            relationships=[],
        )
        mock_extractor = Mock()
        mock_extractor.extract_entities.return_value = extracted
        mock_extractor_class.return_value = mock_extractor

        with patch("blackcore.minimal.transcript_processor.NotionUpdater"):
            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            assert result.success is True
            assert len(result.created) == 0  # Nothing actually created
            assert len(result.updated) == 0

            captured = capsys.readouterr()
            assert "DRY RUN:" in captured.out
            assert "People (1):" in captured.out
            assert "- John Doe" in captured.out
            assert "Organizations (1):" in captured.out
            assert "- ACME Corp" in captured.out


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_process_batch_success(self):
        """Test successful batch processing."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Setup mocks
            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=[], relationships=[]
            )
            mock_extractor_class.return_value = mock_extractor

            mock_updater = Mock()
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)

            # Process batch
            transcripts = BATCH_TRANSCRIPTS[:3]  # Use first 3
            result = processor.process_batch(transcripts)

            assert result.total_transcripts == 3
            assert result.successful == 3
            assert result.failed == 0
            assert result.success_rate == 1.0
            assert len(result.results) == 3

    def test_process_batch_with_failures(self):
        """Test batch processing with some failures."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Setup mock to fail on second transcript
            mock_extractor = Mock()
            mock_extractor.extract_entities.side_effect = [
                ExtractedEntities(entities=[], relationships=[]),
                Exception("AI Error"),
                ExtractedEntities(entities=[], relationships=[]),
            ]
            mock_extractor_class.return_value = mock_extractor

            processor = TranscriptProcessor(config=config)

            # Process batch
            transcripts = BATCH_TRANSCRIPTS[:3]
            result = processor.process_batch(transcripts)

            assert result.total_transcripts == 3
            assert result.successful == 2
            assert result.failed == 1
            assert result.success_rate == 2 / 3
            assert result.results[1].success is False

    def test_process_batch_verbose_output(self, capsys):
        """Test batch processing with verbose output."""
        config = create_test_config()
        config.processing.verbose = True

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=[], relationships=[]
            )
            mock_extractor_class.return_value = mock_extractor

            processor = TranscriptProcessor(config=config)

            # Process batch
            transcripts = BATCH_TRANSCRIPTS[:2]
            result = processor.process_batch(transcripts)

            captured = capsys.readouterr()
            assert "Processing transcript 1/2:" in captured.out
            assert "Processing transcript 2/2:" in captured.out
            assert "Batch processing complete" in captured.out
            assert f"Success rate: {result.success_rate:.1%}" in captured.out


class TestOutputFormatting:
    """Test output formatting methods."""

    def test_print_dry_run_summary(self, capsys):
        """Test dry run summary output."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)

            extracted = ExtractedEntities(
                entities=[
                    Entity(name="John Doe", type=EntityType.PERSON),
                    Entity(name="Jane Smith", type=EntityType.PERSON),
                    Entity(name="ACME Corp", type=EntityType.ORGANIZATION),
                    Entity(name="Review task", type=EntityType.TASK),
                    Entity(name="Data breach", type=EntityType.TRANSGRESSION),
                ],
                relationships=[
                    Relationship(
                        source_entity="John Doe",
                        source_type=EntityType.PERSON,
                        target_entity="ACME Corp",
                        target_type=EntityType.ORGANIZATION,
                        relationship_type="works_for",
                    )
                ],
            )

            processor._print_dry_run_summary(extracted)

            captured = capsys.readouterr()
            output = captured.out

            assert "People (2):" in output
            assert "- John Doe" in output
            assert "- Jane Smith" in output
            assert "Organizations (1):" in output
            assert "- ACME Corp" in output
            assert "Tasks (1):" in output
            assert "- Review task" in output
            assert "Transgressions (1):" in output
            assert "- Data breach" in output
            assert "Relationships (1):" in output
            assert "- John Doe -> works_for -> ACME Corp" in output

    def test_print_result_summary(self, capsys):
        """Test result summary output."""
        config = create_test_config()
        config.processing.verbose = True

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor"),
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            processor = TranscriptProcessor(config=config)

            result = ProcessingResult()
            result.success = True
            result.created = [
                NotionPage(id="1", database_id="db", properties={"Name": "New Person"})
            ]
            result.updated = [
                NotionPage(id="2", database_id="db", properties={"Name": "Existing Person"})
            ]
            result.processing_time = 1.5

            processor._print_result_summary(result)

            captured = capsys.readouterr()
            output = captured.out

            assert "Processing complete in 1.50s" in output
            assert "Created: 1" in output
            assert "Updated: 1" in output
            assert "Errors: 0" in output


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_processing_error_tracking(self):
        """Test that processing errors are properly tracked."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Make AI extraction fail
            mock_extractor = Mock()
            mock_extractor.extract_entities.side_effect = ValueError("Invalid JSON")
            mock_extractor_class.return_value = mock_extractor

            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            assert result.success is False
            assert len(result.errors) == 1
            assert result.errors[0].stage == "processing"
            assert result.errors[0].error_type == "ValueError"
            assert "Invalid JSON" in result.errors[0].message

    def test_notion_api_error_handling(self):
        """Test handling of Notion API errors."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Setup successful extraction
            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=[Entity(name="Test Person", type=EntityType.PERSON)], relationships=[]
            )
            mock_extractor_class.return_value = mock_extractor

            # Make Notion update fail
            mock_updater = Mock()
            mock_updater.find_or_create_page.side_effect = Exception("Notion API Error")
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            # Should still mark as failed even though extraction succeeded
            assert result.success is False
            assert len(result.errors) > 0
