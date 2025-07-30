"""Comprehensive unit tests for CLI module."""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
from argparse import Namespace

from blackcore.minimal.cli import (
    create_parser,
    process_single_file,
    process_batch,
    setup_logging,
    load_config_with_overrides,
    main,
)
from blackcore.minimal.models import ProcessingResult, BatchResult


class TestArgumentParser:
    """Test CLI argument parser creation."""

    def test_create_parser_basic(self):
        """Test basic parser creation."""
        parser = create_parser()

        # Test with minimal args
        args = parser.parse_args(["process", "test.json"])
        assert args.command == "process"
        assert args.input == "test.json"
        assert args.config is None
        assert args.dry_run is False
        assert args.verbose is False

    def test_create_parser_with_options(self):
        """Test parser with all options."""
        parser = create_parser()

        args = parser.parse_args(
            [
                "process",
                "test.json",
                "--config",
                "config.json",
                "--dry-run",
                "--verbose",
                "--notion-api-key",
                "test-key",
                "--ai-provider",
                "openai",
                "--ai-api-key",
                "ai-key",
            ]
        )

        assert args.command == "process"
        assert args.input == "test.json"
        assert args.config == "config.json"
        assert args.dry_run is True
        assert args.verbose is True
        assert args.notion_api_key == "test-key"
        assert args.ai_provider == "openai"
        assert args.ai_api_key == "ai-key"

    def test_process_batch_command(self):
        """Test process-batch command parsing."""
        parser = create_parser()

        args = parser.parse_args(
            [
                "process-batch",
                "/path/to/dir",
                "--pattern",
                "*.txt",
                "--batch-size",
                "20",
                "--output",
                "results.json",
            ]
        )

        assert args.command == "process-batch"
        assert args.directory == "/path/to/dir"
        assert args.pattern == "*.txt"
        assert args.batch_size == 20
        assert args.output == "results.json"

    def test_validate_config_command(self):
        """Test validate-config command."""
        parser = create_parser()

        args = parser.parse_args(["validate-config", "config.json"])
        assert args.command == "validate-config"
        assert args.config_file == "config.json"

    def test_list_databases_command(self):
        """Test list-databases command."""
        parser = create_parser()

        args = parser.parse_args(["list-databases", "--config", "config.json"])
        assert args.command == "list-databases"
        assert args.config == "config.json"


class TestLoggingSetup:
    """Test logging configuration."""

    @patch("logging.basicConfig")
    def test_setup_logging_default(self, mock_logging):
        """Test default logging setup."""
        setup_logging()

        mock_logging.assert_called_once()
        call_args = mock_logging.call_args[1]
        assert call_args["level"] == 20  # INFO level
        assert "%(message)s" in call_args["format"]

    @patch("logging.basicConfig")
    def test_setup_logging_verbose(self, mock_logging):
        """Test verbose logging setup."""
        setup_logging(verbose=True)

        mock_logging.assert_called_once()
        call_args = mock_logging.call_args[1]
        assert call_args["level"] == 10  # DEBUG level
        assert "%(asctime)s" in call_args["format"]
        assert "%(levelname)s" in call_args["format"]


class TestConfigLoading:
    """Test configuration loading with CLI overrides."""

    @patch("blackcore.minimal.cli.ConfigManager")
    def test_load_config_with_overrides_minimal(self, mock_config_manager):
        """Test loading config with minimal overrides."""
        # Setup mock
        mock_config = Mock()
        mock_config_manager.load.return_value = mock_config

        # Create args
        args = Namespace(
            config=None,
            notion_api_key=None,
            ai_provider=None,
            ai_api_key=None,
            dry_run=False,
            verbose=False,
        )

        config = load_config_with_overrides(args)

        mock_config_manager.load.assert_called_once_with(config_path=None)
        assert config == mock_config

    @patch("blackcore.minimal.cli.ConfigManager")
    def test_load_config_with_all_overrides(self, mock_config_manager):
        """Test loading config with all CLI overrides."""
        # Setup mock config
        mock_config = Mock()
        mock_config.notion = Mock()
        mock_config.ai = Mock()
        mock_config.processing = Mock()
        mock_config_manager.load.return_value = mock_config

        # Create args with overrides
        args = Namespace(
            config="config.json",
            notion_api_key="cli-notion-key",
            ai_provider="openai",
            ai_api_key="cli-ai-key",
            dry_run=True,
            verbose=True,
        )

        config = load_config_with_overrides(args)

        # Verify overrides applied
        assert config.notion.api_key == "cli-notion-key"
        assert config.ai.provider == "openai"
        assert config.ai.api_key == "cli-ai-key"
        assert config.processing.dry_run is True
        assert config.processing.verbose is True


