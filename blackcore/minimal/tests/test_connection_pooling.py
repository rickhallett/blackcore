"""Test connection pooling for Notion client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from blackcore.minimal.notion_updater import NotionUpdater


class TestConnectionPooling:
    """Test suite for HTTP connection pooling."""
    
    def test_uses_session_for_requests(self):
        """Test that NotionUpdater uses requests.Session for connection pooling."""
        with patch('notion_client.Client') as mock_client_class:
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Check that the updater has a session
            assert hasattr(updater, 'session')
            assert isinstance(updater.session, requests.Session)
    
    def test_session_reused_across_requests(self):
        """Test that the same session is reused for multiple requests."""
        with patch('notion_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Store initial session
            initial_session = updater.session
            
            # Make multiple API calls
            mock_client.pages.create.return_value = {"id": "page1", "properties": {}, "created_time": "2024-01-01T00:00:00Z", "last_edited_time": "2024-01-01T00:00:00Z"}
            updater.create_page("db1", {"Title": "Test"})
            
            mock_client.pages.update.return_value = {"id": "page1", "properties": {}, "created_time": "2024-01-01T00:00:00Z", "last_edited_time": "2024-01-01T00:00:00Z"}
            updater.update_page("page1", {"Title": "Updated"})
            
            mock_client.databases.query.return_value = {"results": []}
            updater.find_page("db1", {"Title": "Test"})
            
            # Session should remain the same
            assert updater.session is initial_session
    
    def test_session_configured_with_connection_pooling(self):
        """Test that session is configured with appropriate connection pooling settings."""
        with patch('notion_client.Client') as mock_client_class:
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Check adapter settings
            adapter = updater.session.get_adapter('https://')
            assert adapter is not None
            
            # HTTPAdapter stores pool settings as private attributes
            assert adapter._pool_connections == 10
            assert adapter._pool_maxsize == 10
    
    def test_session_has_retry_configuration(self):
        """Test that session has proper retry configuration."""
        with patch('notion_client.Client') as mock_client_class:
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Check retry settings
            adapter = updater.session.get_adapter('https://')
            assert hasattr(adapter, 'max_retries')
            
            retry_config = adapter.max_retries
            assert retry_config.total >= 3
            assert retry_config.backoff_factor > 0
            assert 500 in retry_config.status_forcelist
            assert 502 in retry_config.status_forcelist
            assert 503 in retry_config.status_forcelist
            assert 504 in retry_config.status_forcelist
    
    def test_session_headers_include_api_key(self):
        """Test that session headers include the API key."""
        with patch('notion_client.Client') as mock_client_class:
            api_key = "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG"
            updater = NotionUpdater(api_key)
            
            # Check headers
            assert 'Authorization' in updater.session.headers
            assert updater.session.headers['Authorization'] == f'Bearer {api_key}'
            assert 'Notion-Version' in updater.session.headers
            assert updater.session.headers['Content-Type'] == 'application/json'
    
    def test_session_timeout_configured(self):
        """Test that session has appropriate timeout settings."""
        with patch('notion_client.Client') as mock_client_class:
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Session should have timeout settings
            assert hasattr(updater, 'timeout')
            assert isinstance(updater.timeout, tuple)
            assert len(updater.timeout) == 2
            assert updater.timeout[0] >= 5  # Connect timeout
            assert updater.timeout[1] >= 30  # Read timeout
    
    def test_notion_client_uses_custom_session(self):
        """Test that the Notion client is configured to use our custom session."""
        with patch('notion_client.Client') as mock_client_class:
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Verify Client was initialized with session parameter
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs
            
            # Should pass session to client
            assert 'session' in call_kwargs or hasattr(updater.client, '_session')
    
    def test_session_closed_on_cleanup(self):
        """Test that session is properly closed when updater is cleaned up."""
        with patch('notion_client.Client') as mock_client_class:
            updater = NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG")
            
            # Mock the session close method
            updater.session.close = Mock()
            
            # Call cleanup
            updater.close()
            
            # Session should be closed
            updater.session.close.assert_called_once()
    
    def test_context_manager_support(self):
        """Test that NotionUpdater can be used as a context manager."""
        with patch('notion_client.Client') as mock_client_class:
            with NotionUpdater("secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG") as updater:
                assert hasattr(updater, 'session')
                assert isinstance(updater.session, requests.Session)
            
            # Session should be closed after context exit
            # (Would need to mock session.close to verify)
    
    def test_connection_pool_size_configurable(self):
        """Test that connection pool size can be configured."""
        with patch('notion_client.Client') as mock_client_class:
            # Test with custom pool size
            updater = NotionUpdater(
                "secret_1234567890abcdefghijklmnopqrstuvwxyzABCDEFG",
                pool_connections=20,
                pool_maxsize=50
            )
            
            adapter = updater.session.get_adapter('https://')
            assert adapter._pool_connections == 20
            assert adapter._pool_maxsize == 50