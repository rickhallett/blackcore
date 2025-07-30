"""Integration test configuration and fixtures."""

import pytest
import json
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch
import time

from blackcore.minimal.models import (
    Config,
    NotionConfig,
    AIConfig,
    ProcessingConfig,
    DatabaseConfig,
    NotionPage,
)
from blackcore.minimal.tests.utils.test_helpers import TestDataManager
from blackcore.minimal.tests.utils.mock_validators import MockBehaviorValidator


@pytest.fixture
def integration_config():
    """Create integration test configuration."""
    return Config(
        notion=NotionConfig(
            api_key="test-integration-key",
            databases={
                "people": DatabaseConfig(
                    id="test-people-db",
                    name="Test People",
                    mappings={
                        "name": "Full Name",
                        "email": "Email",
                        "role": "Role",
                        "company": "Company",
                    },
                ),
                "organizations": DatabaseConfig(
                    id="test-org-db",
                    name="Test Organizations",
                    mappings={"name": "Name", "type": "Type", "industry": "Industry"},
                ),
                "tasks": DatabaseConfig(
                    id="test-tasks-db",
                    name="Test Tasks",
                    mappings={
                        "name": "Title",
                        "status": "Status",
                        "assigned_to": "Assigned To",
                    },
                ),
                "events": DatabaseConfig(
                    id="test-events-db",
                    name="Test Events",
                    mappings={"name": "Title", "date": "Date", "location": "Location"},
                ),
                "places": DatabaseConfig(
                    id="test-places-db",
                    name="Test Places",
                    mappings={"name": "Name", "address": "Address", "type": "Type"},
                ),
                "transgressions": DatabaseConfig(
                    id="test-transgressions-db",
                    name="Test Transgressions",
                    mappings={"name": "Title", "severity": "Severity", "date": "Date"},
                ),
            },
        ),
        ai=AIConfig(
            provider="claude",
            api_key="test-ai-key",
            model="claude-3-opus-20240514",
            max_tokens=4000,
            temperature=0.3,
        ),
        processing=ProcessingConfig(
            batch_size=5, cache_ttl=3600, dry_run=False, verbose=True
        ),
        cache_dir=".test_cache",
        cache_ttl=3600,
    )


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def test_data_manager(request):
    """Provide a TestDataManager for the current test."""
    test_name = request.node.name
    with TestDataManager(test_name) as manager:
        yield manager


@pytest.fixture
def mock_notion_client():
    """Create mock Notion client for integration tests."""
    mock_client = Mock()

    # Mock database query responses
    mock_client.databases.query.return_value = {"results": [], "has_more": False}
    
    # Simplified search_database mock - returns consistent test data
    def search_database_side_effect(database_id, query, limit=10):
        """Return predictable mock NotionPage objects."""
        # Standard test data - no complex query logic
        if database_id == "test-people-db":
            return [
                NotionPage(
                    id="test-person-1",
                    database_id=database_id,
                    properties={
                        "Full Name": "John Smith",
                        "Email": "john.smith@example.com",
                        "Role": "CEO"
                    },
                    created_time=datetime(2025, 1, 1, 10, 0),
                    last_edited_time=datetime(2025, 1, 1, 10, 0),
                    url="https://notion.so/test-person-1"
                )
            ]
        elif database_id == "test-org-db":
            return [
                NotionPage(
                    id="test-org-1",
                    database_id=database_id,
                    properties={
                        "Name": "Acme Corporation",
                        "Type": "Technology",
                        "Industry": "Software"
                    },
                    created_time=datetime(2025, 1, 1, 10, 0),
                    last_edited_time=datetime(2025, 1, 1, 10, 0),
                    url="https://notion.so/test-org-1"
                )
            ]
        return []
    
    mock_client.search_database.side_effect = search_database_side_effect

    # Simplified page creation mock - deterministic IDs
    def create_page_side_effect(**kwargs):
        properties = kwargs.get("properties", {})
        database_id = kwargs.get("parent", {}).get("database_id", "unknown-db")
        
        # Generate predictable page ID based on database
        page_id = f"mock-page-{database_id.split('-')[-1]}-{len(properties)}"
        
        return {
            "id": page_id,
            "object": "page",
            "created_time": "2025-01-01T10:00:00.000Z",
            "last_edited_time": "2025-01-01T10:00:00.000Z",
            "properties": properties,
            "parent": {"database_id": database_id},
        }

    mock_client.pages.create.side_effect = create_page_side_effect

    # Mock page update - deterministic response
    mock_client.pages.update.return_value = {
        "id": "mock-updated-page",
        "object": "page",
        "last_edited_time": "2025-01-01T10:00:00.000Z",
    }

    return mock_client


