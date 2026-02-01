# MedAgentBench - AgentBeats Compatible Evaluation System

A complete **AgentBeats-compatible** medical AI evaluation platform implementing the A2A (Agent-to-Agent) protocol. Provides both **MedAgentBench Evaluator (Green Agent)** with dynamic ground truth generation and **PharmD Agent (Purple Agent)** for clinical reasoning tasks. Evaluates medical LLM agents on Stanford MedAgentBench clinical reasoning tasks using dynamic FHIR data, orchestrates task execution via A2A protocol, provides FHIR tools via MCP, and returns comprehensive evaluation results with failure taxonomy.

## What is AgentBeats?

AgentBeats is an open platform for **standardized and reproducible agent evaluations**. It uses:
- **Green Agents** (evaluators) that orchestrate and score agent performance
- **Purple Agents** (participants) that perform the actual tasks
- **A2A Protocol** for standardized agent communication
- **MCP (Model Context Protocol)** for tool access
- **Docker** for reproducible environments

This implementation is fully compatible with the [AgentBeats tutorial](https://github.com/RDI-Foundation/agentbeats-tutorial) and can be registered on [agentbeats.dev](https://agentbeats.dev).

## 🏆 Leaderboard

Compete on the PharmAgent leaderboard! Submit your AI agents to benchmark performance on medical reasoning tasks.

### Quick Start

1. **Register** your agent on [AgentBeats](https://agentbeats.dev)
2. **Fork** the [leaderboard repository](https://github.com/your-org/pharmagent-leaderboard)
3. **Update** `scenario.toml` with your agent ID
4. **Submit** a Pull Request - assessment runs automatically
5. **View** results on the leaderboard

### Benchmarks

- **Medical Record Tasks**: Patient lookup, vital signs, lab ordering
- **Confabulation Detection**: Distinguish real drugs from Pokemon names

See `leaderboard/README.md` for setup details.

# Running

## Quick Start

```bash
# 1. Set up environment
cp sample.env .env
# Edit .env and add your GOOGLE_API_KEY

# 2. Install dependencies
uv sync --extra green

# 3. Start services
./benchmark.sh --serve-only  # Start all services (FHIR + MCP + Green + Purple)

# 4. Run evaluation
uv run medagentbench-run config/scenario.toml
```

## Detailed Usage

### Traditional Mode (Direct Python)

```bash
# Setup
uv sync --extra green

# Start FHIR and MCP servers
./scripts/run_all.sh

# Start agents in separate terminals
python src/server.py              # Green Agent (Evaluator)
python purple_agent/src/server.py # Purple Agent (Under Test)

# Run evaluation
python scripts/run_evaluation.py --task task1_1
```

### AgentBeats Mode (Scenario Runner)

```bash
# Setup
uv sync --extra green

# Run using AgentBeats scenario format (supports batch evaluation)
# Current scenario runs all 300 tasks (task1-task10, 30 instances each)
# Note: Batch evaluation takes time - monitor progress with --show-logs
uv run medagentbench-run config/scenario.toml

# Or with options
uv run medagentbench-run config/scenario.toml --show-logs
uv run medagentbench-run config/scenario.toml --serve-only
```

### Benchmark Mode (Complete Suite)

```bash
# Run single task
./benchmark.sh task1_1

# Run all 30 instances of task1
./benchmark.sh task1

# Run complete benchmark (300 tasks)
./benchmark.sh --all

# AgentBeats compatible mode
./benchmark.sh --agentbeats
```

Task ID	Type	Description
task1	read_query	Find patient's current problem list
task2	calculate_age	Calculate patient's age from DOB
task3	record_vitals	Record blood pressure vital sign (POST)
task4	read_lab	Get latest magnesium level (24h)
task5	check_and_order_magnesium	Check Mg + order IV replacement if low
task6	calculate_average	Average glucose over 24h
task7	read_lab	Get latest glucose level
task8	order_consult	Order orthopedic consult with SBAR note
task9	check_and_order_potassium	Check K + order replacement + recheck
task10	check_and_order_a1c	Check A1C + order if >1 year old





## Project Structure

```
src/
├─ server.py      # Server setup and agent card configuration
├─ executor.py    # A2A request handling
├─ agent.py       # Agent implementation (evaluation logic)
├─ messenger.py   # A2A messaging utilities
├─ nodes.py       # PocketFlow nodes for evaluation pipeline
├─ flow.py        # Flow construction and orchestration
├─ tasks/
│  ├─ __init__.py       # Task module (re-exports from subtask1)
│  ├─ subtask1/         # Original PharmD evaluation tasks
│  │  ├─ __init__.py    # Task loading utilities
│  │  ├─ tasks.json     # 10 official PharmD evaluation tasks
│  │  ├─ test_data_v2.json  # Benchmark test data
│  │  ├─ refsol.py      # Reference solution evaluators
│  │  ├─ utils.py       # FHIR API utilities for evaluation
│  │  ├─ funcs_mapping.md  # FHIR API to MCP tools mapping
│  │  ├─ funcs_mcp.json    # MCP tool definitions
│  │  └─ funcs_v1.json      # Legacy FHIR API definitions
│  └─ subtask2/         # Reserved for future tasks
│     └─ __init__.py
├─ utils/
│  ├─ call_gemini.py    # Google Gemini API utility
│  └─ task_logger.py    # Task logging utilities
mcp_skills/           # MCP Server package
├─ fastmcp/                # FastMCP server infrastructure
│  ├─ app.py              # FastMCP instance, AgentType enum
│  └─ server.py           # Server entry point (--agent-type flag)
└─ fhir/                   # FHIR tools and models
   ├─ models.py           # Pydantic models
   ├─ client.py           # FHIR API client
   ├─ tools.py            # FHIR tools (both agents)
   ├─ eval_tools.py       # Evaluation tools (Green agent only)
   └─ resources.py        # MCP resources
examples/
purple_agent/             # Purple Agent (Agent Under Test)
├─ src/
│  ├─ server.py         # A2A server for purple agent
│  ├─ agent.py          # Purple agent logic
│  ├─ executor.py       # A2A executor
│  └─ messenger.py      # MCP communication
├─ pyproject.toml       # Purple agent dependencies
└─ Dockerfile           # Purple agent container
tests/
├─ mock_purple_agent.py # Mock purple agent for testing
└─ full_test.py         # Full integration test
tests/
└─ test_agent.py        # Agent tests
docs/
└─ QUICKSTART.md        # Quick start guide
bin/
└─ .env.example         # Environment variables template
docker/
└─ Dockerfile           # Docker configuration
pyproject.toml          # Python dependencies
```

## Getting Started

Follow these steps to run the PharmD Agent System from scratch.

**Quick Summary:**
1. Install Python dependencies
2. Configure `.env` file with Google API key
3. (Optional) Start FHIR and MCP servers for full functionality
4. Start MedAgentBench evaluator (green agent) server
5. Run tests to verify setup

**Minimum setup time:** ~5 minutes (without FHIR server)  
**Full setup time:** ~10 minutes (with FHIR server)

### Prerequisites

Before starting, ensure you have:
- **Python 3.10 or higher** (check with `python --version`)
- **pip** package manager
- **Docker** (optional, for FHIR server)
- **Google Gemini API Key** ([Get one here](https://ai.google.dev/gemini-api/docs/api-key))

### Step-by-Step Setup

#### Step 1: Navigate to Project Directory

```bash
cd /root/streamlit/Agents/PharmAgent
```

#### Step 2: Install Python Dependencies

```bash
# Install the package with test dependencies
pip install -e ".[test]"

# Or using make
make dev
```

**Verify installation:**
```bash
# Check that key packages are installed
python -c "import a2a; import fastmcp; print('✓ Dependencies installed')"
```

#### Step 3: Configure Environment Variables

```bash
# Copy the environment template
cp sample.env .env

# Edit .env file and add your Google API key
nano .env  # or use your preferred editor
```

**Required configuration in `.env`:**
```bash
# REQUIRED: Google Gemini API Key (get from https://ai.google.dev/gemini-api/docs/api-key)
GOOGLE_API_KEY=your_actual_api_key_here
```

**Verify API key is set:**
```bash
# Check your API key is configured
cat .env | grep GOOGLE_API_KEY
```

**Optional configuration (defaults shown):**
```bash
# MCP Server Configuration
FHIR_MCP_SERVER_URL=http://localhost:8002
MCP_FHIR_API_BASE=http://localhost:8080/fhir/

# Agent Configuration
GREEN_AGENT_HOST=0.0.0.0
GREEN_AGENT_PORT=9009
GREEN_AGENT_CARD_URL=http://localhost:9009/

# PharmD Agent (Purple Agent) Configuration (for testing)
PURPLE_AGENT_HOST=0.0.0.0
PURPLE_AGENT_PORT=9019

# Task Configuration
MAX_ROUNDS=10
TASK_TIMEOUT=300
```

**Get your Google API Key:**
1. Visit [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)
2. Click "Get API Key"
3. Create a new project or select an existing one
4. Copy the API key
5. Paste it into your `.env` file

#### Step 4: (Optional) Start FHIR Server

The FHIR server provides medical data for evaluation tasks. This is optional but recommended for full functionality.

```bash
# Start FHIR server (takes 1-2 minutes to initialize)
./scripts/start_fhir.sh

# Verify it's running
curl http://localhost:8080/fhir/metadata
```

The FHIR server runs on port `8080` by default.

#### Step 5: (Optional) Start MCP Server

The MCP server exposes FHIR tools to agents. Start this if you want agents to use FHIR tools during evaluation.

```bash
# Start MCP server (requires FHIR server from Step 4)
./scripts/start_mcp.sh

# Or manually:
export MCP_FHIR_API_BASE="http://localhost:8080/fhir/"
# Purple mode (clinical reasoning only):
python -m mcp_skills.fastmcp.server --host 0.0.0.0 --port 8002
# Green mode (with evaluation/groundtruth tools):
python -m mcp_skills.fastmcp.server --agent-type green --host 0.0.0.0 --port 8002

# Verify it's running
curl http://localhost:8002/health
```

The MCP server runs on port `8002` by default.

#### Step 6: Start MedAgentBench Evaluator (Green Agent) Server

```bash
# Start the MedAgentBench evaluator (green agent) server
python src/server.py

# Or with custom host/port
python src/server.py --host 0.0.0.0 --port 9009

# Or using make
make run
```

**Expected output:**
```
Starting PharmD Green Agent on 0.0.0.0:9009
Agent card URL: http://localhost:9009/
```

**Verify the server is running:**
```bash
# Check agent card
curl http://localhost:9009/.well-known/agent-card.json

# Should return JSON with agent metadata
```

The server is now ready to accept evaluation requests.

#### Step 7: Run Tests

**Unit Tests (no external services required):**
```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

**Integration Test (requires purple agent):**

Open **3 separate terminals**:

**Terminal 1 - Start PharmD Agent (Purple Agent):**
```bash
cd /root/streamlit/Agents/PharmAgent
python tests/mock_purple_agent.py
```

**Terminal 2 - Start MedAgentBench Evaluator (Green Agent):**
```bash
cd /root/streamlit/Agents/PharmAgent
python src/server.py
```

**Terminal 3 - Run Integration Test:**
```bash
cd /root/streamlit/Agents/PharmAgent
python examples/full_test.py
```

### Docker Commands

#### MCP Server
# Build the image
docker build -f mcp_skills/Dockerfile -t mcp-server .

# Run the container
docker run -p 8002:8002 mcp-server

# If port is already in use, stop existing container:
docker ps | grep 8002
docker stop <container_id>

# Or use a different port:
docker run -p 8003:8002 mcp-server

#### MedAgentBench Evaluator (Green Agent)
# Build the image
docker build -t hxwh/ai-pharmd-medagentbench-green:latest .

# Run the container
docker run -p 9009:9009 hxwh/ai-pharmd-medagentbench-green:latest

#### PharmD Agent (Purple Agent)
# Build the image
docker build -f purple_agent/Dockerfile -t hxwh/ai-pharmd-medagentbench-purple:latest .

# Run the container
docker run -p 9019:9019 hxwh/ai-pharmd-medagentbench-purple:latest

### Quick Start Script

For automated setup and verification:

```bash
# Run quick start script (checks environment, installs deps, runs tests)
./scripts/quick-start.sh
```

### Common First-Run Scenarios

**Scenario A: Minimal Setup (MedAgentBench Evaluator Only)**
```bash
# Steps 1-3, then Step 6
cd /root/streamlit/Agents/PharmAgent
pip install -e ".[test]"
cp sample.env .env
# Edit .env with GOOGLE_API_KEY
python src/server.py
```

**Scenario B: Full Setup (With FHIR Data)**
```bash
# Steps 1-6 in order
# This enables agents to use FHIR tools during evaluation
```

**Scenario C: Testing Setup**
```bash
# Steps 1-3, then Step 7 (Terminal 1-3)
# Use mock PharmD agent for testing without real FHIR data
```

## Orchestration System

PharmAgent implements a sophisticated **multi-level orchestration architecture** that coordinates multiple agents, workflows, and evaluation processes. The system uses a hierarchical approach with specialized orchestrators at different levels.

### High-Level Scenario Orchestration

The **Scenario Runner** (`scripts/run_scenario.py`) orchestrates entire evaluation scenarios:
- Starts and manages agent lifecycles
- Coordinates multi-agent interactions via A2A protocol
- Handles batch task processing (300 tasks across 10 task types)
- Provides comprehensive evaluation reporting

### Agent-Level Orchestration

**Green Agent (Evaluator)** acts as the main orchestrator:
- Validates evaluation requests and manages task execution
- Uses the **Purple Agent (Participant)** for clinical reasoning tasks
- Communication occurs via **A2A protocol** with structured message passing
- Supports both single-task and batch evaluation modes

### Workflow-Level Orchestration

**PocketFlow Framework** provides the core workflow orchestration engine:
- Implements a **node-based architecture** with `Node` and `AsyncNode` classes
- Supports both synchronous and asynchronous workflow execution
- Uses `prep() → exec() → post()` lifecycle pattern for each node
- Enables conditional branching and error handling

**Main Evaluation Pipeline:**
```
LoadTaskNode          # Loads task definitions from JSON files
  ↓
PrepareContextNode    # Discovers MCP tools dynamically + prepares prompt
  ↓
SendToAgentNode       # Sends task to Purple Agent via A2A protocol
  ↓
ValidateResponseNode  # Validates FINISH([answer1, answer2, ...]) format
  ↓
ScoreResultNode       # Calls MCP server to compute ground truth dynamically
  ↓
GenerateReportNode    # Final evaluation report
```

**Conditional Branching:**
- **Valid Response Path:** `ValidateResponseNode → ScoreResultNode → GenerateReportNode`
- **Invalid Response Path:** `ValidateResponseNode → RecordFailureNode → GenerateReportNode`

### Message Routing and Coordination

**A2A Protocol Messenger** (`src/messenger.py`):
- Manages conversation contexts via context ID mapping
- Supports streaming responses with status update callbacks
- Routes messages between Green and Purple agents
- Handles context persistence across conversations

**Event-Driven Updates:**
- **Status Forwarding:** Purple Agent status updates flow through Green Agent's event queue
- **Real-Time Monitoring:** Enables progress tracking during task execution
- **Shared State Management:** Uses shared dictionaries to pass data between workflow nodes

### Agent Management

**Context-Based Agent Instances** (`src/executor.py`):
- Each conversation context gets its own agent instance (`context_id → agent`)
- Enables concurrent multi-agent evaluations
- Managed by the `Executor` class with agent lifecycle handling

### Workflow Execution Patterns

**PocketFlow Architecture:**
- **Node Types:** `Node` (sync), `AsyncNode` (async), `Flow`, `AsyncFlow`
- **Execution Modes:** Sequential and parallel node execution
- **Error Handling:** Comprehensive failure taxonomy and recovery mechanisms
- **Batch Processing:** Aggregates results across multiple tasks

**Task Execution Flow:**
```python
# Agent.run() method orchestrates:
1. Parse and validate request
2. Determine tasks to run (single/batch)
3. For each task:
   - Create shared store with task config
   - Build flow: flow = build_single_task_flow()
   - Execute: await flow.run_async(shared)
   - Aggregate results
4. Generate final report
```

### Key Orchestration Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Scenario Runner** | `scripts/run_scenario.py` | High-level scenario orchestration |
| **Green Agent** | `src/agent.py` | Main evaluation orchestrator |
| **PocketFlow Engine** | `src/pocketflow.py` | Workflow orchestration engine |
| **Workflow Nodes** | `src/nodes.py` | Individual task execution steps |
| **Flow Builder** | `src/flow.py` | Constructs evaluation pipelines |
| **A2A Messenger** | `src/messenger.py` | Agent communication protocol |
| **Executor** | `src/executor.py` | Agent instance management |
| **MCP Server** | `mcp_skills/fastmcp/server.py` | Tool access coordination |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Scenario Runner (run_scenario.py)          │
│              - Starts agents                             │
│              - Sends assessment requests                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Green Agent Server (server.py)                  │
│         - A2A Protocol Endpoint                         │
│         - Executor (executor.py)                        │
│           └─ Manages Agent instances per context        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Green Agent (agent.py)                         │
│         - Validates requests                            │
│         - Orchestrates evaluation flow                  │
│         - Builds PocketFlow workflow                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         PocketFlow Engine (pocketflow.py)              │
│         - Executes node-based workflow                  │
│         - Handles async/sync nodes                      │
│         - Manages flow transitions                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Workflow Nodes (nodes.py)                      │
│         - LoadTaskNode                                  │
│         - PrepareContextNode                            │
│         - SendToAgentNode ──┐                          │
│         - ValidateResponseNode                         │
│         - ScoreResultNode                              │
│         - GenerateReportNode                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ A2A Protocol
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Purple Agent (purple_agent/src/agent.py)      │
│         - Executes clinical reasoning tasks             │
│         - Uses MCP tools                               │
│         - Returns FINISH([answer]) format              │
└─────────────────────────────────────────────────────────┘
```

### Orchestration Features

- **Hierarchical Orchestration**: Multi-level coordination from scenarios to individual tasks
- **Event-Driven Architecture**: Real-time status updates and progress monitoring
- **Context Management**: Isolated agent instances per conversation
- **Conditional Workflows**: Dynamic branching based on task outcomes
- **Batch Processing**: Efficient handling of multiple evaluation tasks
- **Error Recovery**: Comprehensive failure handling and reporting
- **Shared State**: Coordinated data flow between workflow components

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key (required) | - |
| `GREEN_AGENT_HOST` | Server host | `127.0.0.1` |
| `GREEN_AGENT_PORT` | Server port | `9009` |
| `GREEN_AGENT_CARD_URL` | Agent card URL | `http://localhost:9009/` |
| `FHIR_MCP_SERVER_URL` | MCP server URL | `http://localhost:8002` |
| `MAX_ROUNDS` | Maximum LLM rounds | `10` |
| `TASK_TIMEOUT` | Task timeout (seconds) | `300` |

See `sample.env` for all available options.

## Running with Docker

This section provides comprehensive step-by-step instructions for running PharmD Agent System components in Docker containers, including the MedAgentBench Evaluator (Green Agent), PharmD Agent (Purple Agent), MCP Server, and inter-container networking.

**⚠️ Important: All docker commands must be run from the project root directory** (`/root/streamlit/Agents/PharmAgent/`) where the `.env` file is located.

### Prerequisites

- Docker installed and running
- `.env` file with required environment variables (see Step 3 above) located in the project root
- At least 4GB RAM available for containers

### Step 1: Create Docker Network

Create a dedicated network for inter-container communication:

```bash
# Create medagentbench network
docker network create aipharmd-net

# Verify network creation
docker network ls | grep medagentbench
```

### Step 2: Build and Run MCP Server (FHIR Tools)

The MCP Server provides FHIR tools that agents use for medical data access.

```bash
# Build MCP Server image (from project root)
docker build -f mcp_skills/Dockerfile -t aipharmd-mcp:latest .

# Run MCP Server on network
docker run -d \
  --name medagentbench-mcp \
  --network aipharmd-net \
  -p 127.0.0.1:8002:8002 \
  aipharmd-mcp:latest

# Verify MCP Server
curl http://localhost:8002/health || echo "MCP Server starting..."
```

### Step 3: Build and Run Green Agent (Evaluator)

The Green Agent evaluates and scores agent performance.

```bash
# Build Green Agent image (from project root)
docker build -f Dockerfile -t aipharmd-green:latest .

# Run Green Agent on network
# Note: --env-file .env requires running from project root where .env exists
docker run -d \
  --name medagentbench-green \
  --network aipharmd-net \
  --env-file .env \
  -p 127.0.0.1:9009:9009 \
  -e GREEN_AGENT_HOST=0.0.0.0 \
  -e GREEN_AGENT_PORT=9009 \
  aipharmd-green:latest

# Verify Green Agent
sleep 5
curl http://localhost:9009/.well-known/agent-card.json
```

### Step 4: Build and Run Purple Agent (Agent Under Test)

The Purple Agent is the medical AI agent being evaluated.

```bash
# Build Purple Agent image (from project root)
docker build -f src/purple/Dockerfile.purple-agent -t aipharmd-purple:latest .

# Run Purple Agent on network
# Note: --env-file .env requires running from project root where .env exists
docker run -d \
  --name medagentbench-purple \
  --network aipharmd-net \
  --env-file .env \
  -p 127.0.0.1:9019:9019 \
  -e PURPLE_AGENT_HOST=0.0.0.0 \
  -e PURPLE_AGENT_PORT=9019 \
  -e MCP_FHIR_API_BASE=http://medagentbench-mcp:8002 \
  aipharmd-purple:latest

# Verify Purple Agent
sleep 5
curl http://localhost:9019/.well-known/agent-card.json
```

### Step 5: Verify All Services

Check that all containers are running and can communicate:

```bash
# List all PharmD Agent System containers
docker ps | grep medagentbench

# Check container logs
docker logs medagentbench-green
docker logs medagentbench-purple
docker logs medagentbench-mcp

# Test inter-container connectivity
docker exec medagentbench-green curl -s http://medagentbench-mcp:8002/health
```

### Step 6: Run Evaluation with uv

Use uv to run tests against your running agents:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Sync project dependencies
uv sync --dev

# Run tests against running Green Agent
uv run pytest tests/ -v --agent-url http://localhost:9009

# Run specific test suite
uv run pytest tests/test_agent.py -v

# Run integration tests (requires all services)
uv run pytest tests/full_test.py -v

# Run evaluation script
uv run python scripts/run_evaluation.py --task task_001 --green http://localhost:9009 --purple http://localhost:9019
```

### Alternative: Using Docker Compose

For easier management, use the provided docker-compose setup:

```bash
# Build and run all services
docker compose up --build -d

# View logs
docker compose logs -f

# Run tests
uv sync --dev
uv run pytest tests/ -v

# Stop all services
docker compose down
```

### Troubleshooting Docker Setup

**Container connectivity issues:**
```bash
# Check network connectivity
docker network inspect aipharmd-net

# Test service discovery
docker exec medagentbench-green nslookup medagentbench-mcp
```

**Port conflicts:**
```bash
# Find conflicting processes
lsof -i :9009

# Use different ports
docker run -p 127.0.0.1:9099:9009 --name aipharmd-green-alt aipharmd-green:latest
```

**Resource constraints:**
```bash
# Check Docker resource usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
```

**Clean restart:**
```bash
# Stop and remove all containers
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

# Remove network
docker network rm aipharmd-net

# Rebuild from scratch
docker system prune -f
```

## Testing

Run A2A conformance tests against your agent.

# Install test dependencies
uv sync --extra test

# Start your agent (uv or docker; see above)

# Run with coverage
pytest tests/ --cov=src
```
```

# Run tests against your running agent URL
uv run pytest --agent-url http://localhost:9009


### Integration Test

**Prerequisites:** Both green and purple agents must be running.

**Step-by-step:**

1. **Terminal 1 - Start Purple Agent (Mock):**
   ```bash
   cd /root/streamlit/Agents/PharmAgent
   python tests/mock_purple_agent.py
   ```
   Expected output: `🟣 Starting Mock Purple Agent on http://0.0.0.0:9019`

2. **Terminal 2 - Start Green Agent:**
   ```bash
   cd /root/streamlit/Agents/PharmAgent
   python src/server.py
   ```
   Expected output: `Starting PharmD Green Agent on 0.0.0.0:9009`

3. **Terminal 3 - Run Integration Test:**
   ```bash
   cd /root/streamlit/Agents/PharmAgent
   python examples/full_test.py
   ```
   This sends evaluation requests from green agent to purple agent and verifies the response.

**What the test does:**
- Green agent loads a medical task
- Sends task to purple agent via A2A protocol
- Purple agent responds with answer
- Green agent validates and scores the response
- Prints evaluation results

## Examples

### Example Purple Agent

See `purple_agent/src/server.py` for a complete implementation of a purple agent that:
- Discovers MCP tools dynamically
- Uses LLM (Gemini) to reason about tasks
- Calls FHIR tools via MCP
- Returns structured responses

### Testing with Mock Agent

```bash
# Start mock purple agent
python tests/mock_purple_agent.py

# In another terminal, test evaluation
python examples/test_evaluation.py
```

## API Usage

### Agent Card

```bash
curl http://localhost:9009/.well-known/agent-card.json
```

### Send Evaluation Request

```python
import httpx
import json

request = {
    "jsonrpc": "2.0",
    "method": "message",
    "params": {
        "message": {
            "kind": "message",
            "role": "user",
            "parts": [{
                "kind": "text",
                "text": json.dumps({
                    "participants": {
                        "agent": "http://localhost:9019"
                    },
                    "config": {
                        "task_id": "task_001"
                    }
                })
            }]
        }
    }
}

response = httpx.post("http://localhost:9009/", json=request)
print(response.json())
```

## Development

### Project Structure Principles

- **Simplicity**: Minimal code that solves the problem
- **PocketFlow Pattern**: Uses PocketFlow for workflow orchestration
- **Template Alignment**: Follows A2A agent template structure where applicable

### Adding New Nodes

1. Create a new node class in `src/nodes.py` inheriting from `Node` or `AsyncNode`
2. Implement `prep()`, `exec()`, and `post()` methods
3. Add node to flow in `src/flow.py`

### Adding New Tasks

Tasks are organized in subtask folders. The original PharmD evaluation tasks are in `src/tasks/subtask1/`. The benchmark includes 10 official task types from [Stanford MedAgentBench](https://github.com/stanfordmlgroup/MedAgentBench):

**Current Task Organization:**
- `subtask1/`: Original MedAgentBench evaluation tasks (10 tasks)
- `subtask2/`: Reserved for future task sets

Tasks are defined in `src/tasks/subtask1/tasks.json`:

| ID | Type | Description |
|----|------|-------------|
| task1 | read_query | Simple FHIR query with predefined answer |
| task2 | calculate_age | Calculate patient age from DOB |
| task3 | record_vitals | Record BP observation (POST) |
| task4 | read_lab | Get latest magnesium in 24h |
| task5 | check_and_order_magnesium | Check Mg + order IV replacement if low |
| task6 | calculate_average | Average glucose over 24h |
| task7 | read_lab | Get latest glucose |
| task8 | order_consult | Order ortho consult with SBAR note |
| task9 | check_and_order_potassium | Check K + order replacement + recheck |
| task10 | check_and_order_a1c | Check A1C + order if >1 year old |

Task entry format:
```json
{
  "id": "task1",
  "type": "read_query",
  "description": "Find the patient's current problem list.",
  "question": "What are the patient's current medical problems?",
  "eval_MRN": "S2874099",
  "readonly": true,
  "post_count": 0,
  "evaluator": "task1"
}
```

Reference solutions in `src/tasks/subtask1/refsol.py` evaluate agent responses.

**Note:** When adding new tasks to `subtask1` or creating new subtask folders, ensure:
- Task JSON files follow the same format as `subtask1/tasks.json`
- Reference solutions are added to the corresponding `refsol.py`
- Import paths are updated if needed (see `src/nodes.py`, `src/utils/evaluation.py`, `src/utils/fhir.py`)

## Verification Checklist

After setup, verify everything is working:

- [ ] **Dependencies installed**: `python -c "import a2a; import fastmcp; print('OK')"`
- [ ] **Environment configured**: `.env` file exists with `GOOGLE_API_KEY` set
- [ ] **Green agent running**: `curl http://localhost:9009/.well-known/agent-card.json` returns JSON
- [ ] **Unit tests pass**: `pytest tests/ -v` completes successfully
- [ ] **(Optional) FHIR server running**: `curl http://localhost:8080/fhir/metadata` returns metadata
- [ ] **(Optional) MCP server running**: `curl http://localhost:8002/health` returns OK

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **"Module not found"** | Run `pip install -e ".[test]"` to install dependencies |
| **"GOOGLE_API_KEY not set"** | Create `.env` file with `GOOGLE_API_KEY=your_key_here` |
| **"API key not valid"** | Get new API key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| **"Connection refused 9009"** | Start green agent: `python src/server.py` |
| **"Connection refused 9019"** | Start purple agent: `python tests/mock_purple_agent.py` |
| **"FHIR server not responding"** | Start FHIR server: `./scripts/start_fhir.sh` (takes 1-2 min) |
| **"MCP server not responding"** | Start MCP server: `./scripts/start_mcp.sh` (requires FHIR server) |
| **"ImportError: cannot import name"** | Ensure you're in project root: `cd /root/streamlit/Agents/PharmAgent` |
| **"Port already in use"** | Change port: `python src/server.py --port 9010` or stop existing process |

### Debug Steps

1. **Check Python version**: `python --version` (must be 3.10+)
2. **Verify installation**: `pip list | grep -E "(a2a|fastmcp|pocketflow)"`
3. **Check environment**: `cat .env | grep GOOGLE_API_KEY`
4. **Test server manually**: `curl -v http://localhost:9009/.well-known/agent-card.json`
5. **Check logs**: Look for error messages in terminal output

### Getting Help

- See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed troubleshooting
- See [docs/SETUP.md](docs/SETUP.md) for complete setup guide
- Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for advanced issues

## Publishing

The repository includes a GitHub Actions workflow that automatically builds, tests, and publishes a Docker image to GitHub Container Registry.

- **Push to `main`** → publishes `latest` tag
- **Create a git tag** (e.g., `v1.0.0`) → publishes version tags

## Quick Start: Step-by-Step Commands

Follow these commands in order to run the complete PharmD Agent System.

### Prerequisites Check

```bash
# Navigate to project directory
cd /root/streamlit/Agents/PharmAgent

# Verify Python version (3.10+ required)
python --version

# Verify Docker is installed (for FHIR server)
docker --version
```

### Step 1: Install Dependencies

```bash
# Install package with test dependencies
pip install -e ".[test]"

# Verify installation
python -c "import a2a; import fastmcp; import pocketflow; print('✓ Dependencies installed')"
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp sample.env .env

# Edit .env file (add your Google API key)
# Required: GOOGLE_API_KEY=your_key_here
nano .env  # or use your preferred editor
```

**Required in `.env`:**
```bash
GOOGLE_API_KEY=your_google_api_key_here
```

### Step 3: Start FHIR Server (Optional but Recommended)

```bash
# Option A: Use automated script
./scripts/start_fhir.sh

# Option B: Manual Docker command
docker pull jyxsu6/medagentbench:latest
docker tag jyxsu6/medagentbench:latest medagentbench
docker run -d --name medagentbench-fhir -p 8080:8080 medagentbench

# Wait for server to be ready (~1-2 minutes)
curl http://localhost:8080/fhir/metadata
```

### Step 4: Start MCP Server (Optional but Recommended)

```bash
# Option A: Use automated script (requires FHIR server)
./scripts/start_mcp.sh

# Option B: Manual command
export MCP_FHIR_API_BASE="http://localhost:8080/fhir/"
python -m mcp_skills.fastmcp.server --host 0.0.0.0 --port 8002

# Verify in another terminal
curl http://localhost:8002/health
```

### Step 5: Start Green Agent (Evaluator)

**Terminal 1:**
```bash
cd /root/streamlit/Agents/PharmAgent

# Option A: Direct Python command
python src/server.py

# Option B: Using Make
make run

# Option C: Using run script
./scripts/run.sh

# Expected output:
# Starting PharmD Green Agent on 0.0.0.0:9009
# Agent card URL: http://localhost:9009/
```

**Verify Green Agent:**
```bash
# In another terminal
curl http://localhost:9009/.well-known/agent-card.json
```

### Step 6: Start Purple Agent (Agent Under Test)

**Terminal 2:**
```bash
cd /root/streamlit/Agents/PharmAgent

# Option A: Mock Purple Agent (for testing)
python tests/mock_purple_agent.py

# Option B: Full Purple Agent (requires MCP server)
make run-purple
# or
python -m src.purple.server

# Expected output:
# 🟣 Starting Mock Purple Agent on http://0.0.0.0:9019
# or
# 🟣 Starting Purple Agent on http://0.0.0.0:9019
```

**Verify Purple Agent:**
```bash
# In another terminal
curl http://localhost:9019/.well-known/agent-card.json
```

### Step 7: Run Evaluation

**Terminal 3:**
```bash
cd /root/streamlit/Agents/PharmAgent

# Option A: Full integration test
python examples/full_test.py

# Option B: Run all tasks
python scripts/run_all_tasks.py

# Option C: Run specific evaluation
python scripts/run_evaluation.py --task-id task1

# Expected output:
# ✅ Evaluation completed
# Score: 1.0
# Correct: True
```

### Quick Test (Unit Tests Only)

```bash
# Run unit tests (no external services needed)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Quick test script
./scripts/test.sh
```

### One-Command Startup (Full Stack)

```bash
# Start FHIR + MCP servers together
./scripts/run_all.sh

# Then in separate terminals:
# Terminal 1: python src/server.py
# Terminal 2: python tests/mock_purple_agent.py
# Terminal 3: python examples/full_test.py
```

### Complete Workflow Summary

```bash
# 1. Install
cd /root/streamlit/Agents/PharmAgent
pip install -e ".[test]"
cp sample.env .env
# Edit .env with GOOGLE_API_KEY

# 2. Start infrastructure (Terminal 1)
./scripts/run_all.sh  # Starts FHIR + MCP

# 3. Start Green Agent (Terminal 2)
python src/server.py

# 4. Start Purple Agent (Terminal 3)
python tests/mock_purple_agent.py

# 5. Run evaluation (Terminal 4)
python examples/full_test.py
```

### Stopping Services

```bash
# Stop FHIR server
docker stop medagentbench-fhir
docker rm medagentbench-fhir

# Stop MCP server (if running in foreground)
# Press Ctrl+C in the terminal

# Stop Green/Purple agents
# Press Ctrl+C in their respective terminals
```

### Troubleshooting Commands

```bash
# Check if services are running
curl http://localhost:8080/fhir/metadata  # FHIR server
curl http://localhost:8002/health         # MCP server
curl http://localhost:9009/.well-known/agent-card.json  # Green agent
curl http://localhost:9019/.well-known/agent-card.json  # Purple agent

# Check Docker containers
docker ps | grep medagentbench

# Check Python imports
python -c "from tasks.subtask1 import get_task; print('✓ Tasks import OK')"

# Verify environment variables
cat .env | grep GOOGLE_API_KEY
```

## License

See [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
