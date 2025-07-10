"""Comprehensive unit tests for utils module."""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open

from blackcore.minimal.utils import (
    load_json_file,
    save_json_file,
    format_duration,
    format_filesize,
    sanitize_filename,
    parse_date_string,
    chunk_list,
    retry_with_backoff,
    get_file_hash,
    ensure_directory_exists,
    is_valid_notion_id,
    extract_text_from_file,
    merge_dicts,
    truncate_string,
)


class TestFileOperations:
    """Test file operation utilities."""

    def test_load_json_file_success(self):
        """Test loading valid JSON file."""
        data = {"key": "value", "number": 42}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            loaded = load_json_file(temp_path)
            assert loaded == data
        finally:
            os.unlink(temp_path)

    def test_load_json_file_not_found(self):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_json_file("/non/existent/file.json")

    def test_load_json_file_invalid_json(self):
        """Test loading file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_json_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_save_json_file_success(self):
        """Test saving JSON file."""
        data = {"key": "value", "list": [1, 2, 3]}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            save_json_file(data, file_path)

            # Verify file was created and contains correct data
            assert file_path.exists()
            loaded = load_json_file(file_path)
            assert loaded == data

    def test_save_json_file_pretty_print(self):
        """Test saving JSON with pretty printing."""
        data = {"key": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            save_json_file(data, file_path, pretty=True)

            # Check file contains indented JSON
            content = file_path.read_text()
            assert "{\n" in content  # Pretty printed
            assert '"key": "value"' in content

    def test_save_json_file_creates_directory(self):
        """Test that save_json_file creates parent directories."""
        data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "nested" / "dir" / "test.json"
            save_json_file(data, file_path)

            assert file_path.exists()
            assert file_path.parent.exists()


class TestFormatting:
    """Test formatting utilities."""

    def test_format_duration(self):
        """Test duration formatting."""
        test_cases = [
            (0.5, "0.50s"),
            (1.234, "1.23s"),
            (59.99, "59.99s"),
            (60, "1m 0s"),
            (65.5, "1m 5s"),
            (3600, "1h 0m 0s"),
            (3665, "1h 1m 5s"),
            (7322.5, "2h 2m 2s"),
        ]

        for seconds, expected in test_cases:
            assert format_duration(seconds) == expected

    def test_format_filesize(self):
        """Test file size formatting."""
        test_cases = [
            (0, "0 B"),
            (100, "100 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1572864, "1.5 MB"),
            (1073741824, "1.0 GB"),
            (1610612736, "1.5 GB"),
            (1099511627776, "1.0 TB"),
        ]

        for size, expected in test_cases:
            assert format_filesize(size) == expected

    def test_truncate_string(self):
        """Test string truncation."""
        assert truncate_string("short", 10) == "short"
        assert truncate_string("this is a long string", 10) == "this is..."
        assert truncate_string("exactly10c", 10) == "exactly10c"
        assert truncate_string("", 10) == ""
        assert truncate_string("test", 0) == "..."

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file_with_spaces.txt"),
            ("file/with\\slashes.txt", "file_with_slashes.txt"),
            ("file:with*special?chars.txt", "file_with_special_chars.txt"),
            ('file|with<pipes>quotes".txt', "file_with_pipes_quotes_.txt"),
            ("   spaces   .txt", "spaces.txt"),
            ("", "unnamed"),
            ("...", "unnamed"),
            ("a" * 300, "a" * 255),  # Max length
        ]

        for input_name, expected in test_cases:
            assert sanitize_filename(input_name) == expected


class TestDateParsing:
    """Test date parsing utilities."""

    def test_parse_date_string_iso(self):
        """Test parsing ISO format dates."""
        test_cases = [
            ("2025-01-10", datetime(2025, 1, 10)),
            ("2025-01-10T14:30:00", datetime(2025, 1, 10, 14, 30, 0)),
            ("2025-01-10T14:30:00.123", datetime(2025, 1, 10, 14, 30, 0, 123000)),
            ("2025-01-10T14:30:00Z", datetime(2025, 1, 10, 14, 30, 0)),
        ]

        for date_str, expected in test_cases:
            result = parse_date_string(date_str)
            assert result.replace(tzinfo=None) == expected

    def test_parse_date_string_common_formats(self):
        """Test parsing common date formats."""
        test_cases = [
            ("01/10/2025", datetime(2025, 1, 10)),
            ("10-01-2025", datetime(2025, 1, 10)),
            ("Jan 10, 2025", datetime(2025, 1, 10)),
            ("January 10, 2025", datetime(2025, 1, 10)),
            ("10 Jan 2025", datetime(2025, 1, 10)),
        ]

        for date_str, expected in test_cases:
            result = parse_date_string(date_str)
            # Compare just the date part
            assert result.date() == expected.date()

    def test_parse_date_string_invalid(self):
        """Test parsing invalid date strings."""
        invalid_dates = ["not a date", "2025-13-45", ""]

        for date_str in invalid_dates:
            assert parse_date_string(date_str) is None


class TestListOperations:
    """Test list operation utilities."""

    def test_chunk_list(self):
        """Test list chunking."""
        # Normal case
        items = list(range(10))
        chunks = list(chunk_list(items, 3))
        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]

        # Empty list
        assert list(chunk_list([], 5)) == []

        # Chunk size larger than list
        assert list(chunk_list([1, 2, 3], 10)) == [[1, 2, 3]]

        # Chunk size of 1
        chunks = list(chunk_list([1, 2, 3], 1))
        assert chunks == [[1], [2], [3]]

    def test_merge_dicts(self):
        """Test dictionary merging."""
        # Basic merge
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = merge_dicts(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}

        # Nested merge
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 20, "z": 30}, "c": 4}
        result = merge_dicts(dict1, dict2)
        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3, "c": 4}

        # Empty dicts
        assert merge_dicts({}, {"a": 1}) == {"a": 1}
        assert merge_dicts({"a": 1}, {}) == {"a": 1}
        assert merge_dicts({}, {}) == {}


class TestRetryLogic:
    """Test retry with backoff functionality."""

    def test_retry_success_first_try(self):
        """Test function that succeeds on first try."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test function that succeeds after some failures."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, backoff_factor=0.1)
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_successful()
        assert result == "success"
        assert call_count == 3

    def test_retry_all_attempts_fail(self):
        """Test function that fails all attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, backoff_factor=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Attempt {call_count}")

        with pytest.raises(ValueError) as exc_info:
            always_fails()

        assert "Attempt 3" in str(exc_info.value)
        assert call_count == 3

    def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, exceptions=(ValueError,))
        def raises_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable")
            else:
                raise TypeError("Not retryable")

        with pytest.raises(TypeError):
            raises_different_errors()

        # Should stop after TypeError (not retryable)
        assert call_count == 2


class TestValidation:
    """Test validation utilities."""

    def test_is_valid_notion_id(self):
        """Test Notion ID validation."""
        # Valid IDs (32 char hex without dashes)
        valid_ids = [
            "a" * 32,
            "0123456789abcdef0123456789abcdef",
            "ABCDEF1234567890abcdef1234567890",
        ]

        for notion_id in valid_ids:
            assert is_valid_notion_id(notion_id) is True

        # Valid IDs with dashes (UUID format)
        valid_uuid_ids = [
            "12345678-1234-1234-1234-123456789012",
            "abcdef12-3456-7890-abcd-ef1234567890",
        ]

        for notion_id in valid_uuid_ids:
            assert is_valid_notion_id(notion_id) is True

        # Invalid IDs
        invalid_ids = [
            "",
            "too-short",
            "a" * 31,  # Too short
            "a" * 33,  # Too long
            "not-a-valid-id",
            "12345678-1234-1234-1234",  # Incomplete UUID
            "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",  # Invalid chars
        ]

        for notion_id in invalid_ids:
            assert is_valid_notion_id(notion_id) is False


class TestFileHashing:
    """Test file hashing functionality."""

    def test_get_file_hash(self):
        """Test file hash calculation."""
        content = b"Test content for hashing"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Default SHA256
            hash1 = get_file_hash(temp_path)
            assert len(hash1) == 64  # SHA256 hex length

            # Same content should give same hash
            hash2 = get_file_hash(temp_path)
            assert hash1 == hash2

            # Different algorithm
            md5_hash = get_file_hash(temp_path, algorithm="md5")
            assert len(md5_hash) == 32  # MD5 hex length
            assert md5_hash != hash1
        finally:
            os.unlink(temp_path)

    def test_get_file_hash_not_found(self):
        """Test hashing non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_file_hash("/non/existent/file")


