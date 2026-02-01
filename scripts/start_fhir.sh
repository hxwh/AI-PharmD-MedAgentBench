#!/bin/bash
# Start the FHIR server (jyxsu6/medagentbench:latest)
# Pre-loaded with MedAgentBench patient data

set -e

CONTAINER_NAME="medagentbench-fhir"
FHIR_PORT=${FHIR_PORT:-8080}

# Cleanup function
cleanup() {
    echo "Stopping FHIR server..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    exit 0
}

# Handle Ctrl+C
trap cleanup SIGINT SIGTERM

# Check if already running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "FHIR server already running on port $FHIR_PORT"
    echo "  Stop with: docker rm -f $CONTAINER_NAME"
    exit 0
fi

# Pull and run (matching official Stanford setup)
echo "Starting MedAgentBench FHIR server..."
echo "  Image: jyxsu6/medagentbench:latest"
echo "  Port: $FHIR_PORT"
echo ""

echo "Pulling Docker image (this may take a few minutes)..."
if ! docker pull jyxsu6/medagentbench:latest; then
    echo "Error: Failed to pull jyxsu6/medagentbench:latest"
    echo "  Check your internet connection or try: docker login"
    exit 1
fi
docker tag jyxsu6/medagentbench:latest medagentbench
docker run -d --name "$CONTAINER_NAME" -p ${FHIR_PORT}:8080 medagentbench

echo ""
echo "Waiting for FHIR server to initialize (this takes ~1-2 minutes)..."
echo ""

# Wait for server to be ready
max_attempts=120
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s "http://localhost:${FHIR_PORT}/fhir/metadata" > /dev/null 2>&1; then
        echo ""
        echo "✓ FHIR server ready at http://localhost:${FHIR_PORT}/fhir/"
        echo ""
        echo "To stop: docker rm -f $CONTAINER_NAME"
        exit 0
    fi
    if [ $((attempt % 10)) -eq 0 ]; then
        echo "  Still initializing... (~$((attempt * 2))s elapsed)"
    fi
    sleep 2
    attempt=$((attempt + 1))
done

echo "Error: FHIR server failed to start"
exit 1
