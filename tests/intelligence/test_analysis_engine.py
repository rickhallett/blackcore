"""Tests for analysis engine orchestration."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from blackcore.intelligence.interfaces import (
    AnalysisType,
    AnalysisRequest,
    AnalysisResult,
    Entity,
    Relationship,
    IAnalysisStrategy,
    ILLMProvider,
    IGraphBackend
)

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class TestAnalysisEngine:
    """Tests for the analysis engine."""
    
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
        graph.get_entity = AsyncMock()
        graph.get_entities = AsyncMock(return_value=[])
        graph.get_relationships = AsyncMock(return_value=[])
        graph.search_entities = AsyncMock(return_value=[])
        graph.find_path = AsyncMock(return_value=None)
        return graph
    
    @pytest.fixture
    def mock_strategies(self):
        """Create mock analysis strategies."""
        strategies = []
        
        # Entity extraction strategy
        entity_strategy = Mock(spec=IAnalysisStrategy)
        entity_strategy.can_handle = Mock(
            side_effect=lambda t: t == AnalysisType.ENTITY_EXTRACTION
        )
        entity_strategy.analyze = AsyncMock()
        strategies.append(entity_strategy)
        
        # Relationship mapping strategy
        rel_strategy = Mock(spec=IAnalysisStrategy)
        rel_strategy.can_handle = Mock(
            side_effect=lambda t: t == AnalysisType.RELATIONSHIP_MAPPING
        )
        rel_strategy.analyze = AsyncMock()
        strategies.append(rel_strategy)
        
        # Community detection strategy
        comm_strategy = Mock(spec=IAnalysisStrategy)
        comm_strategy.can_handle = Mock(
            side_effect=lambda t: t == AnalysisType.COMMUNITY_DETECTION
        )
        comm_strategy.analyze = AsyncMock()
        strategies.append(comm_strategy)
        
        return strategies
    
    async def test_route_to_correct_strategy(self, mock_llm, mock_graph, mock_strategies):
        """Test that requests are routed to the correct strategy."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies
        )
        
        # Test entity extraction routing
        entity_request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "John Doe is the CEO of TechCorp"}
        )
        
        mock_strategies[0].analyze.return_value = AnalysisResult(
            request=entity_request,
            success=True,
            data={"entities": []}
        )
        
        result = await engine.analyze(entity_request)
        
        assert result.success is True
        assert mock_strategies[0].analyze.called
        assert not mock_strategies[1].analyze.called
        assert not mock_strategies[2].analyze.called
    
    async def test_handle_unknown_analysis_type(self, mock_llm, mock_graph, mock_strategies):
        """Test handling of unknown analysis types."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies
        )
        
        # Create request with unknown type
        unknown_request = AnalysisRequest(
            type="unknown_type",  # Not a valid AnalysisType
            parameters={}
        )
        
        result = await engine.analyze(unknown_request)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "No strategy found" in result.errors[0]
    
    async def test_parallel_analysis_execution(self, mock_llm, mock_graph, mock_strategies):
        """Test parallel execution of multiple analyses."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies
        )
        
        # Configure mock responses
        mock_strategies[0].analyze.return_value = AnalysisResult(
            request=AnalysisRequest(type=AnalysisType.ENTITY_EXTRACTION, parameters={}),
            success=True,
            data={"entities": []},
            duration_ms=100
        )
        
        mock_strategies[1].analyze.return_value = AnalysisResult(
            request=AnalysisRequest(type=AnalysisType.RELATIONSHIP_MAPPING, parameters={}),
            success=True,
            data={"relationships": []},
            duration_ms=150
        )
        
        # Create multiple requests
        requests = [
            AnalysisRequest(
                type=AnalysisType.ENTITY_EXTRACTION,
                parameters={"text": "Text 1"}
            ),
            AnalysisRequest(
                type=AnalysisType.RELATIONSHIP_MAPPING,
                parameters={"entity_ids": ["e1", "e2"]}
            )
        ]
        
        # Execute in parallel
        results = await engine.analyze_batch(requests)
        
        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_strategies[0].analyze.called
        assert mock_strategies[1].analyze.called
    
    async def test_strategy_error_handling(self, mock_llm, mock_graph, mock_strategies):
        """Test error handling when strategy fails."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies
        )
        
        # Configure strategy to raise error
        mock_strategies[0].analyze.side_effect = Exception("Strategy error")
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Test"}
        )
        
        result = await engine.analyze(request)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "Strategy error" in result.errors[0]
    
    async def test_add_remove_strategies(self, mock_llm, mock_graph):
        """Test adding and removing strategies dynamically."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=[]
        )
        
        # Initially no strategies
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={}
        )
        
        result = await engine.analyze(request)
        assert result.success is False
        
        # Add strategy
        new_strategy = Mock(spec=IAnalysisStrategy)
        new_strategy.can_handle = Mock(return_value=True)
        new_strategy.analyze = AsyncMock(
            return_value=AnalysisResult(
                request=request,
                success=True,
                data={}
            )
        )
        
        engine.add_strategy(new_strategy)
        
        result = await engine.analyze(request)
        assert result.success is True
        
        # Remove strategy
        engine.remove_strategy(new_strategy)
        
        result = await engine.analyze(request)
        assert result.success is False
    
    async def test_request_validation(self, mock_llm, mock_graph, mock_strategies):
        """Test request validation."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies
        )
        
        # Test with missing required parameters
        invalid_request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={}  # Missing required 'text' parameter
        )
        
        # Configure strategy to check parameters
        mock_strategies[0].analyze.return_value = AnalysisResult(
            request=invalid_request,
            success=False,
            data=None,
            errors=["Missing required parameter: text"]
        )
        
        result = await engine.analyze(invalid_request)
        
        assert result.success is False
        assert "Missing required parameter" in result.errors[0]
    
    async def test_analysis_caching(self, mock_llm, mock_graph, mock_strategies):
        """Test caching of analysis results."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        # Create engine with caching enabled
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies,
            enable_caching=True
        )
        
        # Configure strategy response
        mock_strategies[0].analyze.return_value = AnalysisResult(
            request=AnalysisRequest(type=AnalysisType.ENTITY_EXTRACTION, parameters={"text": "Test"}),
            success=True,
            data={"entities": ["Entity1"]}
        )
        
        # First request
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Test"}
        )
        
        result1 = await engine.analyze(request)
        assert result1.success is True
        assert mock_strategies[0].analyze.call_count == 1
        
        # Second identical request should use cache
        result2 = await engine.analyze(request)
        assert result2.success is True
        assert result2.data == result1.data
        assert mock_strategies[0].analyze.call_count == 1  # Not called again
    
    async def test_analysis_timeout(self, mock_llm, mock_graph, mock_strategies):
        """Test timeout handling for long-running analyses."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies,
            timeout_seconds=1  # 1 second timeout
        )
        
        # Configure strategy to take too long
        async def slow_analyze(*args, **kwargs):
            await asyncio.sleep(2)  # Sleep longer than timeout
            return AnalysisResult(
                request=args[0],
                success=True,
                data={}
            )
        
        mock_strategies[0].analyze = slow_analyze
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Test"}
        )
        
        result = await engine.analyze(request)
        
        assert result.success is False
        assert "timed out" in result.errors[0].lower()
    
    async def test_engine_metrics(self, mock_llm, mock_graph, mock_strategies):
        """Test engine metrics collection."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies,
            collect_metrics=True
        )
        
        # Configure mock responses
        mock_strategies[0].analyze.return_value = AnalysisResult(
            request=AnalysisRequest(type=AnalysisType.ENTITY_EXTRACTION, parameters={}),
            success=True,
            data={},
            duration_ms=100
        )
        
        # Execute several analyses
        for i in range(5):
            request = AnalysisRequest(
                type=AnalysisType.ENTITY_EXTRACTION,
                parameters={"text": f"Test {i}"}
            )
            await engine.analyze(request)
        
        # Get metrics
        metrics = engine.get_metrics()
        
        assert metrics["total_requests"] == 5
        assert metrics["successful_requests"] == 5
        assert metrics["failed_requests"] == 0
        assert "average_duration_ms" in metrics
        assert metrics["requests_by_type"][AnalysisType.ENTITY_EXTRACTION] == 5
    
    async def test_pre_post_processing_hooks(self, mock_llm, mock_graph, mock_strategies):
        """Test pre and post-processing hooks."""
        from blackcore.intelligence.engine import AnalysisEngine
        
        pre_processed = False
        post_processed = False
        
        def pre_process_hook(request: AnalysisRequest) -> AnalysisRequest:
            nonlocal pre_processed
            pre_processed = True
            # Add metadata
            request.context["pre_processed"] = True
            return request
        
        def post_process_hook(result: AnalysisResult) -> AnalysisResult:
            nonlocal post_processed
            post_processed = True
            # Add metadata
            result.metadata["post_processed"] = True
            return result
        
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=mock_strategies,
            pre_process_hook=pre_process_hook,
            post_process_hook=post_process_hook
        )
        
        mock_strategies[0].analyze.return_value = AnalysisResult(
            request=AnalysisRequest(type=AnalysisType.ENTITY_EXTRACTION, parameters={}),
            success=True,
            data={}
        )
        
        request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Test"}
        )
        
        result = await engine.analyze(request)
        
        assert pre_processed is True
        assert post_processed is True
        assert result.metadata.get("post_processed") is True


