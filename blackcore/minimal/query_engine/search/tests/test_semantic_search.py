"""Comprehensive tests for the semantic search engine."""

import pytest
from typing import List, Dict, Any

from blackcore.minimal.query_engine.search.semantic_search import (
    SemanticSearchEngine, SemanticSearchResult, TokenInfo
)
from blackcore.minimal.query_engine.models import SearchConfig


class TestSemanticSearchEngine:
    """Test suite for semantic search functionality."""
    
    @pytest.fixture
    def search_engine(self):
        """Create search engine instance."""
        return SemanticSearchEngine()
    
    @pytest.fixture
    def sample_data(self) -> List[Dict[str, Any]]:
        """Create sample test data."""
        return [
            {
                "id": "person1",
                "properties": {
                    "Name": "Alice Johnson",
                    "Email": "alice.johnson@example.com",
                    "Department": "Engineering",
                    "Role": "Senior Software Engineer",
                    "Bio": "Experienced engineer specializing in machine learning and AI"
                },
                "_database": "People & Contacts"
            },
            {
                "id": "person2",
                "properties": {
                    "Name": "Bob Smith",
                    "Email": "bob.smith@example.com",
                    "Department": "Sales",
                    "Role": "Sales Manager",
                    "Bio": "Strategic sales leader with 10 years experience"
                },
                "_database": "People & Contacts"
            },
            {
                "id": "task1",
                "properties": {
                    "Title": "Implement machine learning pipeline",
                    "Description": "Build ML pipeline for customer churn prediction",
                    "Assignee": "Alice Johnson",
                    "Status": "In Progress",
                    "Priority": "High"
                },
                "_database": "Actionable Tasks"
            },
            {
                "id": "doc1",
                "properties": {
                    "Title": "Q4 Engineering Report",
                    "Content": "Quarterly report on engineering team achievements and goals",
                    "Author": "Alice Johnson",
                    "Tags": ["engineering", "quarterly", "report"]
                },
                "_database": "Documents & Evidence"
            },
            {
                "id": "meeting1",
                "properties": {
                    "Title": "Weekly Engineering Sync",
                    "Date": "2024-01-15",
                    "Attendees": ["Alice Johnson", "Team"],
                    "Notes": "Discussed ML pipeline progress and Q4 goals"
                },
                "_database": "Key Places & Events"
            }
        ]
    
    def test_basic_search(self, search_engine, sample_data):
        """Test basic search functionality."""
        results = search_engine.search("Alice", sample_data)
        
        assert len(results) >= 3  # Alice appears in multiple records
        assert results[0].score > 0.5
        assert any("person1" in r.entity["id"] for r in results)
    
    def test_fuzzy_matching(self, search_engine, sample_data):
        """Test fuzzy string matching."""
        # Test with typo
        results = search_engine.search("Alise Johnson", sample_data)
        
        assert len(results) > 0
        assert results[0].entity["properties"]["Name"] == "Alice Johnson"
        assert results[0].score > 0.7
    
    def test_synonym_expansion(self, search_engine, sample_data):
        """Test query expansion with synonyms."""
        # Search for "todo" should find "task"
        results = search_engine.search("todo machine learning", sample_data)
        
        assert len(results) > 0
        assert any("task" in r.entity["id"] for r in results)
    
    def test_entity_recognition(self, search_engine, sample_data):
        """Test entity extraction and recognition."""
        # Email search
        results = search_engine.search("alice.johnson@example.com", sample_data)
        
        assert len(results) > 0
        assert results[0].entity["properties"]["Email"] == "alice.johnson@example.com"
        assert results[0].score > 0.9
        
        # Date search
        results = search_engine.search("2024-01-15", sample_data)
        
        assert len(results) > 0
        assert any("meeting" in r.entity["id"] for r in results)
    
    def test_intent_detection(self, search_engine):
        """Test query intent detection."""
        test_cases = [
            ("Who is Alice Johnson?", "find_person"),
            ("What tasks are in progress?", "find_task"),
            ("Find engineering documents", "find_document"),
            ("Show me meetings on 2024-01-15", "find_by_date"),
            ("How many people in engineering?", "count"),
            ("random search query", "general_search")
        ]
        
        for query, expected_intent in test_cases:
            query_info = search_engine._parse_query(query)
            assert query_info['intent'] == expected_intent
    
    def test_phrase_matching(self, search_engine, sample_data):
        """Test multi-word phrase matching."""
        results = search_engine.search("machine learning pipeline", sample_data)
        
        assert len(results) > 0
        assert results[0].entity["id"] == "task1"
        assert results[0].score > 0.8
    
    def test_quoted_exact_match(self, search_engine, sample_data):
        """Test exact matching with quotes."""
        results = search_engine.search('"Senior Software Engineer"', sample_data)
        
        assert len(results) == 1
        assert results[0].entity["properties"]["Role"] == "Senior Software Engineer"
        assert results[0].score > 0.9
    
    def test_field_weighting(self, search_engine, sample_data):
        """Test that important fields get higher scores."""
        # Name field should score higher than Bio field
        results = search_engine.search("Alice", sample_data)
        
        # Find the person record vs other records
        person_score = next(r.score for r in results if r.entity["id"] == "person1")
        other_scores = [r.score for r in results if r.entity["id"] != "person1"]
        
        assert person_score > max(other_scores) if other_scores else True
    
    def test_highlighting(self, search_engine, sample_data):
        """Test search result highlighting."""
        results = search_engine.search("engineering machine learning", sample_data)
        
        assert len(results) > 0
        result = results[0]
        
        if hasattr(result, 'highlights'):
            assert len(result.highlights) > 0
            # Check that highlights contain context
            for field, highlights in result.highlights.items():
                for highlight in highlights:
                    assert len(highlight) > 0
    
    def test_case_insensitive_search(self, search_engine, sample_data):
        """Test case-insensitive searching."""
        results_lower = search_engine.search("alice johnson", sample_data)
        results_upper = search_engine.search("ALICE JOHNSON", sample_data)
        results_mixed = search_engine.search("Alice JOHNSON", sample_data)
        
        # All should return same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)
        assert results_lower[0].entity["id"] == results_upper[0].entity["id"]
    
    def test_search_suggestions(self, search_engine, sample_data):
        """Test search suggestion generation."""
        suggestions = search_engine.get_search_suggestions("eng", sample_data, 5)
        
        assert len(suggestions) > 0
        assert any("engineering" in s.lower() for s in suggestions)
    
    def test_empty_query(self, search_engine, sample_data):
        """Test handling of empty queries."""
        results = search_engine.search("", sample_data)
        assert len(results) == 0
        
        results = search_engine.search("   ", sample_data)
        assert len(results) == 0
    
    def test_no_results(self, search_engine, sample_data):
        """Test query with no matches."""
        results = search_engine.search("xyz123nonexistent", sample_data)
        assert len(results) == 0
    
    def test_stop_word_filtering(self, search_engine, sample_data):
        """Test that stop words are filtered appropriately."""
        # Query with only stop words should still work
        results = search_engine.search("the and or", sample_data)
        # Should match content but with lower scores
        assert all(r.score < 0.5 for r in results) or len(results) == 0
    
    def test_unicode_normalization(self, search_engine, sample_data):
        """Test Unicode text normalization."""
        # Add data with accents
        unicode_data = sample_data + [{
            "id": "unicode1",
            "properties": {
                "Name": "José García",
                "Department": "Ingeniería"
            },
            "_database": "People & Contacts"
        }]
        
        # Search without accents should find accented version
        results = search_engine.search("Jose Garcia", unicode_data)
        assert len(results) > 0
        assert any("unicode1" in r.entity["id"] for r in results)
    
    def test_relevance_scoring(self, search_engine, sample_data):
        """Test relevance scoring calculation."""
        # Single item test
        score = search_engine.calculate_relevance_score(
            sample_data[0],
            "Alice Johnson Engineering",
            None
        )
        
        assert 0 <= score <= 1
        assert score > 0.7  # Should be high for exact matches
    
    def test_config_min_score(self, search_engine, sample_data):
        """Test minimum score filtering."""
        config = SearchConfig(min_score=0.8)
        results = search_engine.search("engineering", sample_data, config)
        
        assert all(r.score >= 0.8 for r in results)
    
    def test_config_max_results(self, search_engine, sample_data):
        """Test result limit configuration."""
        config = SearchConfig(max_results=2)
        results = search_engine.search("Alice", sample_data, config)
        
        assert len(results) <= 2
    
    def test_semantic_result_attributes(self, search_engine, sample_data):
        """Test SemanticSearchResult attributes."""
        results = search_engine.search("Alice machine learning", sample_data)
        
        assert len(results) > 0
        result = results[0]
        
        assert isinstance(result, SemanticSearchResult)
        assert hasattr(result, 'entity')
        assert hasattr(result, 'score')
        assert hasattr(result, 'database')
        assert hasattr(result, 'explanation')
        assert hasattr(result, 'semantic_score')
    
    def test_complex_query(self, search_engine, sample_data):
        """Test complex multi-criteria query."""
        query = "engineering Alice Q4 report machine learning"
        results = search_engine.search(query, sample_data)
        
        assert len(results) >= 3
        # Should find person, task, and document
        entity_types = {r.entity["_database"] for r in results[:3]}
        assert len(entity_types) >= 2  # Multiple databases represented
    
    def test_performance_large_dataset(self, search_engine):
        """Test search performance on larger dataset."""
        import time
        
        # Generate 1000 records
        large_data = []
        for i in range(1000):
            large_data.append({
                "id": f"item{i}",
                "properties": {
                    "Name": f"Person {i}",
                    "Department": ["Engineering", "Sales", "HR"][i % 3],
                    "Description": f"Description for person {i} with various keywords"
                },
                "_database": "Test"
            })
        
        start_time = time.time()
        results = search_engine.search("Person 500 Engineering", large_data)
        execution_time = time.time() - start_time
        
        assert len(results) > 0
        assert execution_time < 0.5  # Should complete in under 500ms


