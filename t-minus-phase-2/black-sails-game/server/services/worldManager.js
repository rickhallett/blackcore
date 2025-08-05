const { query, getClient } = require('../config/database');

class WorldManager {
  constructor() {
    this.locations = {
      'Nassau': {
        description: 'The bustling pirate haven of Nassau. Ships of all flags crowd the harbor while merchants, pirates, and whores conduct their business in the streets.',
        connections: ['Nassau Tavern', 'Harbor', 'Fort Nassau', 'Warehouse District'],
        type: 'town'
      },
      'Nassau Tavern': {
        description: 'Eleanor Guthrie\'s tavern - the heart of Nassau\'s black market trade. Pirates negotiate deals while whores ply their trade upstairs.',
        connections: ['Nassau', 'Nassau Brothel'],
        type: 'building'
      },
      'Harbor': {
        description: 'Nassau\'s harbor is filled with ships of every size and flag. The smell of tar and salt fills the air.',
        connections: ['Nassau', 'Open Sea'],
        type: 'harbor'
      },
      'Fort Nassau': {
        description: 'The fort overlooks the harbor, its cannons a reminder of the power that controls Nassau.',
        connections: ['Nassau'],
        type: 'fort'
      },
      'Warehouse District': {
        description: 'Warehouses line the streets, filled with goods both legal and illegal. Guards patrol regularly.',
        connections: ['Nassau', 'Guthrie Warehouse'],
        type: 'district'
      },
      'Nassau Brothel': {
        description: 'Max\'s domain. Information flows as freely as the rum here.',
        connections: ['Nassau Tavern'],
        type: 'building'
      },
      'Guthrie Warehouse': {
        description: 'The center of the Guthrie trading empire. Heavily guarded and full of valuable goods.',
        connections: ['Warehouse District'],
        type: 'building'
      },
      'Open Sea': {
        description: 'The Caribbean stretches endlessly before you. Merchant ships and warships dot the horizon.',
        connections: ['Harbor', 'Shipping Lanes', 'Hidden Cove'],
        type: 'sea'
      },
      'Shipping Lanes': {
        description: 'Major trade routes where merchant vessels are common prey for pirates.',
        connections: ['Open Sea'],
        type: 'sea'
      },
      'Hidden Cove': {
        description: 'A secluded cove perfect for hiding from pursuers or burying treasure.',
        connections: ['Open Sea'],
        type: 'sea'
      }
    };
  }

