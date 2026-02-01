#!/bin/bash
# Cleanup script for MedAgentBench Docker resources

set -e

CONTAINER_NAME="medagentbench-fhir"
IMAGE_NAME="medagentbench"
PULLED_IMAGE="jyxsu6/medagentbench:latest"

echo "========================================="
echo "MedAgentBench - Docker Cleanup"
echo "========================================="
echo ""

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing container: ${CONTAINER_NAME}..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    echo "✓ Container removed"
else
    echo "✓ Container not found (already removed)"
fi

# Remove tagged image (optional)
if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}:latest$"; then
    echo ""
    read -p "Remove tagged image '${IMAGE_NAME}:latest'? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rmi "${IMAGE_NAME}:latest" 2>/dev/null || true
        echo "✓ Tagged image removed"
    else
        echo "  Skipping tagged image removal"
    fi
else
    echo "✓ Tagged image not found"
fi

# Remove pulled image (optional - frees ~5GB)
if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${PULLED_IMAGE}$"; then
    echo ""
    read -p "Remove pulled image '${PULLED_IMAGE}' (~5GB)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rmi "${PULLED_IMAGE}" 2>/dev/null || true
        echo "✓ Pulled image removed"
    else
        echo "  Skipping pulled image removal (keeps image for reuse)"
    fi
else
    echo "✓ Pulled image not found"
fi

echo ""
echo "========================================="
echo "Cleanup Complete"
echo "========================================="
echo ""
echo "To check remaining Docker resources:"
echo "  docker ps -a          # All containers"
echo "  docker images          # All images"
echo "  docker system df       # Disk usage"
