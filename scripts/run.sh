#!/bin/bash
# Quick start script for MedAgentBench Green Agent

set -e

echo "🏥 MedAgentBench Green Agent - Quick Start"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found."
    echo "Please create .env file with GOOGLE_API_KEY."
    exit 1
fi

# Check if GOOGLE_API_KEY is set
if ! grep -q "GOOGLE_API_KEY=.*[^[:space:]]" .env; then
    echo "⚠️  GOOGLE_API_KEY not set in .env file."
    echo "Please edit .env and add your Google API key."
    exit 1
fi

# Install dependencies if needed
if ! python -c "import a2a" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -e .
fi

# Load environment variables from .env file
set -a
source .env
set +a

# Start the server
echo "🚀 Starting MedAgentBench Green Agent..."
echo "Server will be available at http://localhost:9009"
echo "Press Ctrl+C to stop"
echo ""

python src/server.py --host "${GREEN_AGENT_HOST:-0.0.0.0}" --port "${GREEN_AGENT_PORT:-9009}"