class TestSearchHelperMethods:
    """Test helper methods of the search engine."""
    
    @pytest.fixture
    def search_engine(self):
        return SemanticSearchEngine()
    
    def test_normalize_text(self, search_engine):
        """Test text normalization."""
        test_cases = [
            ("Hello World", "hello world"),
            ("  Multiple   Spaces  ", "multiple spaces"),
            ("José García", "jose garcia"),
            ("UPPERCASE", "uppercase"),
            ("email@example.com", "email@example.com")
        ]
        
        for input_text, expected in test_cases:
            assert search_engine._normalize_text(input_text) == expected
    
    def test_tokenize(self, search_engine):
        """Test tokenization."""
        text = "The quick brown fox jumps over the lazy dog"
        tokens = search_engine._tokenize(text)
        
        # Stop words should be filtered
        assert "the" not in tokens
        assert "over" not in tokens
        
        # Content words should remain
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens
    
    def test_extract_entities(self, search_engine):
        """Test entity extraction."""
        text = "Contact alice@example.com or call 555-123-4567 on 2024-01-15"
        entities = search_engine._extract_entities(text)
        
        assert "email" in entities
        assert entities["email"] == ["alice@example.com"]
        
        assert "phone" in entities
        assert len(entities["phone"]) > 0
        
        assert "date" in entities
        assert "2024-01-15" in entities["date"]
    
    def test_flatten_dict(self, search_engine):
        """Test dictionary flattening."""
        nested = {
            "a": 1,
            "b": {
                "c": 2,
                "d": {
                    "e": 3
                }
            },
            "f": [4, 5, 6]
        }
        
        flattened = search_engine._flatten_dict(nested)
        flattened_dict = dict(flattened)
        
        assert flattened_dict["a"] == 1
        assert flattened_dict["b.c"] == 2
        assert flattened_dict["b.d.e"] == 3
        assert "4 5 6" in str(flattened_dict["f"])