"""Unit tests for Notion sync functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
import json
from pathlib import Path

from blackcore.notion.client import NotionClient, RateLimiter
from scripts.notion_sync import SyncEngine


class TestPagination:
    """Test pagination handling in NotionClient."""

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    @patch("blackcore.notion.client.Client")
    def test_pagination_single_page(self, mock_client_class, mock_notion_client):
        """Test pagination when results fit in a single page."""
        # Set up the mock client instance
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock response with no more pages
        mock_response = {
            "results": [{"id": f"page-{i}"} for i in range(5)],
            "has_more": False,
            "next_cursor": None,
        }
        mock_client_instance.databases.query.return_value = mock_response

        # Create client
        client = NotionClient()

        # Test pagination
        pages = client.get_all_database_pages("test-db-id")

        assert len(pages) == 5
        assert pages[0]["id"] == "page-0"
        assert mock_client_instance.databases.query.call_count == 1

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    def test_pagination_multiple_pages(self, mock_notion_client):
        """Test pagination when results span multiple pages."""
        # Mock paginated responses
        responses = [
            {
                "results": [{"id": f"page-{i}"} for i in range(100)],
                "has_more": True,
                "next_cursor": "cursor-1",
            },
            {
                "results": [{"id": f"page-{i}"} for i in range(100, 200)],
                "has_more": True,
                "next_cursor": "cursor-2",
            },
            {
                "results": [{"id": f"page-{i}"} for i in range(200, 250)],
                "has_more": False,
                "next_cursor": None,
            },
        ]
        mock_notion_client.databases.query.side_effect = responses

        # Create client with mocked underlying client
        client = NotionClient()
        client.client = mock_notion_client

        # Test pagination
        pages = client.get_all_database_pages("test-db-id")

        assert len(pages) == 250
        assert pages[0]["id"] == "page-0"
        assert pages[249]["id"] == "page-249"
        assert mock_notion_client.databases.query.call_count == 3

        # Verify cursors were used correctly
        calls = mock_notion_client.databases.query.call_args_list
        assert calls[0][1]["start_cursor"] is None
        assert calls[1][1]["start_cursor"] == "cursor-1"
        assert calls[2][1]["start_cursor"] == "cursor-2"

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    def test_pagination_empty_results(self, mock_notion_client):
        """Test pagination with no results."""
        mock_response = {"results": [], "has_more": False, "next_cursor": None}
        mock_notion_client.databases.query.return_value = mock_response

        # Create client with mocked underlying client
        client = NotionClient()
        client.client = mock_notion_client

        # Test pagination
        pages = client.get_all_database_pages("test-db-id")

        assert len(pages) == 0
        assert mock_notion_client.databases.query.call_count == 1


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(requests_per_second=3)
        assert limiter.min_interval == pytest.approx(1.0 / 3, rel=0.01)
        assert limiter.last_request_time == 0.0

    def test_rate_limiter_wait_behavior(self):
        """Test that rate limiter enforces delays between requests."""
        limiter = RateLimiter(requests_per_second=10)  # 100ms between requests

        # First request should not wait
        start_time = time.time()
        limiter.wait_if_needed()
        first_wait = time.time() - start_time
        assert first_wait < 0.01  # Should be instant

        # Second request immediately after should wait
        start_time = time.time()
        limiter.wait_if_needed()
        second_wait = time.time() - start_time
        assert second_wait >= 0.09  # Should wait ~100ms

    def test_rate_limiter_no_wait_after_interval(self):
        """Test that rate limiter doesn't wait if enough time has passed."""
        limiter = RateLimiter(requests_per_second=10)  # 100ms between requests

        # First request
        limiter.wait_if_needed()

        # Wait longer than the minimum interval
        time.sleep(0.2)

        # Next request should not wait
        start_time = time.time()
        limiter.wait_if_needed()
        wait_time = time.time() - start_time
        assert wait_time < 0.01  # Should be instant

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    @patch("time.sleep")
    def test_api_methods_use_rate_limiting(self, mock_sleep, mock_notion_client):
        """Test that API methods apply rate limiting."""
        # Create client
        client = NotionClient()
        client.client = mock_notion_client

        # Mock successful responses
        mock_notion_client.databases.retrieve.return_value = {"id": "test-db"}
        mock_notion_client.search.return_value = {"results": []}
        mock_notion_client.pages.create.return_value = {"id": "new-page"}

        # Make several API calls in quick succession
        client.get_database_schema("test-db-id")
        client.discover_databases()
        client.create_page("test-db-id", {})

        # Rate limiter should have caused waits
        # First call: no wait, second and third calls: wait
        assert mock_sleep.call_count >= 2


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    @patch("time.sleep")
    @patch("blackcore.notion.client.Client")
    def test_retry_on_rate_limit_error(self, mock_client_class, mock_sleep, mock_notion_client):
        """Test that rate limit errors trigger retries."""
        from notion_client.errors import APIResponseError

        # Create a rate limit error with proper response structure
        # APIResponseError needs response, message, and code
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"code": "rate_limited", "message": "Rate limited"}
        rate_limit_error = APIResponseError(mock_response, "Rate limited", "rate_limited")

        # Set up the mock client instance
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock: fail twice, then succeed
        mock_client_instance.databases.retrieve.side_effect = [
            rate_limit_error,
            rate_limit_error,
            {"id": "test-db", "properties": {}},
        ]

        # Create client
        client = NotionClient()

        # Should succeed after retries
        result = client.get_database_schema("test-db-id")
        assert result["id"] == "test-db"

        # Should have retried twice
        assert mock_client_instance.databases.retrieve.call_count == 3
        assert mock_sleep.call_count >= 2  # At least 2 retries

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    @patch("blackcore.notion.client.Client")
    def test_no_retry_on_invalid_request(self, mock_client_class, mock_notion_client):
        """Test that invalid request errors don't trigger retries."""
        from notion_client.errors import APIResponseError

        # Create an invalid request error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": "invalid_request", "message": "Invalid request"}
        invalid_error = APIResponseError(mock_response, "Invalid request", "invalid_request")

        # Set up the mock client instance
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.databases.retrieve.side_effect = invalid_error

        # Create client
        client = NotionClient()

        # Should fail immediately without retries
        with pytest.raises(APIResponseError) as exc_info:
            client.get_database_schema("test-db-id")

        assert exc_info.value.code == "invalid_request"
        assert mock_client_instance.databases.retrieve.call_count == 1  # No retries

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    @patch("time.sleep")
    @patch("blackcore.notion.client.Client")
    def test_exponential_backoff(self, mock_client_class, mock_sleep, mock_notion_client):
        """Test that retry delays increase exponentially."""
        from notion_client.errors import APIResponseError

        # Create a rate limit error
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"code": "rate_limited", "message": "Rate limited"}
        rate_limit_error = APIResponseError(mock_response, "Rate limited", "rate_limited")

        # Set up the mock client instance
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock: fail all attempts
        mock_client_instance.databases.retrieve.side_effect = rate_limit_error

        # Create client
        client = NotionClient()

        # Should fail after max retries
        with pytest.raises(APIResponseError):
            client.get_database_schema("test-db-id")

        # Check that sleep was called with increasing delays
        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) >= 2

        # Delays should increase (with some jitter)
        delays = [call[0][0] for call in sleep_calls]
        assert all(
            delays[i] < delays[i + 1] * 3 for i in range(len(delays) - 1)
        )  # Allow for jitter


