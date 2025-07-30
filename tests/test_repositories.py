"""Unit tests for repository pattern."""

import pytest
from unittest.mock import Mock

from blackcore.repositories import (
    PageRepository,
    DatabaseRepository,
    SearchRepository,
    RepositoryError,
)
from blackcore.models.responses import NotionPage, NotionDatabase


class TestPageRepository:
    """Test page repository functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Notion client."""
        client = Mock()
        client.pages = Mock()
        return client

    @pytest.fixture
    def page_repo(self, mock_client):
        """Create page repository with mocked dependencies."""
        return PageRepository(client=mock_client)

    def test_get_by_id_success(self, page_repo, mock_client):
        """Test successful page retrieval."""
        # Mock response
        mock_page_data = {
            "object": "page",
            "id": "test-page-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "parent": {"type": "database_id", "database_id": "db-1"},
            "properties": {},
            "url": "https://notion.so/test-page",
        }
        mock_client.pages.retrieve.return_value = mock_page_data

        # Test retrieval
        page = page_repo.get_by_id("test-page-id")

        assert isinstance(page, NotionPage)
        assert page.id == "test-page-id"
        mock_client.pages.retrieve.assert_called_once_with(page_id="test-page-id")

    def test_get_by_id_not_found(self, page_repo, mock_client):
        """Test page not found error."""
        mock_client.pages.retrieve.side_effect = Exception("Page not found")

        with pytest.raises(RepositoryError) as exc_info:
            page_repo.get_by_id("non-existent-id")

        assert "Failed to get page" in str(exc_info.value)

    def test_create_page(self, page_repo, mock_client):
        """Test page creation."""
        # Input data
        page_data = {
            "parent": {"type": "database_id", "database_id": "db-1"},
            "properties": {"Name": "Test Page", "Status": "Active"},
        }

        # Mock response
        mock_created = {
            "object": "page",
            "id": "new-page-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "parent": page_data["parent"],
            "properties": {},
            "url": "https://notion.so/new-page",
        }
        mock_client.pages.create.return_value = mock_created

        # Test creation
        page = page_repo.create(page_data)

        assert isinstance(page, NotionPage)
        assert page.id == "new-page-id"

        # Verify API call
        call_args = mock_client.pages.create.call_args
        assert "parent" in call_args[1]
        assert "properties" in call_args[1]

    def test_create_page_missing_parent(self, page_repo):
        """Test page creation without parent."""
        with pytest.raises(RepositoryError) as exc_info:
            page_repo.create({"properties": {}})

        assert "Page must have parent" in str(exc_info.value)

    def test_update_page(self, page_repo, mock_client):
        """Test page update."""
        # Mock response
        mock_updated = {
            "object": "page",
            "id": "test-page-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-02T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "parent": {"type": "database_id", "database_id": "db-1"},
            "properties": {},
            "url": "https://notion.so/test-page",
        }
        mock_client.pages.update.return_value = mock_updated

        # Test update
        update_data = {"properties": {"Status": "Completed"}, "archived": False}

        page = page_repo.update("test-page-id", update_data)

        assert isinstance(page, NotionPage)
        assert page.last_edited_time > page.created_time

        # Verify API call
        mock_client.pages.update.assert_called_once()
        call_args = mock_client.pages.update.call_args
        assert call_args[1]["page_id"] == "test-page-id"
        assert "properties" in call_args[1]

    def test_delete_page(self, page_repo, mock_client):
        """Test page deletion (archiving)."""
        # Mock update response for archiving
        mock_archived = {
            "object": "page",
            "id": "test-page-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-02T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "parent": {"type": "database_id", "database_id": "db-1"},
            "properties": {},
            "url": "https://notion.so/test-page",
            "archived": True,
        }
        mock_client.pages.update.return_value = mock_archived

        # Test deletion
        result = page_repo.delete("test-page-id")

        assert result is True

        # Verify archive call
        mock_client.pages.update.assert_called_once()
        call_args = mock_client.pages.update.call_args
        assert call_args[1]["archived"] is True

    def test_batch_operations(self, page_repo, mock_client):
        """Test batch operations."""
        # Mock responses
        mock_pages = [
            {
                "object": "page",
                "id": f"page-{i}",
                "created_time": "2024-01-01T00:00:00.000Z",
                "last_edited_time": "2024-01-01T00:00:00.000Z",
                "created_by": {"object": "user", "id": "user-1"},
                "last_edited_by": {"object": "user", "id": "user-1"},
                "parent": {"type": "database_id", "database_id": "db-1"},
                "properties": {},
                "url": f"https://notion.so/page-{i}",
            }
            for i in range(3)
        ]

        mock_client.pages.retrieve.side_effect = mock_pages

        # Test batch get
        pages = page_repo.batch_get(["page-0", "page-1", "page-2"])

        assert len(pages) == 3
        assert all(isinstance(p, NotionPage) for p in pages)
        assert mock_client.pages.retrieve.call_count == 3


