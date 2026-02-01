#!/bin/bash
# benchmark.sh - MedAgentBench Benchmarking Script (AgentBeats Compatible)
# cd /root/UTSA-SOYOUDU/PharmAgent
# pkill -f "server.py.*901" || true
# source .venv/bin/activate
# Runs FHIR + MCP + Green + Purple agents for medical reasoning evaluation.
# Supports the full MedAgentBench benchmark with 300 tasks (10 types x 30 instances).
#
# IMPORTANT: Set GOOGLE_API_KEY in .env file before running!
# chmod +x benchmark.sh
#
# Usage:
#   ./benchmark.sh              # Run first task (task1_1) - LOCAL mode
#   ./benchmark.sh --all        # Run COMPLETE benchmark (300 tasks)
#   ./benchmark.sh task1        # Run all task1 variants (30 instances)
#   ./benchmark.sh task1_5      # Run specific task instance
#   ./benchmark.sh --local      # Run locally (explicit)
#   ./benchmark.sh --docker     # Run with Docker Compose
#   ./benchmark.sh --agentbeats # Run using AgentBeats scenario format
#   ./benchmark.sh --scenario config/scenario.toml  # Run specific scenario
#
# Subtask1 Task Types (30 instances each):
#   task1:  Patient MRN lookup
#   task2:  Age calculation
#   task3:  Record vital signs (POST)
#   task4:  Latest magnesium (24h)
#   task5:  Check/order magnesium (POST)
#   task6:  Average glucose (24h)
#   task7:  Latest glucose
#   task8:  Order consult (POST)
#   task9:  Check/order potassium (POST)
#   task10: Check/order HbA1c (POST)
#
# Subtask2 (Pokemon-Drugs Confabulation Detection):
#   ./benchmark.sh --subtask2             # Run subtask2 with subset test (2 cases, one brand, one generic)
#   ./benchmark.sh --subtask2 --full      # Run subtask2 full evaluation
#   ./benchmark.sh --subtask2 --dataset brand  # Run only brand dataset
#   ./benchmark.sh --subtask2 --all-conditions # Run all prompt conditions
#
# Subtask2: Pokemon-Drugs-Names confabulation detection (250 cases per dataset)
#
# Prerequisites:
#   1. GOOGLE_API_KEY in .env file (https://ai.google.dev/gemini-api/docs/api-key)
#   2. Docker for FHIR server: jyxsu6/medagentbench:latest
#   3. Python 3.11+ with dependencies: uv sync --extra green
#
# See: https://github.com/RDI-Foundation/agentbeats-tutorial

set -e  # Exit on error

# Navigate to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for uv or fallback to venv
get_python_cmd() {
    if command -v uv &> /dev/null; then
        echo "uv run python"
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate 2>/dev/null
        echo "./venv/bin/python"
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate 2>/dev/null
        echo "./.venv/bin/python"
    else
        echo "python3"
    fi
}

PYTHON_CMD=$(get_python_cmd)

# Defaults
TASK_ID="${1:-task1_1}"
RUN_ALL=false
LOCAL_MODE=true
DOCKER_MODE=false
AGENTBEATS_MODE=false
SUBTASK2_MODE=false
SCENARIO_FILE="config/scenario.toml"
SHOW_LOGS=false
SERVE_ONLY=false

# Subtask2 configuration
SUBTASK2_DATASET=""
SUBTASK2_FULL=false
SUBTASK2_ALL_CONDITIONS=false
SUBTASK2_CONDITION="default"
SUBTASK2_SUBSET_SIZE=2

# Port configuration
FHIR_PORT=${FHIR_PORT:-8080}
MCP_PORT=${MCP_PORT:-8002}
GREEN_PORT=${GREEN_PORT:-9009}
PURPLE_PORT=${PURPLE_PORT:-9019}
CONTAINER_NAME="medagentbench-fhir"

