require('dotenv').config();
const fs = require('fs').promises;
const path = require('path');
const { pgPool } = require('../server/config/database');

async function runMigrations() {
  console.log('Running database migrations...');
  
  try {
    // Read and execute migration files
    const migrationsDir = path.join(__dirname, 'migrations');
    const files = await fs.readdir(migrationsDir);
    const sqlFiles = files.filter(f => f.endsWith('.sql')).sort();
    
    for (const file of sqlFiles) {
      console.log(`Running migration: ${file}`);
      const sql = await fs.readFile(path.join(migrationsDir, file), 'utf8');
      await pgPool.query(sql);
      console.log(`✓ ${file} completed`);
    }
    
    console.log('All migrations completed successfully!');
  } catch (error) {
    console.error('Migration error:', error);
    throw error;
  }
}

async function runSeeds() {
  console.log('Running database seeds...');
  
  try {
    // Check if we already have seed data
    const result = await pgPool.query('SELECT COUNT(*) FROM market_prices WHERE world_id = 0');
    if (result.rows[0].count > 0) {
      console.log('Seed data already exists, skipping...');
      return;
    }
    
    // Read and execute seed files
    const seedsDir = path.join(__dirname, 'seeds');
    const files = await fs.readdir(seedsDir);
    const sqlFiles = files.filter(f => f.endsWith('.sql')).sort();
    
    for (const file of sqlFiles) {
      console.log(`Running seed: ${file}`);
      const sql = await fs.readFile(path.join(seedsDir, file), 'utf8');
      await pgPool.query(sql);
      console.log(`✓ ${file} completed`);
    }
    
    console.log('All seeds completed successfully!');
  } catch (error) {
    console.error('Seed error:', error);
    throw error;
  }
}

async function setupDatabase() {
  try {
    console.log('🏴‍☠️ Black Sails Game Database Setup');
    console.log('==================================');
    
    // Test connection
    await pgPool.query('SELECT NOW()');
    console.log('✓ Database connection successful');
    
    // Run migrations
    await runMigrations();
    
    // Run seeds
    await runSeeds();
    
    console.log('\n✅ Database setup completed successfully!');
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Database setup failed:', error.message);
    process.exit(1);
  }
}

// Run setup if this file is executed directly
if (require.main === module) {
  setupDatabase();
}

module.exports = { setupDatabase, runMigrations, runSeeds };