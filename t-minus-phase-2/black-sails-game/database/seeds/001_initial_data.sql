-- Insert default market items for Nassau (these will be copied for each new world)
INSERT INTO market_prices (world_id, item_name, base_price, current_price, supply, demand) VALUES
(0, 'Rum', 10, 10, 100, 100),
(0, 'Sugar', 15, 15, 80, 120),
(0, 'Gunpowder', 50, 50, 60, 140),
(0, 'Cannon Balls', 30, 30, 70, 110),
(0, 'Food Supplies', 20, 20, 90, 100),
(0, 'Cotton', 25, 25, 110, 90),
(0, 'Tobacco', 35, 35, 95, 105),
(0, 'Medicine', 60, 60, 40, 160),
(0, 'Sailcloth', 40, 40, 75, 125),
(0, 'Rope', 15, 15, 100, 100),
(0, 'Wood Planks', 20, 20, 120, 80),
(0, 'Gold Doubloons', 100, 100, 20, 180),
(0, 'Silver Pieces', 50, 50, 50, 150),
(0, 'Jewels', 200, 200, 10, 190),
(0, 'Spices', 80, 80, 30, 170),
(0, 'Weapons', 70, 70, 55, 145),
(0, 'Maps', 150, 150, 5, 195),
(0, 'Books', 40, 40, 85, 115),
(0, 'Wine', 45, 45, 65, 135),
(0, 'Tools', 35, 35, 100, 100);

-- Note: world_id 0 is used as a template. When creating a new world, 
-- these entries should be copied with the actual world_id

-- Create a function to initialize a new world with default data
CREATE OR REPLACE FUNCTION initialize_world_data(new_world_id INTEGER)
RETURNS void AS $$
BEGIN
    -- Copy market prices template
    INSERT INTO market_prices (world_id, item_name, base_price, current_price, supply, demand)
    SELECT new_world_id, item_name, base_price, current_price, supply, demand
    FROM market_prices
    WHERE world_id = 0;
    
    -- Create NPCs for the world
    INSERT INTO npcs (world_id, name, npc_type, location, faction, disposition, state_data) VALUES
    (new_world_id, 'Eleanor Guthrie', 'merchant_leader', 'Nassau Tavern', 'merchants', 
     '{"player_relations": {}, "mood": "neutral"}', 
     '{"inventory": ["trade_contracts", "rum"], "gold": 5000}'),
    
    (new_world_id, 'Captain Hornigold', 'pirate_captain', 'Fort Nassau', 'pirates',
     '{"player_relations": {}, "mood": "cautious"}',
     '{"ship": "Royal Lion", "crew_size": 80}'),
    
    (new_world_id, 'Max', 'informant', 'Nassau Brothel', 'independent',
     '{"player_relations": {}, "mood": "opportunistic"}',
     '{"secrets_known": 3, "gold": 200}'),
    
    (new_world_id, 'Mr. Scott', 'advisor', 'Guthrie Warehouse', 'merchants',
     '{"player_relations": {}, "mood": "wise"}',
     '{"knowledge": ["trade_routes", "political_secrets"]}'),
    
    (new_world_id, 'Captain Hume', 'navy_officer', 'HMS Scarborough', 'british',
     '{"player_relations": {}, "mood": "hostile"}',
     '{"ship": "HMS Scarborough", "crew_size": 200, "cannons": 32}'),
    
    (new_world_id, 'Pastor Lambrick', 'religious_leader', 'Interior Settlement', 'independent',
     '{"player_relations": {}, "mood": "disapproving"}',
     '{"followers": 50, "influence": "medium"}'),
    
    (new_world_id, 'Idelle', 'tavern_worker', 'Nassau Tavern', 'independent',
     '{"player_relations": {}, "mood": "friendly"}',
     '{"gossip_level": "high", "gold": 50}'),
    
    (new_world_id, 'Dufresne', 'accountant', 'Nassau', 'pirates',
     '{"player_relations": {}, "mood": "nervous"}',
     '{"ledgers": true, "mathematical_skill": "high"}');
END;
$$ LANGUAGE plpgsql;

-- Create initial quests template
CREATE TABLE IF NOT EXISTS quest_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    giver_npc VARCHAR(100),
    requirements JSONB DEFAULT '{}'::jsonb,
    rewards JSONB DEFAULT '{}'::jsonb,
    quest_data JSONB NOT NULL
);

-- Insert quest templates
INSERT INTO quest_templates (name, description, giver_npc, requirements, rewards, quest_data) VALUES
('The Missing Schedule', 
 'A valuable shipping schedule has gone missing. Find it before other pirates do.',
 'Eleanor Guthrie',
 '{"min_reputation": {"merchants": 10}}',
 '{"gold": 500, "reputation": {"merchants": 10}}',
 '{"type": "fetch", "target": "shipping_schedule", "locations": ["Nassau Tavern", "Warehouse District", "Harbor"]}'),

('Hornigolds Test', 
 'Captain Hornigold wants to test your sailing abilities before considering you for his crew.',
 'Captain Hornigold',
 '{"min_sailing": 6}',
 '{"reputation": {"pirates": 15}, "crew_loyalty": 10}',
 '{"type": "skill_test", "skill": "sailing", "difficulty": 7}'),

('Information Trade',
 'Max has valuable information about Spanish gold shipments, but she wants something in return.',
 'Max',
 '{"gold": 200}',
 '{"information": "urca_route", "reputation": {"independent": 5}}',
 '{"type": "trade", "cost": 200, "item": "spanish_intel"}'),

('Scarborough Sabotage',
 'Sabotage the HMS Scarborough to prevent it from interfering with pirate operations.',
 'Captain Hornigold',
 '{"min_combat": 5, "min_deception": 6}',
 '{"gold": 1000, "reputation": {"pirates": 20, "british": -30}}',
 '{"type": "sabotage", "target": "HMS Scarborough", "methods": ["stealth", "combat", "deception"]}'),

('Merchant Protection',
 'Escort a merchant vessel safely through pirate-infested waters.',
 'Eleanor Guthrie',
 '{"min_reputation": {"merchants": 20}, "ship": true}',
 '{"gold": 750, "reputation": {"merchants": 15, "pirates": -10}}',
 '{"type": "escort", "distance": 3, "danger_level": "high"}');