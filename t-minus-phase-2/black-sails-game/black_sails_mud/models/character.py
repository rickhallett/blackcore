"""Character model with D&D style attributes and progression"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Background(Enum):
    PIRATE = "Pirate"
    NAVY_DESERTER = "Navy Deserter"
    MERCHANT = "Merchant"
    STOWAWAY = "Stowaway"


class Faction(Enum):
    PIRATES = "Pirates"
    NAVY = "Navy"
    MERCHANTS = "Merchants"
    LOCALS = "Locals"


@dataclass
class Stats:
    """D&D style character attributes"""
    brawn: int = 10        # STR - Physical power
    nimbleness: int = 10   # DEX - Agility and reflexes
    cunning: int = 10      # INT - Smarts and wit
    swagger: int = 10      # CHA - Charm and presence
    sea_legs: int = 10     # CON - Constitution and stamina
    fortune: int = 10      # LUCK - Special pirate stat
    
    def roll_stats(self):
        """Roll 3d6 for each stat"""
        for attr in ['brawn', 'nimbleness', 'cunning', 'swagger', 'sea_legs', 'fortune']:
            setattr(self, attr, sum(random.randint(1, 6) for _ in range(3)))
    
    def get_modifier(self, stat_name: str) -> int:
        """Get D&D style modifier for a stat"""
        value = getattr(self, stat_name, 10)
        return (value - 10) // 2


@dataclass
class Skills:
    """Skills that improve with use"""
    swordplay: int = 0
    pistols: int = 0
    sailing: int = 0
    drinking: int = 0
    lying: int = 0
    intimidation: int = 0
    
    def improve(self, skill_name: str, amount: int = 1):
        """Improve a skill by amount"""
        current = getattr(self, skill_name, 0)
        setattr(self, skill_name, current + amount)


@dataclass
class Character:
    """Main character class"""
    name: str
    background: Background
    stats: Stats = field(default_factory=Stats)
    skills: Skills = field(default_factory=Skills)
    
    # Core attributes
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100
    hp: int = 10
    max_hp: int = 10
    
    # Resources
    gold: int = 0
    rum_bottles: int = 0
    
    # Equipment
    weapon: Optional[str] = None
    armor: Optional[str] = None
    inventory: List[str] = field(default_factory=list)
    
    # Reputation
    reputation: Dict[Faction, int] = field(default_factory=dict)
    
    # Status effects
    drunk_level: int = 0  # 0-5, affects all rolls
    injuries: List[str] = field(default_factory=list)
    
    # Turn tracking
    actions_remaining: int = 3
    current_location: str = "Nassau Tavern"
    
    def __post_init__(self):
        """Initialize character based on background"""
        # Set starting reputation
        for faction in Faction:
            self.reputation[faction] = 0
            
        # Background bonuses
        if self.background == Background.PIRATE:
            self.skills.swordplay = 2
            self.skills.intimidation = 1
            self.reputation[Faction.PIRATES] = 20
            self.reputation[Faction.NAVY] = -20
            self.weapon = "Rusty Cutlass"
            self.gold = 10
            self.rum_bottles = 2
            
        elif self.background == Background.NAVY_DESERTER:
            self.skills.swordplay = 1
            self.skills.pistols = 2
            self.reputation[Faction.NAVY] = -50
            self.reputation[Faction.PIRATES] = 10
            self.weapon = "Navy Pistol"
            self.gold = 20
            
        elif self.background == Background.MERCHANT:
            self.skills.lying = 2
            self.skills.sailing = 1
            self.reputation[Faction.MERCHANTS] = 30
            self.gold = 50
            self.inventory.append("Ledger Book")
            
        elif self.background == Background.STOWAWAY:
            self.skills.lying = 1
            self.skills.nimbleness = 2
            self.stats.fortune += 2
            self.gold = 5
            self.inventory.append("Lucky Coin")
            
        # Calculate starting HP
        self.max_hp = 10 + self.stats.get_modifier('sea_legs')
        self.hp = self.max_hp
    
    def roll_check(self, stat: str, skill: Optional[str] = None, 
                   difficulty: int = 15) -> tuple[bool, int]:
        """Roll d20 + modifiers vs difficulty"""
        roll = random.randint(1, 20)
        
        # Get stat modifier
        stat_mod = self.stats.get_modifier(stat)
        
        # Get skill bonus if applicable
        skill_bonus = 0
        if skill:
            skill_bonus = getattr(self.skills, skill, 0)
            
        # Apply drunk penalty
        drunk_penalty = -self.drunk_level
        
        # Lucky bonus on natural 7
        lucky_bonus = 0
        if roll == 7:
            lucky_bonus = self.stats.get_modifier('fortune')
            
        total = roll + stat_mod + skill_bonus + drunk_penalty + lucky_bonus
        
        return (total >= difficulty, total)
    
    def gain_xp(self, amount: int):
        """Gain XP and potentially level up"""
        self.xp += amount
        
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level_up()
            
    def level_up(self):
        """Level up character"""
        self.level += 1
        self.xp_to_next = self.level * 100
        
        # Increase HP
        hp_gain = random.randint(1, 6) + self.stats.get_modifier('sea_legs')
        self.max_hp += max(1, hp_gain)
        self.hp = self.max_hp
        
        # Stat increase every 3 levels
        if self.level % 3 == 0:
            # Player gets to choose which stat to increase
            # For now, random
            stats_list = ['brawn', 'nimbleness', 'cunning', 'swagger', 'sea_legs', 'fortune']
            chosen_stat = random.choice(stats_list)
            current = getattr(self.stats, chosen_stat)
            setattr(self.stats, chosen_stat, current + 1)
    
    def modify_reputation(self, faction: Faction, amount: int):
        """Modify reputation with a faction"""
        self.reputation[faction] = max(-100, min(100, self.reputation[faction] + amount))
        
    def drink_rum(self):
        """Drink rum - improves swagger, reduces nimbleness"""
        if self.rum_bottles > 0:
            self.rum_bottles -= 1
            self.drunk_level = min(5, self.drunk_level + 1)
            self.hp = min(self.max_hp, self.hp + 2)  # Liquid courage
            return True
        return False
    
    def rest(self):
        """Rest to recover HP and reduce drunk level"""
        self.hp = min(self.max_hp, self.hp + 5)
        self.drunk_level = max(0, self.drunk_level - 1)
        self.actions_remaining = 3
        
    def take_damage(self, amount: int) -> bool:
        """Take damage, return True if still alive"""
        self.hp -= amount
        
        if self.hp <= 0:
            self.hp = 0
            return False
        return True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for saving"""
        return {
            'name': self.name,
            'background': self.background.value,
            'stats': self.stats.__dict__,
            'skills': self.skills.__dict__,
            'level': self.level,
            'xp': self.xp,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'gold': self.gold,
            'rum_bottles': self.rum_bottles,
            'weapon': self.weapon,
            'armor': self.armor,
            'inventory': self.inventory,
            'reputation': {k.value: v for k, v in self.reputation.items()},
            'drunk_level': self.drunk_level,
            'injuries': self.injuries,
            'current_location': self.current_location
        }