"""Main game loop and logic"""

import random
import asyncio
from typing import Optional, List
from datetime import datetime

from .models.character import Character, Background, Stats
from .models.world import World
from .systems.commands import CommandParser, CommandResult
from .systems.combat import CombatSystem
from .ui.display import GameDisplay


class BlackSailsMUD:
    """Main game class"""
    
    def __init__(self):
        self.display = GameDisplay()
        self.world = World()
        self.command_parser = CommandParser(self.display)
        self.combat_system = CombatSystem(self.display)
        self.players: List[Character] = []
        self.turn_number = 0
        self.gossip_events: List[str] = []
        
    def create_character(self) -> Character:
        """Character creation process"""
        self.display.clear()
        self.display.print_header("⚓ Black Sails MUD - Character Creation")
        
        # Get name
        name = self.display.prompt("What be yer name, sailor? ")
        
        # Choose background
        self.display.print("\n[bold]Choose your background:[/bold]")
        self.display.print("1. [red]Pirate[/red] - Born to the sea and violence (+swordplay, +intimidation)")
        self.display.print("2. [blue]Navy Deserter[/blue] - Fled the King's service (+pistols, +discipline)")
        self.display.print("3. [yellow]Merchant[/yellow] - Money is your religion (+lying, +sailing)")
        self.display.print("4. [green]Stowaway[/green] - Lucky to be alive (+fortune, +nimbleness)")
        
        while True:
            choice = self.display.prompt("Choose (1-4): ")
            if choice in ["1", "2", "3", "4"]:
                background = [Background.PIRATE, Background.NAVY_DESERTER, 
                            Background.MERCHANT, Background.STOWAWAY][int(choice) - 1]
                break
            else:
                self.display.print_error("Invalid choice!")
                
        # Roll stats
        self.display.print("\n[bold]Rolling your attributes...[/bold]")
        stats = Stats()
        stats.roll_stats()
        
        # Create character
        character = Character(name=name, background=background, stats=stats)
        
        # Show results
        self.display.print("\n[bold green]Character created![/bold green]")
        self.display.print_character_sheet(character)
        
        self.display.prompt("\nPress Enter to begin your adventure...")
        return character
        
    def generate_gossip(self, current_player: Character) -> List[str]:
        """Generate random gossip about what happened in Nassau"""
        events = []
        
        # Random events
        random_events = [
            "Someone taught the parrot new curse words in three languages",
            "The British Navy is still looking for their missing pants",
            "Mad Mary's 'healing potion' turned someone's beard blue",
            "A merchant ship arrived carrying nothing but coconuts",
            "The Philosophical Pirate started a book club. No one joined",
            "Dramatic Dave narrated his own bar fight. He lost dramatically",
            "One-Legged Pete won a race. His opponent was a turtle",
            "The Governor's wig was stolen. Again.",
            "Someone tried to pay their tab with 'treasure map'. It was a napkin",
            "Nervous Ned jumped at his own shadow. Twice.",
            "The Overly Honest Thief returned stolen goods with interest"
        ]
        
        # Add 2-3 random events
        num_events = random.randint(2, 3)
        for _ in range(num_events):
            events.append(random.choice(random_events))
            
        # Add player-specific event if another player exists
        if len(self.players) > 1:
            other_player = [p for p in self.players if p != current_player][0]
            player_events = [
                f"{other_player.name} was seen stumbling out of the tavern",
                f"{other_player.name} got into a heated debate about parrot rights",
                f"{other_player.name} claims to have found real treasure (it's fool's gold)",
                f"Someone saw {other_player.name} practicing sword fighting with a mop"
            ]
            events.append(random.choice(player_events))
            
        return events
        
    def process_turn(self, player: Character) -> bool:
        """Process a player's turn, return False if quitting"""
        # Reset actions at start of turn
        if player.actions_remaining == 0:
            player.actions_remaining = 3
            self.turn_number += 1
            
            # Show turn start
            self.display.clear()
            self.display.print_header(f"Turn {self.turn_number} - {player.name}")
            
            # Show gossip from last turn
            if self.gossip_events:
                self.display.print_turn_summary(self.gossip_events)
                self.gossip_events.clear()
                
        # Show current location
        location = self.world.get_location(player.current_location)
        if location:
            self.display.print_location(location, show_full=True)
            
        # Show actions remaining
        actions_display = "● " * player.actions_remaining + "○ " * (3 - player.actions_remaining)
        self.display.print(f"\nActions: {actions_display}")
        
        # Get command
        command = self.display.prompt()
        
        # Process command
        result = self.command_parser.execute_command(player, self.world, command)
        
        # Handle result
        if result.message:
            if result.message == "quit":
                return False
            self.display.print(result.message)
            
        # Handle combat
        if result.combat_triggered and result.target:
            combat_result = self.combat_system.run_combat(player, result.target)
            self.display.print(combat_result)
            
            # Remove defeated NPCs
            if "defeat" in combat_result.lower() or "gain" in combat_result.lower():
                location = self.world.get_location(player.current_location)
                if location and result.target in [npc.lower() for npc in location.npcs]:
                    # Find and remove the NPC
                    for npc in location.npcs[:]:
                        if npc.lower() == result.target.lower():
                            location.npcs.remove(npc)
                            break
                            
        # Deduct action cost
        if result.success and result.action_cost > 0:
            player.actions_remaining -= result.action_cost
            
        # End of turn
        if player.actions_remaining <= 0:
            self.display.print("\n[dim]End of turn. Press Enter to continue...[/dim]")
            self.display.prompt("")
            
            # Generate gossip for next turn
            self.gossip_events = self.generate_gossip(player)
            
        return True
        
    def run_single_player(self):
        """Run single player game"""
        # Character creation
        player = self.create_character()
        self.players.append(player)
        
        # Introduction
        self.display.clear()
        self.display.print_header("Welcome to Nassau!")
        
        intro_text = """The year is 1715. Nassau has become a republic of pirates, 
a place where fortune favors the bold and the foolish rarely survive long.

You've just arrived at Eleanor Guthrie's tavern, the heart of Nassau's 
underground economy. The smell of rum, sweat, and opportunity fills the air.

Your adventure begins here. Type 'help' for commands."""
        
        self.display.print(intro_text)
        self.display.prompt("\nPress Enter to start...")
        
        # Main game loop
        running = True
        while running:
            running = self.process_turn(player)
            
        # Game over
        self.display.print("\n[bold yellow]Fair winds and following seas, pirate![/bold yellow]")
        
    async def run_multiplayer(self, port: int = 9999):
        """Run multiplayer server (basic implementation)"""
        # TODO: Implement actual networking
        self.display.print(f"Multiplayer server would run on port {port}")
        self.display.print("Not implemented yet - run in single player mode!")
        
    def run(self, mode: str = "single", **kwargs):
        """Main entry point"""
        if mode == "single":
            self.run_single_player()
        elif mode == "multi":
            asyncio.run(self.run_multiplayer(**kwargs))
        else:
            self.display.print_error(f"Unknown mode: {mode}")


def main():
    """Entry point for the game"""
    import sys
    
    game = BlackSailsMUD()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "server":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
            game.run("multi", port=port)
        elif sys.argv[1] == "connect":
            # TODO: Implement client connection
            game.display.print("Client mode not implemented yet!")
        else:
            game.run("single")
    else:
        game.run("single")


if __name__ == "__main__":
    main()