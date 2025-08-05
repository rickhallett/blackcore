"""Complex scenario demonstrating emergence."""

import asyncio
import os
import random
from typing import List

from src.core import (
    Entity, Identity, Position, Properties, ResourceBundle,
    Resource, ResourceType, ResourceConstraints,
    Event, RelationshipType, ModifierFactory
)
from src.world import World, WorldConfig
from src.economy import MarketSystem
from src.ai import (
    NPCMind, PersonalityTrait, EmotionalState, Goal,
    NPCMindSystem, AnthropicProvider, OpenAIProvider
)
from src.patterns import PatternSystem, PatternTemplate, PatternType


class ScenarioBuilder:
    """Builds complex world scenarios."""
    
    def __init__(self, world: World):
        self.world = world
        self.regions = ["market_square", "harbor", "tavern", "warehouse", "docks"]
        self.merchant_names = [
            "Goldhand McGee", "Silver Sarah", "Copper Carl",
            "Diamond Diana", "Ruby Rogers"
        ]
        self.pirate_names = [
            "Black Jack", "Red Anne", "Blue Bill",
            "Green Gary", "Yellow Yates"
        ]
        self.noble_names = [
            "Lord Sterling", "Lady Gold", "Duke Silver",
            "Duchess Platinum", "Count Copper"
        ]
    
    async def create_merchants(self, count: int = 5) -> List[Entity]:
        """Create merchant NPCs with trading focus."""
        merchants = []
        
        for i in range(count):
            name = self.merchant_names[i % len(self.merchant_names)]
            location = random.choice(self.regions)
            
            merchant = self.world.create_entity(
                name=name,
                entity_type="merchant",
                position=Position(
                    x=random.uniform(-50, 50),
                    y=random.uniform(-50, 50),
                    z=0,
                    region=location
                )
            )
            
            # Add significant resources
            resources = ResourceBundle()
            resources.add_resource(Resource(
                resource_type=ResourceType.GOLD,
                amount=random.uniform(200, 1000),
                constraints=ResourceConstraints(min_value=0, max_value=10000)
            ))
            resources.add_resource(Resource(
                resource_type=ResourceType.FOOD,
                amount=random.uniform(50, 200),
                constraints=ResourceConstraints(
                    min_value=0,
                    max_value=1000,
                    decay_rate=0.1  # Food decays
                )
            ))
            resources.add_resource(Resource(
                resource_type=ResourceType.IRON,
                amount=random.uniform(10, 50)
            ))
            merchant.add_component(resources)
            
            # Trading-focused personality
            mind = NPCMind(
                personality_traits={
                    PersonalityTrait.GREEDY: random.uniform(0.6, 0.9),
                    PersonalityTrait.SOCIAL: random.uniform(0.4, 0.7),
                    PersonalityTrait.CAUTIOUS: random.uniform(0.5, 0.8),
                    PersonalityTrait.OPPORTUNISTIC: random.uniform(0.7, 0.9)
                }
            )
            
            # Trading goals
            mind.add_goal(Goal(
                goal_id=f"profit_{merchant.id}",
                description="Maximize trading profits",
                priority=1.0,
                target_resource=ResourceType.GOLD,
                target_value=2000.0
            ))
            
            mind.add_goal(Goal(
                goal_id=f"monopoly_{merchant.id}",
                description="Control food market",
                priority=0.7,
                target_resource=ResourceType.FOOD,
                target_value=500.0
            ))
            
            merchant.add_component(mind)
            merchants.append(merchant)
        
        return merchants
    
    async def create_pirates(self, count: int = 5) -> List[Entity]:
        """Create pirate NPCs with aggressive behavior."""
        pirates = []
        
        for i in range(count):
            name = self.pirate_names[i % len(self.pirate_names)]
            location = random.choice(["harbor", "docks", "tavern"])
            
            pirate = self.world.create_entity(
                name=name,
                entity_type="pirate",
                position=Position(
                    x=random.uniform(-30, 30),
                    y=random.uniform(-30, 30),
                    z=0,
                    region=location
                )
            )
            
            # Limited but stolen resources
            resources = ResourceBundle()
            resources.add_resource(Resource(
                resource_type=ResourceType.GOLD,
                amount=random.uniform(50, 200)
            ))
            resources.add_resource(Resource(
                resource_type=ResourceType.INFLUENCE,
                amount=random.uniform(10, 50),
                constraints=ResourceConstraints(min_value=0, max_value=100)
            ))
            pirate.add_component(resources)
            
            # Aggressive personality
            mind = NPCMind(
                personality_traits={
                    PersonalityTrait.AGGRESSIVE: random.uniform(0.7, 0.95),
                    PersonalityTrait.GREEDY: random.uniform(0.6, 0.9),
                    PersonalityTrait.LOYAL: random.uniform(0.3, 0.6),
                    PersonalityTrait.OPPORTUNISTIC: random.uniform(0.8, 1.0)
                }
            )
            
            # Pirate goals
            mind.add_goal(Goal(
                goal_id=f"plunder_{pirate.id}",
                description="Acquire wealth through any means",
                priority=1.0,
                target_resource=ResourceType.GOLD,
                target_value=1000.0
            ))
            
            mind.add_goal(Goal(
                goal_id=f"fear_{pirate.id}",
                description="Spread fear and gain influence",
                priority=0.8,
                target_resource=ResourceType.INFLUENCE,
                target_value=80.0
            ))
            
            pirate.add_component(mind)
            pirates.append(pirate)
        
        return pirates
    
    async def create_nobles(self, count: int = 3) -> List[Entity]:
        """Create noble NPCs with political focus."""
        nobles = []
        
        for i in range(count):
            name = self.noble_names[i % len(self.noble_names)]
            
            noble = self.world.create_entity(
                name=name,
                entity_type="noble",
                position=Position(
                    x=0,
                    y=0,
                    z=10,  # Higher position
                    region="market_square"
                )
            )
            
            # Vast resources
            resources = ResourceBundle()
            resources.add_resource(Resource(
                resource_type=ResourceType.GOLD,
                amount=random.uniform(1000, 5000)
            ))
            resources.add_resource(Resource(
                resource_type=ResourceType.INFLUENCE,
                amount=random.uniform(50, 90),
                constraints=ResourceConstraints(
                    min_value=0,
                    max_value=100,
                    regen_rate=0.1  # Influence regenerates
                )
            ))
            resources.add_resource(Resource(
                resource_type=ResourceType.REPUTATION,
                amount=random.uniform(60, 90),
                constraints=ResourceConstraints(min_value=-100, max_value=100)
            ))
            noble.add_component(resources)
            
            # Political personality
            mind = NPCMind(
                personality_traits={
                    PersonalityTrait.CAUTIOUS: random.uniform(0.7, 0.9),
                    PersonalityTrait.SOCIAL: random.uniform(0.6, 0.8),
                    PersonalityTrait.GREEDY: random.uniform(0.4, 0.7),
                    PersonalityTrait.LOYAL: random.uniform(0.5, 0.8)
                }
            )
            
            # Political goals
            mind.add_goal(Goal(
                goal_id=f"power_{noble.id}",
                description="Maintain political power",
                priority=1.0,
                target_resource=ResourceType.INFLUENCE,
                target_value=95.0
            ))
            
            mind.add_goal(Goal(
                goal_id=f"reputation_{noble.id}",
                description="Preserve noble reputation",
                priority=0.9,
                target_resource=ResourceType.REPUTATION,
                target_value=90.0
            ))
            
            noble.add_component(mind)
            nobles.append(noble)
        
        return nobles
    
    async def create_initial_relationships(
        self,
        merchants: List[Entity],
        pirates: List[Entity],
        nobles: List[Entity]
    ) -> None:
        """Create initial relationship network."""
        
        # Merchants know each other (competition)
        for i, merchant1 in enumerate(merchants):
            for merchant2 in merchants[i+1:]:
                self.world.relationships.create_binary_relationship(
                    merchant1.id,
                    merchant2.id,
                    RelationshipType.KNOWS,
                    directed=False
                )
                
                # Some are rivals
                if random.random() < 0.3:
                    edge = self.world.relationships.create_binary_relationship(
                        merchant1.id,
                        merchant2.id,
                        RelationshipType.HOSTILE_TO,
                        directed=False
                    )
                    edge.properties.weight = random.uniform(0.3, 0.7)
        
        # Pirates form crews
        if len(pirates) >= 3:
            # First 3 pirates are a crew
            crew_leader = pirates[0]
            for pirate in pirates[1:3]:
                self.world.relationships.create_binary_relationship(
                    pirate.id,
                    crew_leader.id,
                    RelationshipType.MEMBER_OF,
                    directed=True
                )
                
                self.world.relationships.create_binary_relationship(
                    pirate.id,
                    crew_leader.id,
                    RelationshipType.TRUSTS,
                    directed=True
                )
        
        # Nobles have complex relationships
        for i, noble1 in enumerate(nobles):
            for noble2 in nobles[i+1:]:
                # All nobles know each other
                self.world.relationships.create_binary_relationship(
                    noble1.id,
                    noble2.id,
                    RelationshipType.KNOWS,
                    directed=False
                )
                
                # Some are allied
                if random.random() < 0.4:
                    self.world.relationships.create_binary_relationship(
                        noble1.id,
                        noble2.id,
                        RelationshipType.ALLIED_WITH,
                        directed=False
                    )
        
        # Merchants trade with nobles
        for merchant in merchants[:2]:  # Top merchants
            for noble in nobles:
                if random.random() < 0.6:
                    self.world.relationships.create_binary_relationship(
                        merchant.id,
                        noble.id,
                        RelationshipType.TRADES_WITH,
                        directed=False
                    )
        
        # Pirates are hostile to nobles
        for pirate in pirates:
            for noble in nobles:
                edge = self.world.relationships.create_binary_relationship(
                    pirate.id,
                    noble.id,
                    RelationshipType.HOSTILE_TO,
                    directed=True
                )
                edge.properties.weight = random.uniform(0.6, 0.9)
    
    async def create_market_dynamics(self) -> None:
        """Set up initial market conditions."""
        # Food scarcity drives prices up
        self.world.event_bus.emit(Event(
            event_type="market_event",
            data={
                "type": "shortage",
                "resource": ResourceType.FOOD.value,
                "severity": 0.7
            }
        ))
        
        # Some initial orders
        merchants = self.world.query_entities() \
            .where(lambda e: e.identity and e.identity.entity_type == "merchant") \
            .execute()
        
        for merchant in merchants[:3]:
            # Sell orders for food at high prices
            self.world.event_bus.emit(Event(
                event_type="submit_order",
                entity_id=merchant.id,
                data={
                    "resource_type": ResourceType.FOOD.value,
                    "side": "sell",
                    "order_type": "limit",
                    "quantity": random.uniform(10, 30),
                    "price": random.uniform(3.0, 5.0)
                }
            ))
    
    async def apply_scenario_modifiers(self) -> None:
        """Apply scenario-specific modifiers."""
        # Pirates get combat bonuses at night
        pirates = self.world.query_entities() \
            .where(lambda e: e.identity and e.identity.entity_type == "pirate") \
            .execute()
        
        for pirate in pirates:
            from ..core import ModifierStack
            stack = pirate.get_component(ModifierStack)
            if not stack:
                stack = ModifierStack()
                pirate.add_component(stack)
            
            # Night fighter buff
            night_buff = ModifierFactory.create_buff(
                name="Night Fighter",
                target_id="combat",
                value=2.0,
                duration=None  # Permanent
            )
            stack.add_modifier(night_buff)
        
        # Nobles get influence bonus
        nobles = self.world.query_entities() \
            .where(lambda e: e.identity and e.identity.entity_type == "noble") \
            .execute()
        
        for noble in nobles:
            from ..core import ModifierStack
            stack = noble.get_component(ModifierStack)
            if not stack:
                stack = ModifierStack()
                noble.add_component(stack)
            
            # Noble presence aura
            aura = ModifierFactory.create_aura(
                name="Noble Presence",
                effects=[],  # Would affect nearby entities
                source_entity_id=noble.id
            )
            stack.add_modifier(aura)
    
    def register_custom_patterns(self, pattern_system: PatternSystem) -> None:
        """Register scenario-specific patterns."""
        
        # Merchant War pattern
        pattern_system.detector.register_template(PatternTemplate(
            name="merchant_war",
            pattern_type=PatternType.ECONOMIC,
            description="Competing merchants escalate to economic warfare",
            event_types={"trade_executed", "order_cancelled", "relationship_broken"},
            min_events=8,
            max_time_window=600.0,
            sequence_validator=self._validate_merchant_war
        ))
        
        # Pirate Raid pattern
        pattern_system.detector.register_template(PatternTemplate(
            name="pirate_raid",
            pattern_type=PatternType.NARRATIVE,
            description="Pirates coordinate attack on wealthy target",
            event_types={"entity_interaction", "resource_changed", "relationship_created"},
            min_events=5,
            max_time_window=300.0,
            sequence_validator=self._validate_pirate_raid
        ))
        
        # Noble Intrigue pattern
        pattern_system.detector.register_template(PatternTemplate(
            name="noble_intrigue",
            pattern_type=PatternType.SOCIAL,
            description="Political maneuvering among nobility",
            event_types={"relationship_created", "relationship_broken", "resource_changed"},
            min_events=6,
            max_time_window=900.0,
            event_filter=self._filter_noble_events
        ))
    
    def _validate_merchant_war(self, events: List[Event]) -> bool:
        """Validate merchant war pattern."""
        merchants = set()
        hostile_actions = 0
        
        for event in events:
            if event.entity_id:
                entity = self.world.get_entity(event.entity_id)
                if entity and entity.identity and entity.identity.entity_type == "merchant":
                    merchants.add(event.entity_id)
            
            if event.event_type == "order_cancelled":
                hostile_actions += 1
            elif event.event_type == "relationship_broken":
                if event.data.get("type") == RelationshipType.TRADES_WITH.value:
                    hostile_actions += 2
        
        # Need at least 2 merchants and significant hostile actions
        return len(merchants) >= 2 and hostile_actions >= 3
    
    def _validate_pirate_raid(self, events: List[Event]) -> bool:
        """Validate pirate raid pattern."""
        pirates = set()
        victims = set()
        resource_theft = 0
        
        for event in events:
            if event.entity_id:
                entity = self.world.get_entity(event.entity_id)
                if entity and entity.identity:
                    if entity.identity.entity_type == "pirate":
                        pirates.add(event.entity_id)
                    else:
                        victims.add(event.entity_id)
            
            if event.event_type == "resource_changed":
                amount = event.data.get("amount", 0)
                if amount < 0:  # Loss
                    resource_theft += abs(amount)
        
        # Need multiple pirates and significant theft
        return len(pirates) >= 2 and resource_theft > 50
    
    def _filter_noble_events(self, event: Event) -> bool:
        """Filter for noble-related events."""
        if event.entity_id:
            entity = self.world.get_entity(event.entity_id)
            if entity and entity.identity:
                return entity.identity.entity_type == "noble"
        
        # Check if event involves nobles
        for field in ["target_entity", "other_entity"]:
            if field in event.data:
                entity = self.world.get_entity(event.data[field])
                if entity and entity.identity and entity.identity.entity_type == "noble":
                    return True
        
        return False


