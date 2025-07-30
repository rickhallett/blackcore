"""Centrality analysis strategy implementation."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict, deque

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


class CentralityAnalysisStrategy(IAnalysisStrategy):
    """Strategy for analyzing entity centrality in the graph."""
    
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if this strategy can handle the analysis type."""
        return analysis_type == AnalysisType.CENTRALITY_ANALYSIS
    
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Analyze centrality of entities in the graph."""
        start_time = datetime.now()
        
        try:
            # Extract parameters
            metrics = request.parameters.get("metrics", ["degree"])
            normalize = request.parameters.get("normalize", False)
            directed = request.parameters.get("directed", True)
            identify_key_players = request.parameters.get("identify_key_players", False)
            top_k = request.parameters.get("top_k", 10)
            
            # Get entities and relationships
            entities = await graph.get_entities()
            relationships = await graph.get_relationships()
            
            if not entities:
                return AnalysisResult(
                    request=request,
                    success=False,
                    data=None,
                    errors=["No entities found in graph"]
                )
            
            # Calculate centrality scores
            centrality_scores = []
            entity_lookup = {e.id: e for e in entities}
            
            # Calculate requested metrics
            scores_by_entity = defaultdict(dict)
            
            if "degree" in metrics:
                degree_scores = self._calculate_degree_centrality(
                    entities, relationships, directed, normalize
                )
                for entity_id, score in degree_scores.items():
                    scores_by_entity[entity_id]["degree"] = score
            
            if "betweenness" in metrics:
                betweenness_scores = self._calculate_betweenness_centrality(
                    entities, relationships, directed, normalize
                )
                for entity_id, score in betweenness_scores.items():
                    scores_by_entity[entity_id]["betweenness"] = score
            
            if "closeness" in metrics:
                closeness_scores = self._calculate_closeness_centrality(
                    entities, relationships, directed, normalize
                )
                for entity_id, score in closeness_scores.items():
                    scores_by_entity[entity_id]["closeness"] = score
            
            # Format scores
            for entity_id, scores in scores_by_entity.items():
                entity = entity_lookup.get(entity_id)
                if entity:
                    score_entry = {
                        "entity_id": entity_id,
                        "entity_name": entity.name,
                        "entity_type": entity.type,
                        **scores
                    }
                    centrality_scores.append(score_entry)
            
            # Sort by first metric
            if centrality_scores and metrics:
                centrality_scores.sort(
                    key=lambda x: x.get(metrics[0], 0),
                    reverse=True
                )
            
            # Prepare result data
            data = {"centrality_scores": centrality_scores}
            
            # Identify key players if requested
            if identify_key_players:
                key_players = self._identify_key_players(
                    centrality_scores, metrics, top_k
                )
                data["key_players"] = key_players
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare metadata
            metadata = {
                "metrics": metrics,
                "num_entities": len(entities),
                "num_relationships": len(relationships),
                "normalized": normalize,
                "directed": directed
            }
            
            return AnalysisResult(
                request=request,
                success=True,
                data=data,
                metadata=metadata,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Centrality analysis failed: {e}")
            return AnalysisResult(
                request=request,
                success=False,
                data=None,
                errors=[str(e)],
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _calculate_degree_centrality(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        directed: bool,
        normalize: bool
    ) -> Dict[str, float]:
        """Calculate degree centrality for each entity."""
        if directed:
            in_degree = defaultdict(int)
            out_degree = defaultdict(int)
            
            for rel in relationships:
                out_degree[rel.source_id] += 1
                in_degree[rel.target_id] += 1
            
            # Total degree
            degree = {}
            entity_ids = {e.id for e in entities}
            
            for entity_id in entity_ids:
                degree[entity_id] = in_degree[entity_id] + out_degree[entity_id]
        else:
            degree = defaultdict(int)
            
            for rel in relationships:
                degree[rel.source_id] += 1
                degree[rel.target_id] += 1
        
        # Ensure all entities have a score
        entity_ids = {e.id for e in entities}
        for entity_id in entity_ids:
            if entity_id not in degree:
                degree[entity_id] = 0
        
        # Normalize if requested
        if normalize and len(entities) > 1:
            max_possible = 2 * (len(entities) - 1) if directed else (len(entities) - 1)
            for entity_id in degree:
                degree[entity_id] = degree[entity_id] / max_possible
        
        return dict(degree)
    
    def _calculate_betweenness_centrality(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        directed: bool,
        normalize: bool
    ) -> Dict[str, float]:
        """Calculate betweenness centrality using Brandes algorithm (simplified)."""
        # Build adjacency
        adjacency = defaultdict(set)
        
        if directed:
            for rel in relationships:
                adjacency[rel.source_id].add(rel.target_id)
        else:
            for rel in relationships:
                adjacency[rel.source_id].add(rel.target_id)
                adjacency[rel.target_id].add(rel.source_id)
        
        # Initialize betweenness
        betweenness = defaultdict(float)
        entity_ids = [e.id for e in entities]
        
        # Simplified Brandes algorithm
        for source in entity_ids:
            # BFS from source
            stack = []
            pred = defaultdict(list)
            sigma = defaultdict(int)
            sigma[source] = 1
            dist = {source: 0}
            queue = deque([source])
            
            while queue:
                v = queue.popleft()
                stack.append(v)
                
                for w in adjacency[v]:
                    # First time we reach w?
                    if w not in dist:
                        dist[w] = dist[v] + 1
                        queue.append(w)
                    
                    # Shortest path to w via v?
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        pred[w].append(v)
            
            # Accumulate betweenness
            delta = defaultdict(float)
            while stack:
                w = stack.pop()
                for v in pred[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
                if w != source:
                    betweenness[w] += delta[w]
        
        # Normalize if requested
        if normalize and len(entities) > 2:
            # Normalization factor
            if directed:
                norm = 1.0 / ((len(entities) - 1) * (len(entities) - 2))
            else:
                norm = 0.5 / ((len(entities) - 1) * (len(entities) - 2))
            
            for entity_id in betweenness:
                betweenness[entity_id] *= norm
        
        # Ensure all entities have a score
        for entity_id in entity_ids:
            if entity_id not in betweenness:
                betweenness[entity_id] = 0.0
        
        return dict(betweenness)
    
    def _calculate_closeness_centrality(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        directed: bool,
        normalize: bool
    ) -> Dict[str, float]:
        """Calculate closeness centrality."""
        # Build adjacency
        adjacency = defaultdict(set)
        
        if directed:
            for rel in relationships:
                adjacency[rel.source_id].add(rel.target_id)
        else:
            for rel in relationships:
                adjacency[rel.source_id].add(rel.target_id)
                adjacency[rel.target_id].add(rel.source_id)
        
        closeness = {}
        entity_ids = [e.id for e in entities]
        
        for source in entity_ids:
            # BFS to find distances
            distances = self._bfs_distances(source, adjacency, entity_ids)
            
            # Calculate closeness
            total_distance = sum(distances.values())
            reachable = len([d for d in distances.values() if d > 0])
            
            if total_distance > 0:
                closeness[source] = reachable / total_distance
                
                if normalize and len(entities) > 1:
                    closeness[source] *= (reachable / (len(entities) - 1))
            else:
                closeness[source] = 0.0
        
        return closeness
    
    def _bfs_distances(
        self,
        source: str,
        adjacency: Dict[str, Set[str]],
        all_nodes: List[str]
    ) -> Dict[str, int]:
        """Calculate distances from source to all other nodes using BFS."""
        distances = {source: 0}
        queue = deque([source])
        
        while queue:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                if neighbor not in distances:
                    distances[neighbor] = distances[node] + 1
                    queue.append(neighbor)
        
        # Set unreachable nodes to max distance
        for node in all_nodes:
            if node not in distances:
                distances[node] = len(all_nodes)  # Max possible distance
        
        return distances
    
    def _identify_key_players(
        self,
        centrality_scores: List[Dict[str, Any]],
        metrics: List[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Identify key players based on centrality scores."""
        if not centrality_scores or not metrics:
            return []
        
        # Calculate composite score
        for score_entry in centrality_scores:
            composite = 0
            for metric in metrics:
                if metric in score_entry:
                    composite += score_entry[metric]
            score_entry["composite_score"] = composite / len(metrics)
        
        # Sort by composite score
        sorted_scores = sorted(
            centrality_scores,
            key=lambda x: x["composite_score"],
            reverse=True
        )
        
        # Return top k
        key_players = []
        for i, score_entry in enumerate(sorted_scores[:top_k]):
            key_player = {
                "rank": i + 1,
                "entity_id": score_entry["entity_id"],
                "entity_name": score_entry["entity_name"],
                "entity_type": score_entry["entity_type"],
                "composite_score": score_entry["composite_score"]
            }
            
            # Add individual metric scores
            for metric in metrics:
                if metric in score_entry:
                    key_player[f"{metric}_score"] = score_entry[metric]
            
            key_players.append(key_player)
        
        return key_players