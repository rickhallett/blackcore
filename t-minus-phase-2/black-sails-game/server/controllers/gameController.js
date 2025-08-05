const { query, getClient } = require('../config/database');
const worldManager = require('../services/worldManager');
const gameEngine = require('../services/gameEngine');

class GameController {
  async createCharacter(req, res, next) {
    try {
      const playerId = req.user.id;
      const { name, faction, attributes } = req.body;

      // Check if player already has an active character
      const existingChar = await query(
        'SELECT id FROM characters WHERE player_id = $1 AND is_alive = true',
        [playerId]
      );

      if (existingChar.rows.length > 0) {
        return res.status(400).json({
          error: 'You already have an active character'
        });
      }

      // Validate attribute points (total should be 20 for balance)
      const totalPoints = attributes.combat + attributes.sailing + 
                         attributes.negotiation + attributes.deception;
      if (totalPoints > 20) {
        return res.status(400).json({
          error: 'Total attribute points cannot exceed 20'
        });
      }

      const client = await getClient();
      
      try {
        await client.query('BEGIN');

        // Create character
        const charResult = await client.query(
          `INSERT INTO characters 
           (player_id, name, faction, combat, sailing, negotiation, deception) 
           VALUES ($1, $2, $3, $4, $5, $6, $7) 
           RETURNING *`,
          [
            playerId, 
            name, 
            faction,
            attributes.combat,
            attributes.sailing,
            attributes.negotiation,
            attributes.deception
          ]
        );

        const character = charResult.rows[0];

        // Create initial reputation
        const factions = ['pirates', 'merchants', 'british', 'independent'];
        for (const f of factions) {
          const initialRep = f === faction ? 20 : 0;
          await client.query(
            'INSERT INTO reputation (character_id, faction, value) VALUES ($1, $2, $3)',
            [character.id, f, initialRep]
          );
        }

        // Give starting ship based on faction
        const shipTypes = {
          pirates: { name: 'The Vengeance', type: 'sloop', cannons: 8 },
          merchants: { name: 'The Prosperity', type: 'merchant', cannons: 4 },
          british: { name: 'HMS Defender', type: 'frigate', cannons: 12 },
          independent: { name: 'The Wanderer', type: 'sloop', cannons: 6 }
        };

        const shipData = shipTypes[faction];
        await client.query(
          `INSERT INTO ships 
           (character_id, name, ship_type, cannons) 
           VALUES ($1, $2, $3, $4)`,
          [character.id, shipData.name, shipData.type, shipData.cannons]
        );

        await client.query('COMMIT');

        res.status(201).json({
          message: 'Character created successfully',
          character: {
            ...character,
            ship: shipData
          }
        });
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    } catch (error) {
      next(error);
    }
  }

  async getCharacter(req, res, next) {
    try {
      const playerId = req.user.id;
      const characterId = req.params.id;

      let query_text = `
        SELECT c.*, s.*, 
               json_agg(DISTINCT r.*) as reputation,
               json_agg(DISTINCT cq.*) as active_quests
        FROM characters c
        LEFT JOIN ships s ON c.id = s.character_id
        LEFT JOIN reputation r ON c.id = r.character_id
        LEFT JOIN character_quests cq ON c.id = cq.character_id AND cq.status = 'active'
        WHERE c.player_id = $1
      `;

      const params = [playerId];

      if (characterId) {
        query_text += ' AND c.id = $2';
        params.push(characterId);
      } else {
        query_text += ' AND c.is_alive = true';
      }

      query_text += ' GROUP BY c.id, s.id ORDER BY c.created_at DESC LIMIT 1';

      const result = await query(query_text, params);

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Character not found'
        });
      }

