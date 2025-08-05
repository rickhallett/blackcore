"""Resource system with constraints and bundling."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, validator

from .entity import Component
from .events import Event, EventBus


class ResourceType(str, Enum):
    """Common resource types."""
    # Physical
    GOLD = "gold"
    FOOD = "food"
    WATER = "water"
    WOOD = "wood"
    STONE = "stone"
    IRON = "iron"
    
    # Abstract
    INFLUENCE = "influence"
    REPUTATION = "reputation"
    KNOWLEDGE = "knowledge"
    MANA = "mana"
    ENERGY = "energy"
    
    # Social
    LOYALTY = "loyalty"
    FEAR = "fear"
    RESPECT = "respect"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class ResourceConstraints:
    """Constraints for resource values."""
    min_value: float = 0.0
    max_value: float = float('inf')
    can_be_negative: bool = False
    decay_rate: float = 0.0  # Per second
    regen_rate: float = 0.0  # Per second
    transferable: bool = True
    divisible: bool = True
    
    def clamp(self, value: float) -> float:
        """Clamp value to constraints."""
        if not self.can_be_negative and value < 0:
            value = 0
        return max(self.min_value, min(value, self.max_value))
    
    def apply_time_effects(self, value: float, delta_time: float) -> float:
        """Apply decay/regen over time."""
        if self.decay_rate > 0:
            value -= self.decay_rate * delta_time
        if self.regen_rate > 0:
            value += self.regen_rate * delta_time
        return self.clamp(value)


class Resource(BaseModel):
    """Individual resource with amount and constraints."""
    resource_type: ResourceType
    amount: float = 0.0
    constraints: ResourceConstraints = Field(default_factory=ResourceConstraints)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add(self, amount: float) -> float:
        """Add to resource amount."""
        old_amount = self.amount
        self.amount = self.constraints.clamp(self.amount + amount)
        return self.amount - old_amount
    
    def subtract(self, amount: float) -> float:
        """Subtract from resource amount."""
        old_amount = self.amount
        self.amount = self.constraints.clamp(self.amount - amount)
        return old_amount - self.amount
    
    def set(self, amount: float) -> None:
        """Set resource amount."""
        self.amount = self.constraints.clamp(amount)
    
    def can_afford(self, amount: float) -> bool:
        """Check if can afford amount."""
        return self.amount >= amount or self.constraints.can_be_negative
    
    def transfer_to(self, other: Resource, amount: float) -> float:
        """Transfer amount to another resource."""
        if not self.constraints.transferable:
            return 0.0
        
        if not self.constraints.divisible:
            amount = math.floor(amount)
        
        actual = min(amount, self.amount)
        if self.constraints.can_be_negative:
            actual = amount
        
        self.subtract(actual)
        other.add(actual)
        return actual
    
    def update(self, delta_time: float) -> None:
        """Update resource with time effects."""
        self.amount = self.constraints.apply_time_effects(self.amount, delta_time)


class ResourceBundle(Component):
    """Component holding multiple resources."""
    resources: Dict[str, Resource] = Field(default_factory=dict)
    
    def get_resource(self, resource_type: ResourceType) -> Optional[Resource]:
        """Get resource by type."""
        return self.resources.get(resource_type.value)
    
    def add_resource(self, resource: Resource) -> None:
        """Add or update resource."""
        self.resources[resource.resource_type.value] = resource
    
    def remove_resource(self, resource_type: ResourceType) -> Optional[Resource]:
        """Remove and return resource."""
        return self.resources.pop(resource_type.value, None)
    
    def has_resource(self, resource_type: ResourceType, amount: float = 0) -> bool:
        """Check if has resource (optionally with minimum amount)."""
        resource = self.get_resource(resource_type)
        return resource is not None and resource.amount >= amount
    
    def can_afford(self, costs: Dict[ResourceType, float]) -> bool:
        """Check if can afford multiple resource costs."""
        for resource_type, amount in costs.items():
            resource = self.get_resource(resource_type)
            if not resource or not resource.can_afford(amount):
                return False
        return True
    
    def pay(self, costs: Dict[ResourceType, float]) -> bool:
        """Pay multiple resource costs."""
        if not self.can_afford(costs):
            return False
        
        for resource_type, amount in costs.items():
            resource = self.get_resource(resource_type)
            if resource:
                resource.subtract(amount)
        
        return True
    
    def receive(self, rewards: Dict[ResourceType, float]) -> None:
        """Receive multiple resources."""
        for resource_type, amount in rewards.items():
            resource = self.get_resource(resource_type)
            if resource:
                resource.add(amount)
            else:
                # Create new resource if doesn't exist
                new_resource = Resource(
                    resource_type=resource_type,
                    amount=amount
                )
                self.add_resource(new_resource)
    
    def transfer_to(
        self,
        other: ResourceBundle,
        transfers: Dict[ResourceType, float]
    ) -> Dict[ResourceType, float]:
        """Transfer multiple resources to another bundle."""
        actual_transfers = {}
        
        for resource_type, amount in transfers.items():
            source = self.get_resource(resource_type)
            if not source:
                continue
            
            target = other.get_resource(resource_type)
            if not target:
                target = Resource(resource_type=resource_type)
                other.add_resource(target)
            
            actual = source.transfer_to(target, amount)
            if actual > 0:
                actual_transfers[resource_type] = actual
        
        return actual_transfers
    
    def update(self, delta_time: float) -> None:
        """Update all resources with time effects."""
        for resource in self.resources.values():
            resource.update(delta_time)
    
    def get_summary(self) -> Dict[str, float]:
        """Get summary of all resource amounts."""
        return {
            resource_type: resource.amount
            for resource_type, resource in self.resources.items()
        }


class ResourceExchange:
    """System for resource exchange and conversion."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.exchange_rates: Dict[Tuple[str, str], float] = {}
        self.event_bus = event_bus
        
        # Common exchange rates
        self._setup_default_rates()
    
    def _setup_default_rates(self) -> None:
        """Setup default exchange rates."""
        # Gold as base currency
        self.set_exchange_rate(ResourceType.GOLD, ResourceType.FOOD, 10.0)  # 1 gold = 10 food
        self.set_exchange_rate(ResourceType.GOLD, ResourceType.WOOD, 5.0)   # 1 gold = 5 wood
        self.set_exchange_rate(ResourceType.GOLD, ResourceType.STONE, 3.0)  # 1 gold = 3 stone
        self.set_exchange_rate(ResourceType.GOLD, ResourceType.IRON, 0.5)   # 1 gold = 0.5 iron
        
        # Social resources
        self.set_exchange_rate(ResourceType.INFLUENCE, ResourceType.GOLD, 100.0)
        self.set_exchange_rate(ResourceType.REPUTATION, ResourceType.INFLUENCE, 10.0)
    
    def set_exchange_rate(
        self,
        from_type: ResourceType,
        to_type: ResourceType,
        rate: float
    ) -> None:
        """Set exchange rate between resources."""
        key = (from_type.value, to_type.value)
        self.exchange_rates[key] = rate
        
        # Set inverse rate
        if rate > 0:
            inverse_key = (to_type.value, from_type.value)
            self.exchange_rates[inverse_key] = 1.0 / rate
    
    def get_exchange_rate(
        self,
        from_type: ResourceType,
        to_type: ResourceType
    ) -> Optional[float]:
        """Get exchange rate between resources."""
        if from_type == to_type:
            return 1.0
        
        key = (from_type.value, to_type.value)
        return self.exchange_rates.get(key)
    
    def exchange(
        self,
        bundle: ResourceBundle,
        from_type: ResourceType,
        to_type: ResourceType,
        amount: float
    ) -> Optional[float]:
        """Exchange resources in a bundle."""
        rate = self.get_exchange_rate(from_type, to_type)
        if rate is None:
            return None
        
        from_resource = bundle.get_resource(from_type)
        if not from_resource or not from_resource.can_afford(amount):
            return None
        
        to_amount = amount * rate
        
        # Perform exchange
        from_resource.subtract(amount)
        bundle.receive({to_type: to_amount})
        
        if self.event_bus:
            self.event_bus.emit(Event(
                event_type="resource_exchanged",
                data={
                    "from_type": from_type.value,
                    "to_type": to_type.value,
                    "from_amount": amount,
                    "to_amount": to_amount,
                    "rate": rate
                }
            ))
        
        return to_amount
    
    def find_exchange_path(
        self,
        from_type: ResourceType,
        to_type: ResourceType
    ) -> Optional[List[ResourceType]]:
        """Find exchange path between resources using BFS."""
        if from_type == to_type:
            return [from_type]
        
        # Build adjacency list
        graph: Dict[str, Set[str]] = {}
        for (from_res, to_res), rate in self.exchange_rates.items():
            if from_res not in graph:
                graph[from_res] = set()
            graph[from_res].add(to_res)
        
        # BFS
        queue = [(from_type.value, [from_type])]
        visited = {from_type.value}
        
        while queue:
            current, path = queue.pop(0)
            
            if current == to_type.value:
                return path
            
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    try:
                        resource_type = ResourceType(neighbor)
                        queue.append((neighbor, path + [resource_type]))
                    except ValueError:
                        continue
        
        return None
    
    def multi_exchange(
        self,
        bundle: ResourceBundle,
        from_type: ResourceType,
        to_type: ResourceType,
        amount: float
    ) -> Optional[float]:
        """Exchange through multiple steps if needed."""
        path = self.find_exchange_path(from_type, to_type)
        if not path:
            return None
        
        current_amount = amount
        current_type = from_type
        
        for i in range(1, len(path)):
            next_type = path[i]
            rate = self.get_exchange_rate(current_type, next_type)
            if rate is None:
                return None
            
            current_amount = current_amount * rate
            current_type = next_type
        
        # Check if can afford
        from_resource = bundle.get_resource(from_type)
        if not from_resource or not from_resource.can_afford(amount):
            return None
        
        # Perform exchange
        from_resource.subtract(amount)
        bundle.receive({to_type: current_amount})
        
        return current_amount