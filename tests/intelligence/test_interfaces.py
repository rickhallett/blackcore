"""Tests for core intelligence system interfaces."""

import pytest
from datetime import datetime
import json
from typing import Dict, Any


class TestEntity:
    """Tests for Entity model."""
    
    def test_entity_creation(self):
        """Test basic entity creation."""
        from blackcore.intelligence.interfaces import Entity
        
        entity = Entity(
            id="person_john_smith",
            name="John Smith",
            type="person",
            properties={"role": "councillor", "age": 45},
            confidence=0.95,
            source="transcript_001"
        )
        
        assert entity.id == "person_john_smith"
        assert entity.name == "John Smith"
        assert entity.type == "person"
        assert entity.properties["role"] == "councillor"
        assert entity.confidence == 0.95
        assert entity.source == "transcript_001"
        assert isinstance(entity.timestamp, datetime)
    
    def test_entity_to_dict(self):
        """Test entity serialization to dictionary."""
        from blackcore.intelligence.interfaces import Entity
        
        entity = Entity(
            id="org_abc",
            name="ABC Construction",
            type="organization",
            properties={"industry": "construction"},
            confidence=0.85
        )
        
        entity_dict = entity.to_dict()
        
        assert entity_dict["id"] == "org_abc"
        assert entity_dict["name"] == "ABC Construction"
        assert entity_dict["type"] == "organization"
        assert entity_dict["properties"]["industry"] == "construction"
        assert entity_dict["confidence"] == 0.85
        assert "timestamp" in entity_dict
    
    def test_entity_defaults(self):
        """Test entity default values."""
        from blackcore.intelligence.interfaces import Entity
        
        entity = Entity(
            id="test_entity",
            name="Test Entity",
            type="unknown"
        )
        
        assert entity.properties == {}
        assert entity.confidence == 1.0
        assert entity.source is None
        assert isinstance(entity.timestamp, datetime)


class TestRelationship:
    """Tests for Relationship model."""
    
    def test_relationship_creation(self):
        """Test basic relationship creation."""
        from blackcore.intelligence.interfaces import Relationship
        
        relationship = Relationship(
            id="rel_001",
            source_id="person_john_smith",
            target_id="org_abc",
            type="works_for",
            properties={"since": "2020", "position": "consultant"},
            confidence=0.8
        )
        
        assert relationship.id == "rel_001"
        assert relationship.source_id == "person_john_smith"
        assert relationship.target_id == "org_abc"
        assert relationship.type == "works_for"
        assert relationship.properties["since"] == "2020"
        assert relationship.confidence == 0.8
        assert isinstance(relationship.timestamp, datetime)
    
    def test_relationship_to_dict(self):
        """Test relationship serialization to dictionary."""
        from blackcore.intelligence.interfaces import Relationship
        
        relationship = Relationship(
            id="rel_002",
            source_id="entity_1",
            target_id="entity_2",
            type="connected_to",
            properties={"strength": 0.75}
        )
        
        rel_dict = relationship.to_dict()
        
        assert rel_dict["id"] == "rel_002"
        assert rel_dict["source_id"] == "entity_1"
        assert rel_dict["target_id"] == "entity_2"
        assert rel_dict["type"] == "connected_to"
        assert rel_dict["properties"]["strength"] == 0.75
        assert "timestamp" in rel_dict


class TestAnalysisType:
    """Tests for AnalysisType enum."""
    
    def test_analysis_types(self):
        """Test all analysis types are available."""
        from blackcore.intelligence.interfaces import AnalysisType
        
        expected_types = [
            "entity_extraction",
            "relationship_mapping",
            "community_detection",
            "anomaly_detection",
            "path_finding",
            "centrality_analysis",
            "pattern_recognition",
            "risk_scoring",
            "temporal_analysis",
            "financial_analysis"
        ]
        
        for expected in expected_types:
            assert hasattr(AnalysisType, expected.upper())
            assert getattr(AnalysisType, expected.upper()).value == expected


class TestAnalysisRequest:
    """Tests for AnalysisRequest model."""
    
    def test_analysis_request_creation(self):
        """Test basic analysis request creation."""
        from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisType
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Test text", "entity_types": ["person", "organization"]},
            context={"source": "transcript_001"},
            constraints={"max_entities": 10}
        )
        
        assert request.type == AnalysisType.ENTITY_EXTRACTION
        assert request.parameters["text"] == "Test text"
        assert request.context["source"] == "transcript_001"
        assert request.constraints["max_entities"] == 10
    
    def test_analysis_request_to_prompt_context(self):
        """Test conversion to prompt context."""
        from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisType
        
        request = AnalysisRequest(
            type=AnalysisType.RISK_SCORING,
            parameters={"entity_ids": ["entity_1", "entity_2"]},
            context={"investigation_id": "inv_001"}
        )
        
        prompt_context = request.to_prompt_context()
        parsed = json.loads(prompt_context)
        
        assert parsed["analysis_type"] == "risk_scoring"
        assert parsed["parameters"]["entity_ids"] == ["entity_1", "entity_2"]
        assert parsed["context"]["investigation_id"] == "inv_001"
    
    def test_analysis_request_defaults(self):
        """Test default values for analysis request."""
        from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisType
        
        request = AnalysisRequest(type=AnalysisType.COMMUNITY_DETECTION)
        
        assert request.parameters == {}
        assert request.context == {}
        assert request.constraints == {}


