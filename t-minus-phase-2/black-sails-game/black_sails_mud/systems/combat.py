"""Turn-based combat system"""

import random
from typing import Optional, Tuple
from dataclasses import dataclass

from ..models.character import Character
from ..ui.display import GameDisplay


@dataclass
class Combatant:
    """Simple enemy combatant"""
    name: str
    hp: int
    max_hp: int
    attack_bonus: int = 0
    defense: int = 12
    damage: str = "1d6"  # Dice notation
    
    def take_damage(self, amount: int) -> bool:
        """Take damage, return True if still alive"""
        self.hp = max(0, self.hp - amount)
        return self.hp > 0
        
    def roll_damage(self) -> int:
        """Roll damage dice"""
        # Parse dice notation (e.g., "1d6+2")
        if "d" in self.damage:
            parts = self.damage.split("d")
            num_dice = int(parts[0])
            
            if "+" in parts[1]:
                die_parts = parts[1].split("+")
                die_size = int(die_parts[0])
                bonus = int(die_parts[1])
            elif "-" in parts[1]:
                die_parts = parts[1].split("-")
                die_size = int(die_parts[0])
                bonus = -int(die_parts[1])
            else:
                die_size = int(parts[1])
                bonus = 0
                
            total = sum(random.randint(1, die_size) for _ in range(num_dice)) + bonus
            return max(1, total)
        else:
            return int(self.damage)


