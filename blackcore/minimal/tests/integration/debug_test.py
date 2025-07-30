"""Debug test to find TypeError issue."""

import sys
import traceback
from datetime import datetime
from unittest.mock import Mock, patch
import json

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import (
    TranscriptInput,
    Config,
    NotionConfig,
    AIConfig,
    ProcessingConfig,
    DatabaseConfig,
    NotionPage,
)


def test_debug():
    """Debug the TypeError issue."""
    # Create config
    config = Config(
        notion=NotionConfig(
            api_key="test-key",
            databases={
                "people": DatabaseConfig(
                    id="test-people-db",
                    name="Test People",
                    mappings={"name": "Full Name", "email": "Email"},
                ),
            },
        ),
        ai=AIConfig(
            provider="claude",
            api_key="test-ai-key",
            model="claude-3-opus-20240514",
        ),
        processing=ProcessingConfig(
            cache_dir=".test_cache",
            verbose=True,
        ),
    )
    
    # Create mock notion client
    mock_notion_client = Mock()
    
    # Mock search_database to return NotionPage objects
    def search_database_side_effect(database_id, query, limit=10):
        print(f"search_database called with: database_id={database_id}, query={query}, limit={limit}")
        if "john" in query.lower():
            page = NotionPage(
                id="existing-john",
                database_id=database_id,
                properties={
                    "Full Name": "John Smith",
                    "Email": "john.smith@example.com",
                },
                created_time=datetime.utcnow(),
                last_edited_time=datetime.utcnow(),
            )
            return [page]
        return []
    
    mock_notion_client.search_database.side_effect = search_database_side_effect
    mock_notion_client.databases.query.return_value = {"results": [], "has_more": False}
    mock_notion_client.pages.create.return_value = {
        "id": "new-page",
        "object": "page",
        "created_time": datetime.utcnow().isoformat(),
        "last_edited_time": datetime.utcnow().isoformat(),
        "properties": {},
        "parent": {"database_id": "test-people-db"},
    }
    
    # Create mock AI client
    mock_ai_client = Mock()
    
    def create_message_response(*args, **kwargs):
        print(f"AI create called with args: {args}, kwargs: {kwargs}")
        # Create response
        response_data = {
            "entities": [
                {
                    "name": "John Smith",
                    "type": "person",
                    "properties": {"role": "CEO"},
                }
            ],
            "relationships": [],
        }
        
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(response_data))]
        return mock_response
    
    mock_ai_client.messages.create.side_effect = create_message_response
    
    # Create transcript
    transcript = TranscriptInput(
        title="Test Transcript",
        content="Meeting with John Smith from Acme Corporation.",
        date=datetime.now(),
    )
    
    # Patch and process
    with patch("notion_client.Client", return_value=mock_notion_client), \
         patch("anthropic.Anthropic", return_value=mock_ai_client):
        
        try:
            processor = TranscriptProcessor(config=config)
            result = processor.process_transcript(transcript)
            print(f"Success: {result.success}")
            print(f"Created: {len(result.created)}")
            print(f"Updated: {len(result.updated)}")
            print(f"Errors: {result.errors}")
        except Exception as e:
            print(f"Exception occurred: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    test_debug()