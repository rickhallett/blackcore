# Black Sails MUD - Quick Start Guide

A turn-based MUD-style pirate adventure with D&D mechanics and humor!

## Installation

```bash
# Install dependencies
pip install -r requirements_mud.txt
```

## Running the Game

```bash
# Single player mode (default)
python run_mud.py

# Or directly
python -m black_sails_mud.game
```

## Features

- **D&D Style Character Creation**: Roll 3d6 for stats!
- **Turn-Based Combat**: 3 actions per turn
- **Faction Reputation**: Pirates, Navy, Merchants, Locals
- **Funny NPCs**: Each with unique personality
- **Rich Terminal UI**: Beautiful console interface
- **Drinking Mechanic**: Liquid courage (with consequences)
- **XP & Leveling**: Get stronger as you play

## Quick Commands

- `move <direction>` or just `north`, `south`, etc.
- `look` - Examine surroundings
- `talk <npc>` - Chat with NPCs
- `attack <target>` - Start combat
- `drink` - Drink rum (+HP, -accuracy)
- `status` - View character sheet
- `help` - All commands

## Character Backgrounds

1. **Pirate** - Combat focused, starts with cutlass
2. **Navy Deserter** - Pistol expert, hated by Navy
3. **Merchant** - Silver tongue, extra gold
4. **Stowaway** - Lucky and nimble

## Tips

- Talk to everyone - they're hilarious
- Drinking helps HP but makes you clumsy
- One-Legged Pete has terrible luck (easy target)
- The tavern is a safe zone - no combat
- Save your gold for better weapons

## Turn Summaries

At the end of each turn, you'll see funny gossip about what happened in Nassau, including what the other player did (in multiplayer).

## Multiplayer (Coming Soon)

```bash
# Host a game
python run_mud.py server 9999

# Join a game
python run_mud.py connect localhost:9999
```

## Demo Locations

- **Nassau Tavern** - Safe hub with quest board
- **Nassau Square** - Central area, pickpockets active
- **The Docks** - Ships and philosophical pirates
- **Secret Gambling Den** - Lose money to cheaters
- **Governor's Mansion** - High risk, high reward

Enjoy your pirating adventure! 🏴‍☠️