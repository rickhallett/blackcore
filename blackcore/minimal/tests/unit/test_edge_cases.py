"""Edge case and error handling tests for minimal module."""

import pytest
import json
import tempfile
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import threading
import os

from blackcore.minimal.models import (
    TranscriptInput,
    Entity,
    EntityType,
    ProcessingError,
    ExtractedEntities,
)
from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.ai_extractor import AIExtractor
from blackcore.minimal.notion_updater import NotionUpdater, RateLimiter
from blackcore.minimal.cache import SimpleCache
from blackcore.minimal.property_handlers import PropertyHandlerFactory

from ..fixtures import (
    EMPTY_TRANSCRIPT,
    LARGE_TRANSCRIPT,
    SPECIAL_CHARS_TRANSCRIPT,
    ERROR_TRANSCRIPT,
)
from ..utils import create_test_config


class TestLargeDataHandling:
    """Test handling of large data sets."""

    @patch("blackcore.minimal.transcript_processor.AIExtractor")
    @patch("blackcore.minimal.transcript_processor.NotionUpdater")
    @patch("blackcore.minimal.transcript_processor.SimpleCache")
    def test_process_very_large_transcript(
        self, mock_cache, mock_updater_class, mock_extractor_class
    ):
        """Test processing transcript with very large content."""
        # Create a very large transcript (1MB+)
        large_content = "This is a test sentence. " * 50000  # ~1MB
        large_transcript = TranscriptInput(
            title="Large Transcript", content=large_content, date=datetime.now()
        )

        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract_entities.return_value = ExtractedEntities(
            entities=[Entity(name="Test Entity", type=EntityType.PERSON)], relationships=[]
        )
        mock_extractor_class.return_value = mock_extractor

        mock_updater = Mock()
        mock_updater.find_or_create_page.return_value = (Mock(id="page-123"), True)
        mock_updater_class.return_value = mock_updater

        config = create_test_config()
        processor = TranscriptProcessor(config=config)

        # Should handle without error
        result = processor.process_transcript(large_transcript)
        assert result.success is True

        # AI should receive the full content
        mock_extractor.extract_entities.assert_called_once()
        call_text = mock_extractor.extract_entities.call_args[1]["text"]
        assert len(call_text) > 1000000

    def test_process_many_entities(self):
        """Test processing transcript that extracts many entities."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Create many entities
            entities = []
            for i in range(100):
                entities.append(
                    Entity(name=f"Person {i}", type=EntityType.PERSON, properties={"id": i})
                )

            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=entities, relationships=[]
            )
            mock_extractor_class.return_value = mock_extractor

            # Mock updater to handle all entities
            mock_updater = Mock()
            mock_updater.find_or_create_page.return_value = (Mock(id="page-id"), True)
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            assert result.success is True
            assert len(result.created) == 100
            assert mock_updater.find_or_create_page.call_count == 100


class TestConcurrency:
    """Test concurrent access scenarios."""

    def test_cache_concurrent_access(self):
        """Test cache with concurrent read/write operations."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = SimpleCache(cache_dir=cache_dir)

            results = []
            errors = []

            def write_operation(i):
                try:
                    cache.set(f"key_{i}", {"value": i})
                    results.append(f"write_{i}")
                except Exception as e:
                    errors.append(e)

            def read_operation(i):
                try:
                    value = cache.get(f"key_{i}")
                    results.append(f"read_{i}_{value}")
                except Exception as e:
                    errors.append(e)

            # Create threads
            threads = []
            for i in range(10):
                # Alternate between read and write
                if i % 2 == 0:
                    t = threading.Thread(target=write_operation, args=(i,))
                else:
                    t = threading.Thread(target=read_operation, args=(i - 1,))
                threads.append(t)

            # Start all threads
            for t in threads:
                t.start()

            # Wait for completion
            for t in threads:
                t.join()

            # Should complete without errors
            assert len(errors) == 0
            assert len(results) > 0

    def test_rate_limiter_concurrent_requests(self):
        """Test rate limiter with concurrent requests."""
        limiter = RateLimiter(requests_per_second=10)  # 100ms between requests

        request_times = []

        def make_request():
            limiter.wait_if_needed()
            request_times.append(time.time())

        # Create multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)

        # Start all threads at once
        start_time = time.time()
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Check that requests were properly spaced
        request_times.sort()
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i - 1]
            # Allow small margin for thread scheduling
            assert time_diff >= 0.09  # Should be at least 90ms apart


