#!/bin/bash
# One-command start for MedAgentBench
# Starts FHIR server + MCP server

set -e

cd "$(dirname "$0")/.."

FHIR_PORT=${FHIR_PORT:-8080}
MCP_PORT=${MCP_PORT:-8002}
CONTAINER_NAME="medagentbench-fhir"

echo "========================================="
echo "MedAgentBench - Full Stack Startup"
echo "========================================="
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down services..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    [ -n "$MCP_PID" ] && kill $MCP_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Step 1: Start FHIR server
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "✓ FHIR server already running"
else
    echo "Step 1: Starting FHIR server..."
    echo "  Pulling Docker image (this may take a few minutes)..."
    if ! docker pull jyxsu6/medagentbench:latest; then
        echo "Error: Failed to pull jyxsu6/medagentbench:latest"
        echo "  Check your internet connection or try: docker login"
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
echo "Step 2: Starting MCP server..."
export MCP_FHIR_API_BASE="http://localhost:${FHIR_PORT}/fhir/"
# Start MCP server (default: purple agent mode)
python -m mcp_skills.fastmcp.server --host 0.0.0.0 --port "$MCP_PORT" &
MCP_PID=$!
sleep 2

if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "Error: MCP server failed to start"
    cleanup
    exit 1
fi

echo "✓ MCP server ready"
echo ""
echo "========================================="
echo "Services Running"
echo "========================================="
echo "FHIR Server: http://localhost:${FHIR_PORT}/fhir/"
echo "MCP Server:  http://localhost:${MCP_PORT}"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep running
wait $MCP_PID