class TestDatabaseRepository:
    """Test database repository functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Notion client."""
        client = Mock()
        client.databases = Mock()
        return client

    @pytest.fixture
    def db_repo(self, mock_client):
        """Create database repository with mocked dependencies."""
        return DatabaseRepository(client=mock_client)

    def test_get_by_id_success(self, db_repo, mock_client):
        """Test successful database retrieval."""
        # Mock response
        mock_db_data = {
            "object": "database",
            "id": "test-db-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "title": [{"type": "text", "text": {"content": "Test Database"}}],
            "properties": {
                "Name": {"id": "title", "type": "title", "title": {}},
                "Status": {"id": "status", "type": "select", "select": {"options": []}},
            },
            "parent": {"type": "page_id", "page_id": "parent-page"},
            "url": "https://notion.so/test-db",
        }
        mock_client.databases.retrieve.return_value = mock_db_data

        # Test retrieval
        database = db_repo.get_by_id("test-db-id")

        assert isinstance(database, NotionDatabase)
        assert database.id == "test-db-id"
        assert len(database.title) == 1
        assert database.title[0].text["content"] == "Test Database"

    def test_create_database(self, db_repo, mock_client):
        """Test database creation."""
        # Input data
        db_data = {
            "parent": {"type": "page_id", "page_id": "parent-page"},
            "title": "New Database",
            "properties": {
                "Name": {"type": "title", "title": {}},
                "Status": {"type": "select", "select": {"options": []}},
            },
        }

        # Mock response
        mock_created = {
            "object": "database",
            "id": "new-db-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "title": [{"type": "text", "text": {"content": "New Database"}}],
            "properties": db_data["properties"],
            "parent": db_data["parent"],
            "url": "https://notion.so/new-db",
        }
        mock_client.databases.create.return_value = mock_created

        # Test creation
        database = db_repo.create(db_data)

        assert isinstance(database, NotionDatabase)
        assert database.id == "new-db-id"

    def test_query_database(self, db_repo, mock_client):
        """Test database querying."""
        # Mock query response
        mock_response = {
            "object": "list",
            "results": [
                {
                    "object": "page",
                    "id": f"page-{i}",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "created_by": {"object": "user", "id": "user-1"},
                    "last_edited_by": {"object": "user", "id": "user-1"},
                    "parent": {"type": "database_id", "database_id": "test-db"},
                    "properties": {},
                    "url": f"https://notion.so/page-{i}",
                }
                for i in range(5)
            ],
            "has_more": False,
            "next_cursor": None,
        }
        mock_client.databases.query.return_value = mock_response

        # Test query
        pages = db_repo.query("test-db-id")

        assert len(pages) == 5
        assert all(isinstance(p, NotionPage) for p in pages)

    def test_add_property(self, db_repo, mock_client):
        """Test adding property to database."""
        # Mock existing database
        mock_db = {
            "object": "database",
            "id": "test-db-id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "created_by": {"object": "user", "id": "user-1"},
            "last_edited_by": {"object": "user", "id": "user-1"},
            "title": [{"type": "text", "text": {"content": "Test Database"}}],
            "properties": {"Name": {"id": "title", "type": "title", "title": {}}},
            "parent": {"type": "page_id", "page_id": "parent-page"},
            "url": "https://notion.so/test-db",
        }
        mock_client.databases.retrieve.return_value = mock_db

        # Mock update response
        mock_updated = mock_db.copy()
        mock_updated["properties"]["Status"] = {
            "type": "select",
            "select": {"options": []},
        }
        mock_client.databases.update.return_value = mock_updated

        # Test adding property
        new_property = {"type": "select", "select": {"options": []}}
        database = db_repo.add_property("test-db-id", "Status", new_property)

        assert "Status" in database.properties

        # Verify update call
        update_call = mock_client.databases.update.call_args
        assert "Status" in update_call[1]["properties"]