# Log directory
LOG_DIR="/tmp/medagentbench"
mkdir -p "$LOG_DIR"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --help|-h)
            echo -e "${BLUE}MedAgentBench Benchmarking Script${NC}"
            echo -e "${BLUE}AgentBeats Compatible${NC}"
            echo ""
            echo "Usage:"
            echo "  ./benchmark.sh              # Run first task (task1_1)"
            echo "  ./benchmark.sh --all        # Run complete benchmark (300 tasks)"
            echo "  ./benchmark.sh task1        # Run all task1 variants (30 instances)"
            echo "  ./benchmark.sh task1_5      # Run specific task instance"
            echo "  ./benchmark.sh --local      # Run locally (explicit)"
            echo "  ./benchmark.sh --docker     # Run with Docker Compose"
            echo "  ./benchmark.sh --agentbeats # Run using AgentBeats scenario format"
            echo "  ./benchmark.sh --scenario <file.toml>  # Run specific scenario"
            echo "  ./benchmark.sh --show-logs  # Show agent logs during run"
            echo "  ./benchmark.sh --serve-only # Start services without running evaluation"
            echo ""
            echo "Task Types (30 instances each):"
            echo "  task1:  Patient MRN lookup"
            echo "  task2:  Age calculation"
            echo "  task3:  Record vital signs (POST)"
            echo "  task4:  Latest magnesium (24h)"
            echo "  task5:  Check/order magnesium (POST)"
            echo "  task6:  Average glucose (24h)"
            echo "  task7:  Latest glucose"
            echo "  task8:  Order consult (POST)"
            echo "  task9:  Check/order potassium (POST)"
            echo "  task10: Check/order HbA1c (POST)"
            echo ""
            echo "Subtask2: Pokemon-Drugs Confabulation Detection:"
            echo "  ./benchmark.sh --subtask2             # Run subset test (2 cases, one brand, one generic)"
            echo "  ./benchmark.sh --subtask2 --full      # Run full evaluation (all cases)"
            echo "  ./benchmark.sh --subtask2 --dataset brand   # Run brand dataset only"
            echo "  ./benchmark.sh --subtask2 --dataset generic # Run generic dataset only"
            echo "  ./benchmark.sh --subtask2 --all-conditions  # Run all prompt conditions"
            echo "  ./benchmark.sh --subtask2 --condition mitigation  # Run specific condition"
            echo "  ./benchmark.sh --subtask2 --subset-size 20  # Custom subset size"
            echo ""
            echo "Environment Variables:"
            echo "  FHIR_PORT   - FHIR server port (default: 8080)"
            echo "  MCP_PORT    - MCP server port (default: 8002)"
            echo "  GREEN_PORT  - Green agent port (default: 9009)"
            echo "  PURPLE_PORT - Purple agent port (default: 9019)"
            echo ""
            exit 0
        ;;
        --all)
            RUN_ALL=true
            TASK_ID="all"
            ;;
        --local)
            LOCAL_MODE=true
            DOCKER_MODE=false
            AGENTBEATS_MODE=false
            ;;
        --docker)
            LOCAL_MODE=false
            DOCKER_MODE=true
            AGENTBEATS_MODE=false
            ;;
        --agentbeats)
            LOCAL_MODE=false
            DOCKER_MODE=false
            AGENTBEATS_MODE=true
            ;;
        --scenario)
            shift
            SCENARIO_FILE="$1"
            AGENTBEATS_MODE=true
            ;;
        --show-logs)
            SHOW_LOGS=true
            ;;
        --serve-only)
            SERVE_ONLY=true
            ;;
        --subtask2)
            SUBTASK2_MODE=true
            LOCAL_MODE=false
            ;;
        --dataset)
            shift
            SUBTASK2_DATASET="$1"
            ;;
        --full)
            SUBTASK2_FULL=true
            ;;
        --all-conditions)
            SUBTASK2_ALL_CONDITIONS=true
            ;;
        --condition)
            shift
            SUBTASK2_CONDITION="$1"
            ;;
        --subset-size)
            shift
            SUBTASK2_SUBSET_SIZE="$1"
            ;;
        task*)
            TASK_ID="$arg"
            ;;
    esac
done

echo -e "${BLUE}🏥 MedAgentBench Benchmarking${NC}"
echo "========================================"
echo -e "💊 Medical reasoning evaluation with MCP + A2A protocol"
echo -e "📚 AgentBeats Compatible: https://github.com/RDI-Foundation/agentbeats-tutorial"
echo ""

if [ "$LOCAL_MODE" = true ]; then
    echo -e "🏠 Running in ${GREEN}LOCAL${NC} mode"
elif [ "$DOCKER_MODE" = true ]; then
    echo -e "🐳 Running in ${BLUE}DOCKER${NC} mode"
