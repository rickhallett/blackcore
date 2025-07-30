"""Tests for Notion updater module."""

import pytest
from unittest.mock import Mock, patch

from ..notion_updater import NotionUpdater, RateLimiter
from ..models import NotionPage


class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_second=5.0)
        assert limiter.min_interval == 0.2
        assert limiter.last_request_time == 0.0

    @patch("time.sleep")
    @patch("time.time")
    def test_rate_limiting(self, mock_time, mock_sleep):
        """Test rate limiting behavior."""
        # Mock time progression - need to account for time.time() being called twice per wait_if_needed()
        mock_time.side_effect = [
            1.0,  # First call - current_time in first wait_if_needed
            1.0,  # Second call - update last_request_time in first wait_if_needed
            1.1,  # Third call - current_time in second wait_if_needed
            1.1,  # Fourth call - update last_request_time in second wait_if_needed
        ]

        limiter = RateLimiter(requests_per_second=3.0)  # 0.333s between requests

        # First request - no wait
        limiter.wait_if_needed()
        mock_sleep.assert_not_called()

        # Second request - should wait
        limiter.wait_if_needed()
        expected_sleep = 0.333 - 0.1  # min_interval - time_elapsed
        mock_sleep.assert_called_with(pytest.approx(expected_sleep, rel=0.1))


