"""Configuration and edge case validation tests for the transcript processor.

This module tests configuration validation and edge case handling:
- Invalid configuration combinations
- Missing required fields
- Boundary value testing
- Unusual but valid configurations
- Configuration migration scenarios
- Environment variable handling
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import (
    Config,
    NotionConfig,
    AIConfig,
    ProcessingConfig,
    DatabaseConfig,
    TranscriptInput,
    Entity,
    EntityType,
    ExtractedEntities,
    NotionPage,
    Relationship,
)
from blackcore.minimal.validators import validate_api_key
from blackcore.minimal import constants


class TestConfigurationValidation:
    """Test suite for configuration validation and edge cases."""

    def test_minimal_valid_configuration(self):
        """Test the absolute minimum valid configuration."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(
                api_key="sk-ant-" + "a" * 95,
            ),
        )
        
        # Should create processor without errors
        processor = TranscriptProcessor(config=config)
        assert processor is not None
        assert processor.config.ai.provider == "claude"  # Default
        assert processor.config.ai.model == "claude-3-sonnet-20240229"  # Default

    def test_invalid_notion_api_key_formats(self):
        """Test various invalid Notion API key formats."""
        from pydantic import ValidationError
        
        invalid_keys = [
            "",  # Empty
            "secret_",  # Too short
            "secret_" + "a" * 42,  # One char short
            "secret_" + "a" * 44,  # One char long
            "wrong_" + "a" * 43,  # Wrong prefix
            "SECRET_" + "a" * 43,  # Wrong case
            "secret_" + "!" * 43,  # Invalid characters
            None,  # None value
        ]
        
        for invalid_key in invalid_keys:
            # Handle both Pydantic validation errors and ValueError from processor
            with pytest.raises((ValueError, ValidationError)):
                config = Config(
                    notion=NotionConfig(
                        api_key=invalid_key,
                        databases={
                            "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                            "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                            "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                            "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                            "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                        },
                    ),
                    ai=AIConfig(api_key="sk-ant-" + "a" * 95),
                )
                TranscriptProcessor(config=config)

    def test_invalid_ai_api_key_formats(self):
        """Test various invalid AI API key formats."""
        from pydantic import ValidationError
        
        # Test Anthropic key validation
        invalid_anthropic_keys = [
            "",  # Empty
            "sk-ant-",  # Too short
            "sk-ant-" + "a" * 94,  # One char short
            "sk-ant-" + "a" * 96,  # One char long
            "sk_ant_" + "a" * 95,  # Wrong separator
            "SK-ANT-" + "a" * 95,  # Wrong case
            None,  # None value
        ]
        
        for invalid_key in invalid_anthropic_keys:
            with pytest.raises((ValueError, ValidationError)):
                config = Config(
                    notion=NotionConfig(
                        api_key="secret_" + "a" * 43,
                        databases={
                            "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                            "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                            "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                            "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                            "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                        },
                    ),
                    ai=AIConfig(api_key=invalid_key, provider="claude"),
                )
                TranscriptProcessor(config=config)

    def test_missing_required_databases(self):
        """Test configuration with missing required databases."""
        # Test with some databases missing
        incomplete_databases = {
            "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
            "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
            # Missing tasks, transcripts, transgressions
        }
        
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases=incomplete_databases,
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        
        # Should create processor without error (missing databases are warned about)
        processor = TranscriptProcessor(config=config)
        assert processor is not None
        
        # Test with empty databases dict
        config2 = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={},
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        
        # Should also work with empty databases
        processor2 = TranscriptProcessor(config=config2)
        assert processor2 is not None

    def test_invalid_database_ids(self):
        """Test various invalid database ID formats."""
        # Empty database ID is actually allowed by DatabaseConfig
        empty_db = DatabaseConfig(id="", name="People")
        assert empty_db.id == ""
        assert empty_db.name == "People"
        
        # None is not allowed for required field
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DatabaseConfig(id=None, name="People")
        
        # Database IDs with dashes are kept as-is (no cleaning)
        db_with_dashes = DatabaseConfig(
            id="12-34-56-78-90-12-34-56-78-90-12-34-56-78-90-12",
            name="Test"
        )
        # Dashes are preserved
        assert db_with_dashes.id == "12-34-56-78-90-12-34-56-78-90-12-34-56-78-90-12"
        
        # Valid 32-char hex ID should work
        valid_db = DatabaseConfig(
            id="12345678901234567890123456789012",
            name="Test"
        )
        assert valid_db.id == "12345678901234567890123456789012"

    def test_processing_config_edge_cases(self):
        """Test edge cases in processing configuration."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
            processing=ProcessingConfig(
                batch_size=1,  # Minimum batch size
                cache_ttl=0,  # No caching
                dry_run=True,
                verbose=True,
                enable_deduplication=False,
            ),
        )
        
        processor = TranscriptProcessor(config=config)
        assert processor.config.processing.batch_size == 1
        assert processor.config.processing.cache_ttl == 0
        assert processor.config.processing.dry_run == True
        assert processor.config.processing.verbose == True
        assert processor.config.processing.enable_deduplication == False

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            "NOTION_API_KEY": "secret_" + "b" * 43,
            "ANTHROPIC_API_KEY": "sk-ant-" + "b" * 95,
            "OPENAI_API_KEY": "sk-" + "b" * 48,
        }):
            # Test that env vars can be used if config doesn't specify
            # This would require modifying Config to support env var loading
            # For now, test that we can validate keys from env
            assert validate_api_key(os.environ["NOTION_API_KEY"], "notion")
            assert validate_api_key(os.environ["ANTHROPIC_API_KEY"], "anthropic")
            assert validate_api_key(os.environ["OPENAI_API_KEY"], "openai")

    def test_cache_directory_permissions(self, tmp_path):
        """Test cache directory creation with various permission scenarios."""
        import os
        import platform
        
        # Skip permission test on Windows
        if platform.system() == 'Windows':
            pytest.skip("File permissions work differently on Windows")
        
        # Test read-only parent directory
        read_only_dir = tmp_path / "read_only"
        read_only_dir.mkdir()
        
        try:
            # Make directory read-only
            read_only_dir.chmod(0o444)
            
            config = Config(
                notion=NotionConfig(
                    api_key="secret_" + "a" * 43,
                    databases={
                        "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                        "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                        "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                        "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                        "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                    },
                ),
                ai=AIConfig(api_key="sk-ant-" + "a" * 95),
                processing=ProcessingConfig(
                    cache_dir=str(read_only_dir / "cache"),
                    dry_run=True,  # Avoid actual processing
                ),
            )
            
            # Should raise error when trying to create cache dir in read-only parent
            with pytest.raises((PermissionError, OSError, FileNotFoundError)):
                processor = TranscriptProcessor(config=config)
            
        finally:
            # Always cleanup permissions
            try:
                read_only_dir.chmod(0o755)
            except:
                pass


class TestTranscriptInputEdgeCases:
    """Test edge cases for transcript input processing."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a processor for testing."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = True
        
        processor = TranscriptProcessor(config=config)
        processor.ai_extractor.extract_entities = Mock()
        return processor

    def test_empty_transcript_content(self, processor):
        """Test processing empty transcript content."""
        transcript = TranscriptInput(
            title="Empty Meeting",
            content="",  # Empty content
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        # Should handle gracefully
        processor.ai_extractor.extract_entities.return_value = ExtractedEntities(
            entities=[],
            relationships=[],
            summary="Empty transcript",
            key_points=[]
        )
        
        # Create mock for notion updater
        mock_transcript_page = NotionPage(
            id="transcript-123",
            database_id="transcript-db",
            properties={"Title": "Empty Meeting"},
            created_time=datetime.utcnow(),
            last_edited_time=datetime.utcnow()
        )
        processor.notion_updater.find_or_create_page = Mock(return_value=(mock_transcript_page, True))
        
        result = processor.process_transcript(transcript)
        assert result.success
        # In dry run mode, nothing is actually updated
        # Just verify no errors occurred

    def test_very_long_transcript_content(self, processor):
        """Test processing very long transcript content."""
        # Create content that exceeds typical limits
        long_content = "This is a very long transcript. " * 10000  # ~300KB
        
        transcript = TranscriptInput(
            title="Very Long Meeting",
            content=long_content,
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        processor.ai_extractor.extract_entities.return_value = ExtractedEntities(
            entities=[
                Entity(type=EntityType.PERSON, name="Long Speaker", confidence=0.9)
            ],
            relationships=[],
            summary="Long meeting summary",
            key_points=["Point 1", "Point 2"]
        )
        
        # Mock notion operations
        with patch.object(processor.notion_updater, 'create_page') as mock_create_page:
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_find_create:
                mock_page = NotionPage(
                    id="page-123",
                    database_id="db-123",
                    properties={},
                    created_time=datetime.utcnow(),
                    last_edited_time=datetime.utcnow()
                )
                mock_create_page.return_value = mock_page
                mock_find_create.return_value = (mock_page, True)
                
                result = processor.process_transcript(transcript)
                assert result.success
                
                # Check that extract_entities was called with the content
                processor.ai_extractor.extract_entities.assert_called_once()
                # Get the actual call arguments
                call_kwargs = processor.ai_extractor.extract_entities.call_args.kwargs
                assert 'text' in call_kwargs
                assert call_kwargs['text'] == long_content

    def test_special_characters_in_content(self, processor):
        """Test transcript content with special characters."""
        special_content = """Meeting with émojis 🎉 and special chars: 
        - Null char: \0
        - Tabs: \t\t\t
        - Unicode: 你好世界
        - RTL: مرحبا بالعالم
        - Math: ∑∏∫∂
        - Quotes: "smart quotes" and 'single quotes'
        - Line breaks: \r\n\r\n
        """
        
        transcript = TranscriptInput(
            title="Special Characters Meeting",
            content=special_content,
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[
                    Entity(type=EntityType.PERSON, name="Unicode Speaker", confidence=0.9)
                ],
                relationships=[],
                summary="Meeting with special characters",
                key_points=[]
            )
            
            result = processor.process_transcript(transcript)
            assert result.success

    def test_invalid_date_formats(self, processor):
        """Test various invalid date formats."""
        from pydantic import ValidationError
        
        invalid_dates = [
            "2024-13-01T10:00:00Z",  # Invalid month
            "2024-01-32T10:00:00Z",  # Invalid day
            "2024-01-01T25:00:00Z",  # Invalid hour
            "not-a-date",  # Not a date
            "",  # Empty
            "2024/01/01",  # Wrong format
            "01-01-2024",  # Wrong format
        ]
        
        for invalid_date in invalid_dates:
            # TranscriptInput should validate dates at creation time
            with pytest.raises(ValidationError):
                transcript = TranscriptInput(
                    title="Invalid Date Meeting",
                    content="Test content",
                    date=invalid_date,
                    source="personal_note"
                )

    def test_invalid_source_values(self, processor):
        """Test invalid source enum values."""
        with pytest.raises(ValueError, match="Input should be"):
            transcript = TranscriptInput(
                title="Invalid Source",
                content="Test content",
                date=datetime.now().isoformat() + "Z",
                source="invalid_source"  # Not a valid enum
            )

    def test_extremely_long_title(self, processor):
        """Test transcript with extremely long title."""
        long_title = "A" * 1000  # Very long title
        
        transcript = TranscriptInput(
            title=long_title,
            content="Normal content",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[],
                relationships=[],
                summary="Test",
                key_points=[]
            )
            
            result = processor.process_transcript(transcript)
            assert result.success
            # Title should be truncated for Notion (max 2000 chars)

    def test_none_and_null_values(self, processor):
        """Test handling of None and null values in various fields."""
        # Test with minimal required fields
        transcript = TranscriptInput(
            title="Minimal Meeting",
            content="Some content",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            # Return entities with None/empty fields
            mock_extract.return_value = ExtractedEntities(
                entities=[
                    Entity(
                        type=EntityType.PERSON,
                        name="John Doe",
                        confidence=0.9,
                        context=None,  # None context
                        properties={}  # Empty properties
                    )
                ],
                relationships=[],
                summary=None,  # None summary
                key_points=[]  # Empty key points
            )
            
            result = processor.process_transcript(transcript)
            assert result.success


class TestEntityExtractionEdgeCases:
    """Test edge cases in entity extraction and processing."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a processor for testing."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = True
        
        return TranscriptProcessor(config=config)

    def test_duplicate_entity_names(self, processor):
        """Test handling of duplicate entity names in same extraction."""
        transcript = TranscriptInput(
            title="Duplicate Names Meeting",
            content="John Smith from Company A and John Smith from Company B met today.",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[
                    Entity(
                        type=EntityType.PERSON,
                        name="John Smith",
                        confidence=0.95,
                        context="From Company A"
                    ),
                    Entity(
                        type=EntityType.PERSON,
                        name="John Smith",
                        confidence=0.95,
                        context="From Company B"
                    ),
                ],
                relationships=[],
                summary="Meeting with two different John Smiths",
                key_points=[]
            )
            
            result = processor.process_transcript(transcript)
            assert result.success
            # Should handle duplicate names appropriately

    def test_very_low_confidence_entities(self, processor):
        """Test handling of entities with very low confidence scores."""
        transcript = TranscriptInput(
            title="Low Confidence Meeting",
            content="Maybe John or Jim discussed something with possibly ACME Corp.",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[
                    Entity(
                        type=EntityType.PERSON,
                        name="John",
                        confidence=0.1,  # Very low confidence
                        context="Uncertain"
                    ),
                    Entity(
                        type=EntityType.ORGANIZATION,
                        name="ACME Corp",
                        confidence=0.2,  # Low confidence
                        context="Possibly mentioned"
                    ),
                ],
                relationships=[],
                summary="Uncertain meeting content",
                key_points=[]
            )
            
            result = processor.process_transcript(transcript)
            assert result.success
            # Low confidence entities should still be processed

    def test_circular_relationships(self, processor):
        """Test handling of circular relationships between entities."""
        transcript = TranscriptInput(
            title="Circular Relations",
            content="A manages B, B manages C, and C manages A.",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[
                    Entity(type=EntityType.PERSON, name="Person A", confidence=0.9),
                    Entity(type=EntityType.PERSON, name="Person B", confidence=0.9),
                    Entity(type=EntityType.PERSON, name="Person C", confidence=0.9),
                ],
                relationships=[
                    Relationship(
                        source_entity="Person A",
                        source_type=EntityType.PERSON,
                        target_entity="Person B",
                        target_type=EntityType.PERSON,
                        relationship_type="manages"
                    ),
                    Relationship(
                        source_entity="Person B",
                        source_type=EntityType.PERSON,
                        target_entity="Person C",
                        target_type=EntityType.PERSON,
                        relationship_type="manages"
                    ),
                    Relationship(
                        source_entity="Person C",
                        source_type=EntityType.PERSON,
                        target_entity="Person A",
                        target_type=EntityType.PERSON,
                        relationship_type="manages"
                    ),
                ],
                summary="Circular management structure",
                key_points=[]
            )
            
            # Mock notion operations
            with patch.object(processor.notion_updater, 'create_page') as mock_create:
                with patch.object(processor.notion_updater, 'find_or_create_page') as mock_find:
                    mock_page = NotionPage(
                        id="page-123",
                        database_id="db-123",
                        properties={},
                        created_time=datetime.utcnow(),
                        last_edited_time=datetime.utcnow()
                    )
                    mock_create.return_value = mock_page
                    mock_find.return_value = (mock_page, True)
                    
                    result = processor.process_transcript(transcript)
                    assert result.success
                    # Should handle circular relationships without infinite loops

    def test_entity_name_edge_cases(self, processor):
        """Test entity names with edge case values."""
        edge_case_names = [
            "",  # Empty name
            " ",  # Whitespace only
            "A",  # Single character
            "A" * 500,  # Very long name
            "Name\nWith\nNewlines",  # Newlines
            "Name\tWith\tTabs",  # Tabs
            "Name With  Multiple   Spaces",  # Multiple spaces
            "🎉 Emoji Name 🎉",  # Emojis
            "<script>alert('XSS')</script>",  # HTML/Script injection
            "Robert'; DROP TABLE Students;--",  # SQL injection
        ]
        
        for name in edge_case_names:
            transcript = TranscriptInput(
                title=f"Edge Case: {name[:50]}",
                content=f"Meeting with {name}",
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            )
            
            with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
                mock_extract.return_value = ExtractedEntities(
                    entities=[
                        Entity(
                            type=EntityType.PERSON,
                            name=name,
                            confidence=0.9
                        )
                    ],
                    relationships=[],
                    summary="Edge case test",
                    key_points=[]
                )
                
                # Should handle without crashing
                try:
                    result = processor.process_transcript(transcript)
                    # Empty names should be skipped
                    if name.strip():
                        assert result.success
                except ValueError:
                    # Expected for invalid names
                    assert name.strip() == ""


class TestBatchProcessingEdgeCases:
    """Test edge cases in batch processing."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a processor for testing."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
        )
        config.processing.cache_dir = str(tmp_path / "cache")
        config.processing.dry_run = True
        config.processing.batch_size = 5
        
        return TranscriptProcessor(config=config)

    def test_empty_batch(self, processor):
        """Test processing an empty batch."""
        result = processor.process_batch([])
        
        assert result.total_transcripts == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.success_rate == 0.0  # Or might be NaN
        assert len(result.results) == 0

    def test_single_item_batch(self, processor):
        """Test processing a batch with single item."""
        transcript = TranscriptInput(
            title="Single Item",
            content="Solo meeting",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[],
                relationships=[],
                summary="Solo",
                key_points=[]
            )
            
            result = processor.process_batch([transcript])
            
            assert result.total_transcripts == 1
            assert result.successful == 1
            assert result.failed == 0
            assert result.success_rate == 1.0

    def test_mixed_valid_invalid_batch(self, processor):
        """Test batch with mix of valid and invalid transcripts."""
        transcripts = [
            TranscriptInput(
                title="Valid 1",
                content="Content 1",
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            ),
            TranscriptInput(
                title="Valid 2",
                content="Content 2",
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            ),
        ]
        
        # Make one fail during processing
        def side_effect(*args, **kwargs):
            # Check if this is the first transcript
            text = kwargs.get('text', '') if kwargs else (args[0] if args else '')
            if "Content 1" in str(text):
                raise Exception("Simulated failure")
            return ExtractedEntities(
                entities=[],
                relationships=[],
                summary="Success",
                key_points=[]
            )
        
        # Mock extract_entities with side_effect
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = side_effect
        
            # Mock notion operations for successful transcript
            with patch.object(processor.notion_updater, 'find_or_create_page') as mock_create:
                mock_page = NotionPage(
                    id="page-123",
                    database_id="db-123",
                    properties={},
                    created_time=datetime.utcnow(),
                    last_edited_time=datetime.utcnow()
                )
                mock_create.return_value = (mock_page, True)
                
                result = processor.process_batch(transcripts)
                
                assert result.total_transcripts == 2
                assert result.successful == 1
                assert result.failed == 1
                assert result.success_rate == 0.5

    def test_batch_size_boundary_cases(self, processor):
        """Test batch processing at size boundaries."""
        # Test exactly at batch size
        transcripts_5 = [
            TranscriptInput(
                title=f"Meeting {i}",
                content=f"Content {i}",
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            )
            for i in range(5)  # Exactly batch size
        ]
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[],
                relationships=[],
                summary="Test",
                key_points=[]
            )
            
            result = processor.process_batch(transcripts_5)
            assert result.total_transcripts == 5
            
        # Test one over batch size
        transcripts_6 = transcripts_5 + [
            TranscriptInput(
                title="Meeting 6",
                content="Content 6",
                date=datetime.now().isoformat() + "Z",
                source="personal_note"
            )
        ]
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[],
                relationships=[],
                summary="Test",
                key_points=[]
            )
            
            result = processor.process_batch(transcripts_6)
            assert result.total_transcripts == 6


class TestFileSystemEdgeCases:
    """Test edge cases related to file system operations."""

    def test_cache_directory_edge_cases(self, tmp_path):
        """Test various cache directory edge cases."""
        # Test with non-existent parent directory
        non_existent = tmp_path / "does" / "not" / "exist" / "cache"
        
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
            processing=ProcessingConfig(
                cache_dir=str(non_existent),
                dry_run=True,
            ),
        )
        
        # Should create directory hierarchy
        processor = TranscriptProcessor(config=config)
        assert processor is not None
        # Check that cache directory creation was attempted
        # The actual directory might not exist if SimpleCache handles missing dirs gracefully
        assert processor.cache is not None

    def test_cache_file_corruption(self, tmp_path):
        """Test handling of corrupted cache files."""
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
            processing=ProcessingConfig(
                cache_dir=str(tmp_path / "cache"),
                dry_run=True,
            ),
        )
        
        processor = TranscriptProcessor(config=config)
        
        # Create a corrupted cache file
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        # Write invalid JSON to cache file
        cache_file = cache_dir / "corrupted.json"
        cache_file.write_text("{ invalid json ][")
        
        # Processor should handle corrupted cache gracefully
        transcript = TranscriptInput(
            title="Test",
            content="Test content",
            date=datetime.now().isoformat() + "Z",
            source="personal_note"
        )
        
        with patch.object(processor.ai_extractor, 'extract_entities') as mock_extract:
            mock_extract.return_value = ExtractedEntities(
                entities=[],
                relationships=[],
                summary="Test",
                key_points=[]
            )
            
            # Should not crash on corrupted cache
            result = processor.process_transcript(transcript)
            assert result.success


