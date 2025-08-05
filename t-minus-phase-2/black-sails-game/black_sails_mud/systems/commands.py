"""Command system for the game"""

from typing import Dict, Callable, List, Optional, Tuple
from dataclasses import dataclass
import random

from ..models.character import Character
from ..models.world import World
from ..ui.display import GameDisplay


@dataclass
class CommandResult:
    """Result of executing a command"""
    success: bool
    message: str
    action_cost: int = 1
    combat_triggered: bool = False
    target: Optional[str] = None


class CommandParser:
    """Parse and execute player commands"""
    
    def __init__(self, display: GameDisplay):
        self.display = display
        self.commands: Dict[str, Callable] = {}
        self.aliases: Dict[str, str] = {}
        self._register_commands()
        
    def _register_commands(self):
        """Register all available commands"""
        # Movement
        self.register_command("move", self.cmd_move, ["go", "walk"])
        self.register_command("north", lambda p, w, a: self.cmd_move(p, w, ["north"]))
        self.register_command("south", lambda p, w, a: self.cmd_move(p, w, ["south"]))
        self.register_command("east", lambda p, w, a: self.cmd_move(p, w, ["east"]))
        self.register_command("west", lambda p, w, a: self.cmd_move(p, w, ["west"]))
        self.register_command("up", lambda p, w, a: self.cmd_move(p, w, ["up"]))
        self.register_command("down", lambda p, w, a: self.cmd_move(p, w, ["down"]))
        self.register_command("out", lambda p, w, a: self.cmd_move(p, w, ["out"]))
        
        # Basic actions
        self.register_command("look", self.cmd_look, ["l", "examine"])
        self.register_command("inventory", self.cmd_inventory, ["i", "inv"])
        self.register_command("status", self.cmd_status, ["stats", "sheet"])
        self.register_command("reputation", self.cmd_reputation, ["rep", "faction"])
        
        # Interactions
        self.register_command("talk", self.cmd_talk, ["speak", "chat"])
        self.register_command("attack", self.cmd_attack, ["fight", "kill"])
        self.register_command("drink", self.cmd_drink, ["quaff", "chug"])
        self.register_command("rest", self.cmd_rest, ["sleep", "recover"])
        self.register_command("trade", self.cmd_trade, ["shop", "buy", "sell"])
        
        # Social
        self.register_command("insult", self.cmd_insult, ["mock", "taunt"])
        self.register_command("intimidate", self.cmd_intimidate, ["threaten", "scare"])
        self.register_command("lie", self.cmd_lie, ["deceive", "bluff"])
        
        # System
        self.register_command("help", self.cmd_help, ["?", "commands"])
        self.register_command("quit", self.cmd_quit, ["exit", "logout"])
        self.register_command("save", self.cmd_save)
        
    def register_command(self, name: str, func: Callable, aliases: List[str] = None):
        """Register a command and its aliases"""
        self.commands[name] = func
        if aliases:
            for alias in aliases:
                self.aliases[alias] = name
                
    def parse_command(self, input_str: str) -> Tuple[str, List[str]]:
        """Parse input into command and arguments"""
        parts = input_str.strip().lower().split()
        if not parts:
            return "", []
            
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Resolve aliases
        if command in self.aliases:
            command = self.aliases[command]
            
        return command, args
        
    def execute_command(self, player: Character, world: World, input_str: str) -> CommandResult:
        """Execute a command"""
        command, args = self.parse_command(input_str)
        
        if not command:
            return CommandResult(False, "What?")
            
        if command in self.commands:
            return self.commands[command](player, world, args)
        else:
            return CommandResult(False, f"Unknown command: '{command}'. Type 'help' for commands.")
            
    # Command implementations
    
    def cmd_move(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Move in a direction"""
        if not args:
            return CommandResult(False, "Move where? (try: move north)", action_cost=0)
            
        direction = args[0]
        destination = world.move_possible(player.current_location, direction)
        
        if destination:
            player.current_location = destination
            location = world.get_location(destination)
            
            # Check for random encounter
            encounter_msg = ""
            if location.danger_level > 0 and random.randint(1, 5) <= location.danger_level:
                encounter_msg = "\n[bold red]You've been ambushed![/bold red]"
                
            return CommandResult(
                True, 
                f"You move {direction} to {destination}.{encounter_msg}",
                combat_triggered=bool(encounter_msg)
            )
        else:
            return CommandResult(False, "You can't go that way.", action_cost=0)
            
    def cmd_look(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Look at surroundings or specific target"""
        if not args:
            # Look at current location
            location = world.get_location(player.current_location)
            if location:
                self.display.print_location(location)
                return CommandResult(True, "", action_cost=0)
            else:
                return CommandResult(False, "You're in a void. This shouldn't happen.", action_cost=0)
        else:
            # Look at specific target
            target = " ".join(args)
            
            # Check NPCs
            location = world.get_location(player.current_location)
            if location and target in [npc.lower() for npc in location.npcs]:
                npc_descriptions = {
                    "flint's parrot": "A mangy parrot that somehow knows everyone's secrets. And curses. So many curses.",
                    "one-legged pete": "Pete has the worst luck in Nassau. He's currently losing a game he's not even playing.",
                    "dramatic dave": "Dave gestures wildly as he speaks. 'Dramatic Dave examines you examining him!'",
                    "the philosophical pirate": "'To steal or not to steal,' he muses, 'that is never the question. The question is: how much?'",
                    "nervous ned": "Ned jumps at your gaze. His pockets jingle with hastily grabbed coins.",
                    "mad mary": "Her 'potions' are definitely just rum with food coloring. The prices, however, are very real.",
                    "the overly honest thief": "'I'm going to pick your pocket now,' he announces helpfully.",
                    "eleanor guthrie": "The real power in Nassau. Her ledger is mightier than any sword."
                }
                
                desc = npc_descriptions.get(target, f"{target.title()} looks back at you.")
                return CommandResult(True, desc, action_cost=0)
                
            # Check items
            if location and target in [item.lower() for item in location.items]:
                return CommandResult(True, f"It's {target}. Yep, that's what it is.", action_cost=0)
                
            return CommandResult(False, f"You don't see '{target}' here.", action_cost=0)
            
    def cmd_inventory(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Check inventory"""
        inv_text = f"[bold]Gold:[/bold] {player.gold} 🪙\n"
        inv_text += f"[bold]Rum:[/bold] {player.rum_bottles} 🍾\n"
        inv_text += f"[bold]Weapon:[/bold] {player.weapon or 'Bare Hands'}\n"
        
        if player.inventory:
            inv_text += "[bold]Items:[/bold] " + ", ".join(player.inventory)
        else:
            inv_text += "[bold]Items:[/bold] Nothing but lint and broken dreams"
            
        self.display.print(inv_text)
        return CommandResult(True, "", action_cost=0)
        
    def cmd_status(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Show character sheet"""
        self.display.print_character_sheet(player)
        return CommandResult(True, "", action_cost=0)
        
    def cmd_reputation(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Show reputation standings"""
        self.display.print_reputation(player)
        return CommandResult(True, "", action_cost=0)
        
    def cmd_talk(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Talk to an NPC"""
        if not args:
            return CommandResult(False, "Talk to whom?", action_cost=0)
            
        target = " ".join(args)
        location = world.get_location(player.current_location)
        
        if not location or target not in [npc.lower() for npc in location.npcs]:
            return CommandResult(False, f"There's no '{target}' here to talk to.", action_cost=0)
            
        # NPC responses
        npc_dialogue = {
            "flint's parrot": "SQUAWK! 'Pieces of eight! Also, the governor hides his gold in his left boot!' SQUAWK!",
            "one-legged pete": "'I once had two legs, then I bet one in a game of dice. Don't ask about the eye patch.'",
            "dramatic dave": "'Dramatic Dave speaks to you with great intensity about absolutely nothing!'",
            "the philosophical pirate": "'Is a ship still a ship if you replace every plank? Anyway, want to buy some planks?'",
            "nervous ned": "'I didn't take it! Whatever it is! Oh, you're just talking? ...I still didn't take it.'",
            "mad mary": "'My potions cure what ails ye! Side effects include: everything ailing ye twice as bad.'",
            "the overly honest thief": "'Hello! I'm planning to rob you later. Around 3 o'clock work for you?'",
            "eleanor guthrie": "'If you're not here to trade, you're here to waste my time. Which is it?'"
        }
        
        response = npc_dialogue.get(target, f"{target.title()} grunts noncommittally.")
        return CommandResult(True, response)
        
    def cmd_attack(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Attack someone"""
        if not args:
            return CommandResult(False, "Attack whom?", action_cost=0)
            
        target = " ".join(args)
        location = world.get_location(player.current_location)
        
        if not location or target not in [npc.lower() for npc in location.npcs]:
            return CommandResult(False, f"There's no '{target}' here to attack.", action_cost=0)
            
        if location.safe_zone:
            return CommandResult(False, "You can't fight here! Eleanor would have you hanged.", action_cost=0)
            
        return CommandResult(True, f"You attack {target}!", combat_triggered=True, target=target)
        
    def cmd_drink(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Drink rum"""
        if player.drink_rum():
            drunk_messages = [
                "You take a swig of rum. Liquid courage!",
                "The rum burns going down. You feel braver already.",
                "Another bottle down. The world gets a bit wobblier.",
                "Yo ho ho and a bottle of... where'd it go?",
                "*hic* That's the stuff!"
            ]
            message = drunk_messages[min(player.drunk_level - 1, 4)]
            
            if player.drunk_level >= 5:
                message += "\n[red]You're completely sloshed! -5 to all rolls![/red]"
                
            return CommandResult(True, message)
        else:
            return CommandResult(False, "You're out of rum! Why is the rum always gone?", action_cost=0)
            
    def cmd_rest(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Rest to recover"""
        location = world.get_location(player.current_location)
        
        if not location.rest_available:
            return CommandResult(False, "You can't rest here. Find a tavern or your ship.", action_cost=0)
            
        player.rest()
        return CommandResult(True, "You rest and recover. HP restored, drunk level reduced.", action_cost=3)
        
    def cmd_insult(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Insult someone"""
        if not args:
            return CommandResult(False, "Insult whom?", action_cost=0)
            
        target = " ".join(args)
        location = world.get_location(player.current_location)
        
        if not location or target not in [npc.lower() for npc in location.npcs]:
            return CommandResult(False, f"There's no '{target}' here to insult.", action_cost=0)
            
        insults = [
            f"You fight like a dairy farmer!",
            f"I've seen parrots with more backbone than you!",
            f"Your mother was a hamster and your father smelt of elderberries!",
            f"You call yourself a pirate? I've seen more threatening accountants!",
            f"Even One-Legged Pete could beat you in a race!"
        ]
        
        insult = random.choice(insults)
        self.display.print(f"You: '{insult}'")
        
        # Roll for reaction
        success, roll = player.roll_check("swagger", "intimidation", 12)
        
        if success:
            return CommandResult(True, f"{target.title()} looks insulted and backs down.")
        else:
            return CommandResult(True, f"{target.title()} takes offense! 'Them's fighting words!'", 
                               combat_triggered=True, target=target)
            
    def cmd_trade(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Trade with merchants"""
        location = world.get_location(player.current_location)
        
        if not location.shop_available:
            return CommandResult(False, "There's no one here to trade with.", action_cost=0)
            
        # Simple shop interface
        self.display.print("[bold]Shop Inventory:[/bold]")
        self.display.print("1. Cutlass (20 gold) - +2 to combat")
        self.display.print("2. Pistol (30 gold) - +3 to combat, limited ammo")
        self.display.print("3. Rum (5 gold) - Liquid courage")
        self.display.print("4. Lucky Charm (15 gold) - +1 to fortune")
        
        return CommandResult(True, "What would you like to buy? (Not implemented yet)")
        
    def cmd_help(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Show help"""
        help_text = """[bold yellow]Black Sails MUD Commands:[/bold yellow]

[bold]Movement:[/bold]
  move <direction> - Move to another location
  north/south/east/west/up/down/out - Quick movement
  look [target] - Examine surroundings or specific target

[bold]Actions:[/bold]
  talk <npc> - Speak with someone
  attack <target> - Start combat
  drink - Drink rum (+HP, +swagger, -nimbleness)
  rest - Rest to recover (costs 3 actions)
  trade - Open shop interface

[bold]Character:[/bold]
  status/stats - View character sheet
  inventory/inv - Check your belongings
  reputation/rep - View faction standings

[bold]Social:[/bold]
  insult <target> - Provoke someone
  intimidate <target> - Scare someone
  lie <target> - Attempt deception

[bold]System:[/bold]
  help - Show this help
  save - Save your game
  quit - Exit game"""
        
        self.display.print(help_text)
        return CommandResult(True, "", action_cost=0)
        
    def cmd_intimidate(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Intimidate someone"""
        if not args:
            return CommandResult(False, "Intimidate whom?", action_cost=0)
            
        target = " ".join(args)
        
        # Roll intimidation
        success, roll = player.roll_check("brawn", "intimidation", 15)
        self.display.print_dice_roll(roll - player.stats.get_modifier("brawn") - player.skills.intimidation,
                                    player.stats.get_modifier("brawn") + player.skills.intimidation,
                                    roll, success)
        
        if success:
            return CommandResult(True, f"{target.title()} backs away nervously. Your reputation grows!")
        else:
            return CommandResult(True, f"{target.title()} laughs at your attempt. How embarrassing!")
            
    def cmd_lie(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Tell a lie"""
        if not args:
            lies = [
                "You: 'I'm definitely not a pirate. These are just... nautical enthusiast clothes.'",
                "You: 'The governor? Oh yes, he sent me personally to inspect the... barrels.'",
                "You: 'That's MY ship! I just let Captain Blackbeard borrow it.'",
                "You: 'I've never seen that stolen treasure before in my life!'"
            ]
            self.display.print(random.choice(lies))
            return CommandResult(True, "No one seems to be paying attention to your lies.")
            
        # Lie to specific target
        target = " ".join(args)
        success, roll = player.roll_check("cunning", "lying", 14)
        
        if success:
            return CommandResult(True, f"{target.title()} seems to believe your obvious lies!")
        else:
            return CommandResult(True, f"{target.title()} sees right through you. 'Nice try.'")
            
    def cmd_save(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Save game"""
        # TODO: Implement actual saving
        return CommandResult(True, "Game saved! (Not really implemented yet)", action_cost=0)
        
    def cmd_quit(self, player: Character, world: World, args: List[str]) -> CommandResult:
        """Quit game"""
        return CommandResult(True, "quit", action_cost=0)