class TestSearchRepository:
    """Test search repository functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Notion client."""
        client = Mock()
        client.search = Mock()
        return client

    @pytest.fixture
    def search_repo(self, mock_client):
        """Create search repository with mocked dependencies."""
        return SearchRepository(client=mock_client)

    def test_search_all(self, search_repo, mock_client):
        """Test searching for all content."""
        # Mock response
        mock_response = {
            "object": "list",
            "results": [
                {
                    "object": "page",
                    "id": "page-1",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "created_by": {"object": "user", "id": "user-1"},
                    "last_edited_by": {"object": "user", "id": "user-1"},
                    "parent": {"type": "page_id", "page_id": "parent"},
                    "properties": {},
                    "url": "https://notion.so/page-1",
                },
                {
                    "object": "database",
                    "id": "db-1",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "created_by": {"object": "user", "id": "user-1"},
                    "last_edited_by": {"object": "user", "id": "user-1"},
                    "title": [{"type": "text", "text": {"content": "Database"}}],
                    "properties": {},
                    "parent": {"type": "page_id", "page_id": "parent"},
                    "url": "https://notion.so/db-1",
                },
            ],
            "has_more": False,
            "next_cursor": None,
        }
        mock_client.search.return_value = mock_response

        # Test search
        results = search_repo.search("test query")

        assert len(results) == 2
        assert isinstance(results[0], NotionPage)
        assert isinstance(results[1], NotionDatabase)

    def test_search_pages_only(self, search_repo, mock_client):
        """Test searching for pages only."""
        # Mock response with mixed results
        mock_response = {
            "object": "list",
            "results": [
                {
                    "object": "page",
                    "id": "page-1",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "created_by": {"object": "user", "id": "user-1"},
                    "last_edited_by": {"object": "user", "id": "user-1"},
                    "parent": {"type": "page_id", "page_id": "parent"},
                    "properties": {},
                    "url": "https://notion.so/page-1",
                },
                {
                    "object": "database",
                    "id": "db-1",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "created_by": {"object": "user", "id": "user-1"},
                    "last_edited_by": {"object": "user", "id": "user-1"},
                    "title": [{"type": "text", "text": {"content": "Database"}}],
                    "properties": {},
                    "parent": {"type": "page_id", "page_id": "parent"},
                    "url": "https://notion.so/db-1",
                },
            ],
            "has_more": False,
            "next_cursor": None,
        }
        mock_client.search.return_value = mock_response

        # Test search pages only
        pages = search_repo.search_pages("test query")

        assert len(pages) == 1
        assert all(isinstance(p, NotionPage) for p in pages)

        # Verify filter was applied
        search_call = mock_client.search.call_args
        assert search_call[1]["filter"]["value"] == "page"

    def test_unsupported_operations(self, search_repo):
        """Test that unsupported operations raise errors."""
        with pytest.raises(NotImplementedError):
            search_repo.get_by_id("any-id")

        with pytest.raises(NotImplementedError):
            search_repo.create({})

        with pytest.raises(NotImplementedError):
            search_repo.update("any-id", {})

        with pytest.raises(NotImplementedError):
            search_repo.delete("any-id")