class TestProcessSingleFile:
    """Test single file processing."""

    @patch("blackcore.minimal.cli.TranscriptProcessor")
    def test_process_single_json_file(self, mock_processor_class):
        """Test processing a JSON transcript file."""
        # Create test file
        transcript_data = {
            "title": "Test Meeting",
            "content": "Meeting content",
            "date": "2025-01-10",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(transcript_data, f)
            temp_path = f.name

        try:
            # Setup mock processor
            mock_result = ProcessingResult()
            mock_result.success = True
            mock_processor = Mock()
            mock_processor.process_transcript.return_value = mock_result
            mock_processor_class.return_value = mock_processor

            # Process file
            args = Namespace(
                input=temp_path,
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_single_file(args)

            # Verify processor called correctly
            mock_processor.process_transcript.assert_called_once()
            call_args = mock_processor.process_transcript.call_args[0][0]
            assert call_args.title == "Test Meeting"
            assert call_args.content == "Meeting content"

        finally:
            os.unlink(temp_path)

    @patch("blackcore.minimal.cli.TranscriptProcessor")
    def test_process_single_text_file(self, mock_processor_class):
        """Test processing a plain text file."""
        content = "This is a meeting transcript.\nDiscussed important topics."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Setup mock
            mock_result = ProcessingResult()
            mock_result.success = True
            mock_processor = Mock()
            mock_processor.process_transcript.return_value = mock_result
            mock_processor_class.return_value = mock_processor

            args = Namespace(
                input=temp_path,
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_single_file(args)

            # Verify
            mock_processor.process_transcript.assert_called_once()
            call_args = mock_processor.process_transcript.call_args[0][0]
            assert call_args.content == content
            assert temp_path in call_args.title

        finally:
            os.unlink(temp_path)

    @patch("blackcore.minimal.cli.TranscriptProcessor")
    @patch("blackcore.minimal.cli.print")
    def test_process_single_file_with_errors(self, mock_print, mock_processor_class):
        """Test processing file with errors."""
        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"title": "Test", "content": "Content"}, f)
            temp_path = f.name

        try:
            # Setup mock with errors
            mock_result = ProcessingResult()
            mock_result.success = False
            mock_result.add_error(
                stage="processing",
                error_type="TestError",
                message="Something went wrong",
            )

            mock_processor = Mock()
            mock_processor.process_transcript.return_value = mock_result
            mock_processor_class.return_value = mock_processor

            args = Namespace(
                input=temp_path,
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_single_file(args)

            # Should print error information
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("error" in call.lower() for call in print_calls)
            assert any("TestError" in call for call in print_calls)

        finally:
            os.unlink(temp_path)

    def test_process_single_file_not_found(self):
        """Test processing non-existent file."""
        args = Namespace(
            input="/non/existent/file.json",
            config=None,
            notion_api_key=None,
            ai_provider=None,
            ai_api_key=None,
            dry_run=False,
            verbose=False,
        )

        with pytest.raises(FileNotFoundError):
            process_single_file(args)


class TestProcessBatch:
    """Test batch processing functionality."""

    @patch("blackcore.minimal.cli.TranscriptProcessor")
    def test_process_batch_json_files(self, mock_processor_class):
        """Test batch processing of JSON files."""
        # Create test directory with files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i in range(3):
                file_path = Path(temp_dir) / f"transcript_{i}.json"
                data = {"title": f"Meeting {i}", "content": f"Content {i}"}
                file_path.write_text(json.dumps(data))

            # Setup mock
            mock_batch_result = BatchResult(total_transcripts=3, successful=3, failed=0)
            mock_processor = Mock()
            mock_processor.process_batch.return_value = mock_batch_result
            mock_processor_class.return_value = mock_processor

            args = Namespace(
                directory=temp_dir,
                pattern="*.json",
                batch_size=10,
                output=None,
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_batch(args)

            # Verify
            mock_processor.process_batch.assert_called_once()
            transcripts = mock_processor.process_batch.call_args[0][0]
            assert len(transcripts) == 3

    @patch("blackcore.minimal.cli.TranscriptProcessor")
    def test_process_batch_with_pattern(self, mock_processor_class):
        """Test batch processing with file pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mixed files
            Path(temp_dir, "transcript.json").write_text(
                '{"title": "JSON", "content": ""}'
            )
            Path(temp_dir, "notes.txt").write_text("Text content")
            Path(temp_dir, "readme.md").write_text("# Readme")

            # Setup mock
            mock_batch_result = BatchResult(total_transcripts=1, successful=1, failed=0)
            mock_processor = Mock()
            mock_processor.process_batch.return_value = mock_batch_result
            mock_processor_class.return_value = mock_processor

            args = Namespace(
                directory=temp_dir,
                pattern="*.txt",
                batch_size=10,
                output=None,
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_batch(args)

            # Should only process .txt files
            transcripts = mock_processor.process_batch.call_args[0][0]
            assert len(transcripts) == 1
            assert transcripts[0].content == "Text content"

    @patch("blackcore.minimal.cli.TranscriptProcessor")
    def test_process_batch_with_output_file(self, mock_processor_class):
        """Test batch processing with output file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            Path(temp_dir, "test.json").write_text('{"title": "Test", "content": ""}')

            # Setup mock
            mock_batch_result = BatchResult(
                total_transcripts=1,
                successful=1,
                failed=0,
                results=[ProcessingResult()],
            )
            mock_processor = Mock()
            mock_processor.process_batch.return_value = mock_batch_result
            mock_processor_class.return_value = mock_processor

            output_path = Path(temp_dir) / "results.json"

            args = Namespace(
                directory=temp_dir,
                pattern="*.json",
                batch_size=10,
                output=str(output_path),
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_batch(args)

            # Verify output file created
            assert output_path.exists()
            results = json.loads(output_path.read_text())
            assert results["total_transcripts"] == 1
            assert results["successful"] == 1

    @patch("blackcore.minimal.cli.print")
    def test_process_batch_empty_directory(self, mock_print):
        """Test batch processing with no matching files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            args = Namespace(
                directory=temp_dir,
                pattern="*.json",
                batch_size=10,
                output=None,
                config=None,
                notion_api_key=None,
                ai_provider=None,
                ai_api_key=None,
                dry_run=False,
                verbose=False,
            )

            process_batch(args)

            # Should print warning about no files
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("No files found" in call for call in print_calls)


class TestMainFunction:
    """Test main CLI entry point."""

    @patch("blackcore.minimal.cli.process_single_file")
    def test_main_process_command(self, mock_process):
        """Test main with process command."""
        test_args = ["cli.py", "process", "test.json"]

        with patch("sys.argv", test_args):
            main()

        mock_process.assert_called_once()
        args = mock_process.call_args[0][0]
        assert args.command == "process"
        assert args.input == "test.json"

    @patch("blackcore.minimal.cli.process_batch")
    def test_main_process_batch_command(self, mock_batch):
        """Test main with process-batch command."""
        test_args = ["cli.py", "process-batch", "/path/to/dir"]

        with patch("sys.argv", test_args):
            main()

        mock_batch.assert_called_once()
        args = mock_batch.call_args[0][0]
        assert args.command == "process-batch"
        assert args.directory == "/path/to/dir"

    @patch("blackcore.minimal.cli.ConfigManager")
    @patch("blackcore.minimal.cli.print")
    def test_main_validate_config_command(self, mock_print, mock_config_manager):
        """Test main with validate-config command."""
        # Setup mock
        mock_config = Mock()
        mock_config_manager.load_from_file.return_value = mock_config

        test_args = ["cli.py", "validate-config", "config.json"]

        with patch("sys.argv", test_args):
            main()

        mock_config_manager.load_from_file.assert_called_once_with("config.json")
        mock_config_manager.validate_config.assert_called_once_with(mock_config)

        # Should print success message
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("valid" in call.lower() for call in print_calls)

    @patch("blackcore.minimal.cli.NotionUpdater")
    @patch("blackcore.minimal.cli.print")
    def test_main_list_databases_command(self, mock_print, mock_updater_class):
        """Test main with list-databases command."""
        # Setup mock
        mock_db_info = {
            "db-123": {"title": "People", "properties": ["Name", "Email"]},
            "db-456": {"title": "Tasks", "properties": ["Title", "Status"]},
        }
        mock_updater = Mock()
        mock_updater.list_databases.return_value = mock_db_info
        mock_updater_class.return_value = mock_updater

        test_args = ["cli.py", "list-databases"]

        with patch("sys.argv", test_args):
            with patch("blackcore.minimal.cli.load_config_with_overrides") as mock_load:
                mock_load.return_value = Mock()
                main()

        # Should print database information
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("People" in call for call in print_calls)
        assert any("Tasks" in call for call in print_calls)

    @patch("blackcore.minimal.cli.print")
    def test_main_no_arguments(self, mock_print):
        """Test main with no arguments shows help."""
        test_args = ["cli.py"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit):
                main()

    @patch("blackcore.minimal.cli.print")
    def test_main_error_handling(self, mock_print):
        """Test main handles errors gracefully."""
        test_args = ["cli.py", "process", "/non/existent/file.json"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Should exit with error code
        assert exc_info.value.code == 1

        # Should print error message
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("error" in call.lower() for call in print_calls)
