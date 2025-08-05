"""Pattern detection system for emergent narratives and behaviors."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import networkx as nx
from pydantic import BaseModel, Field
import structlog

from ..core.events import Event, EventHandler
from ..core.entity import Entity
from ..core.relationships import RelationshipType
from ..world.engine import World, WorldSystem, SystemPriority

logger = structlog.get_logger()


class PatternType(str, Enum):
    """Types of patterns to detect."""
    NARRATIVE = "narrative"          # Story-like sequences
    BEHAVIORAL = "behavioral"        # Repeated behaviors
    SOCIAL = "social"               # Social dynamics
    ECONOMIC = "economic"           # Market patterns
    EMERGENT = "emergent"           # Unexpected phenomena
    CYCLICAL = "cyclical"           # Repeating cycles
    CASCADE = "cascade"             # Chain reactions


class PatternMatch(BaseModel):
    """A detected pattern instance."""
    pattern_id: str
    pattern_type: PatternType
    confidence: float = 0.0
    events: List[Event] = Field(default_factory=list)
    entities: Set[str] = Field(default_factory=set)
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    
    @property
    def duration(self) -> float:
        """Get pattern duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def add_event(self, event: Event) -> None:
        """Add event to pattern."""
        self.events.append(event)
        if event.entity_id:
            self.entities.add(event.entity_id)


@dataclass
class PatternTemplate:
    """Template for detecting patterns."""
    name: str
    pattern_type: PatternType
    description: str
    
    # Detection criteria
    event_types: Set[str] = field(default_factory=set)
    min_events: int = 2
    max_time_window: float = 300.0  # 5 minutes
    
    # Conditions
    event_filter: Optional[Callable[[Event], bool]] = None
    sequence_validator: Optional[Callable[[List[Event]], bool]] = None
    confidence_calculator: Optional[Callable[[List[Event]], float]] = None
    
    # Actions
    on_detected: Optional[Callable[[PatternMatch], None]] = None
    
    def matches_event(self, event: Event) -> bool:
        """Check if event could be part of this pattern."""
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.event_filter and not self.event_filter(event):
            return False
        
        return True
    
    def validate_sequence(self, events: List[Event]) -> bool:
        """Validate if events form valid pattern."""
        if len(events) < self.min_events:
            return False
        
        # Check time window
        if events:
            time_span = events[-1].timestamp - events[0].timestamp
            if time_span > self.max_time_window:
                return False
        
        # Custom validation
        if self.sequence_validator:
            return self.sequence_validator(events)
        
        return True
    
    def calculate_confidence(self, events: List[Event]) -> float:
        """Calculate pattern confidence."""
        if self.confidence_calculator:
            return self.confidence_calculator(events)
        
        # Default: confidence based on event count
        base_confidence = min(1.0, len(events) / (self.min_events * 2))
        
        # Adjust for time clustering
        if len(events) >= 2:
            time_gaps = []
            for i in range(1, len(events)):
                time_gaps.append(events[i].timestamp - events[i-1].timestamp)
            
            avg_gap = np.mean(time_gaps)
            consistency_bonus = 0.2 * (1.0 - np.std(time_gaps) / (avg_gap + 1))
            base_confidence += consistency_bonus
        
        return min(1.0, base_confidence)