  async createWorld(name, maxPlayers = 2) {
    const client = await getClient();
    
    try {
      await client.query('BEGIN');

      // Create the world
      const worldResult = await client.query(
        `INSERT INTO worlds (name, max_players, world_state) 
         VALUES ($1, $2, $3) 
         RETURNING *`,
        [name, maxPlayers, JSON.stringify({ 
          turn: 0,
          phase: 'waiting',
          weather: 'clear',
          events: []
        })]
      );

      const world = worldResult.rows[0];

      // Initialize world data (market prices, NPCs, etc.)
      await client.query('SELECT initialize_world_data($1)', [world.id]);

      await client.query('COMMIT');

      return world;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async joinWorld(worldId, playerId, characterId) {
    const client = await getClient();

    try {
      await client.query('BEGIN');

      // Check if world has space
      const worldResult = await client.query(
        'SELECT * FROM worlds WHERE id = $1 FOR UPDATE',
        [worldId]
      );

      const world = worldResult.rows[0];
      if (!world) {
        throw new Error('World not found');
      }

      if (world.current_players >= world.max_players) {
        throw new Error('World is full');
      }

      // Update character's world
      await client.query(
        'UPDATE characters SET world_id = $1 WHERE id = $2',
        [worldId, characterId]
      );

      // Update world player count
      await client.query(
        `UPDATE worlds 
         SET current_players = current_players + 1,
             status = CASE 
               WHEN current_players + 1 >= max_players THEN 'active'
               ELSE status
             END,
             started_at = CASE
               WHEN current_players + 1 >= max_players THEN CURRENT_TIMESTAMP
               ELSE started_at
             END
         WHERE id = $1`,
        [worldId]
      );

      await client.query('COMMIT');

      return { success: true, worldId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getValidDestinations(currentLocation) {
    return this.locations[currentLocation]?.connections || [];
  }

  async getLocationDescription(worldId, location) {
    const baseDescription = this.locations[location]?.description || 'An unknown location.';
    
    // Add dynamic elements based on world state
    const events = await query(
      `SELECT * FROM game_events 
       WHERE world_id = $1 
       AND action_data->>'location' = $2 
       ORDER BY created_at DESC 
       LIMIT 5`,
      [worldId, location]
    );

    let dynamicDescription = baseDescription;
    
    if (events.rows.length > 0) {
      // Add recent events to description
      dynamicDescription += '\n\nRecent activity here includes rumors of ';
      dynamicDescription += events.rows.map(e => e.action_data.summary).join(', ');
    }

    return dynamicDescription;
  }

  async getKnownLocations(characterId) {
    // In a full implementation, this would track discovered locations
    return Object.keys(this.locations);
  }

  async advanceTurn(worldId) {
    const client = await getClient();

    try {
      await client.query('BEGIN');

      // Update turn number
      await client.query(
        'UPDATE worlds SET turn_number = turn_number + 1 WHERE id = $1',
        [worldId]
      );

      // Process world events (market changes, NPC movements, etc.)
      await this.processWorldEvents(client, worldId);

      // Check for end conditions
      await this.checkEndConditions(client, worldId);

      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async processWorldEvents(client, worldId) {
    // Update market prices based on supply/demand
    await client.query(
      `UPDATE market_prices 
       SET current_price = GREATEST(1, 
         base_price * (1 + (demand - supply) * 0.01)
       )::INTEGER
       WHERE world_id = $1`,
      [worldId]
    );

    // Random events could be added here
    const randomEvent = Math.random();
    if (randomEvent < 0.1) { // 10% chance of special event
      await this.createRandomEvent(client, worldId);
    }
  }

  async createRandomEvent(client, worldId) {
    const events = [
      {
        type: 'storm',
        description: 'A storm is brewing in the Caribbean!',
        effects: { sailing_difficulty: 2 }
      },
      {
        type: 'navy_patrol',
        description: 'British Navy ships have been spotted patrolling the shipping lanes!',
        effects: { navy_presence: 'high' }
      },
      {
        type: 'treasure_rumor',
        description: 'Rumors of buried treasure spread through Nassau!',
        effects: { new_quest: true }
      }
    ];

    const event = events[Math.floor(Math.random() * events.length)];
    
    await client.query(
      `UPDATE worlds 
       SET world_state = jsonb_set(world_state, '{events}', 
         (world_state->'events')::jsonb || $1::jsonb
       )
       WHERE id = $2`,
      [JSON.stringify([event]), worldId]
    );
  }

  async checkEndConditions(client, worldId) {
    // Check various victory conditions
    const characters = await client.query(
      'SELECT * FROM characters WHERE world_id = $1 AND is_alive = true',
      [worldId]
    );

    // Example: Check if one player has accumulated enough gold
    const wealthyCharacter = characters.rows.find(c => c.gold >= 10000);
    if (wealthyCharacter) {
      await client.query(
        `UPDATE worlds 
         SET status = 'completed', 
             ended_at = CURRENT_TIMESTAMP,
             metadata = jsonb_set(metadata, '{winner}', $1::jsonb)
         WHERE id = $2`,
        [JSON.stringify({ 
          characterId: wealthyCharacter.id, 
          condition: 'wealth',
          gold: wealthyCharacter.gold 
        }), worldId]
      );
    }

    // Add other victory conditions (control of Nassau, Spanish treasure, etc.)
  }

  async getWorldState(worldId) {
    const world = await query(
      'SELECT * FROM worlds WHERE id = $1',
      [worldId]
    );

    if (world.rows.length === 0) {
      return null;
    }

    const characters = await query(
      `SELECT c.id, c.name, c.faction, c.location, p.username 
       FROM characters c
       JOIN players p ON c.player_id = p.id
       WHERE c.world_id = $1 AND c.is_alive = true`,
      [worldId]
    );

    const marketPrices = await query(
      'SELECT item_name, current_price FROM market_prices WHERE world_id = $1',
      [worldId]
    );

    return {
      world: world.rows[0],
      characters: characters.rows,
      market: marketPrices.rows,
      locations: this.locations
    };
  }

  async getAvailableWorlds() {
    const worlds = await query(
      `SELECT * FROM worlds 
       WHERE status = 'waiting' 
       ORDER BY created_at DESC`
    );

    return worlds.rows;
  }
}

module.exports = new WorldManager();