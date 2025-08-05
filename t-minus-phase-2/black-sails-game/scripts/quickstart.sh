#!/bin/bash

echo "🏴‍☠️ Black Sails Game - Quick Start Setup"
echo "========================================"

# Check for required tools
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Visit https://nodejs.org/"; exit 1; }
command -v psql >/dev/null 2>&1 || { echo "❌ PostgreSQL is required but not installed. Visit https://www.postgresql.org/"; exit 1; }
command -v redis-cli >/dev/null 2>&1 || { echo "❌ Redis is required but not installed. Visit https://redis.io/"; exit 1; }

echo "✓ All required tools found"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Setup environment
if [ ! -f .env ]; then
    echo "🔧 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
    echo "   Especially set your DATABASE_URL and JWT_SECRET"
    read -p "Press enter when you've updated .env..."
fi

# Create database
echo "🗄️  Creating database..."
createdb black_sails_game 2>/dev/null || echo "Database may already exist"

# Run migrations
echo "🔨 Running database migrations..."
npm run db:setup

# Check Redis
echo "🔍 Checking Redis..."
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  Redis is not running. Please start it with: redis-server"
else
    echo "✓ Redis is running"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the game:"
echo "1. Make sure Redis is running: redis-server"
echo "2. Start the game server: npm run dev"
echo "3. Open http://localhost:3000 in your browser"
echo ""
echo "⚓ Fair winds and following seas!"