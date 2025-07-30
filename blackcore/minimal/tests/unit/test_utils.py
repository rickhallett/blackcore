"""Unit tests for the utils module."""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

from blackcore.minimal.utils import (
    load_transcript_from_file,
    load_transcripts_from_directory,
    save_processing_result,
    format_entity_summary,
    validate_config_databases,
    create_sample_transcript,
    create_sample_config,
)
from blackcore.minimal.models import TranscriptInput


class TestTranscriptLoading:
    """Tests for transcript loading utilities."""

    def test_load_transcript_from_json_file(self):
        """Test loading a valid JSON transcript file."""
        data = {
            "title": "Test JSON",
            "content": "Content from JSON.",
            "date": "2025-01-10T12:00:00",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            transcript = load_transcript_from_file(temp_path)
            assert isinstance(transcript, TranscriptInput)
            assert transcript.title == "Test JSON"
            assert transcript.content == "Content from JSON."
            assert transcript.date == datetime(2025, 1, 10, 12, 0, 0)
        finally:
            os.unlink(temp_path)

    def test_load_transcript_from_text_file(self):
        """Test loading a plain text transcript file."""
        content = "This is a text transcript."
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir=".") as f:
            # Name the file with a date to test date parsing
            f.name = "2025-01-11_meeting_notes.txt"
            f.write(content)
            temp_path = f.name

        try:
            transcript = load_transcript_from_file(temp_path)
            assert isinstance(transcript, TranscriptInput)
            assert transcript.title == "2025-01-11 Meeting Notes"
            assert transcript.content == content
            assert transcript.date == datetime(2025, 1, 11)
        finally:
            os.unlink(temp_path)

    def test_load_transcript_file_not_found(self):
        """Test loading a non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_transcript_from_file("/non/existent/file.json")

    def test_load_transcript_unsupported_format(self):
        """Test loading a file with an unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            temp_path = f.name
        try:
            with pytest.raises(ValueError):
                load_transcript_from_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_transcripts_from_directory(self):
        """Test loading all transcripts from a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            Path(temp_dir, "t1.txt").write_text("Text 1")
            Path(temp_dir, "t2.json").write_text('{"title": "JSON 2", "content": "Content 2"}')
            Path(temp_dir, "t3.md").write_text("Markdown 3")
            Path(temp_dir, "ignore.dat").write_text("Ignore me")

            transcripts = load_transcripts_from_directory(temp_dir)
            assert len(transcripts) == 3
            titles = {t.title for t in transcripts}
            assert "T1" in titles
            assert "JSON 2" in titles
            assert "T3" in titles


class TestSaveProcessingResult:
    """Tests for saving processing results."""

    def test_save_processing_result(self):
        """Test saving a result dictionary to a file."""
        result = {"success": True, "created": 5, "updated": 2}
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "result.json"
            save_processing_result(result, file_path)

            assert file_path.exists()
            with open(file_path, "r") as f:
                loaded_result = json.load(f)
            assert loaded_result == result


class TestFormattingAndValidation:
    """Tests for summary formatting and config validation."""

    def test_format_entity_summary(self):
        """Test the entity summary formatting."""
        entities = [
            {"name": "John Smith", "type": "person", "confidence": 0.95},
            {"name": "Acme Corp", "type": "organization"},
        ]
        summary = format_entity_summary(entities)
        assert "PERSON (1):" in summary
        assert "ORGANIZATION (1):" in summary
        assert "John Smith (confidence: 95%)" in summary
        assert "Acme Corp" in summary

    def test_validate_config_databases(self):
        """Test the database configuration validation."""
        valid_config = {"notion": {"databases": {"people": {"id": "123"}}}}
        assert validate_config_databases(valid_config) == [
            "Database ID not configured for 'organizations'",
            "Database ID not configured for 'tasks'",
            "Database ID not configured for 'transcripts'",
            "Database ID not configured for 'transgressions'",
        ]

        missing_config = {"notion": {"databases": {}}}
        assert len(validate_config_databases(missing_config)) == 5


class TestSampleCreation:
    """Tests for sample data generation."""

    def test_create_sample_transcript(self):
        """Test the sample transcript creation."""
        transcript = create_sample_transcript()
        assert "title" in transcript
        assert "content" in transcript
        assert "date" in transcript
        assert isinstance(transcript, dict)

    def test_create_sample_config(self):
        """Test the sample config creation."""
        config = create_sample_config()
        assert "notion" in config
        assert "ai" in config
        assert "processing" in config
        assert isinstance(config, dict)