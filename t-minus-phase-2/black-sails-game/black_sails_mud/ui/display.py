"""Rich terminal UI for Black Sails MUD"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from rich.columns import Columns
from rich import box
from typing import Optional, List

from ..models.character import Character, Faction
from ..models.world import Location


class GameDisplay:
    """Handles all game display using Rich"""
    
    def __init__(self):
        self.console = Console()
        
    def clear(self):
        """Clear the terminal"""
        self.console.clear()
        
    def print_header(self, title: str):
        """Print a fancy header"""
        header = Text(title, style="bold yellow")
        panel = Panel(header, box=box.DOUBLE, style="yellow")
        self.console.print(panel)
        
    def print_character_sheet(self, character: Character):
        """Display character sheet in a nice format"""
        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stats", size=10),
            Layout(name="skills", size=8),
            Layout(name="status", size=6)
        )
        
        # Header
        header_text = f"[bold yellow]{character.name}[/bold yellow] - {character.background.value}"
        header_panel = Panel(header_text, box=box.ROUNDED)
        layout["header"].update(header_panel)
        
        # Stats table
        stats_table = Table(title="Attributes", box=box.ROUNDED)
        stats_table.add_column("Stat", style="cyan")
        stats_table.add_column("Value", style="green")
        stats_table.add_column("Modifier", style="yellow")
        
        stats_table.add_row("Brawn (STR)", str(character.stats.brawn), 
                           f"+{character.stats.get_modifier('brawn')}")
        stats_table.add_row("Nimbleness (DEX)", str(character.stats.nimbleness),
                           f"+{character.stats.get_modifier('nimbleness')}")
        stats_table.add_row("Cunning (INT)", str(character.stats.cunning),
                           f"+{character.stats.get_modifier('cunning')}")
        stats_table.add_row("Swagger (CHA)", str(character.stats.swagger),
                           f"+{character.stats.get_modifier('swagger')}")
        stats_table.add_row("Sea Legs (CON)", str(character.stats.sea_legs),
                           f"+{character.stats.get_modifier('sea_legs')}")
        stats_table.add_row("Fortune (LUCK)", str(character.stats.fortune),
                           f"+{character.stats.get_modifier('fortune')}")
        
        layout["stats"].update(Panel(stats_table, title="Stats", box=box.ROUNDED))
        
        # Skills table
        skills_table = Table(title="Skills", box=box.ROUNDED)
        skills_table.add_column("Skill", style="cyan")
        skills_table.add_column("Rank", style="green")
        
        skills_table.add_row("Swordplay", str(character.skills.swordplay))
        skills_table.add_row("Pistols", str(character.skills.pistols))
        skills_table.add_row("Sailing", str(character.skills.sailing))
        skills_table.add_row("Drinking", str(character.skills.drinking))
        skills_table.add_row("Lying", str(character.skills.lying))
        skills_table.add_row("Intimidation", str(character.skills.intimidation))
        
        layout["skills"].update(Panel(skills_table, title="Skills", box=box.ROUNDED))
        
        # Status info
        status_text = f"""[bold]Level:[/bold] {character.level} (XP: {character.xp}/{character.xp_to_next})
