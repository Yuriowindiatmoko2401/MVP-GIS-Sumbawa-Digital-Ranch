#!/bin/bash

# Sumbawa Digital Ranch MVP - Backend Runner Script
# Starts the FastAPI server with proper environment

echo "🚀 Starting Sumbawa Digital Ranch Backend..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please create one based on .env.example"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📚 Installing/updating dependencies..."
    pip install -r requirements.txt
fi

# Set environment variables
export ENVIRONMENT=${ENVIRONMENT:-development}
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🌍 Environment: $ENVIRONMENT"
echo "🔗 Starting FastAPI server on http://0.0.0.0:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🔌 WebSocket endpoint: ws://localhost:8000/ws"

# Start the FastAPI server
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info \
    --access-log \
    --use-colors