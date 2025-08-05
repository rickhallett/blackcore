"""World engine that orchestrates all systems."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

import redis.asyncio as redis
import structlog
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field

from ..core.entity import Entity, EntityQuery, Identity, Position, Properties
from ..core.events import Event, EventBus, EventHandler, EventStore
from ..core.modifiers import ModifierStack
from ..core.relationships import HyperEdge, RelationshipGraph, RelationshipType
from ..core.resources import Resource, ResourceBundle, ResourceExchange, ResourceType

logger = structlog.get_logger()


class WorldConfig(BaseModel):
    """Configuration for world engine."""
    world_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Emergent World"
    tick_rate: float = 1.0  # Seconds between ticks
    max_entities: int = 10000
    redis_url: str = "redis://localhost:6379"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    enable_persistence: bool = True
    enable_ai: bool = True


class SystemPriority:
    """System execution priorities."""
    HIGHEST = 0
    HIGH = 100
    NORMAL = 500
    LOW = 900
    LOWEST = 999


class WorldSystem:
    """Base class for world systems."""
    
    def __init__(self, name: str, priority: int = SystemPriority.NORMAL):
        self.name = name
        self.priority = priority
        self.enabled = True
    
    async def initialize(self, world: World) -> None:
        """Initialize system with world reference."""
        pass
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update system logic."""
        pass
    
    async def shutdown(self) -> None:
        """Clean up system resources."""
        pass


class ResourceSystem(WorldSystem):
    """System for updating resources over time."""
    
    def __init__(self):
        super().__init__("ResourceSystem", SystemPriority.HIGH)
        self.exchange = ResourceExchange()
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update all entity resources."""
        query = EntityQuery(world.entities).with_component(ResourceBundle)
        
        for entity in query.execute():
            bundle = entity.get_component(ResourceBundle)
            if bundle:
                bundle.update(delta_time)
                
                # Check for resource events
                for resource_type, resource in bundle.resources.items():
                    if resource.amount <= 0 and not resource.constraints.can_be_negative:
                        world.event_bus.emit(Event(
                            event_type="resource_depleted",
                            entity_id=entity.id,
                            data={"resource_type": resource_type}
                        ))


class ModifierSystem(WorldSystem):
    """System for updating modifiers."""
    
    def __init__(self):
        super().__init__("ModifierSystem", SystemPriority.HIGH)
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update all entity modifiers."""
        query = EntityQuery(world.entities).with_component(ModifierStack)
        
        for entity in query.execute():
            stack = entity.get_component(ModifierStack)
            if stack:
                expired = stack.update()
                
                # Emit events for expired modifiers
                for modifier_id in expired:
                    world.event_bus.emit(Event(
                        event_type="modifier_expired",
                        entity_id=entity.id,
                        data={"modifier_id": modifier_id}
                    ))


class RelationshipSystem(WorldSystem):
    """System for relationship decay and updates."""
    
    def __init__(self):
        super().__init__("RelationshipSystem", SystemPriority.NORMAL)
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update relationship strengths over time."""
        # Decay relationships without interaction
        for edge in world.relationships.hyperedges.values():
            decay_rate = edge.properties.metadata.get("decay_rate", 0.0)
            if decay_rate > 0:
                edge.properties.weight *= (1.0 - decay_rate * delta_time)
                
                # Remove very weak relationships
                if edge.properties.weight < 0.01:
                    world.relationships.remove_relationship(edge.id)
                    world.event_bus.emit(Event(
                        event_type="relationship_broken",
                        data={
                            "edge_id": edge.id,
                            "entities": list(edge.entities)
                        }
                    ))


class SpatialSystem(WorldSystem):
    """System for spatial queries and movement."""
    
    def __init__(self):
        super().__init__("SpatialSystem", SystemPriority.HIGH)
        self.spatial_index: Dict[str, Set[str]] = {}  # region -> entity_ids
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update spatial index."""
        self.spatial_index.clear()
        
        query = EntityQuery(world.entities).with_component(Position)
        for entity in query.execute():
            pos = entity.position
            if pos and pos.region:
                if pos.region not in self.spatial_index:
                    self.spatial_index[pos.region] = set()
                self.spatial_index[pos.region].add(entity.id)
    
    def get_entities_in_region(self, region: str) -> Set[str]:
        """Get all entities in a region."""
        return self.spatial_index.get(region, set())
    
    def get_nearby_entities(
        self,
        entity_id: str,
        radius: float = 10.0
    ) -> List[Tuple[str, float]]:
        """Get entities within radius of given entity."""
        entity = self.world.entities.get(entity_id)
        if not entity or not entity.position:
            return []
        
        pos = entity.position
        nearby = []
        
        # Check entities in same region
        for other_id in self.get_entities_in_region(pos.region):
            if other_id == entity_id:
                continue
            
            other = self.world.entities.get(other_id)
            if other and other.position:
                distance = (
                    (other.position.x - pos.x) ** 2 +
                    (other.position.y - pos.y) ** 2 +
                    (other.position.z - pos.z) ** 2
                ) ** 0.5
                
                if distance <= radius:
                    nearby.append((other_id, distance))
        
        return sorted(nearby, key=lambda x: x[1])