class TestSpecialCharactersAndEncoding:
    """Test handling of special characters and encoding issues."""

    def test_unicode_in_transcript(self):
        """Test processing transcript with various unicode characters."""
        unicode_transcript = TranscriptInput(
            title="Unicode Test 🌍",
            content="""
            Meeting with François Müller from Zürich.
            Discussed 日本 (Japan) expansion.
            Budget: €1,000,000
            Emojis: 😀 🎉 🚀
            Math: ∑(x²) = ∞
            Symbols: ™ © ® ¶ § ¿
            """,
            metadata={"language": "multi"},
        )

        config = create_test_config()

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
            result = processor.process_transcript(unicode_transcript)

            # Should handle unicode without errors
            assert result.success is True

            # Check that unicode was preserved in AI call
            call_text = mock_extractor.extract_entities.call_args[1]["text"]
            assert "François" in call_text
            assert "€" in call_text
            assert "🌍" in call_text

    def test_special_characters_in_properties(self):
        """Test handling special characters in entity properties."""
        factory = PropertyHandlerFactory()

        # Test various special characters
        test_cases = [
            ("text", "Hello\nWorld\tTab", "rich_text"),
            ("text", "<script>alert('xss')</script>", "rich_text"),
            ("email", "test+special@example.com", "email"),
            ("url", "https://example.com/path?query=value&special=%20", "url"),
            ("phone", "+1 (555) 123-4567", "phone_number"),
            ("select", "Option with spaces & symbols!", "select"),
        ]

        for prop_type, value, expected_type in test_cases:
            handler = factory.create_handler(prop_type)

            # Should validate without errors
            assert handler.validate(value) is True

            # Should format correctly
            formatted = handler.format_for_api(value)
            assert formatted["type"] == expected_type


class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_partial_batch_failure_recovery(self):
        """Test recovery when some items in batch fail."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Make extraction fail for specific transcripts
            call_count = 0

            def extract_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Fail on second transcript
                    raise Exception("AI API Error")
                return ExtractedEntities(entities=[], relationships=[])

            mock_extractor = Mock()
            mock_extractor.extract_entities.side_effect = extract_side_effect
            mock_extractor_class.return_value = mock_extractor

            mock_updater = Mock()
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)

            # Process batch of 3
            transcripts = [
                TranscriptInput(title=f"Test {i}", content=f"Content {i}") for i in range(3)
            ]

            result = processor.process_batch(transcripts)

            # Should process other transcripts despite one failure
            assert result.total_transcripts == 3
            assert result.successful == 2
            assert result.failed == 1
            assert result.success_rate == 2 / 3

    def test_notion_api_intermittent_failures(self):
        """Test handling intermittent Notion API failures."""
        config = create_test_config()

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Setup successful extraction
            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=[
                    Entity(name="Person 1", type=EntityType.PERSON),
                    Entity(name="Person 2", type=EntityType.PERSON),
                    Entity(name="Person 3", type=EntityType.PERSON),
                ],
                relationships=[],
            )
            mock_extractor_class.return_value = mock_extractor

            # Make Notion fail for middle entity
            call_count = 0

            def notion_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Notion API Error")
                return (Mock(id=f"page-{call_count}"), True)

            mock_updater = Mock()
            mock_updater.find_or_create_page.side_effect = notion_side_effect
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            # Should still be marked as failed
            assert result.success is False
            assert len(result.errors) > 0
            # But should have processed some entities
            assert len(result.created) == 2


class TestCacheEdgeCases:
    """Test cache edge cases and error conditions."""

    def test_cache_disk_full_simulation(self):
        """Test cache behavior when disk is full."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = SimpleCache(cache_dir=cache_dir)

            # Mock file write to fail
            with patch("builtins.open", side_effect=OSError("No space left on device")):
                # Should handle gracefully
                cache.set("test_key", {"data": "value"})

                # Get should return None for failed write
                assert cache.get("test_key") is None

    def test_cache_corrupted_file(self):
        """Test cache behavior with corrupted cache files."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = SimpleCache(cache_dir=cache_dir)

            # Write valid cache entry
            cache.set("test_key", {"data": "value"})

            # Corrupt the cache file
            cache_file = Path(cache_dir) / cache._get_cache_filename("test_key")
            cache_file.write_text("{ corrupted json")

            # Should handle gracefully
            result = cache.get("test_key")
            assert result is None

    def test_cache_key_collision(self):
        """Test cache with potential key collisions."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = SimpleCache(cache_dir=cache_dir)

            # These could potentially have same hash
            key1 = "a" * 1000
            key2 = "a" * 1000 + "b"

            cache.set(key1, {"value": 1})
            cache.set(key2, {"value": 2})

            # Should maintain separate values
            assert cache.get(key1)["value"] == 1
            assert cache.get(key2)["value"] == 2


