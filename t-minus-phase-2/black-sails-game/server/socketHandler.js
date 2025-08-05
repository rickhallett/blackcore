const gameEngine = require('./services/gameEngine');
const sessionManager = require('./services/sessionManager');

module.exports = (io, socket) => {
  console.log(`New connection: ${socket.id}`);

  // Handle player authentication
  socket.on('authenticate', async (data) => {
    try {
      const { token } = data;
      const player = await sessionManager.authenticateSocket(token);
      
      if (player) {
        socket.playerId = player.id;
        socket.join(`player:${player.id}`);
        
        // Join the player's current game world if they have one
        if (player.worldId) {
          socket.join(`world:${player.worldId}`);
        }
        
        socket.emit('authenticated', {
          success: true,
          player: {
            id: player.id,
            username: player.username,
            character: player.character
          }
        });
        
        console.log(`Player ${player.username} authenticated`);
      } else {
        socket.emit('authenticated', { success: false, error: 'Invalid token' });
      }
    } catch (error) {
      console.error('Authentication error:', error);
      socket.emit('authenticated', { success: false, error: 'Authentication failed' });
    }
  });

  // Handle game commands
  socket.on('gameCommand', async (data) => {
    try {
      if (!socket.playerId) {
        return socket.emit('error', { message: 'Not authenticated' });
      }

      const { command, args } = data;
      const result = await gameEngine.processCommand(socket.playerId, command, args);
      
      // Send result to player
      socket.emit('commandResult', result);
      
      // If the command affects other players, notify them
      if (result.worldUpdate) {
        socket.to(`world:${result.worldId}`).emit('worldUpdate', result.worldUpdate);
      }
    } catch (error) {
      console.error('Game command error:', error);
      socket.emit('error', { message: 'Command failed', error: error.message });
    }
  });

  // Handle chat messages
  socket.on('chatMessage', async (data) => {
    try {
      if (!socket.playerId) {
        return socket.emit('error', { message: 'Not authenticated' });
      }

      const player = await sessionManager.getPlayer(socket.playerId);
      const { message, channel = 'world' } = data;
      
      const chatData = {
        playerId: player.id,
        playerName: player.username,
        message,
        timestamp: new Date().toISOString(),
        channel
      };

      // Broadcast to appropriate channel
      if (channel === 'world' && player.worldId) {
        io.to(`world:${player.worldId}`).emit('chatMessage', chatData);
      } else if (channel === 'global') {
        io.emit('chatMessage', chatData);
      }
    } catch (error) {
      console.error('Chat error:', error);
      socket.emit('error', { message: 'Failed to send message' });
    }
  });

  // Handle player actions
  socket.on('playerAction', async (data) => {
    try {
      if (!socket.playerId) {
        return socket.emit('error', { message: 'Not authenticated' });
      }

      const { action, target, params } = data;
      const result = await gameEngine.executeAction(socket.playerId, action, target, params);
      
      socket.emit('actionResult', result);
      
      // Notify affected players
      if (result.affectedPlayers) {
        result.affectedPlayers.forEach(playerId => {
          io.to(`player:${playerId}`).emit('actionEffect', result);
        });
      }
    } catch (error) {
      console.error('Action error:', error);
      socket.emit('error', { message: 'Action failed', error: error.message });
    }
  });

  // Handle disconnection
  socket.on('disconnect', () => {
    if (socket.playerId) {
      sessionManager.handleDisconnect(socket.playerId);
      console.log(`Player ${socket.playerId} disconnected`);
    } else {
      console.log(`Socket ${socket.id} disconnected`);
    }
  });
};