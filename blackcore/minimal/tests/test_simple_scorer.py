"""Tests for simple similarity scorer."""

import pytest
from blackcore.minimal.simple_scorer import SimpleScorer


class TestSimpleScorer:
    """Test suite for SimpleScorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return SimpleScorer()
        
    def test_exact_name_match(self, scorer):
        """Test exact name matching."""
        assert scorer.score_names("John Smith", "John Smith") == 100.0
        assert scorer.score_names("john smith", "JOHN SMITH") == 100.0
        
    def test_normalized_name_match(self, scorer):
        """Test normalized name matching."""
        # With punctuation
        assert scorer.score_names("John Smith, Jr.", "John Smith Jr") == 95.0
        
        # With titles
        assert scorer.score_names("Dr. John Smith", "John Smith") == 95.0
        assert scorer.score_names("Mr. John Smith", "John Smith") == 95.0
        
    def test_nickname_matching(self, scorer):
        """Test nickname detection."""
        # Common nicknames
        assert scorer.score_names("Tony Smith", "Anthony Smith") == 90.0
        assert scorer.score_names("Bob Johnson", "Robert Johnson") == 90.0
        assert scorer.score_names("Bill Williams", "William Williams") == 90.0
        assert scorer.score_names("Liz Taylor", "Elizabeth Taylor") == 90.0
        
        # Reverse direction
        assert scorer.score_names("Anthony Smith", "Tony Smith") == 90.0
        
    def test_partial_name_match(self, scorer):
        """Test partial name matching."""
        # Same last name, different first name
        assert scorer.score_names("John Smith", "Jane Smith") == 60.0
        assert scorer.score_names("Michael Johnson", "Sarah Johnson") == 60.0
        
    def test_no_match(self, scorer):
        """Test completely different names."""
        score = scorer.score_names("John Smith", "Sarah Johnson")
        assert score < 50.0
        
    def test_person_entity_scoring(self, scorer):
        """Test person entity matching."""
        person1 = {
            "name": "Tony Smith",
            "email": "tony@example.com",
            "organization": "Acme Corp"
        }
        
        person2 = {
            "name": "Anthony Smith", 
            "email": "tony@example.com",
            "organization": "Acme Corporation"
        }
        
        # Email match should give high score
        score, reason = scorer.score_entities(person1, person2, "person")
        assert score == 95.0
        assert reason == "email match"
        
    def test_person_phone_match(self, scorer):
        """Test person matching by phone."""
        person1 = {
            "name": "John Doe",
            "phone": "+1 (555) 123-4567"
        }
        
        person2 = {
            "name": "Johnny Doe",
            "phone": "15551234567"
        }
        
        score, reason = scorer.score_entities(person1, person2, "person")
        assert score == 92.0
        assert reason == "phone match"
        
    def test_person_name_plus_org_match(self, scorer):
        """Test person matching with organization boost."""
        person1 = {
            "name": "J. Smith",
            "organization": "Nassau Council"
        }
        
        person2 = {
            "name": "John Smith",
            "organization": "Nassau Council"
        }
        
        score, reason = scorer.score_entities(person1, person2, "person")
        assert score > 70.0  # Base score + org boost
        assert "organization" in reason
        
    def test_organization_exact_match(self, scorer):
        """Test organization exact matching."""
        org1 = {"name": "Nassau Town Council"}
        org2 = {"name": "Nassau Town Council"}
        
        score, reason = scorer.score_entities(org1, org2, "organization")
        assert score == 100.0
        
    def test_organization_normalized_match(self, scorer):
        """Test organization normalization."""
        org1 = {"name": "Nassau Council Inc."}
        org2 = {"name": "Nassau Council"}
        
        score, reason = scorer.score_entities(org1, org2, "organization")
        assert score == 95.0
        assert reason == "normalized name match"
        
        # Test with Ltd, Corp, etc.
        org1 = {"name": "Acme Corporation"}
        org2 = {"name": "Acme Corp"}
        
        score, reason = scorer.score_entities(org1, org2, "organization")
        assert score == 95.0
        
    def test_organization_website_match(self, scorer):
        """Test organization matching by website."""
        org1 = {
            "name": "Nassau Council",
            "website": "https://www.nassau.gov"
        }
        
        org2 = {
            "name": "Nassau Town Council", 
            "website": "http://nassau.gov/"
        }
        
        score, reason = scorer.score_entities(org1, org2, "organization")
        assert score == 93.0
        assert reason == "website match"
        
    def test_normalize_url(self, scorer):
        """Test URL normalization."""
        # Same domain, different protocols
        assert scorer._normalize_url("https://example.com") == "example.com"
        assert scorer._normalize_url("http://example.com") == "example.com"
        assert scorer._normalize_url("https://www.example.com") == "example.com"
        assert scorer._normalize_url("http://www.example.com/") == "example.com"
        assert scorer._normalize_url("https://example.com/page") == "example.com"
        
    def test_normalize_phone(self, scorer):
        """Test phone normalization."""
        assert scorer._normalize_phone("+1 (555) 123-4567") == "15551234567"
        assert scorer._normalize_phone("555-123-4567") == "5551234567"
        assert scorer._normalize_phone("(555) 123 4567") == "5551234567"
        assert scorer._normalize_phone("5551234567") == "5551234567"
        
    def test_edge_cases(self, scorer):
        """Test edge cases."""
        # Empty names
        assert scorer.score_names("", "") == 100.0
        assert scorer.score_names("John", "") == 0.0
        
        # Single names
        assert scorer.score_names("John", "John") == 100.0
        assert scorer.score_names("John", "Johnny") > 80.0  # Should be reasonably high
        
        # Very long names
        long_name1 = "John Michael Christopher Smith-Johnson III"
        long_name2 = "John Michael Christopher Smith Johnson"
        assert scorer.score_names(long_name1, long_name2) > 90.0