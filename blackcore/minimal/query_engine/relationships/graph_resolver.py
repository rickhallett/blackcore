"""Graph-based relationship resolution implementation.

This module implements efficient graph traversal algorithms for resolving
entity relationships with support for circular reference detection.
"""

from typing import List, Dict, Any, Optional, Set, Tuple, Deque
from collections import defaultdict, deque
from dataclasses import dataclass, field
import time

from .interfaces import (
    RelationshipResolver,
    RelationshipInclude,
    RelationshipConfig,
    RelationshipGraph,
    RelationshipPath,
    RelationshipDirection,
    TraversalStrategy,
    DataLoader
)


class GraphRelationshipResolver:
    """Implements relationship resolution using graph algorithms."""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.visited_tracker = VisitedTracker()
    
    def resolve_relationships(
        self,
        data: List[Dict[str, Any]],
        includes: List[RelationshipInclude],
        data_loader: DataLoader,
        config: RelationshipConfig
    ) -> List[Dict[str, Any]]:
        """Resolve and include related entities."""
        if not data or not includes:
            return data
        
        # Build initial graph from root entities
        graph = RelationshipGraph()
        for entity in data:
            graph.add_node(entity)
        
        # Process each include specification
        for include in includes:
            self._process_include(graph, include, data_loader, config)
        
        # Convert graph back to list with resolved relationships
        result = []
        for entity_id, entity in graph.nodes.items():
            # Deep copy to avoid modifying original
            resolved_entity = entity.copy()
            
            # Add resolved relationships
            for include in includes:
                field_name = include.field_name
                if field_name in entity:
                    # Get related entities from graph
                    related_ids = entity.get(field_name, [])
                    if isinstance(related_ids, list):
                        related_entities = [
                            graph.nodes.get(rid) for rid in related_ids
                            if rid in graph.nodes
                        ]
                        resolved_entity[f"{field_name}_resolved"] = [
                            e for e in related_entities if e
                        ]
                    elif isinstance(related_ids, str) and related_ids in graph.nodes:
                        resolved_entity[f"{field_name}_resolved"] = graph.nodes[related_ids]
            
            result.append(resolved_entity)
        
        return result
    
    def build_relationship_graph(
        self,
        root_entities: List[Dict[str, Any]],
        max_depth: int,
        data_loader: DataLoader
    ) -> RelationshipGraph:
        """Build graph of entity relationships."""
        graph = RelationshipGraph()
        
        # Initialize with root entities
        for entity in root_entities:
            graph.add_node(entity)
        
        # BFS traversal to build graph
        queue = deque([(entity, 0) for entity in root_entities])
        visited = set()
        
        while queue:
            current_entity, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            entity_id = current_entity.get('id')
            if not entity_id or entity_id in visited:
                continue
            
            visited.add(entity_id)
            
            # Find all relationship fields
            for field_name, field_value in current_entity.items():
                if self._is_relationship_field(field_name, field_value):
                    # Load related entities
                    related_entities = data_loader.load_related_entities(
                        current_entity, field_name
                    )
                    
                    for related_entity in related_entities:
                        related_id = related_entity.get('id')
                        if related_id:
                            # Add to graph
                            graph.add_node(related_entity)
                            graph.add_edge(entity_id, related_id, field_name)
                            
                            # Add to queue for further traversal
                            if related_id not in visited:
                                queue.append((related_entity, depth + 1))
        
        return graph
    
    def find_paths(
        self,
        from_entity_id: str,
        to_entity_id: str,
        max_length: int,
        data_loader: DataLoader
    ) -> List[RelationshipPath]:
        """Find paths between two entities using BFS."""
        if from_entity_id == to_entity_id:
            return [RelationshipPath(nodes=[from_entity_id], edges=[])]
        
        # Build graph if needed
        from_entity = data_loader.load_entity(from_entity_id)
        if not from_entity:
            return []
        
        graph = self.build_relationship_graph([from_entity], max_length, data_loader)
        
        # BFS to find all paths
        paths = []
        queue = deque([(from_entity_id, [from_entity_id], [])])
        
        while queue:
            current_id, path_nodes, path_edges = queue.popleft()
            
            if len(path_nodes) > max_length:
                continue
            
            if current_id == to_entity_id:
                paths.append(RelationshipPath(nodes=path_nodes, edges=path_edges))
                continue
            
            # Explore neighbors
            for neighbor_id, rel_type in graph.get_neighbors(current_id):
                if neighbor_id not in path_nodes:  # Avoid cycles
                    new_path_nodes = path_nodes + [neighbor_id]
                    new_path_edges = path_edges + [(current_id, neighbor_id, rel_type)]
                    queue.append((neighbor_id, new_path_nodes, new_path_edges))
        
        return paths
    
    def detect_circular_references(
        self,
        entities: List[Dict[str, Any]],
        data_loader: DataLoader
    ) -> List[List[str]]:
        """Detect circular references using DFS."""
        graph = self.build_relationship_graph(entities, 10, data_loader)
        
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for neighbor_id, _ in graph.get_neighbors(node_id):
                if neighbor_id not in visited:
                    if dfs(neighbor_id):
                        return True
                elif neighbor_id in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor_id)
                    cycle = path[cycle_start:] + [neighbor_id]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node_id)
            return False
        
        # Check each component
        for node_id in graph.nodes:
            if node_id not in visited:
                dfs(node_id)
        
        return cycles
    
    def _process_include(
        self,
        graph: RelationshipGraph,
        include: RelationshipInclude,
        data_loader: DataLoader,
        config: RelationshipConfig
    ) -> None:
        """Process a single relationship include specification."""
        if config.strategy == TraversalStrategy.BREADTH_FIRST:
            self._process_include_bfs(graph, include, data_loader, config)
        elif config.strategy == TraversalStrategy.DEPTH_FIRST:
            self._process_include_dfs(graph, include, data_loader, config)
        else:
            # Default to BFS
            self._process_include_bfs(graph, include, data_loader, config)
    
    def _process_include_bfs(
        self,
        graph: RelationshipGraph,
        include: RelationshipInclude,
        data_loader: DataLoader,
        config: RelationshipConfig
    ) -> None:
        """Process include using breadth-first traversal."""
        # Get all entities that have the specified field
        queue = deque()
        processed = set()
        
        for entity_id, entity in graph.nodes.items():
            if include.field_name in entity:
                queue.append((entity, 0))
        
        entities_loaded = 0
        
        while queue and entities_loaded < config.max_entities:
            current_entity, depth = queue.popleft()
            
            if depth >= include.max_depth:
                continue
            
            entity_id = current_entity.get('id')
            if not entity_id or entity_id in processed:
                continue
            
            processed.add(entity_id)
            
            # Load related entities
            field_value = current_entity.get(include.field_name)
            if not field_value:
                continue
            
            # Handle both single and multiple relationships
            related_ids = field_value if isinstance(field_value, list) else [field_value]
            
            # Batch load for efficiency
            if config.parallel_loading and len(related_ids) > 1:
                related_entities = data_loader.load_entities(related_ids, include.database_id)
            else:
                related_entities = []
                for rel_id in related_ids:
                    entity = data_loader.load_entity(rel_id, include.database_id)
                    if entity:
                        related_entities.append(entity)
            
            # Apply filters if specified
            if include.filters:
                related_entities = self._apply_filters(related_entities, include.filters)
            
            # Add to graph
            for related_entity in related_entities:
                if entities_loaded >= config.max_entities:
                    break
                
                related_id = related_entity.get('id')
                if related_id and related_id not in graph.nodes:
                    graph.add_node(related_entity)
                    graph.add_edge(entity_id, related_id, include.field_name)
                    entities_loaded += 1
                    
                    # Add to queue for recursive processing
                    if include.recursive and depth + 1 < include.max_depth:
                        queue.append((related_entity, depth + 1))
    
    def _process_include_dfs(
        self,
        graph: RelationshipGraph,
        include: RelationshipInclude,
        data_loader: DataLoader,
        config: RelationshipConfig
    ) -> None:
        """Process include using depth-first traversal."""
        processed = set()
        entities_loaded = 0
        
        def dfs(entity: Dict[str, Any], depth: int) -> None:
            nonlocal entities_loaded
            
            if depth >= include.max_depth or entities_loaded >= config.max_entities:
                return
            
            entity_id = entity.get('id')
            if not entity_id or entity_id in processed:
                return
            
            processed.add(entity_id)
            
            # Load related entities
            field_value = entity.get(include.field_name)
            if not field_value:
                return
            
            related_ids = field_value if isinstance(field_value, list) else [field_value]
            
            for rel_id in related_ids:
                if entities_loaded >= config.max_entities:
                    break
                
                related_entity = data_loader.load_entity(rel_id, include.database_id)
                if related_entity:
                    # Apply filters
                    if include.filters and not self._matches_filters(related_entity, include.filters):
                        continue
                    
                    related_id = related_entity.get('id')
                    if related_id and related_id not in graph.nodes:
                        graph.add_node(related_entity)
                        graph.add_edge(entity_id, related_id, include.field_name)
                        entities_loaded += 1
                        
                        # Recursive call
                        if include.recursive:
                            dfs(related_entity, depth + 1)
        
        # Start DFS from all entities with the field
        for entity in list(graph.nodes.values()):
            if include.field_name in entity:
                dfs(entity, 0)
    
    def _is_relationship_field(self, field_name: str, field_value: Any) -> bool:
        """Check if a field represents a relationship."""
        # Common patterns for relationship fields
        relationship_patterns = [
            '_id', '_ids', '_ref', '_refs', 'related_', 'parent_', 'child_',
            'owner', 'created_by', 'assigned_to', 'members', 'participants'
        ]
        
        # Check field name patterns
        for pattern in relationship_patterns:
            if pattern in field_name:
                return True
        
        # Check field value type (UUID-like strings or lists of them)
        if isinstance(field_value, str):
            # Simple UUID check (32 hex chars with optional dashes)
            import re
            uuid_pattern = r'^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$'
            return bool(re.match(uuid_pattern, field_value, re.IGNORECASE))
        elif isinstance(field_value, list) and field_value:
            # Check if list of potential IDs
            return all(isinstance(v, str) for v in field_value[:5])  # Check first 5
        
        return False
    
    def _apply_filters(self, entities: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to a list of entities."""
        filtered = []
        
        for entity in entities:
            if self._matches_filters(entity, filters):
                filtered.append(entity)
        
        return filtered
    
    def _matches_filters(self, entity: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if entity matches all filters."""
        for field, expected_value in filters.items():
            actual_value = entity.get(field)
            
            # Handle different filter types
            if isinstance(expected_value, dict):
                # Complex filter (e.g., {"$in": [...], "$gt": ...})
                if not self._matches_complex_filter(actual_value, expected_value):
                    return False
            else:
                # Simple equality
                if actual_value != expected_value:
                    return False
        
        return True
    
    def _matches_complex_filter(self, value: Any, filter_spec: Dict[str, Any]) -> bool:
        """Match value against complex filter specification."""
        for op, expected in filter_spec.items():
            if op == "$in" and value not in expected:
                return False
            elif op == "$nin" and value in expected:
                return False
            elif op == "$gt" and not (value > expected):
                return False
            elif op == "$gte" and not (value >= expected):
                return False
            elif op == "$lt" and not (value < expected):
                return False
            elif op == "$lte" and not (value <= expected):
                return False
            elif op == "$ne" and value == expected:
                return False
            elif op == "$exists" and (value is None) != (not expected):
                return False
        
        return True


@dataclass
class VisitedTracker:
    """Tracks visited entities to prevent infinite loops."""
    visited: Set[str] = field(default_factory=set)
    visit_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def visit(self, entity_id: str) -> bool:
        """Mark entity as visited. Returns True if first visit."""
        is_first = entity_id not in self.visited
        self.visited.add(entity_id)
        self.visit_count[entity_id] += 1
        return is_first
    
    def get_visit_count(self, entity_id: str) -> int:
        """Get number of times entity was visited."""
        return self.visit_count[entity_id]
    
    def reset(self) -> None:
        """Reset tracking."""
        self.visited.clear()
        self.visit_count.clear()