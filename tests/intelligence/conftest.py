"""Test configuration and fixtures for intelligence system tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List
import json
from datetime import datetime


@pytest.fixture
def event_loop():
    """Create an instance of the event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_entity():
    """Create a mock entity."""
    from blackcore.intelligence.interfaces import Entity
    return Entity(
        id="test_entity_1",
        name="Test Entity",
        type="person",
        properties={"role": "test", "department": "testing"},
        confidence=0.95,
        source="test_source"
    )


@pytest.fixture
def mock_relationship():
    """Create a mock relationship."""
    from blackcore.intelligence.interfaces import Relationship
    return Relationship(
        id="test_rel_1",
        source_id="test_entity_1",
        target_id="test_entity_2",
        type="works_for",
        properties={"since": "2023"},
        confidence=0.85
    )


@pytest.fixture
def mock_analysis_request():
    """Create a mock analysis request."""
    from blackcore.intelligence.interfaces import AnalysisRequest, AnalysisType
    return AnalysisRequest(
        type=AnalysisType.ENTITY_EXTRACTION,
        parameters={"text": "Test text for entity extraction"},
        context={"test": True}
    )


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock()
    provider.complete = AsyncMock()
    provider.complete_with_functions = AsyncMock()
    provider.estimate_tokens = Mock(return_value=100)
    return provider


@pytest.fixture
def mock_graph_backend():
    """Create a mock graph backend."""
    backend = AsyncMock()
    backend.add_entity = AsyncMock(return_value=True)
    backend.add_relationship = AsyncMock(return_value=True)
    backend.get_entity = AsyncMock()
    backend.get_entities = AsyncMock(return_value=[])
    backend.get_relationships = AsyncMock(return_value=[])
    backend.execute_query = AsyncMock(return_value=[])
    backend.get_subgraph = AsyncMock(return_value={"entities": [], "relationships": []})
    return backend


@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.clear = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def sample_llm_responses():
    """Sample LLM responses for different analysis types."""
    return {
        "entity_extraction": {
            "entities": [
                {
                    "name": "John Smith",
                    "type": "person",
                    "properties": {"role": "Councillor"},
                    "context": "Local government official",
                    "confidence": 0.9
                },
                {
                    "name": "ABC Construction",
                    "type": "organization",
                    "properties": {"industry": "construction"},
                    "context": "Construction company",
                    "confidence": 0.85
                }
            ]
        },
        "relationship_extraction": {
            "relationships": [
                {
                    "source": "John Smith",
                    "target": "ABC Construction",
                    "type": "connected_to",
                    "properties": {"nature": "business"},
                    "context": "Multiple contracts awarded",
                    "confidence": 0.8
                }
            ]
        },
        "community_detection": {
            "communities": [
                {
                    "id": "community_1",
                    "name": "Construction Network",
                    "members": ["entity_1", "entity_2", "entity_3"],
                    "characteristics": "Frequent business interactions",
                    "key_connectors": ["entity_1"],
                    "internal_edges": ["rel_1", "rel_2"],
                    "rationale": "High density of business relationships"
                }
            ],
            "modularity": 0.75
        },
        "anomaly_detection": {
            "anomalies": [
                {
                    "description": "Unusual payment pattern detected",
                    "entity_ids": ["entity_1", "entity_2"],
                    "evidence": {"payment_frequency": "irregular"},
                    "score": 0.85,
                    "implications": "Potential financial irregularity"
                }
            ],
            "summary": "High-risk financial anomalies detected",
            "recommendations": ["Investigate payment records", "Review contracts"]
        },
        "path_finding": {
            "paths": [
                {
                    "nodes": ["entity_1", "entity_3", "entity_2"],
                    "edges": ["rel_1", "rel_2"],
                    "characteristics": "Indirect connection through intermediary",
                    "significance": "Hidden relationship revealed"
                }
            ]
        },
        "risk_scoring": {
            "risk_scores": [
                {
                    "entity_id": "entity_1",
                    "score": 0.78,
                    "factors": ["financial_anomalies", "relationship_patterns"],
                    "evidence": {"anomaly_count": 3, "suspicious_relationships": 2},
                    "rationale": "Multiple risk indicators present"
                }
            ],
            "summary": "High corruption risk identified",
            "recommendations": ["Immediate investigation required"]
        }
    }


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    from blackcore.intelligence.config import IntelligenceConfig, LLMConfig, GraphConfig, CacheConfig
    
    config = IntelligenceConfig()
    config.llm = LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-key",
        temperature=0.7,
        requests_per_minute=50,
        tokens_per_minute=40000
    )
    config.graph = GraphConfig(
        backend="networkx",
        connection_params={}
    )
    config.cache = CacheConfig(
        backend="memory",
        max_size=1000,
        default_ttl=3600
    )
    return config


