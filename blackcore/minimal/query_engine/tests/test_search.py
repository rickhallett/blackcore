"""Tests for the search module."""

import pytest
from typing import List, Dict, Any

from ..search import (
    SimpleTextSearchEngine,
    FuzzyMatcher,
    SearchConfig,
    SearchMode,
    SearchResult
)


class TestSimpleTextSearchEngine:
    """Test cases for SimpleTextSearchEngine."""
    
    @pytest.fixture
    def search_engine(self):
        """Create search engine instance."""
        return SimpleTextSearchEngine()
    
    @pytest.fixture
    def sample_data(self) -> List[Dict[str, Any]]:
        """Sample data for testing."""
        return [
            {
                "id": "1",
                "name": "John Smith",
                "title": "Software Engineer",
                "description": "Experienced developer with Python expertise",
                "tags": ["python", "backend", "api"]
            },
            {
                "id": "2",
                "name": "Jane Doe",
                "title": "Data Scientist",
                "description": "Machine learning specialist focusing on NLP",
                "tags": ["ml", "nlp", "python"]
            },
            {
                "id": "3",
                "name": "Bob Johnson",
                "title": "Project Manager",
                "description": "Agile project management professional",
                "tags": ["agile", "scrum", "management"]
            }
        ]
    
    def test_exact_search(self, search_engine, sample_data):
        """Test exact text matching."""
        config = SearchConfig(mode=SearchMode.EXACT, min_score=0.1)
        results = search_engine.search("John Smith", sample_data, config)
        
        assert len(results) == 1
        assert results[0].entity["id"] == "1"
        assert results[0].score > 0.8
    
    def test_fuzzy_search(self, search_engine, sample_data):
        """Test fuzzy matching with typos."""
        config = SearchConfig(mode=SearchMode.FUZZY, min_score=0.1)
        
        # Search with typo
        results = search_engine.search("Jon Smth", sample_data, config)
        
        assert len(results) >= 1
        assert results[0].entity["id"] == "1"
        assert results[0].score > 0.5
    
    def test_field_weighting(self, search_engine, sample_data):
        """Test field weight influence on scoring."""
        config = SearchConfig(
            field_weights={"name": 2.0, "description": 1.0},
            min_score=0.1
        )
        
        results = search_engine.search("Python", sample_data, config)
        
        # Should find both Python mentions
        assert len(results) >= 2
        
        # Check that results are properly scored
        for result in results:
            assert result.score > 0
            assert "python" in str(result.entity).lower()
    
    def test_search_highlighting(self, search_engine, sample_data):
        """Test search result highlighting."""
        config = SearchConfig(highlight_matches=True, min_score=0.1)
        results = search_engine.search("Machine learning", sample_data, config)
        
        assert len(results) >= 1
        result = results[0]
        assert len(result.highlights) > 0
        assert any("Machine learning" in h for h in result.highlights.get("description", []))
    
    def test_empty_query(self, search_engine, sample_data):
        """Test handling of empty query."""
        config = SearchConfig()
        results = search_engine.search("", sample_data, config)
        
        assert len(results) == 0
    
    def test_no_matches(self, search_engine, sample_data):
        """Test query with no matches."""
        config = SearchConfig(min_score=0.5)
        results = search_engine.search("blockchain cryptocurrency", sample_data, config)
        
        assert len(results) == 0
    
    def test_case_insensitive_search(self, search_engine, sample_data):
        """Test case insensitive matching."""
        config = SearchConfig(case_sensitive=False)
        
        results1 = search_engine.search("PYTHON", sample_data, config)
        results2 = search_engine.search("python", sample_data, config)
        
        assert len(results1) == len(results2)
        assert results1[0].entity["id"] == results2[0].entity["id"]
    
    def test_tokenization(self, search_engine):
        """Test tokenization logic."""
        tokens = search_engine.tokenize("Hello, World! This is a test-case.")
        
        expected = ["hello", "world", "this", "test", "case"]
        assert tokens == expected
    
    def test_fuzzy_match_threshold(self, search_engine):
        """Test fuzzy matching with different thresholds."""
        # High threshold - should not match
        is_match, score = search_engine.fuzzy_match("hello", "hallo", threshold=0.9)
        assert not is_match
        
        # Lower threshold - should match
        is_match, score = search_engine.fuzzy_match("hello", "hallo", threshold=0.7)
        assert is_match
        assert score > 0.7


