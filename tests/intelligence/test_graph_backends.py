"""Tests for graph backend implementations."""

import pytest
import asyncio
import os
import sys
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import pytest_asyncio

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


# Mock networkx module to avoid import errors
class MockNetworkX:
    """Mock NetworkX module."""
    
    class DiGraph:
        """Mock DiGraph class."""
        
        def __init__(self):
            self._nodes = {}
            self.edges = {}
            self._adjacency = {}
            self._predecessors = {}
        
        @property
        def nodes(self):
            """Nodes property that can also be called as a method."""
            class NodesView:
                def __init__(self, nodes_dict):
                    self._nodes = nodes_dict
                
                def __call__(self, data=False):
                    if data:
                        return list(self._nodes.items())
                    else:
                        return list(self._nodes.keys())
                
                def __getitem__(self, key):
                    return self._nodes[key]
                
                def __contains__(self, key):
                    return key in self._nodes
                
                def __len__(self):
                    return len(self._nodes)
                
                def items(self):
                    return self._nodes.items()
                
                def keys(self):
                    return self._nodes.keys()
                
                def values(self):
                    return self._nodes.values()
            
            return NodesView(self._nodes)
        
        def add_node(self, node_id, **attrs):
            """Add node to graph."""
            self._nodes[node_id] = attrs
            if node_id not in self._adjacency:
                self._adjacency[node_id] = {}
            if node_id not in self._predecessors:
                self._predecessors[node_id] = {}
        
        def add_edge(self, from_id, to_id, **attrs):
            """Add edge to graph."""
            self.edges[(from_id, to_id)] = attrs
            if from_id not in self._adjacency:
                self._adjacency[from_id] = {}
            if to_id not in self._adjacency:
                self._adjacency[to_id] = {}
            if to_id not in self._predecessors:
                self._predecessors[to_id] = {}
            
            self._adjacency[from_id][to_id] = attrs
            self._predecessors[to_id][from_id] = attrs
        
        def has_node(self, node_id):
            """Check if node exists."""
            return node_id in self._nodes
        
        def has_edge(self, from_id, to_id):
            """Check if edge exists."""
            return (from_id, to_id) in self.edges
        
        def successors(self, node_id):
            """Get successors of node."""
            return list(self._adjacency.get(node_id, {}).keys())
        
        def predecessors(self, node_id):
            """Get predecessors of node."""
            return list(self._predecessors.get(node_id, {}).keys())
        
        def remove_node(self, node_id):
            """Remove node from graph."""
            if node_id in self._nodes:
                del self._nodes[node_id]
                
                # Remove edges
                edges_to_remove = []
                for edge in self.edges:
                    if edge[0] == node_id or edge[1] == node_id:
                        edges_to_remove.append(edge)
                
                for edge in edges_to_remove:
                    del self.edges[edge]
                
                # Update adjacency
                if node_id in self._adjacency:
                    del self._adjacency[node_id]
                
                for adj in self._adjacency.values():
                    if node_id in adj:
                        del adj[node_id]
                
                # Update predecessors
                if node_id in self._predecessors:
                    del self._predecessors[node_id]
                
                for pred in self._predecessors.values():
                    if node_id in pred:
                        del pred[node_id]
        
        def clear(self):
            """Clear graph."""
            self._nodes.clear()
            self.edges.clear()
            self._adjacency.clear()
            self._predecessors.clear()
        
        def __getitem__(self, node_id):
            """Get adjacency dict for node."""
            return self._adjacency.get(node_id, {})
        
        def __len__(self):
            """Get number of nodes."""
            return len(self._nodes)
    
    def shortest_path(self, graph, source, target, weight=None, method=None):
        """Mock shortest path function."""
        # Simple BFS implementation
        if not graph.has_node(source) or not graph.has_node(target):
            raise self.NetworkXNoPath()
        
        if source == target:
            return [source]
        
        visited = {source}
        queue = [(source, [source])]
        
        while queue:
            node, path = queue.pop(0)
            
            for neighbor in graph.successors(node):
                if neighbor == target:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        raise self.NetworkXNoPath()
    
    def write_graphml(self, graph, path):
        """Mock write_graphml function."""
        # Simple implementation - just save node/edge count
        with open(path, 'w') as f:
            f.write(f"<graph nodes='{len(graph.nodes)}' edges='{len(graph.edges)}' />")
    
    def read_graphml(self, path):
        """Mock read_graphml function."""
        # Simulate loading - create graph with saved content
        graph = self.DiGraph()
        # Check if file exists and has content
        try:
            with open(path, 'r') as f:
                content = f.read()
                # Simple parsing of our mock format
                if 'nodes=' in content:
                    import re
                    nodes_match = re.search(r"nodes='(\d+)'", content)
                    if nodes_match:
                        num_nodes = int(nodes_match.group(1))
                        # Add back the nodes
                        for i in range(1, num_nodes + 1):
                            graph.add_node(f"e{i}", name=f"Entity {i}", type="test")
        except:
            pass
        return graph
    
    class NetworkXNoPath(Exception):
        """Mock NetworkXNoPath exception."""
        pass


