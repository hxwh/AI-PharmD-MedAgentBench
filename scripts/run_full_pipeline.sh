#!/bin/bash
# Complete MedAgentBench Pipeline Runner
# Starts all services and runs evaluations

set -e

cd "$(dirname "$0")/.."

FHIR_PORT=${FHIR_PORT:-8080}
MCP_PORT=${MCP_PORT:-8002}
GREEN_PORT=${GREEN_PORT:-9009}
PURPLE_PORT=${PURPLE_PORT:-9019}
CONTAINER_NAME="medagentbench-fhir"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "MedAgentBench - Full Pipeline"
echo "========================================="
echo ""

# Check prerequisites
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "   Please create .env file with GOOGLE_API_KEY"
    exit 1
fi

if ! grep -q "GOOGLE_API_KEY=.*[^[:space:]]" .env 2>/dev/null; then
    echo -e "${RED}❌ GOOGLE_API_KEY not set in .env${NC}"
    exit 1
fi

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    [ -n "$MCP_PID" ] && kill $MCP_PID 2>/dev/null || true
    [ -n "$PURPLE_PID" ] && kill $PURPLE_PID 2>/dev/null || true
    [ -n "$GREEN_PID" ] && kill $GREEN_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Step 1: Start FHIR server
echo -e "${GREEN}Step 1: Starting FHIR server...${NC}"
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "✓ FHIR server already running"
else
    echo "  Pulling Docker image (this may take a few minutes)..."
    if ! docker pull jyxsu6/medagentbench:latest; then
        echo -e "${RED}Error: Failed to pull Docker image${NC}"
        exit 1
    fi
    docker tag jyxsu6/medagentbench:latest medagentbench
    docker run -d --name "$CONTAINER_NAME" -p ${FHIR_PORT}:8080 medagentbench
    
    echo "  Waiting for FHIR server (~1-2 min)..."
    max_attempts=120
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:${FHIR_PORT}/fhir/metadata" > /dev/null 2>&1; then
            echo "✓ FHIR server ready"
            break
        fi
        [ $((attempt % 10)) -eq 0 ] && echo "  Still initializing..."
        sleep 2
        attempt=$((attempt + 1))
    done
fi

# Step 2: Start MCP server
echo ""
echo -e "${GREEN}Step 2: Starting MCP server...${NC}"
export MCP_FHIR_API_BASE="http://localhost:${FHIR_PORT}/fhir/"
# Start MCP with green agent type for evaluation (has groundtruth access)
python -m mcp_skills.fastmcp.server --agent-type green --host 0.0.0.0 --port "$MCP_PORT" > /tmp/mcp_server.log 2>&1 &
MCP_PID=$!
sleep 3

if ! kill -0 $MCP_PID 2>/dev/null; then
    echo -e "${RED}Error: MCP server failed to start${NC}"
    cat /tmp/mcp_server.log
    cleanup
    exit 1
fi
echo "✓ MCP server ready (PID: $MCP_PID)"

# Step 3: Start Purple Agent
echo ""
echo -e "${GREEN}Step 3: Starting Purple Agent...${NC}"
(cd purple_agent/src && python server.py) > /tmp/purple_agent.log 2>&1 &
PURPLE_PID=$!
sleep 3

if ! kill -0 $PURPLE_PID 2>/dev/null; then
    echo -e "${RED}Error: Purple agent failed to start${NC}"
    cat /tmp/purple_agent.log
    cleanup
    exit 1
fi

# Wait for purple agent to be ready
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s "http://localhost:${PURPLE_PORT}/.well-known/agent-card.json" > /dev/null 2>&1; then
        echo "✓ Purple agent ready (PID: $PURPLE_PID)"
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done

# Step 4: Start Green Agent
echo ""
echo -e "${GREEN}Step 4: Starting Green Agent (Evaluator)...${NC}"
python src/server.py > /tmp/green_agent.log 2>&1 &
GREEN_PID=$!
sleep 3

if ! kill -0 $GREEN_PID 2>/dev/null; then
    echo -e "${RED}Error: Green agent failed to start${NC}"
    cat /tmp/green_agent.log
    cleanup
    exit 1
fi

# Wait for green agent to be ready
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s "http://localhost:${GREEN_PORT}/.well-known/agent-card.json" > /dev/null 2>&1; then
        echo "✓ Green agent ready (PID: $GREEN_PID)"
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done

echo ""
echo "========================================="
echo "All Services Running"
echo "========================================="
echo "FHIR Server: http://localhost:${FHIR_PORT}/fhir/"
echo "MCP Server:  http://localhost:${MCP_PORT}"
echo "Purple Agent: http://localhost:${PURPLE_PORT}"
echo "Green Agent:  http://localhost:${GREEN_PORT}"
echo ""

# Step 5: Run evaluation
echo "========================================="
echo "Step 5: Running Evaluation"
echo "========================================="
echo ""

# Check if user wants to run all tasks or specific task
if [ "$1" == "--all-tasks" ]; then
    echo "Running all tasks (task1-task10)..."
    python scripts/run_all_tasks.py
elif [ -n "$1" ]; then
    echo "Running task: $1"
    python scripts/run_evaluation.py --task "$1"
else
    echo "Running default task: task_001"
    echo ""
    echo "To run all tasks: ./scripts/run_full_pipeline.sh --all-tasks"
    echo "To run specific task: ./scripts/run_full_pipeline.sh task1"
    echo ""
    python scripts/run_evaluation.py --task task_001
fi

echo ""
echo "========================================="
echo "Evaluation Complete"
echo "========================================="
echo ""
echo "Services are still running. Press Ctrl+C to stop all services."
echo "Or run: ./scripts/cleanup_docker.sh"
echo ""

# Keep running until interrupted
wait $GREEN_PID
