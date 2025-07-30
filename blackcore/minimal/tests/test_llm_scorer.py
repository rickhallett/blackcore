"""Tests for LLM-based similarity scorer."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from blackcore.minimal.llm_scorer import (
    LLMScorer,
    LLMScorerCache,
    LLMScorerWithFallback,
)
from blackcore.minimal.simple_scorer import SimpleScorer


class TestLLMScorerCache:
    """Test LLM scorer cache functionality."""

    def test_cache_key_generation(self):
        """Test consistent cache key generation."""
        cache = LLMScorerCache()

        entity1 = {"name": "John Smith", "email": "john@example.com"}
        entity2 = {"name": "John Smith", "organization": "Acme Corp"}

        # Same entities should produce same key regardless of order
        key1 = cache.get_cache_key(entity1, entity2, "person")
        key2 = cache.get_cache_key(entity2, entity1, "person")
        assert key1 == key2

        # Different entity types should produce different keys
        key3 = cache.get_cache_key(entity1, entity2, "organization")
        assert key1 != key3

    def test_cache_set_and_get(self):
        """Test cache storage and retrieval."""
        cache = LLMScorerCache(ttl_seconds=60)

        key = "test_key"
        value = (95.0, "email match", {"is_match": True})

        # Set value
        cache.set(key, value)

        # Get value should return it
        assert cache.get(key) == value

        # Non-existent key should return None
        assert cache.get("non_existent") is None

    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = LLMScorerCache(ttl_seconds=1)

        key = "test_key"
        value = (95.0, "email match", {"is_match": True})

        # Set value
        cache.set(key, value)
        assert cache.get(key) == value

        # Mock time to simulate expiration
        with patch("blackcore.minimal.llm_scorer.datetime") as mock_datetime:
            # Set current time to 2 seconds later
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)

            # Value should be expired
            assert cache.get(key) is None

    def test_clear_expired(self):
        """Test clearing expired entries."""
        cache = LLMScorerCache(ttl_seconds=1)

        # Add multiple entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Mock time for one entry to expire
        with patch.object(
            cache,
            "cache",
            {
                "key1": ("value1", datetime.now() - timedelta(seconds=2)),
                "key2": ("value2", datetime.now()),
            },
        ):
            cache.clear_expired()

            # Only non-expired entry should remain
            assert "key1" not in cache.cache
            assert "key2" in cache.cache


class TestLLMScorer:
    """Test LLM scorer functionality."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client."""
        with patch("blackcore.minimal.llm_scorer.anthropic") as mock_anthropic:
            client = Mock()
            mock_anthropic.Anthropic.return_value = client
            yield client

    @pytest.fixture
    def scorer(self, mock_anthropic_client):
        """Create LLM scorer with mocked client."""
        return LLMScorer(api_key="test_key", model="claude-3-5-haiku-20241022")

    def test_initialization(self, mock_anthropic_client):
        """Test scorer initialization."""
        scorer = LLMScorer(
            api_key="test_key", model="custom-model", cache_ttl=7200, temperature=0.2
        )

        assert scorer.model == "custom-model"
        assert scorer.temperature == 0.2
        assert scorer.cache.ttl.total_seconds() == 7200

    def test_score_entities_person_match(self, scorer, mock_anthropic_client):
        """Test scoring matching person entities."""
        # Mock response with tool use
        mock_response = Mock()
        mock_content = Mock()
        mock_content.type = "tool_use"
        mock_content.name = "score_entity_match"
        mock_content.input = {
            "confidence_score": 95.0,
            "is_match": True,
            "match_reason": "Same person - nickname variation with matching email domain",
            "supporting_evidence": [
                "Tony is common nickname for Anthony",
                "Email domains match (nassau.gov)",
                "Same organization mentioned",
            ],
            "analysis_dimensions": {
                "name_similarity": 90,
                "professional_context": 95,
                "communication_pattern": 100,
            },
        }
        mock_response.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_response

        # Test entities
        entity1 = {
            "name": "Tony Smith",
            "email": "anthony.smith@nassau.gov",
            "organization": "Nassau Council",
        }
        entity2 = {
            "name": "Anthony Smith",
            "email": "asmith@nassau.gov",
            "organization": "Nassau Council Inc",
        }

        score, reason, details = scorer.score_entities(entity1, entity2, "person")

        assert score == 95.0
        assert reason == "Same person - nickname variation with matching email domain"
        assert details["is_match"] is True
        assert len(details["evidence"]) == 3
        assert details["dimensions"]["name_similarity"] == 90

    def test_score_entities_organization_no_match(self, scorer, mock_anthropic_client):
        """Test scoring non-matching organization entities."""
        # Mock response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.type = "tool_use"
        mock_content.name = "score_entity_match"
        mock_content.input = {
            "confidence_score": 15.0,
            "is_match": False,
            "match_reason": "Different organizations - no significant overlap",
            "supporting_evidence": [
                "Completely different names",
                "No domain or location overlap",
                "Different industries",
            ],
        }
        mock_response.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_response

        # Test entities
        entity1 = {"name": "Acme Corp", "website": "acme.com"}
        entity2 = {"name": "Tech Solutions Ltd", "website": "techsolutions.io"}

        score, reason, details = scorer.score_entities(entity1, entity2, "organization")

        assert score == 15.0
        assert reason == "Different organizations - no significant overlap"
        assert details["is_match"] is False

    def test_score_entities_with_cache(self, scorer, mock_anthropic_client):
        """Test that cache is used for repeated queries."""
        # Mock response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.type = "tool_use"
        mock_content.name = "score_entity_match"
        mock_content.input = {
            "confidence_score": 85.0,
            "is_match": True,
            "match_reason": "Likely match",
            "supporting_evidence": [],
        }
        mock_response.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_response

        entity1 = {"name": "Test Entity"}
        entity2 = {"name": "Test Entity 2"}

        # First call should hit API
        score1, _, _ = scorer.score_entities(entity1, entity2, "person")
        assert mock_anthropic_client.messages.create.call_count == 1

        # Second call should use cache
        score2, _, _ = scorer.score_entities(entity1, entity2, "person")
        assert (
            mock_anthropic_client.messages.create.call_count == 1
        )  # No additional call
        assert score1 == score2

    def test_score_entities_error_handling(self, scorer, mock_anthropic_client):
        """Test error handling in scoring."""
        # Mock API error
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        entity1 = {"name": "Test"}
        entity2 = {"name": "Test2"}

        score, reason, details = scorer.score_entities(entity1, entity2, "person")

        assert score == 0.0
        assert "LLM error" in reason
        assert details["error"] is True

    def test_prompt_building_with_context(self, scorer):
        """Test prompt building with additional context."""
        entity1 = {"name": "John Doe", "email": "john@example.com"}
        entity2 = {"name": "J. Doe", "phone": "555-1234"}

        context = {
            "time_gap": "2 days",
            "shared_connections": ["Jane Smith", "Bob Johnson"],
            "source_documents": ["Meeting Notes 2024-01-15", "Email Thread"],
        }

        prompt = scorer._build_prompt(entity1, entity2, "person", context)

        assert "Time between mentions: 2 days" in prompt
        assert "Shared connections: Jane Smith, Bob Johnson" in prompt
        assert "Source documents: Meeting Notes 2024-01-15, Email Thread" in prompt

    def test_batch_scoring(self, scorer, mock_anthropic_client):
        """Test batch scoring of multiple entity pairs."""
        # Mock response with multiple tool uses
        mock_response = Mock()
        mock_contents = []
        for i in range(3):
            mock_content = Mock()
            mock_content.type = "tool_use"
            mock_content.name = "score_entity_match"
            mock_content.input = {
                "confidence_score": 80.0 + i * 5,
                "is_match": True,
                "match_reason": f"Match {i}",
                "supporting_evidence": [],
            }
            mock_contents.append(mock_content)
        mock_response.content = mock_contents
        mock_anthropic_client.messages.create.return_value = mock_response

        # Test batch
        entity_pairs = [
            ({"name": f"Entity {i}"}, {"name": f"Entity {i}b"}, "person")
            for i in range(3)
        ]

        results = scorer.score_batch(entity_pairs, batch_size=5)

        assert len(results) == 3
        assert results[0][0] == 80.0
        assert results[1][0] == 85.0
        assert results[2][0] == 90.0