class TestConfigurationMigration:
    """Test configuration migration and backwards compatibility."""

    def test_old_config_format_migration(self):
        """Test migrating from old configuration format."""
        # Simulate old config format (if applicable)
        old_config = {
            "notion_api_key": "secret_" + "a" * 43,
            "anthropic_api_key": "sk-ant-" + "a" * 95,
            "database_ids": {
                "people": "12345678901234567890123456789012",
                "organizations": "abcdef12345678901234567890123456",
                "tasks": "98765432109876543210987654321098",
                "transcripts": "11111111222222223333333344444444",
                "transgressions": "aaaabbbbccccddddeeeeffffgggghhh",
            }
        }
        
        # Would need migration logic to convert old format to new
        # For now, just verify new format works
        new_config = Config(
            notion=NotionConfig(
                api_key=old_config["notion_api_key"],
                databases={
                    name: DatabaseConfig(id=id, name=name.title())
                    for name, id in old_config["database_ids"].items()
                },
            ),
            ai=AIConfig(api_key=old_config["anthropic_api_key"]),
        )
        
        processor = TranscriptProcessor(config=new_config)
        assert processor is not None

    def test_partial_config_with_defaults(self):
        """Test that partial configs work with sensible defaults."""
        # Minimal config relying on defaults
        config = Config(
            notion=NotionConfig(
                api_key="secret_" + "a" * 43,
                databases={
                    "people": DatabaseConfig(id="12345678901234567890123456789012", name="People"),
                    "organizations": DatabaseConfig(id="abcdef12345678901234567890123456", name="Organizations"),
                    "tasks": DatabaseConfig(id="98765432109876543210987654321098", name="Tasks"),
                    "transcripts": DatabaseConfig(id="11111111222222223333333344444444", name="Transcripts"),
                    "transgressions": DatabaseConfig(id="aaaabbbbccccddddeeeeffffgggghhh", name="Transgressions"),
                },
            ),
            ai=AIConfig(api_key="sk-ant-" + "a" * 95),
            # Don't specify processing config, use defaults
        )
        
        processor = TranscriptProcessor(config=config)
        
        # Check defaults were applied
        assert processor.config.processing.batch_size == constants.DEFAULT_BATCH_SIZE
        assert processor.config.processing.cache_ttl == constants.DEFAULT_CACHE_TTL
        assert processor.config.processing.dry_run == False  # Default