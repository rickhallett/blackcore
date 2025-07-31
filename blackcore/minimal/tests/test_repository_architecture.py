"""Test the new repository architecture."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from blackcore.minimal.repositories import BaseRepository, PageRepository, DatabaseRepository
from blackcore.minimal.services import TranscriptService
from blackcore.minimal.notion_updater_v2 import NotionUpdaterV2


class TestRepositoryArchitecture:
    """Test repository pattern implementation."""

    def test_base_repository_abstract(self):
        """Test that BaseRepository is abstract."""
        with pytest.raises(TypeError):
            BaseRepository(Mock(), Mock())

    @patch.object(PageRepository, '_make_api_call')
    def test_page_repository_create(self, mock_api_call):
        """Test page repository create operation."""
        # Mock response
        mock_response = {
            "id": "test-page-id",
            "properties": {"Name": {"title": [{"text": {"content": "Test"}}]}}
        }
        mock_api_call.return_value = mock_response
        
        # Create repository
        repo = PageRepository(Mock())

        # Test create
        result = repo.create({
            "parent": {"database_id": "test-db"},
            "properties": {"Name": {"title": [{"text": {"content": "Test"}}]}}
        })

        assert result["id"] == "test-page-id"
        mock_api_call.assert_called_once_with(
            "pages.create",
            parent={"database_id": "test-db"},
            properties={"Name": {"title": [{"text": {"content": "Test"}}]}}
        )

    @patch.object(DatabaseRepository, 'get_by_id')
    def test_database_repository_get_schema(self, mock_get_by_id):
        """Test database repository schema retrieval."""
        # Mock response
        mock_response = {
            "id": "test-db-id",
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "select", "select": {"options": []}}
            }
        }
        mock_get_by_id.return_value = mock_response

        # Create repository
        repo = DatabaseRepository(Mock())

        # Test get schema
        schema = repo.get_schema("test-db-id")

        assert "Name" in schema
        assert schema["Name"]["type"] == "title"
        assert "Status" in schema
        mock_get_by_id.assert_called_once_with("test-db-id")

    def test_transcript_service_find_title_property(self):
        """Test service can find title property."""
        # Create service with mocked repos
        service = TranscriptService(Mock(), Mock())

        # Test schema
        schema = {
            "Name": {"type": "title"},
            "Status": {"type": "select"},
            "Description": {"type": "rich_text"}
        }

        title_prop = service._find_title_property(schema)
        assert title_prop == "Name"

    def test_notion_updater_v2_initialization(self):
        """Test NotionUpdaterV2 initializes correctly."""
        # Mock notion_client module
        mock_client_class = Mock()
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Patch the import
        import sys
        mock_module = Mock()
        mock_module.Client = mock_client_class
        sys.modules['notion_client'] = mock_module

        try:
            # Create updater
            updater = NotionUpdaterV2("test-api-key")

            # Verify initialization
            assert updater.page_repo is not None
            assert updater.db_repo is not None
            assert updater.transcript_service is not None
            assert hasattr(updater, 'create_page')
            assert hasattr(updater, 'update_page')
            assert hasattr(updater, 'find_page_by_title')

            # Verify client was created with API key
            mock_client_class.assert_called_once_with(auth="test-api-key")

        finally:
            # Clean up
            del sys.modules['notion_client']

    @patch.object(PageRepository, 'create')
    def test_batch_operations(self, mock_create):
        """Test batch operations in repository."""
        # Mock create to return different pages
        mock_create.side_effect = [
            {"id": f"page-{i}"} for i in range(3)
        ]

        # Create repository
        repo = PageRepository(Mock())

        # Test batch create
        items = [
            {"parent": {"database_id": "test-db"}, "properties": {}}
            for _ in range(3)
        ]
        results = repo.batch_create(items)

        assert len(results) == 3
        assert all(r["id"].startswith("page-") for r in results)
        assert mock_create.call_count == 3