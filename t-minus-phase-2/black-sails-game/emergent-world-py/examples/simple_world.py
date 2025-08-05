"""Simple example demonstrating the emergent world."""

import asyncio
import os
from typing import Optional

from src.core import (
    Entity, Identity, Position, Properties, ResourceBundle,
    Resource, ResourceType, ResourceConstraints,
    Event, RelationshipType
)
from src.world import World, WorldConfig
from src.economy import MarketSystem
from src.ai import (
    NPCMind, PersonalityTrait, Goal, NPCMindSystem,
    AnthropicProvider, OpenAIProvider
)


async def create_merchant(world: World, name: str, location: str) -> Entity:
    """Create a merchant NPC."""
    entity = world.create_entity(
        name=name,
        entity_type="merchant",
        position=Position(x=0, y=0, z=0, region=location)
    )
    
    # Add resources
    resources = ResourceBundle()
    resources.add_resource(Resource(
        resource_type=ResourceType.GOLD,
        amount=100.0,
        constraints=ResourceConstraints(min_value=0, max_value=10000)
    ))
    resources.add_resource(Resource(
        resource_type=ResourceType.FOOD,
        amount=50.0,
        constraints=ResourceConstraints(min_value=0, max_value=500)
    ))
    entity.add_component(resources)
    
    # Add AI mind
    mind = NPCMind(
        personality_traits={
            PersonalityTrait.GREEDY: 0.8,
            PersonalityTrait.SOCIAL: 0.6,
            PersonalityTrait.CAUTIOUS: 0.4
        }
    )
    
    # Add trading goal
    mind.add_goal(Goal(
        goal_id=f"trade_profit_{entity.id}",
        description="Make profitable trades",
        priority=1.0,
        target_resource=ResourceType.GOLD,
        target_value=500.0
    ))
    
    entity.add_component(mind)
    
    return entity


async def create_adventurer(world: World, name: str, location: str) -> Entity:
    """Create an adventurer NPC."""
    entity = world.create_entity(
        name=name,
        entity_type="adventurer",
        position=Position(x=10, y=0, z=0, region=location)
    )
    
    # Add resources
    resources = ResourceBundle()
    resources.add_resource(Resource(
        resource_type=ResourceType.GOLD,
        amount=50.0
    ))
    resources.add_resource(Resource(
        resource_type=ResourceType.FOOD,
        amount=20.0
    ))
    entity.add_component(resources)
    
    # Add AI mind
    mind = NPCMind(
        personality_traits={
            PersonalityTrait.CURIOUS: 0.9,
            PersonalityTrait.AGGRESSIVE: 0.5,
            PersonalityTrait.SOCIAL: 0.7
        }
    )
    
    # Add exploration goal
    mind.add_goal(Goal(
        goal_id=f"explore_{entity.id}",
        description="Explore new locations",
        priority=0.8
    ))
    
    entity.add_component(mind)
    
    return entity


async def create_relationships(world: World, entities: list[Entity]) -> None:
    """Create initial relationships between entities."""
    if len(entities) >= 2:
        # Merchant and first adventurer know each other
        world.relationships.create_binary_relationship(
            entities[0].id,  # Merchant
            entities[1].id,  # Adventurer
            RelationshipType.KNOWS,
            properties=None,
            directed=False
        )
        
        # They also trade
        world.relationships.create_binary_relationship(
            entities[0].id,
            entities[1].id,
            RelationshipType.TRADES_WITH,
            directed=False
        )


async def simulate_trading(world: World) -> None:
    """Simulate some trading activity."""
    # Find merchant
    merchants = world.query_entities() \
        .with_tag("merchant") \
        .execute()
    
    if merchants:
        merchant = merchants[0]
        
        # Submit a sell order for food
        world.event_bus.emit(Event(
            event_type="submit_order",
            entity_id=merchant.id,
            data={
                "resource_type": ResourceType.FOOD.value,
                "side": "sell",
                "order_type": "limit",
                "quantity": 10.0,
                "price": 2.0  # 2 gold per food
            }
        ))
        
    # Find adventurer
    adventurers = world.query_entities() \
        .where(lambda e: e.identity and e.identity.entity_type == "adventurer") \
        .execute()
    
    if adventurers:
        adventurer = adventurers[0]
        
        # Submit a buy order for food
        world.event_bus.emit(Event(
            event_type="submit_order",
            entity_id=adventurer.id,
            data={
                "resource_type": ResourceType.FOOD.value,
                "side": "buy",
                "order_type": "limit",
                "quantity": 5.0,
                "price": 2.5  # Willing to pay 2.5 gold per food
            }
        ))