class World:
    """Main world container and orchestrator."""
    
    def __init__(self, config: Optional[WorldConfig] = None):
        self.config = config or WorldConfig()
        self.entities: Dict[str, Entity] = {}
        self.event_bus = EventBus()
        self.relationships = RelationshipGraph(self.event_bus)
        self.systems: List[WorldSystem] = []
        self.running = False
        self.tick_count = 0
        self.start_time = time.time()
        self.last_tick = self.start_time
        
        # External connections
        self._redis: Optional[redis.Redis] = None
        self._neo4j_driver = None
        
        # Register default systems
        self._register_default_systems()
        
        logger.info(
            "world_created",
            world_id=self.config.world_id,
            name=self.config.name
        )
    
    def _register_default_systems(self) -> None:
        """Register default world systems."""
        self.add_system(ResourceSystem())
        self.add_system(ModifierSystem())
        self.add_system(RelationshipSystem())
        self.add_system(SpatialSystem())
    
    def add_system(self, system: WorldSystem) -> None:
        """Add a system to the world."""
        self.systems.append(system)
        self.systems.sort(key=lambda s: s.priority)
    
    def create_entity(
        self,
        name: Optional[str] = None,
        entity_type: str = "generic",
        position: Optional[Position] = None,
        **properties
    ) -> Entity:
        """Create a new entity in the world."""
        if len(self.entities) >= self.config.max_entities:
            raise ValueError(f"Maximum entity limit ({self.config.max_entities}) reached")
        
        entity = Entity(event_bus=self.event_bus)
        
        # Add identity
        entity.add_component(Identity(
            name=name or f"Entity_{entity.id[:8]}",
            entity_type=entity_type
        ))
        
        # Add position if provided
        if position:
            entity.add_component(position)
        
        # Add properties if provided
        if properties:
            props = Properties()
            props.data.update(properties)
            entity.add_component(props)
        
        # Add to world
        self.entities[entity.id] = entity
        
        # Emit creation event
        self.event_bus.emit(Event(
            event_type="entity_created",
            entity_id=entity.id,
            data={
                "name": entity.identity.name,
                "type": entity_type
            }
        ))
        
        logger.info(
            "entity_created",
            entity_id=entity.id,
            name=entity.identity.name,
            type=entity_type
        )
        
        return entity
    
    def remove_entity(self, entity_id: str) -> bool:
        """Remove entity from world."""
        if entity_id not in self.entities:
            return False
        
        entity = self.entities[entity_id]
        
        # Remove all relationships
        relationships = self.relationships.get_relationships(entity_id)
        for edge in relationships:
            self.relationships.remove_relationship(edge.id)
        
        # Remove entity
        del self.entities[entity_id]
        
        # Emit removal event
        self.event_bus.emit(Event(
            event_type="entity_removed",
            entity_id=entity_id,
            data={"name": entity.identity.name if entity.identity else "Unknown"}
        ))
        
        return True
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)
    
    def query_entities(self) -> EntityQuery:
        """Start a query for entities."""
        return EntityQuery(self.entities)
    
    async def initialize(self) -> None:
        """Initialize world and all systems."""
        # Start event bus
        await self.event_bus.start()
        
        # Initialize external connections
        if self.config.enable_persistence:
            self._redis = await redis.from_url(self.config.redis_url)
            self._neo4j_driver = AsyncGraphDatabase.driver(
                self.config.neo4j_url,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
        
        # Initialize all systems
        for system in self.systems:
            await system.initialize(self)
        
        logger.info("world_initialized", world_id=self.config.world_id)
    
    async def tick(self) -> None:
        """Execute one world tick."""
        current_time = time.time()
        delta_time = current_time - self.last_tick
        
        # Update all systems
        for system in self.systems:
            if system.enabled:
                try:
                    await system.update(self, delta_time)
                except Exception as e:
                    logger.error(
                        "system_update_error",
                        system=system.name,
                        error=str(e)
                    )
        
        self.last_tick = current_time
        self.tick_count += 1
    
    async def run(self) -> None:
        """Run world simulation loop."""
        self.running = True
        logger.info("world_started", world_id=self.config.world_id)
        
        while self.running:
            tick_start = time.time()
            
            await self.tick()
            
            # Sleep to maintain tick rate
            tick_duration = time.time() - tick_start
            sleep_time = self.config.tick_rate - tick_duration
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                logger.warning(
                    "tick_overrun",
                    duration=tick_duration,
                    target=self.config.tick_rate
                )
    
    async def stop(self) -> None:
        """Stop world simulation."""
        self.running = False
        
        # Shutdown systems
        for system in self.systems:
            await system.shutdown()
        
        # Stop event bus
        await self.event_bus.stop()
        
        # Close external connections
        if self._redis:
            await self._redis.close()
        
        if self._neo4j_driver:
            await self._neo4j_driver.close()
        
        logger.info("world_stopped", world_id=self.config.world_id)
    
    async def save_state(self) -> None:
        """Save world state to persistence layer."""
        if not self.config.enable_persistence:
            return
        
        # Save to Redis
        if self._redis:
            # Save world metadata
            await self._redis.hset(
                f"world:{self.config.world_id}",
                mapping={
                    "name": self.config.name,
                    "tick_count": str(self.tick_count),
                    "entity_count": str(len(self.entities)),
                    "last_save": str(time.time())
                }
            )
            
            # Save entities
            for entity_id, entity in self.entities.items():
                entity_data = {
                    "version": str(entity.version),
                    "created_at": str(entity.created_at),
                    "components": {}
                }
                
                # Serialize components
                for comp_name, component in entity.components.items():
                    entity_data["components"][comp_name] = component.pack().hex()
                
                await self._redis.hset(
                    f"entity:{entity_id}",
                    mapping=entity_data
                )
        
        # Save to Neo4j
        if self._neo4j_driver:
            async with self._neo4j_driver.session() as session:
                await self.relationships.persist_to_neo4j(session)
        
        logger.info(
            "world_saved",
            world_id=self.config.world_id,
            entities=len(self.entities)
        )
    
    async def load_state(self) -> None:
        """Load world state from persistence layer."""
        if not self.config.enable_persistence:
            return
        
        # Load from Redis
        if self._redis:
            # Load world metadata
            world_data = await self._redis.hgetall(f"world:{self.config.world_id}")
            if world_data:
                self.tick_count = int(world_data.get(b"tick_count", 0))
                logger.info(
                    "world_metadata_loaded",
                    world_id=self.config.world_id,
                    tick_count=self.tick_count
                )
        
        # Load from Neo4j
        if self._neo4j_driver:
            async with self._neo4j_driver.session() as session:
                await self.relationships.load_from_neo4j(session)
        
        logger.info("world_loaded", world_id=self.config.world_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get world statistics."""
        return {
            "world_id": self.config.world_id,
            "name": self.config.name,
            "tick_count": self.tick_count,
            "uptime": time.time() - self.start_time,
            "entity_count": len(self.entities),
            "relationship_count": len(self.relationships.hyperedges),
            "event_count": len(self.event_bus.event_store.events),
            "systems": [
                {
                    "name": system.name,
                    "priority": system.priority,
                    "enabled": system.enabled
                }
                for system in self.systems
            ]
        }