"""Tests for JSON sync functionality."""

import json
import pytest
from unittest.mock import Mock, patch

from blackcore.minimal.json_sync import JSONSyncProcessor, SyncResult


class TestJSONSyncProcessor:
    """Test suite for JSONSyncProcessor."""

    @pytest.fixture
    def mock_notion_config(self, tmp_path):
        """Create a mock notion configuration."""
        config = {
            "People & Contacts": {
                "id": "test-people-db-id",
                "local_json_path": str(tmp_path / "people.json"),
                "title_property": "Full Name",
                "relations": {},
            },
            "Organizations & Bodies": {
                "id": "test-org-db-id",
                "local_json_path": str(tmp_path / "orgs.json"),
                "title_property": "Organization Name",
                "relations": {},
            },
        }
        
        # Create the JSON files
        people_data = {
            "People & Contacts": [
                {
                    "Full Name": "John Doe",
                    "Role": "Developer",
                    "Status": "Active",
                    "Notes": "Test person",
                },
                {
                    "Full Name": "Jane Smith",
                    "Role": "Manager",
                    "Status": "Active",
                    "Notes": "Test manager",
                },
            ]
        }
        
        orgs_data = {
            "Organizations & Bodies": [
                {
                    "Organization Name": "Test Corp",
                    "Type": "Company",
                    "Status": "Active",
                }
            ]
        }
        
        with open(tmp_path / "people.json", "w") as f:
            json.dump(people_data, f)
            
        with open(tmp_path / "orgs.json", "w") as f:
            json.dump(orgs_data, f)
        
        return config, tmp_path

    @patch("blackcore.minimal.json_sync.ConfigManager")
    @patch("blackcore.minimal.json_sync.NotionUpdater")
    def test_init(self, mock_updater_class, mock_config_manager_class):
        """Test processor initialization."""
        # Setup mocks
        mock_config = Mock()
        mock_config.notion.api_key = "test-key"
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_config_manager
        
        with patch.object(JSONSyncProcessor, "_load_notion_config", return_value={}):
            processor = JSONSyncProcessor()
            
        assert processor.config == mock_config
        assert processor.dry_run is False
        assert processor.verbose is False
        mock_updater_class.assert_called_once_with("test-key")

    def test_load_json_data(self, tmp_path):
        """Test loading JSON data from files."""
        # Create test JSON file
        test_data = {"TestDB": [{"id": 1, "name": "Test"}]}
        json_path = tmp_path / "test.json"
        with open(json_path, "w") as f:
            json.dump(test_data, f)
        
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            
        # Test loading
        result = processor._load_json_data(str(json_path))
        assert result == [{"id": 1, "name": "Test"}]
        
        # Test file not found
        with pytest.raises(FileNotFoundError):
            processor._load_json_data("nonexistent.json")

    def test_prepare_properties(self):
        """Test property preparation for Notion."""
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
        
        db_config = {
            "title_property": "Name",
            "relations": {"Related People": "People & Contacts"},
        }
        
        record = {
            "Name": "Test Item",
            "Status": "Active",
            "Count": 42,
            "Is Active": True,
            "Tags": ["tag1", "tag2"],
            "Description": "Test description",
            "Related People": ["Person 1", "Person 2"],  # Relation, should be skipped
        }
        
        properties = processor._prepare_properties(record, db_config)
        
        # Check title property
        assert "Name" in properties
        assert properties["Name"]["title"][0]["text"]["content"] == "Test Item"
        
        # Check select property
        assert properties["Status"]["select"]["name"] == "Active"
        
        # Check number property
        assert properties["Count"]["number"] == 42
        
        # Check checkbox property
        assert properties["Is Active"]["checkbox"] is True
        
        # Check multi-select property
        assert len(properties["Tags"]["multi_select"]) == 2
        assert properties["Tags"]["multi_select"][0]["name"] == "tag1"
        
        # Check rich text property
        assert properties["Description"]["rich_text"][0]["text"]["content"] == "Test description"
        
        # Check that relation was skipped
        assert "Related People" not in properties

    @patch("blackcore.minimal.json_sync.NotionUpdater")
    def test_sync_database_dry_run(self, mock_updater_class, mock_notion_config):
        """Test syncing a database in dry run mode."""
        config, tmp_path = mock_notion_config
        
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            processor.notion_config = config
            processor.dry_run = True
            processor.verbose = True
            processor.notion_updater = Mock()
        
        result = processor.sync_database("People & Contacts")
        
        assert result.success is True
        assert result.created_count == 2  # Both records should be "created" in dry run
        assert result.updated_count == 0
        assert len(result.errors) == 0
        
        # In dry run, no actual API calls should be made
        processor.notion_updater.client.pages.create.assert_not_called()
        processor.notion_updater.client.pages.update.assert_not_called()

    @patch("blackcore.minimal.json_sync.NotionUpdater")
    def test_sync_database_create_pages(self, mock_updater_class, mock_notion_config):
        """Test creating new pages in Notion."""
        config, tmp_path = mock_notion_config
        
        # Setup mock Notion client
        mock_client = Mock()
        mock_client.databases.query.return_value = {"results": []}  # No existing pages
        mock_client.pages.create.return_value = {"id": "created-page-id"}
        
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            processor.notion_config = config
            processor.dry_run = False
            processor.verbose = False
            processor.notion_updater = Mock()
            processor.notion_updater.client = mock_client
        
        result = processor.sync_database("People & Contacts")
        
        assert result.success is True
        assert result.created_count == 2
        assert result.updated_count == 0
        assert len(result.created_pages) == 2
        
        # Verify create was called twice
        assert mock_client.pages.create.call_count == 2

    @patch("blackcore.minimal.json_sync.NotionUpdater")
    def test_sync_database_update_pages(self, mock_updater_class, mock_notion_config):
        """Test updating existing pages in Notion."""
        config, tmp_path = mock_notion_config
        
        # Setup mock Notion client
        mock_client = Mock()
        # Return existing pages for both queries
        mock_client.databases.query.return_value = {
            "results": [{"id": "existing-page-id"}]
        }
        mock_client.pages.update.return_value = {"id": "existing-page-id"}
        
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            processor.notion_config = config
            processor.dry_run = False
            processor.verbose = False
            processor.notion_updater = Mock()
            processor.notion_updater.client = mock_client
        
        result = processor.sync_database("People & Contacts")
        
        assert result.success is True
        assert result.created_count == 0
        assert result.updated_count == 2
        assert len(result.updated_pages) == 2
        
        # Verify update was called twice
        assert mock_client.pages.update.call_count == 2

    def test_sync_all(self, mock_notion_config):
        """Test syncing all databases."""
        config, tmp_path = mock_notion_config
        
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            processor.notion_config = config
            processor.dry_run = True
            processor.verbose = True
        
        # Mock the sync_database method
        with patch.object(processor, "sync_database") as mock_sync:
            # Setup return values for each database
            people_result = SyncResult(created_count=2, updated_count=0)
            org_result = SyncResult(created_count=1, updated_count=0)
            mock_sync.side_effect = [people_result, org_result]
            
            result = processor.sync_all()
        
        assert result.success is True
        assert result.created_count == 3  # 2 people + 1 org
        assert result.updated_count == 0
        assert mock_sync.call_count == 2

    def test_sync_database_not_found(self):
        """Test syncing a non-existent database."""
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            processor.notion_config = {}
        
        result = processor.sync_database("Non-existent DB")
        
        assert result.success is False
        assert len(result.errors) == 1
        assert "not found in configuration" in result.errors[0]

    @patch("blackcore.minimal.json_sync.NotionUpdater")
    def test_sync_database_api_error(self, mock_updater_class, mock_notion_config):
        """Test handling API errors during sync."""
        config, tmp_path = mock_notion_config
        
        # Setup mock Notion client to raise an error
        mock_client = Mock()
        mock_client.databases.query.return_value = {"results": []}
        mock_client.pages.create.side_effect = Exception("API Error")
        
        with patch.object(JSONSyncProcessor, "__init__", return_value=None):
            processor = JSONSyncProcessor.__new__(JSONSyncProcessor)
            processor.notion_config = config
            processor.dry_run = False
            processor.verbose = True
            processor.notion_updater = Mock()
            processor.notion_updater.client = mock_client
        
        result = processor.sync_database("People & Contacts")
        
        assert result.success is True  # Still succeeds, but with errors
        assert result.created_count == 0
        assert len(result.errors) == 2  # One error per failed record