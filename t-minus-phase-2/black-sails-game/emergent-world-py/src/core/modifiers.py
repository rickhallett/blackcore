"""Modifier system with stackable effects and DAG dependencies."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

import networkx as nx
from pydantic import BaseModel, Field

from .entity import Component, Entity
from .events import Event, EventBus


class ModifierType(str, Enum):
    """Types of modifiers."""
    ADD = "add"
    MULTIPLY = "multiply"
    OVERRIDE = "override"
    CONDITIONAL = "conditional"
    TEMPORAL = "temporal"
    CUSTOM = "custom"


class ModifierTarget(str, Enum):
    """What the modifier affects."""
    RESOURCE = "resource"
    ATTRIBUTE = "attribute"
    RELATIONSHIP = "relationship"
    COMPONENT = "component"
    CUSTOM = "custom"


@dataclass
class ModifierEffect:
    """Effect of a modifier."""
    target: ModifierTarget
    target_id: str  # Resource type, attribute name, etc.
    operation: ModifierType
    value: Union[float, Callable[[float], float]]
    condition: Optional[Callable[[Entity], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def apply(self, current_value: float, entity: Optional[Entity] = None) -> float:
        """Apply modifier effect to a value."""
        # Check condition
        if self.condition and entity and not self.condition(entity):
            return current_value
        
        # Apply operation
        if self.operation == ModifierType.ADD:
            if callable(self.value):
                return current_value + self.value(current_value)
            return current_value + self.value
        
        elif self.operation == ModifierType.MULTIPLY:
            if callable(self.value):
                return current_value * self.value(current_value)
            return current_value * self.value
        
        elif self.operation == ModifierType.OVERRIDE:
            if callable(self.value):
                return self.value(current_value)
            return self.value
        
        return current_value


class Modifier(BaseModel):
    """Individual modifier with effects and metadata."""
    modifier_id: str
    name: str
    description: str = ""
    effects: List[ModifierEffect] = Field(default_factory=list)
    duration: Optional[float] = None  # None = permanent
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    stacks: int = 1
    max_stacks: int = 1
    unique: bool = False  # Only one instance can exist
    tags: Set[str] = Field(default_factory=set)
    source_entity_id: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_expired(self) -> bool:
        """Check if modifier has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def add_stack(self) -> bool:
        """Add a stack to the modifier."""
        if self.stacks < self.max_stacks:
            self.stacks += 1
            if self.duration and self.expires_at:
                # Refresh duration
                self.expires_at = time.time() + self.duration
            return True
        return False
    
    def remove_stack(self) -> int:
        """Remove a stack from the modifier."""
        if self.stacks > 0:
            self.stacks -= 1
        return self.stacks


