"""Tests for AI extractor module."""

import pytest
from unittest.mock import Mock, patch
import json

from ..ai_extractor import AIExtractor, ClaudeProvider, OpenAIProvider
from ..models import ExtractedEntities, EntityType


class TestClaudeProvider:
    """Test Claude AI provider."""

    @patch("anthropic.Anthropic")
    def test_claude_provider_init(self, mock_anthropic):
        """Test Claude provider initialization."""
        provider = ClaudeProvider(api_key="test-key", model="claude-3")

        mock_anthropic.assert_called_once_with(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model == "claude-3"

    @patch("anthropic.Anthropic")
    def test_extract_entities_success(self, mock_anthropic):
        """Test successful entity extraction with Claude."""
        # Mock response
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    {
                        "entities": [
                            {
                                "name": "John Doe",
                                "type": "person",
                                "properties": {"role": "Mayor"},
                                "context": "Mayor of the town",
                                "confidence": 0.95,
                            }
                        ],
                        "relationships": [
                            {
                                "source_entity": "John Doe",
                                "source_type": "person",
                                "target_entity": "Town Council",
                                "target_type": "organization",
                                "relationship_type": "works_for",
                            }
                        ],
                        "summary": "Meeting about survey",
                        "key_points": ["Survey concerns raised"],
                    }
                )
            )
        ]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        provider = ClaudeProvider(api_key="test-key")
        result = provider.extract_entities("Test transcript", "Extract entities")

        assert len(result.entities) == 1
        assert result.entities[0].name == "John Doe"
        assert result.entities[0].type == EntityType.PERSON
        assert len(result.relationships) == 1
        assert result.summary == "Meeting about survey"

    @patch("anthropic.Anthropic")
    def test_parse_response_with_markdown(self, mock_anthropic):
        """Test parsing response with markdown code blocks."""
        provider = ClaudeProvider(api_key="test-key")

        response = """Here's the extracted data:
        
```json
{
    "entities": [{"name": "Test", "type": "person"}],
    "relationships": [],
    "summary": "Test summary"
}
```
        
Done!"""

        result = provider._parse_response(response)
        assert len(result.entities) == 1
        assert result.entities[0].name == "Test"

    @patch("anthropic.Anthropic")
    def test_fallback_parse(self, mock_anthropic):
        """Test fallback parsing when JSON fails."""
        provider = ClaudeProvider(api_key="test-key")

        response = "This mentions John Doe and Jane Smith in the meeting."

        result = provider._fallback_parse(response)
        assert len(result.entities) == 2
        assert any(e.name == "John Doe" for e in result.entities)
        assert any(e.name == "Jane Smith" for e in result.entities)
        assert all(e.confidence == 0.5 for e in result.entities)


class TestOpenAIProvider:
    """Test OpenAI provider."""

    @patch("openai.OpenAI")
    def test_openai_provider_init(self, mock_openai):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        mock_openai.assert_called_once_with(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4"

    @patch("openai.OpenAI")
    def test_extract_entities_success(self, mock_openai):
        """Test successful entity extraction with OpenAI."""
        # Mock response
        mock_message = Mock()
        mock_message.content = json.dumps(
            {
                "entities": [
                    {
                        "name": "Review Task",
                        "type": "task",
                        "properties": {"status": "pending"},
                        "confidence": 1.0,
                    }
                ],
                "relationships": [],
                "summary": "Task identified",
                "key_points": [],
            }
        )

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        result = provider.extract_entities("Test transcript", "Extract entities")

        assert len(result.entities) == 1
        assert result.entities[0].name == "Review Task"
        assert result.entities[0].type == EntityType.TASK


class TestAIExtractor:
    """Test main AI extractor class."""

    @patch("anthropic.Anthropic")
    def test_extractor_with_claude(self, mock_anthropic):
        """Test extractor initialization with Claude."""
        extractor = AIExtractor(provider="claude", api_key="test-key")

        assert extractor.provider_name == "claude"
        assert isinstance(extractor.provider, ClaudeProvider)

    @patch("openai.OpenAI")
    def test_extractor_with_openai(self, mock_openai):
        """Test extractor initialization with OpenAI."""
        extractor = AIExtractor(provider="openai", api_key="test-key")

        assert extractor.provider_name == "openai"
        assert isinstance(extractor.provider, OpenAIProvider)

    def test_extractor_invalid_provider(self):
        """Test extractor with invalid provider."""
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            AIExtractor(provider="invalid", api_key="test-key")

    @patch("anthropic.Anthropic")
    def test_extract_entities(self, mock_anthropic):
        """Test entity extraction through main extractor."""
        # Setup mock
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({"entities": [], "relationships": [], "summary": "Test"}))
        ]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        extractor = AIExtractor(provider="claude", api_key="test-key")
        result = extractor.extract_entities("Test text")

        assert isinstance(result, ExtractedEntities)
        assert result.summary == "Test"

    @patch("anthropic.Anthropic")
    def test_extract_from_batch(self, mock_anthropic):
        """Test batch extraction."""
        # Setup mock
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({"entities": [], "relationships": [], "summary": "Test"}))
        ]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        extractor = AIExtractor(provider="claude", api_key="test-key")

        transcripts = [
            {"title": "Meeting 1", "content": "Content 1"},
            {"title": "Meeting 2", "content": "Content 2"},
        ]

        results = extractor.extract_from_batch(transcripts)

        assert len(results) == 2
        assert all(isinstance(r, ExtractedEntities) for r in results)
        assert mock_client.messages.create.call_count == 2

    def test_default_prompt(self):
        """Test default extraction prompt."""
        extractor = AIExtractor(provider="claude", api_key="test-key")
        prompt = extractor._get_default_prompt()

        assert "people" in prompt.lower()
        assert "organizations" in prompt.lower()
        assert "tasks" in prompt.lower()
        assert "json" in prompt.lower()