class TestLLMScorerWithFallback:
    """Test LLM scorer with fallback functionality."""

    @pytest.fixture
    def simple_scorer(self):
        """Create simple scorer for fallback."""
        return SimpleScorer()

    @pytest.fixture
    def mock_anthropic_failing(self):
        """Mock Anthropic client that always fails."""
        with patch("blackcore.minimal.llm_scorer.anthropic") as mock_anthropic:
            client = Mock()
            client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.Anthropic.return_value = client
            yield client

    def test_fallback_on_error(self, mock_anthropic_failing, simple_scorer):
        """Test fallback to simple scorer on LLM error."""
        scorer = LLMScorerWithFallback(
            api_key="test_key", fallback_scorer=simple_scorer
        )

        entity1 = {"name": "Tony Smith", "email": "tony@example.com"}
        entity2 = {"name": "Anthony Smith", "email": "anthony@example.com"}

        score, reason, details = scorer.score_entities(entity1, entity2, "person")

        # Should get result from simple scorer
        assert score == 90.0  # Nickname match score from simple scorer
        assert details["fallback"] is True
        assert "API Error" in details["error"]

    def test_no_fallback_without_fallback_scorer(self, mock_anthropic_failing):
        """Test that error is raised when no fallback scorer is provided."""
        scorer = LLMScorerWithFallback(api_key="test_key", fallback_scorer=None)

        entity1 = {"name": "Test"}
        entity2 = {"name": "Test2"}

        with pytest.raises(Exception, match="API Error"):
            scorer.score_entities(entity1, entity2, "person")
