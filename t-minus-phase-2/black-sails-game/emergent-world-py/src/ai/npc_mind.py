"""LLM-powered NPC decision making and behavior."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ..core.entity import Component, Entity, Identity
from ..core.events import Event, EventBus, EventHandler
from ..core.relationships import RelationshipType
from ..core.resources import ResourceType
from ..world.engine import World, WorldSystem, SystemPriority

logger = structlog.get_logger()


class PersonalityTrait(str, Enum):
    """NPC personality traits."""
    AGGRESSIVE = "aggressive"
    PEACEFUL = "peaceful"
    GREEDY = "greedy"
    GENEROUS = "generous"
    SOCIAL = "social"
    RECLUSIVE = "reclusive"
    CURIOUS = "curious"
    CAUTIOUS = "cautious"
    LOYAL = "loyal"
    OPPORTUNISTIC = "opportunistic"


class EmotionalState(str, Enum):
    """NPC emotional states."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    ANXIOUS = "anxious"


class Goal(BaseModel):
    """NPC goal or objective."""
    goal_id: str
    description: str
    priority: float = 1.0
    target_entity_id: Optional[str] = None
    target_resource: Optional[ResourceType] = None
    target_value: Optional[float] = None
    progress: float = 0.0
    created_at: float = Field(default_factory=time.time)
    deadline: Optional[float] = None
    completed: bool = False
    
    def is_expired(self) -> bool:
        """Check if goal has expired."""
        if self.deadline is None:
            return False
        return time.time() > self.deadline


class Memory(BaseModel):
    """NPC memory of an event or interaction."""
    memory_id: str
    event_type: str
    description: str
    entities_involved: List[str] = Field(default_factory=list)
    emotional_impact: Dict[str, float] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    importance: float = 1.0
    decay_rate: float = 0.01  # Per day
    
    def get_current_importance(self) -> float:
        """Get importance with decay applied."""
        days_passed = (time.time() - self.timestamp) / 86400
        return self.importance * (1.0 - self.decay_rate * days_passed)


