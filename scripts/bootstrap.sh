#!/bin/bash
set -e

echo "🚀 Bootstrapping Agent Red-Teaming Framework..."

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration before running."
fi

# Start infrastructure
echo "🐳 Starting infrastructure..."
docker-compose -f docker-compose.dev.yml up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if backend directory exists
if [ -d "backend" ]; then
    echo "🔧 Setting up backend..."
    cd backend
    
    # Create virtual environment
    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi
    
    source .venv/bin/activate
    pip install -e ".[dev]"
    
    # Run migrations
    echo "📦 Running database migrations..."
    alembic upgrade head
    
    # Seed development data
    if [ "$DEV_SEED_DATA" = "true" ]; then
        echo "🌱 Seeding development data..."
        python ../scripts/seed_demo_data.py
    fi
    
    cd ..
fi

# Check if frontend directory exists
if [ -d "frontend" ]; then
    echo "🎨 Setting up frontend..."
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    
    cd ..
fi

echo "✅ Bootstrap complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Edit .env with your API keys and configuration"
echo "  2. Start backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  3. Start frontend: cd frontend && npm run dev"
echo "  4. Open http://localhost:3000"
echo ""
echo "🐳 Or run everything with Docker:"
echo "  docker-compose -f docker-compose.dev.yml up"