class TestNotionUpdater:
    """Test Notion updater functionality."""

    @patch("notion_client.Client")
    def test_notion_updater_init(self, mock_client_class):
        """Test Notion updater initialization."""
        updater = NotionUpdater(api_key="test-key", rate_limit=5.0, retry_attempts=2)

        assert updater.api_key == "test-key"
        assert updater.retry_attempts == 2
        assert updater.rate_limiter.min_interval == 0.2
        mock_client_class.assert_called_once_with(auth="test-key")

    @patch("notion_client.Client")
    def test_create_page(self, mock_client_class):
        """Test creating a page."""
        # Setup mock
        mock_response = {
            "id": "page-123",
            "parent": {"database_id": "db-123"},
            "properties": {"Title": {"title": [{"text": {"content": "Test Page"}}]}},
            "created_time": "2025-01-09T12:00:00.000Z",
            "last_edited_time": "2025-01-09T12:00:00.000Z",
            "url": "https://notion.so/page-123",
        }

        mock_client = Mock()
        mock_client.pages.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key")

        # Create page
        page = updater.create_page(
            database_id="db-123", properties={"Title": "Test Page", "Status": "Active"}
        )

        assert isinstance(page, NotionPage)
        assert page.id == "page-123"
        assert page.database_id == "db-123"

        # Verify API call
        mock_client.pages.create.assert_called_once()
        call_args = mock_client.pages.create.call_args
        assert call_args[1]["parent"]["database_id"] == "db-123"

    @patch("notion_client.Client")
    def test_update_page(self, mock_client_class):
        """Test updating a page."""
        # Setup mock
        mock_response = {
            "id": "page-123",
            "parent": {"database_id": "db-123"},
            "properties": {"Status": {"select": {"name": "Completed"}}},
            "created_time": "2025-01-09T12:00:00.000Z",
            "last_edited_time": "2025-01-09T13:00:00.000Z",
        }

        mock_client = Mock()
        mock_client.pages.update.return_value = mock_response
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key")

        # Update page
        page = updater.update_page(
            page_id="page-123", properties={"Status": "Completed"}
        )

        assert page.id == "page-123"
        mock_client.pages.update.assert_called_once_with(
            page_id="page-123",
            properties={"Status": {"rich_text": [{"text": {"content": "Completed"}}]}},
        )

    @patch("notion_client.Client")
    def test_find_page(self, mock_client_class):
        """Test finding a page."""
        # Setup mock
        mock_response = {
            "results": [
                {
                    "id": "page-123",
                    "parent": {"database_id": "db-123"},
                    "properties": {
                        "Name": {"title": [{"text": {"content": "John Doe"}}]}
                    },
                    "created_time": "2025-01-09T12:00:00.000Z",
                    "last_edited_time": "2025-01-09T12:00:00.000Z",
                }
            ]
        }

        mock_client = Mock()
        mock_client.databases.query.return_value = mock_response
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key")

        # Find page
        page = updater.find_page("db-123", {"Full Name": "John Doe"})

        assert page is not None
        assert page.id == "page-123"

        # Test not found
        mock_client.databases.query.return_value = {"results": []}
        page = updater.find_page("db-123", {"Full Name": "Jane Doe"})
        assert page is None

    @patch("notion_client.Client")
    def test_find_or_create_page(self, mock_client_class):
        """Test find or create page functionality."""
        # Setup mock - page not found, then created
        mock_client = Mock()
        mock_client.databases.query.return_value = {"results": []}
        mock_client.pages.create.return_value = {
            "id": "new-page",
            "parent": {"database_id": "db-123"},
            "properties": {},
            "created_time": "2025-01-09T12:00:00.000Z",
            "last_edited_time": "2025-01-09T12:00:00.000Z",
        }
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key")

        # Should create new page
        page, created = updater.find_or_create_page(
            "db-123", {"Name": "New Person", "Role": "Tester"}, match_property="Name"
        )

        assert created is True
        assert page.id == "new-page"
        mock_client.pages.create.assert_called_once()

    @patch("notion_client.Client")
    def test_property_formatting(self, mock_client_class):
        """Test property type inference and formatting."""
        updater = NotionUpdater(api_key="test-key")

        # Test various property types
        formatted = updater._format_properties(
            {
                "Text": "Simple text",
                "Number": 42,
                "Checkbox": True,
                "Email": "test@example.com",
                "URL": "https://example.com",
                "Tags": ["Tag1", "Tag2"],
            }
        )

        assert formatted["Text"]["rich_text"][0]["text"]["content"] == "Simple text"
        assert formatted["Number"]["number"] == 42.0
        assert formatted["Checkbox"]["checkbox"] is True
        assert formatted["Email"]["email"] == "test@example.com"
        assert formatted["URL"]["url"] == "https://example.com"
        assert len(formatted["Tags"]["multi_select"]) == 2

    @patch("notion_client.Client")
    def test_retry_logic(self, mock_client_class):
        """Test retry logic for failed requests."""
        # Setup mock to fail twice then succeed
        mock_client = Mock()
        mock_client.pages.create.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            {
                "id": "page-123",
                "parent": {"database_id": "db-123"},
                "properties": {},
                "created_time": "2025-01-09T12:00:00.000Z",
                "last_edited_time": "2025-01-09T12:00:00.000Z",
            },
        ]
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key", retry_attempts=3)

        with patch("time.sleep"):  # Mock sleep to speed up test
            page = updater.create_page("db-123", {"Title": "Test"})

        assert page.id == "page-123"
        assert mock_client.pages.create.call_count == 3

    @patch("notion_client.Client")
    def test_non_retryable_errors(self, mock_client_class):
        """Test that certain errors are not retried."""
        # Setup mock
        mock_error = Exception("Unauthorized")
        mock_error.code = "unauthorized"

        mock_client = Mock()
        mock_client.pages.create.side_effect = mock_error
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key", retry_attempts=3)

        with pytest.raises(Exception, match="Unauthorized"):
            updater.create_page("db-123", {"Title": "Test"})

        # Should only be called once (no retries)
        assert mock_client.pages.create.call_count == 1

    @patch("notion_client.Client")
    def test_get_database_schema(self, mock_client_class):
        """Test getting database schema."""
        # Setup mock
        mock_response = {
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "select"},
                "Tags": {"type": "multi_select"},
                "Created": {"type": "created_time"},
            }
        }

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = mock_response
        mock_client_class.return_value = mock_client

        updater = NotionUpdater(api_key="test-key")
        schema = updater.get_database_schema("db-123")

        assert schema["Name"] == "title"
        assert schema["Status"] == "select"
        assert schema["Tags"] == "multi_select"
        assert schema["Created"] == "created_time"