async def run_simulation(duration: int = 60) -> None:
    """Run the simulation for specified duration."""
    # Create world
    config = WorldConfig(
        name="Simple Emergent World",
        tick_rate=1.0,  # 1 second per tick
        enable_persistence=False,  # No external dependencies for demo
        enable_ai=True
    )
    
    world = World(config)
    
    # Add market system
    world.add_system(MarketSystem())
    
    # Setup LLM provider if available
    llm_provider: Optional[LLMProvider] = None
    
    if os.getenv("ANTHROPIC_API_KEY"):
        llm_provider = AnthropicProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-3-haiku-20240307"
        )
    elif os.getenv("OPENAI_API_KEY"):
        llm_provider = OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini"
        )
    
    # Add NPC mind system
    world.add_system(NPCMindSystem(
        llm_provider=llm_provider,
        decision_interval=5.0  # Decisions every 5 seconds
    ))
    
    # Initialize world
    await world.initialize()
    
    # Create entities
    print("Creating world entities...")
    
    merchant = await create_merchant(world, "Greedy McGoldface", "market_square")
    adventurer1 = await create_adventurer(world, "Curious George", "market_square")
    adventurer2 = await create_adventurer(world, "Bold Explorer", "tavern")
    
    entities = [merchant, adventurer1, adventurer2]
    
    # Create relationships
    await create_relationships(world, entities)
    
    # Simulate some initial trading
    await simulate_trading(world)
    
    print(f"\nStarting simulation for {duration} seconds...")
    print("=" * 60)
    
    # Run simulation
    simulation_task = asyncio.create_task(world.run())
    
    # Monitor for duration
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < duration:
        await asyncio.sleep(5)
        
        # Print stats
        stats = world.get_stats()
        print(f"\nTick {stats['tick_count']}:")
        print(f"  Entities: {stats['entity_count']}")
        print(f"  Relationships: {stats['relationship_count']}")
        print(f"  Events: {stats['event_count']}")
        
        # Check market data
        market_system = next(
            (s for s in world.systems if isinstance(s, MarketSystem)),
            None
        )
        if market_system and market_system.matching_engine:
            for resource_type in [ResourceType.FOOD, ResourceType.GOLD]:
                market_data = market_system.matching_engine.get_market_data(resource_type)
                if market_data["last_price"]:
                    print(f"  {resource_type.value} market: "
                          f"${market_data['last_price']:.2f} "
                          f"(vol: {market_data['volume']:.0f})")
        
        # Sample entity states
        for entity in entities[:2]:
            if entity.identity:
                print(f"\n  {entity.identity.name}:")
                
                # Resources
                bundle = entity.get_component(ResourceBundle)
                if bundle:
                    summary = bundle.get_summary()
                    print(f"    Resources: {summary}")
                
                # Mind state
                mind = entity.get_component(NPCMind)
                if mind:
                    print(f"    Emotion: {mind.emotional_state.value}")
                    print(f"    Memories: {len(mind.memories)}")
                    
                    # Current goal
                    active_goals = [g for g in mind.goals if not g.completed]
                    if active_goals:
                        print(f"    Goal: {active_goals[0].description}")
    
    # Stop simulation
    await world.stop()
    
    print("\n" + "=" * 60)
    print("Simulation complete!")
    
    # Final summary
    print("\nFinal World State:")
    final_stats = world.get_stats()
    for key, value in final_stats.items():
        if key != "systems":
            print(f"  {key}: {value}")
    
    # Check relationships
    print("\nRelationship Network:")
    for entity in entities:
        if entity.identity:
            relationships = world.relationships.get_relationships(entity.id)
            if relationships:
                print(f"  {entity.identity.name}:")
                for rel in relationships:
                    other_ids = [eid for eid in rel.entities if eid != entity.id]
                    for other_id in other_ids:
                        other = world.get_entity(other_id)
                        if other and other.identity:
                            print(f"    - {rel.relationship_type.value} -> {other.identity.name}")


if __name__ == "__main__":
    # Run the simulation
    asyncio.run(run_simulation(duration=30))  # 30 second demo