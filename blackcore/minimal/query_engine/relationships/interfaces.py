"""Relationship resolution module interfaces for the query engine.

This module defines the protocols and data structures for resolving entity relationships.
"""

from typing import List, Dict, Any, Optional, Protocol, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum


class RelationshipDirection(Enum):
    """Direction of relationship traversal."""
    FORWARD = "forward"      # From source to target
    BACKWARD = "backward"    # From target to source
    BOTH = "both"           # Bidirectional


class TraversalStrategy(Enum):
    """Strategy for traversing relationships."""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    SHORTEST_PATH = "shortest_path"
    ALL_PATHS = "all_paths"


@dataclass
class RelationshipInclude:
    """Specification for including related entities."""
    field_name: str
    database_id: Optional[str] = None
    max_depth: int = 1
    direction: RelationshipDirection = RelationshipDirection.FORWARD
    filters: Dict[str, Any] = field(default_factory=dict)
    fields_to_include: Optional[List[str]] = None
    recursive: bool = False


@dataclass
class RelationshipConfig:
    """Configuration for relationship resolution."""
    max_depth: int = 3
    max_entities: int = 1000
    strategy: TraversalStrategy = TraversalStrategy.BREADTH_FIRST
    detect_cycles: bool = True
    cache_enabled: bool = True
    parallel_loading: bool = True
    batch_size: int = 50


@dataclass
class RelationshipPath:
    """Represents a path between entities."""
    nodes: List[str]  # Entity IDs
    edges: List[Tuple[str, str, str]]  # (from_id, to_id, relationship_type)
    
    @property
    def length(self) -> int:
        """Length of the path."""
        return len(self.edges)
    
    def contains_cycle(self) -> bool:
        """Check if path contains a cycle."""
        return len(set(self.nodes)) < len(self.nodes)


@dataclass
class RelationshipGraph:
    """Graph representation of entity relationships."""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)
    adjacency_list: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    
    def add_node(self, entity: Dict[str, Any]) -> None:
        """Add entity node to graph."""
        self.nodes[entity['id']] = entity
        if entity['id'] not in self.adjacency_list:
            self.adjacency_list[entity['id']] = []
    
    def add_edge(self, from_id: str, to_id: str, relationship_type: str) -> None:
        """Add relationship edge to graph."""
        self.edges.append((from_id, to_id, relationship_type))
        self.adjacency_list.setdefault(from_id, []).append((to_id, relationship_type))
    
    def get_neighbors(self, entity_id: str) -> List[Tuple[str, str]]:
        """Get neighboring entities."""
        return self.adjacency_list.get(entity_id, [])
    
    def has_cycle(self) -> bool:
        """Detect if graph contains cycles."""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor, _ in self.get_neighbors(node):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False


class DataLoader(Protocol):
    """Protocol for loading entity data."""
    
    def load_entity(self, entity_id: str, database_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load a single entity by ID.
        
        Args:
            entity_id: ID of entity to load
            database_id: Optional database ID for disambiguation
            
        Returns:
            Entity data or None if not found
        """
        ...
    
    def load_entities(self, entity_ids: List[str], database_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load multiple entities by IDs.
        
        Args:
            entity_ids: List of entity IDs to load
            database_id: Optional database ID
            
        Returns:
            List of loaded entities
        """
        ...
    
    def load_related_entities(
        self,
        entity: Dict[str, Any],
        relationship_field: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Load entities related through a specific field.
        
        Args:
            entity: Source entity
            relationship_field: Field containing relationship
            filters: Optional filters for related entities
            
        Returns:
            List of related entities
        """
        ...


class RelationshipResolver(Protocol):
    """Protocol for relationship resolution implementations."""
    
    def resolve_relationships(
        self,
        data: List[Dict[str, Any]],
        includes: List[RelationshipInclude],
        data_loader: DataLoader,
        config: RelationshipConfig
    ) -> List[Dict[str, Any]]:
        """Resolve and include related entities.
        
        Args:
            data: List of root entities
            includes: Relationship specifications
            data_loader: Data loader for fetching entities
            config: Resolution configuration
            
        Returns:
            List of entities with resolved relationships
        """
        ...
    
    def build_relationship_graph(
        self,
        root_entities: List[Dict[str, Any]],
        max_depth: int,
        data_loader: DataLoader
    ) -> RelationshipGraph:
        """Build graph of entity relationships.
        
        Args:
            root_entities: Starting entities
            max_depth: Maximum traversal depth
            data_loader: Data loader for fetching entities
            
        Returns:
            Relationship graph
        """
        ...
    
    def find_paths(
        self,
        from_entity_id: str,
        to_entity_id: str,
        max_length: int,
        data_loader: DataLoader
    ) -> List[RelationshipPath]:
        """Find paths between two entities.
        
        Args:
            from_entity_id: Starting entity ID
            to_entity_id: Target entity ID
            max_length: Maximum path length
            data_loader: Data loader
            
        Returns:
            List of paths between entities
        """
        ...
    
    def detect_circular_references(
        self,
        entities: List[Dict[str, Any]],
        data_loader: DataLoader
    ) -> List[List[str]]:
        """Detect circular references in entity relationships.
        
        Args:
            entities: Entities to check
            data_loader: Data loader
            
        Returns:
            List of cycles (each cycle is a list of entity IDs)
        """
        ...


class RelationshipCache(Protocol):
    """Protocol for caching relationship data."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        ...
    
    def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        ...
    
    def clear(self) -> None:
        """Clear entire cache."""
        ...


class RelationshipAnalyzer(Protocol):
    """Protocol for analyzing entity relationships."""
    
    def analyze_connectivity(self, graph: RelationshipGraph) -> Dict[str, Any]:
        """Analyze graph connectivity metrics.
        
        Args:
            graph: Relationship graph
            
        Returns:
            Connectivity analysis results
        """
        ...
    
    def find_communities(self, graph: RelationshipGraph) -> List[Set[str]]:
        """Find communities in relationship graph.
        
        Args:
            graph: Relationship graph
            
        Returns:
            List of entity ID sets representing communities
        """
        ...
    
    def calculate_centrality(self, graph: RelationshipGraph) -> Dict[str, float]:
        """Calculate entity centrality scores.
        
        Args:
            graph: Relationship graph
            
        Returns:
            Map of entity ID to centrality score
        """
        ...
    
    def suggest_relationships(
        self,
        entity: Dict[str, Any],
        graph: RelationshipGraph,
        max_suggestions: int = 10
    ) -> List[Tuple[str, float, str]]:
        """Suggest potential relationships for an entity.
        
        Args:
            entity: Entity to analyze
            graph: Relationship graph
            max_suggestions: Maximum suggestions to return
            
        Returns:
            List of (entity_id, confidence, relationship_type) tuples
        """
        ...