class ModifierStack(Component):
    """Component that holds and manages modifiers."""
    modifiers: Dict[str, Modifier] = Field(default_factory=dict)
    dependencies: nx.DiGraph = Field(default_factory=nx.DiGraph)
    event_bus: Optional[EventBus] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def add_modifier(
        self,
        modifier: Modifier,
        depends_on: Optional[List[str]] = None
    ) -> bool:
        """Add modifier to the stack."""
        # Check if unique modifier already exists
        if modifier.unique:
            for existing in self.modifiers.values():
                if existing.name == modifier.name and existing.modifier_id != modifier.modifier_id:
                    return False
        
        # Check if modifier exists and can stack
        if modifier.modifier_id in self.modifiers:
            return self.modifiers[modifier.modifier_id].add_stack()
        
        # Add new modifier
        self.modifiers[modifier.modifier_id] = modifier
        self.dependencies.add_node(modifier.modifier_id)
        
        # Add dependencies
        if depends_on:
            for dep_id in depends_on:
                if dep_id in self.modifiers:
                    self.dependencies.add_edge(dep_id, modifier.modifier_id)
        
        # Set expiration if duration specified
        if modifier.duration:
            modifier.expires_at = time.time() + modifier.duration
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="modifier_added",
                data={
                    "modifier_id": modifier.modifier_id,
                    "name": modifier.name,
                    "stacks": modifier.stacks
                }
            ))
        
        return True
    
    def remove_modifier(self, modifier_id: str) -> bool:
        """Remove modifier from the stack."""
        if modifier_id not in self.modifiers:
            return False
        
        modifier = self.modifiers[modifier_id]
        
        # Check dependencies
        if self.dependencies.out_degree(modifier_id) > 0:
            # Has dependents, just remove a stack
            if modifier.remove_stack() == 0:
                # Remove completely
                self._remove_modifier_complete(modifier_id)
        else:
            # No dependents, remove completely
            self._remove_modifier_complete(modifier_id)
        
        return True
    
    def _remove_modifier_complete(self, modifier_id: str) -> None:
        """Completely remove modifier and update dependencies."""
        del self.modifiers[modifier_id]
        
        # Remove from dependency graph
        # Get dependents before removal
        dependents = list(self.dependencies.successors(modifier_id))
        self.dependencies.remove_node(modifier_id)
        
        # Recursively remove orphaned dependents
        for dependent_id in dependents:
            if self.dependencies.in_degree(dependent_id) == 0:
                self.remove_modifier(dependent_id)
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="modifier_removed",
                data={"modifier_id": modifier_id}
            ))
    
    def get_modifiers_by_tag(self, tag: str) -> List[Modifier]:
        """Get all modifiers with a specific tag."""
        return [
            modifier for modifier in self.modifiers.values()
            if tag in modifier.tags
        ]
    
    def get_modifiers_by_target(
        self,
        target: ModifierTarget,
        target_id: str
    ) -> List[Modifier]:
        """Get all modifiers affecting a specific target."""
        result = []
        for modifier in self.modifiers.values():
            for effect in modifier.effects:
                if effect.target == target and effect.target_id == target_id:
                    result.append(modifier)
                    break
        return result
    
    def calculate_value(
        self,
        base_value: float,
        target: ModifierTarget,
        target_id: str,
        entity: Optional[Entity] = None
    ) -> float:
        """Calculate modified value after applying all relevant modifiers."""
        # Update expired modifiers first
        self.update()
        
        # Get modifiers in dependency order
        modifiers = self.get_modifiers_by_target(target, target_id)
        if not modifiers:
            return base_value
        
        # Sort by dependency order
        modifier_ids = [m.modifier_id for m in modifiers]
        try:
            ordered_ids = list(nx.topological_sort(
                self.dependencies.subgraph(modifier_ids)
            ))
        except nx.NetworkXError:
            # Cycle detected, use original order
            ordered_ids = modifier_ids
        
        # Apply modifiers in order
        current_value = base_value
        overridden = False
        
        # First pass: Apply overrides (highest priority)
        for modifier_id in ordered_ids:
            modifier = self.modifiers.get(modifier_id)
            if not modifier:
                continue
            
            for effect in modifier.effects:
                if (effect.target == target and 
                    effect.target_id == target_id and
                    effect.operation == ModifierType.OVERRIDE):
                    for _ in range(modifier.stacks):
                        current_value = effect.apply(current_value, entity)
                    overridden = True
                    break
            
            if overridden:
                break
        
        if not overridden:
            # Second pass: Apply additions
            for modifier_id in ordered_ids:
                modifier = self.modifiers.get(modifier_id)
                if not modifier:
                    continue
                
                for effect in modifier.effects:
                    if (effect.target == target and 
                        effect.target_id == target_id and
                        effect.operation == ModifierType.ADD):
                        for _ in range(modifier.stacks):
                            current_value = effect.apply(current_value, entity)
            
            # Third pass: Apply multiplications
            for modifier_id in ordered_ids:
                modifier = self.modifiers.get(modifier_id)
                if not modifier:
                    continue
                
                for effect in modifier.effects:
                    if (effect.target == target and 
                        effect.target_id == target_id and
                        effect.operation == ModifierType.MULTIPLY):
                        for _ in range(modifier.stacks):
                            current_value = effect.apply(current_value, entity)
        
        return current_value
    
    def update(self) -> List[str]:
        """Update modifiers, removing expired ones."""
        expired = []
        current_time = time.time()
        
        for modifier_id, modifier in list(self.modifiers.items()):
            if modifier.is_expired():
                expired.append(modifier_id)
        
        # Remove expired modifiers
        for modifier_id in expired:
            self.remove_modifier(modifier_id)
        
        return expired
    
    def get_active_effects(self) -> List[Dict[str, Any]]:
        """Get summary of all active effects."""
        self.update()
        
        effects = []
        for modifier in self.modifiers.values():
            for effect in modifier.effects:
                effects.append({
                    "modifier": modifier.name,
                    "target": effect.target.value,
                    "target_id": effect.target_id,
                    "operation": effect.operation.value,
                    "stacks": modifier.stacks,
                    "expires_in": (
                        modifier.expires_at - time.time()
                        if modifier.expires_at else None
                    )
                })
        
        return effects


# Common modifier factories
class ModifierFactory:
    """Factory for creating common modifiers."""
    
    @staticmethod
    def create_buff(
        name: str,
        target_id: str,
        value: float,
        duration: float = 60.0,
        modifier_type: ModifierType = ModifierType.ADD
    ) -> Modifier:
        """Create a simple buff modifier."""
        return Modifier(
            modifier_id=f"buff_{name}_{time.time()}",
            name=name,
            effects=[
                ModifierEffect(
                    target=ModifierTarget.ATTRIBUTE,
                    target_id=target_id,
                    operation=modifier_type,
                    value=value
                )
            ],
            duration=duration,
            tags={"buff"}
        )
    
    @staticmethod
    def create_debuff(
        name: str,
        target_id: str,
        value: float,
        duration: float = 30.0
    ) -> Modifier:
        """Create a simple debuff modifier."""
        return Modifier(
            modifier_id=f"debuff_{name}_{time.time()}",
            name=name,
            effects=[
                ModifierEffect(
                    target=ModifierTarget.ATTRIBUTE,
                    target_id=target_id,
                    operation=ModifierType.ADD,
                    value=-abs(value)
                )
            ],
            duration=duration,
            tags={"debuff"}
        )
    
    @staticmethod
    def create_aura(
        name: str,
        effects: List[ModifierEffect],
        source_entity_id: str
    ) -> Modifier:
        """Create an aura modifier."""
        return Modifier(
            modifier_id=f"aura_{name}_{source_entity_id}",
            name=name,
            effects=effects,
            source_entity_id=source_entity_id,
            unique=True,
            tags={"aura"}
        )
    
    @staticmethod
    def create_conditional(
        name: str,
        target_id: str,
        value: float,
        condition: Callable[[Entity], bool]
    ) -> Modifier:
        """Create a conditional modifier."""
        return Modifier(
            modifier_id=f"conditional_{name}_{time.time()}",
            name=name,
            effects=[
                ModifierEffect(
                    target=ModifierTarget.ATTRIBUTE,
                    target_id=target_id,
                    operation=ModifierType.ADD,
                    value=value,
                    condition=condition
                )
            ],
            tags={"conditional"}
        )