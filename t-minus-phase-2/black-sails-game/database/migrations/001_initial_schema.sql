-- Create enum types
CREATE TYPE faction_type AS ENUM ('pirates', 'merchants', 'british', 'independent');
CREATE TYPE player_status AS ENUM ('active', 'inactive', 'banned');
CREATE TYPE world_status AS ENUM ('waiting', 'active', 'completed');
CREATE TYPE action_type AS ENUM ('movement', 'combat', 'trade', 'dialogue', 'quest', 'special');

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    username VARCHAR(30) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status player_status DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Worlds table (game instances)
CREATE TABLE IF NOT EXISTS worlds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status world_status DEFAULT 'waiting',
    max_players INTEGER DEFAULT 2,
    current_players INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    turn_number INTEGER DEFAULT 0,
    world_state JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Characters table
CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
    world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    faction faction_type NOT NULL,
    
    -- Attributes
    combat INTEGER DEFAULT 5 CHECK (combat >= 1 AND combat <= 10),
    sailing INTEGER DEFAULT 5 CHECK (sailing >= 1 AND sailing <= 10),
    negotiation INTEGER DEFAULT 5 CHECK (negotiation >= 1 AND negotiation <= 10),
    deception INTEGER DEFAULT 5 CHECK (deception >= 1 AND deception <= 10),
    
    -- Resources
    gold INTEGER DEFAULT 100,
    crew_loyalty INTEGER DEFAULT 50 CHECK (crew_loyalty >= 0 AND crew_loyalty <= 100),
    
    -- Status
    health INTEGER DEFAULT 100 CHECK (health >= 0 AND health <= 100),
    location VARCHAR(100) DEFAULT 'Nassau',
    is_alive BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    character_data JSONB DEFAULT '{}'::jsonb,
    
    UNIQUE(player_id, world_id)
);

-- Ships table
CREATE TABLE IF NOT EXISTS ships (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    ship_type VARCHAR(50) DEFAULT 'sloop',
    hull_health INTEGER DEFAULT 100 CHECK (hull_health >= 0 AND hull_health <= 100),
    sail_health INTEGER DEFAULT 100 CHECK (sail_health >= 0 AND sail_health <= 100),
    cannons INTEGER DEFAULT 8,
    cargo_capacity INTEGER DEFAULT 100,
    current_cargo INTEGER DEFAULT 0,
    speed INTEGER DEFAULT 5,
    ship_data JSONB DEFAULT '{}'::jsonb
);

-- Reputation table
CREATE TABLE IF NOT EXISTS reputation (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    faction faction_type NOT NULL,
    value INTEGER DEFAULT 0 CHECK (value >= -100 AND value <= 100),
    UNIQUE(character_id, faction)
);

-- Actions/Events log
CREATE TABLE IF NOT EXISTS game_events (
    id SERIAL PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    action_type action_type NOT NULL,
    action_data JSONB NOT NULL,
    result_data JSONB,
    turn_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quests table
CREATE TABLE IF NOT EXISTS quests (
    id SERIAL PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    giver_npc VARCHAR(100),
    quest_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Character quests junction table
CREATE TABLE IF NOT EXISTS character_quests (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    quest_id INTEGER REFERENCES quests(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'active',
    progress JSONB DEFAULT '{}'::jsonb,
    accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(character_id, quest_id)
);

-- Messages/Chat table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    sender_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    recipient_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    channel VARCHAR(50) DEFAULT 'world',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market prices table (Nassau economy)
CREATE TABLE IF NOT EXISTS market_prices (
    id SERIAL PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    item_name VARCHAR(100) NOT NULL,
    base_price INTEGER NOT NULL,
    current_price INTEGER NOT NULL,
    supply INTEGER DEFAULT 100,
    demand INTEGER DEFAULT 100,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(world_id, item_name)
);

-- NPC state table
CREATE TABLE IF NOT EXISTS npcs (
    id SERIAL PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    npc_type VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    faction faction_type,
    disposition JSONB DEFAULT '{}'::jsonb,
    state_data JSONB DEFAULT '{}'::jsonb,
    is_alive BOOLEAN DEFAULT true
);

-- Create indexes for performance
CREATE INDEX idx_players_username ON players(username);
CREATE INDEX idx_characters_player_world ON characters(player_id, world_id);
CREATE INDEX idx_game_events_world_turn ON game_events(world_id, turn_number);
CREATE INDEX idx_messages_world_created ON messages(world_id, created_at);
CREATE INDEX idx_reputation_character ON reputation(character_id);

-- Create update timestamp function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add update timestamp trigger to market_prices
CREATE TRIGGER update_market_prices_timestamp
BEFORE UPDATE ON market_prices
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();