async def run_complex_scenario(duration: int = 120) -> None:
    """Run complex emergent scenario."""
    print("🌍 Complex Emergent World Scenario")
    print("=" * 60)
    print()
    print("Creating a world with merchants, pirates, and nobles...")
    print("Watch for emergent patterns like:")
    print("- Economic warfare between merchants")
    print("- Pirate raids on the wealthy")
    print("- Noble political intrigue")
    print("- Market bubbles and crashes")
    print("- Alliance cascades")
    print()
    
    # Create world with enhanced configuration
    config = WorldConfig(
        name="Nassau Complex",
        tick_rate=0.5,  # Faster ticks for more activity
        max_entities=100,
        enable_persistence=False,
        enable_ai=True
    )
    
    world = World(config)
    
    # Add all systems
    world.add_system(MarketSystem())
    
    # LLM provider
    llm_provider = None
    if os.getenv("ANTHROPIC_API_KEY"):
        llm_provider = AnthropicProvider(os.getenv("ANTHROPIC_API_KEY"))
    elif os.getenv("OPENAI_API_KEY"):
        llm_provider = OpenAIProvider(os.getenv("OPENAI_API_KEY"))
    
    world.add_system(NPCMindSystem(
        llm_provider=llm_provider,
        decision_interval=3.0  # More frequent decisions
    ))
    
    pattern_system = PatternSystem()
    world.add_system(pattern_system)
    
    # Initialize
    await world.initialize()
    
    # Build scenario
    builder = ScenarioBuilder(world)
    
    print("Creating NPCs...")
    merchants = await builder.create_merchants(5)
    pirates = await builder.create_pirates(5)
    nobles = await builder.create_nobles(3)
    
    print(f"Created {len(merchants)} merchants, {len(pirates)} pirates, {len(nobles)} nobles")
    
    print("Establishing relationships...")
    await builder.create_initial_relationships(merchants, pirates, nobles)
    
    print("Setting up market dynamics...")
    await builder.create_market_dynamics()
    
    print("Applying scenario modifiers...")
    await builder.apply_scenario_modifiers()
    
    print("Registering custom patterns...")
    builder.register_custom_patterns(pattern_system)
    
    print("\nStarting simulation...")
    print("=" * 60)
    
    # Run simulation
    simulation_task = asyncio.create_task(world.run())
    
    # Monitor
    start_time = asyncio.get_event_loop().time()
    last_pattern_count = 0
    
    while asyncio.get_event_loop().time() - start_time < duration:
        await asyncio.sleep(10)
        
        stats = world.get_stats()
        pattern_stats = pattern_system.detector.get_statistics()
        
        print(f"\n[Tick {stats['tick_count']}]")
        print(f"Entities: {stats['entity_count']} | "
              f"Relationships: {stats['relationship_count']} | "
              f"Events: {stats['event_count']}")
        
        # Pattern detection
        total_patterns = sum(pattern_stats["pattern_counts"].values())
        if total_patterns > last_pattern_count:
            print(f"\n🔮 NEW PATTERNS DETECTED:")
            for pattern_name, count in pattern_stats["pattern_counts"].items():
                if count > 0:
                    print(f"  - {pattern_name.replace('_', ' ').title()}: {count}")
            last_pattern_count = total_patterns
        
        # Sample interesting events
        recent_events = list(world.event_bus.event_store.events.values())[-20:]
        interesting_events = [
            e for e in recent_events
            if e.event_type in ["pirate_raid", "merchant_war", "noble_intrigue", "pattern_detected"]
        ]
        
        if interesting_events:
            print("\n📡 Notable Events:")
            for event in interesting_events[-3:]:
                print(f"  - {event.event_type}: {event.data.get('description', 'No details')}")
        
        # Economic snapshot
        market_system = next(
            (s for s in world.systems if isinstance(s, MarketSystem)),
            None
        )
        if market_system and market_system.matching_engine:
            print("\n📈 Market Activity:")
            for resource_type in [ResourceType.FOOD, ResourceType.GOLD]:
                data = market_system.matching_engine.get_market_data(resource_type)
                if data["volume"] > 0:
                    print(f"  - {resource_type.value}: ${data['last_price']:.2f} "
                          f"(volume: {data['volume']:.0f})")
        
        # Faction power levels
        print("\n⚔️ Faction Power:")
        faction_resources = {"merchant": 0, "pirate": 0, "noble": 0}
        
        for entity in world.entities.values():
            if entity.identity:
                faction = entity.identity.entity_type
                if faction in faction_resources:
                    bundle = entity.get_component(ResourceBundle)
                    if bundle:
                        gold = bundle.get_resource(ResourceType.GOLD)
                        if gold:
                            faction_resources[faction] += gold.amount
        
        for faction, total_gold in faction_resources.items():
            print(f"  - {faction.title()}s: ${total_gold:.0f}")
    
    # Stop simulation
    await world.stop()
    
    print("\n" + "=" * 60)
    print("Simulation complete!")
    
    # Final analysis
    print("\n📊 Final Analysis:")
    
    pattern_stats = pattern_system.detector.get_statistics()
    print(f"\nPatterns Detected: {sum(pattern_stats['pattern_counts'].values())}")
    for pattern_name, count in sorted(
        pattern_stats["pattern_counts"].items(),
        key=lambda x: x[1],
        reverse=True
    ):
        if count > 0:
            print(f"  - {pattern_name.replace('_', ' ').title()}: {count}")
    
    # Relationship analysis
    print(f"\n🔗 Relationship Network:")
    rel_types = {}
    for edge in world.relationships.hyperedges.values():
        rel_type = edge.relationship_type.value
        rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
    
    for rel_type, count in sorted(rel_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {rel_type.replace('_', ' ').title()}: {count}")
    
    # Economic summary
    trades = [
        e for e in world.event_bus.event_store.events.values()
        if e.event_type == "trade_executed"
    ]
    if trades:
        total_volume = sum(t.data.get("quantity", 0) * t.data.get("price", 0) for t in trades)
        print(f"\n💰 Economic Activity:")
        print(f"  - Total trades: {len(trades)}")
        print(f"  - Total volume: ${total_volume:.2f}")


if __name__ == "__main__":
    asyncio.run(run_complex_scenario(duration=120))