class TestSyncEngine:
    """Test SyncEngine functionality."""

    @patch("blackcore.notion.client.NotionClient")
    def test_sync_engine_initialization(self, mock_client_class):
        """Test SyncEngine initialization."""
        mock_client = Mock()
        config = {
            "id": "test-db-id",
            "title_property": "Name",
            "local_json_path": "test.json",
            "json_data_key": "Test Data",
            "relations": {},
        }

        engine = SyncEngine("Test Database", config, mock_client)

        assert engine.db_name == "Test Database"
        assert engine.config == config
        assert engine.notion == mock_client
        assert engine.title_prop == "Name"

    @patch("blackcore.notion.client.NotionClient")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_prepare_relation_lookups(self, mock_open, mock_exists, mock_client_class):
        """Test relation lookup preparation."""
        # Mock cache file existence
        mock_exists.return_value = True

        # Mock cached data
        cached_data = [
            {"Full Name": "John Doe", "notion_page_id": "john-id"},
            {"Full Name": "Jane Smith", "notion_page_id": "jane-id"},
        ]
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(cached_data)

        # Mock config loading
        with patch("scripts.notion_sync.load_config_from_file") as mock_load_config:
            mock_load_config.return_value = {"People & Contacts": {"title_property": "Full Name"}}

            config = {
                "id": "test-db-id",
                "title_property": "Name",
                "relations": {"Assignee": "People & Contacts"},
            }

            engine = SyncEngine("Test Database", config, Mock())
            lookups = engine._prepare_relation_lookups()

            assert "Assignee" in lookups
            assert lookups["Assignee"]["target_db"] == "People & Contacts"
            assert lookups["Assignee"]["id_map"]["John Doe"] == "john-id"
            assert lookups["Assignee"]["id_map"]["Jane Smith"] == "jane-id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