      res.json({
        character: result.rows[0]
      });
    } catch (error) {
      next(error);
    }
  }

  async joinWorld(req, res, next) {
    try {
      const playerId = req.user.id;
      const { worldId } = req.body;

      // Get player's active character
      const charResult = await query(
        'SELECT id FROM characters WHERE player_id = $1 AND is_alive = true',
        [playerId]
      );

      if (charResult.rows.length === 0) {
        return res.status(400).json({
          error: 'You need to create a character first'
        });
      }

      const characterId = charResult.rows[0].id;
      let targetWorldId = worldId;

      // If no specific world requested, find or create one
      if (!targetWorldId) {
        const availableWorlds = await worldManager.getAvailableWorlds();
        
        if (availableWorlds.length > 0) {
          targetWorldId = availableWorlds[0].id;
        } else {
          // Create new world
          const newWorld = await worldManager.createWorld('Caribbean Adventure');
          targetWorldId = newWorld.id;
        }
      }

      // Join the world
      const result = await worldManager.joinWorld(targetWorldId, playerId, characterId);

      res.json({
        message: 'Successfully joined world',
        worldId: result.worldId
      });
    } catch (error) {
      next(error);
    }
  }

  async getWorldState(req, res, next) {
    try {
      const worldId = req.params.id;
      const playerId = req.user.id;

      // Verify player is in this world
      const charResult = await query(
        'SELECT id FROM characters WHERE player_id = $1 AND world_id = $2',
        [playerId, worldId]
      );

      if (charResult.rows.length === 0) {
        return res.status(403).json({
          error: 'You are not in this world'
        });
      }

      const worldState = await worldManager.getWorldState(worldId);

      res.json({
        world: worldState
      });
    } catch (error) {
      next(error);
    }
  }

  async getAvailableWorlds(req, res, next) {
    try {
      const worlds = await worldManager.getAvailableWorlds();

      res.json({
        worlds
      });
    } catch (error) {
      next(error);
    }
  }

  async executeAction(req, res, next) {
    try {
      const playerId = req.user.id;
      const { action, target, params } = req.body;

      const result = await gameEngine.executeAction(playerId, action, target, params);

      res.json({
        result
      });
    } catch (error) {
      next(error);
    }
  }

  async getActionHistory(req, res, next) {
    try {
      const playerId = req.user.id;
      const limit = parseInt(req.query.limit) || 20;

      const result = await query(
        `SELECT ge.* 
         FROM game_events ge
         JOIN characters c ON ge.character_id = c.id
         WHERE c.player_id = $1
         ORDER BY ge.created_at DESC
         LIMIT $2`,
        [playerId, limit]
      );

      res.json({
        history: result.rows
      });
    } catch (error) {
      next(error);
    }
  }

  async getQuests(req, res, next) {
    try {
      const playerId = req.user.id;

      // Get character
      const charResult = await query(
        'SELECT id, world_id FROM characters WHERE player_id = $1 AND is_alive = true',
        [playerId]
      );

      if (charResult.rows.length === 0) {
        return res.status(404).json({
          error: 'No active character found'
        });
      }

      const character = charResult.rows[0];

      // Get active quests
      const activeQuests = await query(
        `SELECT q.*, cq.status, cq.progress, cq.accepted_at
         FROM quests q
         JOIN character_quests cq ON q.id = cq.quest_id
         WHERE cq.character_id = $1`,
        [character.id]
      );

      // Get available quests
      const availableQuests = await query(
        `SELECT q.* 
         FROM quests q
         WHERE q.world_id = $1 
         AND q.is_active = true
         AND q.id NOT IN (
           SELECT quest_id FROM character_quests WHERE character_id = $2
         )`,
        [character.world_id, character.id]
      );

      res.json({
        active: activeQuests.rows,
        available: availableQuests.rows
      });
    } catch (error) {
      next(error);
    }
  }

  async getMarketPrices(req, res, next) {
    try {
      const playerId = req.user.id;

      // Get character's world
      const charResult = await query(
        'SELECT world_id FROM characters WHERE player_id = $1 AND is_alive = true',
        [playerId]
      );

      if (charResult.rows.length === 0) {
        return res.status(404).json({
          error: 'No active character found'
        });
      }

      const worldId = charResult.rows[0].world_id;

      // Get market prices
      const prices = await query(
        `SELECT item_name, current_price, base_price, supply, demand 
         FROM market_prices 
         WHERE world_id = $1 
         ORDER BY item_name`,
        [worldId]
      );

      res.json({
        market: prices.rows
      });
    } catch (error) {
      next(error);
    }
  }

  async getShipStatus(req, res, next) {
    try {
      const playerId = req.user.id;

      const result = await query(
        `SELECT s.* 
         FROM ships s
         JOIN characters c ON s.character_id = c.id
         WHERE c.player_id = $1 AND c.is_alive = true`,
        [playerId]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'No ship found'
        });
      }

      res.json({
        ship: result.rows[0]
      });
    } catch (error) {
      next(error);
    }
  }

  async getReputation(req, res, next) {
    try {
      const playerId = req.user.id;

      const result = await query(
        `SELECT r.faction, r.value 
         FROM reputation r
         JOIN characters c ON r.character_id = c.id
         WHERE c.player_id = $1 AND c.is_alive = true
         ORDER BY r.faction`,
        [playerId]
      );

      res.json({
        reputation: result.rows
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new GameController();