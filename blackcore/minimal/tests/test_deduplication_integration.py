"""Integration tests for deduplication functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import (
    TranscriptInput,
    Entity,
    EntityType,
    ExtractedEntities,
    NotionPage,
    Config,
    ProcessingConfig,
)


class TestDeduplicationIntegration:
    """Integration tests for the deduplication workflow."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration with deduplication enabled."""
        config = Mock(spec=Config)
        config.processing = ProcessingConfig(
            enable_deduplication=True, deduplication_threshold=90.0, verbose=True
        )
        config.notion = Mock()
        config.notion.api_key = "test-key"
        config.notion.databases = {
            "people": Mock(
                id="people-db-id",
                mappings={
                    "name": "Full Name",
                    "email": "Email",
                    "phone": "Phone",
                    "organization": "Organization",
                    "notes": "Notes",
                },
            ),
            "organizations": Mock(
                id="org-db-id",
                mappings={
                    "name": "Organization Name",
                    "website": "Website",
                    "notes": "Notes",
                },
            ),
            "transcripts": Mock(
                id="transcript-db-id",
                mappings={
                    "title": "Entry Title",
                    "content": "Raw Transcript/Note",
                    "status": "Processing Status",
                    "date": "Date Recorded",
                    "source": "Source",
                    "summary": "AI Summary",
                    "entities": "Tagged Entities",
                },
            ),
        }
        config.notion.rate_limit = 3.0
        config.notion.retry_attempts = 3
        config.ai = Mock()
        config.ai.provider = "claude"
        config.ai.api_key = "test-key"
        config.ai.model = "claude-3-sonnet"
        return config

    @pytest.fixture
    def processor(self, mock_config):
        """Create processor with mocked dependencies."""
        with patch("blackcore.minimal.transcript_processor.AIExtractor"):
            with patch("blackcore.minimal.transcript_processor.NotionUpdater"):
                processor = TranscriptProcessor(config=mock_config)
                return processor

    def test_person_deduplication_exact_match(self, processor):
        """Test deduplication with exact email match."""
        # Setup existing person in Notion
        existing_person = NotionPage(
            id="existing-person-id",
            database_id="people-db-id",
            properties={
                "Full Name": "Anthony Smith",
                "Email": "tony@example.com",
                "Organization": "Nassau Council",
            },
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        # Mock search to return existing person
        processor.notion_updater.search_database.return_value = [existing_person]
        processor.notion_updater.update_page.return_value = existing_person

        # Process a person that should match
        person = Entity(
            name="Tony Smith",
            type=EntityType.PERSON,
            properties={
                "email": "tony@example.com",
                "organization": "Nassau Town Council",
            },
        )

        page, created = processor._process_person(person)

        # Should have found and updated existing
        assert not created
        assert page.id == "existing-person-id"

        # Should have called search
        processor.notion_updater.search_database.assert_called_once_with(
            database_id="people-db-id", query="Tony Smith", limit=10
        )

        # Should have updated with new organization
        processor.notion_updater.update_page.assert_called_once()
        update_args = processor.notion_updater.update_page.call_args[0]
        assert update_args[0] == "existing-person-id"
        assert "Organization" in update_args[1]

    def test_person_deduplication_nickname_match(self, processor):
        """Test deduplication with nickname matching."""
        # Setup existing person
        existing_person = NotionPage(
            id="existing-bob-id",
            database_id="people-db-id",
            properties={"Full Name": "Robert Johnson", "Phone": "555-1234"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        # Mock search
        processor.notion_updater.search_database.return_value = [existing_person]
        processor.notion_updater.update_page.return_value = existing_person

        # Process nickname variant
        person = Entity(
            name="Bob Johnson",
            type=EntityType.PERSON,
            properties={"phone": "(555) 123-4000"},  # Different phone
        )

        page, created = processor._process_person(person)

        # Should match by nickname
        assert not created
        assert page.id == "existing-bob-id"

    def test_person_deduplication_no_match(self, processor):
        """Test when no duplicate is found."""
        # Mock search returns empty
        processor.notion_updater.search_database.return_value = []

        new_page = NotionPage(
            id="new-person-id",
            database_id="people-db-id",
            properties={"Full Name": "Jane Doe"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )
        processor.notion_updater.create_page.return_value = new_page

        # Process new person
        person = Entity(
            name="Jane Doe",
            type=EntityType.PERSON,
            properties={"email": "jane@example.com"},
        )

        page, created = processor._process_person(person)

        # Should create new
        assert created
        assert page.id == "new-person-id"

        # Should have called create
        processor.notion_updater.create_page.assert_called_once()

    def test_organization_deduplication(self, processor):
        """Test organization deduplication."""
        # Setup existing org
        existing_org = NotionPage(
            id="existing-org-id",
            database_id="org-db-id",
            properties={
                "Organization Name": "Nassau Council Inc",
                "Website": "https://nassau.gov",
            },
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        processor.notion_updater.search_database.return_value = [existing_org]
        processor.notion_updater.update_page.return_value = existing_org

        # Process similar org name
        org = Entity(
            name="Nassau Council",  # Without "Inc"
            type=EntityType.ORGANIZATION,
            properties={"website": "http://www.nassau.gov/"},  # Different format
        )

        page, created = processor._process_organization(org)

        # Should match by normalized name
        assert not created
        assert page.id == "existing-org-id"

    def test_deduplication_disabled(self, processor):
        """Test behavior when deduplication is disabled."""
        # Disable deduplication
        processor.config.processing.enable_deduplication = False

        # Even with exact match, should create new
        new_page = NotionPage(
            id="new-person-id",
            database_id="people-db-id",
            properties={"Full Name": "John Smith"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )
        processor.notion_updater.create_page.return_value = new_page

        person = Entity(name="John Smith", type=EntityType.PERSON, properties={})

        page, created = processor._process_person(person)

        # Should create without searching
        assert created
        processor.notion_updater.search_database.assert_not_called()
        processor.notion_updater.create_page.assert_called_once()

    def test_deduplication_threshold(self, processor):
        """Test deduplication threshold behavior."""
        # Set high threshold
        processor.config.processing.deduplication_threshold = 95.0

        # Setup person with similar but not exact match
        existing_person = NotionPage(
            id="existing-id",
            database_id="people-db-id",
            properties={"Full Name": "John Smith", "Organization": "Different Org"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        processor.notion_updater.search_database.return_value = [existing_person]

        # Create new page for no match
        new_page = NotionPage(
            id="new-id",
            database_id="people-db-id",
            properties={"Full Name": "J. Smith"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )
        processor.notion_updater.create_page.return_value = new_page

        # Process similar name (would score ~85%)
        person = Entity(name="J. Smith", type=EntityType.PERSON, properties={})

        page, created = processor._process_person(person)

        # Should create new due to threshold
        assert created
        assert page.id == "new-id"

    def test_full_transcript_processing_with_dedup(self, processor):
        """Test full transcript processing with deduplication."""
        # Setup transcript
        transcript = TranscriptInput(
            title="Meeting Notes",
            content="Tony Smith from Nassau Council discussed the project.",
            date=datetime.utcnow(),
        )

        # Mock AI extraction
        extracted = ExtractedEntities(
            entities=[
                Entity(
                    name="Tony Smith",
                    type=EntityType.PERSON,
                    properties={"organization": "Nassau Council"},
                ),
                Entity(
                    name="Nassau Council", type=EntityType.ORGANIZATION, properties={}
                ),
            ],
            summary="Meeting discussion",
        )
        processor.ai_extractor.extract_entities.return_value = extracted

        # Setup existing matches
        existing_person = NotionPage(
            id="anthony-id",
            database_id="people-db-id",
            properties={"Full Name": "Anthony Smith"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        existing_org = NotionPage(
            id="nassau-id",
            database_id="org-db-id",
            properties={"Organization Name": "Nassau Council"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        # Mock search results
        def mock_search(database_id, query, limit):
            if "Tony" in query:
                return [existing_person]
            elif "Nassau" in query:
                return [existing_org]
            return []

        processor.notion_updater.search_database.side_effect = mock_search
        processor.notion_updater.update_page.side_effect = [
            existing_person,
            existing_org,
        ]

        # Mock transcript creation
        transcript_page = NotionPage(
            id="transcript-id",
            database_id="transcript-db-id",
            properties={},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )
        processor.notion_updater.find_or_create_page.return_value = (
            transcript_page,
            True,
        )

        # Process
        result = processor.process_transcript(transcript)

        # Should have found duplicates
        assert result.success
        assert len(result.updated) == 3  # 2 entities + transcript
        assert len(result.created) == 0  # Nothing new created