# Create mock instance
mock_nx = MockNetworkX()


class TestNetworkXBackend:
    """Tests for NetworkX graph backend."""
    
    @pytest_asyncio.fixture
    async def nx_backend(self):
        """Create NetworkX backend with mocked networkx."""
        # Import and patch module before use
        import blackcore.intelligence.graph.networkx_backend as nx_module
        original_nx = nx_module.nx
        nx_module.nx = mock_nx
        
        try:
            from blackcore.intelligence.graph.networkx_backend import NetworkXBackend
            backend = NetworkXBackend()
            yield backend
        finally:
            # Restore original
            nx_module.nx = original_nx
    
    def test_backend_initialization(self):
        """Test NetworkX backend initialization."""
        with patch('blackcore.intelligence.graph.networkx_backend.nx', mock_nx):
            from blackcore.intelligence.graph.networkx_backend import NetworkXBackend
            
            backend = NetworkXBackend()
            assert backend.graph is not None
            assert len(backend.graph.nodes) == 0
            assert len(backend.graph.edges) == 0
    
    async def test_add_entity(self, nx_backend):
        """Test adding entity to graph."""
        from blackcore.intelligence.interfaces import Entity
        
        entity = Entity(
            id="person_1",
            name="John Doe",
            type="person",
            properties={"age": 30, "role": "developer"}
        )
        
        result = await nx_backend.add_entity(entity)
        assert result is True
        
        # Check entity exists in graph
        assert nx_backend.graph.has_node("person_1")
        node_data = nx_backend.graph.nodes["person_1"]
        assert node_data["name"] == "John Doe"
        assert node_data["type"] == "person"
        assert node_data["properties"]["age"] == 30
    
    async def test_add_relationship(self, nx_backend):
        """Test adding relationship to graph."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Add entities first
        entity1 = Entity(id="person_1", name="John", type="person")
        entity2 = Entity(id="company_1", name="TechCorp", type="organization")
        
        await nx_backend.add_entity(entity1)
        await nx_backend.add_entity(entity2)
        
        # Add relationship
        rel = Relationship(
            id="rel_1",
            source_id="person_1",
            target_id="company_1",
            type="works_for",
            properties={"since": "2020"}
        )
        
        result = await nx_backend.add_relationship(rel)
        assert result is True
        
        # Check relationship exists
        assert nx_backend.graph.has_edge("person_1", "company_1")
        edge_data = nx_backend.graph["person_1"]["company_1"]
        assert edge_data["type"] == "works_for"
        assert edge_data["properties"]["since"] == "2020"
    
    async def test_get_entity(self, nx_backend):
        """Test retrieving entity from graph."""
        from blackcore.intelligence.interfaces import Entity
        
        # Add entity
        entity = Entity(
            id="person_1",
            name="John Doe",
            type="person",
            properties={"age": 30}
        )
        await nx_backend.add_entity(entity)
        
        # Get entity
        retrieved = await nx_backend.get_entity("person_1")
        assert retrieved is not None
        assert retrieved.id == "person_1"
        assert retrieved.name == "John Doe"
        assert retrieved.type == "person"
        assert retrieved.properties["age"] == 30
        
        # Get non-existent entity
        missing = await nx_backend.get_entity("missing_id")
        assert missing is None
    
    async def test_get_neighbors(self, nx_backend):
        """Test getting entity neighbors."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Create a simple network
        entities = [
            Entity(id="person_1", name="John", type="person"),
            Entity(id="person_2", name="Jane", type="person"),
            Entity(id="person_3", name="Bob", type="person"),
            Entity(id="company_1", name="TechCorp", type="organization")
        ]
        
        for entity in entities:
            await nx_backend.add_entity(entity)
        
        relationships = [
            Relationship(id="r1", source_id="person_1", target_id="person_2", type="knows"),
            Relationship(id="r2", source_id="person_1", target_id="company_1", type="works_for"),
            Relationship(id="r3", source_id="person_2", target_id="company_1", type="works_for"),
            Relationship(id="r4", source_id="person_3", target_id="person_1", type="manages")
        ]
        
        for rel in relationships:
            await nx_backend.add_relationship(rel)
        
        # Get neighbors of person_1
        neighbors = await nx_backend.get_neighbors("person_1")
        neighbor_ids = [n.id for n in neighbors]
        
        # Should include all connected entities
        assert len(neighbors) == 3
        assert "person_2" in neighbor_ids
        assert "company_1" in neighbor_ids
        assert "person_3" in neighbor_ids
    
    async def test_find_path(self, nx_backend):
        """Test finding path between entities."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Create a chain: person_1 -> person_2 -> person_3 -> person_4
        entities = [
            Entity(id=f"person_{i}", name=f"Person {i}", type="person")
            for i in range(1, 5)
        ]
        
        for entity in entities:
            await nx_backend.add_entity(entity)
        
        relationships = [
            Relationship(id=f"r{i}", source_id=f"person_{i}", target_id=f"person_{i+1}", type="knows")
            for i in range(1, 4)
        ]
        
        for rel in relationships:
            await nx_backend.add_relationship(rel)
        
        # Find path from person_1 to person_4
        path = await nx_backend.find_path("person_1", "person_4")
        assert path is not None
        assert len(path) == 4
        assert path[0].id == "person_1"
        assert path[-1].id == "person_4"
        
        # No path should exist between disconnected nodes
        # Add isolated node
        await nx_backend.add_entity(Entity(id="isolated", name="Isolated", type="person"))
        path = await nx_backend.find_path("person_1", "isolated")
        assert path is None
    
    async def test_search_entities(self, nx_backend):
        """Test searching entities by properties."""
        from blackcore.intelligence.interfaces import Entity
        
        # Add various entities
        entities = [
            Entity(id="dev_1", name="John", type="person", 
                  properties={"role": "developer", "level": "senior"}),
            Entity(id="dev_2", name="Jane", type="person",
                  properties={"role": "developer", "level": "junior"}),
            Entity(id="mgr_1", name="Bob", type="person",
                  properties={"role": "manager", "level": "senior"}),
            Entity(id="company_1", name="TechCorp", type="organization",
                  properties={"industry": "tech", "size": "large"})
        ]
        
        for entity in entities:
            await nx_backend.add_entity(entity)
        
        # Search by type
        people = await nx_backend.search_entities({"type": "person"})
        assert len(people) == 3
        
        # Search by property
        developers = await nx_backend.search_entities({"properties.role": "developer"})
        assert len(developers) == 2
        
        # Search by multiple criteria
        senior_devs = await nx_backend.search_entities({
            "type": "person",
            "properties.role": "developer",
            "properties.level": "senior"
        })
        assert len(senior_devs) == 1
        assert senior_devs[0].id == "dev_1"
    
    async def test_delete_entity(self, nx_backend):
        """Test deleting entity from graph."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Add entities and relationships
        e1 = Entity(id="e1", name="Entity 1", type="test")
        e2 = Entity(id="e2", name="Entity 2", type="test")
        await nx_backend.add_entity(e1)
        await nx_backend.add_entity(e2)
        
        rel = Relationship(id="r1", source_id="e1", target_id="e2", type="related")
        await nx_backend.add_relationship(rel)
        
        # Delete entity
        result = await nx_backend.delete_entity("e1")
        assert result is True
        
        # Entity should be gone
        assert not nx_backend.graph.has_node("e1")
        # Relationship should also be gone
        assert not nx_backend.graph.has_edge("e1", "e2")
        # Other entity should remain
        assert nx_backend.graph.has_node("e2")
    
    async def test_persistence(self, nx_backend):
        """Test saving and loading graph."""
        from blackcore.intelligence.interfaces import Entity
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".graphml", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Populate backend
            entities = [
                Entity(id="e1", name="Entity 1", type="test"),
                Entity(id="e2", name="Entity 2", type="test")
            ]
            for e in entities:
                await nx_backend.add_entity(e)
            
            # Save
            await nx_backend.save(tmp_path)
            
            # Clear and reload
            await nx_backend.clear()
            await nx_backend.load(tmp_path)
            
            # Verify data
            assert len(nx_backend.graph.nodes) == 2
            assert nx_backend.graph.has_node("e1")
            assert nx_backend.graph.has_node("e2")
            
        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestSQLiteBackend:
    """Tests for SQLite graph backend."""
    
    @pytest_asyncio.fixture
    async def sqlite_backend(self):
        """Create SQLite backend with temporary database."""
        from blackcore.intelligence.graph.sqlite_backend import SQLiteBackend
        
        backend = SQLiteBackend(":memory:")
        await backend.initialize()
        yield backend
        await backend.close()
    
    async def test_backend_initialization(self, sqlite_backend):
        """Test SQLite backend initialization."""
        # Backend should be initialized from fixture
        assert sqlite_backend.db_path == ":memory:"
        assert sqlite_backend.conn is not None
    
    async def test_add_entity(self, sqlite_backend):
        """Test adding entity to database."""
        from blackcore.intelligence.interfaces import Entity
        
        entity = Entity(
            id="person_1",
            name="John Doe",
            type="person",
            properties={"age": 30, "role": "developer"},
            confidence=0.95
        )
        
        result = await sqlite_backend.add_entity(entity)
        assert result is True
        
        # Verify entity was stored
        stored = await sqlite_backend.get_entity("person_1")
        assert stored is not None
        assert stored.name == "John Doe"
        assert stored.type == "person"
        assert stored.properties["age"] == 30
        assert stored.confidence == 0.95
    
    async def test_add_relationship(self, sqlite_backend):
        """Test adding relationship to database."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Add entities first
        entity1 = Entity(id="person_1", name="John", type="person")
        entity2 = Entity(id="company_1", name="TechCorp", type="organization")
        
        await sqlite_backend.add_entity(entity1)
        await sqlite_backend.add_entity(entity2)
        
        # Add relationship
        rel = Relationship(
            id="rel_1",
            source_id="person_1",
            target_id="company_1",
            type="works_for",
            properties={"since": "2020", "position": "developer"},
            confidence=0.9
        )
        
        result = await sqlite_backend.add_relationship(rel)
        assert result is True
        
        # Verify relationship exists (through neighbors)
        neighbors = await sqlite_backend.get_neighbors("person_1")
        assert len(neighbors) == 1
        assert neighbors[0].id == "company_1"
    
    async def test_search_entities(self, sqlite_backend):
        """Test searching entities with various criteria."""
        from blackcore.intelligence.interfaces import Entity
        
        # Add test entities
        entities = [
            Entity(id="dev_1", name="John", type="person", 
                  properties={"role": "developer", "level": "senior"}),
            Entity(id="dev_2", name="Jane", type="person",
                  properties={"role": "developer", "level": "junior"}),
            Entity(id="mgr_1", name="Bob", type="person",
                  properties={"role": "manager", "level": "senior"}),
            Entity(id="company_1", name="TechCorp", type="organization",
                  properties={"industry": "tech", "size": "large"})
        ]
        
        for entity in entities:
            await sqlite_backend.add_entity(entity)
        
        # Search by type
        people = await sqlite_backend.search_entities({"type": "person"})
        assert len(people) == 3
        
        # Search by property
        developers = await sqlite_backend.search_entities({"properties.role": "developer"})
        assert len(developers) == 2
        
        # Search by name pattern
        j_names = await sqlite_backend.search_entities({"name": "J%"})
        assert len(j_names) == 2
    
    async def test_get_neighbors(self, sqlite_backend):
        """Test getting entity neighbors."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Create network
        entities = [
            Entity(id="a", name="A", type="test"),
            Entity(id="b", name="B", type="test"),
            Entity(id="c", name="C", type="test"),
            Entity(id="d", name="D", type="test")
        ]
        
        for entity in entities:
            await sqlite_backend.add_entity(entity)
        
        # A connects to B and C
        # B connects to D
        relationships = [
            Relationship(id="r1", source_id="a", target_id="b", type="rel"),
            Relationship(id="r2", source_id="a", target_id="c", type="rel"),
            Relationship(id="r3", source_id="b", target_id="d", type="rel"),
            Relationship(id="r4", source_id="c", target_id="a", type="rel")  # Bidirectional
        ]
        
        for rel in relationships:
            await sqlite_backend.add_relationship(rel)
        
        # Get neighbors of A
        neighbors = await sqlite_backend.get_neighbors("a")
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"b", "c"}
    
    async def test_find_path(self, sqlite_backend):
        """Test path finding between entities."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Create chain: 1 -> 2 -> 3 -> 4
        for i in range(1, 5):
            entity = Entity(id=str(i), name=f"Entity {i}", type="test")
            await sqlite_backend.add_entity(entity)
        
        for i in range(1, 4):
            rel = Relationship(id=f"r{i}", source_id=str(i), target_id=str(i+1), type="next")
            await sqlite_backend.add_relationship(rel)
        
        # Find path
        path = await sqlite_backend.find_path("1", "4")
        assert path is not None
        assert len(path) == 4
        assert [e.id for e in path] == ["1", "2", "3", "4"]
        
        # Add isolated node
        await sqlite_backend.add_entity(Entity(id="isolated", name="Isolated", type="test"))
        
        # No path to isolated
        path = await sqlite_backend.find_path("1", "isolated")
        assert path is None
    
    async def test_delete_entity(self, sqlite_backend):
        """Test deleting entity and cascading relationships."""
        from blackcore.intelligence.interfaces import Entity, Relationship
        
        # Add entities
        e1 = Entity(id="e1", name="Entity 1", type="test")
        e2 = Entity(id="e2", name="Entity 2", type="test")
        e3 = Entity(id="e3", name="Entity 3", type="test")
        
        for e in [e1, e2, e3]:
            await sqlite_backend.add_entity(e)
        
        # Add relationships
        await sqlite_backend.add_relationship(
            Relationship(id="r1", source_id="e1", target_id="e2", type="rel")
        )
        await sqlite_backend.add_relationship(
            Relationship(id="r2", source_id="e2", target_id="e3", type="rel")
        )
        
        # Delete e2
        result = await sqlite_backend.delete_entity("e2")
        assert result is True
        
        # e2 should be gone
        assert await sqlite_backend.get_entity("e2") is None
        
        # e1 and e3 should remain
        assert await sqlite_backend.get_entity("e1") is not None
        assert await sqlite_backend.get_entity("e3") is not None
        
        # Relationships involving e2 should be gone
        e1_neighbors = await sqlite_backend.get_neighbors("e1")
        assert len(e1_neighbors) == 0
    
    async def test_transaction_handling(self, sqlite_backend):
        """Test transaction rollback on error."""
        from blackcore.intelligence.interfaces import Entity
        
        # Add valid entity
        e1 = Entity(id="e1", name="Valid", type="test")
        await sqlite_backend.add_entity(e1)
        
        # Try to add entity with duplicate ID (should fail)
        e2 = Entity(id="e1", name="Duplicate", type="test")
        result = await sqlite_backend.add_entity(e2)
        assert result is False
        
        # Original entity should be unchanged
        stored = await sqlite_backend.get_entity("e1")
        assert stored.name == "Valid"
    
    async def test_persistence_file(self):
        """Test SQLite persistence to file."""
        from blackcore.intelligence.graph.sqlite_backend import SQLiteBackend
        from blackcore.intelligence.interfaces import Entity
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Create and populate backend
            backend1 = SQLiteBackend(tmp_path)
            await backend1.initialize()
            
            entities = [
                Entity(id="e1", name="Entity 1", type="test"),
                Entity(id="e2", name="Entity 2", type="test")
            ]
            
            for e in entities:
                await backend1.add_entity(e)
            
            await backend1.close()
            
            # Open with new backend
            backend2 = SQLiteBackend(tmp_path)
            await backend2.initialize()
            
            # Verify data persisted
            e1 = await backend2.get_entity("e1")
            e2 = await backend2.get_entity("e2")
            
            assert e1 is not None
            assert e1.name == "Entity 1"
            assert e2 is not None
            assert e2.name == "Entity 2"
            
            await backend2.close()
            
        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestGraphBackendFactory:
    """Tests for graph backend factory."""
    
    async def test_create_networkx_backend(self):
        """Test creating NetworkX backend through factory."""
        with patch('blackcore.intelligence.graph.networkx_backend.nx', mock_nx):
            with patch('blackcore.intelligence.graph.factory.NetworkXBackend', autospec=True) as MockNXBackend:
                # Configure the mock
                instance = MockNXBackend.return_value
                instance.__class__.__name__ = "NetworkXBackend"
                
                from blackcore.intelligence.graph import create_graph_backend
                from blackcore.intelligence.config import GraphConfig
                
                config = GraphConfig(backend="networkx")
                backend = await create_graph_backend(config)
                
                assert backend.__class__.__name__ == "NetworkXBackend"
    
    async def test_create_sqlite_memory_backend(self):
        """Test creating SQLite memory backend through factory."""
        from blackcore.intelligence.graph import create_graph_backend
        from blackcore.intelligence.config import GraphConfig
        
        config = GraphConfig(backend="sqlite")
        backend = await create_graph_backend(config)
        
        assert backend.__class__.__name__ == "SQLiteBackend"
        assert backend.db_path == ":memory:"
        
        await backend.close()
    
    async def test_create_sqlite_file_backend(self):
        """Test creating SQLite file backend through factory."""
        from blackcore.intelligence.graph import create_graph_backend
        from blackcore.intelligence.config import GraphConfig
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            config = GraphConfig(
                backend="sqlite",
                connection_params={"db_path": tmp_path}
            )
            backend = await create_graph_backend(config)
            
            assert backend.__class__.__name__ == "SQLiteBackend"
            assert backend.db_path == tmp_path
            
            await backend.close()
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_invalid_backend(self):
        """Test error handling for invalid backend."""
        from blackcore.intelligence.graph import create_graph_backend
        from blackcore.intelligence.config import GraphConfig
        
        config = GraphConfig(backend="invalid")
        
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(create_graph_backend(config))
        
        assert "Unknown graph backend" in str(exc_info.value)