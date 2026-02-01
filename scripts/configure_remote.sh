#!/bin/bash
# Configure MedAgentBench for remote access

set -e

echo "🌐 MedAgentBench Remote Configuration"
echo "===================================="

# Use hardcoded server IP
SERVER_IP="66.179.241.197"
echo "Using server IP: $SERVER_IP"

# Backup original .env
if [ -f .env ]; then
    cp .env .env.backup
    echo "✅ Backed up .env to .env.backup"
fi

# Update .env file
cat > .env << EOF
# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# MCP Server Configuration
FHIR_MCP_SERVER_URL=http://localhost:8002
FHIR_SERVER_BASE_URL=http://localhost:8080/fhir

# Green Agent Configuration (Evaluator)
GREEN_AGENT_HOST=0.0.0.0
GREEN_AGENT_PORT=9009
GREEN_AGENT_CARD_URL=http://$SERVER_IP:9009/

# Purple Agent Configuration (Test Subject - for mock agent)
PURPLE_AGENT_HOST=0.0.0.0
PURPLE_AGENT_PORT=9019
PURPLE_AGENT_CARD_URL=http://$SERVER_IP:9019/

# Task Configuration
MAX_ROUNDS=10
TASK_TIMEOUT=300
EOF

echo "✅ Updated .env with remote URLs:"
echo "   Green Agent: http://$SERVER_IP:9009/"
echo "   Purple Agent: http://$SERVER_IP:9019/"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env and add your GOOGLE_API_KEY"
echo "2. Run: ./scripts/run.sh (for green agent)"
echo "3. Run: python examples/mock_purple_agent.py (for purple agent)"
echo "4. Test: curl http://$SERVER_IP:9009/.well-known/agent-card.json"
echo ""
echo "🎉 Configuration complete!"