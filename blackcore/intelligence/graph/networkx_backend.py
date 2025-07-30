"""NetworkX-based graph backend implementation."""

import json
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime

try:
    import networkx as nx
except ImportError:
    nx = None

from ..interfaces import IGraphBackend, Entity, Relationship

logger = logging.getLogger(__name__)


class NetworkXBackend(IGraphBackend):
    """NetworkX-based in-memory graph backend."""
    
    def __init__(self):
        if nx is None:
            raise ImportError("networkx is required for NetworkXBackend")
        
        self.graph = nx.DiGraph()
    
    async def add_entity(self, entity: Entity) -> bool:
        """Add entity to graph."""
        try:
            # Store entity data as node attributes
            self.graph.add_node(
                entity.id,
                name=entity.name,
                type=entity.type,
                properties=entity.properties,
                confidence=entity.confidence,
                source=entity.source,
                timestamp=entity.timestamp.isoformat()
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add entity {entity.id}: {e}")
            return False
    
    async def add_relationship(self, relationship: Relationship) -> bool:
        """Add relationship to graph."""
        try:
            # Ensure both entities exist
            if not self.graph.has_node(relationship.source_id):
                logger.warning(f"Source entity {relationship.source_id} not found")
                return False
            
            if not self.graph.has_node(relationship.target_id):
                logger.warning(f"Target entity {relationship.target_id} not found")
                return False
            
            # Add edge with relationship data
            self.graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                type=relationship.type,
                properties=relationship.properties,
                confidence=relationship.confidence,
                timestamp=relationship.timestamp.isoformat()
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            return False
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        if not self.graph.has_node(entity_id):
            return None
        
        try:
            node_data = self.graph.nodes[entity_id]
            return Entity(
                id=entity_id,
                name=node_data["name"],
                type=node_data["type"],
                properties=node_data.get("properties", {}),
                confidence=node_data.get("confidence", 1.0),
                source=node_data.get("source")
            )
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None
    
    async def get_neighbors(
        self, 
        entity_id: str, 
        relationship_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Entity]:
        """Get neighboring entities."""
        if not self.graph.has_node(entity_id):
            return []
        
        neighbors = []
        neighbor_ids = set()
        
        try:
            # Get outgoing neighbors
            if direction in ["out", "both"]:
                for neighbor_id in self.graph.successors(entity_id):
                    # Check relationship type if specified
                    if relationship_type:
                        edge_data = self.graph[entity_id][neighbor_id]
                        if edge_data.get("type") != relationship_type:
                            continue
                    neighbor_ids.add(neighbor_id)
            
            # Get incoming neighbors
            if direction in ["in", "both"]:
                for neighbor_id in self.graph.predecessors(entity_id):
                    # Check relationship type if specified
                    if relationship_type:
                        edge_data = self.graph[neighbor_id][entity_id]
                        if edge_data.get("type") != relationship_type:
                            continue
                    neighbor_ids.add(neighbor_id)
            
            # Convert to Entity objects
            for neighbor_id in neighbor_ids:
                entity = await self.get_entity(neighbor_id)
                if entity:
                    neighbors.append(entity)
            
            return neighbors
            
        except Exception as e:
            logger.error(f"Failed to get neighbors for {entity_id}: {e}")
            return []
    
    async def find_path(
        self, 
        from_id: str, 
        to_id: str,
        max_length: Optional[int] = None
    ) -> Optional[List[Entity]]:
        """Find shortest path between entities."""
        if not self.graph.has_node(from_id) or not self.graph.has_node(to_id):
            return None
        
        try:
            # Find shortest path
            if max_length:
                path_ids = nx.shortest_path(
                    self.graph, from_id, to_id, 
                    weight=None, method='dijkstra'
                )
                if len(path_ids) > max_length:
                    return None
            else:
                path_ids = nx.shortest_path(self.graph, from_id, to_id)
            
            # Convert to entities
            path = []
            for node_id in path_ids:
                entity = await self.get_entity(node_id)
                if entity:
                    path.append(entity)
            
            return path
            
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.error(f"Failed to find path from {from_id} to {to_id}: {e}")
            return None
    
    async def search_entities(self, criteria: Dict[str, Any]) -> List[Entity]:
        """Search entities by criteria."""
        results = []
        
        try:
            for node_id, node_data in self.graph.nodes(data=True):
                match = True
                
                for key, value in criteria.items():
                    # Handle nested property search
                    if key.startswith("properties."):
                        prop_key = key[11:]  # Remove "properties." prefix
                        if node_data.get("properties", {}).get(prop_key) != value:
                            match = False
                            break
                    # Direct attribute search
                    elif node_data.get(key) != value:
                        match = False
                        break
                
                if match:
                    entity = await self.get_entity(node_id)
                    if entity:
                        results.append(entity)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search entities: {e}")
            return []
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and its relationships."""
        if not self.graph.has_node(entity_id):
            return False
        
        try:
            self.graph.remove_node(entity_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            return False
    
    async def save(self, path: str) -> bool:
        """Save graph to file."""
        try:
            # Save as GraphML format
            nx.write_graphml(self.graph, path)
            return True
        except Exception as e:
            logger.error(f"Failed to save graph to {path}: {e}")
            return False
    
    async def load(self, path: str) -> bool:
        """Load graph from file."""
        try:
            # Load from GraphML format
            self.graph = nx.read_graphml(path)
            return True
        except Exception as e:
            logger.error(f"Failed to load graph from {path}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all data."""
        try:
            self.graph.clear()
            return True
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            return False
    
    async def close(self):
        """Close backend (no-op for NetworkX)."""
        pass
    
    async def get_entities(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Get entities with optional filters."""
        if filters:
            # Use search_entities for filtered results
            results = await self.search_entities(filters)
        else:
            # Return all entities
            results = []
            for node_id in self.graph.nodes():
                entity = await self.get_entity(node_id)
                if entity:
                    results.append(entity)
        
        # Apply limit if specified
        if limit and len(results) > limit:
            results = results[:limit]
        
        return results
    
    async def get_relationships(
        self,
        entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Relationship]:
        """Get relationships with optional filters."""
        relationships = []
        
        try:
            edges = []
            
            if entity_id:
                # Get edges connected to specific entity
                edges.extend((entity_id, target) for target in self.graph.successors(entity_id))
                edges.extend((source, entity_id) for source in self.graph.predecessors(entity_id))
            else:
                # Get all edges
                edges = list(self.graph.edges())
            
            # Convert edges to relationships
            for from_id, to_id in edges:
                edge_data = self.graph[from_id][to_id]
                
                # Filter by type if specified
                if relationship_type and edge_data.get("type") != relationship_type:
                    continue
                
                rel = Relationship(
                    id=f"{from_id}_{to_id}_{edge_data.get('type', 'unknown')}",
                    source_id=from_id,
                    target_id=to_id,
                    type=edge_data.get("type", "unknown"),
                    properties=edge_data.get("properties", {}),
                    confidence=edge_data.get("confidence", 1.0),
                    timestamp=datetime.fromisoformat(edge_data.get("timestamp", datetime.now().isoformat()))
                )
                relationships.append(rel)
                
                # Apply limit if specified
                if limit and len(relationships) >= limit:
                    break
            
            return relationships
            
        except Exception as e:
            logger.error(f"Failed to get relationships: {e}")
            return []
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute graph query (not implemented for NetworkX)."""
        logger.warning("Query execution not supported for NetworkX backend")
        return []
    
    async def get_subgraph(
        self,
        entity_ids: List[str],
        max_depth: int = 1
    ) -> Dict[str, List[Any]]:
        """Get subgraph around entities."""
        result = {"entities": [], "relationships": []}
        visited_entities = set()
        visited_edges = set()
        
        try:
            # BFS to explore subgraph
            queue = [(entity_id, 0) for entity_id in entity_ids if self.graph.has_node(entity_id)]
            
            while queue:
                current_id, depth = queue.pop(0)
                
                if current_id in visited_entities:
                    continue
                
                visited_entities.add(current_id)
                
                # Add entity
                entity = await self.get_entity(current_id)
                if entity:
                    result["entities"].append(entity)
                
                # Explore neighbors if within depth
                if depth < max_depth:
                    # Outgoing edges
                    for neighbor_id in self.graph.successors(current_id):
                        edge_key = (current_id, neighbor_id)
                        if edge_key not in visited_edges:
                            visited_edges.add(edge_key)
                            
                            # Add relationship
                            edge_data = self.graph[current_id][neighbor_id]
                            rel = Relationship(
                                id=f"{current_id}_{neighbor_id}_{edge_data.get('type', 'unknown')}",
                                source_id=current_id,
                                target_id=neighbor_id,
                                type=edge_data.get("type", "unknown"),
                                properties=edge_data.get("properties", {}),
                                confidence=edge_data.get("confidence", 1.0)
                            )
                            result["relationships"].append(rel)
                        
                        if neighbor_id not in visited_entities:
                            queue.append((neighbor_id, depth + 1))
                    
                    # Incoming edges
                    for neighbor_id in self.graph.predecessors(current_id):
                        edge_key = (neighbor_id, current_id)
                        if edge_key not in visited_edges:
                            visited_edges.add(edge_key)
                            
                            # Add relationship
                            edge_data = self.graph[neighbor_id][current_id]
                            rel = Relationship(
                                id=f"{neighbor_id}_{current_id}_{edge_data.get('type', 'unknown')}",
                                source_id=neighbor_id,
                                target_id=current_id,
                                type=edge_data.get("type", "unknown"),
                                properties=edge_data.get("properties", {}),
                                confidence=edge_data.get("confidence", 1.0)
                            )
                            result["relationships"].append(rel)
                        
                        if neighbor_id not in visited_entities:
                            queue.append((neighbor_id, depth + 1))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get subgraph: {e}")
            return {"entities": [], "relationships": []}