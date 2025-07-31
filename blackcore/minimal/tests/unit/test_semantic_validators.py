"""Tests for semantic validators."""

import pytest
from blackcore.minimal.tests.utils.semantic_validators import (
    SemanticValidator,
    EntityType,
    ValidationSeverity,
    ExtractionAccuracyAnalyzer
)


class TestPersonValidator:
    """Test person entity validation."""
    
    def test_valid_person(self):
        """Test validation of a valid person entity."""
        validator = SemanticValidator()
        entity = {
            "id": "person-1",
            "type": "person",
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "+1-555-123-4567",
            "role": "Software Engineer"
        }
        
        result = validator.validate_entity(entity, EntityType.PERSON)
        assert result.is_valid
        assert result.confidence_score == 1.0
        assert len(result.issues) == 0
    
    def test_person_missing_name(self):
        """Test person validation with missing name."""
        validator = SemanticValidator()
        entity = {
            "id": "person-1",
            "type": "person",
            "email": "john@example.com"
        }
        
        result = validator.validate_entity(entity, EntityType.PERSON)
        assert not result.is_valid
        assert result.confidence_score < 1.0
        assert any(issue.field == "name" and issue.severity == ValidationSeverity.ERROR 
                  for issue in result.issues)
    
    def test_person_with_org_name(self):
        """Test person validation when name looks like organization."""
        validator = SemanticValidator()
        entity = {
            "id": "person-1",
            "type": "person",
            "name": "Acme Corp Ltd"
        }
        
        result = validator.validate_entity(entity, EntityType.PERSON)
        assert result.is_valid  # Still valid, just warning
        assert result.confidence_score < 1.0
        assert any(issue.field == "name" and issue.severity == ValidationSeverity.WARNING 
                  for issue in result.issues)
        assert any("organization" in suggestion for suggestion in result.suggestions)
    
    def test_person_invalid_email(self):
        """Test person validation with invalid email."""
        validator = SemanticValidator()
        entity = {
            "id": "person-1",
            "type": "person",
            "name": "John Smith",
            "email": "not-an-email"
        }
        
        result = validator.validate_entity(entity, EntityType.PERSON)
        assert result.is_valid  # Email issues are warnings
        assert result.confidence_score < 1.0
        assert any(issue.field == "email" and issue.severity == ValidationSeverity.WARNING 
                  for issue in result.issues)
    
    def test_person_context_validation(self):
        """Test person validation against context."""
        validator = SemanticValidator()
        entity = {
            "id": "person-1",
            "type": "person",
            "name": "John Smith"
        }
        context = "The meeting was attended by Jane Doe and Bob Wilson."
        
        result = validator.validate_entity(entity, EntityType.PERSON, context)
        assert result.is_valid
        assert any(issue.field == "name" and "not found in provided context" in issue.message 
                  for issue in result.issues)


class TestOrganizationValidator:
    """Test organization entity validation."""
    
    def test_valid_organization(self):
        """Test validation of a valid organization entity."""
        validator = SemanticValidator()
        entity = {
            "id": "org-1",
            "type": "organization",
            "name": "Acme Corporation",
            "website": "https://acme.com",
            "type": "technology"
        }
        
        result = validator.validate_entity(entity, EntityType.ORGANIZATION)
        assert result.is_valid
        assert result.confidence_score == 1.0
        assert len(result.issues) == 0
    
    def test_org_with_person_name(self):
        """Test organization validation when name looks like person."""
        validator = SemanticValidator()
        entity = {
            "id": "org-1",
            "type": "organization",
            "name": "John Smith"
        }
        
        result = validator.validate_entity(entity, EntityType.ORGANIZATION)
        assert result.is_valid  # Still valid, just warning
        assert result.confidence_score < 1.0
        assert any(issue.field == "name" and "person's name" in issue.message 
                  for issue in result.issues)
    
    def test_org_invalid_website(self):
        """Test organization validation with invalid website."""
        validator = SemanticValidator()
        entity = {
            "id": "org-1",
            "type": "organization",
            "name": "Acme Corp",
            "website": "not-a-url"
        }
        
        result = validator.validate_entity(entity, EntityType.ORGANIZATION)
        assert result.is_valid  # Website issues are warnings
        assert any(issue.field == "website" and issue.severity == ValidationSeverity.WARNING 
                  for issue in result.issues)


class TestRelationshipValidation:
    """Test relationship validation between entities."""
    
    def test_valid_person_org_relationship(self):
        """Test valid relationship between person and organization."""
        validator = SemanticValidator()
        entities = [
            {"id": "person-1", "type": "person", "name": "John Smith"},
            {"id": "org-1", "type": "organization", "name": "Acme Corp"}
        ]
        relationships = [{
            "source": "person-1",
            "target": "org-1",
            "type": "works_at"
        }]
        
        result = validator.validate_relationships(entities, relationships)
        assert result.is_valid
        assert result.confidence_score == 1.0
        assert len(result.issues) == 0
    
    def test_invalid_relationship_type(self):
        """Test invalid relationship type between entities."""
        validator = SemanticValidator()
        entities = [
            {"id": "person-1", "type": "person", "name": "John Smith"},
            {"id": "person-2", "type": "person", "name": "Jane Doe"}
        ]
        relationships = [{
            "source": "person-1",
            "target": "person-2",
            "type": "located_at"  # Invalid for person-person
        }]
        
        result = validator.validate_relationships(entities, relationships)
        assert result.is_valid  # Warnings don't make it invalid
        assert result.confidence_score < 1.0
        assert any("Invalid relationship" in issue.message for issue in result.issues)
    
    def test_missing_entity_in_relationship(self):
        """Test relationship referencing non-existent entity."""
        validator = SemanticValidator()
        entities = [
            {"id": "person-1", "type": "person", "name": "John Smith"}
        ]
        relationships = [{
            "source": "person-1",
            "target": "org-999",  # Doesn't exist
            "type": "works_at"
        }]
        
        result = validator.validate_relationships(entities, relationships)
        assert not result.is_valid
        assert any("not found" in issue.message and issue.severity == ValidationSeverity.ERROR 
                  for issue in result.issues)


