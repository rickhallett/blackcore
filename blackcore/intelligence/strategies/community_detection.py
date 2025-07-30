"""Community detection strategy implementation."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import uuid

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


class CommunityDetectionStrategy(IAnalysisStrategy):
    """Strategy for detecting communities in entity networks."""
    
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if this strategy can handle the analysis type."""
        return analysis_type == AnalysisType.COMMUNITY_DETECTION
    
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Detect communities in the entity graph."""
        start_time = datetime.now()
        
        try:
            # Extract parameters
            algorithm = request.parameters.get("algorithm", "louvain")
            use_weights = request.parameters.get("use_weights", False)
            weight_property = request.parameters.get("weight_property", "weight")
            max_levels = request.parameters.get("max_levels", 3)
            
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
            
            # Build adjacency structure
            adjacency = self._build_adjacency(entities, relationships, use_weights, weight_property)
            
            # Detect communities based on algorithm
            if algorithm == "louvain":
                communities = self._louvain_communities(adjacency)
            elif algorithm == "hierarchical":
                result_data = self._hierarchical_communities(adjacency, max_levels)
                # For hierarchical, return the full hierarchy
                return AnalysisResult(
                    request=request,
                    success=True,
                    data=result_data,
                    metadata={
                        "algorithm": algorithm,
                        "num_entities": len(entities),
                        "num_relationships": len(relationships)
                    },
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            else:
                # Simple connected components as fallback
                communities = self._connected_components(adjacency)
            
            # Build result
            community_data = []
            entity_lookup = {e.id: e for e in entities}
            
            for community_id, member_ids in communities.items():
                members = []
                for member_id in member_ids:
                    if member_id in entity_lookup:
                        entity = entity_lookup[member_id]
                        members.append({
                            "id": entity.id,
                            "name": entity.name,
                            "type": entity.type
                        })
                
                community_data.append({
                    "id": community_id,
                    "members": members,
                    "size": len(members),
                    "density": self._calculate_density(member_ids, adjacency)
                })
            
            # Sort by size
            community_data.sort(key=lambda x: x["size"], reverse=True)
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare metadata
            metadata = {
                "algorithm": algorithm,
                "num_communities": len(community_data),
                "num_entities": len(entities),
                "num_relationships": len(relationships),
                "modularity": self._calculate_modularity(communities, adjacency)
            }
            
            return AnalysisResult(
                request=request,
                success=True,
                data={"communities": community_data},
                metadata=metadata,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return AnalysisResult(
                request=request,
                success=False,
                data=None,
                errors=[str(e)],
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _build_adjacency(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        use_weights: bool,
        weight_property: str
    ) -> Dict[str, Dict[str, float]]:
        """Build adjacency structure from entities and relationships."""
        adjacency = defaultdict(dict)
        
        for rel in relationships:
            weight = 1.0
            if use_weights and weight_property in rel.properties:
                weight = float(rel.properties[weight_property])
            
            # Undirected graph for community detection
            adjacency[rel.source_id][rel.target_id] = weight
            adjacency[rel.target_id][rel.source_id] = weight
        
        # Ensure all entities are in adjacency
        for entity in entities:
            if entity.id not in adjacency:
                adjacency[entity.id] = {}
        
        return dict(adjacency)
    
    def _louvain_communities(
        self,
        adjacency: Dict[str, Dict[str, float]]
    ) -> Dict[str, Set[str]]:
        """Simplified Louvain algorithm for community detection."""
        # Initialize each node in its own community
        node_community = {node: node for node in adjacency}
        
        # Iterate until no improvement (with max iterations to prevent infinite loops)
        improved = True
        max_iterations = 100
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for node in adjacency:
                current_community = node_community[node]
                
                # Calculate modularity gain for each neighbor's community
                neighbor_communities = set()
                for neighbor in adjacency[node]:
                    neighbor_communities.add(node_community[neighbor])
                
                best_community = current_community
                best_gain = 0
                
                for community in neighbor_communities:
                    if community != current_community:
                        gain = self._modularity_gain(node, community, adjacency, node_community)
                        if gain > best_gain:
                            best_gain = gain
                            best_community = community
                
                if best_community != current_community:
                    node_community[node] = best_community
                    improved = True
        
        # Group nodes by community
        communities = defaultdict(set)
        for node, community in node_community.items():
            communities[community].add(node)
        
        # Renumber communities
        final_communities = {}
        for i, (_, members) in enumerate(communities.items()):
            final_communities[f"community_{i}"] = members
        
        return final_communities
    
    def _hierarchical_communities(
        self,
        adjacency: Dict[str, Dict[str, float]],
        max_levels: int
    ) -> Dict[str, Any]:
        """Hierarchical community detection."""
        levels = []
        current_adjacency = adjacency.copy()
        
        for level in range(max_levels):
            # Detect communities at this level
            communities = self._louvain_communities(current_adjacency)
            
            if len(communities) == 1:
                # All nodes in one community, stop
                break
            
            levels.append({
                "level": level,
                "communities": [
                    {
                        "id": comm_id,
                        "members": list(members),
                        "size": len(members)
                    }
                    for comm_id, members in communities.items()
                ]
            })
            
            # Build super-graph for next level
            if level < max_levels - 1:
                current_adjacency = self._build_super_graph(communities, adjacency)
                if len(current_adjacency) <= 1:
                    break
        
        return {
            "hierarchy": {
                "levels": levels,
                "num_levels": len(levels)
            }
        }
    
    def _connected_components(
        self,
        adjacency: Dict[str, Dict[str, float]]
    ) -> Dict[str, Set[str]]:
        """Find connected components as simple communities."""
        visited = set()
        communities = {}
        community_id = 0
        
        for node in adjacency:
            if node not in visited:
                # BFS to find component
                component = set()
                queue = [node]
                
                while queue:
                    current = queue.pop(0)
                    if current not in visited:
                        visited.add(current)
                        component.add(current)
                        
                        for neighbor in adjacency[current]:
                            if neighbor not in visited:
                                queue.append(neighbor)
                
                communities[f"community_{community_id}"] = component
                community_id += 1
        
        return communities
    
    def _calculate_density(
        self,
        member_ids: Set[str],
        adjacency: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate density of a community."""
        if len(member_ids) <= 1:
            return 1.0
        
        internal_edges = 0
        for node in member_ids:
            for neighbor in adjacency.get(node, {}):
                if neighbor in member_ids:
                    internal_edges += 1
        
        # Divide by 2 for undirected graph
        internal_edges //= 2
        
        max_edges = len(member_ids) * (len(member_ids) - 1) / 2
        return internal_edges / max_edges if max_edges > 0 else 0
    
    def _calculate_modularity(
        self,
        communities: Dict[str, Set[str]],
        adjacency: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate modularity of community partition."""
        # Simplified modularity calculation
        total_weight = sum(
            sum(weights.values())
            for weights in adjacency.values()
        ) / 2  # Divide by 2 for undirected
        
        if total_weight == 0:
            return 0
        
        modularity = 0
        node_community = {}
        for comm_id, members in communities.items():
            for member in members:
                node_community[member] = comm_id
        
        for node in adjacency:
            for neighbor, weight in adjacency[node].items():
                if node_community.get(node) == node_community.get(neighbor):
                    # Same community
                    node_degree = sum(adjacency[node].values())
                    neighbor_degree = sum(adjacency[neighbor].values())
                    expected = (node_degree * neighbor_degree) / (2 * total_weight)
                    modularity += (weight - expected) / (2 * total_weight)
        
        return modularity
    
    def _modularity_gain(
        self,
        node: str,
        target_community: str,
        adjacency: Dict[str, Dict[str, float]],
        node_community: Dict[str, str]
    ) -> float:
        """Calculate modularity gain from moving node to target community."""
        # Simplified calculation
        internal_weight = 0
        for neighbor, weight in adjacency[node].items():
            if node_community[neighbor] == target_community:
                internal_weight += weight
        
        node_degree = sum(adjacency[node].values())
        community_degree = sum(
            sum(adjacency[n].values())
            for n, c in node_community.items()
            if c == target_community
        )
        
        total_weight = sum(
            sum(weights.values())
            for weights in adjacency.values()
        ) / 2
        
        if total_weight == 0:
            return 0
        
        return (internal_weight / total_weight) - (node_degree * community_degree / (2 * total_weight ** 2))
    
    def _build_super_graph(
        self,
        communities: Dict[str, Set[str]],
        original_adjacency: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """Build super-graph where communities become nodes."""
        super_adjacency = defaultdict(dict)
        
        # Map nodes to communities
        node_to_community = {}
        for comm_id, members in communities.items():
            for member in members:
                node_to_community[member] = comm_id
        
        # Aggregate edges between communities
        for node, neighbors in original_adjacency.items():
            node_comm = node_to_community[node]
            
            for neighbor, weight in neighbors.items():
                neighbor_comm = node_to_community[neighbor]
                
                if node_comm != neighbor_comm:
                    if neighbor_comm not in super_adjacency[node_comm]:
                        super_adjacency[node_comm][neighbor_comm] = 0
                    super_adjacency[node_comm][neighbor_comm] += weight
        
        return dict(super_adjacency)