class TestAnalysisEngineIntegration:
    """Integration tests for analysis engine with real strategies."""
    
    async def test_entity_extraction_to_relationship_mapping_flow(self):
        """Test flow from entity extraction to relationship mapping."""
        from blackcore.intelligence.engine import AnalysisEngine
        from blackcore.intelligence.strategies import (
            EntityExtractionStrategy,
            RelationshipMappingStrategy
        )
        
        # Create mocks
        mock_llm = Mock(spec=ILLMProvider)
        mock_llm.complete = AsyncMock()
        
        mock_graph = Mock(spec=IGraphBackend)
        mock_graph.add_entity = AsyncMock(return_value=True)
        mock_graph.add_relationship = AsyncMock(return_value=True)
        mock_graph.get_entity = AsyncMock()
        mock_graph.search_entities = AsyncMock(return_value=[])
        
        # Create engine with real strategies
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=[
                EntityExtractionStrategy(),
                RelationshipMappingStrategy()
            ]
        )
        
        # First extract entities
        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {
                    "name": "Alice",
                    "type": "person",
                    "properties": {"role": "Manager"},
                    "confidence": 0.9
                },
                {
                    "name": "Bob",
                    "type": "person",
                    "properties": {"role": "Developer"},
                    "confidence": 0.9
                }
            ]
        })
        
        extraction_request = AnalysisRequest(
            type=AnalysisType.ENTITY_EXTRACTION,
            parameters={"text": "Alice manages Bob in the development team"}
        )
        
        extraction_result = await engine.analyze(extraction_request)
        assert extraction_result.success is True
        
        # Then map relationships
        # Configure mocks for relationship mapping
        entities = [
            Entity(id="person_alice", name="Alice", type="person"),
            Entity(id="person_bob", name="Bob", type="person")
        ]
        
        async def async_get_entity(entity_id):
            entity_map = {e.id: e for e in entities}
            return entity_map.get(entity_id)
        
        mock_graph.get_entity.side_effect = async_get_entity
        
        mock_llm.complete.return_value = json.dumps({
            "relationships": [
                {
                    "source": "Alice",
                    "target": "Bob",
                    "type": "manages",
                    "properties": {},
                    "confidence": 0.85
                }
            ]
        })
        
        mapping_request = AnalysisRequest(
            type=AnalysisType.RELATIONSHIP_MAPPING,
            parameters={"entity_ids": ["person_alice", "person_bob"]}
        )
        
        mapping_result = await engine.analyze(mapping_request)
        assert mapping_result.success is True
        assert len(mapping_result.data["relationships"]) == 1
    
    async def test_concurrent_strategy_execution(self):
        """Test concurrent execution of different analysis types."""
        from blackcore.intelligence.engine import AnalysisEngine
        from blackcore.intelligence.strategies import (
            EntityExtractionStrategy,
            CommunityDetectionStrategy,
            AnomalyDetectionStrategy
        )
        
        # Create mocks
        mock_llm = Mock(spec=ILLMProvider)
        mock_llm.complete = AsyncMock(return_value='{"entities": []}')
        
        mock_graph = Mock(spec=IGraphBackend)
        mock_graph.get_entities = AsyncMock(return_value=[
            Entity(id=f"e{i}", name=f"Entity{i}", type="entity")
            for i in range(10)
        ])
        mock_graph.get_relationships = AsyncMock(return_value=[])
        
        # Create engine
        engine = AnalysisEngine(
            llm_provider=mock_llm,
            graph_backend=mock_graph,
            strategies=[
                EntityExtractionStrategy(),
                CommunityDetectionStrategy(),
                AnomalyDetectionStrategy()
            ]
        )
        
        # Create different request types
        requests = [
            AnalysisRequest(
                type=AnalysisType.ENTITY_EXTRACTION,
                parameters={"text": "Test text"}
            ),
            AnalysisRequest(
                type=AnalysisType.COMMUNITY_DETECTION,
                parameters={"algorithm": "louvain"}
            ),
            AnalysisRequest(
                type=AnalysisType.ANOMALY_DETECTION,
                parameters={"method": "statistical"}
            )
        ]
        
        # Execute concurrently
        results = await engine.analyze_batch(requests)
        
        assert len(results) == 3
        assert all(isinstance(r, AnalysisResult) for r in results)


# Need to import json for the integration tests
import json