# Emergent World Engine (Python)

A sophisticated simulation engine designed with minimal primitives to enable maximum emergent behavior. Built with Python for rapid iteration and seamless LLM integration.

## Core Philosophy

"Simple rules, complex outcomes" - The engine provides just five core primitives:

1. **Entity** - Things that exist (with dynamic component properties)
2. **Relationship** - Hypergraph connections between entities
3. **Resource** - Quantifiable values with constraints
4. **Event** - Immutable record of what happened
5. **Modifier** - Temporary or permanent effects

From these primitives emerge complex behaviors: economies, social dynamics, narratives, and unpredictable phenomena.

## Features

### 🧠 LLM-Powered NPCs
- Integrated with OpenAI and Anthropic APIs
- Personality-driven decision making
- Emotional states and memory systems
- Goal-oriented behavior with dynamic priorities

### 📊 Market Microstructure
- Order book implementation with price-time priority
- Market, limit, and stop orders
- Real-time trade matching engine
- Price discovery through supply and demand

### 🕸️ Hypergraph Relationships
- Multi-entity connections (not just binary)
- Directed and ordered relationships
- Neo4j persistence for complex queries
- Network analysis and pathfinding

### ⚡ Event Sourcing
- Complete audit trail of all actions
- Causal chain tracking
- Pattern detection opportunities
- Time-travel debugging

### 🔧 Component System
- Dynamic property bags for emergent attributes
- Type-safe components with Pydantic
- Versioning and rollback support
- Hot-swappable behaviors

## Installation

```bash
# Clone the repository
git clone <your-repo>
cd emergent-world-py

# Install with pip (Python 3.11+ required)
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from src.core import Entity, Position, ResourceBundle
from src.world import World, WorldConfig
from src.ai import NPCMind, PersonalityTrait

async def main():
    # Create world
    world = World(WorldConfig(name="My World"))
    await world.initialize()
    
    # Create an entity
    merchant = world.create_entity(
        name="Greedy Merchant",
        entity_type="npc",
        position=Position(x=0, y=0, region="market")
    )
    
    # Add AI mind
    mind = NPCMind(
        personality_traits={
            PersonalityTrait.GREEDY: 0.9,
            PersonalityTrait.SOCIAL: 0.5
        }
    )
    merchant.add_component(mind)
    
    # Run simulation
    simulation = asyncio.create_task(world.run())
    await asyncio.sleep(30)  # Run for 30 seconds
    
    await world.stop()

asyncio.run(main())
```

## Architecture

### System Layers

```
┌─────────────────────────────────────┐
│         Application Layer           │
│  (Game Logic, Scenarios, Content)   │
├─────────────────────────────────────┤
│           AI Layer                  │
│  (LLM Integration, NPC Behavior)    │
├─────────────────────────────────────┤
│         Economy Layer               │
│  (Markets, Trading, Resources)      │
├─────────────────────────────────────┤
│          World Engine               │
│  (Systems, Tick Loop, Queries)      │
├─────────────────────────────────────┤
│         Core Primitives             │
│  (Entity, Event, Relationship)      │
├─────────────────────────────────────┤
│        Infrastructure               │
│  (Redis, Neo4j, Async Runtime)      │
└─────────────────────────────────────┘
```

### Component Example

```python
# Define custom component
class Reputation(Component):
    values: Dict[str, float] = Field(default_factory=dict)
    
    def modify(self, faction: str, change: float):
        current = self.values.get(faction, 0.0)
        self.values[faction] = max(-1.0, min(1.0, current + change))

# Use it
entity.add_component(Reputation())
rep = entity.get_component(Reputation)
rep.modify("pirates", 0.3)
```

### Event Flow

```python
# Emit event
world.event_bus.emit(Event(
    event_type="trade_proposed",
    entity_id=merchant.id,
    data={"item": "sword", "price": 100}
))

# Handle event
class TradeHandler(EventHandler):
    async def handle(self, event: Event):
        # Process trade logic
        pass
```

