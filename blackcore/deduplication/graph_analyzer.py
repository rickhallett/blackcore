"""
Graph-Based Relationship Analyzer

Analyzes entity relationships and network connections to improve deduplication
accuracy through contextual analysis and relationship pattern recognition.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class EntityNode:
    """Represents an entity as a node in the relationship graph."""

    entity_id: str
    entity_type: str
    entity_data: Dict[str, Any]
    connections: Set[str] = field(default_factory=set)
    connection_strength: Dict[str, float] = field(default_factory=dict)
    centrality_score: float = 0.0
    cluster_id: Optional[str] = None


@dataclass
class RelationshipEdge:
    """Represents a relationship between two entities."""

    source_id: str
    target_id: str
    relationship_type: str
    strength: float
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class GraphAnalysisResult:
    """Result of graph-based relationship analysis."""

    entity_clusters: Dict[str, List[str]]
    relationship_patterns: Dict[str, Any]
    disambiguation_suggestions: List[Dict[str, Any]]
    network_metrics: Dict[str, float]
    confidence_scores: Dict[str, float]


class GraphRelationshipAnalyzer:
    """
    Analyzes entity relationships using graph-based methods.

    Builds relationship graphs from entity data and uses network analysis
    to identify patterns that help disambiguate potential duplicates.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the graph analyzer."""
        self.config = config or self._load_default_config()

        # Graph storage
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: List[RelationshipEdge] = []
        self.relationship_types = set()

        # Analysis cache
        self.analysis_cache = {}

        # Statistics
        self.stats = {
            "nodes_processed": 0,
            "relationships_identified": 0,
            "clusters_formed": 0,
            "disambiguation_suggestions": 0,
        }

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for graph analysis."""
        return {
            "min_relationship_strength": 0.3,
            "clustering_threshold": 0.6,
            "max_cluster_size": 20,
            "enable_centrality_analysis": True,
            "relationship_weights": {
                "shared_organization": 0.8,
                "shared_location": 0.6,
                "shared_event": 0.7,
                "shared_contact": 0.5,
                "similar_role": 0.4,
                "temporal_proximity": 0.3,
            },
        }

    def build_relationship_graph(
        self, databases: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Build a comprehensive relationship graph from all entity data."""

        logger.info("🌐 Building relationship graph from entity data")

        # Clear existing graph
        self.nodes.clear()
        self.edges.clear()
        self.relationship_types.clear()

        # Process each database
        for db_name, entities in databases.items():
            self._process_database_entities(db_name, entities)

        # Identify relationships between entities
        self._identify_relationships()

        # Calculate graph metrics
        self._calculate_centrality_scores()

        logger.info(f"✅ Graph built: {len(self.nodes)} nodes, {len(self.edges)} edges")
        logger.info(f"   🔗 Relationship types: {len(self.relationship_types)}")

    def _process_database_entities(
        self, db_name: str, entities: List[Dict[str, Any]]
    ) -> None:
        """Process entities from a single database."""

        for entity in entities:
            entity_id = self._generate_entity_id(entity, db_name)

            node = EntityNode(
                entity_id=entity_id, entity_type=db_name, entity_data=entity
            )

            self.nodes[entity_id] = node
            self.stats["nodes_processed"] += 1

    def _generate_entity_id(self, entity: Dict[str, Any], db_name: str) -> str:
        """Generate a unique ID for an entity."""
        # Use existing ID if available, otherwise create one
        if "id" in entity:
            return f"{db_name}:{entity['id']}"

        # Create ID from key fields
        key_fields = [
            "Full Name",
            "Organization Name",
            "Event / Place Name",
            "Title",
            "Entry Title",
        ]

        for field in key_fields:
            if field in entity and entity[field]:
                # Clean and truncate for ID
                clean_name = str(entity[field])[:50].replace(" ", "_").lower()
                return f"{db_name}:{clean_name}:{hash(str(entity)) % 10000}"

        # Fallback to hash
        return f"{db_name}:entity_{hash(str(entity)) % 10000}"

    def _identify_relationships(self) -> None:
        """Identify relationships between entities across the graph."""

        logger.info("🔍 Identifying relationships between entities")

        # Compare all entity pairs to find relationships
        node_list = list(self.nodes.values())

        for i, node_a in enumerate(node_list):
            for node_b in node_list[i + 1 :]:
                relationships = self._find_relationships(node_a, node_b)

                for relationship in relationships:
                    self.edges.append(relationship)
                    self.relationship_types.add(relationship.relationship_type)

                    # Update node connections
                    node_a.connections.add(node_b.entity_id)
                    node_b.connections.add(node_a.entity_id)

                    # Store connection strength
                    node_a.connection_strength[node_b.entity_id] = relationship.strength
                    node_b.connection_strength[node_a.entity_id] = relationship.strength

                    self.stats["relationships_identified"] += 1

    def _find_relationships(
        self, node_a: EntityNode, node_b: EntityNode
    ) -> List[RelationshipEdge]:
        """Find relationships between two entity nodes."""
        relationships = []

        entity_a = node_a.entity_data
        entity_b = node_b.entity_data

        # Shared organization relationship
        org_rel = self._check_shared_organization(entity_a, entity_b)
        if org_rel:
            relationships.append(
                RelationshipEdge(
                    source_id=node_a.entity_id,
                    target_id=node_b.entity_id,
                    relationship_type="shared_organization",
                    strength=org_rel["strength"],
                    evidence=org_rel["evidence"],
                    confidence=org_rel["confidence"],
                )
            )

        # Shared location relationship
        loc_rel = self._check_shared_location(entity_a, entity_b)
        if loc_rel:
            relationships.append(
                RelationshipEdge(
                    source_id=node_a.entity_id,
                    target_id=node_b.entity_id,
                    relationship_type="shared_location",
                    strength=loc_rel["strength"],
                    evidence=loc_rel["evidence"],
                    confidence=loc_rel["confidence"],
                )
            )

        # Shared event relationship
        event_rel = self._check_shared_event(entity_a, entity_b)
        if event_rel:
            relationships.append(
                RelationshipEdge(
                    source_id=node_a.entity_id,
                    target_id=node_b.entity_id,
                    relationship_type="shared_event",
                    strength=event_rel["strength"],
                    evidence=event_rel["evidence"],
                    confidence=event_rel["confidence"],
                )
            )

        # Contact information relationship
        contact_rel = self._check_contact_relationship(entity_a, entity_b)
        if contact_rel:
            relationships.append(
                RelationshipEdge(
                    source_id=node_a.entity_id,
                    target_id=node_b.entity_id,
                    relationship_type="shared_contact",
                    strength=contact_rel["strength"],
                    evidence=contact_rel["evidence"],
                    confidence=contact_rel["confidence"],
                )
            )

        return relationships

    def _check_shared_organization(
        self, entity_a: Dict[str, Any], entity_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for shared organizational connections."""
        org_fields = ["Organization", "Company", "Affiliation", "Key People"]

        evidence = []
        total_strength = 0.0
        matches = 0

        for field in org_fields:
            val_a = str(entity_a.get(field, "")).lower().strip()
            val_b = str(entity_b.get(field, "")).lower().strip()

            if val_a and val_b and val_a == val_b:
                evidence.append(f"Shared {field}: {entity_a.get(field)}")
                total_strength += self.config["relationship_weights"][
                    "shared_organization"
                ]
                matches += 1

        if matches > 0:
            return {
                "strength": min(total_strength / matches, 1.0),
                "evidence": evidence,
                "confidence": min(matches * 0.3, 1.0),
            }

        return None

    def _check_shared_location(
        self, entity_a: Dict[str, Any], entity_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for shared location connections."""
        location_fields = ["Address", "Location", "Venue", "Place"]

        evidence = []
        matches = 0

        for field in location_fields:
            val_a = str(entity_a.get(field, "")).lower().strip()
            val_b = str(entity_b.get(field, "")).lower().strip()

            if val_a and val_b:
                # Check for exact match or substantial overlap
                if val_a == val_b:
                    evidence.append(f"Same {field}: {entity_a.get(field)}")
                    matches += 1
                elif self._location_similarity(val_a, val_b) > 0.8:
                    evidence.append(
                        f"Similar {field}: {entity_a.get(field)} / {entity_b.get(field)}"
                    )
                    matches += 0.5

        if matches > 0:
            strength = min(
                matches * self.config["relationship_weights"]["shared_location"], 1.0
            )
            return {
                "strength": strength,
                "evidence": evidence,
                "confidence": min(matches * 0.4, 1.0),
            }

        return None

    def _location_similarity(self, loc_a: str, loc_b: str) -> float:
        """Calculate similarity between two location strings."""
        # Simple token-based similarity
        tokens_a = set(loc_a.split())
        tokens_b = set(loc_b.split())

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)

        return intersection / union if union > 0 else 0.0

    def _check_shared_event(
        self, entity_a: Dict[str, Any], entity_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for shared event connections."""
        # Look for references to each other in event descriptions or attendee lists
        text_fields = ["Description", "Notes", "People Involved", "Tagged Entities"]

        entity_a_name = entity_a.get("Full Name", "").lower()
        entity_b_name = entity_b.get("Full Name", "").lower()

        evidence = []
        strength = 0.0

        # Check if entity A is mentioned in entity B's context
        for field in text_fields:
            text_b = str(entity_b.get(field, "")).lower()
            if entity_a_name and entity_a_name in text_b:
                evidence.append(f"Entity A mentioned in Entity B's {field}")
                strength += 0.3

        # Check if entity B is mentioned in entity A's context
        for field in text_fields:
            text_a = str(entity_a.get(field, "")).lower()
            if entity_b_name and entity_b_name in text_a:
                evidence.append(f"Entity B mentioned in Entity A's {field}")
                strength += 0.3

        if evidence:
            return {
                "strength": min(strength, 1.0),
                "evidence": evidence,
                "confidence": min(len(evidence) * 0.3, 1.0),
            }

        return None

    def _check_contact_relationship(
        self, entity_a: Dict[str, Any], entity_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for shared contact information patterns."""
        contact_fields = ["Email", "Phone", "Website"]

        evidence = []
        strength = 0.0

        for field in contact_fields:
            val_a = str(entity_a.get(field, "")).lower().strip()
            val_b = str(entity_b.get(field, "")).lower().strip()

            if val_a and val_b:
                # Check for domain similarity (emails) or pattern similarity
                if field == "Email" and "@" in val_a and "@" in val_b:
                    domain_a = val_a.split("@")[1]
                    domain_b = val_b.split("@")[1]
                    if domain_a == domain_b:
                        evidence.append(f"Shared email domain: {domain_a}")
                        strength += 0.4

                elif field == "Phone" and self._phone_similarity(val_a, val_b) > 0.8:
                    evidence.append("Similar phone numbers")
                    strength += 0.3

        if evidence:
            return {
                "strength": min(strength, 1.0),
                "evidence": evidence,
                "confidence": min(len(evidence) * 0.4, 1.0),
            }

        return None

    def _phone_similarity(self, phone_a: str, phone_b: str) -> float:
        """Calculate similarity between phone numbers."""
        # Extract digits only
        digits_a = "".join(filter(str.isdigit, phone_a))
        digits_b = "".join(filter(str.isdigit, phone_b))

        if not digits_a or not digits_b:
            return 0.0

        # Check for substantial overlap
        if len(digits_a) >= 6 and len(digits_b) >= 6:
            # Compare last 7 digits (local number)
            suffix_a = digits_a[-7:] if len(digits_a) >= 7 else digits_a
            suffix_b = digits_b[-7:] if len(digits_b) >= 7 else digits_b

            if suffix_a == suffix_b:
                return 1.0

        return 0.0

    def _calculate_centrality_scores(self) -> None:
        """Calculate centrality scores for all nodes."""
        if not self.config["enable_centrality_analysis"]:
            return

        logger.info("📊 Calculating node centrality scores")

        # Simple degree centrality calculation
        max_connections = (
            max(len(node.connections) for node in self.nodes.values())
            if self.nodes
            else 1
        )

        for node in self.nodes.values():
            # Degree centrality normalized by maximum possible connections
            node.centrality_score = (
                len(node.connections) / max_connections if max_connections > 0 else 0.0
            )

    def analyze_for_disambiguation(
        self, entity_pairs: List[Tuple[str, str]]
    ) -> GraphAnalysisResult:
        """Analyze entity pairs using graph-based methods for disambiguation."""

        logger.info(
            f"🔍 Analyzing {len(entity_pairs)} entity pairs using graph methods"
        )

        entity_clusters = self._identify_entity_clusters()
        relationship_patterns = self._analyze_relationship_patterns()
        disambiguation_suggestions = []
        confidence_scores = {}

        for entity_a_id, entity_b_id in entity_pairs:
            suggestion = self._analyze_entity_pair_context(entity_a_id, entity_b_id)
            if suggestion:
                disambiguation_suggestions.append(suggestion)
                confidence_scores[f"{entity_a_id}|{entity_b_id}"] = suggestion[
                    "confidence"
                ]

        # Calculate network metrics
        network_metrics = {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "average_connections": sum(len(n.connections) for n in self.nodes.values())
            / max(len(self.nodes), 1),
            "relationship_types": len(self.relationship_types),
            "largest_cluster_size": max(
                (len(cluster) for cluster in entity_clusters.values()), default=0
            ),
        }

        self.stats["disambiguation_suggestions"] = len(disambiguation_suggestions)
        self.stats["clusters_formed"] = len(entity_clusters)

        return GraphAnalysisResult(
            entity_clusters=entity_clusters,
            relationship_patterns=relationship_patterns,
            disambiguation_suggestions=disambiguation_suggestions,
            network_metrics=network_metrics,
            confidence_scores=confidence_scores,
        )

    def _identify_entity_clusters(self) -> Dict[str, List[str]]:
        """Identify clusters of closely related entities."""
        clusters = {}
        visited = set()
        cluster_id = 0

        for node_id, node in self.nodes.items():
            if node_id in visited:
                continue

            # Build cluster using DFS
            cluster = self._build_cluster(node_id, visited)

            if len(cluster) > 1:  # Only include multi-entity clusters
                clusters[f"cluster_{cluster_id}"] = cluster
                cluster_id += 1

        return clusters

    def _build_cluster(self, start_node_id: str, visited: Set[str]) -> List[str]:
        """Build a cluster starting from a given node using DFS."""
        cluster = []
        stack = [start_node_id]

        while stack:
            current_id = stack.pop()

            if current_id in visited:
                continue

            visited.add(current_id)
            cluster.append(current_id)

            # Add connected nodes that meet clustering threshold
            current_node = self.nodes[current_id]
            for connected_id in current_node.connections:
                if (
                    connected_id not in visited
                    and current_node.connection_strength.get(connected_id, 0)
                    >= self.config["clustering_threshold"]
                ):
                    stack.append(connected_id)

        return cluster

    def _analyze_relationship_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in the relationship graph."""
        patterns = {
            "relationship_type_frequency": Counter(),
            "hub_entities": [],
            "isolated_entities": [],
            "strong_connections": [],
        }

        # Relationship type frequency
        for edge in self.edges:
            patterns["relationship_type_frequency"][edge.relationship_type] += 1

        # Identify hub entities (high centrality)
        hub_threshold = 0.7
        for node_id, node in self.nodes.items():
            if node.centrality_score >= hub_threshold:
                patterns["hub_entities"].append(
                    {
                        "entity_id": node_id,
                        "centrality_score": node.centrality_score,
                        "connections": len(node.connections),
                    }
                )

        # Identify isolated entities
        for node_id, node in self.nodes.items():
            if len(node.connections) == 0:
                patterns["isolated_entities"].append(node_id)

        # Identify strong connections
        strength_threshold = 0.8
        for edge in self.edges:
            if edge.strength >= strength_threshold:
                patterns["strong_connections"].append(
                    {
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "strength": edge.strength,
                        "type": edge.relationship_type,
                    }
                )

        return patterns

    def _analyze_entity_pair_context(
        self, entity_a_id: str, entity_b_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze the graph context of two entities for disambiguation."""

        if entity_a_id not in self.nodes or entity_b_id not in self.nodes:
            return None

        node_a = self.nodes[entity_a_id]
        node_b = self.nodes[entity_b_id]

        # Check for direct relationship
        direct_relationship = self._get_direct_relationship(entity_a_id, entity_b_id)

        # Analyze shared connections
        shared_connections = node_a.connections & node_b.connections

        # Calculate context-based confidence
        context_confidence = 0.0
        evidence = []

        # Direct relationship boosts confidence
        if direct_relationship:
            context_confidence += direct_relationship.strength * 0.4
            evidence.append(
                f"Direct {direct_relationship.relationship_type} relationship"
            )

        # Shared connections boost confidence
        if shared_connections:
            shared_strength = sum(
                min(
                    node_a.connection_strength.get(conn_id, 0),
                    node_b.connection_strength.get(conn_id, 0),
                )
                for conn_id in shared_connections
            ) / len(shared_connections)

            context_confidence += shared_strength * 0.3
            evidence.append(
                f"Shared connections with {len(shared_connections)} entities"
            )

        # Similar centrality suggests similar roles/importance
        centrality_diff = abs(node_a.centrality_score - node_b.centrality_score)
        if centrality_diff < 0.2:  # Similar centrality
            context_confidence += 0.2
            evidence.append("Similar network centrality")

        if context_confidence > 0.1:  # Only return if meaningful context found
            return {
                "entity_a_id": entity_a_id,
                "entity_b_id": entity_b_id,
                "confidence": min(context_confidence, 1.0),
                "evidence": evidence,
                "shared_connections": len(shared_connections),
                "direct_relationship": (
                    direct_relationship.relationship_type
                    if direct_relationship
                    else None
                ),
            }

        return None

    def _get_direct_relationship(
        self, entity_a_id: str, entity_b_id: str
    ) -> Optional[RelationshipEdge]:
        """Get direct relationship between two entities."""
        for edge in self.edges:
            if (edge.source_id == entity_a_id and edge.target_id == entity_b_id) or (
                edge.source_id == entity_b_id and edge.target_id == entity_a_id
            ):
                return edge
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph analyzer statistics."""
        return {
            "nodes_processed": self.stats["nodes_processed"],
            "relationships_identified": self.stats["relationships_identified"],
            "clusters_formed": self.stats["clusters_formed"],
            "disambiguation_suggestions": self.stats["disambiguation_suggestions"],
            "relationship_types": list(self.relationship_types),
            "configuration": self.config,
        }