@pytest.fixture
def mock_ai_responses():
    """Create predefined AI responses for different transcript types."""
    return {
        "simple": {
            "entities": [
                {
                    "name": "John Smith",
                    "type": "person",
                    "properties": {"role": "CEO", "email": "john.smith@example.com"},
                },
                {
                    "name": "Acme Corporation",
                    "type": "organization",
                    "properties": {"type": "Technology", "industry": "Software"},
                },
            ],
            "relationships": [
                {
                    "source_entity": "John Smith",
                    "source_type": "person",
                    "target_entity": "Acme Corporation",
                    "target_type": "organization",
                    "relationship_type": "works_for",
                }
            ],
        },
        "complex": {
            "entities": [
                {
                    "name": "Sarah Johnson",
                    "type": "person",
                    "properties": {"role": "VP Sales"},
                },
                {
                    "name": "Mike Chen",
                    "type": "person",
                    "properties": {"role": "Engineer"},
                },
                {
                    "name": "TechCorp",
                    "type": "organization",
                    "properties": {"type": "Startup"},
                },
                {
                    "name": "Q4 Planning",
                    "type": "task",
                    "properties": {"status": "In Progress"},
                },
                {
                    "name": "Annual Review Meeting",
                    "type": "event",
                    "properties": {"date": "2025-01-15"},
                },
            ],
            "relationships": [
                {
                    "source_entity": "Sarah Johnson",
                    "source_type": "person",
                    "target_entity": "TechCorp",
                    "target_type": "organization",
                    "relationship_type": "works_for",
                },
                {
                    "source_entity": "Mike Chen",
                    "source_type": "person",
                    "target_entity": "TechCorp",
                    "target_type": "organization",
                    "relationship_type": "works_for",
                },
            ],
        },
        "error": {
            "entities": [
                {
                    "name": "Data Breach",
                    "type": "transgression",
                    "properties": {"severity": "High", "date": "2025-01-01"},
                }
            ],
            "relationships": [],
        },
    }


@pytest.fixture
def mock_ai_client(mock_ai_responses):
    """Create mock AI client that returns predefined responses."""

    mock_client = Mock()

    def create_message_response(*args, **kwargs):
        # Always return the simple response for predictable testing
        response_data = mock_ai_responses["simple"]
        
        # Create mock response
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(response_data))]
        
        return mock_response

    mock_client.messages.create.side_effect = create_message_response

    return mock_client


@pytest.fixture
def sample_transcripts():
    """Create sample transcripts for integration testing."""
    return {
        "meeting": {
            "title": "Q4 Strategy Meeting",
            "content": """
            Meeting Notes - Q4 Strategy Session
            Date: October 15, 2025
            
            Attendees:
            - John Smith (CEO, Acme Corporation) - john.smith@example.com
            - Sarah Johnson (VP Sales)
            - Mike Chen (Senior Engineer)
            
            Discussion Points:
            1. Q4 revenue targets and planning
            2. New product launch timeline
            3. Team expansion plans
            
            Action Items:
            - Sarah to prepare sales forecast by Friday
            - Mike to complete technical feasibility study
            - Schedule follow-up meeting for next week
            
            Location: NYC Headquarters, Conference Room A
            """,
            "date": "2025-10-15",
            "metadata": {"meeting_type": "strategy", "duration": "2 hours"},
        },
        "incident": {
            "title": "Security Incident Report",
            "content": """
            CONFIDENTIAL - Security Incident Report
            Date: January 1, 2025
            
            Incident Type: Data Breach
            Severity: High
            
            Description:
            Unauthorized access detected to customer database.
            Immediate action taken to isolate affected systems.
            
            Affected Systems:
            - Customer database server
            - Backup systems
            
            Response Team:
            - Security team lead
            - IT Operations
            - Legal counsel
            
            Next Steps:
            - Complete forensic analysis
            - Notify affected customers
            - Implement additional security measures
            """,
            "date": "2025-01-01",
            "metadata": {"incident_type": "security", "severity": "high"},
        },
    }