elif [ "$AGENTBEATS_MODE" = true ]; then
    echo -e "🎯 Running in ${YELLOW}AGENTBEATS${NC} mode with scenario: $SCENARIO_FILE"
elif [ "$SUBTASK2_MODE" = true ]; then
    echo -e "🎮 Running in ${YELLOW}SUBTASK2${NC} mode (Pokemon-Drugs Confabulation Detection)"
fi

if [ "$RUN_ALL" = true ]; then
    echo "📋 Task Mode: Running COMPLETE benchmark (300 tasks)"
elif [[ "$TASK_ID" =~ ^task[0-9]+_[0-9]+$ ]]; then
    echo "📋 Task Mode: Running specific task instance '$TASK_ID'"
elif [[ "$TASK_ID" =~ ^task[0-9]+$ ]]; then
    echo "📋 Task Mode: Running all instances of task type '$TASK_ID'"
else
    echo "📋 Task Mode: Running task '$TASK_ID'"
fi
echo ""

# Function to start FHIR server
start_fhir_server() {
    # Check if already running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "✅ FHIR server already running on port $FHIR_PORT"
        return 0
    fi
    
    # Check if container exists but stopped
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "🔄 Starting existing FHIR container..."
        docker start "$CONTAINER_NAME"
    else
        echo "📦 Starting FHIR server (jyxsu6/medagentbench:latest)..."
        echo "   This may take a few minutes on first run..."
        docker pull jyxsu6/medagentbench:latest 2>/dev/null || true
        docker run -d --name "$CONTAINER_NAME" -p ${FHIR_PORT}:8080 jyxsu6/medagentbench:latest
    fi
    
    # Wait for FHIR server
    echo "⏳ Waiting for FHIR server to initialize..."
    local max_attempts=60
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:${FHIR_PORT}/fhir/metadata" > /dev/null 2>&1; then
            echo -e "✅ FHIR server ready at http://localhost:${FHIR_PORT}/fhir/"
            return 0
        fi
        if [ $((attempt % 10)) -eq 0 ]; then
            echo "   Still initializing... (~$((attempt * 2))s elapsed)"
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ FHIR server failed to start${NC}"
    return 1
}

# Wait for agent to be ready
wait_for_agent() {
    local url=$1
    local name=$2
    local max_attempts=${3:-30}
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "${url}/.well-known/agent-card.json" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

# Wait for MCP server to be ready (longer timeout, different health check)
wait_for_mcp() {
    local port=$1
    local max_attempts=${2:-60}  # MCP servers take longer to start
    local attempt=1

    echo "⏳ Waiting for MCP server to initialize..."
    while [ $attempt -le $max_attempts ]; do
        # Try health endpoint first
        if curl -f -s "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo -e "✅ MCP server ready at http://localhost:${port}/"
            return 0
        fi
        # Also try root endpoint
        if curl -f -s "http://localhost:${port}/" > /dev/null 2>&1; then
            echo -e "✅ MCP server ready at http://localhost:${port}/"
            return 0
        fi
        if [ $((attempt % 10)) -eq 0 ]; then
            echo "   Still initializing... (~${attempt}s elapsed)"
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e "${YELLOW}⚠️  MCP server may not be ready (port $port)${NC}"
    return 1
}

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    [ -n "$MCP_PID" ] && kill $MCP_PID 2>/dev/null && echo "  Stopped MCP server" || true
    [ -n "$GREEN_PID" ] && kill $GREEN_PID 2>/dev/null && echo "  Stopped Green agent" || true
    [ -n "$PURPLE_PID" ] && kill $PURPLE_PID 2>/dev/null && echo "  Stopped Purple agent" || true
    echo ""
    echo "💡 FHIR server still running. Stop with: docker rm -f $CONTAINER_NAME"
}

# Load environment
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        echo -e "✅ Loaded environment from .env"
    elif [ -f "sample.env" ]; then
        echo -e "${YELLOW}⚠️  No .env file found. Copy sample.env to .env and configure it.${NC}"
        echo "   cp sample.env .env"
        return 1
    fi
    return 0
}

# Validate API key
validate_api_key() {
    if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your_google_api_key_here" ]; then
        echo -e "${RED}❌ GOOGLE_API_KEY not properly configured${NC}"
        echo ""
        echo "📝 To fix this:"
        echo "   1. Copy: cp sample.env .env"
        echo "   2. Edit .env and add your Google API key"
        echo "   3. Get key at: https://ai.google.dev/gemini-api/docs/api-key"
        echo ""
        return 1
    fi
    return 0
}

