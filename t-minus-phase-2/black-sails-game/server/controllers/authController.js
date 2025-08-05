const bcrypt = require('bcrypt');
const { query } = require('../config/database');
const sessionManager = require('../services/sessionManager');

class AuthController {
  async register(req, res, next) {
    try {
      const { username, password, email } = req.body;

      // Check if user already exists
      const existingUser = await query(
        'SELECT id FROM players WHERE username = $1 OR email = $2',
        [username, email]
      );

      if (existingUser.rows.length > 0) {
        return res.status(400).json({
          error: 'Username or email already exists'
        });
      }

      // Hash password
      const saltRounds = 10;
      const passwordHash = await bcrypt.hash(password, saltRounds);

      // Create new player
      const result = await query(
        `INSERT INTO players (username, email, password_hash) 
         VALUES ($1, $2, $3) 
         RETURNING id, username, email`,
        [username, email, passwordHash]
      );

      const player = result.rows[0];

      // Generate tokens
      const accessToken = sessionManager.generateToken(player.id, player.username);
      const refreshToken = await sessionManager.createRefreshToken(player.id);

      res.status(201).json({
        message: 'Registration successful',
        player: {
          id: player.id,
          username: player.username,
          email: player.email
        },
        tokens: {
          access: accessToken,
          refresh: refreshToken
        }
      });
    } catch (error) {
      next(error);
    }
  }

  async login(req, res, next) {
    try {
      const { username, password } = req.body;

      // Get player by username
      const result = await query(
        'SELECT * FROM players WHERE username = $1 AND status = $2',
        [username, 'active']
      );

      if (result.rows.length === 0) {
        return res.status(401).json({
          error: 'Invalid credentials'
        });
      }

      const player = result.rows[0];

      // Verify password
      const validPassword = await bcrypt.compare(password, player.password_hash);
      if (!validPassword) {
        return res.status(401).json({
          error: 'Invalid credentials'
        });
      }

      // Update last login
      await query(
        'UPDATE players SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
        [player.id]
      );

      // Generate tokens
      const accessToken = sessionManager.generateToken(player.id, player.username);
      const refreshToken = await sessionManager.createRefreshToken(player.id);

      // Get player's active character if any
      const characterResult = await query(
        `SELECT c.*, w.name as world_name 
         FROM characters c
         LEFT JOIN worlds w ON c.world_id = w.id
         WHERE c.player_id = $1 AND c.is_alive = true
         ORDER BY c.created_at DESC
         LIMIT 1`,
        [player.id]
      );

      res.json({
        message: 'Login successful',
        player: {
          id: player.id,
          username: player.username,
          email: player.email,
          character: characterResult.rows[0] || null
        },
        tokens: {
          access: accessToken,
          refresh: refreshToken
        }
      });
    } catch (error) {
      next(error);
    }
  }

  async refreshToken(req, res, next) {
    try {
      const { refreshToken } = req.body;

      if (!refreshToken) {
        return res.status(400).json({
          error: 'Refresh token required'
        });
      }

      // Validate refresh token
      const userId = await sessionManager.validateRefreshToken(refreshToken);
      if (!userId) {
        return res.status(401).json({
          error: 'Invalid refresh token'
        });
      }

      // Get player info
      const result = await query(
        'SELECT id, username FROM players WHERE id = $1 AND status = $2',
        [userId, 'active']
      );

      if (result.rows.length === 0) {
        return res.status(401).json({
          error: 'User not found or inactive'
        });
      }

      const player = result.rows[0];

      // Generate new access token
      const accessToken = sessionManager.generateToken(player.id, player.username);

      res.json({
        accessToken
      });
    } catch (error) {
      next(error);
    }
  }

  async logout(req, res, next) {
    try {
      const userId = req.user.id;

      // Revoke refresh token
      await sessionManager.revokeRefreshToken(userId);

      res.json({
        message: 'Logout successful'
      });
    } catch (error) {
      next(error);
    }
  }

  async getCurrentUser(req, res, next) {
    try {
      const userId = req.user.id;

      // Get player info
      const playerResult = await query(
        'SELECT id, username, email, created_at, last_login FROM players WHERE id = $1',
        [userId]
      );

      if (playerResult.rows.length === 0) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      const player = playerResult.rows[0];

      // Get active character
      const characterResult = await query(
        `SELECT c.*, w.name as world_name, w.status as world_status,
         s.name as ship_name, s.ship_type
         FROM characters c
         LEFT JOIN worlds w ON c.world_id = w.id
         LEFT JOIN ships s ON c.id = s.character_id
         WHERE c.player_id = $1 AND c.is_alive = true
         ORDER BY c.created_at DESC
         LIMIT 1`,
        [userId]
      );

      // Get reputation
      let reputation = [];
      if (characterResult.rows.length > 0) {
        const repResult = await query(
          'SELECT faction, value FROM reputation WHERE character_id = $1',
          [characterResult.rows[0].id]
        );
        reputation = repResult.rows;
      }

      res.json({
        player: {
          ...player,
          character: characterResult.rows[0] || null,
          reputation
        }
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new AuthController();