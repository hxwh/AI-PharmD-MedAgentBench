#!/bin/bash
# Start the MCP server for FHIR tools

set -e

cd "$(dirname "$0")/.."

FHIR_PORT=${FHIR_PORT:-8080}
MCP_PORT=${MCP_PORT:-8002}

# Set FHIR API base URL
export MCP_FHIR_API_BASE="http://localhost:${FHIR_PORT}/fhir/"

echo "Starting MedAgentBench MCP Server..."
echo "  FHIR API: $MCP_FHIR_API_BASE"
echo "  MCP Port: $MCP_PORT"
echo ""

# Check if FHIR server is accessible
if ! curl -s "http://localhost:${FHIR_PORT}/fhir/metadata" > /dev/null 2>&1; then
    echo "Warning: FHIR server not detected at http://localhost:${FHIR_PORT}"
    echo "  Run ./scripts/start_fhir.sh first"
    echo ""
fi

# Start MCP server (default: purple agent, use --agent-type green for green agent)
python -m mcp_skills.fastmcp.server --host 0.0.0.0 --port "$MCP_PORT"