class CombatSystem:
    """Handles combat encounters"""
    
    def __init__(self, display: GameDisplay):
        self.display = display
        self.enemy_templates = self._create_enemy_templates()
        
    def _create_enemy_templates(self) -> dict:
        """Create enemy templates"""
        return {
            "one-legged pete": Combatant("One-Legged Pete", 15, 15, -2, 10, "1d4"),
            "nervous ned": Combatant("Nervous Ned", 12, 12, 0, 11, "1d6-1"),
            "dramatic dave": Combatant("Dramatic Dave", 18, 18, 1, 13, "1d6"),
            "british guard": Combatant("British Guard", 25, 25, 3, 15, "1d8+1"),
            "the philosophical pirate": Combatant("The Philosophical Pirate", 20, 20, 2, 14, "1d6+1"),
            "the overly honest thief": Combatant("The Overly Honest Thief", 10, 10, 1, 16, "1d4"),
            "angry drunk": Combatant("Angry Drunk", 15, 15, 0, 10, "1d6"),
            "smuggler": Combatant("Smuggler", 18, 18, 2, 13, "1d6+1"),
        }
        
    def create_enemy(self, enemy_type: str) -> Optional[Combatant]:
        """Create an enemy from template"""
        template = self.enemy_templates.get(enemy_type.lower())
        if template:
            # Create a copy
            return Combatant(
                name=template.name,
                hp=template.hp,
                max_hp=template.max_hp,
                attack_bonus=template.attack_bonus,
                defense=template.defense,
                damage=template.damage
            )
        else:
            # Generic enemy
            return Combatant(
                name=enemy_type.title(),
                hp=15,
                max_hp=15,
                attack_bonus=1,
                defense=12,
                damage="1d6"
            )
            
    def start_combat(self, player: Character, enemy_name: str) -> Combatant:
        """Initialize combat encounter"""
        enemy = self.create_enemy(enemy_name)
        
        self.display.print_header(f"⚔️  COMBAT: {player.name} vs {enemy.name}")
        
        # Flavor text
        combat_starts = {
            "one-legged pete": "Pete hobbles toward you, surprisingly fast for a man with one leg!",
            "nervous ned": "Ned attacks in a panic! His sword shakes in his hands!",
            "dramatic dave": "'Dramatic Dave engages in MORTAL COMBAT!' he shouts.",
            "british guard": "The guard draws his sword with practiced efficiency.",
            "the philosophical pirate": "'Violence is the last refuge of the incompetent,' he says, drawing his sword anyway.",
            "the overly honest thief": "'I'm attacking you now!' he announces helpfully."
        }
        
        flavor = combat_starts.get(enemy_name.lower(), f"{enemy.name} attacks!")
        self.display.print(flavor)
        
        return enemy
        
    def player_turn(self, player: Character, enemy: Combatant) -> Tuple[bool, str]:
        """Handle player's turn, return (combat_continues, message)"""
        self.display.print_combat_status(player, enemy.name, enemy.hp)
        
        while True:
            action = self.display.prompt("Combat action (attack/defend/taunt/run): ").lower()
            
            if action in ["a", "attack"]:
                return self._player_attack(player, enemy)
            elif action in ["d", "defend"]:
                return self._player_defend(player, enemy)
            elif action in ["t", "taunt"]:
                return self._player_taunt(player, enemy)
            elif action in ["r", "run"]:
                return self._player_run(player, enemy)
            else:
                self.display.print_error("Invalid action! Try: attack, defend, taunt, or run")
                
    def _player_attack(self, player: Character, enemy: Combatant) -> Tuple[bool, str]:
        """Player attacks enemy"""
        # Roll to hit
        attack_stat = "brawn" if player.weapon else "nimbleness"
        skill = "swordplay" if "sword" in (player.weapon or "").lower() else "pistols"
        
        success, roll = player.roll_check(attack_stat, skill, enemy.defense)
        self.display.print_dice_roll(
            roll - player.stats.get_modifier(attack_stat) - getattr(player.skills, skill, 0),
            player.stats.get_modifier(attack_stat) + getattr(player.skills, skill, 0),
            roll,
            success
        )
        
        if success:
            # Roll damage
            if player.weapon:
                damage = random.randint(1, 8) + player.stats.get_modifier("brawn")
            else:
                damage = random.randint(1, 4) + player.stats.get_modifier("brawn")
                
            damage = max(1, damage)
            
            # Critical hit on natural 20
            if roll - player.stats.get_modifier(attack_stat) - getattr(player.skills, skill, 0) == 20:
                damage *= 2
                self.display.print_success(f"CRITICAL HIT! You deal {damage} damage!")
            else:
                self.display.print_success(f"Hit! You deal {damage} damage!")
                
            if not enemy.take_damage(damage):
                # Enemy defeated
                xp_reward = enemy.max_hp * 5
                gold_reward = random.randint(5, 20)
                
                player.gain_xp(xp_reward)
                player.gold += gold_reward
                
                victory_messages = {
                    "one-legged pete": "Pete falls over. 'Not again!' he groans.",
                    "nervous ned": "Ned drops everything and runs away, leaving his coin purse!",
                    "dramatic dave": "'Dramatic Dave has been... DEFEATED!' he gasps dramatically.",
                    "the philosophical pirate": "'I die, therefore I am... dead,' he philosophizes.",
                    "the overly honest thief": "'You've beaten me fair and square!' he admits."
                }
                
                message = victory_messages.get(enemy.name.lower(), f"{enemy.name} is defeated!")
                message += f"\n[green]You gain {xp_reward} XP and {gold_reward} gold![/green]"
                
                # Improve combat skills
                player.skills.improve(skill)
                
                return False, message
        else:
            self.display.print_error("You miss!")
            
        return True, ""
        
    def _player_defend(self, player: Character, enemy: Combatant) -> Tuple[bool, str]:
        """Player takes defensive stance"""
        self.display.print("You take a defensive stance. (+5 to defense this round)")
        # The bonus will be applied during enemy's attack
        return True, "defend"
        
    def _player_taunt(self, player: Character, enemy: Combatant) -> Tuple[bool, str]:
        """Player taunts enemy"""
        taunts = [
            "You fight like a dairy farmer!",
            "I've met parrots scarier than you!",
            "My grandmother has better swordplay!",
            "You're about as threatening as One-Legged Pete!",
            "Even the British Navy rejects sailors like you!"
        ]
        
        taunt = random.choice(taunts)
        self.display.print(f"You: '{taunt}'")
        
        # Roll to demoralize
        success, roll = player.roll_check("swagger", "intimidation", 14)
        
        if success:
            self.display.print_success(f"{enemy.name} is demoralized! (-2 to attacks)")
            enemy.attack_bonus -= 2
        else:
            self.display.print(f"{enemy.name} is unimpressed.")
            
        return True, ""
        
    def _player_run(self, player: Character, enemy: Combatant) -> Tuple[bool, str]:
        """Player attempts to flee"""
        # Roll to escape
        success, roll = player.roll_check("nimbleness", None, 15)
        
        if success:
            self.display.print_success("You manage to escape!")
            return False, "fled"
        else:
            self.display.print_error("You fail to escape!")
            return True, ""
            
    def enemy_turn(self, player: Character, enemy: Combatant, player_defending: bool) -> Tuple[bool, str]:
        """Handle enemy's turn"""
        # Enemy attack patterns
        if enemy.hp < enemy.max_hp // 3:
            # Low health - desperate attack
            self.display.print(f"{enemy.name} attacks desperately!")
            enemy.attack_bonus += 2
            
        # Roll to hit
        defense = 10 + player.stats.get_modifier("nimbleness")
        if player_defending:
            defense += 5
            
        roll = random.randint(1, 20) + enemy.attack_bonus
        
        if roll >= defense:
            damage = enemy.roll_damage()
            
            # Critical fail for enemy on natural 1
            if roll - enemy.attack_bonus == 1:
                self.display.print_error(f"{enemy.name} fumbles spectacularly!")
                fumbles = [
                    f"{enemy.name} hits themselves for {damage // 2} damage!",
                    f"{enemy.name} drops their weapon!",
                    f"{enemy.name} trips and falls prone!"
                ]
                self.display.print(random.choice(fumbles))
                if "hits themselves" in fumbles[0]:
                    enemy.take_damage(damage // 2)
            else:
                self.display.print_error(f"{enemy.name} hits you for {damage} damage!")
                
                if not player.take_damage(damage):
                    # Player defeated
                    defeat_messages = [
                        "You have been defeated! Your pirating days are over... for now.",
                        "Everything goes black. You wake up missing your gold and dignity.",
                        "You've been bested! Time to respawn at the tavern with a headache."
                    ]
                    return False, random.choice(defeat_messages)
        else:
            self.display.print(f"{enemy.name} misses!")
            
        return True, ""
        
    def run_combat(self, player: Character, enemy_name: str) -> str:
        """Run a complete combat encounter"""
        enemy = self.start_combat(player, enemy_name)
        player_defending = False
        
        # Combat loop
        while True:
            # Player turn
            if player.actions_remaining > 0:
                continues, result = self.player_turn(player, enemy)
                player.actions_remaining -= 1
                
                if not continues:
                    return result
                    
                player_defending = (result == "defend")
            else:
                self.display.print_info("You're out of actions this turn!")
                
            # Enemy turn
            continues, result = self.enemy_turn(player, enemy, player_defending)
            player_defending = False  # Reset defense
            
            if not continues:
                return result