class PatternDetector:
    """Detects patterns in event streams."""
    
    def __init__(self):
        self.templates: Dict[str, PatternTemplate] = {}
        self.active_patterns: List[PatternMatch] = []
        self.completed_patterns: List[PatternMatch] = []
        self.event_buffer: List[Event] = []
        self.buffer_size = 1000
        
        # Pattern statistics
        self.pattern_counts: Dict[str, int] = defaultdict(int)
        
        # Register default patterns
        self._register_default_patterns()
    
    def _register_default_patterns(self) -> None:
        """Register built-in pattern templates."""
        
        # Alliance Cascade
        self.register_template(PatternTemplate(
            name="alliance_cascade",
            pattern_type=PatternType.CASCADE,
            description="Chain reaction of alliance formations",
            event_types={"relationship_created"},
            min_events=3,
            max_time_window=600.0,
            event_filter=lambda e: e.data.get("type") == RelationshipType.ALLIED_WITH.value,
            confidence_calculator=self._cascade_confidence
        ))
        
        # Market Bubble
        self.register_template(PatternTemplate(
            name="market_bubble",
            pattern_type=PatternType.ECONOMIC,
            description="Rapid price increases followed by crash",
            event_types={"trade_executed"},
            min_events=10,
            max_time_window=300.0,
            sequence_validator=self._validate_bubble,
            confidence_calculator=self._bubble_confidence
        ))
        
        # Social Conflict Escalation
        self.register_template(PatternTemplate(
            name="conflict_escalation",
            pattern_type=PatternType.SOCIAL,
            description="Escalating conflict between entities",
            event_types={"entity_interaction", "relationship_created", "relationship_broken"},
            min_events=4,
            max_time_window=600.0,
            sequence_validator=self._validate_conflict,
            confidence_calculator=self._conflict_confidence
        ))
        
        # Resource Hoarding
        self.register_template(PatternTemplate(
            name="resource_hoarding",
            pattern_type=PatternType.BEHAVIORAL,
            description="Entity accumulating resources rapidly",
            event_types={"resource_changed", "trade_completed"},
            min_events=5,
            max_time_window=300.0,
            event_filter=lambda e: e.data.get("amount", 0) > 0,
            sequence_validator=self._validate_hoarding
        ))
        
        # Trust Network Formation
        self.register_template(PatternTemplate(
            name="trust_network",
            pattern_type=PatternType.EMERGENT,
            description="Organic formation of trust networks",
            event_types={"relationship_created"},
            min_events=6,
            max_time_window=900.0,
            event_filter=lambda e: e.data.get("type") in [
                RelationshipType.TRUSTS.value,
                RelationshipType.KNOWS.value
            ],
            sequence_validator=self._validate_trust_network
        ))
        
        # Betrayal Arc
        self.register_template(PatternTemplate(
            name="betrayal_arc",
            pattern_type=PatternType.NARRATIVE,
            description="Trust followed by betrayal",
            event_types={"relationship_created", "relationship_broken", "entity_interaction"},
            min_events=3,
            max_time_window=1800.0,
            sequence_validator=self._validate_betrayal
        ))
    
    def register_template(self, template: PatternTemplate) -> None:
        """Register a pattern template."""
        self.templates[template.name] = template
        logger.info("pattern_template_registered", name=template.name)
    
    def process_event(self, event: Event) -> List[PatternMatch]:
        """Process new event and detect patterns."""
        # Add to buffer
        self.event_buffer.append(event)
        if len(self.event_buffer) > self.buffer_size:
            self.event_buffer.pop(0)
        
        detected = []
        
        # Check each template
        for template in self.templates.values():
            if not template.matches_event(event):
                continue
            
            # Try to extend existing patterns
            extended = False
            for pattern in self.active_patterns:
                if pattern.pattern_type == template.pattern_type:
                    # Try adding event to pattern
                    test_events = pattern.events + [event]
                    if template.validate_sequence(test_events):
                        pattern.add_event(event)
                        pattern.confidence = template.calculate_confidence(pattern.events)
                        extended = True
            
            # Try to start new pattern
            if not extended:
                matches = self._find_pattern_matches(template, event)
                for match in matches:
                    self.active_patterns.append(match)
                    detected.append(match)
                    self.pattern_counts[template.name] += 1
                    
                    # Trigger callback
                    if template.on_detected:
                        template.on_detected(match)
        
        # Clean up old patterns
        self._cleanup_patterns()
        
        return detected
    
    def _find_pattern_matches(
        self,
        template: PatternTemplate,
        trigger_event: Event
    ) -> List[PatternMatch]:
        """Find pattern matches in event buffer."""
        matches = []
        
        # Get relevant events from buffer
        relevant_events = [
            e for e in self.event_buffer
            if template.matches_event(e) and 
            e.timestamp >= trigger_event.timestamp - template.max_time_window
        ]
        
        # Try different combinations
        if len(relevant_events) >= template.min_events:
            # For now, just use the most recent sequence
            sequence = relevant_events[-template.min_events:]
            
            if template.validate_sequence(sequence):
                match = PatternMatch(
                    pattern_id=f"{template.name}_{time.time()}",
                    pattern_type=template.pattern_type,
                    events=sequence,
                    confidence=template.calculate_confidence(sequence),
                    description=template.description
                )
                
                # Extract entities
                for event in sequence:
                    if event.entity_id:
                        match.entities.add(event.entity_id)
                
                matches.append(match)
        
        return matches
    
    def _cleanup_patterns(self) -> None:
        """Move old patterns to completed list."""
        current_time = time.time()
        
        for pattern in self.active_patterns[:]:
            # Check if pattern is too old
            if pattern.events:
                last_event_time = pattern.events[-1].timestamp
                template = self.templates.get(pattern.pattern_id.split('_')[0])
                
                if template and current_time - last_event_time > template.max_time_window:
                    pattern.end_time = last_event_time
                    self.completed_patterns.append(pattern)
                    self.active_patterns.remove(pattern)
    
    # Pattern-specific validators and calculators
    
    def _cascade_confidence(self, events: List[Event]) -> float:
        """Calculate confidence for cascade patterns."""
        if len(events) < 3:
            return 0.3
        
        # Check for increasing rate
        time_gaps = []
        for i in range(1, len(events)):
            time_gaps.append(events[i].timestamp - events[i-1].timestamp)
        
        # Cascades should accelerate
        if len(time_gaps) >= 2:
            acceleration = time_gaps[-1] < time_gaps[0]
            if acceleration:
                return min(1.0, 0.5 + len(events) * 0.1)
        
        return 0.4
    
    def _validate_bubble(self, events: List[Event]) -> bool:
        """Validate market bubble pattern."""
        if len(events) < 5:
            return False
        
        # Extract prices
        prices = []
        for event in events:
            if "price" in event.data:
                prices.append(event.data["price"])
        
        if len(prices) < 5:
            return False
        
        # Check for rapid increase
        price_changes = np.diff(prices)
        positive_changes = sum(1 for c in price_changes if c > 0)
        
        return positive_changes >= len(price_changes) * 0.7
    
    def _bubble_confidence(self, events: List[Event]) -> float:
        """Calculate bubble confidence."""
        prices = [e.data.get("price", 0) for e in events if "price" in e.data]
        
        if len(prices) < 5:
            return 0.2
        
        # Calculate price momentum
        returns = np.diff(np.log(prices))
        momentum = np.mean(returns)
        
        # Higher momentum = higher confidence
        return min(1.0, 0.3 + abs(momentum) * 10)
    
    def _validate_conflict(self, events: List[Event]) -> bool:
        """Validate conflict escalation."""
        # Look for negative interactions
        negative_count = 0
        entities = set()
        
        for event in events:
            if event.entity_id:
                entities.add(event.entity_id)
            
            # Check for negative events
            if event.event_type == "relationship_broken":
                negative_count += 2
            elif event.event_type == "entity_interaction":
                if event.data.get("type") in ["confront", "attack", "threaten"]:
                    negative_count += 1
        
        # Need at least 2 entities and mostly negative
        return len(entities) >= 2 and negative_count >= len(events) * 0.5
    
    def _conflict_confidence(self, events: List[Event]) -> float:
        """Calculate conflict confidence."""
        # More events = higher confidence
        base = min(1.0, len(events) / 10)
        
        # Check for reciprocal actions
        entities = defaultdict(int)
        for event in events:
            if event.entity_id:
                entities[event.entity_id] += 1
        
        # Both sides active = higher confidence
        if len(entities) >= 2:
            participation = min(entities.values()) / max(entities.values())
            return base * (0.5 + participation * 0.5)
        
        return base * 0.5
    
    def _validate_hoarding(self, events: List[Event]) -> bool:
        """Validate resource hoarding."""
        # All events should be for same entity
        entities = set(e.entity_id for e in events if e.entity_id)
        if len(entities) != 1:
            return False
        
        # Check for accumulation
        total_gained = 0
        for event in events:
            if event.event_type == "resource_changed":
                total_gained += event.data.get("amount", 0)
            elif event.event_type == "trade_completed":
                # Assume positive if they're hoarding
                total_gained += abs(event.data.get("quantity", 0))
        
        return total_gained > 0
    
    def _validate_trust_network(self, events: List[Event]) -> bool:
        """Validate trust network formation."""
        # Build network graph
        G = nx.Graph()
        
        for event in events:
            if event.event_type == "relationship_created":
                entities = event.data.get("entities", [])
                if len(entities) >= 2:
                    G.add_edge(entities[0], entities[1])
        
        # Check for connected component
        if G.number_of_nodes() < 3:
            return False
        
        # Trust networks should be somewhat connected
        components = list(nx.connected_components(G))
        largest_component = max(components, key=len)
        
        return len(largest_component) >= G.number_of_nodes() * 0.6
    
    def _validate_betrayal(self, events: List[Event]) -> bool:
        """Validate betrayal narrative."""
        # Need trust establishment followed by breaking
        trust_established = False
        trust_broken = False
        entities = set()
        
        for event in events:
            if event.entity_id:
                entities.add(event.entity_id)
            
            if event.event_type == "relationship_created":
                if event.data.get("type") in [
                    RelationshipType.TRUSTS.value,
                    RelationshipType.ALLIED_WITH.value
                ]:
                    trust_established = True
            
            elif event.event_type == "relationship_broken" and trust_established:
                trust_broken = True
        
        return trust_established and trust_broken and len(entities) >= 2
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pattern detection statistics."""
        return {
            "templates_registered": len(self.templates),
            "active_patterns": len(self.active_patterns),
            "completed_patterns": len(self.completed_patterns),
            "pattern_counts": dict(self.pattern_counts),
            "buffer_size": len(self.event_buffer),
            "most_common_pattern": max(
                self.pattern_counts.items(),
                key=lambda x: x[1],
                default=("none", 0)
            )[0] if self.pattern_counts else None
        }


class PatternSystem(WorldSystem):
    """System for pattern detection in world events."""
    
    def __init__(self):
        super().__init__("PatternSystem", SystemPriority.LOW)
        self.detector = PatternDetector()
        self.narrative_generator = NarrativeGenerator()
    
    async def initialize(self, world: World) -> None:
        """Initialize pattern system."""
        self.world = world
        
        # Register event handler
        world.event_bus.register_handler(PatternEventHandler(self))
        
        # Register world-specific patterns
        self._register_world_patterns()
    
    def _register_world_patterns(self) -> None:
        """Register patterns specific to this world."""
        # Power Vacuum
        self.detector.register_template(PatternTemplate(
            name="power_vacuum",
            pattern_type=PatternType.EMERGENT,
            description="Leadership void creates instability",
            event_types={"entity_removed", "relationship_broken"},
            min_events=3,
            max_time_window=600.0,
            sequence_validator=self._validate_power_vacuum
        ))
        
        # Economic Monopoly
        self.detector.register_template(PatternTemplate(
            name="monopoly_formation",
            pattern_type=PatternType.ECONOMIC,
            description="Single entity dominates market",
            event_types={"trade_executed", "order_filled"},
            min_events=10,
            max_time_window=900.0,
            sequence_validator=self._validate_monopoly
        ))
    
    def _validate_power_vacuum(self, events: List[Event]) -> bool:
        """Validate power vacuum pattern."""
        # Look for removal of high-influence entity
        removed_entities = set()
        broken_relationships = 0
        
        for event in events:
            if event.event_type == "entity_removed":
                removed_entities.add(event.entity_id)
            elif event.event_type == "relationship_broken":
                broken_relationships += 1
        
        # Power vacuum needs significant disruption
        return len(removed_entities) >= 1 and broken_relationships >= 2
    
    def _validate_monopoly(self, events: List[Event]) -> bool:
        """Validate monopoly formation."""
        # Count trades by entity
        trade_counts = defaultdict(int)
        
        for event in events:
            if event.event_type == "trade_executed":
                buyer = event.data.get("buyer_entity_id")
                seller = event.data.get("seller_entity_id")
                
                if buyer:
                    trade_counts[buyer] += 1
                if seller:
                    trade_counts[seller] += 1
        
        if not trade_counts:
            return False
        
        # Check for dominance
        total_trades = sum(trade_counts.values())
        max_trades = max(trade_counts.values())
        
        # One entity has >60% of trades
        return max_trades / total_trades > 0.6
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update pattern detection."""
        # Get recent patterns
        active = self.detector.active_patterns
        
        if active:
            logger.info(
                "active_patterns",
                count=len(active),
                types=[p.pattern_type.value for p in active]
            )
            
            # Generate narratives for significant patterns
            for pattern in active:
                if pattern.confidence > 0.7:
                    narrative = self.narrative_generator.generate(pattern, world)
                    if narrative:
                        logger.info(
                            "narrative_generated",
                            pattern=pattern.pattern_id,
                            narrative=narrative
                        )


