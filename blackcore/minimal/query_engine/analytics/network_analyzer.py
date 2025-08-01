"""Network analysis for entity relationships and graph analytics."""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, deque
import statistics
import re

from .models import NetworkAlgorithm, NetworkNode, NetworkEdge, Community, NetworkMetrics

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """Analyzes entity relationships and network structures."""
    
    def __init__(self):
        """Initialize the network analyzer."""
        logger.debug("NetworkAnalyzer initialized")
    
    def analyze_network(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        algorithm: NetworkAlgorithm = NetworkAlgorithm.CENTRALITY,
        max_depth: int = 3,
        min_connections: int = 2,
        focus_entity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze entity relationship networks.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            algorithm: Analysis algorithm to use
            max_depth: Maximum relationship depth to traverse
            min_connections: Minimum connections to include node
            focus_entity: Optional entity to focus analysis on
            
        Returns:
            Dictionary with network analysis results
        """
        try:
            # Build the network graph
            graph = self._build_graph(all_data)
            
            # Filter nodes by minimum connections if specified
            if min_connections > 1:
                graph = self._filter_by_connections(graph, min_connections)
            
            # Apply focus entity filtering if specified
            if focus_entity:
                graph = self._focus_on_entity(graph, focus_entity, max_depth)
            
            # Convert to nodes and edges
            nodes, edges = self._graph_to_nodes_edges(graph, all_data)
            
            # Apply the specified algorithm
            if algorithm == NetworkAlgorithm.CENTRALITY:
                nodes = self._calculate_centrality(nodes, edges)
            elif algorithm == NetworkAlgorithm.COMMUNITY:
                nodes, communities = self._detect_communities(nodes, edges)
            elif algorithm == NetworkAlgorithm.INFLUENCE:
                nodes = self._calculate_influence(nodes, edges)
            elif algorithm == NetworkAlgorithm.CLUSTERING:
                nodes = self._calculate_clustering(nodes, edges)
            
            # Detect communities if not already done
            if algorithm != NetworkAlgorithm.COMMUNITY:
                nodes, communities = self._detect_communities(nodes, edges)
            
            # Calculate network metrics
            metrics = self._calculate_network_metrics(nodes, edges, communities)
            
            return {
                'nodes': [node.dict() for node in nodes],
                'edges': [edge.dict() for edge in edges],
                'communities': [community.dict() for community in communities],
                'metrics': metrics.dict()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing network: {e}")
            return {
                'nodes': [],
                'edges': [],
                'communities': [],
                'metrics': NetworkMetrics(
                    total_nodes=0,
                    total_edges=0,
                    density=0.0,
                    avg_clustering=0.0,
                    diameter=None,
                    communities_count=0
                ).dict()
            }
    
    def _build_graph(self, all_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Set[str]]:
        """Build a graph from entity relationships.
        
        Args:
            all_data: Dictionary mapping database names to entity lists
            
        Returns:
            Dictionary representing the graph as adjacency lists
        """
        graph = defaultdict(set)
        
        for db_name, entities in all_data.items():
            for entity in entities:
                entity_id = self._get_entity_id(entity, db_name)
                
                # Extract relationships from various fields
                relationships = self._extract_relationships(entity)
                
                for related_id in relationships:
                    if related_id and related_id != entity_id:
                        graph[entity_id].add(related_id)
                        graph[related_id].add(entity_id)  # Undirected graph
        
        return dict(graph)
    
    def _get_entity_id(self, entity: Dict[str, Any], db_name: str) -> str:
        """Generate a unique ID for an entity.
        
        Args:
            entity: Entity data
            db_name: Database name
            
        Returns:
            Unique entity ID
        """
        # Try to find a unique identifier
        for id_field in ['id', 'ID', 'uuid', 'Full Name', 'Task Name', 'Title', 'Name']:
            if id_field in entity and entity[id_field]:
                base_id = str(entity[id_field]).strip()
                if base_id:
                    return f"{db_name}:{base_id}"
        
        # Fallback to a hash of the entity
        import hashlib
        entity_str = json.dumps(entity, sort_keys=True, default=str)
        hash_id = hashlib.md5(entity_str.encode()).hexdigest()[:8]
        return f"{db_name}:{hash_id}"
    
    def _extract_relationships(self, entity: Dict[str, Any]) -> List[str]:
        """Extract relationship references from an entity.
        
        Args:
            entity: Entity data
            
        Returns:
            List of related entity identifiers
        """
        relationships = []
        
        # Common relationship field patterns
        relationship_fields = [
            'Organization', 'Related to', 'Assignee', 'Assigned To', 'Manager',
            'Team', 'Department', 'Parent', 'Child', 'Contact', 'Owner',
            'Agendas & Epics', 'People & Contacts', 'Organizations & Bodies'
        ]
        
        for field in relationship_fields:
            if field in entity:
                value = entity[field]
                
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            # Handle Notion-style relations with id/name
                            if 'id' in item:
                                relationships.append(item['id'])
                            elif 'name' in item:
                                relationships.append(item['name'])
                        elif isinstance(item, str) and item.strip():
                            relationships.append(item.strip())
                
                elif isinstance(value, str) and value.strip():
                    relationships.append(value.strip())
        
        # Extract mentions from text fields
        text_fields = ['Notes', 'Description', 'Comments', 'Summary']
        for field in text_fields:
            if field in entity and isinstance(entity[field], str):
                mentions = self._extract_mentions_from_text(entity[field])
                relationships.extend(mentions)
        
        return relationships
    
    def _extract_mentions_from_text(self, text: str) -> List[str]:
        """Extract entity mentions from text fields.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of mentioned entities
        """
        mentions = []
        
        # Simple pattern matching for names and organizations
        patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last names
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # First Middle Last
            r'\b[A-Z][A-Za-z\s]+ Council\b',  # Organizations ending in Council
            r'\b[A-Z][A-Za-z\s]+ Forum\b',   # Organizations ending in Forum
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            mentions.extend(matches)
        
        return mentions
    
    def _filter_by_connections(
        self, 
        graph: Dict[str, Set[str]], 
        min_connections: int
    ) -> Dict[str, Set[str]]:
        """Filter graph to include only nodes with minimum connections.
        
        Args:
            graph: Graph as adjacency lists
            min_connections: Minimum number of connections
            
        Returns:
            Filtered graph
        """
        filtered_graph = {}
        
        for node, connections in graph.items():
            if len(connections) >= min_connections:
                filtered_connections = {conn for conn in connections 
                                      if len(graph.get(conn, set())) >= min_connections}
                if filtered_connections:
                    filtered_graph[node] = filtered_connections
        
        return filtered_graph
    
    def _focus_on_entity(
        self, 
        graph: Dict[str, Set[str]], 
        focus_entity: str, 
        max_depth: int
    ) -> Dict[str, Set[str]]:
        """Focus graph analysis on a specific entity and its neighborhood.
        
        Args:
            graph: Graph as adjacency lists
            focus_entity: Entity to focus on
            max_depth: Maximum depth to traverse
            
        Returns:
            Filtered graph focused on the entity
        """
        # Find the focus entity in the graph
        focus_node = None
        for node in graph:
            if focus_entity.lower() in node.lower():
                focus_node = node
                break
        
        if not focus_node:
            return graph  # Return original if focus entity not found
        
        # BFS to find nodes within max_depth
        visited = set()
        queue = deque([(focus_node, 0)])
        focused_nodes = set()
        
        while queue:
            node, depth = queue.popleft()
            
            if node in visited or depth > max_depth:
                continue
            
            visited.add(node)
            focused_nodes.add(node)
            
            if depth < max_depth:
                for neighbor in graph.get(node, set()):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))
        
        # Build focused graph
        focused_graph = {}
        for node in focused_nodes:
            if node in graph:
                connections = graph[node] & focused_nodes
                if connections:
                    focused_graph[node] = connections
        
        return focused_graph
    
    def _graph_to_nodes_edges(
        self, 
        graph: Dict[str, Set[str]], 
        all_data: Dict[str, List[Dict[str, Any]]]
    ) -> Tuple[List[NetworkNode], List[NetworkEdge]]:
        """Convert graph to NetworkNode and NetworkEdge objects.
        
        Args:
            graph: Graph as adjacency lists
            all_data: Original entity data
            
        Returns:
            Tuple of (nodes, edges)
        """
        nodes = []
        edges = []
        edge_set = set()  # To avoid duplicate edges
        
        # Create entity lookup
        entity_lookup = {}
        for db_name, entities in all_data.items():
            for entity in entities:
                entity_id = self._get_entity_id(entity, db_name)
                entity_lookup[entity_id] = (entity, db_name)
        
        # Create nodes
        for node_id in graph:
            entity_data, db_name = entity_lookup.get(node_id, ({}, 'Unknown'))
            
            # Extract node properties
            label = self._get_entity_label(entity_data)
            node_type = self._get_entity_type(entity_data, db_name)
            properties = self._extract_node_properties(entity_data)
            
            node = NetworkNode(
                id=node_id,
                label=label,
                type=node_type,
                properties=properties,
                centrality_score=0.0,  # Will be calculated later
                connections=len(graph[node_id]),
                community=None  # Will be assigned later
            )
            nodes.append(node)
        
        # Create edges
        for source_id, targets in graph.items():
            for target_id in targets:
                edge_key = tuple(sorted([source_id, target_id]))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    
                    # Determine relationship type
                    relationship = self._determine_relationship_type(
                        source_id, target_id, entity_lookup
                    )
                    
                    edge = NetworkEdge(
                        source=source_id,
                        target=target_id,
                        relationship=relationship,
                        weight=1.0,  # Default weight
                        properties={}
                    )
                    edges.append(edge)
        
        return nodes, edges
    
    def _get_entity_label(self, entity: Dict[str, Any]) -> str:
        """Get display label for an entity.
        
        Args:
            entity: Entity data
            
        Returns:
            Display label
        """
        for label_field in ['Full Name', 'Task Name', 'Title', 'Name', 'Label']:
            if label_field in entity and entity[label_field]:
                return str(entity[label_field])
        
        return "Unknown Entity"
    
    def _get_entity_type(self, entity: Dict[str, Any], db_name: str) -> str:
        """Get entity type.
        
        Args:
            entity: Entity data
            db_name: Database name
            
        Returns:
            Entity type
        """
        # Use database name as base type
        type_mapping = {
            'People & Contacts': 'person',
            'Organizations & Bodies': 'organization',
            'Actionable Tasks': 'task',
            'Documents & Evidence': 'document',
            'Intelligence & Transcripts': 'intelligence',
            'Agendas & Epics': 'agenda',
            'Key Places & Events': 'location',
            'Identified Transgressions': 'transgression'
        }
        
        return type_mapping.get(db_name, 'entity')
    
    def _extract_node_properties(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key properties for a node.
        
        Args:
            entity: Entity data
            
        Returns:
            Dictionary of key properties
        """
        properties = {}
        
        # Key fields to include as properties
        key_fields = ['Status', 'Role', 'Priority', 'Department', 'Category', 'Type']
        
        for field in key_fields:
            if field in entity and entity[field]:
                properties[field.lower()] = entity[field]
        
        return properties
    
    def _determine_relationship_type(
        self, 
        source_id: str, 
        target_id: str, 
        entity_lookup: Dict[str, Tuple[Dict[str, Any], str]]
    ) -> str:
        """Determine the type of relationship between entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            entity_lookup: Entity lookup dictionary
            
        Returns:
            Relationship type
        """
        source_entity, source_db = entity_lookup.get(source_id, ({}, ''))
        target_entity, target_db = entity_lookup.get(target_id, ({}, ''))
        
        # Determine relationship based on entity types
        if source_db == 'People & Contacts' and target_db == 'Organizations & Bodies':
            return 'works_for'
        elif source_db == 'Actionable Tasks' and target_db == 'People & Contacts':
            return 'assigned_to'
        elif source_db == 'People & Contacts' and target_db == 'People & Contacts':
            return 'collaborates_with'
        elif 'task' in source_db.lower() and 'agenda' in target_db.lower():
            return 'supports'
        else:
            return 'related_to'
    
    def _calculate_centrality(
        self, 
        nodes: List[NetworkNode], 
        edges: List[NetworkEdge]
    ) -> List[NetworkNode]:
        """Calculate centrality scores for nodes.
        
        Args:
            nodes: List of network nodes
            edges: List of network edges
            
        Returns:
            Updated nodes with centrality scores
        """
        # Build adjacency list for centrality calculation
        adjacency = defaultdict(set)
        for edge in edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
        
        # Calculate degree centrality (normalized)
        max_connections = max(len(adjacency[node.id]) for node in nodes) if nodes else 1
        
        for node in nodes:
            connections = len(adjacency[node.id])
            node.centrality_score = connections / max_connections if max_connections > 0 else 0.0
        
        return nodes
    
    def _calculate_influence(
        self, 
        nodes: List[NetworkNode], 
        edges: List[NetworkEdge]
    ) -> List[NetworkNode]:
        """Calculate influence scores using PageRank-like algorithm.
        
        Args:
            nodes: List of network nodes
            edges: List of network edges
            
        Returns:
            Updated nodes with influence scores
        """
        # Simplified PageRank calculation
        node_scores = {node.id: 1.0 for node in nodes}
        adjacency = defaultdict(set)
        
        for edge in edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
        
        # Run simplified PageRank iterations
        for _ in range(10):
            new_scores = {}
            for node in nodes:
                score = 0.15  # Damping factor
                for neighbor in adjacency[node.id]:
                    neighbor_connections = len(adjacency[neighbor])
                    if neighbor_connections > 0:
                        score += 0.85 * node_scores[neighbor] / neighbor_connections
                new_scores[node.id] = score
            node_scores = new_scores
        
        # Normalize scores
        max_score = max(node_scores.values()) if node_scores else 1.0
        for node in nodes:
            node.centrality_score = node_scores[node.id] / max_score
        
        return nodes
    
    def _calculate_clustering(
        self, 
        nodes: List[NetworkNode], 
        edges: List[NetworkEdge]
    ) -> List[NetworkNode]:
        """Calculate local clustering coefficients.
        
        Args:
            nodes: List of network nodes
            edges: List of network edges
            
        Returns:
            Updated nodes with clustering scores
        """
        # Build adjacency list
        adjacency = defaultdict(set)
        for edge in edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
        
        for node in nodes:
            neighbors = list(adjacency[node.id])
            if len(neighbors) < 2:
                node.centrality_score = 0.0
                continue
            
            # Count triangles
            triangles = 0
            possible_triangles = len(neighbors) * (len(neighbors) - 1) // 2
            
            for i, neighbor1 in enumerate(neighbors):
                for neighbor2 in neighbors[i + 1:]:
                    if neighbor2 in adjacency[neighbor1]:
                        triangles += 1
            
            node.centrality_score = triangles / possible_triangles if possible_triangles > 0 else 0.0
        
        return nodes
    
    def _detect_communities(
        self, 
        nodes: List[NetworkNode], 
        edges: List[NetworkEdge]
    ) -> Tuple[List[NetworkNode], List[Community]]:
        """Detect communities using simple clustering.
        
        Args:
            nodes: List of network nodes
            edges: List of network edges
            
        Returns:
            Tuple of (updated nodes, communities)
        """
        # Build adjacency list
        adjacency = defaultdict(set)
        for edge in edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
        
        # Simple community detection using connected components
        visited = set()
        communities = []
        
        for node in nodes:
            if node.id not in visited:
                # BFS to find connected component
                community_members = []
                queue = deque([node.id])
                
                while queue:
                    current = queue.popleft()
                    if current not in visited:
                        visited.add(current)
                        community_members.append(current)
                        
                        for neighbor in adjacency[current]:
                            if neighbor not in visited:
                                queue.append(neighbor)
                
                if len(community_members) > 1:
                    community_id = f"community_{len(communities) + 1}"
                    
                    # Find center node (highest degree)
                    center_node = max(community_members, 
                                    key=lambda n: len(adjacency[n]))
                    
                    community = Community(
                        id=community_id,
                        label=f"Community {len(communities) + 1}",
                        members=community_members,
                        size=len(community_members),
                        modularity=0.5,  # Simplified
                        center_node=center_node
                    )
                    communities.append(community)
                    
                    # Assign community to nodes
                    for member_id in community_members:
                        for node in nodes:
                            if node.id == member_id:
                                node.community = community_id
                                break
        
        return nodes, communities
    
    def _calculate_network_metrics(
        self, 
        nodes: List[NetworkNode], 
        edges: List[NetworkEdge],
        communities: List[Community]
    ) -> NetworkMetrics:
        """Calculate overall network metrics.
        
        Args:
            nodes: List of network nodes
            edges: List of network edges
            communities: List of detected communities
            
        Returns:
            Network metrics
        """
        total_nodes = len(nodes)
        total_edges = len(edges)
        
        # Calculate density
        max_possible_edges = total_nodes * (total_nodes - 1) // 2
        density = total_edges / max_possible_edges if max_possible_edges > 0 else 0.0
        
        # Calculate average clustering
        clustering_scores = [node.centrality_score for node in nodes if hasattr(node, 'centrality_score')]
        avg_clustering = statistics.mean(clustering_scores) if clustering_scores else 0.0
        
        # Calculate diameter (simplified - just use max connections as proxy)
        max_connections = max(node.connections for node in nodes) if nodes else 0
        diameter = max_connections if max_connections > 0 else None
        
        return NetworkMetrics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            density=density,
            avg_clustering=avg_clustering,
            diameter=diameter,
            communities_count=len(communities)
        )