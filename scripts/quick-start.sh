#!/bin/bash
# Quick start script to fix common issues and start testing

set -e

echo "🔧 MedAgentBench - Quick Fix & Start"
echo "====================================="
echo ""

cd /root/streamlit/Agents/MedAgentBench

# 1. Install all dependencies
echo "📦 Step 1: Installing dependencies..."
pip install -e ".[test]" fastapi -q
echo "✅ Dependencies installed"
echo ""

# 2. Check environment
echo "🔍 Step 2: Checking environment..."
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo "   Please create .env file and add GOOGLE_API_KEY"
    echo ""
    echo "   Then run: ./scripts/quick-start.sh"
    exit 0
fi

if ! grep -q "GOOGLE_API_KEY=.*[^[:space:]]" .env 2>/dev/null; then
    echo "⚠️  GOOGLE_API_KEY not set in .env"
    echo "   Please edit .env and add your Google API key"
    echo ""
    echo "   Get one at: https://ai.google.dev/gemini-api/docs/api-key"
    exit 0
fi

echo "✅ Environment configured"
echo ""

# 3. Run quick tests
echo "🧪 Step 3: Running unit tests..."
pytest tests/ -v --tb=short -q
echo "✅ Unit tests passed"
echo ""

# 4. Instructions for full test
echo "✅ Setup complete!"
echo ""
echo "====================================="
echo "Next: Run Full Integration Test"
echo "====================================="
echo ""
echo "Open 3 terminals and run:"
echo ""
echo "  Terminal 1: python examples/mock_purple_agent.py"
echo "  Terminal 2: python src/server.py"
echo "  Terminal 3: python examples/full_test.py"
echo ""
echo "Or test just the green agent:"
echo "  python src/server.py"
echo ""
