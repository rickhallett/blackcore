"""Tests for the NLP module."""

import pytest
from typing import List, Dict, Any

from ..nlp import (
    SimpleQueryParser,
    SimpleSpellChecker,
    ContextualSpellChecker,
    IntelligentQuerySuggester,
    QueryIntent,
    EntityType,
    ExtractedEntity,
    ParsedQuery,
    SpellCorrection,
    QuerySuggestion,
    NLPConfig
)


class TestSimpleQueryParser:
    """Test cases for SimpleQueryParser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return SimpleQueryParser()
    
    def test_parse_simple_search(self, parser):
        """Test parsing simple search queries."""
        query = "find all people"
        result = parser.parse(query)
        
        assert result.intent == QueryIntent.SEARCH_ENTITY
        assert result.confidence > 0.7
        assert any(e.text == "people" for e in result.entities)
    
    def test_extract_entities(self, parser):
        """Test entity extraction."""
        text = "Find John Smith from Microsoft who attended the Annual Conference"
        entities = parser.extract_entities(text)
        
        # Should find person name
        person_entities = [e for e in entities if e.entity_type == EntityType.PERSON]
        assert len(person_entities) >= 1
        assert any("John Smith" in e.text for e in person_entities)
        
        # Should find organization
        org_entities = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]
        assert len(org_entities) >= 1
        
        # Should find event
        event_entities = [e for e in entities if e.entity_type == EntityType.EVENT]
        assert len(event_entities) >= 1
    
    def test_classify_intent(self, parser):
        """Test intent classification."""
        # Search intent
        intent, conf = parser.classify_intent("find all organizations", [])
        assert intent == QueryIntent.SEARCH_ENTITY
        assert conf > 0.7
        
        # Relationship intent
        intent, conf = parser.classify_intent("show relationships between John and Jane", [])
        assert intent == QueryIntent.FIND_RELATIONSHIP
        assert conf > 0.8
        
        # Aggregate intent
        intent, conf = parser.classify_intent("count all tasks by status", [])
        assert intent == QueryIntent.AGGREGATE_DATA
        assert conf > 0.8
        
        # Sort intent
        intent, conf = parser.classify_intent("sort by created date", [])
        assert intent == QueryIntent.SORT_RESULTS
        assert conf > 0.8
    
    def test_extract_filters(self, parser):
        """Test filter extraction."""
        query = "find tasks created after 2024-01-01 with status open"
        parsed = parser.parse(query)
        
        assert "status" in parsed.filters
        assert parsed.filters["status"] == "open"
        
        # Date filters should be extracted
        assert any("created" in k or "date" in k for k in parsed.filters)
    
    def test_extract_sort_criteria(self, parser):
        """Test sort criteria extraction."""
        query = "find all people sorted by name ascending"
        parsed = parser.parse(query)
        
        assert len(parsed.sort_criteria) > 0
        assert parsed.sort_criteria[0] == ("name", "asc")
    
    def test_extract_limit(self, parser):
        """Test limit extraction."""
        queries = [
            ("show top 10 results", 10),
            ("find first 5 people", 5),
            ("list 20 organizations", 20)
        ]
        
        for query, expected_limit in queries:
            parsed = parser.parse(query)
            assert parsed.limit == expected_limit
    
    def test_extract_relationships(self, parser):
        """Test relationship extraction."""
        query = "find people with their tasks and organizations"
        parsed = parser.parse(query)
        
        assert "tasks" in parsed.relationships_to_include
        assert "organizations" in parsed.relationships_to_include
    
    def test_extract_aggregations(self, parser):
        """Test aggregation extraction."""
        query = "count tasks grouped by status"
        parsed = parser.parse(query)
        
        assert len(parsed.aggregations) >= 1
        
        # Should have count aggregation
        count_agg = next((a for a in parsed.aggregations if a["type"] == "count"), None)
        assert count_agg is not None
        
        # Should have group by
        group_agg = next((a for a in parsed.aggregations if a["type"] == "group_by"), None)
        assert group_agg is not None
        assert group_agg["field"] == "status"
    
    def test_date_filter_extraction(self, parser):
        """Test date-based filter extraction."""
        queries = [
            ("created today", "today"),
            ("updated yesterday", "yesterday"),
            ("modified this week", "this week"),
            ("changed last week", "last week")
        ]
        
        for query, expected in queries:
            parsed = parser.parse(query)
            assert "date" in parsed.filters or any(expected.replace(" ", "_") in str(v) for v in parsed.filters.values())
    
    def test_complex_query(self, parser):
        """Test parsing complex query with multiple components."""
        query = (
            "find all people named John from Microsoft "
            "with status active created after 2024-01-01 "
            "sorted by name including their tasks limit 10"
        )
        
        parsed = parser.parse(query)
        
        assert parsed.intent == QueryIntent.SEARCH_ENTITY
        assert len(parsed.entities) >= 2  # John and Microsoft
        assert "status" in parsed.filters
        assert len(parsed.sort_criteria) > 0
        assert parsed.limit == 10
        assert "tasks" in parsed.relationships_to_include


class TestSpellChecker:
    """Test cases for spell checking."""
    
    @pytest.fixture
    def checker(self):
        """Create spell checker instance."""
        return SimpleSpellChecker()
    
    def test_check_spelling(self, checker):
        """Test basic spell checking."""
        corrections = checker.check("find peeple named Jhon")
        
        assert len(corrections) >= 2
        
        # Should suggest corrections for misspellings
        correction_texts = [c.original for c in corrections]
        assert "peeple" in correction_texts
        assert "Jhon" in correction_texts
        
        # Should have reasonable suggestions
        people_correction = next(c for c in corrections if c.original == "peeple")
        assert people_correction.corrected == "people"
        assert people_correction.confidence > 0.7
    
    def test_auto_correct(self, checker):
        """Test automatic correction."""
        text = "find peeple with there tasks"
        corrected = checker.correct(text, auto_correct=True)
        
        assert "people" in corrected
        assert "their" in corrected or "there" in corrected  # Might not correct homonyms
    
    def test_custom_dictionary(self, checker):
        """Test adding words to custom dictionary."""
        # Add technical terms
        checker.add_to_dictionary(["kubernetes", "microservice"])
        
        # Should not flag as misspellings
        corrections = checker.check("deploy kubernetes microservice")
        
        correction_words = [c.original for c in corrections]
        assert "kubernetes" not in correction_words
        assert "microservice" not in correction_words
    
    def test_proper_nouns(self, checker):
        """Test handling of proper nouns."""
        # Capitalized words should be accepted
        corrections = checker.check("John Smith from Microsoft")
        
        correction_words = [c.original for c in corrections]
        assert "John" not in correction_words
        assert "Smith" not in correction_words
        assert "Microsoft" not in correction_words
    
    def test_contextual_spell_checker(self):
        """Test contextual spell checking."""
        checker = ContextualSpellChecker()
        
        # Should consider context for suggestions
        corrections = checker.check_with_context(
            "find peeple in the organiztion",
            domain="business"
        )
        
        # Should have corrections
        assert len(corrections) >= 2
        
        # Domain vocabulary should influence suggestions
        org_correction = next(
            (c for c in corrections if c.original == "organiztion"),
            None
        )
        assert org_correction is not None
        assert org_correction.corrected == "organization"


class TestQuerySuggester:
    """Test cases for query suggestions."""
    
    @pytest.fixture
    def suggester(self):
        """Create suggester instance."""
        return IntelligentQuerySuggester()
    
    def test_starter_suggestions(self, suggester):
        """Test suggestions for empty query."""
        suggestions = suggester.suggest("", [], None)
        
        assert len(suggestions) > 0
        assert all(isinstance(s, QuerySuggestion) for s in suggestions)
        
        # Should have common starters
        suggestion_texts = [s.text for s in suggestions]
        assert any("find" in text.lower() for text in suggestion_texts)
    
    def test_template_suggestions(self, suggester):
        """Test template-based suggestions."""
        suggestions = suggester.suggest("find all ", [], None)
        
        assert len(suggestions) > 0
        
        # Should complete with entity types
        suggestion_texts = [s.text for s in suggestions]
        assert any("people" in text for text in suggestion_texts)
        assert any("organizations" in text for text in suggestion_texts)
    
    def test_history_suggestions(self, suggester):
        """Test suggestions based on history."""
        history = [
            "find all people with status active",
            "show tasks assigned to John",
            "list organizations in New York"
        ]
        
        # Should suggest from history
        suggestions = suggester.suggest("find all p", history, None)
        
        suggestion_texts = [s.text for s in suggestions]
        assert any("find all people with status active" in text for text in suggestion_texts)
    
    def test_data_driven_suggestions(self, suggester):
        """Test suggestions based on available data."""
        data = [
            {"name": "John Smith", "status": "active"},
            {"name": "Jane Doe", "status": "active"},
            {"name": "Bob Johnson", "status": "inactive"}
        ]
        
        suggestions = suggester.suggest("status ", [], data)
        
        # Should suggest actual status values
        suggestion_texts = [s.text for s in suggestions]
        assert any("active" in text for text in suggestion_texts)
    
    def test_learning_from_selection(self, suggester):
        """Test learning from user selections."""
        # Simulate user behavior
        suggester.learn_from_selection(
            "find p",
            "find people with status active",
            ["person1", "person2"]
        )
        
        # Should boost this suggestion in future
        suggestions = suggester.suggest("find p", [], None)
        
        # The learned suggestion should rank high
        suggestion_texts = [s.text for s in suggestions[:3]]
        assert any("find people with status active" in text for text in suggestion_texts)
    
    def test_completion_suggestions(self, suggester):
        """Test word completion suggestions."""
        suggestions = suggester.suggest("find ", [], None)
        
        # Should offer completions
        suggestion_texts = [s.text for s in suggestions]
        assert any(text.startswith("find all") for text in suggestion_texts)
        assert any(text.startswith("find people") for text in suggestion_texts)
    
    def test_deduplication(self, suggester):
        """Test suggestion deduplication."""
        # Create scenario with potential duplicates
        history = ["find all people", "Find All People", "FIND ALL PEOPLE"]
        
        suggestions = suggester.suggest("find", history, None)
        
        # Should deduplicate case variations
        suggestion_texts = [s.text.lower() for s in suggestions]
        assert len(suggestion_texts) == len(set(suggestion_texts))


class TestNLPIntegration:
    """Integration tests for NLP functionality."""
    
    def test_parse_and_correct(self):
        """Test parsing with spell correction."""
        parser = SimpleQueryParser()
        checker = SimpleSpellChecker()
        
        # Query with typos
        query = "find peeple with statis active"
        
        # Correct first
        corrected = checker.correct(query)
        
        # Then parse
        parsed = parser.parse(corrected)
        
        assert parsed.intent == QueryIntent.SEARCH_ENTITY
        assert "people" in corrected
    
    def test_suggestion_to_parse(self):
        """Test flow from suggestion to parsing."""
        suggester = IntelligentQuerySuggester()
        parser = SimpleQueryParser()
        
        # Get suggestions
        suggestions = suggester.suggest("find people with", [], None)
        
        # Take first suggestion and parse it
        if suggestions:
            suggested_query = suggestions[0].text
            parsed = parser.parse(suggested_query)
            
            assert parsed.intent in [QueryIntent.SEARCH_ENTITY, QueryIntent.FILTER_RESULTS]
    
    def test_entity_aware_spelling(self):
        """Test spell checking with entity awareness."""
        parser = SimpleQueryParser()
        checker = ContextualSpellChecker()
        
        # Add known entities to dictionary
        checker.add_to_dictionary(["TechCorp", "DataAnalytics"])
        
        query = "find people from TechCorp in DataAnalytics"
        
        # Should not correct entity names
        corrections = checker.check(query)
        correction_words = [c.original for c in corrections]
        
        assert "TechCorp" not in correction_words
        assert "DataAnalytics" not in correction_words
        
        # Parse should recognize them as entities
        parsed = parser.parse(query)
        entity_texts = [e.text for e in parsed.entities]
        
        assert any("TechCorp" in text for text in entity_texts)