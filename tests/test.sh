#!/bin/bash
# Quick test script for MedAgentBench Green Agent

set -e

echo "🧪 MedAgentBench Green Agent - Quick Test"
echo "=========================================="
echo ""

# Check if in correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Run this from MedAgentBench directory"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
if ! python -c "import pytest" 2>/dev/null; then
    echo "⚠️  Installing test dependencies..."
    pip install -e ".[test]" -q
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies OK"
fi

echo ""
echo "🧪 Running unit tests..."
echo "----------------------------------------"
pytest tests/ -v --tb=short

echo ""
echo "=========================================="
echo "✅ Unit tests complete!"
echo ""
echo "Next steps:"
echo "  1. Start servers for integration test:"
echo "     Terminal 1: python examples/mock_purple_agent.py"
echo "     Terminal 2: python src/server.py"
echo "     Terminal 3: python tests/full_test.py"
echo ""
echo "  2. See docs/TESTING.md for more test options"
echo ""