@pytest.fixture
def validated_notion_client(mock_notion_client):
    """Validate Notion client mock behavior."""
    validator = MockBehaviorValidator()
    
    # Validate Notion client behavior
    notion_errors = validator.validate_mock_notion_client(mock_notion_client)
    if notion_errors:
        pytest.fail(f"Mock Notion client validation failed: {'; '.join(notion_errors)}")
    
    return mock_notion_client


@pytest.fixture  
def validated_ai_client(mock_ai_client):
    """Validate AI client mock behavior."""
    validator = MockBehaviorValidator()
    
    # Validate AI client behavior
    ai_errors = validator.validate_mock_ai_client(mock_ai_client)
    if ai_errors:
        pytest.fail(f"Mock AI client validation failed: {'; '.join(ai_errors)}")
    
    return mock_ai_client


@pytest.fixture
def validated_mocks(validated_notion_client, validated_ai_client):
    """Validate that mocks behave like real APIs before tests run."""
    return {
        "notion_client": validated_notion_client,
        "ai_client": validated_ai_client,
    }


@pytest.fixture
def integration_test_env(
    integration_config, temp_cache_dir, validated_mocks
):
    """Set up simplified integration test environment with validated mocks."""
    # Update cache directory in processing config
    integration_config.processing.cache_dir = temp_cache_dir

    # Patch component constructors to return our validated mocks
    with patch('blackcore.minimal.transcript_processor.AIExtractor') as mock_ai_extractor, \
         patch('blackcore.minimal.transcript_processor.NotionUpdater') as mock_notion_updater:
        
        # Configure the mock constructors to return our validated clients
        from blackcore.minimal.models import ExtractedEntities, Entity, EntityType
        
        mock_ai_instance = Mock()
        mock_ai_instance.extract_entities.return_value = ExtractedEntities(
            entities=[
                Entity(
                    name="John Smith", 
                    type=EntityType.PERSON,
                    properties={"role": "CEO", "email": "john.smith@example.com"}
                )
            ], 
            relationships=[]
        )
        mock_ai_extractor.return_value = mock_ai_instance
        
        mock_notion_instance = Mock()
        
        # Mock the actual methods called by TranscriptProcessor
        test_page = NotionPage(
            id="test-page-123", 
            database_id="test-people-db",
            properties={"Full Name": "John Smith"},
            created_time=datetime(2025, 1, 1, 10, 0),
            last_edited_time=datetime(2025, 1, 1, 10, 0),
            url="https://notion.so/test-page-123"
        )
        
        mock_notion_instance.search_database.return_value = []  # No duplicates found
        mock_notion_instance.create_page.return_value = test_page
        mock_notion_instance.update_page.return_value = test_page  
        mock_notion_instance.find_or_create_page.return_value = (test_page, True)  # Returns (page, created)
        mock_notion_updater.return_value = mock_notion_instance

        yield {
            "config": integration_config,
            "cache_dir": temp_cache_dir,
            "notion_client": validated_mocks["notion_client"],
            "ai_client": validated_mocks["ai_client"],
            "mock_ai_extractor": mock_ai_instance,
            "mock_notion_updater": mock_notion_instance,
        }


@pytest.fixture
def rate_limit_test_config(integration_config):
    """Create config for rate limit testing."""
    # Set very low rate limit for testing
    config = integration_config.model_copy()
    config.notion.rate_limit = 2  # 2 requests per second
    return config


@pytest.fixture
def performance_monitor():
    """Create performance monitoring fixture."""

    class PerformanceMonitor:
        def __init__(self):
            self.timings = []
            self.api_calls = []

        def record_timing(self, operation, duration):
            self.timings.append(
                {"operation": operation, "duration": duration, "timestamp": time.time()}
            )

        def record_api_call(self, api_type, endpoint, duration):
            self.api_calls.append(
                {
                    "api_type": api_type,
                    "endpoint": endpoint,
                    "duration": duration,
                    "timestamp": time.time(),
                }
            )

        def get_summary(self):
            total_time = sum(t["duration"] for t in self.timings)
            api_time = sum(c["duration"] for c in self.api_calls)

            return {
                "total_time": total_time,
                "api_time": api_time,
                "processing_time": total_time - api_time,
                "api_call_count": len(self.api_calls),
                "average_api_time": (
                    api_time / len(self.api_calls) if self.api_calls else 0
                ),
            }

    return PerformanceMonitor()
