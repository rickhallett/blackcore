"""Tests for the relationships module."""

import pytest
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock

from ..relationships import (
    GraphRelationshipResolver,
    RelationshipGraph,
    RelationshipInclude,
    RelationshipConfig,
    RelationshipDirection,
    TraversalStrategy,
    LRURelationshipCache,
    TwoLevelCache,
    CacheKeyBuilder,
    DataLoader
)


class MockDataLoader:
    """Mock data loader for testing."""
    
    def __init__(self, data: Dict[str, Dict[str, Any]]):
        self.data = data
        self.load_count = 0
    
    def load_entity(self, entity_id: str, database_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load a single entity by ID."""
        self.load_count += 1
        return self.data.get(entity_id)
    
    def load_entities(self, entity_ids: List[str], database_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load multiple entities by IDs."""
        self.load_count += len(entity_ids)
        return [self.data[eid] for eid in entity_ids if eid in self.data]
    
    def load_related_entities(
        self,
        entity: Dict[str, Any],
        relationship_field: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Load entities related through a specific field."""
        related_ids = entity.get(relationship_field, [])
        if isinstance(related_ids, str):
            related_ids = [related_ids]
        
        entities = self.load_entities(related_ids)
        
        # Apply filters if provided
        if filters:
            filtered = []
            for e in entities:
                match = True
                for field, value in filters.items():
                    if e.get(field) != value:
                        match = False
                        break
                if match:
                    filtered.append(e)
            return filtered
        
        return entities


class TestGraphRelationshipResolver:
    """Test cases for GraphRelationshipResolver."""
    
    @pytest.fixture
    def resolver(self):
        """Create resolver instance."""
        return GraphRelationshipResolver()
    
    @pytest.fixture
    def sample_data(self) -> Dict[str, Dict[str, Any]]:
        """Create sample entity data with relationships."""
        return {
            "person1": {
                "id": "person1",
                "name": "John Doe",
                "type": "person",
                "organization_id": "org1",
                "manager_id": "person2",
                "task_ids": ["task1", "task2"]
            },
            "person2": {
                "id": "person2",
                "name": "Jane Smith",
                "type": "person",
                "organization_id": "org1",
                "reports": ["person1", "person3"]
            },
            "person3": {
                "id": "person3",
                "name": "Bob Johnson",
                "type": "person",
                "organization_id": "org2",
                "manager_id": "person2"
            },
            "org1": {
                "id": "org1",
                "name": "TechCorp",
                "type": "organization",
                "parent_org_id": "org2"
            },
            "org2": {
                "id": "org2",
                "name": "GlobalCorp",
                "type": "organization",
                "subsidiary_ids": ["org1"]
            },
            "task1": {
                "id": "task1",
                "title": "Complete Project",
                "assignee_id": "person1",
                "status": "open"
            },
            "task2": {
                "id": "task2",
                "title": "Review Code",
                "assignee_id": "person1",
                "status": "completed"
            }
        }
    
    def test_simple_relationship_resolution(self, resolver, sample_data):
        """Test basic relationship resolution."""
        data_loader = MockDataLoader(sample_data)
        
        # Start with person1
        root_data = [sample_data["person1"]]
        
        # Include organization
        includes = [
            RelationshipInclude(
                field_name="organization_id",
                max_depth=1
            )
        ]
        
        config = RelationshipConfig(max_depth=1)
        
        result = resolver.resolve_relationships(root_data, includes, data_loader, config)
        
        assert len(result) == 1
        assert "organization_id_resolved" in result[0]
        assert result[0]["organization_id_resolved"]["name"] == "TechCorp"
    
    def test_multi_level_relationships(self, resolver, sample_data):
        """Test multi-level relationship traversal."""
        data_loader = MockDataLoader(sample_data)
        
        # Start with person1
        root_data = [sample_data["person1"]]
        
        # Include manager and their organization
        includes = [
            RelationshipInclude(
                field_name="manager_id",
                max_depth=2,
                recursive=True
            )
        ]
        
        config = RelationshipConfig(max_depth=2)
        
        result = resolver.resolve_relationships(root_data, includes, data_loader, config)
        
        assert len(result) == 1
        assert "manager_id_resolved" in result[0]
        assert result[0]["manager_id_resolved"]["name"] == "Jane Smith"
    
    def test_array_relationships(self, resolver, sample_data):
        """Test resolution of array relationship fields."""
        data_loader = MockDataLoader(sample_data)
        
        # Start with person1
        root_data = [sample_data["person1"]]
        
        # Include tasks
        includes = [
            RelationshipInclude(
                field_name="task_ids",
                max_depth=1
            )
        ]
        
        config = RelationshipConfig()
        
        result = resolver.resolve_relationships(root_data, includes, data_loader, config)
        
        assert len(result) == 1
        assert "task_ids_resolved" in result[0]
        assert len(result[0]["task_ids_resolved"]) == 2
        assert all(t["id"] in ["task1", "task2"] for t in result[0]["task_ids_resolved"])
    
    def test_filtered_relationships(self, resolver, sample_data):
        """Test relationship resolution with filters."""
        data_loader = MockDataLoader(sample_data)
        
        # Start with person1
        root_data = [sample_data["person1"]]
        
        # Include only open tasks
        includes = [
            RelationshipInclude(
                field_name="task_ids",
                filters={"status": "open"}
            )
        ]
        
        config = RelationshipConfig()
        
        result = resolver.resolve_relationships(root_data, includes, data_loader, config)
        
        assert len(result) == 1
        assert "task_ids_resolved" in result[0]
        assert len(result[0]["task_ids_resolved"]) == 1
        assert result[0]["task_ids_resolved"][0]["status"] == "open"
    
    def test_build_relationship_graph(self, resolver, sample_data):
        """Test building a relationship graph."""
        data_loader = MockDataLoader(sample_data)
        
        root_entities = [sample_data["person1"]]
        graph = resolver.build_relationship_graph(root_entities, 2, data_loader)
        
        # Check graph structure
        assert "person1" in graph.nodes
        assert "person2" in graph.nodes  # Manager
        assert "org1" in graph.nodes     # Organization
        assert "task1" in graph.nodes    # Task
        
        # Check edges
        assert len(graph.edges) > 0
        edge_types = [edge[2] for edge in graph.edges]
        assert "manager_id" in edge_types
        assert "organization_id" in edge_types
    
    def test_circular_reference_detection(self, resolver):
        """Test detection of circular references."""
        # Create data with circular reference
        circular_data = {
            "a": {"id": "a", "next": "b"},
            "b": {"id": "b", "next": "c"},
            "c": {"id": "c", "next": "a"}  # Circular reference
        }
        
        data_loader = MockDataLoader(circular_data)
        entities = list(circular_data.values())
        
        cycles = resolver.detect_circular_references(entities, data_loader)
        
        assert len(cycles) > 0
        # Should detect the a->b->c->a cycle
        cycle = cycles[0]
        assert len(cycle) == 4  # Including return to start
        assert cycle[0] == cycle[-1]  # Cycle completes
    
    def test_find_paths(self, resolver, sample_data):
        """Test finding paths between entities."""
        data_loader = MockDataLoader(sample_data)
        
        paths = resolver.find_paths("person1", "org2", 3, data_loader)
        
        assert len(paths) > 0
        # Should find path: person1 -> org1 -> org2
        shortest_path = min(paths, key=lambda p: p.length)
        assert shortest_path.length == 2
    
    def test_max_entities_limit(self, resolver, sample_data):
        """Test max entities limit is respected."""
        data_loader = MockDataLoader(sample_data)
        
        root_data = [sample_data["person1"]]
        includes = [
            RelationshipInclude(
                field_name="task_ids",
                max_depth=1
            )
        ]
        
        # Limit to 1 entity
        config = RelationshipConfig(max_entities=1)
        
        result = resolver.resolve_relationships(root_data, includes, data_loader, config)
        
        # Should have limited the resolved relationships
        assert len(result[0].get("task_ids_resolved", [])) <= 1


class TestRelationshipCache:
    """Test cases for relationship caching."""
    
    def test_lru_cache_basic(self):
        """Test basic LRU cache operations."""
        cache = LRURelationshipCache(max_size=3)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test miss
        assert cache.get("key2") is None
        
        # Test eviction
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"
    
    def test_lru_cache_ttl(self):
        """Test cache TTL expiration."""
        import time
        
        cache = LRURelationshipCache(default_ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key1") is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation patterns."""
        cache = LRURelationshipCache()
        
        # Set multiple keys
        cache.set("user:1", "data1")
        cache.set("user:2", "data2")
        cache.set("org:1", "data3")
        
        # Invalidate by pattern
        cache.invalidate("user:*")
        
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("org:1") == "data3"
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = LRURelationshipCache()
        
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
    
    def test_two_level_cache(self):
        """Test two-level cache behavior."""
        cache = TwoLevelCache(l1_size=2, l2_size=5)
        
        # Set value (goes to both levels)
        cache.set("key1", "value1")
        
        # Get from L1
        assert cache.get("key1") == "value1"
        
        # Fill L1 to trigger promotion
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # L1 is now full
        
        # Access key1 from L2 (should promote to L1)
        cache.l1.cache.clear()  # Clear L1
        assert cache.get("key1") == "value1"  # From L2, promoted to L1
        assert cache.l1.get("key1") == "value1"  # Now in L1
    
    def test_cache_key_builder(self):
        """Test cache key generation."""
        # Relationship key
        key = CacheKeyBuilder.build_relationship_key(
            "entity1", "tasks", 2, {"status": "open"}
        )
        assert "entity1" in key
        assert "tasks" in key
        assert "2" in key
        
        # Path key
        key = CacheKeyBuilder.build_path_key("from1", "to1", 5)
        assert key == "path:from1:to1:5"
        
        # Graph key (consistent ordering)
        key1 = CacheKeyBuilder.build_graph_key(["b", "a", "c"], 3)
        key2 = CacheKeyBuilder.build_graph_key(["c", "a", "b"], 3)
        assert key1 == key2  # Same key despite different order


class TestRelationshipGraph:
    """Test cases for RelationshipGraph."""
    
    def test_graph_operations(self):
        """Test basic graph operations."""
        graph = RelationshipGraph()
        
        # Add nodes
        entity1 = {"id": "1", "name": "Entity 1"}
        entity2 = {"id": "2", "name": "Entity 2"}
        
        graph.add_node(entity1)
        graph.add_node(entity2)
        
        assert "1" in graph.nodes
        assert "2" in graph.nodes
        
        # Add edge
        graph.add_edge("1", "2", "related_to")
        
        neighbors = graph.get_neighbors("1")
        assert len(neighbors) == 1
        assert neighbors[0] == ("2", "related_to")
    
    def test_cycle_detection(self):
        """Test cycle detection in graph."""
        graph = RelationshipGraph()
        
        # Create graph with cycle
        for i in range(4):
            graph.add_node({"id": str(i)})
        
        graph.add_edge("0", "1", "next")
        graph.add_edge("1", "2", "next")
        graph.add_edge("2", "3", "next")
        graph.add_edge("3", "0", "next")  # Creates cycle
        
        assert graph.has_cycle() is True
        
        # Graph without cycle
        graph2 = RelationshipGraph()
        for i in range(4):
            graph2.add_node({"id": str(i)})
        
        graph2.add_edge("0", "1", "next")
        graph2.add_edge("0", "2", "next")
        graph2.add_edge("1", "3", "next")
        
        assert graph2.has_cycle() is False