class PatternEventHandler(EventHandler):
    """Handles events for pattern detection."""
    
    def __init__(self, pattern_system: PatternSystem):
        super().__init__()
        self.pattern_system = pattern_system
        self.event_types = set()  # Accept all events
        self.priority = 100  # High priority to see events early
    
    async def handle(self, event: Event) -> Any:
        """Process event for patterns."""
        detected = self.pattern_system.detector.process_event(event)
        
        if detected:
            for pattern in detected:
                logger.info(
                    "pattern_detected",
                    pattern_type=pattern.pattern_type.value,
                    pattern_id=pattern.pattern_id,
                    confidence=pattern.confidence,
                    entities=list(pattern.entities)
                )
                
                # Emit pattern detection event
                self.pattern_system.world.event_bus.emit(Event(
                    event_type="pattern_detected",
                    data={
                        "pattern_id": pattern.pattern_id,
                        "pattern_type": pattern.pattern_type.value,
                        "confidence": pattern.confidence,
                        "description": pattern.description
                    }
                ))


class NarrativeGenerator:
    """Generates narrative descriptions from patterns."""
    
    def __init__(self):
        self.templates = {
            PatternType.CASCADE: [
                "A chain reaction of {event_type} spreads through the world",
                "Like dominoes falling, {event_type} cascades across {entity_count} entities"
            ],
            PatternType.SOCIAL: [
                "Tensions rise as {entities} engage in {event_type}",
                "Social dynamics shift as relationships form and break"
            ],
            PatternType.ECONOMIC: [
                "Market forces reshape the economy through {event_count} trades",
                "Economic patterns emerge in the marketplace"
            ],
            PatternType.NARRATIVE: [
                "A story unfolds: {description}",
                "Drama emerges as {entities} play out their roles"
            ]
        }
    
    def generate(self, pattern: PatternMatch, world: World) -> str:
        """Generate narrative from pattern."""
        # Get entity names
        entity_names = []
        for entity_id in list(pattern.entities)[:3]:  # First 3
            entity = world.get_entity(entity_id)
            if entity and entity.identity:
                entity_names.append(entity.identity.name)
        
        # Build context
        context = {
            "event_type": pattern.events[0].event_type if pattern.events else "events",
            "event_count": len(pattern.events),
            "entity_count": len(pattern.entities),
            "entities": " and ".join(entity_names) if entity_names else "various entities",
            "description": pattern.description
        }
        
        # Select template
        templates = self.templates.get(pattern.pattern_type, ["A pattern emerges"])
        template = templates[len(pattern.events) % len(templates)]
        
        # Generate narrative
        try:
            return template.format(**context)
        except KeyError:
            return pattern.description