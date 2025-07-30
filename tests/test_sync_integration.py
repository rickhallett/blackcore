"""Integration tests for Notion sync scenarios."""

import pytest
from unittest.mock import Mock, patch, mock_open
import json

from blackcore.notion.client import NotionClient
from scripts.sync.notion_sync import SyncEngine


class TestFullSyncScenarios:
    """Test complete sync scenarios from JSON to Notion."""

    @patch("blackcore.notion.client.NotionClient")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_initial_sync_empty_to_populated(
        self, mock_file, mock_exists, mock_client_class
    ):
        """Test syncing fresh data to an empty Notion database."""
        # Setup
        mock_exists.return_value = True
        mock_client = Mock()

        # Mock empty Notion database
        mock_client.get_all_database_pages.return_value = []
        mock_client.get_database_schema.return_value = {
            "id": "test-db-id",
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "select"},
                "Priority": {"type": "number"},
            },
        }

        # Mock local JSON data
        local_data = {
            "Test Database": [
                {"Name": "Item 1", "Status": "Active", "Priority": 1},
                {"Name": "Item 2", "Status": "Pending", "Priority": 2},
                {"Name": "Item 3", "Status": "Complete", "Priority": 3},
            ]
        }
        mock_file.return_value.read.return_value = json.dumps(local_data)

        # Mock successful page creation
        mock_client.create_page.return_value = {"id": "new-page-id"}
        mock_client.build_payload_properties = NotionClient.build_payload_properties
        mock_client.simplify_page_properties = NotionClient.simplify_page_properties

        # Configure engine
        config = {
            "id": "test-db-id",
            "title_property": "Name",
            "local_json_path": "test_data.json",
            "json_data_key": "Test Database",
            "relations": {},
        }

        # Run sync
        engine = SyncEngine("Test Database", config, mock_client)

        # Fetch and cache
        engine.fetch_and_cache_db()

        # Plan sync
        plan = engine.plan_sync()

        # Verify plan
        assert len(plan) == 3
        assert all(p["action"] == "CREATE" for p in plan)

        # Execute plan (live mode)
        engine.execute_plan(plan, is_live=True)

        # Verify all items were created
        assert mock_client.create_page.call_count == 3

    @patch("blackcore.notion.client.NotionClient")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_incremental_sync_with_existing_data(
        self, mock_file, mock_exists, mock_client_class
    ):
        """Test syncing when some data already exists in Notion."""
        # Setup
        mock_exists.return_value = True
        mock_client = Mock()

        # Mock Notion database with existing pages
        existing_pages = [
            {
                "id": "page-1",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Item 1"}]}
                },
            },
            {
                "id": "page-2",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Item 2"}]}
                },
            },
        ]
        mock_client.get_all_database_pages.return_value = existing_pages
        mock_client.simplify_page_properties.side_effect = [
            {"notion_page_id": "page-1", "Name": "Item 1"},
            {"notion_page_id": "page-2", "Name": "Item 2"},
        ]

        # Mock local JSON data with new and existing items
        local_data = {
            "Test Database": [
                {"Name": "Item 1", "Status": "Active"},  # Exists
                {"Name": "Item 2", "Status": "Pending"},  # Exists
                {"Name": "Item 3", "Status": "New"},  # New
                {"Name": "Item 4", "Status": "New"},  # New
            ]
        }

        # Set up file reads
        mock_file.return_value.read.side_effect = [
            json.dumps(
                [
                    {"notion_page_id": "page-1", "Name": "Item 1"},
                    {"notion_page_id": "page-2", "Name": "Item 2"},
                ]
            ),  # Cache read
            json.dumps(local_data),  # Local data read
        ]

        # Configure engine
        config = {
            "id": "test-db-id",
            "title_property": "Name",
            "local_json_path": "test_data.json",
            "json_data_key": "Test Database",
            "relations": {},
        }

        # Run sync
        engine = SyncEngine("Test Database", config, mock_client)

        # Plan sync
        plan = engine.plan_sync()

        # Verify plan
        create_actions = [p for p in plan if p["action"] == "CREATE"]
        skip_actions = [p for p in plan if p["action"] == "SKIP"]

        assert len(create_actions) == 2  # Only new items
        assert len(skip_actions) == 2  # Existing items
        assert create_actions[0]["data"]["Name"] == "Item 3"
        assert create_actions[1]["data"]["Name"] == "Item 4"

    @patch("blackcore.notion.client.NotionClient")
    @patch("scripts.sync.notion_sync.load_config_from_file")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_sync_with_relations(
        self, mock_file, mock_exists, mock_load_config, mock_client_class
    ):
        """Test syncing data with cross-database relations."""
        # Setup
        mock_exists.return_value = True
        mock_client = Mock()

        # Mock config for relation lookups
        mock_load_config.return_value = {
            "People & Contacts": {"title_property": "Full Name"},
            "Organizations & Bodies": {"title_property": "Organization Name"},
        }

        # Mock cache files for related databases
        people_cache = [
            {"Full Name": "John Doe", "notion_page_id": "john-id"},
            {"Full Name": "Jane Smith", "notion_page_id": "jane-id"},
        ]
        orgs_cache = [
            {"Organization Name": "Acme Corp", "notion_page_id": "acme-id"},
            {"Organization Name": "Tech Inc", "notion_page_id": "tech-id"},
        ]

        # Mock database schema with relations
        mock_client.get_database_schema.return_value = {
            "id": "test-db-id",
            "properties": {
                "Task Name": {"type": "title"},
                "Assignee": {"type": "relation"},
                "Organization": {"type": "relation"},
            },
        }

        # Mock empty Notion database
        mock_client.get_all_database_pages.return_value = []

        # Local data with relations
        local_data = {
            "Actionable Tasks": [
                {
                    "Task Name": "Task 1",
                    "Assignee": ["John Doe"],
                    "Organization": ["Acme Corp"],
                },
                {
                    "Task Name": "Task 2",
                    "Assignee": ["Jane Smith"],
                    "Organization": ["Tech Inc"],
                },
            ]
        }

        # Set up file reads
        read_counter = 0

        def mock_read():
            nonlocal read_counter
            read_counter += 1
            if read_counter == 1:
                return json.dumps([])  # Empty cache
            elif read_counter == 2:
                return json.dumps(people_cache)  # People cache
            elif read_counter == 3:
                return json.dumps(orgs_cache)  # Orgs cache
            elif read_counter == 4:
                return json.dumps(local_data)  # Local data
            elif read_counter == 5:
                return json.dumps([])  # Re-read empty cache for plan

        mock_file.return_value.read.side_effect = mock_read

        # Mock build_payload_properties to capture calls
        payload_calls = []

        def capture_payload(*args, **kwargs):
            payload_calls.append(args)
            return {
                "Task Name": {"title": [{"text": {"content": args[1]["Task Name"]}}]}
            }

        mock_client.build_payload_properties.side_effect = capture_payload
        mock_client.simplify_page_properties = NotionClient.simplify_page_properties

        # Configure engine
        config = {
            "id": "test-db-id",
            "title_property": "Task Name",
            "local_json_path": "test_data.json",
            "json_data_key": "Actionable Tasks",
            "relations": {
                "Assignee": "People & Contacts",
                "Organization": "Organizations & Bodies",
            },
        }

        # Run sync
        engine = SyncEngine("Actionable Tasks", config, mock_client)
        engine.fetch_and_cache_db()
        plan = engine.plan_sync()
        engine.execute_plan(plan, is_live=True)

        # Verify relations were resolved
        assert len(payload_calls) == 2

        # Check that relation lookups were passed correctly
        relation_lookups = payload_calls[0][2]  # Third argument is relation_lookups
        assert "Assignee" in relation_lookups
        assert relation_lookups["Assignee"]["id_map"]["John Doe"] == "john-id"
        assert "Organization" in relation_lookups
        assert relation_lookups["Organization"]["id_map"]["Acme Corp"] == "acme-id"

    def test_sync_error_recovery(self):
        """Test sync behavior when errors occur during execution."""
        from notion_client.errors import APIResponseError

        mock_client = Mock()

        # Mock database schema
        mock_client.get_database_schema.return_value = {
            "id": "test-db-id",
            "properties": {"Name": {"type": "title"}},
        }

        # Mock empty database
        mock_client.get_all_database_pages.return_value = []

        # Mock page creation that fails on second item
        create_results = [
            {"id": "page-1"},  # Success
            APIResponseError(code="validation_error", message="Invalid data"),  # Fail
            {"id": "page-3"},  # Would succeed but won't be reached
        ]
        mock_client.create_page.side_effect = create_results

        # Configure engine
        config = {
            "id": "test-db-id",
            "title_property": "Name",
            "local_json_path": "test_data.json",
            "json_data_key": "Test Data",
            "relations": {},
        }

        # Create plan with 3 items
        plan = [
            {"action": "CREATE", "data": {"Name": "Item 1"}},
            {"action": "CREATE", "data": {"Name": "Item 2"}},
            {"action": "CREATE", "data": {"Name": "Item 3"}},
        ]

        engine = SyncEngine("Test Database", config, mock_client)

        # Execute should continue despite error
        engine.execute_plan(plan, is_live=True)

        # Verify first item succeeded, second failed, third wasn't attempted
        assert mock_client.create_page.call_count == 2

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_data_integrity_validation(self, mock_file, mock_exists, mock_mkdir):
        """Test that synced data maintains integrity."""
        # Setup
        mock_exists.return_value = True
        mock_client = Mock()

        # Complex test data with all property types
        test_data = {
            "Test Database": [
                {
                    "Name": "Complex Item",
                    "Description": "Test description with unicode: 🚀",
                    "Status": "Active",
                    "Tags": ["Tag1", "Tag2", "Tag3"],
                    "Priority": 42,
                    "Is Active": True,
                    "Due Date": "2025-07-15",
                    "Date Range": {"start": "2025-07-15", "end": "2025-07-20"},
                    "Website": "https://example.com",
                    "Email": "test@example.com",
                    "Phone": "+1234567890",
                    "Long Text": "x" * 3000,  # Should be truncated
                    "Related Items": ["Item A", "Item B"],
                }
            ]
        }

        # Mock database schema
        schema = {
            "id": "test-db-id",
            "properties": {
                "Name": {"type": "title"},
                "Description": {"type": "rich_text"},
                "Status": {"type": "select"},
                "Tags": {"type": "multi_select"},
                "Priority": {"type": "number"},
                "Is Active": {"type": "checkbox"},
                "Due Date": {"type": "date"},
                "Date Range": {"type": "date"},
                "Website": {"type": "url"},
                "Email": {"type": "email"},
                "Phone": {"type": "phone_number"},
                "Long Text": {"type": "rich_text"},
                "Related Items": {"type": "relation"},
            },
        }

        mock_client.get_database_schema.return_value = schema
        mock_client.get_all_database_pages.return_value = []
        mock_client.simplify_page_properties = NotionClient.simplify_page_properties

        # Capture the payload sent to create_page
        created_payload = None

        def capture_create(db_id, properties):
            nonlocal created_payload
            created_payload = properties
            return {"id": "new-page-id"}

        mock_client.create_page.side_effect = capture_create
        mock_client.build_payload_properties = NotionClient.build_payload_properties

        # Mock file reads
        mock_file.return_value.read.side_effect = [
            json.dumps([]),  # Empty cache
            json.dumps(test_data),  # Local data
            json.dumps([]),  # Re-read for plan
        ]

        # Configure and run sync
        config = {
            "id": "test-db-id",
            "title_property": "Name",
            "local_json_path": "test_data.json",
            "json_data_key": "Test Database",
            "relations": {"Related Items": "Items Database"},
        }

        engine = SyncEngine("Test Database", config, mock_client)
        engine.fetch_and_cache_db()
        plan = engine.plan_sync()
        engine.execute_plan(plan, is_live=True)

        # Verify data integrity
        assert created_payload is not None

        # Check text truncation
        assert (
            len(created_payload["Long Text"]["rich_text"][0]["text"]["content"]) == 2000
        )

        # Check all property types maintained correctly
        assert created_payload["Name"]["title"][0]["text"]["content"] == "Complex Item"
        assert created_payload["Priority"]["number"] == 42
        assert created_payload["Is Active"]["checkbox"] is True
        assert created_payload["Tags"]["multi_select"] == [
            {"name": "Tag1"},
            {"name": "Tag2"},
            {"name": "Tag3"},
        ]
        assert created_payload["Due Date"]["date"]["start"] == "2025-07-15"
        assert created_payload["Website"]["url"] == "https://example.com"


