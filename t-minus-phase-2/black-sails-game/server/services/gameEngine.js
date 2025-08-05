const { query, getClient } = require('../config/database');
const worldManager = require('./worldManager');
const storyGenerator = require('./storyGenerator');

class GameEngine {
  constructor() {
    this.commands = new Map();
    this.initializeCommands();
  }

  initializeCommands() {
    // Movement commands
    this.commands.set('move', this.handleMove.bind(this));
    this.commands.set('sail', this.handleSail.bind(this));
    
    // Interaction commands
    this.commands.set('talk', this.handleTalk.bind(this));
    this.commands.set('trade', this.handleTrade.bind(this));
    this.commands.set('attack', this.handleAttack.bind(this));
    
    // Information commands
    this.commands.set('look', this.handleLook.bind(this));
    this.commands.set('inventory', this.handleInventory.bind(this));
    this.commands.set('status', this.handleStatus.bind(this));
    this.commands.set('map', this.handleMap.bind(this));
    
    // Quest commands
    this.commands.set('quests', this.handleQuests.bind(this));
    this.commands.set('accept', this.handleAcceptQuest.bind(this));
  }

  async processCommand(playerId, command, args) {
    try {
      // Get player's character
      const character = await this.getPlayerCharacter(playerId);
      if (!character) {
        return {
          success: false,
          message: 'You need to create a character first.'
        };
      }

      // Check if it's player's turn
      const canAct = await this.canPlayerAct(character.world_id, playerId);
      if (!canAct) {
        return {
          success: false,
          message: 'It\'s not your turn yet.'
        };
      }

      // Process the command
      const handler = this.commands.get(command.toLowerCase());
      if (!handler) {
        return {
          success: false,
          message: `Unknown command: ${command}. Type 'help' for available commands.`
        };
      }

      const result = await handler(character, args);
      
      // Log the action
      await this.logGameEvent(character.world_id, character.id, command, args, result);
      
      // Generate narrative response using LLM
      if (result.success) {
        result.narrative = await storyGenerator.generateNarrative(command, args, result, character);
      }

      return result;
    } catch (error) {
      console.error('Command processing error:', error);
      return {
        success: false,
        message: 'An error occurred while processing your command.'
      };
    }
  }

  async getPlayerCharacter(playerId) {
    const result = await query(
      `SELECT c.*, s.* 
       FROM characters c
       LEFT JOIN ships s ON c.id = s.character_id
       WHERE c.player_id = $1 AND c.is_alive = true
       ORDER BY c.created_at DESC
       LIMIT 1`,
      [playerId]
    );
    return result.rows[0];
  }

  async canPlayerAct(worldId, playerId) {
    // For now, always return true. In a full implementation,
    // this would check turn order and action limits
    return true;
  }

  async logGameEvent(worldId, characterId, action, args, result) {
    await query(
      `INSERT INTO game_events (world_id, character_id, action_type, action_data, result_data, turn_number)
       VALUES ($1, $2, $3, $4, $5, (SELECT turn_number FROM worlds WHERE id = $1))`,
      [worldId, characterId, this.getActionType(action), { command: action, args }, result]
    );
  }

  getActionType(command) {
    const actionTypes = {
      move: 'movement',
      sail: 'movement',
      talk: 'dialogue',
      trade: 'trade',
      attack: 'combat',
      look: 'special',
      inventory: 'special',
      status: 'special',
      map: 'special',
      quests: 'quest',
      accept: 'quest'
    };
    return actionTypes[command] || 'special';
  }

  // Command handlers
  async handleMove(character, args) {
    const destination = args.join(' ');
    if (!destination) {
      return {
        success: false,
        message: 'Where do you want to go? Example: move Nassau Tavern'
      };
    }

    // Check if destination is valid for current location
    const validDestinations = await worldManager.getValidDestinations(character.location);
    if (!validDestinations.includes(destination)) {
      return {
        success: false,
        message: `You can't go to ${destination} from here. Valid destinations: ${validDestinations.join(', ')}`
      };
    }

    // Update character location
    await query(
      'UPDATE characters SET location = $1 WHERE id = $2',
      [destination, character.id]
    );

    return {
      success: true,
      message: `You move to ${destination}.`,
      location: destination,
      worldUpdate: {
        type: 'player_movement',
        playerId: character.player_id,
        from: character.location,
        to: destination
      }
    };
  }

  async handleSail(character, args) {
    if (!character.ship_id) {
      return {
        success: false,
        message: 'You need a ship to sail!'
      };
    }

    const destination = args.join(' ');
    // Sailing logic would go here
    return {
      success: true,
      message: `You set sail for ${destination}. The journey will take time...`
    };
  }

