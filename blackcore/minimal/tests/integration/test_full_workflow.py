"""Integration tests for full transcript processing workflow."""

import pytest
import json
import time
from datetime import datetime
from pathlib import Path

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput, ProcessingError


class TestFullWorkflow:
    """Test complete transcript processing workflow."""

    def test_simple_transcript_end_to_end(self, integration_test_env, sample_transcripts):
        """Test processing a simple transcript from input to Notion pages."""
        env = integration_test_env
        transcript_data = sample_transcripts["meeting"]

        # Create transcript input
        transcript = TranscriptInput(
            title=transcript_data["title"],
            content=transcript_data["content"],
            date=datetime.fromisoformat(transcript_data["date"]),
            metadata=transcript_data["metadata"],
        )

        # Process transcript
        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Verify success
        assert result.success is True
        assert len(result.errors) == 0

        # Verify entities were created
        assert len(result.created) > 0

        # Verify Notion API was called
        notion_client = env["notion_client"]
        assert notion_client.databases.query.called
        assert notion_client.pages.create.called

        # Verify AI extraction was called
        ai_client = env["ai_client"]
        assert ai_client.messages.create.called

        # Verify cache was used
        cache_dir = Path(env["cache_dir"])
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) > 0

    def test_complex_transcript_with_relationships(self, integration_test_env, sample_transcripts):
        """Test processing transcript with multiple entities and relationships."""
        env = integration_test_env

        # Create complex transcript
        transcript = TranscriptInput(
            title="Complex Meeting with Multiple Entities",
            content="""
            Complex meeting involving multiple people and organizations.
            Sarah Johnson from TechCorp discussed Q4 planning with Mike Chen.
            They scheduled the Annual Review Meeting for December 15th.
            """,
            date=datetime.now(),
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        assert result.success is True

        # Should create multiple entities
        assert len(result.created) >= 3  # At least 2 people + 1 org

        # Check entity types
        created_types = {page.database_id for page in result.created}
        assert "test-people-db" in created_types
        assert "test-org-db" in created_types

    def test_batch_processing_integration(self, integration_test_env, sample_transcripts):
        """Test batch processing of multiple transcripts."""
        env = integration_test_env

        # Create batch of transcripts
        transcripts = []
        for i in range(3):
            transcript = TranscriptInput(
                title=f"Meeting {i}",
                content=f"Meeting {i} with John Smith from Acme Corporation.",
                date=datetime.now(),
            )
            transcripts.append(transcript)

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_batch(transcripts)

        # Verify batch results
        assert result.total_transcripts == 3
        assert result.successful == 3
        assert result.failed == 0
        assert result.success_rate == 1.0

        # Verify individual results
        assert len(result.results) == 3
        for individual_result in result.results:
            assert individual_result.success is True

    def test_error_handling_integration(self, integration_test_env):
        """Test error handling in full workflow."""
        env = integration_test_env

        # Make AI extraction fail
        env["ai_client"].messages.create.side_effect = Exception("AI Service Error")

        transcript = TranscriptInput(
            title="Test Transcript",
            content="Content that will fail AI extraction",
            date=datetime.now(),
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Should handle error gracefully
        assert result.success is False
        assert len(result.errors) > 0
        assert any(error.stage == "processing" for error in result.errors)
        assert any("AI Service Error" in error.message for error in result.errors)

    def test_cache_integration(self, integration_test_env, sample_transcripts):
        """Test caching behavior in full workflow."""
        env = integration_test_env
        transcript_data = sample_transcripts["meeting"]

        transcript = TranscriptInput(
            title=transcript_data["title"],
            content=transcript_data["content"],
            date=datetime.fromisoformat(transcript_data["date"]),
        )

        processor = TranscriptProcessor(config=env["config"])

        # First processing - should call AI
        result1 = processor.process_transcript(transcript)
        ai_call_count_1 = env["ai_client"].messages.create.call_count

        # Second processing - should use cache
        result2 = processor.process_transcript(transcript)
        ai_call_count_2 = env["ai_client"].messages.create.call_count

        # Verify cache was used (AI not called again)
        assert ai_call_count_2 == ai_call_count_1
        assert result1.success == result2.success

    def test_dry_run_integration(self, integration_test_env, sample_transcripts):
        """Test dry run mode in full workflow."""
        env = integration_test_env
        env["config"].processing.dry_run = True

        transcript = TranscriptInput(
            title="Dry Run Test",
            content="Meeting with John Smith from Acme Corporation.",
            date=datetime.now(),
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Should succeed but not create anything
        assert result.success is True
        assert len(result.created) == 0
        assert len(result.updated) == 0

        # AI should be called for extraction
        assert env["ai_client"].messages.create.called

        # Notion should NOT be called for creation
        assert not env["notion_client"].pages.create.called

    def test_rate_limiting_integration(self, rate_limit_test_config, integration_test_env):
        """Test rate limiting in full workflow."""
        env = integration_test_env
        env["config"] = rate_limit_test_config

        # Create transcript that will generate multiple entities
        transcript = TranscriptInput(
            title="Rate Limit Test",
            content="""
            Meeting with multiple people:
            - Person 1 from Company A
            - Person 2 from Company B
            - Person 3 from Company C
            - Person 4 from Company D
            - Person 5 from Company E
            """,
            date=datetime.now(),
        )

        # Track API call times
        call_times = []
        original_create = env["notion_client"].pages.create

        def tracked_create(**kwargs):
            call_times.append(time.time())
            return original_create(**kwargs)

        env["notion_client"].pages.create = tracked_create

        processor = TranscriptProcessor(config=env["config"])
        start_time = time.time()
        result = processor.process_transcript(transcript)
        end_time = time.time()

        # Should succeed
        assert result.success is True

        # Check rate limiting (2 requests per second = 0.5s between calls)
        if len(call_times) > 1:
            for i in range(1, len(call_times)):
                time_diff = call_times[i] - call_times[i - 1]
                # Allow small margin for execution time
                assert time_diff >= 0.45  # Should be ~0.5s apart


class TestDatabaseInteractions:
    """Test interactions with different Notion databases."""

    def test_all_entity_types(self, integration_test_env):
        """Test creating all supported entity types."""
        env = integration_test_env

        # Create transcript with all entity types
        transcript = TranscriptInput(
            title="All Entity Types Test",
            content="""
            Comprehensive transcript with all entity types:
            - John Doe (person) will handle the new task
            - Acme Corp (organization) is hosting the event
            - Annual Conference (event) at NYC Office (place)
            - Security Breach (transgression) discovered
            """,
            date=datetime.now(),
        )

        # Modify AI response to include all entity types
        env["ai_client"].messages.create.return_value.content[0].text = json.dumps(
            {
                "entities": [
                    {"name": "John Doe", "type": "person"},
                    {"name": "Acme Corp", "type": "organization"},
                    {"name": "Handle project", "type": "task"},
                    {"name": "Annual Conference", "type": "event"},
                    {"name": "NYC Office", "type": "place"},
                    {"name": "Security Breach", "type": "transgression"},
                ],
                "relationships": [],
            }
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        assert result.success is True

        # Verify all entity types were processed
        created_dbs = {page.database_id for page in result.created}
        expected_dbs = {
            "test-people-db",
            "test-org-db",
            "test-tasks-db",
            "test-events-db",
            "test-places-db",
            "test-transgressions-db",
        }
        assert created_dbs == expected_dbs

    def test_property_mapping(self, integration_test_env):
        """Test that properties are correctly mapped to database fields."""
        env = integration_test_env

        transcript = TranscriptInput(
            title="Property Mapping Test",
            content="John Smith (CEO) from Acme Corporation (Technology company).",
            date=datetime.now(),
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        assert result.success is True

        # Check that properties were mapped correctly
        create_calls = env["notion_client"].pages.create.call_args_list

        for call in create_calls:
            properties = call.kwargs["properties"]
            database_id = call.kwargs["parent"]["database_id"]

            if database_id == "test-people-db":
                # Check person properties mapping
                assert "Full Name" in properties
                assert properties["Full Name"]["rich_text"][0]["text"]["content"] == "John Smith"
                if "Role" in properties:
                    assert properties["Role"]["rich_text"][0]["text"]["content"] == "CEO"

            elif database_id == "test-org-db":
                # Check organization properties mapping
                assert "Name" in properties
                assert properties["Name"]["rich_text"][0]["text"]["content"] == "Acme Corporation"


class TestPerformance:
    """Test performance characteristics of the integration."""

    def test_processing_performance(
        self, integration_test_env, performance_monitor, sample_transcripts
    ):
        """Test and measure processing performance."""
        env = integration_test_env
        transcript_data = sample_transcripts["meeting"]

        transcript = TranscriptInput(
            title=transcript_data["title"],
            content=transcript_data["content"],
            date=datetime.fromisoformat(transcript_data["date"]),
        )

        # Track performance
        start_time = time.time()
        processor = TranscriptProcessor(config=env["config"])

        # Process transcript
        process_start = time.time()
        result = processor.process_transcript(transcript)
        process_end = time.time()

        performance_monitor.record_timing("total_processing", process_end - process_start)

        # Verify success
        assert result.success is True

        # Check performance
        total_time = process_end - process_start
        assert total_time < 5.0  # Should complete within 5 seconds

        # Verify result contains timing information
        assert result.processing_time > 0
        assert result.processing_time < 5.0

    def test_batch_performance(self, integration_test_env, performance_monitor):
        """Test batch processing performance."""
        env = integration_test_env

        # Create larger batch
        transcripts = []
        for i in range(10):
            transcript = TranscriptInput(
                title=f"Batch Test {i}",
                content=f"Meeting {i} content with John Smith.",
                date=datetime.now(),
            )
            transcripts.append(transcript)

        processor = TranscriptProcessor(config=env["config"])

        start_time = time.time()
        result = processor.process_batch(transcripts)
        end_time = time.time()

        performance_monitor.record_timing("batch_processing", end_time - start_time)

        # Verify all processed
        assert result.total_transcripts == 10
        assert result.successful == 10

        # Check performance
        total_time = end_time - start_time
        avg_time_per_transcript = total_time / 10

        # Should be efficient (less than 1s per transcript on average)
        assert avg_time_per_transcript < 1.0

        # Get performance summary
        summary = performance_monitor.get_summary()
        assert summary["total_time"] > 0


class TestEdgeCasesIntegration:
    """Test edge cases in the integration."""

    def test_empty_transcript(self, integration_test_env):
        """Test processing empty transcript."""
        env = integration_test_env

        transcript = TranscriptInput(title="Empty Content", content="", date=datetime.now())

        # Configure AI to return no entities
        env["ai_client"].messages.create.return_value.content[0].text = json.dumps(
            {"entities": [], "relationships": []}
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Should succeed with no entities
        assert result.success is True
        assert len(result.created) == 0
        assert len(result.errors) == 0

    def test_malformed_ai_response(self, integration_test_env):
        """Test handling malformed AI response."""
        env = integration_test_env

        # Make AI return invalid JSON
        env["ai_client"].messages.create.return_value.content[0].text = "{ invalid json"

        transcript = TranscriptInput(
            title="Malformed Response Test", content="Test content", date=datetime.now()
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Should handle error gracefully
        assert result.success is False
        assert len(result.errors) > 0

    def test_partial_database_configuration(self, integration_test_env):
        """Test with only some databases configured."""
        env = integration_test_env

        # Remove some database configurations
        env["config"].notion.databases = {
            "people": env["config"].notion.databases["people"]
            # Only people database configured
        }

        transcript = TranscriptInput(
            title="Partial Config Test",
            content="John Smith from Acme Corporation discussed the new task.",
            date=datetime.now(),
        )

        processor = TranscriptProcessor(config=env["config"])
        result = processor.process_transcript(transcript)

        # Should only create person entity
        assert result.success is True
        assert len(result.created) == 1
        assert result.created[0].database_id == "test-people-db"