[bold]HP:[/bold] {character.hp}/{character.max_hp} {"🍺" * character.drunk_level if character.drunk_level > 0 else ""}
[bold]Gold:[/bold] {character.gold} 🪙  [bold]Rum:[/bold] {character.rum_bottles} 🍾
[bold]Weapon:[/bold] {character.weapon or 'Bare Hands'}
[bold]Location:[/bold] {character.current_location}"""
        
        layout["status"].update(Panel(status_text, title="Status", box=box.ROUNDED))
        
        self.console.print(layout)
        
    def print_location(self, location: Location, show_full: bool = True):
        """Display current location"""
        # Location name and type
        loc_style = {
            "tavern": "bold yellow on red",
            "dock": "bold blue",
            "market": "bold green",
            "wilderness": "bold green on black",
            "building": "bold white",
            "ship": "bold cyan"
        }.get(location.location_type.value, "bold white")
        
        self.console.print(f"\n[{loc_style}]{location.name}[/{loc_style}]\n")
        
        if show_full:
            # Description
            self.console.print(Panel(location.description, box=box.ROUNDED))
            
            # NPCs
            if location.npcs:
                npc_text = "You see: " + ", ".join([f"[bold cyan]{npc}[/bold cyan]" 
                                                   for npc in location.npcs])
                self.console.print(npc_text)
                
            # Items
            if location.items:
                item_text = "Items here: " + ", ".join([f"[yellow]{item}[/yellow]" 
                                                       for item in location.items])
                self.console.print(item_text)
                
            # Exits
            self.console.print(f"\n[dim]{location.get_exit_description()}[/dim]")
            
    def print_combat_status(self, player: Character, enemy_name: str, enemy_hp: int):
        """Display combat UI"""
        combat_layout = Layout()
        combat_layout.split_row(
            Layout(name="player", ratio=1),
            Layout(name="vs", size=10),
            Layout(name="enemy", ratio=1)
        )
        
        # Player panel
        player_hp_bar = self._create_hp_bar(player.hp, player.max_hp)
        player_text = f"""[bold green]{player.name}[/bold green]
{player_hp_bar}
HP: {player.hp}/{player.max_hp}
Actions: {"● " * player.actions_remaining}{"○ " * (3 - player.actions_remaining)}"""
        
        combat_layout["player"].update(Panel(player_text, title="You", box=box.ROUNDED))
        
        # VS
        combat_layout["vs"].update(Panel("⚔️", box=box.ROUNDED))
        
        # Enemy panel
        enemy_hp_bar = self._create_hp_bar(enemy_hp, 20)  # Assume 20 max HP for now
        enemy_text = f"""[bold red]{enemy_name}[/bold red]
{enemy_hp_bar}
HP: {enemy_hp}/20"""
        
        combat_layout["enemy"].update(Panel(enemy_text, title="Enemy", box=box.ROUNDED))
        
        self.console.print(combat_layout)
        
    def _create_hp_bar(self, current: int, maximum: int) -> str:
        """Create a visual HP bar"""
        if maximum == 0:
            return "[red]DEAD[/red]"
            
        percent = current / maximum
        filled = int(percent * 10)
        empty = 10 - filled
        
        color = "green" if percent > 0.5 else "yellow" if percent > 0.25 else "red"
        return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
        
    def print_reputation(self, character: Character):
        """Display reputation standings"""
        rep_table = Table(title="Faction Reputation", box=box.ROUNDED)
        rep_table.add_column("Faction", style="cyan")
        rep_table.add_column("Standing", style="bold")
        rep_table.add_column("Reputation", justify="center")
        
        for faction, rep in character.reputation.items():
            # Determine standing
            if rep >= 50:
                standing = "[green]Honored[/green]"
            elif rep >= 20:
                standing = "[green]Friendly[/green]"
            elif rep >= -20:
                standing = "[yellow]Neutral[/yellow]"
            elif rep >= -50:
                standing = "[red]Hostile[/red]"
            else:
                standing = "[bold red]Hated[/bold red]"
                
            # Create reputation bar
            rep_bar = self._create_rep_bar(rep)
            rep_table.add_row(faction.value, standing, rep_bar)
            
        self.console.print(rep_table)
        
    def _create_rep_bar(self, reputation: int) -> str:
        """Create a visual reputation bar from -100 to 100"""
        # Normalize to 0-20 range
        normalized = int((reputation + 100) / 10)
        
        bar = ""
        for i in range(20):
            if i < 10:  # Negative side
                if i < normalized:
                    bar += "[red]█[/red]"
                else:
                    bar += "[dim red]░[/dim red]"
            else:  # Positive side
                if i < normalized:
                    bar += "[green]█[/green]"
                else:
                    bar += "[dim green]░[/dim green]"
                    
        return bar
        
    def print_turn_summary(self, events: List[str]):
        """Print end of turn summary/gossip"""
        if not events:
            return
            
        gossip_text = "📜 [bold yellow]Meanwhile in Nassau...[/bold yellow]\n\n"
        for event in events:
            gossip_text += f"• {event}\n"
            
        self.console.print(Panel(gossip_text, title="Tavern Gossip", box=box.DOUBLE))
        
    def print_dice_roll(self, roll: int, modifiers: int, total: int, success: bool):
        """Animate a dice roll"""
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        
        # Show rolling animation (simplified for now)
        result_text = f"🎲 Rolling... [{roll}]"
        if modifiers != 0:
            result_text += f" + {modifiers}" if modifiers > 0 else f" - {abs(modifiers)}"
        result_text += f" = {total}"
        
        if success:
            result_text += " [bold green]Success![/bold green]"
        else:
            result_text += " [bold red]Failed![/bold red]"
            
        self.console.print(result_text)
        
    def prompt(self, text: str = "> ") -> str:
        """Get input from player"""
        return self.console.input(f"[bold cyan]{text}[/bold cyan]")
        
    def print(self, text: str, style: Optional[str] = None):
        """Print text with optional style"""
        if style:
            self.console.print(f"[{style}]{text}[/{style}]")
        else:
            self.console.print(text)
            
    def print_error(self, text: str):
        """Print error message"""
        self.console.print(f"[bold red]❌ {text}[/bold red]")
        
    def print_success(self, text: str):
        """Print success message"""
        self.console.print(f"[bold green]✅ {text}[/bold green]")
        
    def print_info(self, text: str):
        """Print info message"""
        self.console.print(f"[bold blue]ℹ️  {text}[/bold blue]")