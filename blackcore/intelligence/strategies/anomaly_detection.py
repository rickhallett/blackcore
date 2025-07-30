"""Anomaly detection strategy implementation."""

import json
import logging
import statistics
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict

from ..interfaces import (
    IAnalysisStrategy,
    ILLMProvider,
    IGraphBackend,
    AnalysisType,
    AnalysisRequest,
    AnalysisResult,
    Entity,
    Relationship
)

logger = logging.getLogger(__name__)


class AnomalyDetectionStrategy(IAnalysisStrategy):
    """Strategy for detecting anomalies in entity and relationship data."""
    
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if this strategy can handle the analysis type."""
        return analysis_type == AnalysisType.ANOMALY_DETECTION
    
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Detect anomalies in entity/relationship data."""
        start_time = datetime.now()
        
        try:
            # Extract parameters
            entity_type = request.parameters.get("entity_type")
            method = request.parameters.get("method", "statistical")
            threshold = request.parameters.get("threshold", 2.0)
            context_window = request.parameters.get("context_window", 100)
            metrics = request.parameters.get("metrics", ["degree"])
            
            # Detect based on method
            if method == "statistical":
                anomalies = await self._detect_statistical_anomalies(
                    graph, entity_type, threshold
                )
            elif method == "pattern":
                anomalies = await self._detect_pattern_anomalies(
                    graph, llm, entity_type, context_window
                )
            elif method == "graph":
                anomalies = await self._detect_graph_anomalies(
                    graph, metrics, threshold
                )
            else:
                # Default to statistical
                anomalies = await self._detect_statistical_anomalies(
                    graph, entity_type, threshold
                )
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare metadata
            metadata = {
                "method": method,
                "entity_type": entity_type,
                "anomalies_found": len(anomalies),
                "threshold": threshold
            }
            
            return AnalysisResult(
                request=request,
                success=True,
                data={"anomalies": anomalies},
                metadata=metadata,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return AnalysisResult(
                request=request,
                success=False,
                data=None,
                errors=[str(e)],
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _detect_statistical_anomalies(
        self,
        graph: IGraphBackend,
        entity_type: Optional[str],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect statistical anomalies in entity properties."""
        # Get entities
        entities = await graph.get_entities()
        
        # Filter by type if specified
        if entity_type:
            entities = [e for e in entities if e.type == entity_type]
        
        if not entities:
            return []
        
        # Analyze numeric properties
        anomalies = []
        
        # Get all numeric properties
        numeric_properties = defaultdict(list)
        for entity in entities:
            for prop_name, prop_value in entity.properties.items():
                if isinstance(prop_value, (int, float)):
                    numeric_properties[prop_name].append((entity, prop_value))
        
        # Detect outliers for each property
        for prop_name, entity_values in numeric_properties.items():
            if len(entity_values) < 3:
                continue
            
            values = [v for _, v in entity_values]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            if stdev == 0:
                continue
            
            # Find outliers
            for entity, value in entity_values:
                z_score = abs((value - mean) / stdev)
                if z_score > threshold:
                    anomalies.append({
                        "entity_id": entity.id,
                        "entity_name": entity.name,
                        "entity_type": entity.type,
                        "property": prop_name,
                        "value": value,
                        "z_score": z_score,
                        "mean": mean,
                        "stdev": stdev,
                        "type": "statistical_outlier"
                    })
        
        return anomalies
    
    async def _detect_pattern_anomalies(
        self,
        graph: IGraphBackend,
        llm: ILLMProvider,
        entity_type: Optional[str],
        context_window: int
    ) -> List[Dict[str, Any]]:
        """Detect pattern-based anomalies using LLM."""
        # Get entities
        entities = await graph.get_entities(limit=context_window)
        
        # Filter by type if specified
        if entity_type:
            entities = [e for e in entities if e.type == entity_type]
        
        if not entities:
            return []
        
        # Build prompt for pattern analysis
        prompt = self._build_pattern_prompt(entities)
        
        # Get LLM analysis
        response = await llm.complete(
            prompt=prompt,
            system_prompt=self._get_pattern_system_prompt(),
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        try:
            result = json.loads(response)
            return result.get("anomalies", [])
        except json.JSONDecodeError:
            logger.error("Failed to parse pattern anomaly response")
            return []
    
    async def _detect_graph_anomalies(
        self,
        graph: IGraphBackend,
        metrics: List[str],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect graph-based anomalies (unusual connectivity patterns)."""
        # Get entities and relationships
        entities = await graph.get_entities()
        relationships = await graph.get_relationships()
        
        if not entities:
            return []
        
        anomalies = []
        
        # Calculate graph metrics
        if "degree" in metrics:
            degree_anomalies = self._detect_degree_anomalies(
                entities, relationships, threshold
            )
            anomalies.extend(degree_anomalies)
        
        if "centrality" in metrics:
            centrality_anomalies = self._detect_centrality_anomalies(
                entities, relationships, threshold
            )
            anomalies.extend(centrality_anomalies)
        
        return anomalies
    
    def _detect_degree_anomalies(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect entities with anomalous degree (connectivity)."""
        # Calculate degree for each entity
        degree_map = defaultdict(int)
        
        for rel in relationships:
            degree_map[rel.source_id] += 1
            degree_map[rel.target_id] += 1
        
        # Ensure all entities are in the map
        entity_ids = {e.id for e in entities}
        for entity_id in entity_ids:
            if entity_id not in degree_map:
                degree_map[entity_id] = 0
        
        if len(degree_map) < 3:
            return []
        
        # Calculate statistics
        degrees = list(degree_map.values())
        mean_degree = statistics.mean(degrees)
        stdev_degree = statistics.stdev(degrees)
        
        if stdev_degree == 0:
            return []
        
        # Find anomalies
        anomalies = []
        entity_lookup = {e.id: e for e in entities}
        
        for entity_id, degree in degree_map.items():
            z_score = abs((degree - mean_degree) / stdev_degree)
            if z_score > threshold:
                entity = entity_lookup.get(entity_id)
                if entity:
                    anomalies.append({
                        "entity_id": entity_id,
                        "entity_name": entity.name,
                        "entity_type": entity.type,
                        "metric": "degree",
                        "value": degree,
                        "z_score": z_score,
                        "mean": mean_degree,
                        "stdev": stdev_degree,
                        "type": "graph_anomaly"
                    })
        
        return anomalies
    
    def _detect_centrality_anomalies(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect entities with anomalous centrality."""
        # Simple betweenness centrality approximation
        # Count how many shortest paths go through each node
        
        # Build adjacency for path finding
        adjacency = defaultdict(set)
        for rel in relationships:
            adjacency[rel.source_id].add(rel.target_id)
            adjacency[rel.target_id].add(rel.source_id)
        
        # Calculate betweenness (simplified)
        betweenness = defaultdict(int)
        entity_ids = [e.id for e in entities]
        
        # Sample pairs for efficiency
        import random
        sample_size = min(len(entity_ids), 20)
        sampled_ids = random.sample(entity_ids, sample_size)
        
        for i, source in enumerate(sampled_ids):
            for target in sampled_ids[i+1:]:
                if source != target:
                    # Find shortest path
                    path = self._bfs_shortest_path(source, target, adjacency)
                    if path and len(path) > 2:
                        # Count intermediate nodes
                        for node in path[1:-1]:
                            betweenness[node] += 1
        
        if not betweenness or len(betweenness) < 3:
            return []
        
        # Normalize and detect anomalies
        values = list(betweenness.values())
        mean_between = statistics.mean(values)
        stdev_between = statistics.stdev(values) if len(values) > 1 else 1
        
        if stdev_between == 0:
            return []
        
        anomalies = []
        entity_lookup = {e.id: e for e in entities}
        
        for entity_id, between_value in betweenness.items():
            z_score = abs((between_value - mean_between) / stdev_between)
            if z_score > threshold:
                entity = entity_lookup.get(entity_id)
                if entity:
                    anomalies.append({
                        "entity_id": entity_id,
                        "entity_name": entity.name,
                        "entity_type": entity.type,
                        "metric": "betweenness_centrality",
                        "value": between_value,
                        "z_score": z_score,
                        "type": "graph_anomaly"
                    })
        
        return anomalies
    
    def _bfs_shortest_path(
        self,
        source: str,
        target: str,
        adjacency: Dict[str, Set[str]]
    ) -> Optional[List[str]]:
        """Find shortest path using BFS."""
        if source == target:
            return [source]
        
        visited = {source}
        queue = [(source, [source])]
        
        while queue:
            node, path = queue.pop(0)
            
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    
                    if neighbor == target:
                        return new_path
                    
                    queue.append((neighbor, new_path))
        
        return None
    
    def _build_pattern_prompt(self, entities: List[Entity]) -> str:
        """Build prompt for pattern anomaly detection."""
        entities_info = []
        for entity in entities[:50]:  # Limit for prompt size
            info = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "properties": entity.properties
            }
            entities_info.append(json.dumps(info))
        
        return f"""Analyze the following entities and identify any that exhibit anomalous patterns:

Entities:
{chr(10).join(entities_info)}

Look for:
- Entities with unusual property combinations
- Behavioral anomalies based on entity type
- Entities that don't fit expected patterns
- Suspicious or outlier characteristics

For each anomaly found, provide:
- entity_id: The ID of the anomalous entity
- type: The type of anomaly (e.g., "behavioral", "property_mismatch", "suspicious_pattern")
- description: A clear description of why this is anomalous
- confidence: Confidence score (0-1)

Return the result as a JSON object with an "anomalies" array."""
    
    def _get_pattern_system_prompt(self) -> str:
        """Get system prompt for pattern anomaly detection."""
        return """You are an expert at detecting anomalies and unusual patterns in data.
Focus on identifying entities that deviate from normal patterns or expected behavior.
Be thorough but avoid false positives - only flag clear anomalies.
Consider the context and entity type when determining what constitutes normal behavior."""