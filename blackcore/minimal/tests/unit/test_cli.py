"""Unit tests for the CLI module."""

import pytest
from unittest.mock import patch, Mock
import sys

# Import the main function from the module where the CLI logic is now located.
# The file is blackcore/minimal/cli.py and the function is main.
from blackcore.minimal.cli import main


@patch("blackcore.minimal.cli.process_single_transcript")
def test_cli_process_single_transcript(mock_process_single):
    """Test the CLI 'process' command."""
    test_argv = ["cli.py", "process", "transcript.txt", "--dry-run", "-v"]
    with patch.object(sys, "argv", test_argv):
        main()
    mock_process_single.assert_called_once()
    args = mock_process_single.call_args[0][0]
    assert args.command == "process"
    assert args.transcript == "transcript.txt"
    assert args.dry_run is True
    assert args.verbose is True


@patch("blackcore.minimal.cli.process_batch")
def test_cli_process_batch(mock_process_batch):
    """Test the CLI 'process-batch' command."""
    test_argv = ["cli.py", "process-batch", "./transcripts", "--batch-size", "5"]
    with patch.object(sys, "argv", test_argv):
        main()
    mock_process_batch.assert_called_once()
    args = mock_process_batch.call_args[0][0]
    assert args.command == "process-batch"
    assert args.directory == "./transcripts"
    assert args.batch_size == 5


@patch("blackcore.minimal.cli.generate_config")
def test_cli_generate_config(mock_generate_config):
    """Test the CLI 'generate-config' command."""
    test_argv = ["cli.py", "generate-config", "-o", "config.json"]
    with patch.object(sys, "argv", test_argv):
        main()
    mock_generate_config.assert_called_once()
    args = mock_generate_config.call_args[0][0]
    assert args.command == "generate-config"
    assert args.output == "config.json"


@patch("blackcore.minimal.cli.generate_sample")
def test_cli_generate_sample(mock_generate_sample):
    """Test the CLI 'generate-sample' command."""
    test_argv = ["cli.py", "generate-sample"]
    with patch.object(sys, "argv", test_argv):
        main()
    mock_generate_sample.assert_called_once()


@patch("blackcore.minimal.cli.cache_info")
def test_cli_cache_info(mock_cache_info):
    """Test the CLI 'cache-info' command."""
    test_argv = ["cli.py", "cache-info", "--cleanup", "--clear"]
    with patch.object(sys, "argv", test_argv):
        main()
    mock_cache_info.assert_called_once()
    args = mock_cache_info.call_args[0][0]
    assert args.command == "cache-info"
    assert args.cleanup is True
    assert args.clear is True


@patch("blackcore.minimal.cli.sync_json")
def test_cli_sync_json(mock_sync_json):
    """Test the CLI 'sync-json' command."""
    test_argv = ["cli.py", "sync-json", "-d", "people"]
    with patch.object(sys, "argv", test_argv):
        main()
    mock_sync_json.assert_called_once()
    args = mock_sync_json.call_args[0][0]
    assert args.command == "sync-json"
    assert args.database == "people"


@patch("argparse.ArgumentParser.print_help")
def test_cli_no_command(mock_print_help):
    """Test that running the CLI with no command prints help."""
    test_argv = ["cli.py"]
    with patch.object(sys, "argv", test_argv):
        # The main function should call parser.print_help() and return 1
        assert main() == 1
    mock_print_help.assert_called_once()


@patch("builtins.print")
def test_cli_error_handling(mock_print):
    """Test the main error handling wrapper."""
    test_argv = ["cli.py", "process", "nonexistent.file"]
    # Mock the downstream function to raise an error
    with patch("blackcore.minimal.cli.process_single_transcript", side_effect=FileNotFoundError("File not found")):
        with patch.object(sys, "argv", test_argv):
            return_code = main()

    assert return_code == 1
    # Check that a user-friendly error message was printed
    error_message_found = False
    for call in mock_print.call_args_list:
        if "error" in str(call.args[0]).lower() and "file not found" in str(call.args[0]).lower():
            error_message_found = True
            break
    assert error_message_found, "Expected error message was not printed"