class TestFuzzyMatcher:
    """Test cases for FuzzyMatcher."""
    
    @pytest.fixture
    def matcher(self):
        """Create fuzzy matcher instance."""
        return FuzzyMatcher()
    
    def test_levenshtein_distance(self, matcher):
        """Test Levenshtein distance calculation."""
        assert matcher.levenshtein_distance("", "") == 0
        assert matcher.levenshtein_distance("hello", "hello") == 0
        assert matcher.levenshtein_distance("hello", "hallo") == 1
        assert matcher.levenshtein_distance("hello", "world") == 4
        assert matcher.levenshtein_distance("kitten", "sitting") == 3
    
    def test_jaro_similarity(self, matcher):
        """Test Jaro similarity calculation."""
        assert matcher.jaro_similarity("", "") == 1.0
        assert matcher.jaro_similarity("hello", "hello") == 1.0
        assert matcher.jaro_similarity("hello", "hallo") > 0.8
        assert matcher.jaro_similarity("martha", "marhta") > 0.9
        assert matcher.jaro_similarity("dixon", "dicksonx") > 0.7
    
    def test_jaro_winkler_similarity(self, matcher):
        """Test Jaro-Winkler similarity with prefix bonus."""
        # Same prefix should boost score
        jaro = matcher.jaro_similarity("prefixed", "preference")
        jaro_winkler = matcher.jaro_winkler_similarity("prefixed", "preference")
        assert jaro_winkler > jaro
    
    def test_soundex(self, matcher):
        """Test Soundex phonetic encoding."""
        assert matcher.soundex("Smith") == matcher.soundex("Smyth")
        assert matcher.soundex("Johnson") == matcher.soundex("Jonson")
        assert matcher.soundex("Williams") != matcher.soundex("Wilson")
        
        # Test caching
        assert matcher.soundex("Test") == matcher.soundex("Test")
    
    def test_metaphone(self, matcher):
        """Test Metaphone phonetic encoding."""
        assert matcher.metaphone("Smith") == matcher.metaphone("Smyth")
        assert matcher.metaphone("Catherine") == matcher.metaphone("Katherine")
        assert len(matcher.metaphone("test")) <= 4  # Max length
    
    def test_ngram_similarity(self, matcher):
        """Test n-gram similarity."""
        assert matcher.ngram_similarity("hello", "hello") == 1.0
        assert matcher.ngram_similarity("hello", "hallo") > 0.5
        assert matcher.ngram_similarity("", "test") == 0.0
        
        # Test with different n
        sim_2 = matcher.ngram_similarity("hello", "world", n=2)
        sim_3 = matcher.ngram_similarity("hello", "world", n=3)
        assert sim_2 != sim_3
    
    def test_cosine_similarity(self, matcher):
        """Test cosine similarity based on character frequency."""
        assert matcher.cosine_similarity("hello", "hello") == 1.0
        assert matcher.cosine_similarity("hello", "hallo") > 0.8
        assert matcher.cosine_similarity("abc", "xyz") == 0.0
    
    def test_best_match(self, matcher):
        """Test finding best match from candidates."""
        candidates = ["hello", "hallo", "world", "help"]
        
        match, score = matcher.best_match("helo", candidates, threshold=0.6)
        assert match in ["hello", "hallo"]
        assert score > 0.6
        
        # No match above threshold
        match, score = matcher.best_match("xyz", candidates, threshold=0.8)
        assert match is None
    
    def test_normalize_text(self, matcher):
        """Test text normalization."""
        assert matcher.normalize_text("Hello World!") == "hello world"
        assert matcher.normalize_text("café") == "cafe"
        assert matcher.normalize_text("  multiple   spaces  ") == "multiple spaces"
        assert matcher.normalize_text("test's") == "test's"


class TestSearchIntegration:
    """Integration tests for search functionality."""
    
    def test_multi_field_search(self):
        """Test searching across multiple fields."""
        engine = SimpleTextSearchEngine()
        data = [
            {
                "id": "1",
                "title": "Python Development",
                "content": "Advanced programming techniques",
                "author": "John Python"
            },
            {
                "id": "2",
                "title": "Data Science",
                "content": "Python for machine learning",
                "author": "Jane Smith"
            }
        ]
        
        config = SearchConfig(
            field_weights={"title": 2.0, "content": 1.0, "author": 1.5}
        )
        
        results = engine.search("Python", data, config)
        
        # Both should match, but first should score higher (title match)
        assert len(results) == 2
        assert results[0].entity["id"] == "1"  # Title match weighted higher
    
    def test_phonetic_search(self):
        """Test phonetic matching capabilities."""
        engine = SimpleTextSearchEngine()
        data = [
            {"id": "1", "name": "Stephen Smith"},
            {"id": "2", "name": "Steven Smyth"},
            {"id": "3", "name": "John Johnson"}
        ]
        
        config = SearchConfig(mode=SearchMode.FUZZY)
        results = engine.search("Stefan Smit", data, config)
        
        # Should find phonetically similar names
        assert len(results) >= 2
        found_ids = [r.entity["id"] for r in results]
        assert "1" in found_ids or "2" in found_ids