class TestAPILimits:
    """Test handling of API limits and constraints."""

    def test_notion_block_limit(self):
        """Test handling Notion's 2000 block limit."""
        # Create content that would exceed block limit
        huge_content = "\n".join([f"Line {i}" for i in range(3000)])

        handler = PropertyHandlerFactory().create_handler("text")

        # Should truncate to fit within limits
        formatted = handler.format_for_api(huge_content)

        # Rich text should be limited
        assert "rich_text" in formatted
        text_content = formatted["rich_text"][0]["text"]["content"]
        # Notion limit is 2000 chars per text block
        assert len(text_content) <= 2000

    def test_ai_token_limit_handling(self):
        """Test handling of AI token limits."""
        # Create very long content that might exceed token limits
        long_content = "This is a test. " * 10000  # ~40k tokens

        config = create_test_config()
        config.ai.max_tokens = 4000  # Set a limit

        extractor = AIExtractor(config.ai)

        # Mock the AI client
        with patch("anthropic.Anthropic") as mock_claude:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text=json.dumps({"entities": [], "relationships": []}))]
            mock_client.messages.create.return_value = mock_response
            mock_claude.return_value = mock_client

            # Should handle without error
            result = extractor.extract_entities(long_content)
            assert isinstance(result, ExtractedEntities)

            # Check that max_tokens was passed
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 4000


class TestDatabaseConfigurationEdgeCases:
    """Test edge cases in database configuration."""

    def test_missing_database_config(self):
        """Test handling when database configs are missing."""
        config = create_test_config()
        # Remove all database configs
        config.notion.databases = {}

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater"),
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            # Extract various entity types
            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=[
                    Entity(name="Person", type=EntityType.PERSON),
                    Entity(name="Org", type=EntityType.ORGANIZATION),
                    Entity(name="Task", type=EntityType.TASK),
                ],
                relationships=[],
            )
            mock_extractor_class.return_value = mock_extractor

            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            # Should complete but not create any pages
            assert result.success is True
            assert len(result.created) == 0
            assert len(result.updated) == 0

    def test_partial_database_config(self):
        """Test with only some databases configured."""
        config = create_test_config()
        # Only keep people database
        config.notion.databases = {"people": config.notion.databases["people"]}

        with (
            patch("blackcore.minimal.transcript_processor.AIExtractor") as mock_extractor_class,
            patch("blackcore.minimal.transcript_processor.NotionUpdater") as mock_updater_class,
            patch("blackcore.minimal.transcript_processor.SimpleCache"),
        ):
            mock_extractor = Mock()
            mock_extractor.extract_entities.return_value = ExtractedEntities(
                entities=[
                    Entity(name="Person", type=EntityType.PERSON),
                    Entity(name="Org", type=EntityType.ORGANIZATION),
                ],
                relationships=[],
            )
            mock_extractor_class.return_value = mock_extractor

            mock_updater = Mock()
            mock_updater.find_or_create_page.return_value = (Mock(id="person-1"), True)
            mock_updater_class.return_value = mock_updater

            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(SIMPLE_TRANSCRIPT)

            # Should only process person entity
            assert result.success is True
            assert len(result.created) == 1
            assert mock_updater.find_or_create_page.call_count == 1
