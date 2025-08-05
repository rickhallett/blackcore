const jwt = require('jsonwebtoken');
const { redis, query } = require('../config/database');

class SessionManager {
  constructor() {
    this.activeSessions = new Map();
    this.sessionTimeout = 30 * 60 * 1000; // 30 minutes
  }

  async authenticateSocket(token) {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      
      // Get player from database
      const result = await query(
        'SELECT id, username FROM players WHERE id = $1 AND status = $2',
        [decoded.userId, 'active']
      );

      if (result.rows.length === 0) {
        return null;
      }

      const player = result.rows[0];

      // Get player's active character and world
      const characterResult = await query(
        `SELECT c.*, w.id as world_id 
         FROM characters c
         JOIN worlds w ON c.world_id = w.id
         WHERE c.player_id = $1 AND c.is_alive = true AND w.status = 'active'
         ORDER BY c.created_at DESC
         LIMIT 1`,
        [player.id]
      );

      // Store session in Redis
      const sessionData = {
        playerId: player.id,
        username: player.username,
        character: characterResult.rows[0] || null,
        worldId: characterResult.rows[0]?.world_id || null,
        connectedAt: new Date().toISOString()
      };

      await redis.setex(
        `session:${player.id}`,
        this.sessionTimeout / 1000,
        JSON.stringify(sessionData)
      );

      // Store in memory for quick access
      this.activeSessions.set(player.id, sessionData);

      return sessionData;
    } catch (error) {
      console.error('Socket authentication error:', error);
      return null;
    }
  }

  async getPlayer(playerId) {
    // Check memory first
    if (this.activeSessions.has(playerId)) {
      return this.activeSessions.get(playerId);
    }

    // Check Redis
    const sessionData = await redis.get(`session:${playerId}`);
    if (sessionData) {
      const parsed = JSON.parse(sessionData);
      this.activeSessions.set(playerId, parsed);
      return parsed;
    }

    // Fallback to database
    const result = await query(
      'SELECT id, username FROM players WHERE id = $1',
      [playerId]
    );

    if (result.rows.length > 0) {
      return {
        playerId: result.rows[0].id,
        username: result.rows[0].username
      };
    }

    return null;
  }

  async updateSession(playerId, updates) {
    const session = await this.getPlayer(playerId);
    if (!session) return;

    const updatedSession = { ...session, ...updates };
    
    // Update Redis
    await redis.setex(
      `session:${playerId}`,
      this.sessionTimeout / 1000,
      JSON.stringify(updatedSession)
    );

    // Update memory
    this.activeSessions.set(playerId, updatedSession);
  }

  async handleDisconnect(playerId) {
    // Remove from active sessions
    this.activeSessions.delete(playerId);

    // Update last seen in database
    await query(
      'UPDATE players SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
      [playerId]
    );

    // Keep Redis session for reconnection
  }

  async getActivePlayers(worldId) {
    const keys = await redis.keys('session:*');
    const activePlayers = [];

    for (const key of keys) {
      const sessionData = await redis.get(key);
      if (sessionData) {
        const parsed = JSON.parse(sessionData);
        if (parsed.worldId === worldId) {
          activePlayers.push(parsed);
        }
      }
    }

    return activePlayers;
  }

  async isPlayerOnline(playerId) {
    return this.activeSessions.has(playerId) || 
           await redis.exists(`session:${playerId}`);
  }

  generateToken(userId, username) {
    return jwt.sign(
      { userId, username },
      process.env.JWT_SECRET,
      { expiresIn: process.env.JWT_EXPIRES_IN || '7d' }
    );
  }

  async createRefreshToken(userId) {
    const refreshToken = jwt.sign(
      { userId, type: 'refresh' },
      process.env.JWT_SECRET,
      { expiresIn: '30d' }
    );

    // Store refresh token in Redis
    await redis.setex(
      `refresh:${userId}`,
      30 * 24 * 60 * 60, // 30 days in seconds
      refreshToken
    );

    return refreshToken;
  }

  async validateRefreshToken(token) {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      if (decoded.type !== 'refresh') {
        return null;
      }

      // Check if token exists in Redis
      const storedToken = await redis.get(`refresh:${decoded.userId}`);
      if (storedToken !== token) {
        return null;
      }

      return decoded.userId;
    } catch (error) {
      return null;
    }
  }

  async revokeRefreshToken(userId) {
    await redis.del(`refresh:${userId}`);
  }

  // Clean up expired sessions periodically
  async cleanupSessions() {
    const keys = await redis.keys('session:*');
    
    for (const key of keys) {
      const ttl = await redis.ttl(key);
      if (ttl === -2) { // Key doesn't exist
        const playerId = parseInt(key.split(':')[1]);
        this.activeSessions.delete(playerId);
      }
    }
  }
}

module.exports = new SessionManager();

// Run cleanup every 5 minutes
setInterval(() => {
  module.exports.cleanupSessions().catch(console.error);
}, 5 * 60 * 1000);