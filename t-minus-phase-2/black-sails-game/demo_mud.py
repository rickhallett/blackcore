#!/usr/bin/env python3
"""Demo script to show the game components work"""

from black_sails_mud.models.character import Character, Background, Stats
from black_sails_mud.models.world import World
from black_sails_mud.ui.display import GameDisplay

def demo():
    """Run a quick demo of the game components"""
    display = GameDisplay()
    
    # Show header
    display.print_header("⚓ Black Sails MUD Demo")
    
    # Create a test character
    display.print("\n[bold]Creating demo character...[/bold]")
    stats = Stats()
    stats.roll_stats()
    
    character = Character(
        name="Jack Sparrow",
        background=Background.PIRATE,
        stats=stats
    )
    
    # Show character sheet
    display.print_character_sheet(character)
    
    # Show location
    display.print("\n[bold]Demo Location:[/bold]")
    world = World()
    location = world.get_location("Nassau Tavern")
    if location:
        display.print_location(location)
    
    # Demo combat display
    display.print("\n[bold]Combat Display Demo:[/bold]")
    display.print_combat_status(character, "One-Legged Pete", 10)
    
    # Demo dice roll
    display.print("\n[bold]Dice Roll Demo:[/bold]")
    display.print_dice_roll(15, 5, 20, True)
    
    # Demo reputation
    display.print("\n[bold]Reputation Display:[/bold]")
    display.print_reputation(character)
    
    # Demo gossip
    display.print("\n[bold]Turn Summary Demo:[/bold]")
    gossip = [
        "Someone taught the parrot new curse words",
        "The British Navy is still looking for their missing pants",
        "One-Legged Pete won a race against a turtle"
    ]
    display.print_turn_summary(gossip)
    
    display.print("\n[bold green]✅ All systems working! Ready to play![/bold green]")
    display.print("\nRun 'python run_mud.py' to start the full game!")

if __name__ == "__main__":
    demo()