class TestDirectoryOperations:
    """Test directory operation utilities."""

    def test_ensure_directory_exists(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test creating new directory
            new_dir = Path(temp_dir) / "new" / "nested" / "dir"
            ensure_directory_exists(new_dir)
            assert new_dir.exists()
            assert new_dir.is_dir()

            # Test with existing directory (should not fail)
            ensure_directory_exists(new_dir)
            assert new_dir.exists()

    def test_ensure_directory_exists_with_file(self):
        """Test ensure_directory_exists with file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file
            file_path = Path(temp_dir) / "test.txt"
            file_path.write_text("test")

            # Should raise error if path is a file
            with pytest.raises(NotADirectoryError):
                ensure_directory_exists(file_path)


class TestTextExtraction:
    """Test text extraction from files."""

    def test_extract_text_from_txt_file(self):
        """Test extracting text from plain text file."""
        content = "This is a test file.\nWith multiple lines."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            extracted = extract_text_from_file(temp_path)
            assert extracted == content
        finally:
            os.unlink(temp_path)

    def test_extract_text_from_json_file(self):
        """Test extracting text from JSON file."""
        data = {
            "title": "Test Document",
            "content": "This is the content",
            "metadata": {"author": "Test Author"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            extracted = extract_text_from_file(temp_path)
            # Should convert JSON to readable text
            assert "Test Document" in extracted
            assert "This is the content" in extracted
            assert "Test Author" in extracted
        finally:
            os.unlink(temp_path)

    def test_extract_text_unsupported_format(self):
        """Test extracting text from unsupported file format."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"Binary content")
            temp_path = f.name

        try:
            extracted = extract_text_from_file(temp_path)
            # Should return empty string or raise appropriate error
            assert extracted == "" or "Unsupported" in extracted
        finally:
            os.unlink(temp_path)
