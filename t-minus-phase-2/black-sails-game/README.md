# Black Sails: Nassau 1715 - A 2-Player Text Adventure Game

A multiplayer text-based adventure game inspired by the Black Sails TV series, where two players navigate the dangerous waters of piracy, politics, and profit in 1715 Nassau.

## Features

- **Persistent World**: Your actions affect the game world permanently
- **Asymmetric Gameplay**: Choose different paths - pirate, merchant, British Navy, or independent
- **Dynamic Storytelling**: LLM-powered narrative generation creates unique stories
- **Real-time Multiplayer**: Two players share the same world with real-time updates
- **Economic System**: Dynamic market prices affected by player actions
- **Faction Reputation**: Your choices affect how different groups view you
- **Quest System**: Dynamic quests based on world state and player choices
- **Ship Combat**: Naval battles and boarding actions
- **Character Development**: Improve your skills through gameplay

## Prerequisites

- Node.js (v16 or higher)
- PostgreSQL (v12 or higher)
- Redis (v6 or higher)
- An OpenAI or Anthropic API key (optional, for enhanced narrative generation)

## Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd black-sails-game
```

2. **Install dependencies**
```bash
npm install
```

3. **Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Server Configuration
PORT=3000
NODE_ENV=development

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/black_sails_game
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your_super_secret_jwt_key_change_this_in_production
JWT_EXPIRES_IN=7d

# LLM API Configuration (optional)
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Game Configuration
MAX_PLAYERS_PER_WORLD=2
TURN_DURATION_MINUTES=10
MAX_ACTIONS_PER_TURN=3
```

4. **Set up the database**

Create a PostgreSQL database:
```bash
createdb black_sails_game
```

Run database migrations:
```bash
npm run db:setup
```

5. **Start Redis**
```bash
redis-server
```

6. **Start the game server**
```bash
npm run dev  # For development with auto-reload
# or
npm start    # For production
```

7. **Access the game**

Open your browser and navigate to `http://localhost:3000`

## How to Play

### Getting Started

1. **Create an Account**: Register with a username and password
2. **Create a Character**: Choose your name, faction, and distribute skill points
3. **Join a World**: Either join an existing world or create a new one

### Factions

- **Pirates**: Live by the code, seek treasure and freedom
- **Merchants**: Control trade, accumulate wealth and influence
- **British Navy**: Enforce the law, hunt pirates
- **Independent**: Chart your own course

### Character Attributes (20 points total)

- **Combat**: Effectiveness in fights and duels
- **Sailing**: Ship handling and naval combat
- **Negotiation**: Trading and diplomacy
- **Deception**: Stealth, lies, and subterfuge

### Basic Commands

```
Movement:
  move <location>   - Move to a new location
  sail <location>   - Sail to a distant location
  look [target]     - Examine surroundings or specific target
  map              - Show the map

Interaction:
  talk <person>    - Speak with NPCs
  trade <person>   - Open trade interface
  attack <target>  - Initiate combat

Character:
  status           - View your character status
  inventory        - Check your inventory
  ship            - View ship status
  reputation      - Check faction reputations

Quests:
  quests          - List active and available quests
  accept <quest>  - Accept a new quest

System:
  help            - Show available commands
  clear           - Clear the terminal
```

### Game Locations

- **Nassau**: The pirate haven, center of trade and intrigue
- **Nassau Tavern**: Eleanor Guthrie's establishment, hub of information
- **Harbor**: Where ships dock and crews gather
- **Fort Nassau**: Military stronghold overlooking the harbor
- **Warehouse District**: Center of trade goods
- **Open Sea**: The vast Caribbean, full of opportunities and dangers

## Technical Architecture

### Server Components

- **Express.js**: REST API endpoints
- **Socket.io**: Real-time bidirectional communication
- **PostgreSQL**: Persistent game state storage
- **Redis**: Session management and caching
- **JWT**: Secure authentication

### Key Systems

1. **World Manager**: Handles world state, locations, and events
2. **Game Engine**: Processes commands and game logic
3. **Story Generator**: Creates dynamic narratives using LLM
4. **Session Manager**: Manages player connections and authentication

### Database Schema

- Players, Characters, Ships
- Worlds, Game Events, Quests
- Market Prices, NPCs, Reputation
- Messages and Chat

## Development

### Project Structure
```
black-sails-game/
├── server/               # Backend server code
│   ├── controllers/      # Request handlers
│   ├── services/         # Business logic
│   ├── routes/          # API endpoints
│   ├── middleware/      # Express middleware
│   └── config/          # Configuration files
├── client/              # Frontend code
│   └── public/          # Static files and client JS
├── database/            # Database scripts
│   ├── migrations/      # Schema migrations
│   └── seeds/          # Initial data
└── game/               # Game-specific logic
    ├── characters/     # Character system
    ├── story/         # Narrative generation
    └── world/         # World management
```

### Adding New Features

1. **New Commands**: Add to `gameEngine.js` in the `initializeCommands()` method
2. **New Locations**: Add to `worldManager.js` in the `locations` object
3. **New NPCs**: Add to the seed data in `database/seeds/`
4. **New Quests**: Add quest templates to the database

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env
   - Verify database exists: `psql -l`

2. **Redis connection errors**
   - Ensure Redis is running: `redis-cli ping`
   - Check REDIS_URL in .env

3. **Cannot create character**
   - Ensure total attribute points don't exceed 20
   - Check that player doesn't already have an active character

4. **No narrative generation**
   - LLM API key is optional
   - Game will use fallback narratives if no API key is provided

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Acknowledgments

- Inspired by the Black Sails TV series
- Built as a demonstration of multiplayer game architecture
- Uses various open-source libraries and frameworks

## Future Enhancements

- [ ] Turn-based combat system
- [ ] More complex ship mechanics
- [ ] Trading and economy expansion
- [ ] Additional story content
- [ ] Mobile-responsive UI
- [ ] Voice command support
- [ ] Save/load game states
- [ ] Spectator mode