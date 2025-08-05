"""Entity-Component System with versioning and dynamic properties."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TypeVar

import msgpack
from pydantic import BaseModel, Field

from .events import Event, EventBus


T = TypeVar("T")


class Component(BaseModel):
    """Base component with automatic serialization."""
    
    class Config:
        arbitrary_types_allowed = True
        
    @property
    def component_type(self) -> str:
        return self.__class__.__name__
    
    def pack(self) -> bytes:
        """Serialize to msgpack bytes."""
        return msgpack.packb(self.model_dump())
    
    @classmethod
    def unpack(cls: type[T], data: bytes) -> T:
        """Deserialize from msgpack bytes."""
        return cls(**msgpack.unpackb(data))


class Position(Component):
    """Spatial position component."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    region: Optional[str] = None


class Properties(Component):
    """Dynamic property bag for emergent attributes."""
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def __getattr__(self, name: str) -> Any:
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"Property '{name}' not found")
    
    def __setattr__(self, name: str, value: Any) -> None:
        if name == "data":
            super().__setattr__(name, value)
        else:
            self.data[name] = value


class Identity(Component):
    """Core identity information."""
    name: str
    entity_type: str
    tags: Set[str] = Field(default_factory=set)
    created_at: float = Field(default_factory=time.time)


@dataclass
class EntityVersion:
    """Immutable snapshot of entity state."""
    entity_id: str
    version: int
    timestamp: float
    components: Dict[str, bytes]  # Serialized components
    metadata: Dict[str, Any]


class Entity:
    """Core entity with component management and versioning."""
    
    def __init__(
        self,
        entity_id: Optional[str] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.id = entity_id or str(uuid.uuid4())
        self.components: Dict[str, Component] = {}
        self.version = 0
        self.created_at = time.time()
        self.modified_at = self.created_at
        self.event_bus = event_bus
        self._version_history: List[EntityVersion] = []
        self._component_indices: Dict[str, Set[str]] = {}  # For fast queries
        
    def add_component(self, component: Component) -> Entity:
        """Add or update a component."""
        old_component = self.components.get(component.component_type)
        self.components[component.component_type] = component
        
        # Update indices
        self._update_indices(component)
        
        # Create version snapshot
        self._create_version()
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="component_added",
                entity_id=self.id,
                data={
                    "component_type": component.component_type,
                    "old_value": old_component.model_dump() if old_component else None,
                    "new_value": component.model_dump()
                }
            ))
        
        return self
    
    def get_component(self, component_type: type[T]) -> Optional[T]:
        """Get component by type."""
        return self.components.get(component_type.__name__)
    
    def has_component(self, component_type: type[Component]) -> bool:
        """Check if entity has component."""
        return component_type.__name__ in self.components
    
    def remove_component(self, component_type: type[Component]) -> Entity:
        """Remove component from entity."""
        component_name = component_type.__name__
        if component_name in self.components:
            old_component = self.components.pop(component_name)
            self._create_version()
            
            if self.event_bus:
                self.event_bus.emit(Event(
                    event_type="component_removed",
                    entity_id=self.id,
                    data={
                        "component_type": component_name,
                        "old_value": old_component.model_dump()
                    }
                ))
        
        return self
    
    def _create_version(self) -> None:
        """Create immutable version snapshot."""
        self.version += 1
        self.modified_at = time.time()
        
        # Serialize all components
        serialized = {
            name: component.pack()
            for name, component in self.components.items()
        }
        
        version = EntityVersion(
            entity_id=self.id,
            version=self.version,
            timestamp=self.modified_at,
            components=serialized,
            metadata={
                "indices": dict(self._component_indices)
            }
        )
        
        self._version_history.append(version)
        
        # Keep only last N versions to prevent memory bloat
        if len(self._version_history) > 100:
            self._version_history = self._version_history[-100:]
    
    def _update_indices(self, component: Component) -> None:
        """Update component indices for fast queries."""
        # Index by component type
        comp_type = component.component_type
        if comp_type not in self._component_indices:
            self._component_indices[comp_type] = set()
        self._component_indices[comp_type].add(self.id)
        
        # Index by tags if Identity component
        if isinstance(component, Identity):
            for tag in component.tags:
                index_key = f"tag:{tag}"
                if index_key not in self._component_indices:
                    self._component_indices[index_key] = set()
                self._component_indices[index_key].add(self.id)
    
    def get_version(self, version_number: int) -> Optional[EntityVersion]:
        """Get specific version of entity."""
        for version in self._version_history:
            if version.version == version_number:
                return version
        return None
    
    def rollback_to_version(self, version_number: int) -> bool:
        """Rollback entity to specific version."""
        version = self.get_version(version_number)
        if not version:
            return False
        
        # Clear current components
        self.components.clear()
        
        # Restore components from version
        for comp_name, comp_data in version.components.items():
            # Need component registry to deserialize properly
            # For now, we'll skip deserialization
            pass
        
        self._create_version()
        
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="entity_rollback",
                entity_id=self.id,
                data={
                    "from_version": self.version - 1,
                    "to_version": version_number
                }
            ))
        
        return True
    
    @property
    def properties(self) -> Optional[Properties]:
        """Quick access to properties component."""
        return self.get_component(Properties)
    
    @property
    def position(self) -> Optional[Position]:
        """Quick access to position component."""
        return self.get_component(Position)
    
    @property
    def identity(self) -> Optional[Identity]:
        """Quick access to identity component."""
        return self.get_component(Identity)
    
    def __repr__(self) -> str:
        identity = self.identity
        if identity:
            return f"Entity({self.id[:8]}, {identity.name}, v{self.version})"
        return f"Entity({self.id[:8]}, v{self.version})"


class EntityQuery:
    """Fluent query builder for entities."""
    
    def __init__(self, entities: Dict[str, Entity]):
        self.entities = entities
        self.filters: List[callable] = []
    
    def with_component(self, component_type: type[Component]) -> EntityQuery:
        """Filter entities with specific component."""
        self.filters.append(
            lambda e: e.has_component(component_type)
        )
        return self
    
    def with_tag(self, tag: str) -> EntityQuery:
        """Filter entities with specific tag."""
        def has_tag(entity: Entity) -> bool:
            identity = entity.identity
            return identity is not None and tag in identity.tags
        
        self.filters.append(has_tag)
        return self
    
    def in_region(self, region: str) -> EntityQuery:
        """Filter entities in specific region."""
        def in_region_filter(entity: Entity) -> bool:
            pos = entity.position
            return pos is not None and pos.region == region
        
        self.filters.append(in_region_filter)
        return self
    
    def where(self, predicate: callable) -> EntityQuery:
        """Add custom filter predicate."""
        self.filters.append(predicate)
        return self
    
    def execute(self) -> List[Entity]:
        """Execute query and return matching entities."""
        results = []
        for entity in self.entities.values():
            if all(f(entity) for f in self.filters):
                results.append(entity)
        return results