class TestExtractionAccuracy:
    """Test extraction accuracy analysis."""
    
    def test_perfect_extraction(self):
        """Test analysis of perfect extraction."""
        analyzer = ExtractionAccuracyAnalyzer()
        
        extracted = [
            {"id": "1", "type": "person", "name": "John Smith"},
            {"id": "2", "type": "organization", "name": "Acme Corp"}
        ]
        ground_truth = [
            {"id": "1", "type": "person", "name": "John Smith"},
            {"id": "2", "type": "organization", "name": "Acme Corp"}
        ]
        context = "John Smith works at Acme Corp."
        
        results = analyzer.analyze_extraction(extracted, ground_truth, context)
        
        assert results["precision"] == 1.0
        assert results["recall"] == 1.0
        assert results["f1_score"] == 1.0
        assert len(results["missing_entities"]) == 0
        assert len(results["extra_entities"]) == 0
    
    def test_partial_extraction(self):
        """Test analysis of partial extraction."""
        analyzer = ExtractionAccuracyAnalyzer()
        
        extracted = [
            {"id": "1", "type": "person", "name": "John Smith"}
        ]
        ground_truth = [
            {"id": "1", "type": "person", "name": "John Smith"},
            {"id": "2", "type": "organization", "name": "Acme Corp"}
        ]
        context = "John Smith works at Acme Corp."
        
        results = analyzer.analyze_extraction(extracted, ground_truth, context)
        
        assert results["precision"] == 1.0  # All extracted are correct
        assert results["recall"] == 0.5     # Only half of truth extracted
        assert results["f1_score"] == pytest.approx(0.667, rel=0.01)
        assert len(results["missing_entities"]) == 1
        assert results["missing_entities"][0]["name"] == "Acme Corp"
    
    def test_extraction_with_errors(self):
        """Test analysis with extraction errors."""
        analyzer = ExtractionAccuracyAnalyzer()
        
        extracted = [
            {"id": "1", "type": "person", "name": "John Smith"},
            {"id": "3", "type": "person", "name": "Acme Corp"}  # Wrong type
        ]
        ground_truth = [
            {"id": "1", "type": "person", "name": "John Smith"},
            {"id": "2", "type": "organization", "name": "Acme Corp"}
        ]
        context = "John Smith works at Acme Corp."
        
        results = analyzer.analyze_extraction(extracted, ground_truth, context)
        
        assert results["precision"] == 0.5  # Only 1 of 2 correct
        assert results["recall"] == 0.5     # Only 1 of 2 found
        assert results["semantic_accuracy"] < 1.0  # Due to validation issues
        assert len(results["validation_issues"]) > 0
    
    def test_entity_matching(self):
        """Test entity matching with similar names."""
        analyzer = ExtractionAccuracyAnalyzer()
        
        # Test exact match
        score = analyzer._calculate_similarity(
            {"type": "person", "name": "John Smith"},
            {"type": "person", "name": "John Smith"}
        )
        assert score == 1.0
        
        # Test substring match
        score = analyzer._calculate_similarity(
            {"type": "person", "name": "John"},
            {"type": "person", "name": "John Smith"}
        )
        assert score == 0.8
        
        # Test partial match
        score = analyzer._calculate_similarity(
            {"type": "person", "name": "John Doe"},
            {"type": "person", "name": "John Smith"}
        )
        assert 0 < score < 0.8
        
        # Test type mismatch
        score = analyzer._calculate_similarity(
            {"type": "person", "name": "John Smith"},
            {"type": "organization", "name": "John Smith"}
        )
        assert score == 0.0


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_entity(self):
        """Test validation of empty entity."""
        validator = SemanticValidator()
        entity = {"type": "person"}
        
        result = validator.validate_entity(entity, EntityType.PERSON)
        assert not result.is_valid
        assert result.confidence_score < 1.0
    
    def test_unknown_entity_type(self):
        """Test validation of unknown entity type."""
        validator = SemanticValidator()
        entity = {"name": "Test", "type": "unknown"}
        
        # Create a fake entity type for testing
        from enum import Enum
        class FakeType(Enum):
            UNKNOWN = "unknown"
        
        result = validator.validate_entity(entity, FakeType.UNKNOWN)
        assert not result.is_valid
        assert "Unknown entity type" in result.issues[0].message
    
    def test_unicode_names(self):
        """Test validation with unicode names."""
        validator = SemanticValidator()
        entity = {
            "id": "person-1",
            "type": "person",
            "name": "José García-López",
            "email": "jose@example.com"
        }
        
        result = validator.validate_entity(entity, EntityType.PERSON)
        assert result.is_valid
        assert result.confidence_score == 1.0