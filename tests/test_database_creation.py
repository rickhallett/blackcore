"""Tests for database creation functionality."""

import pytest
from unittest.mock import Mock, patch
from blackcore.notion.client import NotionClient
from blackcore.notion.database_creator import DatabaseCreator
from blackcore.notion.schemas.all_databases import (
    get_people_contacts_schema,
    get_all_database_schemas,
    RELATION_MAPPINGS,
)
from blackcore.models.notion_properties import (
    TitleProperty,
    SelectProperty,
    SelectOption,
    RelationProperty,
)


class TestDatabaseSchemas:
    """Test database schema definitions."""

    def test_people_contacts_schema(self):
        """Test People & Contacts database schema."""
        schema = get_people_contacts_schema()

        assert schema.name == "People & Contacts"
        assert len(schema.properties) == 9

        # Check property names
        prop_names = [prop.name for prop in schema.properties]
        assert "Full Name" in prop_names
        assert "Role" in prop_names
        assert "Email" in prop_names
        assert "Organization" in prop_names

        # Check property types
        title_props = [p for p in schema.properties if isinstance(p, TitleProperty)]
        assert len(title_props) == 1
        assert title_props[0].name == "Full Name"

        # Check select options
        role_prop = next(p for p in schema.properties if p.name == "Role")
        assert isinstance(role_prop, SelectProperty)
        assert len(role_prop.options) == 5
        option_names = [opt.name for opt in role_prop.options]
        assert "Target" in option_names
        assert "Ally" in option_names

    def test_all_database_schemas(self):
        """Test that all 8 database schemas are defined."""
        schemas = get_all_database_schemas()

        assert len(schemas) == 8

        expected_names = [
            "People & Contacts",
            "Organizations & Bodies",
            "Agendas & Epics",
            "Actionable Tasks",
            "Intelligence & Transcripts",
            "Documents & Evidence",
            "Key Places & Events",
            "Identified Transgressions",
        ]

        actual_names = [schema.name for schema in schemas]
        assert actual_names == expected_names

    def test_relation_mappings(self):
        """Test relation mappings are complete."""
        schemas = get_all_database_schemas()

        for schema in schemas:
            if schema.name in RELATION_MAPPINGS:
                relations = RELATION_MAPPINGS[schema.name]

                # Get relation properties from schema
                relation_props = [p for p in schema.properties if isinstance(p, RelationProperty)]

                # Check that all relation properties have mappings
                for prop in relation_props:
                    assert prop.name in relations


class TestNotionClient:
    """Test Notion client wrapper."""

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-key"})
    def test_client_initialization(self):
        """Test client initialization with API key."""
        client = NotionClient()
        assert client.api_key == "test-key"
        assert client.client is not None

    def test_client_initialization_no_key(self):
        """Test client initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="NOTION_API_KEY not found"):
                NotionClient()

    @patch("blackcore.notion.client.Client")
    def test_create_database(self, mock_client_class):
        """Test database creation."""
        # Mock the Notion client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.create.return_value = {"id": "test-db-id", "object": "database"}

        # Create our client
        client = NotionClient(api_key="test-key")

        # Create a database
        properties = {"Name": {"title": {}}}
        result = client.create_database(
            parent_page_id="parent-id", title="Test Database", properties=properties
        )

        assert result["id"] == "test-db-id"
        assert client._database_cache["Test Database"] == "test-db-id"

        # Verify the API was called correctly
        mock_client.databases.create.assert_called_once()


class TestDatabaseCreator:
    """Test database creator functionality."""

    def test_initialization(self):
        """Test DatabaseCreator initialization."""
        mock_client = Mock(spec=NotionClient)
        creator = DatabaseCreator(mock_client, "parent-page-id")

        assert creator.client == mock_client
        assert creator.parent_page_id == "parent-page-id"
        assert creator.database_ids == {}
        assert creator.created_databases == []

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_create_database_without_relations(self, mock_sleep):
        """Test creating a database without relation properties."""
        mock_client = Mock(spec=NotionClient)
        mock_client.create_database.return_value = {"id": "test-db-id"}

        creator = DatabaseCreator(mock_client, "parent-page-id")

        # Create a simple schema
        schema = get_people_contacts_schema()
        db_id = creator._create_database_without_relations(schema)

        assert db_id == "test-db-id"

        # Verify relations were excluded
        call_args = mock_client.create_database.call_args
        properties = call_args.kwargs["properties"]

        # Check that no relation properties were included
        for prop_name in properties:
            assert prop_name not in ["Organization", "Linked Transgressions"]

    def test_check_existing_databases(self):
        """Test checking for existing databases."""
        mock_client = Mock(spec=NotionClient)
        mock_client.search_databases.side_effect = [
            [{"id": "existing-1"}],  # People & Contacts exists
            [],  # Organizations & Bodies doesn't exist
            [],  # Others don't exist
            [],
            [],
            [],
            [],
            [],
        ]

        creator = DatabaseCreator(mock_client, "parent-page-id")
        existing = creator._check_existing_databases()

        assert len(existing) == 1
        assert "People & Contacts" in existing


class TestPropertyModels:
    """Test property model conversions."""

    def test_title_property_to_notion(self):
        """Test title property conversion."""
        prop = TitleProperty(name="Test Title")
        notion_format = prop.to_notion()

        assert notion_format == {"title": {}}

    def test_select_property_to_notion(self):
        """Test select property conversion."""
        prop = SelectProperty(
            name="Status",
            options=[
                SelectOption(name="Active", color="green"),
                SelectOption(name="Inactive", color="red"),
            ],
        )
        notion_format = prop.to_notion()

        assert "select" in notion_format
        assert len(notion_format["select"]["options"]) == 2
        assert notion_format["select"]["options"][0]["name"] == "Active"
        assert notion_format["select"]["options"][0]["color"] == "green"

    def test_relation_property_without_config(self):
        """Test relation property without configuration."""
        prop = RelationProperty(name="Test Relation")
        notion_format = prop.to_notion()

        assert "relation" in notion_format
        assert notion_format["relation"]["database_id"] == "placeholder"

    def test_relation_property_with_config(self):
        """Test relation property with configuration."""
        from blackcore.models.notion_properties import RelationConfig

        config = RelationConfig(database_id="target-db-id", type="dual_property")
        prop = RelationProperty(name="Test Relation", config=config)
        notion_format = prop.to_notion()

        assert "relation" in notion_format
        assert notion_format["relation"]["database_id"] == "target-db-id"
        assert notion_format["relation"]["type"] == "dual_property"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
