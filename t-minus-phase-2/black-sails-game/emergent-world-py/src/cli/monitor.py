"""Rich CLI for real-time world monitoring."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from ..core import Entity, RelationshipType, ResourceType
from ..world import World, WorldConfig
from ..economy import MarketSystem
from ..ai import NPCMindSystem
from ..patterns import PatternSystem

app = typer.Typer()
console = Console()


class WorldMonitor:
    """Real-time world monitoring interface."""
    
    def __init__(self, world: World):
        self.world = world
        self.layout = self._create_layout()
        self.start_time = time.time()
        self.last_update = time.time()
        self.event_history: List[Dict[str, Any]] = []
        self.max_events = 20
    
    def _create_layout(self) -> Layout:
        """Create the layout structure."""
        layout = Layout()
        
        # Main split
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Body split
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="center"),
            Layout(name="right")
        )
        
        # Left column
        layout["left"].split_column(
            Layout(name="stats", size=10),
            Layout(name="entities"),
            Layout(name="patterns", size=8)
        )
        
        # Center column
        layout["center"].split_column(
            Layout(name="events"),
            Layout(name="market", size=12)
        )
        
        # Right column
        layout["right"].split_column(
            Layout(name="relationships"),
            Layout(name="npcs")
        )
        
        return layout
    
    def update(self) -> None:
        """Update all panels."""
        self.layout["header"].update(self._create_header())
        self.layout["stats"].update(self._create_stats())
        self.layout["entities"].update(self._create_entities())
        self.layout["patterns"].update(self._create_patterns())
        self.layout["events"].update(self._create_events())
        self.layout["market"].update(self._create_market())
        self.layout["relationships"].update(self._create_relationships())
        self.layout["npcs"].update(self._create_npcs())
        self.layout["footer"].update(self._create_footer())
        
        self.last_update = time.time()
    
    def _create_header(self) -> Panel:
        """Create header panel."""
        stats = self.world.get_stats()
        uptime = time.time() - self.start_time
        
        header_text = Text()
        header_text.append("🌍 Emergent World Monitor", style="bold cyan")
        header_text.append(f" | World: {stats['name']}", style="white")
        header_text.append(f" | Tick: {stats['tick_count']}", style="yellow")
        header_text.append(f" | Uptime: {uptime:.0f}s", style="green")
        
        return Panel(header_text, style="bold")
    
    def _create_stats(self) -> Panel:
        """Create statistics panel."""
        stats = self.world.get_stats()
        
        table = Table(show_header=False, padding=(0, 1))
        table.add_column("Stat", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Entities", str(stats["entity_count"]))
        table.add_row("Relationships", str(stats["relationship_count"]))
        table.add_row("Events", str(stats["event_count"]))
        table.add_row("Active Systems", str(len([s for s in stats["systems"] if s["enabled"]])))
        
        return Panel(table, title="📊 Statistics", border_style="blue")
    
    def _create_entities(self) -> Panel:
        """Create entities panel."""
        entities = list(self.world.entities.values())[:10]  # Top 10
        
        tree = Tree("🎭 Entities")
        
        # Group by type
        by_type: Dict[str, List[Entity]] = {}
        for entity in entities:
            if entity.identity:
                entity_type = entity.identity.entity_type
                if entity_type not in by_type:
                    by_type[entity_type] = []
                by_type[entity_type].append(entity)
        
        for entity_type, type_entities in by_type.items():
            type_branch = tree.add(f"[yellow]{entity_type}[/yellow]")
            
            for entity in type_entities[:5]:  # Max 5 per type
                name = entity.identity.name if entity.identity else "Unknown"
                
                # Get resources
                resources_str = ""
                bundle = entity.get_component(ResourceBundle)
                if bundle:
                    resources = bundle.get_summary()
                    if resources:
                        res_parts = []
                        for res_type, amount in list(resources.items())[:3]:
                            res_parts.append(f"{res_type}: {amount:.0f}")
                        resources_str = f" [{', '.join(res_parts)}]"
                
                type_branch.add(f"{name}{resources_str}")
        
        return Panel(tree, title="🎭 Active Entities", border_style="green")
    
    def _create_patterns(self) -> Panel:
        """Create patterns panel."""
        pattern_system = None
        for system in self.world.systems:
            if isinstance(system, PatternSystem):
                pattern_system = system
                break
        
        if not pattern_system:
            return Panel("No pattern system active", title="🔮 Patterns")
        
        stats = pattern_system.detector.get_statistics()
        
        table = Table(show_header=True, padding=(0, 1))
        table.add_column("Pattern", style="cyan")
        table.add_column("Count", style="white")
        
        for pattern_name, count in sorted(
            stats["pattern_counts"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            table.add_row(pattern_name.replace("_", " ").title(), str(count))
        
        # Add active patterns
        if stats["active_patterns"] > 0:
            table.add_row("", "")
            table.add_row("[bold]Active Now[/bold]", f"[bold]{stats['active_patterns']}[/bold]")
        
        return Panel(table, title="🔮 Pattern Detection", border_style="magenta")
    
    def _create_events(self) -> Panel:
        """Create events panel."""
        # Get recent events
        recent_events = self.world.event_bus.event_store.events
        event_list = sorted(recent_events.values(), key=lambda e: e.timestamp, reverse=True)[:self.max_events]
        
        table = Table(show_header=True, padding=(0, 1))
        table.add_column("Time", style="dim", width=8)
        table.add_column("Type", style="cyan")
        table.add_column("Details", style="white")
        
        for event in event_list:
            # Format time
            event_time = datetime.fromtimestamp(event.timestamp)
            time_str = event_time.strftime("%H:%M:%S")
            
            # Format type
            event_type = event.event_type.replace("_", " ").title()
            
            # Format details
            details = ""
            if event.entity_id:
                entity = self.world.get_entity(event.entity_id)
                if entity and entity.identity:
                    details = f"{entity.identity.name}"
            
            # Add specific details based on type
            if event.event_type == "trade_executed":
                price = event.data.get("price", 0)
                quantity = event.data.get("quantity", 0)
                details += f" | {quantity:.0f} @ ${price:.2f}"
            elif event.event_type == "relationship_created":
                rel_type = event.data.get("type", "unknown")
                details += f" | {rel_type}"
            elif event.event_type == "npc_decision":
                action = event.data.get("action", "unknown")
                details += f" | {action}"
            
            table.add_row(time_str, event_type, details)
        
        return Panel(table, title="📡 Event Stream", border_style="cyan")
    
    def _create_market(self) -> Panel:
        """Create market panel."""
        market_system = None
        for system in self.world.systems:
            if isinstance(system, MarketSystem):
                market_system = system
                break
        
        if not market_system or not market_system.matching_engine:
            return Panel("No market system active", title="📈 Markets")
        
        table = Table(show_header=True, padding=(0, 1))
        table.add_column("Resource", style="cyan")
        table.add_column("Last", style="white")
        table.add_column("Bid", style="green")
        table.add_column("Ask", style="red")
        table.add_column("Volume", style="yellow")
        
        for resource_type in [ResourceType.GOLD, ResourceType.FOOD, ResourceType.WOOD]:
            data = market_system.matching_engine.get_market_data(resource_type)
            
            last = f"${data['last_price']:.2f}" if data['last_price'] else "-"
            bid = f"${data['bid']:.2f}" if data['bid'] else "-"
            ask = f"${data['ask']:.2f}" if data['ask'] else "-"
            volume = f"{data['volume']:.0f}" if data['volume'] else "0"
            
            table.add_row(resource_type.value.title(), last, bid, ask, volume)
        
        return Panel(table, title="📈 Market Data", border_style="yellow")
    
    def _create_relationships(self) -> Panel:
        """Create relationships panel."""
        # Count relationships by type
        rel_counts: Dict[str, int] = {}
        total_strength = 0.0
        
        for edge in self.world.relationships.hyperedges.values():
            rel_type = edge.relationship_type.value
            rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
            total_strength += edge.properties.weight
        
        table = Table(show_header=True, padding=(0, 1))
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="white")
        
        for rel_type, count in sorted(rel_counts.items(), key=lambda x: x[1], reverse=True):
            table.add_row(rel_type.replace("_", " ").title(), str(count))
        
        if rel_counts:
            avg_strength = total_strength / len(self.world.relationships.hyperedges)
            table.add_row("", "")
            table.add_row("[dim]Avg Strength[/dim]", f"[dim]{avg_strength:.2f}[/dim]")
        
        return Panel(table, title="🔗 Relationships", border_style="green")
    
    def _create_npcs(self) -> Panel:
        """Create NPC status panel."""
        npcs = self.world.query_entities().with_component(NPCMind).execute()[:5]
        
        tree = Tree("🧠 NPC Minds")
        
        for npc in npcs:
            if not npc.identity:
                continue
            
            mind = npc.get_component(NPCMind)
            if not mind:
                continue
            
            npc_branch = tree.add(f"[bold]{npc.identity.name}[/bold]")
            
            # Emotional state
            emotion_style = {
                "happy": "green",
                "sad": "blue",
                "angry": "red",
                "fearful": "yellow",
                "neutral": "white"
            }.get(mind.emotional_state.value, "white")
            
            npc_branch.add(f"[{emotion_style}]Emotion: {mind.emotional_state.value}[/{emotion_style}]")
            
            # Personality
            personality = mind.get_personality_summary()
            if personality:
                npc_branch.add(f"Traits: {personality}")
            
            # Current goal
            active_goals = [g for g in mind.goals if not g.completed]
            if active_goals:
                goal = active_goals[0]
                npc_branch.add(f"Goal: {goal.description[:30]}...")
            
            # Memory count
            npc_branch.add(f"Memories: {len(mind.memories)}")
        
        return Panel(tree, title="🧠 NPC Status", border_style="magenta")
    
    def _create_footer(self) -> Panel:
        """Create footer panel."""
        instructions = Text()
        instructions.append("Commands: ", style="bold")
        instructions.append("q", style="bold cyan")
        instructions.append(" - quit | ", style="white")
        instructions.append("p", style="bold cyan")
        instructions.append(" - pause | ", style="white")
        instructions.append("r", style="bold cyan")
        instructions.append(" - resume | ", style="white")
        instructions.append("s", style="bold cyan")
        instructions.append(" - stats", style="white")
        
        return Panel(instructions, style="dim")


async def run_monitor(world: World, refresh_rate: float = 1.0) -> None:
    """Run the monitoring interface."""
    monitor = WorldMonitor(world)
    
    with Live(monitor.layout, refresh_per_second=1/refresh_rate, screen=True) as live:
        try:
            while True:
                monitor.update()
                await asyncio.sleep(refresh_rate)
        except KeyboardInterrupt:
            pass


@app.command()
def monitor(
    world_config: Optional[str] = None,
    refresh_rate: float = 1.0
):
    """Launch the world monitor interface."""
    console.print("[bold cyan]🌍 Emergent World Monitor[/bold cyan]")
    console.print("Loading world...\n")
    
    # Create or load world
    if world_config:
        # TODO: Load from config file
        config = WorldConfig()
    else:
        config = WorldConfig(
            name="Monitored World",
            tick_rate=1.0,
            enable_persistence=False
        )
    
    world = World(config)
    
    # Add systems
    world.add_system(MarketSystem())
    world.add_system(NPCMindSystem())
    world.add_system(PatternSystem())
    
    async def run():
        await world.initialize()
        
        # Create some demo entities
        console.print("Creating demo entities...\n")
        
        for i in range(5):
            entity = world.create_entity(
                name=f"Entity_{i}",
                entity_type="npc" if i % 2 == 0 else "merchant"
            )
            
            # Add resources
            from ..core import ResourceBundle, Resource
            bundle = ResourceBundle()
            bundle.add_resource(Resource(
                resource_type=ResourceType.GOLD,
                amount=100.0 + i * 20
            ))
            entity.add_component(bundle)
            
            # Add mind to some
            if i % 2 == 0:
                from ..ai import NPCMind, PersonalityTrait
                mind = NPCMind(
                    personality_traits={
                        PersonalityTrait.CURIOUS: 0.7,
                        PersonalityTrait.SOCIAL: 0.5
                    }
                )
                entity.add_component(mind)
        
        # Start world simulation
        world_task = asyncio.create_task(world.run())
        
        # Run monitor
        await run_monitor(world, refresh_rate)
        
        # Clean up
        await world.stop()
        await world_task
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped by user[/yellow]")


if __name__ == "__main__":
    app()