  async handleTalk(character, args) {
    const npcName = args.join(' ');
    
    // Get NPCs at current location
    const npcs = await query(
      'SELECT * FROM npcs WHERE world_id = $1 AND location = $2 AND is_alive = true',
      [character.world_id, character.location]
    );

    const npc = npcs.rows.find(n => n.name.toLowerCase().includes(npcName.toLowerCase()));
    if (!npc) {
      return {
        success: false,
        message: `There's no one named "${npcName}" here.`
      };
    }

    // Generate dialogue using story generator
    const dialogue = await storyGenerator.generateNPCDialogue(npc, character);

    return {
      success: true,
      message: `${npc.name}: "${dialogue}"`,
      npc: npc.name
    };
  }

  async handleTrade(character, args) {
    // Trade logic would go here
    return {
      success: true,
      message: 'Trade interface opened...'
    };
  }

  async handleAttack(character, args) {
    const target = args.join(' ');
    
    // Combat logic would go here
    return {
      success: true,
      message: `You prepare to attack ${target}...`,
      combatInitiated: true
    };
  }

  async handleLook(character, args) {
    const target = args.join(' ');
    
    if (!target) {
      // Describe current location
      const description = await worldManager.getLocationDescription(character.world_id, character.location);
      const npcs = await query(
        'SELECT name, npc_type FROM npcs WHERE world_id = $1 AND location = $2 AND is_alive = true',
        [character.world_id, character.location]
      );

      return {
        success: true,
        message: description,
        npcs: npcs.rows,
        location: character.location
      };
    }

    // Look at specific target
    return {
      success: true,
      message: `You examine ${target} closely...`
    };
  }

  async handleInventory(character, args) {
    return {
      success: true,
      message: 'Your inventory:',
      inventory: character.character_data.inventory || [],
      gold: character.gold
    };
  }

  async handleStatus(character, args) {
    const reputation = await query(
      'SELECT faction, value FROM reputation WHERE character_id = $1',
      [character.id]
    );

    return {
      success: true,
      message: 'Character Status:',
      status: {
        name: character.name,
        faction: character.faction,
        health: character.health,
        attributes: {
          combat: character.combat,
          sailing: character.sailing,
          negotiation: character.negotiation,
          deception: character.deception
        },
        resources: {
          gold: character.gold,
          crew_loyalty: character.crew_loyalty
        },
        reputation: reputation.rows
      }
    };
  }

  async handleMap(character, args) {
    return {
      success: true,
      message: 'World Map:',
      currentLocation: character.location,
      knownLocations: await worldManager.getKnownLocations(character.id)
    };
  }

  async handleQuests(character, args) {
    const quests = await query(
      `SELECT q.*, cq.status, cq.progress 
       FROM quests q
       JOIN character_quests cq ON q.id = cq.quest_id
       WHERE cq.character_id = $1`,
      [character.id]
    );

    return {
      success: true,
      message: 'Your quests:',
      quests: quests.rows
    };
  }

  async handleAcceptQuest(character, args) {
    const questName = args.join(' ');
    
    // Quest acceptance logic would go here
    return {
      success: true,
      message: `Quest "${questName}" accepted!`
    };
  }

  async executeAction(playerId, action, target, params) {
    // This method is called by the socket handler for more complex actions
    const character = await this.getPlayerCharacter(playerId);
    if (!character) {
      throw new Error('Character not found');
    }

    // Process the action based on type
    switch (action) {
      case 'ship_battle':
        return await this.handleShipBattle(character, target, params);
      case 'duel':
        return await this.handleDuel(character, target, params);
      case 'negotiate':
        return await this.handleNegotiation(character, target, params);
      default:
        throw new Error(`Unknown action: ${action}`);
    }
  }

  async handleShipBattle(character, targetShipId, params) {
    // Ship combat logic
    return {
      success: true,
      message: 'Ship battle initiated!',
      battleId: Math.random().toString(36).substr(2, 9)
    };
  }

  async handleDuel(character, targetCharacterId, params) {
    // Duel logic
    return {
      success: true,
      message: 'Duel initiated!',
      duelId: Math.random().toString(36).substr(2, 9)
    };
  }

  async handleNegotiation(character, target, params) {
    // Negotiation logic
    return {
      success: true,
      message: 'Negotiation started...',
      negotiationId: Math.random().toString(36).substr(2, 9)
    };
  }
}

module.exports = new GameEngine();