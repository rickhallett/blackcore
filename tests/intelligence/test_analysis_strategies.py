"""Tests for analysis strategy implementations."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from blackcore.intelligence.interfaces import (
    AnalysisType,
    AnalysisRequest,
    AnalysisResult,
    Entity,
    Relationship,
    ILLMProvider,
    IGraphBackend
)

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class TestEntityExtractionStrategy:
    """Tests for entity extraction strategy."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = Mock(spec=ILLMProvider)
        llm.complete = AsyncMock()
        llm.complete_with_functions = AsyncMock()
        llm.estimate_tokens = Mock(return_value=100)
        return llm
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock graph backend."""
        graph = Mock(spec=IGraphBackend)
        graph.add_entity = AsyncMock(return_value=True)
        graph.add_relationship = AsyncMock(return_value=True)
        graph.get_entity = AsyncMock(return_value=None)
        graph.search_entities = AsyncMock(return_value=[])
        return graph
    
    async def test_extract_entities_from_text(self, mock_llm, mock_graph):
        """Test extracting entities from unstructured text."""
        from blackcore.intelligence.strategies.entity_extraction import EntityExtractionStrategy
        
        strategy = EntityExtractionStrategy()
        
        # Configure mock LLM response
        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {
                    "name": "John Doe",
                    "type": "person",
                    "properties": {
                        "role": "CEO",
                        "company": "TechCorp"
                    },
                    "confidence": 0.95
                },
                {
                    "name": "TechCorp",
                    "type": "organization",
                    "properties": {
                        "industry": "technology",
                        "founded": "2020"
                    },
                    "confidence": 0.9
                }
            ]
        })
        
        # Create request
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={
                "text": "John Doe is the CEO of TechCorp, a technology company founded in 2020.",
                "entity_types": ["person", "organization", "location"]
            }
        )
        
        # Execute analysis
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        # Verify result
        assert result.success is True
        assert "entities" in result.data
        assert len(result.data["entities"]) == 2
        
        # Verify entities were added to graph
        assert mock_graph.add_entity.call_count == 2
        
        # Check first entity
        first_call = mock_graph.add_entity.call_args_list[0]
        entity = first_call[0][0]
        assert entity.name == "John Doe"
        assert entity.type == "person"
        assert entity.properties["role"] == "CEO"
    
    async def test_extract_entities_with_context(self, mock_llm, mock_graph):
        """Test entity extraction with additional context."""
        from blackcore.intelligence.strategies.entity_extraction import EntityExtractionStrategy
        
        strategy = EntityExtractionStrategy()
        
        # Configure mock response
        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {
                    "name": "Project Alpha",
                    "type": "project",
                    "properties": {
                        "status": "active",
                        "budget": "$1M",
                        "timeline": "Q1 2024"
                    },
                    "confidence": 0.85
                }
            ]
        })
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={
                "text": "The project is currently active with a budget of $1M."
            },
            context={
                "project_name": "Project Alpha",
                "timeline": "Q1 2024"
            }
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert len(result.data["entities"]) == 1
        assert result.data["entities"][0]["name"] == "Project Alpha"
    
    async def test_handle_extraction_errors(self, mock_llm, mock_graph):
        """Test error handling in entity extraction."""
        from blackcore.intelligence.strategies.entity_extraction import EntityExtractionStrategy
        
        strategy = EntityExtractionStrategy()
        
        # Configure mock to raise error
        mock_llm.complete.side_effect = Exception("LLM API error")
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Some text"}
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "LLM API error" in result.errors[0]
    
    async def test_deduplicate_entities(self, mock_llm, mock_graph):
        """Test entity deduplication during extraction."""
        from blackcore.intelligence.strategies.entity_extraction import EntityExtractionStrategy
        
        strategy = EntityExtractionStrategy()
        
        # Configure existing entity in graph
        existing_entity = Entity(
            id="person_john_doe",
            name="John Doe",
            type="person",
            properties={"role": "CTO"}
        )
        mock_graph.search_entities.return_value = [existing_entity]
        
        # Configure LLM response with duplicate
        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {
                    "name": "John Doe",
                    "type": "person",
                    "properties": {"role": "CEO"},
                    "confidence": 0.9
                }
            ]
        })
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "John Doe is the CEO."}
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        # Should merge/update existing entity rather than create new
        assert result.metadata["merged_count"] == 1


class TestRelationshipMappingStrategy:
    """Tests for relationship mapping strategy."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = Mock(spec=ILLMProvider)
        llm.complete = AsyncMock()
        llm.complete_with_functions = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock graph backend."""
        graph = Mock(spec=IGraphBackend)
        graph.add_relationship = AsyncMock(return_value=True)
        graph.get_entity = AsyncMock()
        graph.get_entities = AsyncMock(return_value=[])
        return graph
    
    async def test_map_relationships_from_entities(self, mock_llm, mock_graph):
        """Test mapping relationships between known entities."""
        from blackcore.intelligence.strategies.relationship_mapping import RelationshipMappingStrategy
        
        strategy = RelationshipMappingStrategy()
        
        # Configure mock entities
        entities = [
            Entity(id="p1", name="John Doe", type="person"),
            Entity(id="o1", name="TechCorp", type="organization"),
            Entity(id="p2", name="Jane Smith", type="person")
        ]
        
        # Create entity lookup
        entity_lookup = {e.id: e for e in entities}
        
        # Configure get_entity to return specific entities
        async def async_get_entity(entity_id):
            return entity_lookup.get(entity_id)
        
        mock_graph.get_entity.side_effect = async_get_entity
        
        # Configure LLM response
        mock_llm.complete.return_value = json.dumps({
            "relationships": [
                {
                    "source": "John Doe",
                    "target": "TechCorp",
                    "type": "works_for",
                    "properties": {"position": "CEO"},
                    "confidence": 0.95
                },
                {
                    "source": "Jane Smith",
                    "target": "TechCorp",
                    "type": "works_for",
                    "properties": {"position": "CTO"},
                    "confidence": 0.9
                },
                {
                    "source": "John Doe",
                    "target": "Jane Smith",
                    "type": "manages",
                    "properties": {},
                    "confidence": 0.85
                }
            ]
        })
        
        request = AnalysisRequest(
            type=AnalysisType.RELATIONSHIP_MAPPING,
            parameters={"entity_ids": ["p1", "o1", "p2"]}
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert "relationships" in result.data
        assert len(result.data["relationships"]) == 3
        
        # Verify relationships were added
        assert mock_graph.add_relationship.call_count == 3
    
    async def test_map_relationships_with_constraints(self, mock_llm, mock_graph):
        """Test relationship mapping with type constraints."""
        from blackcore.intelligence.strategies.relationship_mapping import RelationshipMappingStrategy
        
        strategy = RelationshipMappingStrategy()
        
        # Configure entities
        entities = [
            Entity(id="p1", name="Alice", type="person"),
            Entity(id="p2", name="Bob", type="person")
        ]
        
        # Create entity lookup
        entity_lookup = {e.id: e for e in entities}
        
        # Configure get_entity to return specific entities
        async def async_get_entity(entity_id):
            return entity_lookup.get(entity_id)
        
        mock_graph.get_entity.side_effect = async_get_entity
        
        mock_llm.complete.return_value = json.dumps({
            "relationships": [
                {
                    "source": "Alice",
                    "target": "Bob",
                    "type": "knows",
                    "properties": {"since": "2020"},
                    "confidence": 0.8
                }
            ]
        })
        
        request = AnalysisRequest(
            type=AnalysisType.RELATIONSHIP_MAPPING,
            parameters={"entity_ids": ["p1", "p2"]},
            constraints={"relationship_types": ["knows", "related_to"]}
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert len(result.data["relationships"]) == 1
        assert result.data["relationships"][0]["type"] == "knows"
    
    async def test_infer_implicit_relationships(self, mock_llm, mock_graph):
        """Test inferring implicit relationships from context."""
        from blackcore.intelligence.strategies.relationship_mapping import RelationshipMappingStrategy
        
        strategy = RelationshipMappingStrategy()
        
        # Configure entities with properties
        entities = [
            Entity(
                id="p1", 
                name="Project A", 
                type="project",
                properties={"owner": "John Doe", "budget": "$1M"}
            ),
            Entity(
                id="p2",
                name="Project B",
                type="project", 
                properties={"owner": "John Doe", "budget": "$2M"}
            )
        ]
        
        # Create entity lookup
        entity_lookup = {e.id: e for e in entities}
        
        # Configure get_entity to return specific entities
        async def async_get_entity(entity_id):
            return entity_lookup.get(entity_id)
        
        mock_graph.get_entity.side_effect = async_get_entity
        
        mock_llm.complete.return_value = json.dumps({
            "relationships": [
                {
                    "source": "Project A",
                    "target": "Project B",
                    "type": "related_to",
                    "properties": {"reason": "same owner"},
                    "confidence": 0.7
                }
            ]
        })
        
        request = AnalysisRequest(
            type=AnalysisType.RELATIONSHIP_MAPPING,
            parameters={
                "entity_ids": ["p1", "p2"],
                "infer_implicit": True
            }
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert len(result.data["relationships"]) >= 1


class TestCommunityDetectionStrategy:
    """Tests for community detection strategy."""
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock graph backend with network data."""
        graph = Mock(spec=IGraphBackend)
        
        # Create a simple network
        entities = [
            Entity(id="a", name="Alice", type="person"),
            Entity(id="b", name="Bob", type="person"),
            Entity(id="c", name="Charlie", type="person"),
            Entity(id="d", name="David", type="person"),
            Entity(id="e", name="Eve", type="person")
        ]
        
        relationships = [
            Relationship(id="r1", source_id="a", target_id="b", type="knows"),
            Relationship(id="r2", source_id="b", target_id="c", type="knows"),
            Relationship(id="r3", source_id="a", target_id="c", type="knows"),
            Relationship(id="r4", source_id="d", target_id="e", type="knows"),
            Relationship(id="r5", source_id="c", target_id="d", type="knows")  # Bridge
        ]
        
        graph.get_entities.return_value = entities
        graph.get_relationships.return_value = relationships
        graph.get_subgraph = AsyncMock(return_value={
            "entities": entities,
            "relationships": relationships
        })
        
        return graph
    
    async def test_detect_communities_basic(self, mock_graph):
        """Test basic community detection."""
        from blackcore.intelligence.strategies.community_detection import CommunityDetectionStrategy
        
        strategy = CommunityDetectionStrategy()
        
        request = AnalysisRequest(
            type=AnalysisType.COMMUNITY_DETECTION,
            parameters={"algorithm": "louvain"}
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "communities" in result.data
        assert len(result.data["communities"]) >= 2  # Should detect at least 2 communities
        
        # Check community structure
        for community in result.data["communities"]:
            assert "id" in community
            assert "members" in community
            assert "size" in community
            assert community["size"] == len(community["members"])
    
    async def test_detect_communities_with_weights(self, mock_graph):
        """Test community detection with relationship weights."""
        from blackcore.intelligence.strategies.community_detection import CommunityDetectionStrategy
        
        strategy = CommunityDetectionStrategy()
        
        # Add weighted relationships
        relationships = [
            Relationship(
                id="r1", source_id="a", target_id="b", type="knows",
                properties={"weight": 1.0}
            ),
            Relationship(
                id="r2", source_id="b", target_id="c", type="knows",
                properties={"weight": 0.5}
            )
        ]
        mock_graph.get_relationships.return_value = relationships
        
        request = AnalysisRequest(
            type=AnalysisType.COMMUNITY_DETECTION,
            parameters={
                "algorithm": "louvain",
                "use_weights": True,
                "weight_property": "weight"
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "communities" in result.data
    
    async def test_hierarchical_community_detection(self, mock_graph):
        """Test hierarchical community detection."""
        from blackcore.intelligence.strategies.community_detection import CommunityDetectionStrategy
        
        strategy = CommunityDetectionStrategy()
        
        request = AnalysisRequest(
            type=AnalysisType.COMMUNITY_DETECTION,
            parameters={
                "algorithm": "hierarchical",
                "max_levels": 3
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "hierarchy" in result.data
        assert "levels" in result.data["hierarchy"]


class TestAnomalyDetectionStrategy:
    """Tests for anomaly detection strategy."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = Mock(spec=ILLMProvider)
        llm.complete = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock graph backend."""
        graph = Mock(spec=IGraphBackend)
        
        # Normal pattern entities
        normal_entities = [
            Entity(
                id=f"tx_{i}",
                name=f"Transaction {i}",
                type="transaction",
                properties={"amount": 100 + i * 10, "risk_score": 0.1}
            )
            for i in range(10)
        ]
        
        # Add anomaly
        anomaly = Entity(
            id="tx_anomaly",
            name="Suspicious Transaction",
            type="transaction",
            properties={"amount": 10000, "risk_score": 0.9}
        )
        
        graph.get_entities.return_value = normal_entities + [anomaly]
        graph.search_entities = AsyncMock(return_value=[])
        
        return graph
    
    async def test_detect_statistical_anomalies(self, mock_llm, mock_graph):
        """Test statistical anomaly detection."""
        from blackcore.intelligence.strategies.anomaly_detection import AnomalyDetectionStrategy
        
        strategy = AnomalyDetectionStrategy()
        
        request = AnalysisRequest(
            type=AnalysisType.ANOMALY_DETECTION,
            parameters={
                "entity_type": "transaction",
                "method": "statistical",
                "threshold": 2.0  # 2 standard deviations
            }
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert "anomalies" in result.data
        assert len(result.data["anomalies"]) >= 1
        
        # Check anomaly was detected
        anomaly_ids = [a["entity_id"] for a in result.data["anomalies"]]
        assert "tx_anomaly" in anomaly_ids
    
    async def test_detect_pattern_anomalies(self, mock_llm, mock_graph):
        """Test pattern-based anomaly detection."""
        from blackcore.intelligence.strategies.anomaly_detection import AnomalyDetectionStrategy
        
        strategy = AnomalyDetectionStrategy()
        
        # Configure LLM to identify pattern anomalies
        mock_llm.complete.return_value = json.dumps({
            "anomalies": [
                {
                    "entity_id": "tx_anomaly",
                    "type": "behavioral",
                    "description": "Transaction amount significantly exceeds normal pattern",
                    "confidence": 0.95
                }
            ]
        })
        
        request = AnalysisRequest(
            type=AnalysisType.ANOMALY_DETECTION,
            parameters={
                "entity_type": "transaction",
                "method": "pattern",
                "context_window": 100
            }
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert len(result.data["anomalies"]) == 1
        assert result.data["anomalies"][0]["type"] == "behavioral"
    
    async def test_detect_graph_anomalies(self, mock_llm, mock_graph):
        """Test graph-based anomaly detection."""
        from blackcore.intelligence.strategies.anomaly_detection import AnomalyDetectionStrategy
        
        strategy = AnomalyDetectionStrategy()
        
        # Create entities with unusual connectivity
        entities = [
            Entity(id=f"node_{i}", name=f"Node {i}", type="entity")
            for i in range(5)
        ]
        
        # Node 0 has many more connections (anomaly)
        relationships = []
        for i in range(1, 5):
            relationships.append(
                Relationship(id=f"r_{i}", source_id="node_0", target_id=f"node_{i}", type="connects")
            )
        
        mock_graph.get_entities.return_value = entities
        mock_graph.get_relationships.return_value = relationships
        
        request = AnalysisRequest(
            type=AnalysisType.ANOMALY_DETECTION,
            parameters={
                "method": "graph",
                "metrics": ["degree", "centrality"],
                "threshold": 1.0  # Lower threshold to catch anomalies
            }
        )
        
        result = await strategy.analyze(request, mock_llm, mock_graph)
        
        assert result.success is True
        assert "anomalies" in result.data
        # Node 0 should be detected as anomaly due to high degree
        anomaly_ids = [a["entity_id"] for a in result.data["anomalies"]]
        assert "node_0" in anomaly_ids


class TestPathFindingStrategy:
    """Tests for path finding strategy."""
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock graph backend."""
        graph = Mock(spec=IGraphBackend)
        graph.find_path = AsyncMock()
        graph.get_entity = AsyncMock()
        return graph
    
    async def test_find_direct_path(self, mock_graph):
        """Test finding direct path between entities."""
        from blackcore.intelligence.strategies.path_finding import PathFindingStrategy
        
        strategy = PathFindingStrategy()
        
        # Configure path
        path_entities = [
            Entity(id="a", name="Start", type="entity"),
            Entity(id="b", name="End", type="entity")
        ]
        mock_graph.find_path.return_value = path_entities
        
        request = AnalysisRequest(
            type=AnalysisType.PATH_FINDING,
            parameters={
                "source_id": "a",
                "target_id": "b"
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "path" in result.data
        assert len(result.data["path"]) == 2
        assert result.data["path"][0]["id"] == "a"
        assert result.data["path"][-1]["id"] == "b"
    
    async def test_find_path_with_constraints(self, mock_graph):
        """Test path finding with constraints."""
        from blackcore.intelligence.strategies.path_finding import PathFindingStrategy
        
        strategy = PathFindingStrategy()
        
        # Configure longer path
        path_entities = [
            Entity(id="a", name="Start", type="entity"),
            Entity(id="b", name="Middle1", type="entity"),
            Entity(id="c", name="Middle2", type="entity"),
            Entity(id="d", name="End", type="entity")
        ]
        mock_graph.find_path.return_value = path_entities
        
        request = AnalysisRequest(
            type=AnalysisType.PATH_FINDING,
            parameters={
                "source_id": "a",
                "target_id": "d",
                "max_length": 5
            },
            constraints={
                "avoid_entity_types": ["restricted"],
                "prefer_relationship_types": ["trusted"]
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert len(result.data["path"]) == 4
        assert result.data["path_length"] == 3  # Number of edges
    
    async def test_find_multiple_paths(self, mock_graph):
        """Test finding multiple paths between entities."""
        from blackcore.intelligence.strategies.path_finding import PathFindingStrategy
        
        strategy = PathFindingStrategy()
        
        # Configure multiple paths
        path1 = [
            Entity(id="a", name="Start", type="entity"),
            Entity(id="b", name="Path1", type="entity"),
            Entity(id="d", name="End", type="entity")
        ]
        
        path2 = [
            Entity(id="a", name="Start", type="entity"),
            Entity(id="c", name="Path2", type="entity"),
            Entity(id="d", name="End", type="entity")
        ]
        
        # Mock returns different paths on subsequent calls
        # Create async side effect
        async def async_find_path_side_effect(*args):
            if async_find_path_side_effect.call_count == 0:
                async_find_path_side_effect.call_count += 1
                return path1
            elif async_find_path_side_effect.call_count == 1:
                async_find_path_side_effect.call_count += 1
                return path2
            else:
                return None
        
        async_find_path_side_effect.call_count = 0
        mock_graph.find_path.side_effect = async_find_path_side_effect
        
        request = AnalysisRequest(
            type=AnalysisType.PATH_FINDING,
            parameters={
                "source_id": "a",
                "target_id": "d",
                "find_all": True,
                "max_paths": 5
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "paths" in result.data
        assert len(result.data["paths"]) >= 2


class TestCentralityAnalysisStrategy:
    """Tests for centrality analysis strategy."""
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock graph backend."""
        graph = Mock(spec=IGraphBackend)
        
        # Create hub-and-spoke network
        entities = [
            Entity(id="hub", name="Central Hub", type="entity"),
            Entity(id="n1", name="Node 1", type="entity"),
            Entity(id="n2", name="Node 2", type="entity"),
            Entity(id="n3", name="Node 3", type="entity"),
            Entity(id="n4", name="Node 4", type="entity")
        ]
        
        relationships = [
            Relationship(id="r1", source_id="hub", target_id="n1", type="connects"),
            Relationship(id="r2", source_id="hub", target_id="n2", type="connects"),
            Relationship(id="r3", source_id="hub", target_id="n3", type="connects"),
            Relationship(id="r4", source_id="hub", target_id="n4", type="connects"),
            Relationship(id="r5", source_id="n1", target_id="n2", type="connects")
        ]
        
        graph.get_entities.return_value = entities
        graph.get_relationships.return_value = relationships
        
        return graph
    
    async def test_calculate_degree_centrality(self, mock_graph):
        """Test degree centrality calculation."""
        from blackcore.intelligence.strategies.centrality_analysis import CentralityAnalysisStrategy
        
        strategy = CentralityAnalysisStrategy()
        
        request = AnalysisRequest(
            type=AnalysisType.CENTRALITY_ANALYSIS,
            parameters={
                "metrics": ["degree"],
                "normalize": True
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "centrality_scores" in result.data
        
        # Hub should have highest degree centrality
        scores = result.data["centrality_scores"]
        hub_score = next(s for s in scores if s["entity_id"] == "hub")
        assert hub_score["degree"] >= 0.5  # Hub has 4 connections out of 8 possible (4 other nodes)
    
    async def test_calculate_betweenness_centrality(self, mock_graph):
        """Test betweenness centrality calculation."""
        from blackcore.intelligence.strategies.centrality_analysis import CentralityAnalysisStrategy
        
        strategy = CentralityAnalysisStrategy()
        
        request = AnalysisRequest(
            type=AnalysisType.CENTRALITY_ANALYSIS,
            parameters={
                "metrics": ["betweenness"],
                "directed": False
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "centrality_scores" in result.data
        
        # Check all entities have betweenness scores
        scores = result.data["centrality_scores"]
        for score in scores:
            assert "betweenness" in score
            assert score["betweenness"] >= 0
    
    async def test_identify_key_players(self, mock_graph):
        """Test identifying key players in network."""
        from blackcore.intelligence.strategies.centrality_analysis import CentralityAnalysisStrategy
        
        strategy = CentralityAnalysisStrategy()
        
        request = AnalysisRequest(
            type=AnalysisType.CENTRALITY_ANALYSIS,
            parameters={
                "metrics": ["degree", "betweenness", "closeness"],
                "identify_key_players": True,
                "top_k": 3
            }
        )
        
        result = await strategy.analyze(request, None, mock_graph)
        
        assert result.success is True
        assert "key_players" in result.data
        assert len(result.data["key_players"]) <= 3
        
        # Hub should be identified as key player
        key_player_ids = [kp["entity_id"] for kp in result.data["key_players"]]
        assert "hub" in key_player_ids


class TestStrategyIntegration:
    """Test strategy integration and coordination."""
    
    async def test_strategy_can_handle_check(self):
        """Test strategy can_handle method."""
        from blackcore.intelligence.strategies.entity_extraction import EntityExtractionStrategy
        from blackcore.intelligence.strategies.relationship_mapping import RelationshipMappingStrategy
        
        entity_strategy = EntityExtractionStrategy()
        rel_strategy = RelationshipMappingStrategy()
        
        assert entity_strategy.can_handle(AnalysisType.ENTITY_EXTRACTION) is True
        assert entity_strategy.can_handle(AnalysisType.RELATIONSHIP_MAPPING) is False
        
        assert rel_strategy.can_handle(AnalysisType.RELATIONSHIP_MAPPING) is True
        assert rel_strategy.can_handle(AnalysisType.ENTITY_EXTRACTION) is False