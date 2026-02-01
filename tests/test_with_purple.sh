#!/bin/bash
# Quick script to test with Purple Agent

set -e

echo "============================================================"
echo "MedAgentBench - Test with Purple Agent"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if services are running
check_service() {
    local url=$1
    local name=$2
    
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $name is running"
        return 0
    else
        echo -e "${RED}❌${NC} $name is NOT running"
        return 1
    fi
}

echo "Checking services..."
echo ""

MCP_RUNNING=false
PURPLE_RUNNING=false
GREEN_RUNNING=false

# Check MCP Server (port 8002)
if check_service "http://localhost:8002/mcp" "MCP Server"; then
    MCP_RUNNING=true
else
    echo "   Start with: MCP_FHIR_API_BASE='...' python -m mcp_skills.fastmcp.server"
fi

# Check Purple Agent (port 9019)
if check_service "http://localhost:9019/.well-known/agent-card.json" "Purple Agent"; then
    PURPLE_RUNNING=true
else
    echo "   Start with: python examples/mock_purple_agent.py"
fi

# Check Green Agent (port 9009)
if check_service "http://localhost:9009/.well-known/agent-card.json" "Green Agent"; then
    GREEN_RUNNING=true
else
    echo "   Start with: python src/server.py"
fi

echo ""

# Run appropriate test based on what's running
if [ "$MCP_RUNNING" = true ] && [ "$PURPLE_RUNNING" = true ] && [ "$GREEN_RUNNING" = true ]; then
    echo -e "${GREEN}All services running!${NC}"
    echo ""
    echo "Running full integration test..."
    echo ""
    python tests/full_test.py
elif [ "$PURPLE_RUNNING" = true ] && [ "$GREEN_RUNNING" = true ]; then
    echo -e "${YELLOW}⚠️  MCP Server not running, but continuing with test...${NC}"
    echo ""
    echo "Running evaluation test..."
    echo ""
    python scripts/run_evaluation.py --task task_001
elif [ "$GREEN_RUNNING" = true ]; then
    echo -e "${YELLOW}⚠️  Purple Agent not running${NC}"
    echo ""
    echo "Running unit tests instead..."
    echo ""
    pytest tests/ -v
else
    echo -e "${RED}❌ No services running${NC}"
    echo ""
    echo "Please start at least one service:"
    echo "  1. Green Agent: python src/server.py"
    echo "  2. Purple Agent: python examples/mock_purple_agent.py"
    echo "  3. MCP Server: MCP_FHIR_API_BASE='...' python -m mcp_skills.fastmcp.server"
    exit 1
fi
