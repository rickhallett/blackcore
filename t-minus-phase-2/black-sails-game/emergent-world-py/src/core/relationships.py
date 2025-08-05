"""Hypergraph relationship system for complex multi-entity connections."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from neo4j import AsyncGraphDatabase, AsyncSession
from pydantic import BaseModel, Field

from .entity import Entity
from .events import Event, EventBus


class RelationshipType(str, Enum):
    """Common relationship types."""
    OWNS = "owns"
    MEMBER_OF = "member_of"
    LOCATED_AT = "located_at"
    KNOWS = "knows"
    TRUSTS = "trusts"
    TRADES_WITH = "trades_with"
    ALLIED_WITH = "allied_with"
    HOSTILE_TO = "hostile_to"
    DEPENDS_ON = "depends_on"
    INFLUENCES = "influences"
    CUSTOM = "custom"


class RelationshipStrength(str, Enum):
    """Relationship strength levels."""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class RelationshipProperties:
    """Properties for a relationship edge."""
    strength: RelationshipStrength = RelationshipStrength.MODERATE
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    def update(self, **kwargs) -> None:
        """Update properties."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.modified_at = time.time()


class HyperEdge:
    """Represents a hyperedge connecting multiple entities."""
    
    def __init__(
        self,
        edge_id: Optional[str] = None,
        relationship_type: RelationshipType = RelationshipType.CUSTOM,
        entities: Optional[Set[str]] = None,
        properties: Optional[RelationshipProperties] = None,
        directed: bool = False,
        ordered: bool = False
    ):
        self.id = edge_id or str(uuid.uuid4())
        self.relationship_type = relationship_type
        self.entities = entities or set()
        self.properties = properties or RelationshipProperties()
        self.directed = directed
        self.ordered = ordered
        
        # For directed hyperedges
        self.source_entities: Set[str] = set()
        self.target_entities: Set[str] = set()
        
        # For ordered hyperedges
        self.entity_order: List[str] = []
    
    def add_entity(self, entity_id: str, role: Optional[str] = None) -> None:
        """Add entity to hyperedge."""
        self.entities.add(entity_id)
        if role:
            self.properties.metadata[f"role:{entity_id}"] = role
    
    def remove_entity(self, entity_id: str) -> None:
        """Remove entity from hyperedge."""
        self.entities.discard(entity_id)
        self.source_entities.discard(entity_id)
        self.target_entities.discard(entity_id)
        if entity_id in self.entity_order:
            self.entity_order.remove(entity_id)
    
    def set_direction(self, sources: Set[str], targets: Set[str]) -> None:
        """Set direction for directed hyperedge."""
        if not self.directed:
            raise ValueError("Cannot set direction on undirected hyperedge")
        self.source_entities = sources
        self.target_entities = targets
        self.entities = sources | targets
    
    def set_order(self, order: List[str]) -> None:
        """Set entity order for ordered hyperedge."""
        if not self.ordered:
            raise ValueError("Cannot set order on unordered hyperedge")
        self.entity_order = order
        self.entities = set(order)
    
    def involves(self, entity_id: str) -> bool:
        """Check if entity is involved in this hyperedge."""
        return entity_id in self.entities
    
    def get_role(self, entity_id: str) -> Optional[str]:
        """Get role of entity in hyperedge."""
        return self.properties.metadata.get(f"role:{entity_id}")
    
    def __repr__(self) -> str:
        return f"HyperEdge({self.id[:8]}, {self.relationship_type.value}, {len(self.entities)} entities)"