class TestPerformanceScenarios:
    """Test performance-related scenarios."""

    @patch("blackcore.notion.client.NotionClient")
    def test_large_dataset_sync(self, mock_client_class, test_data_generator):
        """Test syncing a large dataset efficiently."""
        # Generate large test dataset
        people_data = test_data_generator["generate_people"](1000)

        # Mock client
        mock_client = Mock()
        mock_client.get_all_database_pages.return_value = []
        mock_client.get_database_schema.return_value = {
            "id": "people-db-id",
            "properties": {
                "Full Name": {"type": "title"},
                "Role": {"type": "select"},
                "Email": {"type": "email"},
                "Priority": {"type": "number"},
            },
        }

        # Track memory usage
        created_count = 0

        def count_creates(*args, **kwargs):
            nonlocal created_count
            created_count += 1
            return {"id": f"page-{created_count}"}

        mock_client.create_page.side_effect = count_creates
        mock_client.build_payload_properties = NotionClient.build_payload_properties
        mock_client.simplify_page_properties = NotionClient.simplify_page_properties

        # Configure engine
        config = {
            "id": "people-db-id",
            "title_property": "Full Name",
            "local_json_path": "test_data.json",
            "json_data_key": "People & Contacts",
            "relations": {},
        }

        # Create plan (without executing to test memory efficiency)
        plan = []
        for person in people_data:
            plan.append({"action": "CREATE", "data": person})

        engine = SyncEngine("People & Contacts", config, mock_client)

        # Execute in batches to simulate memory-efficient processing
        batch_size = 100
        for i in range(0, len(plan), batch_size):
            batch = plan[i : i + batch_size]
            engine.execute_plan(batch, is_live=True)

        # Verify all items were created
        assert created_count == 1000

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limit_compliance_under_load(self, mock_sleep, mock_time):
        """Test that rate limiting is maintained during heavy sync operations."""
        # Mock time to control rate limit testing
        current_time = [0.0]

        def get_time():
            return current_time[0]

        def sleep_time(duration):
            current_time[0] += duration

        mock_time.side_effect = get_time
        mock_sleep.side_effect = sleep_time

        # Create client with rate limiter
        from blackcore.notion.client import RateLimiter

        limiter = RateLimiter(requests_per_second=3)

        # Track request times
        request_times = []

        # Make 10 rapid requests
        for i in range(10):
            limiter.wait_if_needed()
            request_times.append(current_time[0])

        # Verify rate limiting
        # First request should be immediate
        assert request_times[0] == 0.0

        # Subsequent requests should be spaced ~333ms apart
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i - 1]
            assert time_diff >= 0.33  # Allow small tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