class NPCMind(Component):
    """NPC mind component with personality and decision making."""
    personality_traits: Dict[PersonalityTrait, float] = Field(default_factory=dict)
    emotional_state: EmotionalState = EmotionalState.NEUTRAL
    emotional_values: Dict[EmotionalState, float] = Field(default_factory=dict)
    goals: List[Goal] = Field(default_factory=list)
    memories: List[Memory] = Field(default_factory=list)
    max_memories: int = 100
    decision_threshold: float = 0.7
    last_decision_time: float = Field(default_factory=time.time)
    decision_cooldown: float = 5.0  # Seconds
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_memory(self, memory: Memory) -> None:
        """Add memory, removing oldest if at capacity."""
        self.memories.append(memory)
        
        # Sort by importance and recency
        self.memories.sort(
            key=lambda m: m.get_current_importance(),
            reverse=True
        )
        
        # Keep only most important memories
        if len(self.memories) > self.max_memories:
            self.memories = self.memories[:self.max_memories]
    
    def add_goal(self, goal: Goal) -> None:
        """Add goal to NPC's objectives."""
        self.goals.append(goal)
        self.goals.sort(key=lambda g: g.priority, reverse=True)
    
    def update_emotional_state(self) -> None:
        """Update primary emotional state based on values."""
        if not self.emotional_values:
            self.emotional_state = EmotionalState.NEUTRAL
            return
        
        # Find dominant emotion
        max_emotion = max(
            self.emotional_values.items(),
            key=lambda x: x[1]
        )
        
        if max_emotion[1] > 0.3:  # Threshold for emotion change
            self.emotional_state = max_emotion[0]
        else:
            self.emotional_state = EmotionalState.NEUTRAL
    
    def get_personality_summary(self) -> str:
        """Get text summary of personality."""
        traits = []
        for trait, value in sorted(
            self.personality_traits.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]:  # Top 3 traits
            if value > 0.5:
                traits.append(trait.value)
        
        return ", ".join(traits) if traits else "balanced"
    
    def get_relevant_memories(
        self,
        entity_ids: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Get memories relevant to context."""
        relevant = []
        
        for memory in self.memories:
            if entity_ids and not any(
                eid in memory.entities_involved for eid in entity_ids
            ):
                continue
            
            if event_types and memory.event_type not in event_types:
                continue
            
            if memory.get_current_importance() > 0.1:
                relevant.append(memory)
        
        return relevant[:limit]
    
    def can_make_decision(self) -> bool:
        """Check if NPC can make a new decision."""
        return time.time() - self.last_decision_time > self.decision_cooldown


@dataclass
class DecisionContext:
    """Context for NPC decision making."""
    entity: Entity
    world_state: Dict[str, Any]
    nearby_entities: List[Tuple[str, float]]  # (entity_id, distance)
    available_actions: List[str]
    recent_events: List[Event]
    relationships: Dict[str, Any]
    resources: Dict[str, float]
    current_location: Optional[str] = None


class NPCDecision(BaseModel):
    """Decision made by NPC."""
    action: str
    target_entity_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0


class LLMProvider:
    """Base class for LLM providers."""
    
    async def decide(
        self,
        context: DecisionContext,
        mind: NPCMind
    ) -> NPCDecision:
        """Make decision based on context."""
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def decide(
        self,
        context: DecisionContext,
        mind: NPCMind
    ) -> NPCDecision:
        """Make decision using Claude."""
        # Build prompt
        prompt = self._build_prompt(context, mind)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.7,
                system="You are an NPC in an emergent world simulation. Make decisions based on your personality, goals, and current context. Respond only with valid JSON.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            content = response.content[0].text
            decision_data = json.loads(content)
            
            return NPCDecision(**decision_data)
            
        except Exception as e:
            logger.error("llm_decision_error", error=str(e))
            # Fallback to simple decision
            return self._fallback_decision(context, mind)
    
    def _build_prompt(self, context: DecisionContext, mind: NPCMind) -> str:
        """Build decision prompt."""
        # Get entity identity
        identity = context.entity.identity
        name = identity.name if identity else "Unknown"
        
        # Format nearby entities
        nearby = []
        for entity_id, distance in context.nearby_entities[:5]:
            nearby.append(f"- Entity {entity_id[:8]} at distance {distance:.1f}")
        
        # Format goals
        active_goals = [g for g in mind.goals if not g.completed][:3]
        goals_text = "\n".join([
            f"- {g.description} (priority: {g.priority:.1f})"
            for g in active_goals
        ])
        
        # Format memories
        recent_memories = mind.get_relevant_memories(limit=5)
        memories_text = "\n".join([
            f"- {m.description} ({m.get_current_importance():.1f} importance)"
            for m in recent_memories
        ])
        
        return f"""
You are {name}, an NPC with these traits: {mind.get_personality_summary()}
Current emotional state: {mind.emotional_state.value}

Current context:
- Location: {context.current_location or "Unknown"}
- Resources: {json.dumps(context.resources)}
- Nearby entities:
{chr(10).join(nearby)}

Your goals:
{goals_text}

Recent memories:
{memories_text}

Available actions: {', '.join(context.available_actions)}

Based on your personality, emotional state, goals, and memories, what action do you take?

Respond with JSON in this format:
{{
    "action": "action_name",
    "target_entity_id": "entity_id or null",
    "parameters": {{}},
    "reasoning": "Brief explanation of your decision",
    "confidence": 0.0-1.0
}}
"""
    
    def _fallback_decision(
        self,
        context: DecisionContext,
        mind: NPCMind
    ) -> NPCDecision:
        """Simple fallback decision."""
        # Default to exploring if curious
        if PersonalityTrait.CURIOUS in mind.personality_traits:
            return NPCDecision(
                action="explore",
                reasoning="Curiosity drives exploration",
                confidence=0.5
            )
        
        # Trade if greedy and has resources
        if PersonalityTrait.GREEDY in mind.personality_traits and context.resources:
            return NPCDecision(
                action="trade",
                reasoning="Seeking profit opportunities",
                confidence=0.6
            )
        
        # Default to waiting
        return NPCDecision(
            action="wait",
            reasoning="No clear action available",
            confidence=0.3
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def decide(
        self,
        context: DecisionContext,
        mind: NPCMind
    ) -> NPCDecision:
        """Make decision using GPT."""
        # Similar implementation to Anthropic
        # Build prompt
        prompt = self._build_prompt(context, mind)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an NPC in an emergent world simulation. Make decisions based on your personality, goals, and current context. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            decision_data = json.loads(content)
            
            return NPCDecision(**decision_data)
            
        except Exception as e:
            logger.error("llm_decision_error", error=str(e))
            return self._fallback_decision(context, mind)
    
    def _build_prompt(self, context: DecisionContext, mind: NPCMind) -> str:
        """Build decision prompt (same as Anthropic)."""
        # Reuse the same prompt building logic
        provider = AnthropicProvider("dummy")
        return provider._build_prompt(context, mind)
    
    def _fallback_decision(
        self,
        context: DecisionContext,
        mind: NPCMind
    ) -> NPCDecision:
        """Simple fallback decision (same as Anthropic)."""
        provider = AnthropicProvider("dummy")
        return provider._fallback_decision(context, mind)


class NPCMindSystem(WorldSystem):
    """System for NPC AI and decision making."""
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        decision_interval: float = 10.0
    ):
        super().__init__("NPCMindSystem", SystemPriority.LOW)
        self.llm_provider = llm_provider
        self.decision_interval = decision_interval
        self.last_decision_time: Dict[str, float] = {}
        self._decision_queue: asyncio.Queue[str] = asyncio.Queue()
        self._decision_tasks: List[asyncio.Task] = []
    
    async def initialize(self, world: World) -> None:
        """Initialize NPC mind system."""
        self.world = world
        
        # Start decision workers
        for i in range(3):  # 3 concurrent decision makers
            task = asyncio.create_task(self._decision_worker())
            self._decision_tasks.append(task)
        
        # Register event handlers
        world.event_bus.register_handler(NPCEventHandler(self))
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update NPC minds."""
        current_time = time.time()
        
        # Find NPCs that need decisions
        npcs = world.query_entities().with_component(NPCMind).execute()
        
        for entity in npcs:
            mind = entity.get_component(NPCMind)
            if not mind or not mind.can_make_decision():
                continue
            
            # Check decision interval
            last_time = self.last_decision_time.get(entity.id, 0)
            if current_time - last_time < self.decision_interval:
                continue
            
            # Queue for decision
            await self._decision_queue.put(entity.id)
            self.last_decision_time[entity.id] = current_time
    
    async def _decision_worker(self) -> None:
        """Worker for processing NPC decisions."""
        while True:
            try:
                entity_id = await self._decision_queue.get()
                await self._make_decision(entity_id)
            except Exception as e:
                logger.error("decision_worker_error", error=str(e))
    
    async def _make_decision(self, entity_id: str) -> None:
        """Make decision for NPC."""
        entity = self.world.get_entity(entity_id)
        if not entity:
            return
        
        mind = entity.get_component(NPCMind)
        if not mind:
            return
        
        # Build context
        context = await self._build_context(entity)
        
        # Use LLM if available
        if self.llm_provider and mind.decision_threshold < 0.8:
            try:
                decision = await self.llm_provider.decide(context, mind)
            except Exception as e:
                logger.error("llm_decision_failed", error=str(e))
                decision = self._make_simple_decision(context, mind)
        else:
            decision = self._make_simple_decision(context, mind)
        
        # Execute decision
        await self._execute_decision(entity, decision)
        
        # Update last decision time
        mind.last_decision_time = time.time()
    
    async def _build_context(self, entity: Entity) -> DecisionContext:
        """Build decision context for NPC."""
        # Get spatial system
        spatial_system = None
        for system in self.world.systems:
            if system.name == "SpatialSystem":
                spatial_system = system
                break
        
        # Get nearby entities
        nearby = []
        if spatial_system and entity.position:
            nearby = spatial_system.get_nearby_entities(entity.id, radius=20.0)
        
        # Get relationships
        relationships = {}
        for edge in self.world.relationships.get_relationships(entity.id):
            for other_id in edge.entities:
                if other_id != entity.id:
                    relationships[other_id] = {
                        "type": edge.relationship_type.value,
                        "strength": edge.properties.weight
                    }
        
        # Get resources
        resources = {}
        bundle = entity.get_component(ResourceBundle)
        if bundle:
            resources = bundle.get_summary()
        
        # Get recent events
        recent_events = self.world.event_bus.query_events(
            entity_id=entity.id,
            since=time.time() - 300  # Last 5 minutes
        )
        
        return DecisionContext(
            entity=entity,
            world_state={
                "time": time.time(),
                "tick": self.world.tick_count
            },
            nearby_entities=nearby,
            available_actions=self._get_available_actions(entity),
            recent_events=recent_events,
            relationships=relationships,
            resources=resources,
            current_location=entity.position.region if entity.position else None
        )
    
    def _get_available_actions(self, entity: Entity) -> List[str]:
        """Get available actions for entity."""
        actions = ["wait", "explore", "interact"]
        
        # Add resource actions if has resources
        if entity.get_component(ResourceBundle):
            actions.extend(["trade", "gather", "consume"])
        
        # Add social actions if near others
        actions.extend(["greet", "befriend", "avoid"])
        
        return actions
    
    def _make_simple_decision(
        self,
        context: DecisionContext,
        mind: NPCMind
    ) -> NPCDecision:
        """Make simple rule-based decision."""
        # Check goals
        for goal in mind.goals:
            if goal.completed or goal.is_expired():
                continue
            
            # Resource gathering goal
            if goal.target_resource:
                return NPCDecision(
                    action="gather",
                    parameters={"resource": goal.target_resource.value},
                    reasoning=f"Working towards goal: {goal.description}",
                    confidence=0.7
                )
            
            # Social goal
            if goal.target_entity_id and goal.target_entity_id in [
                e[0] for e in context.nearby_entities
            ]:
                return NPCDecision(
                    action="interact",
                    target_entity_id=goal.target_entity_id,
                    reasoning=f"Pursuing social goal: {goal.description}",
                    confidence=0.8
                )
        
        # Emotional responses
        if mind.emotional_state == EmotionalState.ANGRY:
            # Find someone to be angry at
            if context.nearby_entities:
                return NPCDecision(
                    action="confront",
                    target_entity_id=context.nearby_entities[0][0],
                    reasoning="Expressing anger",
                    confidence=0.6
                )
        
        elif mind.emotional_state == EmotionalState.FEARFUL:
            # Avoid others
            return NPCDecision(
                action="flee",
                reasoning="Avoiding perceived threats",
                confidence=0.7
            )
        
        # Personality-based decisions
        if PersonalityTrait.SOCIAL in mind.personality_traits and context.nearby_entities:
            return NPCDecision(
                action="greet",
                target_entity_id=context.nearby_entities[0][0],
                reasoning="Social personality seeks interaction",
                confidence=0.6
            )
        
        # Default exploration
        return NPCDecision(
            action="explore",
            reasoning="No specific goals, exploring world",
            confidence=0.4
        )
    
    async def _execute_decision(self, entity: Entity, decision: NPCDecision) -> None:
        """Execute NPC decision."""
        # Emit decision event
        self.world.event_bus.emit(Event(
            event_type="npc_decision",
            entity_id=entity.id,
            data={
                "action": decision.action,
                "target": decision.target_entity_id,
                "parameters": decision.parameters,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence
            }
        ))
        
        # Log decision
        logger.info(
            "npc_decision_made",
            entity_id=entity.id,
            entity_name=entity.identity.name if entity.identity else "Unknown",
            action=decision.action,
            confidence=decision.confidence
        )
    
    async def shutdown(self) -> None:
        """Shutdown decision workers."""
        for task in self._decision_tasks:
            task.cancel()
        
        await asyncio.gather(*self._decision_tasks, return_exceptions=True)


class NPCEventHandler(EventHandler):
    """Handles events that affect NPC minds."""
    
    def __init__(self, mind_system: NPCMindSystem):
        super().__init__()
        self.mind_system = mind_system
        self.event_types = {
            "entity_interaction",
            "resource_changed",
            "relationship_created",
            "trade_completed"
        }
    
    async def handle(self, event: Event) -> Any:
        """Update NPC memories and emotions based on events."""
        if not event.entity_id:
            return
        
        entity = self.mind_system.world.get_entity(event.entity_id)
        if not entity:
            return
        
        mind = entity.get_component(NPCMind)
        if not mind:
            return
        
        # Create memory of event
        memory = Memory(
            memory_id=f"mem_{event.event_id[:8]}",
            event_type=event.event_type,
            description=self._describe_event(event),
            entities_involved=self._extract_entities(event),
            importance=self._calculate_importance(event, mind)
        )
        
        # Update emotional impact
        emotional_impact = self._calculate_emotional_impact(event, mind)
        memory.emotional_impact = emotional_impact
        
        # Apply emotional changes
        for emotion, impact in emotional_impact.items():
            current = mind.emotional_values.get(emotion, 0.0)
            mind.emotional_values[emotion] = max(0, min(1, current + impact))
        
        # Update emotional state
        mind.update_emotional_state()
        
        # Add memory
        mind.add_memory(memory)
    
    def _describe_event(self, event: Event) -> str:
        """Generate description of event."""
        descriptions = {
            "entity_interaction": f"Interacted with {event.data.get('other_entity', 'someone')}",
            "resource_changed": f"Resource {event.data.get('resource_type', 'unknown')} changed by {event.data.get('amount', 0)}",
            "relationship_created": f"Formed {event.data.get('type', 'unknown')} relationship",
            "trade_completed": f"Traded {event.data.get('given', 'something')} for {event.data.get('received', 'something')}"
        }
        
        return descriptions.get(event.event_type, f"Experienced {event.event_type}")
    
    def _extract_entities(self, event: Event) -> List[str]:
        """Extract entity IDs from event."""
        entities = []
        
        if event.entity_id:
            entities.append(event.entity_id)
        
        # Check common data fields
        for field in ["other_entity", "target_entity", "buyer_entity_id", "seller_entity_id"]:
            if field in event.data and event.data[field]:
                entities.append(event.data[field])
        
        return list(set(entities))
    
    def _calculate_importance(self, event: Event, mind: NPCMind) -> float:
        """Calculate importance of event to NPC."""
        base_importance = 0.5
        
        # Adjust based on event type
        importance_modifiers = {
            "entity_interaction": 0.3,
            "resource_changed": 0.2,
            "relationship_created": 0.6,
            "trade_completed": 0.4,
            "entity_attacked": 0.9,
            "goal_completed": 0.8
        }
        
        base_importance += importance_modifiers.get(event.event_type, 0.0)
        
        # Adjust based on personality
        if PersonalityTrait.SOCIAL in mind.personality_traits:
            if "interaction" in event.event_type or "relationship" in event.event_type:
                base_importance += 0.2
        
        if PersonalityTrait.GREEDY in mind.personality_traits:
            if "resource" in event.event_type or "trade" in event.event_type:
                base_importance += 0.2
        
        return min(1.0, base_importance)
    
    def _calculate_emotional_impact(
        self,
        event: Event,
        mind: NPCMind
    ) -> Dict[EmotionalState, float]:
        """Calculate emotional impact of event."""
        impact = {}
        
        if event.event_type == "entity_interaction":
            # Social interactions generally positive
            impact[EmotionalState.HAPPY] = 0.1
            if PersonalityTrait.SOCIAL in mind.personality_traits:
                impact[EmotionalState.HAPPY] += 0.1
            elif PersonalityTrait.RECLUSIVE in mind.personality_traits:
                impact[EmotionalState.ANXIOUS] = 0.2
        
        elif event.event_type == "resource_changed":
            amount = event.data.get("amount", 0)
            if amount > 0:
                impact[EmotionalState.HAPPY] = 0.15
                if PersonalityTrait.GREEDY in mind.personality_traits:
                    impact[EmotionalState.EXCITED] = 0.2
            else:
                impact[EmotionalState.SAD] = 0.1
                impact[EmotionalState.ANXIOUS] = 0.05
        
        elif event.event_type == "relationship_created":
            rel_type = event.data.get("type", "")
            if rel_type in ["friend", "ally"]:
                impact[EmotionalState.HAPPY] = 0.3
            elif rel_type in ["enemy", "rival"]:
                impact[EmotionalState.ANGRY] = 0.2
                impact[EmotionalState.ANXIOUS] = 0.1
        
        return impact