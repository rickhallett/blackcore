"""World model with locations and connections"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum


class LocationType(Enum):
    TAVERN = "tavern"
    DOCK = "dock"
    MARKET = "market"
    WILDERNESS = "wilderness"
    BUILDING = "building"
    SHIP = "ship"


@dataclass
class Location:
    """A location in the game world"""
    name: str
    description: str
    location_type: LocationType
    connections: Dict[str, str] = field(default_factory=dict)  # direction: location_name
    npcs: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    activities: List[str] = field(default_factory=list)
    danger_level: int = 0  # 0-5, chance of random encounters
    
    # Special flags
    safe_zone: bool = False  # No PvP
    rest_available: bool = False
    shop_available: bool = False
    quest_board: bool = False
    
    def get_exits(self) -> List[str]:
        """Get available exits"""
        return list(self.connections.keys())
    
    def get_exit_description(self) -> str:
        """Get formatted exit description"""
        if not self.connections:
            return "There are no obvious exits."
        
        exits = ", ".join(self.connections.keys())
        return f"Exits: {exits}"


class World:
    """The game world"""
    
    def __init__(self):
        self.locations: Dict[str, Location] = {}
        self.starting_location = "Nassau Tavern"
        self._create_world()
        
    def _create_world(self):
        """Create the game world locations"""
        
        # Nassau Tavern - Main hub
        self.locations["Nassau Tavern"] = Location(
            name="Nassau Tavern",
            description=(
                "Eleanor Guthrie's establishment buzzes with activity. Pirates, "
                "merchants, and mysterious figures huddle over drinks. A large "
                "QUEST BOARD dominates one wall, while a suspicious parrot "
                "eyes your coin purse from its perch."
            ),
            location_type=LocationType.TAVERN,
            connections={
                "out": "Nassau Square",
                "upstairs": "Tavern Rooms",
                "cellar": "Secret Gambling Den"
            },
            npcs=["Eleanor Guthrie", "Flint's Parrot", "One-Legged Pete", "Dramatic Dave"],
            activities=["drink", "gamble", "rest", "trade"],
            safe_zone=True,
            rest_available=True,
            shop_available=True,
            quest_board=True
        )
        
        # Nassau Square - Central area
        self.locations["Nassau Square"] = Location(
            name="Nassau Square",
            description=(
                "The heart of Nassau bustles with pirates, merchants, and the "
                "occasional British spy trying too hard to blend in. A gallows "
                "stands ominously in the center, currently unoccupied. Street "
                "vendors hawk their wares while pickpockets work the crowd."
            ),
            location_type=LocationType.MARKET,
            connections={
                "north": "The Docks",
                "south": "Governor's Mansion",
                "east": "Nassau Tavern",
                "west": "Warehouse District"
            },
            npcs=["The Overly Honest Thief", "Mad Mary", "Street Vendor"],
            danger_level=1
        )
        
        # The Docks - Ships and sea access
        self.locations["The Docks"] = Location(
            name="The Docks",
            description=(
                "Ships of all sizes bob in the harbor. The smell of salt, tar, "
                "and yesterday's catch fills the air. Sailors stumble between "
                "ships and taverns while merchants nervously guard their cargo. "
                "A philosophical pirate contemplates the meaning of plunder."
            ),
            location_type=LocationType.DOCK,
            connections={
                "south": "Nassau Square",
                "east": "Shipwright's Shop",
                "west": "Smuggler's Cove",
                "ship": "The Rusty Anchor"
            },
            npcs=["The Philosophical Pirate", "Nervous Ned", "Salty Sam the Shipwright"],
            activities=["sail", "trade", "recruit"],
            danger_level=2
        )
        
        # Governor's Mansion - High risk, high reward
        self.locations["Governor's Mansion"] = Location(
            name="Governor's Mansion",
            description=(
                "The Governor's mansion looms before you, its white walls "
                "gleaming in stark contrast to the rest of Nassau. British "
                "soldiers patrol the grounds, looking bored and hot in their "
                "uniforms. You can practically smell the gold inside."
            ),
            location_type=LocationType.BUILDING,
            connections={
                "north": "Nassau Square",
                "sneak": "Mansion Gardens"
            },
            npcs=["British Guard", "Pompous Butler"],
            danger_level=4
        )
        
        # Warehouse District - Trade and smuggling
        self.locations["Warehouse District"] = Location(
            name="Warehouse District",
            description=(
                "Rows of warehouses stretch before you, some legitimate, "
                "most... not so much. The air is thick with the scent of "
                "spices, gunpowder, and profit. Shady deals happen in every "
                "shadow, and everyone pretends not to notice."
            ),
            location_type=LocationType.MARKET,
            connections={
                "east": "Nassau Square",
                "north": "Black Market",
                "south": "Abandoned Warehouse"
            },
            npcs=["Shady Merchant", "Warehouse Guard", "Lost Tourist"],
            activities=["trade", "steal", "hide"],
            danger_level=2,
            shop_available=True
        )
        
        # Secret Gambling Den
        self.locations["Secret Gambling Den"] = Location(
            name="Secret Gambling Den",
            description=(
                "Down a rickety staircase, you find Nassau's worst-kept secret: "
                "a gambling den where fortunes are won and lost faster than you "
                "can say 'parley'. One-Legged Pete is here, somehow already "
                "losing despite just arriving."
            ),
            location_type=LocationType.BUILDING,
            connections={
                "up": "Nassau Tavern"
            },
            npcs=["Gambling Denis", "Cheating Charlie", "One-Legged Pete"],
            activities=["gamble", "cheat", "brawl"],
            danger_level=2
        )
        
        # The Rusty Anchor - Player ship
        self.locations["The Rusty Anchor"] = Location(
            name="The Rusty Anchor",
            description=(
                "Your 'ship' - and we use that term loosely. The Rusty Anchor "
                "is more rust than anchor at this point, but she floats... "
                "mostly. The crew consists of you and a very judgmental seagull."
            ),
            location_type=LocationType.SHIP,
            connections={
                "dock": "The Docks",
                "sail": "Open Sea"
            },
            npcs=["Judgmental Seagull"],
            activities=["rest", "repair", "sail"],
            safe_zone=True,
            rest_available=True
        )
        
        # Smuggler's Cove - Hidden location
        self.locations["Smuggler's Cove"] = Location(
            name="Smuggler's Cove",
            description=(
                "A hidden cove known only to the saltiest of sea dogs. Barrels "
                "of 'definitely legal' goods are stacked high. A one-eyed cat "
                "guards the entrance, demanding tribute in fish or coin."
            ),
            location_type=LocationType.WILDERNESS,
            connections={
                "east": "The Docks",
                "tunnel": "Secret Tunnel"
            },
            npcs=["One-Eyed Cat", "Smuggler Jim", "Definitely Not a Spy"],
            items=["Mysterious Crate", "Bottle of Rum"],
            danger_level=3
        )
        
        # Add more locations as needed...
        
    def get_location(self, name: str) -> Optional[Location]:
        """Get a location by name"""
        return self.locations.get(name)
    
    def move_possible(self, from_location: str, direction: str) -> Optional[str]:
        """Check if movement is possible, return destination"""
        location = self.get_location(from_location)
        if location and direction in location.connections:
            return location.connections[direction]
        return None
    
    def get_all_npcs_at(self, location_name: str) -> List[str]:
        """Get all NPCs at a location"""
        location = self.get_location(location_name)
        return location.npcs if location else []
    
    def get_all_items_at(self, location_name: str) -> List[str]:
        """Get all items at a location"""
        location = self.get_location(location_name)
        return location.items if location else []