class TestAnalysisResult:
    """Tests for AnalysisResult model."""
    
    def test_analysis_result_success(self):
        """Test successful analysis result."""
        from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisResult, AnalysisType
        
        request = AnalysisRequest(type=AnalysisType.ENTITY_EXTRACTION)
        result = AnalysisResult(
            request=request,
            success=True,
            data={
                "entities": [
                    {"name": "John Smith", "type": "person"}
                ],
                "count": 1
            },
            metadata={"llm_model": "gpt-4"},
            duration_ms=1250.5
        )
        
        assert result.success is True
        assert result.data["count"] == 1
        assert result.metadata["llm_model"] == "gpt-4"
        assert result.errors == []
        assert result.duration_ms == 1250.5
        assert isinstance(result.timestamp, datetime)
    
    def test_analysis_result_failure(self):
        """Test failed analysis result."""
        from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisResult, AnalysisType
        
        request = AnalysisRequest(type=AnalysisType.PATH_FINDING)
        result = AnalysisResult(
            request=request,
            success=False,
            data=None,
            errors=["Source entity not found", "Invalid graph state"]
        )
        
        assert result.success is False
        assert result.data is None
        assert len(result.errors) == 2
        assert "Source entity not found" in result.errors
    
    def test_analysis_result_to_dict(self):
        """Test result serialization to dictionary."""
        from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisResult, AnalysisType
        
        request = AnalysisRequest(
            type=AnalysisType.ANOMALY_DETECTION,
            parameters={"anomaly_type": "financial"}
        )
        result = AnalysisResult(
            request=request,
            success=True,
            data={"anomalies": [], "summary": "No anomalies found"},
            metadata={"processing_time": "2.5s"},
            duration_ms=2500
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["request"]["type"] == "anomaly_detection"
        assert result_dict["request"]["parameters"]["anomaly_type"] == "financial"
        assert result_dict["success"] is True
        assert result_dict["data"]["summary"] == "No anomalies found"
        assert result_dict["metadata"]["processing_time"] == "2.5s"
        assert result_dict["duration_ms"] == 2500
        assert "timestamp" in result_dict


class TestInterfaceAbstractions:
    """Tests for abstract interfaces."""
    
    def test_llm_provider_interface(self):
        """Test LLM provider interface definition."""
        from blackcore.intelligence.interfaces import ILLMProvider
        
        # Verify interface methods
        assert hasattr(ILLMProvider, "complete")
        assert hasattr(ILLMProvider, "complete_with_functions")
        assert hasattr(ILLMProvider, "estimate_tokens")
    
    def test_graph_backend_interface(self):
        """Test graph backend interface definition."""
        from blackcore.intelligence.interfaces import IGraphBackend
        
        # Verify interface methods
        expected_methods = [
            "add_entity", "add_relationship", "get_entity",
            "get_entities", "get_relationships", "execute_query",
            "get_subgraph"
        ]
        
        for method in expected_methods:
            assert hasattr(IGraphBackend, method)
    
    def test_analysis_strategy_interface(self):
        """Test analysis strategy interface definition."""
        from blackcore.intelligence.interfaces import IAnalysisStrategy
        
        assert hasattr(IAnalysisStrategy, "analyze")
        assert hasattr(IAnalysisStrategy, "can_handle")
    
    def test_cache_interface(self):
        """Test cache interface definition."""
        from blackcore.intelligence.interfaces import ICache
        
        expected_methods = ["get", "set", "delete", "clear"]
        for method in expected_methods:
            assert hasattr(ICache, method)
    
    def test_investigation_pipeline_interface(self):
        """Test investigation pipeline interface definition."""
        from blackcore.intelligence.interfaces import IInvestigationPipeline
        
        expected_methods = ["investigate", "add_evidence", "get_investigation"]
        for method in expected_methods:
            assert hasattr(IInvestigationPipeline, method)


class TestModelValidation:
    """Tests for model validation and edge cases."""
    
    def test_entity_confidence_bounds(self):
        """Test entity confidence must be between 0 and 1."""
        from blackcore.intelligence.interfaces import Entity
        
        # Valid confidence
        entity = Entity(id="test", name="Test", type="test", confidence=0.5)
        assert entity.confidence == 0.5
        
        # Test bounds (implementation should validate these)
        entity_low = Entity(id="test", name="Test", type="test", confidence=0.0)
        assert entity_low.confidence == 0.0
        
        entity_high = Entity(id="test", name="Test", type="test", confidence=1.0)
        assert entity_high.confidence == 1.0
    
    def test_empty_properties(self):
        """Test models with empty properties."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        entity = Entity(id="test", name="Test", type="test", properties={})
        assert entity.properties == {}
        
        relationship = Relationship(
            id="rel", 
            source_id="src", 
            target_id="tgt", 
            type="test", 
            properties={}
        )
        assert relationship.properties == {}
    
    def test_json_serialization_compatibility(self):
        """Test that all models can be JSON serialized."""
        from blackcore.intelligence.interfaces import Entity, Relationship, AnalysisRequest, AnalysisResult, AnalysisType
        
        # Entity
        entity = Entity(id="test", name="Test", type="test")
        json.dumps(entity.to_dict())  # Should not raise
        
        # Relationship
        rel = Relationship(id="rel", source_id="src", target_id="tgt", type="test")
        json.dumps(rel.to_dict())  # Should not raise
        
        # AnalysisRequest
        req = AnalysisRequest(type=AnalysisType.ENTITY_EXTRACTION)
        json.dumps(req.to_prompt_context())  # Should not raise
        
        # AnalysisResult
        result = AnalysisResult(request=req, success=True, data={"test": "data"})
        json.dumps(result.to_dict())  # Should not raise