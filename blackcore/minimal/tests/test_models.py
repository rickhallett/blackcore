"""Tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from ..models import (
    Entity,
    EntityType,
    Relationship,
    ExtractedEntities,
    TranscriptInput,
    TranscriptSource,
    NotionPage,
    ProcessingResult,
    BatchResult,
    DatabaseConfig,
    NotionConfig,
    AIConfig,
    Config,
)


class TestEntity:
    """Test Entity model."""

    def test_entity_creation(self):
        """Test creating a valid entity."""
        entity = Entity(
            name="John Doe",
            type=EntityType.PERSON,
            properties={"role": "Mayor"},
            context="Mentioned as the mayor in the meeting",
            confidence=0.95,
        )

        assert entity.name == "John Doe"
        assert entity.type == "person"
        assert entity.properties["role"] == "Mayor"
        assert entity.confidence == 0.95

    def test_entity_defaults(self):
        """Test entity default values."""
        entity = Entity(name="Test Org", type=EntityType.ORGANIZATION)

        assert entity.properties == {}
        assert entity.context is None
        assert entity.confidence == 1.0

    def test_entity_confidence_validation(self):
        """Test confidence value validation."""
        # Valid confidence
        entity = Entity(name="Test", type=EntityType.PERSON, confidence=0.5)
        assert entity.confidence == 0.5

        # Invalid confidence
        with pytest.raises(ValidationError):
            Entity(name="Test", type=EntityType.PERSON, confidence=1.5)

        with pytest.raises(ValidationError):
            Entity(name="Test", type=EntityType.PERSON, confidence=-0.1)


class TestRelationship:
    """Test Relationship model."""

    def test_relationship_creation(self):
        """Test creating a valid relationship."""
        rel = Relationship(
            source_entity="John Doe",
            source_type=EntityType.PERSON,
            target_entity="Town Council",
            target_type=EntityType.ORGANIZATION,
            relationship_type="works_for",
            context="John Doe works for the Town Council",
        )

        assert rel.source_entity == "John Doe"
        assert rel.source_type == "person"
        assert rel.relationship_type == "works_for"


class TestExtractedEntities:
    """Test ExtractedEntities model."""

    def test_extracted_entities_creation(self):
        """Test creating extracted entities container."""
        entities = [
            Entity(name="John Doe", type=EntityType.PERSON),
            Entity(name="Town Council", type=EntityType.ORGANIZATION),
            Entity(name="Review Survey", type=EntityType.TASK),
        ]

        relationships = [
            Relationship(
                source_entity="John Doe",
                source_type=EntityType.PERSON,
                target_entity="Town Council",
                target_type=EntityType.ORGANIZATION,
                relationship_type="works_for",
            )
        ]

        extracted = ExtractedEntities(
            entities=entities,
            relationships=relationships,
            summary="Meeting discussed survey concerns",
            key_points=["Survey methodology questioned", "Action items assigned"],
        )

        assert len(extracted.entities) == 3
        assert len(extracted.relationships) == 1
        assert extracted.summary == "Meeting discussed survey concerns"
        assert len(extracted.key_points) == 2

    def test_get_entities_by_type(self):
        """Test filtering entities by type."""
        entities = [
            Entity(name="John Doe", type=EntityType.PERSON),
            Entity(name="Jane Smith", type=EntityType.PERSON),
            Entity(name="Town Council", type=EntityType.ORGANIZATION),
            Entity(name="Review Survey", type=EntityType.TASK),
        ]

        extracted = ExtractedEntities(entities=entities)

        people = extracted.get_entities_by_type(EntityType.PERSON)
        assert len(people) == 2
        assert all(p.type == "person" for p in people)

        orgs = extracted.get_entities_by_type(EntityType.ORGANIZATION)
        assert len(orgs) == 1
        assert orgs[0].name == "Town Council"


class TestTranscriptInput:
    """Test TranscriptInput model."""

    def test_transcript_creation(self):
        """Test creating a valid transcript input."""
        transcript = TranscriptInput(
            title="Meeting with Mayor",
            content="Discussion about beach hut survey...",
            date=datetime(2025, 1, 9, 14, 0, 0),
            source=TranscriptSource.VOICE_MEMO,
            metadata={"duration": 45},
        )

        assert transcript.title == "Meeting with Mayor"
        assert transcript.date.day == 9
        assert transcript.source == "voice_memo"

    def test_transcript_date_parsing(self):
        """Test date parsing from string."""
        transcript = TranscriptInput(title="Test", content="Content", date="2025-01-09T14:00:00")

        assert isinstance(transcript.date, datetime)
        assert transcript.date.year == 2025

        # Test with timezone
        transcript2 = TranscriptInput(title="Test", content="Content", date="2025-01-09T14:00:00Z")

        assert transcript2.date.tzinfo is not None


class TestProcessingResult:
    """Test ProcessingResult model."""

    def test_processing_result_creation(self):
        """Test creating a processing result."""
        result = ProcessingResult()

        assert result.success is True
        assert len(result.created) == 0
        assert len(result.errors) == 0
        assert result.total_changes == 0

    def test_add_error(self):
        """Test adding errors to result."""
        result = ProcessingResult()

        result.add_error(
            stage="extraction",
            error_type="APIError",
            message="Failed to connect to AI",
            entity="John Doe",
        )

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].stage == "extraction"
        assert result.errors[0].entity == "John Doe"

    def test_total_changes_calculation(self):
        """Test total changes calculation."""
        result = ProcessingResult()

        # Add some mock pages
        page1 = NotionPage(
            id="page1",
            database_id="db1",
            properties={},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow(),
        )

        result.created.append(page1)
        result.updated.append(page1)
        result.relationships_created = 3

        assert result.total_changes == 5


class TestBatchResult:
    """Test BatchResult model."""

    def test_batch_result_creation(self):
        """Test creating a batch result."""
        batch = BatchResult(total_transcripts=10, successful=0, failed=0)

        assert batch.total_transcripts == 10
        assert batch.successful == 0
        assert batch.failed == 0
        assert batch.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        batch = BatchResult(total_transcripts=10, successful=7, failed=3)

        assert batch.success_rate == 0.7

    def test_processing_time(self):
        """Test processing time calculation."""
        batch = BatchResult(total_transcripts=5, successful=5, failed=0)
        batch.end_time = datetime.utcnow()

        assert batch.processing_time is not None
        assert batch.processing_time >= 0


class TestConfiguration:
    """Test configuration models."""

    def test_database_config(self):
        """Test DatabaseConfig model."""
        config = DatabaseConfig(
            id="db123", name="People & Contacts", mappings={"name": "Full Name", "role": "Role"}
        )

        assert config.id == "db123"
        assert config.name == "People & Contacts"
        assert config.mappings["name"] == "Full Name"

    def test_notion_config(self):
        """Test NotionConfig model."""
        config = NotionConfig(
            api_key="secret123", databases={"people": DatabaseConfig(id="db1", name="People")}
        )

        assert config.api_key == "secret123"
        assert config.rate_limit == 3.0  # default
        assert config.retry_attempts == 3  # default

    def test_ai_config(self):
        """Test AIConfig model."""
        config = AIConfig(api_key="ai-key-123")

        assert config.provider == "claude"  # default
        assert config.model == "claude-3-sonnet-20240229"  # default
        assert config.temperature == 0.3  # default

    def test_complete_config(self):
        """Test complete Config model."""
        config = Config(
            notion=NotionConfig(api_key="notion-key", databases={}), ai=AIConfig(api_key="ai-key")
        )

        assert config.notion.api_key == "notion-key"
        assert config.ai.api_key == "ai-key"
        assert config.processing.dry_run is False  # default
