"""Integration test configuration and fixtures."""

import pytest
import json
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch
import time

from blackcore.minimal.config import (
    Config,
    NotionConfig,
    AIConfig,
    ProcessingConfig,
    DatabaseConfig,
)


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
def mock_notion_client():
    """Create mock Notion client for integration tests."""
    mock_client = Mock()

    # Mock database query responses
    mock_client.databases.query.return_value = {"results": [], "has_more": False}

    # Mock page creation
    def create_page_side_effect(**kwargs):
        properties = kwargs.get("properties", {})
        title = "Unknown"
        if "Full Name" in properties:
            title = properties["Full Name"]["rich_text"][0]["text"]["content"]
        elif "Name" in properties:
            title = properties["Name"]["rich_text"][0]["text"]["content"]
        elif "Title" in properties:
            title = properties["Title"]["rich_text"][0]["text"]["content"]

        return {
            "id": f"page-{hash(title) % 10000}",
            "object": "page",
            "created_time": datetime.utcnow().isoformat(),
            "last_edited_time": datetime.utcnow().isoformat(),
            "properties": properties,
        }

    mock_client.pages.create.side_effect = create_page_side_effect

    # Mock page update
    mock_client.pages.update.return_value = {
        "id": "updated-page",
        "object": "page",
        "last_edited_time": datetime.utcnow().isoformat(),
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
                    "properties": {"date": "2025-12-15"},
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

    def create_message_response(messages, **kwargs):
        # Extract the text from the user message
        user_message = messages[-1]["content"]

        # Determine which response to return based on content
        if "error" in user_message.lower() or "breach" in user_message.lower():
            response_key = "error"
        elif "complex" in user_message.lower() or "multiple" in user_message.lower():
            response_key = "complex"
        else:
            response_key = "simple"

        response_data = mock_ai_responses[response_key]

        # Create mock response
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(response_data))]

        return mock_response

    mock_client = Mock()
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
def integration_test_env(
    integration_config, temp_cache_dir, mock_notion_client, mock_ai_client
):
    """Set up complete integration test environment."""
    # Update cache directory in config
    integration_config.cache_dir = temp_cache_dir

    # Create patches
    notion_patch = patch("notion_client.Client", return_value=mock_notion_client)
    claude_patch = patch("anthropic.Anthropic", return_value=mock_ai_client)
    openai_patch = patch("openai.OpenAI", return_value=mock_ai_client)

    # Start patches
    notion_patch.start()
    claude_patch.start()
    openai_patch.start()

    yield {
        "config": integration_config,
        "cache_dir": temp_cache_dir,
        "notion_client": mock_notion_client,
        "ai_client": mock_ai_client,
    }

    # Stop patches
    notion_patch.stop()
    claude_patch.stop()
    openai_patch.stop()


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
