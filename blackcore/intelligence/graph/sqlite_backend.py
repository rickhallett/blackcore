"""SQLite-based graph backend implementation."""

import json
import sqlite3
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..interfaces import IGraphBackend, Entity, Relationship

logger = logging.getLogger(__name__)


class SQLiteBackend(IGraphBackend):
    """SQLite-based persistent graph backend."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize database and create tables."""
        async with self._lock:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            
            # Create entities table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create relationships table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_id) REFERENCES entities (id) ON DELETE CASCADE,
                    FOREIGN KEY (to_id) REFERENCES entities (id) ON DELETE CASCADE,
                    UNIQUE (from_id, to_id, type)
                )
            """)
            
            # Create indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships (from_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships (to_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships (type)")
            
            self.conn.commit()
    
    async def add_entity(self, entity: Entity) -> bool:
        """Add entity to database."""
        async with self._lock:
            try:
                # Check if entity already exists
                cursor = self.conn.execute(
                    "SELECT COUNT(*) FROM entities WHERE id = ?",
                    (entity.id,)
                )
                count = cursor.fetchone()[0]
                if count > 0:
                    logger.warning(f"Entity {entity.id} already exists")
                    return False
                
                # Insert new entity
                self.conn.execute("""
                    INSERT INTO entities 
                    (id, name, type, properties, confidence, source, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.id,
                    entity.name,
                    entity.type,
                    json.dumps(entity.properties),
                    entity.confidence,
                    entity.source,
                    entity.timestamp.isoformat()
                ))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to add entity {entity.id}: {e}")
                self.conn.rollback()
                return False
    
    async def add_relationship(self, relationship: Relationship) -> bool:
        """Add relationship to database."""
        async with self._lock:
            try:
                # Check if entities exist
                cursor = self.conn.execute(
                    "SELECT COUNT(*) FROM entities WHERE id IN (?, ?)",
                    (relationship.source_id, relationship.target_id)
                )
                count = cursor.fetchone()[0]
                if count != 2:
                    logger.warning("One or both entities do not exist")
                    return False
                
                self.conn.execute("""
                    INSERT OR REPLACE INTO relationships 
                    (from_id, to_id, type, properties, confidence, source, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    relationship.source_id,
                    relationship.target_id,
                    relationship.type,
                    json.dumps(relationship.properties),
                    relationship.confidence,
                    None,  # Relationship doesn't have source attribute
                    relationship.timestamp.isoformat()
                ))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to add relationship: {e}")
                self.conn.rollback()
                return False
    
    def _get_entity_no_lock(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID without acquiring lock (internal use only)."""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM entities WHERE id = ?",
                (entity_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Entity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                properties=json.loads(row["properties"] or "{}"),
                confidence=row["confidence"],
                source=row["source"],
                timestamp=datetime.fromisoformat(row["timestamp"])
            )
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        async with self._lock:
            return self._get_entity_no_lock(entity_id)
    
    async def get_neighbors(
        self, 
        entity_id: str, 
        relationship_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Entity]:
        """Get neighboring entities."""
        neighbors = []
        
        async with self._lock:
            try:
                queries = []
                params = []
                
                # Outgoing relationships
                if direction in ["out", "both"]:
                    query = """
                        SELECT DISTINCT e.* FROM entities e
                        JOIN relationships r ON e.id = r.to_id
                        WHERE r.from_id = ?
                    """
                    if relationship_type:
                        query += " AND r.type = ?"
                        queries.append((query, (entity_id, relationship_type)))
                    else:
                        queries.append((query, (entity_id,)))
                
                # Incoming relationships
                if direction in ["in", "both"]:
                    query = """
                        SELECT DISTINCT e.* FROM entities e
                        JOIN relationships r ON e.id = r.from_id
                        WHERE r.to_id = ?
                    """
                    if relationship_type:
                        query += " AND r.type = ?"
                        queries.append((query, (entity_id, relationship_type)))
                    else:
                        queries.append((query, (entity_id,)))
                
                # Execute queries and collect results
                seen_ids = set()
                for query, params in queries:
                    cursor = self.conn.execute(query, params)
                    for row in cursor:
                        if row["id"] not in seen_ids:
                            seen_ids.add(row["id"])
                            entity = Entity(
                                id=row["id"],
                                name=row["name"],
                                type=row["type"],
                                properties=json.loads(row["properties"] or "{}"),
                                confidence=row["confidence"],
                                source=row["source"],
                                timestamp=datetime.fromisoformat(row["timestamp"])
                            )
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
        """Find shortest path between entities using BFS."""
        if from_id == to_id:
            entity = await self.get_entity(from_id)
            return [entity] if entity else None
        
        async with self._lock:
            try:
                # BFS to find shortest path
                queue = [(from_id, [from_id])]
                visited = {from_id}
                
                while queue:
                    current_id, path = queue.pop(0)
                    
                    # Check path length limit
                    if max_length and len(path) > max_length:
                        continue
                    
                    # Get neighbors
                    cursor = self.conn.execute("""
                        SELECT DISTINCT to_id FROM relationships WHERE from_id = ?
                        UNION
                        SELECT DISTINCT from_id FROM relationships WHERE to_id = ?
                    """, (current_id, current_id))
                    
                    for row in cursor:
                        neighbor_id = row[0]
                        
                        if neighbor_id == to_id:
                            # Found target - reconstruct path
                            full_path = path + [neighbor_id]
                            entities = []
                            
                            for node_id in full_path:
                                entity = self._get_entity_no_lock(node_id)
                                if entity:
                                    entities.append(entity)
                            
                            return entities
                        
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            queue.append((neighbor_id, path + [neighbor_id]))
                
                return None
                
            except Exception as e:
                logger.error(f"Failed to find path from {from_id} to {to_id}: {e}")
                return None
    
    async def search_entities(self, criteria: Dict[str, Any]) -> List[Entity]:
        """Search entities by criteria."""
        results = []
        
        async with self._lock:
            try:
                # Build query
                conditions = []
                params = []
                
                for key, value in criteria.items():
                    if key == "type":
                        conditions.append("type = ?")
                        params.append(value)
                    elif key == "name":
                        # Support pattern matching
                        if "%" in str(value):
                            conditions.append("name LIKE ?")
                        else:
                            conditions.append("name = ?")
                        params.append(value)
                    elif key.startswith("properties."):
                        # JSON search
                        prop_key = key[11:]
                        conditions.append(f"json_extract(properties, '$.{prop_key}') = ?")
                        params.append(value)
                
                if not conditions:
                    return []
                
                query = f"SELECT * FROM entities WHERE {' AND '.join(conditions)}"
                cursor = self.conn.execute(query, params)
                
                for row in cursor:
                    entity = Entity(
                        id=row["id"],
                        name=row["name"],
                        type=row["type"],
                        properties=json.loads(row["properties"] or "{}"),
                        confidence=row["confidence"],
                        source=row["source"],
                        timestamp=datetime.fromisoformat(row["timestamp"])
                    )
                    results.append(entity)
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to search entities: {e}")
                return []
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and its relationships."""
        async with self._lock:
            try:
                # SQLite cascading delete will handle relationships
                self.conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to delete entity {entity_id}: {e}")
                self.conn.rollback()
                return False
    
    async def save(self, path: str) -> bool:
        """Save database (already persisted for file-based DB)."""
        if self.db_path == ":memory:":
            # For in-memory DB, create a backup
            try:
                backup_conn = sqlite3.connect(path)
                with backup_conn:
                    self.conn.backup(backup_conn)
                backup_conn.close()
                return True
            except Exception as e:
                logger.error(f"Failed to save database to {path}: {e}")
                return False
        return True
    
    async def load(self, path: str) -> bool:
        """Load database from file."""
        # For SQLite, this would typically mean switching to a new database
        # For simplicity, we'll just log a warning
        logger.warning("Load operation not supported for SQLite backend after initialization")
        return False
    
    async def clear(self) -> bool:
        """Clear all data."""
        async with self._lock:
            try:
                self.conn.execute("DELETE FROM relationships")
                self.conn.execute("DELETE FROM entities")
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to clear database: {e}")
                self.conn.rollback()
                return False
    
    async def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    async def get_entities(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Get entities with optional filters."""
        if filters:
            return await self.search_entities(filters)
        
        async with self._lock:
            try:
                query = "SELECT * FROM entities"
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor = self.conn.execute(query)
                entities = []
                
                for row in cursor:
                    entity = Entity(
                        id=row["id"],
                        name=row["name"],
                        type=row["type"],
                        properties=json.loads(row["properties"] or "{}"),
                        confidence=row["confidence"],
                        source=row["source"],
                        timestamp=datetime.fromisoformat(row["timestamp"])
                    )
                    entities.append(entity)
                
                return entities
                
            except Exception as e:
                logger.error(f"Failed to get entities: {e}")
                return []
    
    async def get_relationships(
        self,
        entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Relationship]:
        """Get relationships with optional filters."""
        async with self._lock:
            try:
                conditions = []
                params = []
                
                if entity_id:
                    conditions.append("(from_id = ? OR to_id = ?)")
                    params.extend([entity_id, entity_id])
                
                if relationship_type:
                    conditions.append("type = ?")
                    params.append(relationship_type)
                
                query = "SELECT * FROM relationships"
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor = self.conn.execute(query, params)
                relationships = []
                
                for row in cursor:
                    rel = Relationship(
                        id=f"{row['from_id']}_{row['to_id']}_{row['type']}",
                        source_id=row["from_id"],
                        target_id=row["to_id"],
                        type=row["type"],
                        properties=json.loads(row["properties"] or "{}"),
                        confidence=row["confidence"],
                        timestamp=datetime.fromisoformat(row["timestamp"])
                    )
                    relationships.append(rel)
                
                return relationships
                
            except Exception as e:
                logger.error(f"Failed to get relationships: {e}")
                return []
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        async with self._lock:
            try:
                cursor = self.conn.execute(query)
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in cursor:
                    result = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        # Try to parse JSON fields
                        if column == "properties" and value:
                            try:
                                value = json.loads(value)
                            except:
                                pass
                        result[column] = value
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
                return []
    
    async def get_subgraph(
        self,
        entity_ids: List[str],
        max_depth: int = 1
    ) -> Dict[str, List[Any]]:
        """Get subgraph around entities."""
        result = {"entities": [], "relationships": []}
        visited_entities = set()
        
        async with self._lock:
            try:
                # BFS to explore subgraph
                queue = [(entity_id, 0) for entity_id in entity_ids]
                
                while queue:
                    current_id, depth = queue.pop(0)
                    
                    if current_id in visited_entities:
                        continue
                    
                    visited_entities.add(current_id)
                    
                    # Get entity
                    entity = self._get_entity_no_lock(current_id)
                    if entity:
                        result["entities"].append(entity)
                    
                    # Explore relationships if within depth
                    if depth < max_depth:
                        # Get all relationships for this entity
                        cursor = self.conn.execute("""
                            SELECT * FROM relationships 
                            WHERE from_id = ? OR to_id = ?
                        """, (current_id, current_id))
                        
                        for row in cursor:
                            rel = Relationship(
                                id=f"{row['from_id']}_{row['to_id']}_{row['type']}",
                                source_id=row["from_id"],
                                target_id=row["to_id"],
                                type=row["type"],
                                properties=json.loads(row["properties"] or "{}"),
                                confidence=row["confidence"],
                                timestamp=datetime.fromisoformat(row["timestamp"])
                            )
                            result["relationships"].append(rel)
                            
                            # Add connected entities to queue
                            if row["from_id"] == current_id:
                                neighbor_id = row["to_id"]
                            else:
                                neighbor_id = row["from_id"]
                            
                            if neighbor_id not in visited_entities:
                                queue.append((neighbor_id, depth + 1))
                
                # Remove duplicate relationships
                seen = set()
                unique_relationships = []
                for rel in result["relationships"]:
                    key = (rel.from_id, rel.to_id, rel.type)
                    if key not in seen:
                        seen.add(key)
                        unique_relationships.append(rel)
                
                result["relationships"] = unique_relationships
                return result
                
            except Exception as e:
                logger.error(f"Failed to get subgraph: {e}")
                return {"entities": [], "relationships": []}