# ============================================================
# SUBTASK2 MODE - Pokemon-Drugs Confabulation Detection
# ============================================================
if [ "$SUBTASK2_MODE" = true ]; then
    echo -e "${YELLOW}🎮 Subtask2: Pokemon-Drugs Confabulation Detection${NC}"
    echo ""

    # Load environment
    load_env || exit 1
    validate_api_key || exit 1
    echo -e "✅ Environment configured"

    # Set up trap for cleanup
    trap cleanup EXIT SIGINT SIGTERM

    # Start Purple agent only (no FHIR needed for subtask2)
    echo ""
    echo "🚀 Starting Purple Agent..."

    # Check if port is already in use and clean it up
    if lsof -i :$PURPLE_PORT > /dev/null 2>&1; then
        echo "  ⚠️  Port $PURPLE_PORT already in use, cleaning up..."
        lsof -ti :$PURPLE_PORT | xargs kill -9 2>/dev/null || true
        sleep 2
        echo "  ✅ Port $PURPLE_PORT cleaned up"
    fi

    if [ "$SHOW_LOGS" = true ]; then
        (cd purple_agent/src && $PYTHON_CMD server.py --host 0.0.0.0 --port $PURPLE_PORT) &
    else
        (cd purple_agent/src && $PYTHON_CMD server.py --host 0.0.0.0 --port $PURPLE_PORT > "$LOG_DIR/purple.log" 2>&1) &
    fi
    PURPLE_PID=$!
    sleep 5

    if ! kill -0 $PURPLE_PID 2>/dev/null; then
        echo -e "${RED}❌ Purple agent failed to start${NC}"
        [ -f "$LOG_DIR/purple.log" ] && tail -20 "$LOG_DIR/purple.log"
        exit 1
    fi

    # Verify Purple agent is ready
    if wait_for_agent "http://localhost:${PURPLE_PORT}" "Purple agent" 30; then
        echo -e "  ✅ Purple agent started (PID: $PURPLE_PID)"
    else
        echo -e "${RED}❌ Purple agent failed to respond${NC}"
        [ -f "$LOG_DIR/purple.log" ] && tail -20 "$LOG_DIR/purple.log"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}🎉 Services ready!${NC}"
    echo ""

    # Build evaluation command
    EVAL_ARGS="--purple-agent-url http://localhost:${PURPLE_PORT}"

    if [ -n "$SUBTASK2_DATASET" ]; then
        EVAL_ARGS="$EVAL_ARGS --dataset $SUBTASK2_DATASET"
    fi

    if [ "$SUBTASK2_FULL" = true ]; then
        EVAL_ARGS="$EVAL_ARGS --full"
    else
        EVAL_ARGS="$EVAL_ARGS --subset-size $SUBTASK2_SUBSET_SIZE"
    fi

    if [ "$SUBTASK2_ALL_CONDITIONS" = true ]; then
        EVAL_ARGS="$EVAL_ARGS --all-conditions"
    else
        EVAL_ARGS="$EVAL_ARGS --condition $SUBTASK2_CONDITION"
    fi

    # Run evaluation
    echo "🧪 Running Subtask2 evaluation..."
    echo "========================================"

    $PYTHON_CMD -m src.tasks.subtask2.run_evaluation $EVAL_ARGS
    EXIT_CODE=$?

    echo ""
    echo "========================================"

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Subtask2 evaluation completed successfully!${NC}"
        echo ""

        # Find the latest subtask2 results file
        LATEST_RESULT=$(find ./experiments/subtask2/ -name "*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

        if [ -f "$LATEST_RESULT" ]; then
            # Extract metrics from the JSON file
            METRICS=$(python3 -c "
import json
with open('$LATEST_RESULT', 'r') as f:
    data = json.load(f)
    metrics = data['metrics']
    total = metrics['total_cases']
    correct = metrics['correct']
    inherited = metrics['inherited_hallucinations']
    epistemic = metrics['epistemic_hallucinations']
    hallucinations = inherited + epistemic
    accuracy_pct = (correct/total*100) if total > 0 else 0
    print(f'{correct}/{total}')
    print(f'{accuracy_pct:.1f}%')
    print(f'{hallucinations}')
")

            echo "📊 Performance Metrics:"
            echo "  🎯 Accuracy: $(echo "$METRICS" | head -1) ($(echo "$METRICS" | head -2 | tail -1))"
            echo "  🛠️  Hallucinations Detected: $(echo "$METRICS" | tail -1)"
            echo "  ⏱️  Time: <1 minute"
            echo ""

            # Extract log path from results
            LOG_PATH=$(python3 -c "
import json
with open('$LATEST_RESULT', 'r') as f:
    data = json.load(f)
    print(data.get('log_path', 'N/A'))
")

            if [ "$LOG_PATH" != "N/A" ]; then
                echo "📋 Agent trajectory log: $LOG_PATH"
            else
                echo "📋 Agent trajectory log: (not found in results file)"
            fi
            echo ""
        fi

        echo "📁 Results saved to: ./experiments/subtask2/"
    else
        echo -e "${RED}❌ Subtask2 evaluation had errors.${NC}"
        echo ""
        echo "🔍 Debug logs:"
        echo "  Purple agent: $LOG_DIR/purple.log"
    fi

    echo ""
    echo "🏁 Subtask2 evaluation finished."
    exit $EXIT_CODE
fi

# ============================================================
# AGENTBEATS MODE - Uses scenario.toml format
# ============================================================
if [ "$AGENTBEATS_MODE" = true ]; then
    echo -e "${YELLOW}🎯 AgentBeats Mode${NC}"
    echo ""
    
    # Load environment
    load_env || exit 1
    validate_api_key || exit 1
    
    # Check scenario file
    if [ ! -f "$SCENARIO_FILE" ]; then
        echo -e "${RED}❌ Scenario file not found: $SCENARIO_FILE${NC}"
        exit 1
    fi
    
    # Update scenario with current task
    if [ "$TASK_ID" != "task1_1" ] && [ "$TASK_ID" != "all" ]; then
        echo "📝 Updating scenario with task_id: $TASK_ID"
        # Create temp scenario file with updated task_id
        TEMP_SCENARIO=$(mktemp)
        sed "s/task_id = .*/task_id = \"$TASK_ID\"/" "$SCENARIO_FILE" > "$TEMP_SCENARIO"
        SCENARIO_FILE="$TEMP_SCENARIO"
    fi
    
    # Set up trap for cleanup
    trap cleanup EXIT SIGINT SIGTERM
    
    # Start FHIR server
    echo ""
    start_fhir_server || exit 1
    echo ""
    
    # Start MCP server first (needed by both agents)
    echo "🚀 Starting MCP server..."

    # Check if port is already in use and clean it up
    if lsof -i :$MCP_PORT > /dev/null 2>&1; then
        echo "  ⚠️  Port $MCP_PORT already in use, cleaning up..."
        # Kill any existing processes on the port
        lsof -ti :$MCP_PORT | xargs kill -9 2>/dev/null || true
        sleep 2
        echo "  ✅ Port $MCP_PORT cleaned up"
    fi

    export MCP_FHIR_API_BASE="http://localhost:${FHIR_PORT}/fhir/"
    
    if [ "$SHOW_LOGS" = true ]; then
        $PYTHON_CMD -m mcp_skills.fastmcp.server --agent-type green --host 0.0.0.0 --port "$MCP_PORT" &
    else
        $PYTHON_CMD -m mcp_skills.fastmcp.server --agent-type green --host 0.0.0.0 --port "$MCP_PORT" > "$LOG_DIR/mcp.log" 2>&1 &
    fi
    MCP_PID=$!
    sleep 3
    
    if ! kill -0 $MCP_PID 2>/dev/null; then
        echo -e "${RED}❌ MCP server failed to start - process exited immediately${NC}"
        echo "   Possible causes:"
        echo "   • Port $MCP_PORT already in use by another process"
        echo "   • FHIR server not running on port $FHIR_PORT"
        echo "   • Missing dependencies or configuration errors"
        echo ""
        echo "   Checking port $MCP_PORT usage:"
        lsof -i :$MCP_PORT 2>/dev/null || echo "   No process found on port $MCP_PORT"
        echo ""
        [ -f "$LOG_DIR/mcp.log" ] && echo "   MCP server log:" && cat "$LOG_DIR/mcp.log"
        exit 1
    fi

    # Wait a bit more and test health endpoint
    sleep 2
    if curl -f -s "http://localhost:$MCP_PORT/health" > /dev/null 2>&1; then
        echo -e "  ✅ MCP server started and healthy (PID: $MCP_PID)"
    else
        echo -e "${YELLOW}⚠️  MCP server started but health check failed${NC}"
        echo "   Server may still be initializing..."
    fi
    
    # Run using AgentBeats scenario runner
    echo ""
    echo "🎯 Running AgentBeats scenario..."
    echo "========================================"
    
    RUNNER_ARGS="$SCENARIO_FILE"
    [ "$SHOW_LOGS" = true ] && RUNNER_ARGS="$RUNNER_ARGS --show-logs"
    [ "$SERVE_ONLY" = true ] && RUNNER_ARGS="$RUNNER_ARGS --serve-only"
    
    $PYTHON_CMD scripts/run_scenario.py $RUNNER_ARGS
    EXIT_CODE=$?
    
    echo ""
    echo "========================================"
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Benchmarking completed successfully!${NC}"
        echo ""
        echo "📁 Results saved to: ./experiments/"
    else
        echo -e "${RED}❌ Benchmarking had errors.${NC}"
        echo ""
        echo "🔍 Debug logs:"
        echo "  MCP server:    $LOG_DIR/mcp.log"
    fi
    
    echo ""
    echo "🏁 Benchmarking finished."
    exit $EXIT_CODE
fi

# ============================================================
# LOCAL MODE - Direct Python execution
# ============================================================
if [ "$LOCAL_MODE" = true ]; then
    echo "🔧 Checking environment..."

    # Load .env file
    load_env || exit 1
    validate_api_key || exit 1
    echo -e "✅ Environment configured"

    # Set up trap for cleanup
    trap cleanup EXIT SIGINT SIGTERM

    # Start FHIR server
    echo ""
    start_fhir_server || exit 1
    echo ""

    # Start MCP server
    echo "🚀 Starting services..."
    echo "  Starting MCP server..."

    # Check if port is already in use and clean it up
    if lsof -i :$MCP_PORT > /dev/null 2>&1; then
        echo "    ⚠️  Port $MCP_PORT already in use, cleaning up..."
        # Kill any existing processes on the port
        lsof -ti :$MCP_PORT | xargs kill -9 2>/dev/null || true
        sleep 2
        echo "    ✅ Port $MCP_PORT cleaned up"
    fi

    export MCP_FHIR_API_BASE="http://localhost:${FHIR_PORT}/fhir/"
    
    if [ "$SHOW_LOGS" = true ]; then
        $PYTHON_CMD -m mcp_skills.fastmcp.server --agent-type green --host 0.0.0.0 --port "$MCP_PORT" &
    else
        $PYTHON_CMD -m mcp_skills.fastmcp.server --agent-type green --host 0.0.0.0 --port "$MCP_PORT" > "$LOG_DIR/mcp.log" 2>&1 &
    fi
    MCP_PID=$!
    sleep 5  # Give MCP server more time to initialize

    if ! kill -0 $MCP_PID 2>/dev/null; then
        echo -e "${RED}❌ MCP server failed to start - process exited immediately${NC}"
        echo "   Possible causes:"
        echo "   • Port $MCP_PORT already in use by another process"
        echo "   • FHIR server not running on port $FHIR_PORT"
        echo "   • Missing dependencies or configuration errors"
        echo ""
        echo "   Checking port $MCP_PORT usage:"
        lsof -i :$MCP_PORT 2>/dev/null || echo "   No process found on port $MCP_PORT"
        echo ""
        [ -f "$LOG_DIR/mcp.log" ] && echo "   MCP server log:" && cat "$LOG_DIR/mcp.log"
        exit 1
    fi

    # Wait a bit more and test health endpoint
    sleep 2
    if curl -f -s "http://localhost:$MCP_PORT/health" > /dev/null 2>&1; then
        echo "  ✅ MCP server started and healthy (PID: $MCP_PID)"
    else
        echo -e "${YELLOW}⚠️  MCP server started but health check failed${NC}"
        echo "   Server may still be initializing..."
    fi

    # Start Green agent
    echo "  Starting Green Agent..."

    # Check if port is already in use and clean it up
    if lsof -i :$GREEN_PORT > /dev/null 2>&1; then
        echo "    ⚠️  Port $GREEN_PORT already in use, cleaning up..."
        # Kill any existing processes on the port
        lsof -ti :$GREEN_PORT | xargs kill -9 2>/dev/null || true
        sleep 2
        echo "    ✅ Port $GREEN_PORT cleaned up"
    fi

    if [ "$SHOW_LOGS" = true ]; then
        $PYTHON_CMD src/server.py --host 0.0.0.0 --port $GREEN_PORT &
    else
        $PYTHON_CMD src/server.py --host 0.0.0.0 --port $GREEN_PORT > "$LOG_DIR/green.log" 2>&1 &
    fi
    GREEN_PID=$!
    sleep 3

    if ! kill -0 $GREEN_PID 2>/dev/null; then
        echo -e "${RED}❌ Green agent failed to start - process exited immediately${NC}"
        echo "   Possible causes:"
        echo "   • Port $GREEN_PORT already in use by another process"
        echo "   • MCP server not running or unreachable"
        echo "   • Missing dependencies or configuration errors"
        echo ""
        echo "   Checking port $GREEN_PORT usage:"
        lsof -i :$GREEN_PORT 2>/dev/null || echo "   No process found on port $GREEN_PORT"
        echo ""
        [ -f "$LOG_DIR/green.log" ] && echo "   Green agent log:" && cat "$LOG_DIR/green.log"
        exit 1
    fi

    # Test agent card endpoint
    sleep 2
    if curl -f -s "http://localhost:$GREEN_PORT/.well-known/agent-card.json" > /dev/null 2>&1; then
        echo "  ✅ Green agent started and responding (PID: $GREEN_PID)"
    else
        echo -e "${YELLOW}⚠️  Green agent started but health check failed${NC}"
        echo "   Agent may still be initializing..."
    fi

    # Start Purple agent
    echo "  Starting Purple Agent..."

    # Check if port is already in use and clean it up
    if lsof -i :$PURPLE_PORT > /dev/null 2>&1; then
        echo "    ⚠️  Port $PURPLE_PORT already in use, cleaning up..."
        # Kill any existing processes on the port
        lsof -ti :$PURPLE_PORT | xargs kill -9 2>/dev/null || true
        sleep 2
        echo "    ✅ Port $PURPLE_PORT cleaned up"
    fi

    if [ "$SHOW_LOGS" = true ]; then
        (cd purple_agent/src && $PYTHON_CMD server.py --host 0.0.0.0 --port $PURPLE_PORT) &
    else
        (cd purple_agent/src && $PYTHON_CMD server.py --host 0.0.0.0 --port $PURPLE_PORT > "$LOG_DIR/purple.log" 2>&1) &
    fi
    PURPLE_PID=$!
    sleep 5

    if ! kill -0 $PURPLE_PID 2>/dev/null; then
        echo -e "${RED}❌ Purple agent failed to start - process exited immediately${NC}"
        echo "   Possible causes:"
        echo "   • Port $PURPLE_PORT already in use by another process"
        echo "   • MCP server not running or unreachable"
        echo "   • Missing dependencies or configuration errors"
        echo ""
        echo "   Checking port $PURPLE_PORT usage:"
        lsof -i :$PURPLE_PORT 2>/dev/null || echo "   No process found on port $PURPLE_PORT"
        echo ""
        [ -f "$LOG_DIR/purple.log" ] && echo "   Purple agent log:" && cat "$LOG_DIR/purple.log"
        exit 1
    fi

    # Verify services
    echo ""
    echo "🏥 Verifying services..."
    
    if curl -f -s http://localhost:${FHIR_PORT}/fhir/metadata > /dev/null 2>&1; then
        echo -e "  ✅ FHIR server (port $FHIR_PORT)"
    else
        echo -e "  ${RED}❌ FHIR server failed${NC}"
        exit 1
    fi

    if wait_for_mcp "$MCP_PORT" 30; then
        echo -e "  ✅ MCP server (port $MCP_PORT)"
    else
        echo -e "  ${YELLOW}⚠️  MCP server may not be ready (port $MCP_PORT)${NC}"
    fi

    if wait_for_agent "http://localhost:${GREEN_PORT}" "Green agent" 10; then
        echo -e "  ✅ Green agent (port $GREEN_PORT)"
    else
        echo -e "  ${RED}❌ Green agent failed${NC}"
        [ -f "$LOG_DIR/green.log" ] && tail -20 "$LOG_DIR/green.log"
        exit 1
    fi

    if wait_for_agent "http://localhost:${PURPLE_PORT}" "Purple agent" 10; then
        echo -e "  ✅ Purple agent (port $PURPLE_PORT)"
    else
        echo -e "  ${RED}❌ Purple agent failed${NC}"
        [ -f "$LOG_DIR/purple.log" ] && tail -20 "$LOG_DIR/purple.log"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}🎉 All services ready!${NC}"
    echo ""

    # Handle serve-only mode
    if [ "$SERVE_ONLY" = true ]; then
        echo "📡 Serve-only mode. Press Ctrl+C to stop."
        echo ""
        echo "Endpoints:"
        echo "  FHIR Server:  http://localhost:${FHIR_PORT}/fhir/"
        echo "  MCP Server:   http://localhost:${MCP_PORT}"
        echo "  Green Agent:  http://localhost:${GREEN_PORT}"
        echo "  Purple Agent: http://localhost:${PURPLE_PORT}"
        echo ""
        while true; do
            sleep 1
        done
    fi

    # Run benchmark
    echo "🧪 Running benchmark..."
    echo "========================================"
    
    if [ "$RUN_ALL" = true ]; then
        # Run all 300 tasks
        $PYTHON_CMD scripts/run_all_tasks.py
        EXIT_CODE=$?
    elif [[ "$TASK_ID" =~ ^task[0-9]+$ ]]; then
        # Run all instances of a task type (e.g., task1 -> task1_1 to task1_30)
        TASK_NUM="${TASK_ID#task}"
        echo "Running all instances of task$TASK_NUM (30 tasks)..."
        EXIT_CODE=0
        for i in $(seq 1 30); do
            echo ""
            echo "--- Task ${TASK_NUM}_${i} ---"
            $PYTHON_CMD scripts/run_evaluation.py --task "task${TASK_NUM}_${i}" || EXIT_CODE=1
        done
    else
        # Run single task
        $PYTHON_CMD scripts/run_evaluation.py --task "$TASK_ID"
        EXIT_CODE=$?
    fi

    echo ""
    echo "========================================"

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Benchmarking completed successfully!${NC}"
        echo ""
        echo "📁 Results saved to: ./experiments/"
    else
        echo -e "${RED}❌ Benchmarking had errors.${NC}"
        echo ""
        echo "🔍 Debug logs:"
        echo "  MCP server:    $LOG_DIR/mcp.log"
        echo "  Green agent:   $LOG_DIR/green.log"
        echo "  Purple agent:  $LOG_DIR/purple.log"
    fi

    echo ""
    echo "🏁 Benchmarking finished."
    exit $EXIT_CODE
fi

# ============================================================
# DOCKER MODE - Docker Compose execution
# ============================================================
if [ "$DOCKER_MODE" = true ]; then
    echo -e "${BLUE}🐳 Running in DOCKER mode${NC}"
    echo ""

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi

    # Start FHIR server first
    start_fhir_server || exit 1
    echo ""

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        echo -e "${RED}❌ Docker Compose not available${NC}"
        exit 1
    fi

    # Start services
    echo "📦 Starting Docker services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi

    # Wait for health
    echo "⏳ Waiting for services to be healthy..."
    sleep 15

    # Check status
    echo "🔍 Checking service status..."
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    # Handle serve-only mode
    if [ "$SERVE_ONLY" = true ]; then
        echo ""
        echo "📡 Serve-only mode. Press Ctrl+C to stop."
        echo ""
        while true; do
            sleep 1
        done
    fi

    # Run evaluation
    echo ""
    echo "🧪 Running benchmark..."
    
    if [ "$RUN_ALL" = true ]; then
        $PYTHON_CMD scripts/run_all_tasks.py
    else
        $PYTHON_CMD scripts/run_evaluation.py --task "$TASK_ID"
    fi
    
    EXIT_CODE=$?

    # Cleanup
    echo ""
    echo "🧹 Stopping Docker services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi

    echo ""
    echo "💡 FHIR server still running. Stop with: docker rm -f $CONTAINER_NAME"
    echo "🏁 Benchmarking finished."
    exit $EXIT_CODE
fi