## Advanced Features

### Hypergraph Relationships

```python
# Create multi-entity relationship
world.relationships.create_relationship(
    entities={entity1.id, entity2.id, entity3.id},
    relationship_type=RelationshipType.ALLIED_WITH,
    properties=RelationshipProperties(
        strength=RelationshipStrength.STRONG,
        metadata={"formed_at": "battle_of_nassau"}
    )
)
```

### Market Trading

```python
# Submit order
order = Order(
    entity_id=trader.id,
    resource_type=ResourceType.GOLD,
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=100,
    price=1.5
)
trades = matching_engine.submit_order(order)
```

### NPC Decision Making

```python
# Configure NPC behavior
mind = NPCMind(
    personality_traits={
        PersonalityTrait.CURIOUS: 0.8,
        PersonalityTrait.CAUTIOUS: 0.6
    }
)

# Add goals
mind.add_goal(Goal(
    description="Find ancient treasure",
    priority=1.0,
    target_resource=ResourceType.GOLD,
    target_value=1000
))

# Memory system tracks interactions
mind.add_memory(Memory(
    event_type="betrayal",
    description="Betrayed by Black Jack",
    emotional_impact={EmotionalState.ANGRY: 0.8},
    importance=0.9
))
```

### Pattern Detection (Coming Soon)

The event stream enables pattern detection for emergent narratives:

```python
# Detect alliance formation patterns
pattern = PatternDetector(
    name="alliance_cascade",
    trigger_events=["relationship_created"],
    conditions=lambda events: len(events) > 3,
    time_window=300  # 5 minutes
)
```

## Configuration

### Environment Variables

```bash
# LLM Configuration (optional)
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Persistence (optional)
REDIS_URL=redis://localhost:6379
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### World Configuration

```python
config = WorldConfig(
    world_id="unique_id",
    name="Nassau 1715",
    tick_rate=1.0,  # Seconds between ticks
    max_entities=10000,
    enable_persistence=True,
    enable_ai=True
)
```

## Performance Considerations

- **Async by Design**: All I/O operations are async
- **Batch Processing**: Events processed in batches
- **Lazy Loading**: Components loaded on demand
- **Index Everything**: Spatial and relationship indices
- **LRU Caching**: Recently accessed entities cached

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_entity.py::test_component_system
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/

# Type checking
mypy src/
```

### Adding New Systems

```python
class WeatherSystem(WorldSystem):
    def __init__(self):
        super().__init__("WeatherSystem", SystemPriority.LOW)
        
    async def update(self, world: World, delta_time: float):
        # Update weather patterns
        # Affect entity moods, resources, etc.
        pass

# Register with world
world.add_system(WeatherSystem())
```

## Examples

See the `examples/` directory for:
- `simple_world.py` - Basic world with trading NPCs
- `pirate_republic.py` - Nassau-themed scenario
- `ecosystem.py` - Predator-prey dynamics
- `social_network.py` - Relationship dynamics

## Why Python?

After initial Rust implementation, we chose Python for:

1. **LLM Ecosystem**: Native SDKs for all major providers
2. **Rapid Iteration**: Test emergent behaviors quickly
3. **Data Science**: NumPy/Pandas for pattern analysis
4. **Flexibility**: Dynamic typing suits emergent properties
5. **Performance**: Bottleneck is LLM calls, not simulation

The engine handles thousands of entities with sub-second ticks. For millions of entities, consider our Rust implementation or horizontal scaling.

## Roadmap

- [ ] Pattern detection system with ML
- [ ] Distributed world sharding
- [ ] Time-travel debugging UI
- [ ] Narrative generation from event streams
- [ ] Physics simulation integration
- [ ] Advanced economic models
- [ ] Procedural quest generation

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by Dwarf Fortress's emergent storytelling
- Economic models from EVE Online
- Entity-Component pattern from game engines
- Event sourcing from distributed systems