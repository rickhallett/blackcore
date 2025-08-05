const express = require('express');
const router = express.Router();
const { body, validationResult } = require('express-validator');
const gameController = require('../controllers/gameController');
const authMiddleware = require('../middleware/authMiddleware');

// All game routes require authentication
router.use(authMiddleware);

// Validation middleware
const handleValidationErrors = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  next();
};

// Create new character
router.post('/character', [
  body('name')
    .isLength({ min: 2, max: 30 })
    .withMessage('Character name must be between 2 and 30 characters'),
  body('faction')
    .isIn(['pirates', 'merchants', 'british', 'independent'])
    .withMessage('Invalid faction'),
  body('attributes.combat').isInt({ min: 1, max: 10 }),
  body('attributes.sailing').isInt({ min: 1, max: 10 }),
  body('attributes.negotiation').isInt({ min: 1, max: 10 }),
  body('attributes.deception').isInt({ min: 1, max: 10 }),
  handleValidationErrors
], gameController.createCharacter);

// Get character info
router.get('/character/:id?', gameController.getCharacter);

// Join or create world
router.post('/world/join', gameController.joinWorld);

// Get world state
router.get('/world/:id', gameController.getWorldState);

// Get available worlds
router.get('/worlds', gameController.getAvailableWorlds);

// Execute game action
router.post('/action', [
  body('action').notEmpty().withMessage('Action is required'),
  body('target').optional(),
  body('params').optional().isObject(),
  handleValidationErrors
], gameController.executeAction);

// Get player's action history
router.get('/history', gameController.getActionHistory);

// Get current quests
router.get('/quests', gameController.getQuests);

// Get Nassau market prices
router.get('/market', gameController.getMarketPrices);

// Get player's ship status
router.get('/ship', gameController.getShipStatus);

// Get relationships/reputation
router.get('/reputation', gameController.getReputation);

module.exports = router;