@pytest.fixture
def mock_entity_list():
    """Create a list of mock entities."""
    from blackcore.intelligence.interfaces import Entity
    return [
        Entity(
            id=f"entity_{i}",
            name=f"Entity {i}",
            type="person" if i % 2 == 0 else "organization",
            properties={"index": i},
            confidence=0.8 + (i * 0.01)
        )
        for i in range(5)
    ]


@pytest.fixture
def mock_relationship_list():
    """Create a list of mock relationships."""
    from blackcore.intelligence.interfaces import Relationship
    return [
        Relationship(
            id=f"rel_{i}",
            source_id=f"entity_{i}",
            target_id=f"entity_{i+1}",
            type="connected_to",
            properties={"strength": i * 0.2},
            confidence=0.7 + (i * 0.05)
        )
        for i in range(4)
    ]


@pytest.fixture
def mock_graph_data(mock_entity_list, mock_relationship_list):
    """Create mock graph data."""
    return {
        "entities": [e.to_dict() for e in mock_entity_list],
        "relationships": [r.to_dict() for r in mock_relationship_list],
        "metadata": {
            "num_nodes": len(mock_entity_list),
            "num_edges": len(mock_relationship_list)
        }
    }


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None
    
    async def complete(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        response_format: Dict[str, Any] = None
    ) -> str:
        """Mock completion."""
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        
        # Return appropriate response based on prompt content
        if "entity" in prompt.lower() and "extraction" in prompt.lower():
            return json.dumps(self.responses.get("entity_extraction", {"entities": []}))
        elif "relationship" in prompt.lower():
            return json.dumps(self.responses.get("relationship_extraction", {"relationships": []}))
        elif "community" in prompt.lower():
            return json.dumps(self.responses.get("community_detection", {"communities": []}))
        elif "anomaly" in prompt.lower():
            return json.dumps(self.responses.get("anomaly_detection", {"anomalies": []}))
        elif "path" in prompt.lower():
            return json.dumps(self.responses.get("path_finding", {"paths": []}))
        elif "risk" in prompt.lower():
            return json.dumps(self.responses.get("risk_scoring", {"risk_scores": []}))
        
        return json.dumps({})
    
    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: str = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Mock function completion."""
        self.call_count += 1
        self.last_prompt = prompt
        return {"content": "Function called"}
    
    def estimate_tokens(self, text: str) -> int:
        """Mock token estimation."""
        return len(text) // 4


@pytest.fixture
def mock_llm_provider_with_responses(sample_llm_responses):
    """Create a mock LLM provider with predefined responses."""
    return MockLLMProvider(responses=sample_llm_responses)


@pytest.fixture
async def cleanup_graph_backend():
    """Cleanup function for graph backend tests."""
    backends = []
    
    def register(backend):
        backends.append(backend)
        return backend
    
    yield register
    
    # Cleanup
    for backend in backends:
        if hasattr(backend, 'close'):
            await backend.close()


@pytest.fixture
def assert_valid_entity():
    """Helper to assert entity validity."""
    def _assert(entity):
        assert hasattr(entity, 'id')
        assert hasattr(entity, 'name')
        assert hasattr(entity, 'type')
        assert hasattr(entity, 'properties')
        assert hasattr(entity, 'confidence')
        assert hasattr(entity, 'to_dict')
        assert callable(entity.to_dict)
        assert 0 <= entity.confidence <= 1
    return _assert


@pytest.fixture
def assert_valid_relationship():
    """Helper to assert relationship validity."""
    def _assert(relationship):
        assert hasattr(relationship, 'id')
        assert hasattr(relationship, 'source_id')
        assert hasattr(relationship, 'target_id')
        assert hasattr(relationship, 'type')
        assert hasattr(relationship, 'properties')
        assert hasattr(relationship, 'confidence')
        assert hasattr(relationship, 'to_dict')
        assert callable(relationship.to_dict)
        assert 0 <= relationship.confidence <= 1
    return _assert


@pytest.fixture
def assert_valid_analysis_result():
    """Helper to assert analysis result validity."""
    def _assert(result):
        assert hasattr(result, 'request')
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'to_dict')
        assert callable(result.to_dict)
        assert isinstance(result.success, bool)
        assert isinstance(result.errors, list)
    return _assert