class RelationshipGraph:
    """Hypergraph implementation for entity relationships."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.hyperedges: Dict[str, HyperEdge] = {}
        self.entity_edges: Dict[str, Set[str]] = {}  # entity_id -> edge_ids
        self.event_bus = event_bus
        
        # NetworkX graph for analysis
        self._nx_graph = nx.Graph()
        self._directed_graph = nx.DiGraph()
        
    def create_relationship(
        self,
        entities: Set[str],
        relationship_type: RelationshipType,
        properties: Optional[RelationshipProperties] = None,
        directed: bool = False,
        ordered: bool = False
    ) -> HyperEdge:
        """Create a new hyperedge relationship."""
        edge = HyperEdge(
            relationship_type=relationship_type,
            entities=entities,
            properties=properties,
            directed=directed,
            ordered=ordered
        )
        
        self.hyperedges[edge.id] = edge
        
        # Update indices
        for entity_id in entities:
            if entity_id not in self.entity_edges:
                self.entity_edges[entity_id] = set()
            self.entity_edges[entity_id].add(edge.id)
        
        # Update NetworkX graphs
        self._update_nx_graphs(edge)
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="relationship_created",
                data={
                    "edge_id": edge.id,
                    "type": relationship_type.value,
                    "entities": list(entities),
                    "directed": directed,
                    "ordered": ordered
                }
            ))
        
        return edge
    
    def create_binary_relationship(
        self,
        entity1: str,
        entity2: str,
        relationship_type: RelationshipType,
        properties: Optional[RelationshipProperties] = None,
        directed: bool = False
    ) -> HyperEdge:
        """Convenience method for binary relationships."""
        edge = self.create_relationship(
            entities={entity1, entity2},
            relationship_type=relationship_type,
            properties=properties,
            directed=directed
        )
        
        if directed:
            edge.set_direction({entity1}, {entity2})
        
        return edge
    
    def remove_relationship(self, edge_id: str) -> bool:
        """Remove a hyperedge."""
        edge = self.hyperedges.get(edge_id)
        if not edge:
            return False
        
        # Update indices
        for entity_id in edge.entities:
            if entity_id in self.entity_edges:
                self.entity_edges[entity_id].discard(edge_id)
        
        # Remove from graphs
        self._remove_from_nx_graphs(edge)
        
        del self.hyperedges[edge_id]
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="relationship_removed",
                data={"edge_id": edge_id}
            ))
        
        return True
    
    def get_relationships(
        self,
        entity_id: str,
        relationship_types: Optional[List[RelationshipType]] = None,
        include_indirect: bool = False
    ) -> List[HyperEdge]:
        """Get all relationships involving an entity."""
        edge_ids = self.entity_edges.get(entity_id, set())
        relationships = []
        
        for edge_id in edge_ids:
            edge = self.hyperedges.get(edge_id)
            if edge:
                if relationship_types and edge.relationship_type not in relationship_types:
                    continue
                relationships.append(edge)
        
        if include_indirect:
            # Find indirect relationships through shared hyperedges
            indirect = self._find_indirect_relationships(entity_id, relationships)
            relationships.extend(indirect)
        
        return relationships
    
    def get_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[RelationshipType]] = None,
        max_depth: int = 1
    ) -> Set[str]:
        """Get all entities related to a given entity."""
        if max_depth < 1:
            return set()
        
        related = set()
        visited_edges = set()
        
        def explore(eid: str, depth: int):
            if depth > max_depth:
                return
            
            edges = self.get_relationships(eid, relationship_types)
            for edge in edges:
                if edge.id in visited_edges:
                    continue
                visited_edges.add(edge.id)
                
                for other_id in edge.entities:
                    if other_id != eid:
                        related.add(other_id)
                        if depth < max_depth:
                            explore(other_id, depth + 1)
        
        explore(entity_id, 1)
        return related
    
    def find_path(
        self,
        start_entity: str,
        end_entity: str,
        relationship_types: Optional[List[RelationshipType]] = None
    ) -> Optional[List[str]]:
        """Find path between two entities."""
        try:
            # Use NetworkX for pathfinding
            if self._nx_graph.has_node(start_entity) and self._nx_graph.has_node(end_entity):
                path = nx.shortest_path(self._nx_graph, start_entity, end_entity)
                return path
        except nx.NetworkXNoPath:
            pass
        
        return None
    
    def get_clusters(self) -> List[Set[str]]:
        """Find entity clusters based on relationships."""
        if not self._nx_graph.nodes:
            return []
        
        # Find connected components
        components = list(nx.connected_components(self._nx_graph))
        return [set(component) for component in components]
    
    def calculate_centrality(self, entity_id: str) -> float:
        """Calculate centrality score for an entity."""
        if entity_id not in self._nx_graph:
            return 0.0
        
        # Use eigenvector centrality
        centrality = nx.eigenvector_centrality_numpy(self._nx_graph)
        return centrality.get(entity_id, 0.0)
    
    def _update_nx_graphs(self, edge: HyperEdge) -> None:
        """Update NetworkX graphs with new edge."""
        # For analysis, we create clique from hyperedge
        entities = list(edge.entities)
        weight = edge.properties.weight
        
        # Add nodes
        for entity in entities:
            if not self._nx_graph.has_node(entity):
                self._nx_graph.add_node(entity)
                self._directed_graph.add_node(entity)
        
        # Add edges (create clique for hyperedge)
        if len(entities) == 2:
            # Binary edge
            if edge.directed:
                if edge.source_entities:
                    source = list(edge.source_entities)[0]
                    target = list(edge.target_entities)[0]
                    self._directed_graph.add_edge(source, target, weight=weight, edge_id=edge.id)
                else:
                    self._directed_graph.add_edge(entities[0], entities[1], weight=weight, edge_id=edge.id)
            self._nx_graph.add_edge(entities[0], entities[1], weight=weight, edge_id=edge.id)
        else:
            # Hyperedge - create clique
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    self._nx_graph.add_edge(
                        entities[i], entities[j],
                        weight=weight,
                        edge_id=edge.id,
                        hyperedge=True
                    )
    
    def _remove_from_nx_graphs(self, edge: HyperEdge) -> None:
        """Remove edge from NetworkX graphs."""
        # Remove all edges with this edge_id
        edges_to_remove = []
        
        for u, v, data in self._nx_graph.edges(data=True):
            if data.get('edge_id') == edge.id:
                edges_to_remove.append((u, v))
        
        for u, v in edges_to_remove:
            self._nx_graph.remove_edge(u, v)
            if self._directed_graph.has_edge(u, v):
                self._directed_graph.remove_edge(u, v)
    
    def _find_indirect_relationships(
        self,
        entity_id: str,
        direct_relationships: List[HyperEdge]
    ) -> List[HyperEdge]:
        """Find indirect relationships through shared hyperedges."""
        indirect = []
        direct_edge_ids = {edge.id for edge in direct_relationships}
        
        # Find entities connected through direct relationships
        connected_entities = set()
        for edge in direct_relationships:
            connected_entities.update(edge.entities)
        connected_entities.discard(entity_id)
        
        # Find edges involving connected entities
        for connected_id in connected_entities:
            edges = self.entity_edges.get(connected_id, set())
            for edge_id in edges:
                if edge_id not in direct_edge_ids:
                    edge = self.hyperedges.get(edge_id)
                    if edge and not edge.involves(entity_id):
                        indirect.append(edge)
        
        return indirect
    
    async def persist_to_neo4j(self, session: AsyncSession) -> None:
        """Persist graph to Neo4j."""
        # Create entities as nodes
        for entity_id in self.entity_edges.keys():
            await session.run(
                "MERGE (e:Entity {id: $id})",
                id=entity_id
            )
        
        # Create relationships
        for edge in self.hyperedges.values():
            if len(edge.entities) == 2:
                # Binary relationship
                entities = list(edge.entities)
                await session.run(
                    f"""
                    MATCH (a:Entity {{id: $id1}})
                    MATCH (b:Entity {{id: $id2}})
                    MERGE (a)-[r:{edge.relationship_type.value}]->(b)
                    SET r.weight = $weight,
                        r.edge_id = $edge_id,
                        r.created_at = $created_at
                    """,
                    id1=entities[0],
                    id2=entities[1],
                    weight=edge.properties.weight,
                    edge_id=edge.id,
                    created_at=edge.properties.created_at
                )
            else:
                # Hyperedge - create HyperEdge node
                await session.run(
                    """
                    MERGE (h:HyperEdge {id: $edge_id})
                    SET h.type = $type,
                        h.weight = $weight,
                        h.created_at = $created_at
                    """,
                    edge_id=edge.id,
                    type=edge.relationship_type.value,
                    weight=edge.properties.weight,
                    created_at=edge.properties.created_at
                )
                
                # Connect entities to hyperedge
                for entity_id in edge.entities:
                    role = edge.get_role(entity_id)
                    await session.run(
                        """
                        MATCH (e:Entity {id: $entity_id})
                        MATCH (h:HyperEdge {id: $edge_id})
                        MERGE (e)-[r:PARTICIPATES_IN]->(h)
                        SET r.role = $role
                        """,
                        entity_id=entity_id,
                        edge_id=edge.id,
                        role=role
                    )
    
    async def load_from_neo4j(self, session: AsyncSession) -> None:
        """Load graph from Neo4j."""
        # Load binary relationships
        result = await session.run(
            """
            MATCH (a:Entity)-[r]->(b:Entity)
            WHERE type(r) <> 'PARTICIPATES_IN'
            RETURN a.id as source, b.id as target, type(r) as type,
                   r.weight as weight, r.edge_id as edge_id, r.created_at as created_at
            """
        )
        
        async for record in result:
            edge = HyperEdge(
                edge_id=record["edge_id"],
                relationship_type=RelationshipType(record["type"]),
                entities={record["source"], record["target"]},
                directed=True
            )
            edge.set_direction({record["source"]}, {record["target"]})
            edge.properties.weight = record["weight"] or 1.0
            edge.properties.created_at = record["created_at"] or time.time()
            
            self.hyperedges[edge.id] = edge
            self._update_indices(edge)
        
        # Load hyperedges
        result = await session.run(
            """
            MATCH (h:HyperEdge)
            MATCH (e:Entity)-[r:PARTICIPATES_IN]->(h)
            RETURN h.id as edge_id, h.type as type, h.weight as weight,
                   h.created_at as created_at, collect({id: e.id, role: r.role}) as entities
            """
        )
        
        async for record in result:
            entities = {e["id"] for e in record["entities"]}
            edge = HyperEdge(
                edge_id=record["edge_id"],
                relationship_type=RelationshipType(record["type"]),
                entities=entities
            )
            edge.properties.weight = record["weight"] or 1.0
            edge.properties.created_at = record["created_at"] or time.time()
            
            # Set roles
            for e in record["entities"]:
                if e["role"]:
                    edge.properties.metadata[f"role:{e['id']}"] = e["role"]
            
            self.hyperedges[edge.id] = edge
            self._update_indices(edge)
    
    def _update_indices(self, edge: HyperEdge) -> None:
        """Update internal indices."""
        for entity_id in edge.entities:
            if entity_id not in self.entity_edges:
                self.entity_edges[entity_id] = set()
            self.entity_edges[entity_id].add(edge.id)
        self._update_nx_graphs(edge)